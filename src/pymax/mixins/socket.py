import asyncio
import socket
import ssl
import sys
from collections.abc import Callable
from typing import Any

import lz4.block
import msgpack
from typing_extensions import override

from pymax.exceptions import SocketNotConnectedError, SocketSendError
from pymax.filters import Filter, Message
from pymax.interfaces import ClientProtocol
from pymax.payloads import BaseWebSocketMessage, SyncPayload, UserAgentPayload
from pymax.static.constant import DEFAULT_TIMEOUT
from pymax.static.enum import MessageStatus, Opcode
from pymax.types import Channel, Chat, Dialog, Me


class SocketMixin(ClientProtocol):

    def __init__(self, token: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token = token

    @property
    def sock(self) -> socket.socket:
        if self._socket is None or not self.is_connected:
            self.logger.critical("Socket not connected when access attempted")
            raise SocketNotConnectedError()
        return self._socket

    def _unpack_packet(self, data: bytes) -> dict[str, Any] | None:
        ver = int.from_bytes(data[0:1], "big")
        cmd = int.from_bytes(data[1:3], "big")
        seq = int.from_bytes(data[3:4], "big")
        opcode = int.from_bytes(data[4:6], "big")
        packed_len = int.from_bytes(data[6:10], "big", signed=False)
        comp_flag = packed_len >> 24
        payload_length = packed_len & 0xFFFFFF
        payload_bytes = data[10 : 10 + payload_length]

        payload = None
        if payload_bytes:
            if comp_flag != 0:
                # TODO: надо выяснить правильный размер распаковки
                # uncompressed_size = int.from_bytes(payload_bytes[0:4], "big")
                compressed_data = payload_bytes
                try:
                    payload_bytes = lz4.block.decompress(
                        compressed_data,
                        uncompressed_size=99999,
                    )
                except lz4.block.LZ4BlockError:
                    return None
            payload = msgpack.unpackb(
                payload_bytes, raw=False, strict_map_key=False
            )

        return {
            "ver": ver,
            "cmd": cmd,
            "seq": seq,
            "opcode": opcode,
            "payload": payload,
        }

    def _pack_packet(
        self,
        ver: int,
        cmd: int,
        seq: int,
        opcode: int,
        payload: dict[str, Any],
    ) -> bytes:
        ver_b = ver.to_bytes(1, "big")
        cmd_b = cmd.to_bytes(2, "big")
        seq_b = seq.to_bytes(1, "big")
        opcode_b = opcode.to_bytes(2, "big")
        payload_bytes: bytes | None = msgpack.packb(payload)
        if payload_bytes is None:
            payload_bytes = b""
        payload_len = len(payload_bytes) & 0xFFFFFF
        self.logger.debug(
            "Packing message: payload size=%d bytes", len(payload_bytes)
        )
        payload_len_b = payload_len.to_bytes(4, "big")
        return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes

    async def _connect(self, user_agent: UserAgentPayload) -> dict[str, Any]:
        try:
            if sys.version_info[:2] == (3, 12):
                self.logger.warning(
                    """
===============================================================
         ⚠️⚠️ \033[0;31mWARNING: Python 3.12 detected!\033[0m ⚠️⚠️
Socket connections may be unstable, SSL issues are possible.
===============================================================
    """
                )
            self.logger.info(
                "Connecting to socket %s:%s", self.host, self.port
            )
            loop = asyncio.get_running_loop()
            raw_sock = await loop.run_in_executor(
                None, lambda: socket.create_connection((self.host, self.port))
            )
            self._socket = self._ssl_context.wrap_socket(
                raw_sock, server_hostname=self.host
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.is_connected = True
            self._incoming = asyncio.Queue()
            self._pending = {}
            self._recv_task = asyncio.create_task(self._recv_loop())
            self.logger.info("Socket connected, starting handshake")
            return await self._handshake(user_agent)
        except Exception as e:
            self.logger.error("Failed to connect: %s", e, exc_info=True)
            raise ConnectionError(f"Failed to connect: {e}")

    async def _handshake(self, user_agent: UserAgentPayload) -> dict[str, Any]:
        try:
            self.logger.debug(
                "Sending handshake with user_agent keys=%s",
                user_agent.model_dump().keys(),
            )
            resp = await self._send_and_wait(
                opcode=Opcode.SESSION_INIT,
                payload={
                    "deviceId": str(self._device_id),
                    "userAgent": user_agent,
                },
            )
            self.logger.info("Handshake completed")
            return resp
        except Exception as e:
            self.logger.error("Handshake failed: %s", e, exc_info=True)
            raise ConnectionError(f"Handshake failed: {e}")

    async def _recv_loop(self) -> None:
        if self._socket is None:
            self.logger.warning("Recv loop started without socket instance")
            return

        sock = self._socket
        loop = asyncio.get_running_loop()

        def _recv_exactly(n: int) -> bytes:
            """Синхронная функция: читает ровно n байт из сокета или возвращает b'' если закрыт."""
            buf = bytearray()
            while len(buf) < n:
                chunk = sock.recv(n - len(buf))
                if not chunk:
                    return bytes(buf)
                buf.extend(chunk)
            return bytes(buf)

        try:
            while True:
                try:
                    header = await loop.run_in_executor(
                        None, lambda: _recv_exactly(10)
                    )
                    if not header or len(header) < 10:
                        self.logger.info(
                            "Socket connection closed; exiting recv loop"
                        )
                        self.is_connected = False
                        try:
                            sock.close()
                        except Exception:
                            pass  # nosec B110
                        finally:
                            break

                    packed_len = int.from_bytes(
                        header[6:10], "big", signed=False
                    )
                    payload_length = packed_len & 0xFFFFFF
                    remaining = payload_length
                    payload = bytearray()

                    while remaining > 0:
                        min_read = min(remaining, 8192)
                        chunk = await loop.run_in_executor(
                            None, _recv_exactly, min_read
                        )
                        if not chunk:
                            self.logger.error(
                                "Connection closed while reading payload"
                            )
                            break
                        payload.extend(chunk)
                        remaining -= len(chunk)

                    if remaining > 0:
                        self.logger.error(
                            "Incomplete payload received; skipping packet"
                        )
                        continue

                    raw = header + payload
                    if len(raw) < 10 + payload_length:
                        self.logger.error(
                            "Incomplete packet: expected %d bytes, got %d",
                            10 + payload_length,
                            len(raw),
                        )
                        await asyncio.sleep(0.5)
                        continue

                    data = self._unpack_packet(raw)
                    if not data:
                        self.logger.warning(
                            "Failed to unpack packet, skipping"
                        )
                        continue

                    payload_objs = data.get("payload")
                    datas = (
                        [{**data, "payload": obj} for obj in payload_objs]
                        if isinstance(payload_objs, list)
                        else [data]
                    )

                    for data_item in datas:
                        seq = data_item.get("seq")
                        fut = (
                            self._pending.get(seq)
                            if isinstance(seq, int)
                            else None
                        )
                        if fut and not fut.done():
                            fut.set_result(data_item)
                            self.logger.debug(
                                "Matched response for pending seq=%s", seq
                            )
                            continue

                        if self._incoming is not None:
                            try:
                                self._incoming.put_nowait(data_item)
                            except asyncio.QueueFull:
                                self.logger.warning(
                                    "Incoming queue full; dropping message seq=%s",
                                    seq,
                                )

                        if (
                            data_item.get("opcode") == Opcode.NOTIF_MESSAGE
                            and self._on_message_handlers
                        ):
                            try:
                                for (
                                    handler,
                                    filter,
                                ) in self._on_message_handlers:
                                    payload = data_item.get("payload", {})
                                    msg_dict = (
                                        payload
                                        if isinstance(payload, dict)
                                        else None
                                    )
                                    msg = (
                                        Message.from_dict(msg_dict)
                                        if msg_dict
                                        else None
                                    )
                                    if msg and msg.status:
                                        if msg.status == MessageStatus.EDITED:
                                            for (
                                                edit_handler,
                                                edit_filter,
                                            ) in (
                                                self._on_message_edit_handlers
                                            ):
                                                await self._process_message_handler(
                                                    handler=edit_handler,
                                                    filter=edit_filter,
                                                    message=msg,
                                                )
                                        elif (
                                            msg.status == MessageStatus.REMOVED
                                        ):
                                            for (
                                                remove_handler,
                                                remove_filter,
                                            ) in (
                                                self._on_message_delete_handlers
                                            ):
                                                await self._process_message_handler(
                                                    handler=remove_handler,
                                                    filter=remove_filter,
                                                    message=msg,
                                                )
                                        await self._process_message_handler(
                                            handler=handler,
                                            filter=filter,
                                            message=msg,
                                        )
                            except Exception:
                                self.logger.exception(
                                    "Error in on_message_handler"
                                )
                except asyncio.CancelledError:
                    self.logger.debug("Recv loop cancelled")
                    break
                except Exception:
                    self.logger.exception(
                        "Error in recv_loop; backing off briefly"
                    )
                    await asyncio.sleep(0.5)
        finally:
            self.logger.warning("<<< Recv loop exited (socket)")

    def _log_task_exception(self, task: asyncio.Task[Any]) -> None:
        try:
            exc = task.exception()
            if exc:
                self.logger.exception("Background task exception: %s", exc)
        except Exception as e:
            self.logger.exception("Error getting task exception: %s", e)
            pass

    async def _process_message_handler(
        self,
        handler: Callable[[Message], Any],
        filter: Filter | None,
        message: Message,
    ) -> None:
        if filter and not filter.match(message):
            return

        result = handler(message)
        if asyncio.iscoroutine(result):
            task = asyncio.create_task(result)
            self._background_tasks.add(task)
            task.add_done_callback(
                lambda t: self._background_tasks.discard(t)  # type: ignore[func-returns-value]
                or self._log_task_exception(t)  # type: ignore[func-returns-value]
            )

    async def _send_interactive_ping(self) -> None:
        while self.is_connected:
            try:
                await self._send_and_wait(
                    opcode=Opcode.PING,
                    payload={"interactive": True},
                    cmd=0,
                )
                self.logger.debug(
                    "Interactive ping sent successfully (socket)"
                )
            except Exception:
                self.logger.warning(
                    "Interactive ping failed (socket)", exc_info=True
                )
            await asyncio.sleep(30)

    def _make_message(
        self, opcode: Opcode, payload: dict[str, Any], cmd: int = 0
    ) -> dict[str, Any]:
        self._seq += 1
        msg = BaseWebSocketMessage(
            cmd=cmd,
            seq=self._seq,
            opcode=opcode.value,
            payload=payload,
        ).model_dump(by_alias=True)
        self.logger.debug(
            "make_message opcode=%s cmd=%s seq=%s", opcode, cmd, self._seq
        )
        return msg

    @override
    async def _send_and_wait(
        self,
        opcode: Opcode,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if not self.is_connected or self._socket is None:
            raise SocketNotConnectedError
        sock = self.sock
        msg = self._make_message(opcode, payload, cmd)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[msg["seq"]] = fut
        try:
            self.logger.debug(
                "Sending frame opcode=%s cmd=%s seq=%s",
                opcode,
                cmd,
                msg["seq"],
            )
            packet = self._pack_packet(
                msg["ver"],
                msg["cmd"],
                msg["seq"],
                msg["opcode"],
                msg["payload"],
            )
            await loop.run_in_executor(None, lambda: sock.sendall(packet))
            data = await asyncio.wait_for(fut, timeout=timeout)
            self.logger.debug(
                "Received frame for seq=%s opcode=%s",
                data.get("seq"),
                data.get("opcode"),
            )
            return data

        except (ssl.SSLEOFError, ssl.SSLError, ConnectionError) as conn_err:
            self.logger.warning("Connection lost, reconnecting...")
            self.is_connected = False
            try:
                await self._connect(self.user_agent)
            except Exception as exc:
                self.logger.exception("Reconnect failed")
                raise exc from conn_err
            raise SocketNotConnectedError from conn_err
        except Exception as exc:
            self.logger.exception(
                "Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"]
            )
            raise SocketSendError from exc

        finally:
            self._pending.pop(msg["seq"], None)

    async def _sync(self) -> None:
        try:
            self.logger.info("Starting initial sync (socket)")
            payload = SyncPayload(
                interactive=True,
                token=self._token,
                chats_sync=0,
                contacts_sync=0,
                presence_sync=0,
                drafts_sync=0,
                chats_count=40,
            ).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.LOGIN, payload=payload
            )
            raw_payload = data.get("payload", {})
            if error := raw_payload.get("error"):
                self.logger.error("Sync error: %s", error)
                return
            for raw_chat in raw_payload.get("chats", []):
                try:
                    if raw_chat.get("type") == "DIALOG":
                        self.dialogs.append(Dialog.from_dict(raw_chat))
                    elif raw_chat.get("type") == "CHAT":
                        self.chats.append(Chat.from_dict(raw_chat))
                    elif raw_chat.get("type") == "CHANNEL":
                        self.channels.append(Channel.from_dict(raw_chat))
                except Exception:
                    self.logger.exception("Error parsing chat entry (socket)")
            if raw_payload.get("profile", {}).get("contact"):
                self.me = Me.from_dict(
                    raw_payload.get("profile", {}).get("contact", {})
                )
            self.logger.info(
                "Sync completed: dialogs=%d chats=%d channels=%d",
                len(self.dialogs),
                len(self.chats),
                len(self.channels),
            )
        except Exception:
            self.logger.exception("Sync failed (socket)")

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

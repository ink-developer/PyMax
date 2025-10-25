import asyncio
import socket
import ssl
import sys
import time
from collections.abc import Callable
from typing import Any

import lz4.block
import msgpack
from typing_extensions import override

from pymax.exceptions import SocketNotConnectedError, SocketSendError
from pymax.filters import Filter, Message
from pymax.interfaces import ClientProtocol
from pymax.payloads import BaseWebSocketMessage, SyncPayload
from pymax.static import MessageStatus, Opcode
from pymax.types import Channel, Chat, Dialog, Me


class SocketMixin(ClientProtocol):
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
                uncompressed_size = int.from_bytes(payload_bytes[0:4], "big")
                compressed_data = payload_bytes
                try:
                    payload_bytes = lz4.block.decompress(
                        compressed_data,
                        uncompressed_size=99999,
                    )
                except lz4.block.LZ4BlockError:
                    return None
            payload = msgpack.unpackb(payload_bytes, raw=False, strict_map_key=False)

        return {
            "ver": ver,
            "cmd": cmd,
            "seq": seq,
            "opcode": opcode,
            "payload": payload,
        }

    def _pack_packet(
        self, ver: int, cmd: int, seq: int, opcode: int, payload: dict[str, Any]
    ) -> bytes:
        ver_b = ver.to_bytes(1, "big")
        cmd_b = cmd.to_bytes(2, "big")
        seq_b = seq.to_bytes(1, "big")
        opcode_b = opcode.to_bytes(2, "big")
        payload_bytes = msgpack.packb(payload)
        payload_len = len(payload_bytes) & 0xFFFFFF
        self.logger.debug("Packing message: payload size=%d bytes", len(payload_bytes))
        payload_len_b = payload_len.to_bytes(4, "big")
        return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes

    async def _connect(self, user_agent: dict[str, Any]) -> dict[str, Any]:
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
            self.logger.info("Connecting to socket %s:%s", self.host, self.port)
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
            self._outgoing = asyncio.Queue()
            self._pending = {}
            self._recv_task = asyncio.create_task(self._recv_loop())
            self._outgoing_task = asyncio.create_task(self._outgoing_loop())
            self.logger.info("Socket connected, starting handshake")
            return await self._handshake(user_agent)
        except Exception as e:
            self.logger.error("Failed to connect: %s", e, exc_info=True)
            raise ConnectionError(f"Failed to connect: {e}")

    async def _handshake(self, user_agent: dict[str, Any]) -> dict[str, Any]:
        try:
            self.logger.debug(
                "Sending handshake with user_agent keys=%s", list(user_agent.keys())
            )
            resp = await self._send_and_wait(
                opcode=Opcode.SESSION_INIT,
                payload={"deviceId": str(self._device_id), "userAgent": user_agent},
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

        loop = asyncio.get_running_loop()

        def _recv_exactly(n: int) -> bytes:
            """Синхронная функция: читает ровно n байт из сокета или возвращает b'' если закрыт."""
            buf = bytearray()
            sock = self._socket
            while len(buf) < n:
                chunk = sock.recv(n - len(buf))
                if not chunk:
                    return bytes(buf)
                buf.extend(chunk)
            return bytes(buf)

        try:
            while True:
                try:
                    header = await loop.run_in_executor(None, lambda: _recv_exactly(10))
                    if not header or len(header) < 10:
                        self.logger.info("Socket connection closed; exiting recv loop")
                        self.is_connected = False
                        try:
                            self._socket.close()
                        except Exception:
                            pass
                        break

                    packed_len = int.from_bytes(header[6:10], "big", signed=False)
                    payload_length = packed_len & 0xFFFFFF
                    remaining = payload_length
                    payload = bytearray()

                    while remaining > 0:
                        chunk = await loop.run_in_executor(
                            None, lambda r=remaining: _recv_exactly(min(r, 8192))
                        )
                        if not chunk:
                            self.logger.error("Connection closed while reading payload")
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
                        self.logger.warning("Failed to unpack packet, skipping")
                        continue

                    payload_objs = data.get("payload")
                    datas = (
                        [{**data, "payload": obj} for obj in payload_objs]
                        if isinstance(payload_objs, list)
                        else [data]
                    )

                    for data_item in datas:
                        seq = data_item.get("seq")
                        fut = self._pending.get(seq) if isinstance(seq, int) else None
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
                                for handler, filter in self._on_message_handlers:
                                    payload = data_item.get("payload", {})
                                    msg_dict = (
                                        payload if isinstance(payload, dict) else None
                                    )
                                    msg = (
                                        Message.from_dict(msg_dict)
                                        if msg_dict
                                        else None
                                    )
                                    if msg:
                                        if msg.status:
                                            if msg.status == MessageStatus.EDITED:
                                                for (
                                                    edit_handler,
                                                    edit_filter,
                                                ) in self._on_message_edit_handlers:
                                                    await self._process_message_handler(
                                                        handler=edit_handler,
                                                        msg_filter=edit_filter,
                                                        message=msg,
                                                    )
                                            elif msg.status == MessageStatus.REMOVED:
                                                for (
                                                    remove_handler,
                                                    remove_filter,
                                                ) in self._on_message_delete_handlers:
                                                    await self._process_message_handler(
                                                        handler=remove_handler,
                                                        msg_filter=remove_filter,
                                                        message=msg,
                                                    )
                                        await self._process_message_handler(
                                            handler=handler,
                                            msg_filter=filter,
                                            message=msg,
                                        )
                            except Exception:
                                self.logger.exception("Error in on_message_handler")
                except asyncio.CancelledError:
                    self.logger.debug("Recv loop cancelled")
                    break
                except Exception:
                    self.logger.exception("Error in recv_loop; backing off briefly")
                    await asyncio.sleep(0.5)
        finally:
            self.logger.warning("<<< Recv loop exited (socket)")

    def _log_task_exception(self, task: asyncio.Task[Any]) -> None:
        try:
            exc = task.exception()
            if exc:
                self.logger.exception("Background task exception: %s", exc)
        except Exception:
            self.logger.exception("Error getting task exception")

    async def _process_message_handler(
        self,
        handler: Callable[[Message], Any],
        msg_filter: Filter | None,
        message: Message,
    ) -> None:
        if msg_filter and not msg_filter.match(message):
            return

        result = handler(message)
        if asyncio.iscoroutine(result):
            task = asyncio.create_task(result)
            self._background_tasks.add(task)
            task.add_done_callback(
                lambda t: self._background_tasks.discard(t)
                or self._log_task_exception(t)
            )

    async def _send_interactive_ping(self) -> None:
        while self.is_connected:
            try:
                await self._send_and_wait(
                    opcode=Opcode.PING,
                    payload={"interactive": True},
                    cmd=0,
                )
                self.logger.debug("Interactive ping sent successfully (socket)")
            except Exception:
                self.logger.warning("Interactive ping failed (socket)", exc_info=True)
            await asyncio.sleep(30)

    def _make_message(
        self, opcode: int, payload: dict[str, Any], cmd: int = 0
    ) -> dict[str, Any]:
        self._seq += 1
        msg = BaseWebSocketMessage(
            ver=11,
            cmd=cmd,
            seq=self._seq,
            opcode=opcode,
            payload=payload,
        ).model_dump(by_alias=True)
        self.logger.debug(
            "make_message opcode=%s cmd=%s seq=%s", opcode, cmd, self._seq
        )
        return msg

    @override
    async def _send_and_wait(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = 10.0,
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
                "Sending frame opcode=%s cmd=%s seq=%s", opcode, cmd, msg["seq"]
            )
            packet = self._pack_packet(
                msg["ver"], msg["cmd"], msg["seq"], msg["opcode"], msg["payload"]
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

    async def _outgoing_loop(self) -> None:
        while self.is_connected:
            try:
                if self._outgoing is None:
                    await asyncio.sleep(0.1)
                    continue
                
                if self._circuit_breaker:
                    if time.time() - self._last_error_time > 60:
                        self._circuit_breaker = False
                        self._error_count = 0
                        self.logger.info("Circuit breaker reset (socket)")
                    else:
                        await asyncio.sleep(5)
                        continue
                
                message = await self._outgoing.get() # TODO: persistent msg q mb?
                if not message:
                    continue
                
                retry_count = message.get("retry_count", 0)
                max_retries = message.get("max_retries", 3)
                
                try:
                    await self._send_and_wait(
                        opcode=message["opcode"],
                        payload=message["payload"],
                        cmd=message.get("cmd", 0),
                        timeout=message.get("timeout", 10.0)
                    )
                    self.logger.debug("Message sent successfully from queue (socket)")
                    self._error_count = max(0, self._error_count - 1)
                except Exception as e:
                    self._error_count += 1
                    self._last_error_time = time.time()
                    
                    if self._error_count > 10: # TODO: export to constant
                        self._circuit_breaker = True
                        self.logger.warning("Circuit breaker activated due to %d consecutive errors (socket)", self._error_count)
                        await self._outgoing.put(message)
                        continue
                    
                    retry_delay = self._get_retry_delay(e, retry_count)
                    self.logger.warning("Failed to send message from queue (socket): %s (delay: %ds)", e, retry_delay)
                    
                    if retry_count < max_retries:
                        message["retry_count"] = retry_count + 1
                        await asyncio.sleep(retry_delay)
                        await self._outgoing.put(message)
                    else:
                        self.logger.error("Message failed after %d retries, dropping (socket)", max_retries)
                        
            except Exception:
                self.logger.exception("Error in outgoing loop (socket)")
                await asyncio.sleep(1)

    def _get_retry_delay(self, error: Exception, retry_count: int) -> float: # TODO: tune delays later
        if isinstance(error, (ConnectionError, OSError, ssl.SSLError)):
            return 1.0
        elif isinstance(error, TimeoutError):
            return 5.0
        elif isinstance(error, SocketNotConnectedError):
            return 2.0
        else:
            return 2 ** retry_count

    async def _queue_message(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        if self._outgoing is None:
            self.logger.warning("Outgoing queue not initialized (socket)")
            return
            
        message = {
            "opcode": opcode,
            "payload": payload,
            "cmd": cmd,
            "timeout": timeout,
            "retry_count": 0,
            "max_retries": max_retries,
        }
        
        await self._outgoing.put(message)
        self.logger.debug("Message queued for sending (socket)")

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
            data = await self._send_and_wait(opcode=Opcode.LOGIN, payload=payload)
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

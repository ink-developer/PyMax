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

from pymax.exceptions import Error, SocketNotConnectedError, SocketSendError
from pymax.filters import BaseFilter
from pymax.interfaces import ClientProtocol
from pymax.payloads import BaseWebSocketMessage, SyncPayload, UserAgentPayload
from pymax.static.constant import (
    DEFAULT_PING_INTERVAL,
    DEFAULT_TIMEOUT,
    RECV_LOOP_BACKOFF_DELAY,
)
from pymax.static.enum import ChatType, MessageStatus, Opcode
from pymax.types import (
    Channel,
    Chat,
    Dialog,
    Me,
    Message,
    ReactionCounter,
    ReactionInfo,
    User,
)


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
            payload = msgpack.unpackb(payload_bytes, raw=False, strict_map_key=False)

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
        self.logger.debug("Packing message: payload size=%d bytes", len(payload_bytes))
        payload_len_b = payload_len.to_bytes(4, "big")
        return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes

    async def connect(self, user_agent: UserAgentPayload | None = None) -> dict[str, Any]:
        """
        Устанавливает соединение с сервером и выполняет handshake.

        :param user_agent: Пользовательский агент для handshake. Если None, используется значение по умолчанию.
        :type user_agent: UserAgentPayload | None
        :return: Результат handshake.
        :rtype: dict[str, Any] | None
        """
        if user_agent is None:
            user_agent = UserAgentPayload()
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
        self._socket = self._ssl_context.wrap_socket(raw_sock, server_hostname=self.host)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.is_connected = True
        self._incoming = asyncio.Queue()
        self._outgoing = asyncio.Queue()
        self._pending = {}
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._outgoing_task = asyncio.create_task(self._outgoing_loop())
        self.logger.info("Socket connected, starting handshake")
        return await self._handshake(user_agent)

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

    def _recv_exactly(self, sock: socket.socket, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return bytes(buf)
            buf.extend(chunk)
        return bytes(buf)

    async def _parse_header(
        self, loop: asyncio.AbstractEventLoop, sock: socket.socket
    ) -> bytes | None:
        header = await loop.run_in_executor(None, lambda: self._recv_exactly(sock=sock, n=10))
        if not header or len(header) < 10:
            self.logger.info("Socket connection closed; exiting recv loop")
            self.is_connected = False
            try:
                sock.close()
            except Exception:
                return None

        return header

    async def _recv_data(
        self, loop: asyncio.AbstractEventLoop, header: bytes, sock: socket.socket
    ) -> list[dict[str, Any]] | None:
        packed_len = int.from_bytes(header[6:10], "big", signed=False)
        payload_length = packed_len & 0xFFFFFF
        remaining = payload_length
        payload = bytearray()

        while remaining > 0:
            min_read = min(remaining, 8192)
            chunk = await loop.run_in_executor(None, lambda: self._recv_exactly(sock, min_read))
            if not chunk:
                self.logger.error("Connection closed while reading payload")
                break
            payload.extend(chunk)
            remaining -= len(chunk)

        if remaining > 0:
            self.logger.error("Incomplete payload received; skipping packet")
            return None

        raw = header + payload
        if len(raw) < 10 + payload_length:
            self.logger.error(
                "Incomplete packet: expected %d bytes, got %d",
                10 + payload_length,
                len(raw),
            )
            await asyncio.sleep(RECV_LOOP_BACKOFF_DELAY)
            return None

        data = self._unpack_packet(raw)
        if not data:
            self.logger.warning("Failed to unpack packet, skipping")
            return None

        payload_objs = data.get("payload")
        return (
            [{**data, "payload": obj} for obj in payload_objs]
            if isinstance(payload_objs, list)
            else [data]
        )

    def _handle_pending(self, seq: int | None, data: dict) -> bool:
        if isinstance(seq, int):
            fut = self._pending.get(seq)
            if fut and not fut.done():
                fut.set_result(data)
                self.logger.debug("Matched response for pending seq=%s", seq)
                return True
        return False

    async def _handle_incoming_queue(self, data: dict[str, Any]) -> None:
        if self._incoming:
            try:
                self._incoming.put_nowait(data)
            except asyncio.QueueFull:
                self.logger.warning(
                    "Incoming queue full; dropping message seq=%s", data.get("seq")
                )

    async def _handle_file_upload(self, data: dict[str, Any]) -> None:
        if data.get("opcode") != Opcode.NOTIF_ATTACH:
            return
        payload = data.get("payload", {})
        for key in ("fileId", "videoId"):
            id_ = payload.get(key)
            if id_ is not None:
                fut = self._file_upload_waiters.pop(id_, None)
                if fut and not fut.done():
                    fut.set_result(data)
                    self.logger.debug("Fulfilled file upload waiter for %s=%s", key, id_)

    async def _handle_message_notifications(self, data: dict) -> None:
        if data.get("opcode") != Opcode.NOTIF_MESSAGE.value:
            return
        payload = data.get("payload", {})
        msg = Message.from_dict(payload)
        if not msg:
            return
        handlers_map = {
            MessageStatus.EDITED: self._on_message_edit_handlers,
            MessageStatus.REMOVED: self._on_message_delete_handlers,
        }
        if msg.status and msg.status in handlers_map:
            for handler, filter in handlers_map[msg.status]:
                await self._process_message_handler(handler, filter, msg)
        for handler, filter in self._on_message_handlers:
            await self._process_message_handler(handler, filter, msg)

    async def _handle_reactions(self, data: dict):
        if data.get("opcode") != Opcode.NOTIF_MSG_REACTIONS_CHANGED:
            return

        payload = data.get("payload", {})
        chat_id = payload.get("chatId")
        message_id = payload.get("messageId")

        if not (chat_id and message_id):
            return

        total_count = payload.get("totalCount")
        your_reaction = payload.get("yourReaction")
        counters = [ReactionCounter.from_dict(c) for c in payload.get("counters", [])]

        reaction_info = ReactionInfo(
            total_count=total_count,
            your_reaction=your_reaction,
            counters=counters,
        )

        for handler in self._on_reaction_change_handlers:
            try:
                result = handler(message_id, chat_id, reaction_info)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.exception("Error in on_reaction_change_handler: %s", e)

    async def _handle_chat_updates(self, data: dict) -> None:
        if data.get("opcode") != Opcode.NOTIF_CHAT:
            return

        payload = data.get("payload", {})
        chat_data = payload.get("chat", {})
        chat = Chat.from_dict(chat_data)
        if not chat:
            return

        for handler in self._on_chat_update_handlers:
            try:
                result = handler(chat)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.exception("Error in on_chat_update_handler: %s", e)

    async def _handle_raw_receive(self, data: dict[str, Any]) -> None:
        for handler in self._on_raw_receive_handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.exception("Error in on_raw_receive_handler: %s", e)

    async def _dispatch_incoming(self, data: dict[str, Any]) -> None:
        await self._handle_raw_receive(data)
        await self._handle_file_upload(data)
        await self._handle_message_notifications(data)
        await self._handle_reactions(data)
        await self._handle_chat_updates(data)

    async def _recv_loop(self) -> None:
        if self._socket is None:
            self.logger.warning("Recv loop started without socket instance")
            return

        sock = self._socket
        loop = asyncio.get_running_loop()

        while True:
            try:
                header = await self._parse_header(loop, sock)

                if not header:
                    break

                datas = await self._recv_data(loop, header, sock)

                if not datas:
                    continue

                for data_item in datas:
                    seq = data_item.get("seq")

                    if self._handle_pending(seq, data_item):
                        continue

                    if self._incoming is not None:
                        await self._handle_incoming_queue(data_item)

                    await self._dispatch_incoming(data_item)

            except asyncio.CancelledError:
                self.logger.debug("Recv loop cancelled")
                raise
            except Exception:
                self.logger.exception("Error in recv_loop; backing off briefly")
                await asyncio.sleep(RECV_LOOP_BACKOFF_DELAY)

    def _log_task_exception(self, fut: asyncio.Future[Any]) -> None:
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception("Error getting task exception: %s", e)
            pass

    async def _process_message_handler(
        self,
        handler: Callable[[Message], Any],
        filter: BaseFilter[Message] | None,
        message: Message,
    ) -> None:
        if filter is not None and not filter(message):
            return

        result = handler(message)
        if asyncio.iscoroutine(result):
            task = asyncio.create_task(result)
            task.add_done_callback(self._log_task_exception)
            self._background_tasks.add(task)

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
            await asyncio.sleep(DEFAULT_PING_INTERVAL)

    def _make_message(
        self, opcode: Opcode, payload: dict[str, Any], cmd: int = 0
    ) -> dict[str, Any]:
        self._seq += 1
        msg = BaseWebSocketMessage(
            ver=10,
            cmd=cmd,
            seq=self._seq,
            opcode=opcode.value,
            payload=payload,
        ).model_dump(by_alias=True)
        self.logger.debug("make_message opcode=%s cmd=%s seq=%s", opcode, cmd, self._seq)
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
                await self.connect(self.user_agent)
            except Exception as exc:
                self.logger.exception("Reconnect failed")
                raise exc from conn_err
            raise SocketNotConnectedError from conn_err
        except Exception as exc:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
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

                message = await self._outgoing.get()  # TODO: persistent msg q mb?

                if not message:
                    continue

                retry_count = message.get("retry_count", 0)
                max_retries = message.get("max_retries", 3)

                try:
                    await self._send_and_wait(
                        opcode=message["opcode"],
                        payload=message["payload"],
                        cmd=message.get("cmd", 0),
                        timeout=message.get("timeout", 10.0),
                    )
                    self.logger.debug("Message sent successfully from queue (socket)")
                    self._error_count = max(0, self._error_count - 1)
                except Exception as e:
                    self._error_count += 1
                    self._last_error_time = time.time()

                    if self._error_count > 10:  # TODO: export to constant
                        self._circuit_breaker = True
                        self.logger.warning(
                            "Circuit breaker activated due to %d consecutive errors (socket)",
                            self._error_count,
                        )
                        await self._outgoing.put(message)
                        continue

                    retry_delay = self._get_retry_delay(e, retry_count)
                    self.logger.warning(
                        "Failed to send message from queue (socket): %s (delay: %ds)",
                        e,
                        retry_delay,
                    )

                    if retry_count < max_retries:
                        message["retry_count"] = retry_count + 1
                        await asyncio.sleep(retry_delay)
                        await self._outgoing.put(message)
                    else:
                        self.logger.error(
                            "Message failed after %d retries, dropping (socket)",
                            max_retries,
                        )

            except Exception:
                self.logger.exception("Error in outgoing loop (socket)")
                await asyncio.sleep(1)

    def _get_retry_delay(
        self, error: Exception, retry_count: int
    ) -> float:  # TODO: tune delays later
        if isinstance(error, (ConnectionError, OSError, ssl.SSLError)):
            return 1.0
        elif isinstance(error, TimeoutError):
            return 5.0
        elif isinstance(error, SocketNotConnectedError):
            return 2.0
        else:
            return 2**retry_count

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
            localized_message = raw_payload.get("localizedMessage")
            title = raw_payload.get("title")
            message = raw_payload.get("message")
            raise Error(
                error=error,
                message=message,
                title=title,
                localized_message=localized_message,
            )
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

        for raw_user in raw_payload.get("contacts", []):
            try:
                user = User.from_dict(raw_user)
                if user:
                    self.contacts.append(user)
            except Exception:
                self.logger.exception("Error parsing contact entry (socket)")

        if raw_payload.get("profile", {}).get("contact"):
            self.me = Me.from_dict(raw_payload.get("profile", {}).get("contact", {}))
        self.logger.info(
            "Sync completed: dialogs=%d chats=%d channels=%d",
            len(self.dialogs),
            len(self.chats),
            len(self.channels),
        )

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

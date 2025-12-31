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
from pymax.interfaces import BaseTransport
from pymax.payloads import BaseWebSocketMessage, SyncPayload, UserAgentPayload
from pymax.protocols import ClientProtocol
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


class SocketMixin(BaseTransport):
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
        seq_b = (seq % 256).to_bytes(1, "big")
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

                    if self._handle_pending(seq % 256 if seq is not None else None, data_item):
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
        seq_key = msg["seq"] % 256

        old_fut = self._pending.get(seq_key)
        if old_fut and not old_fut.done():
            old_fut.cancel()

        self._pending[seq_key] = fut
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
        except asyncio.TimeoutError:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise SocketSendError from None
        except Exception as exc:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise SocketSendError from exc

        finally:
            self._pending.pop(msg["seq"] % 256, None)

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

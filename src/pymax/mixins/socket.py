import asyncio
import contextlib
import errno
import json
import socket
import ssl
import sys
from typing import Any
from urllib.parse import urlparse

import lz4.block
import lz4.frame
import msgpack
from typing_extensions import override

from pymax.exceptions import Error, SocketNotConnectedError, SocketSendError
from pymax.filters import BaseFilter
from pymax.interfaces import BaseTransport
from pymax.payloads import UserAgentPayload
from pymax.static.constant import (
    DEFAULT_TIMEOUT,
    RECV_LOOP_BACKOFF_DELAY,
)
from pymax.static.enum import Opcode
from pymax.types import (
    Chat,
)


class SocketMixin(BaseTransport):
    MAX_UNCOMPRESSED_SIZE = 10 * 1024 * 1024
    MAX_PAYLOAD_LENGTH = 50 * 1024 * 1024

    async def _close_socket(self):
        async with self._sock_lock:
            sock = self._socket
            self._socket = None
        if sock:
            try:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                sock.close()
            except Exception as e:
                self.logger.debug("Error closing socket: %s", e, exc_info=True)

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
        compress: bool = False,
    ) -> bytes:
        ver_b = ver.to_bytes(1, "big")
        cmd_b = cmd.to_bytes(1, "big")
        seq_b = seq.to_bytes(2, "big")
        opcode_b = opcode.to_bytes(2, "big")

        payload_bytes = msgpack.packb(payload) or b""

        comp_flag = 1 if compress else 0
        payload_len = len(payload_bytes) & 0xFFFFFF
        packed_len = (comp_flag << 24) | payload_len
        payload_len_b = packed_len.to_bytes(4, "big")

        return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes

    def _create_socket_with_proxy(self, proxy: str) -> socket.socket:
        parsed = urlparse(proxy)

        if parsed.scheme not in ("socks5", ""):
            raise ValueError("Only SOCKS5 proxy is supported")

        if not parsed.hostname or not parsed.port:
            raise ValueError(f"Invalid proxy URL: {proxy}")

        proxy_host = parsed.hostname
        proxy_port = parsed.port

        username = parsed.username
        password = parsed.password

        self.logger.info(
            "Connecting to socket %s:%s via SOCKS5 proxy %s:%s (auth=%s)",
            self.host,
            self.port,
            proxy_host,
            proxy_port,
            "yes" if username else "no",
        )

        sock = socket.create_connection((proxy_host, proxy_port))

        if username:
            sock.sendall(b"\x05\x02\x00\x02")
        else:
            sock.sendall(b"\x05\x01\x00")

        response = self._recv_exactly_plain(sock, 2)
        if response[0] != 0x05:
            sock.close()
            raise ConnectionError("Invalid SOCKS5 proxy response")

        method = response[1]
        if method == 0xFF:
            sock.close()
            raise ConnectionError("SOCKS5 proxy: no acceptable auth methods")

        if method == 0x02:
            if not username or not password:
                sock.close()
                raise ConnectionError("SOCKS5 proxy requires authentication")

            u = username.encode("utf-8")
            p = password.encode("utf-8")

            if len(u) > 255 or len(p) > 255:
                sock.close()
                raise ValueError("SOCKS5 username/password too long")

            auth_req = b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p
            sock.sendall(auth_req)

            auth_resp = self._recv_exactly_plain(sock, 2)
            if auth_resp != b"\x01\x00":
                sock.close()
                raise ConnectionError("SOCKS5 authentication failed")

        host_bytes = self.host.encode("utf-8")
        connect_req = (
            b"\x05\x01\x00\x03"
            + bytes([len(host_bytes)])
            + host_bytes
            + self.port.to_bytes(2, "big")
        )
        sock.sendall(connect_req)

        resp = self._recv_exactly_plain(sock, 4)
        if resp[0] != 0x05 or resp[1] != 0x00:
            sock.close()
            raise ConnectionError(f"SOCKS5 connect failed, code={resp[1]}")

        atyp = resp[3]
        if atyp == 0x01:
            self._recv_exactly_plain(sock, 4 + 2)
        elif atyp == 0x03:
            domain_len = self._recv_exactly_plain(sock, 1)[0]
            self._recv_exactly_plain(sock, domain_len + 2)
        elif atyp == 0x04:
            self._recv_exactly_plain(sock, 16 + 2)
        else:
            sock.close()
            raise ConnectionError(f"Unknown ATYP: {atyp}")

        return sock

    def _recv_exactly_plain(self, sock: socket.socket, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed during SOCKS handshake")
            buf.extend(chunk)
        return bytes(buf)

    def _perform_ssl_handshake(self, raw_sock: socket.socket) -> socket.socket:
        """
        Выполняет SSL handshake с сервером.

        :param raw_sock: Обычный сокет
        :return: SSL сокет
        """
        try:
            raw_sock.settimeout(10.0)
            wrapped = self._ssl_context.wrap_socket(
                raw_sock,
                server_hostname=self.host,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True,
            )
            wrapped.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            return wrapped
        except ssl.SSLError as e:
            self.logger.error("SSL handshake failed: %s", e)
            raw_sock.close()
            raise

    async def connect(self, user_agent: UserAgentPayload | None = None) -> dict[str, Any]:
        """
        Устанавливает соединение с сервером и выполняет handshake.

        :param user_agent: Пользовательский агент для handshake. Если None, используется значение по умолчанию.
        :type user_agent: UserAgentPayload | None
        :return: Результат handshake.
        :rtype: dict[str, Any] | None
        """
        if user_agent is None or self.headers is None:
            self.logger.debug("No user agent provided, using default")
            user_agent = self.headers or UserAgentPayload()

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

        if self.proxy:
            raw_sock = await loop.run_in_executor(
                None, lambda: self._create_socket_with_proxy(self.proxy)
            )
        else:
            raw_sock = await loop.run_in_executor(
                None, lambda: socket.create_connection((self.host, self.port), timeout=10.0)
            )

        try:
            self._socket = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._perform_ssl_handshake(raw_sock)),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            raw_sock.close()
            self.logger.error("SSL handshake timeout")
            raise

        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(SocketNotConnectedError())
        self._pending.clear()

        self.is_connected = True
        self._incoming = asyncio.Queue()
        self._outgoing = asyncio.Queue()
        self._pending = {}
        if self._recv_task and not self._recv_task.done():
            try:
                self._recv_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._recv_task
            except Exception:
                self.logger.debug("Old recv_task cancellation raised", exc_info=True)

        self.logger.debug("Old recv_task cancellation raised", exc_info=True)
        self._recv_task = self._create_safe_task(self._recv_loop(), name="recv_loop socket task")
        self._recv_task.add_done_callback(
            lambda t: self.logger.debug(
                "recv_task done: cancelled=%s, exc=%r", t.cancelled(), t.exception()
            )
        )

        self.logger.debug("is_connected=%s before starting ping", self.is_connected)
        ping_task = self._create_safe_task(
            self._send_interactive_ping(),
            name="interactive_ping",
        )

        self._outgoing_task = self._create_safe_task(
            self._outgoing_loop(), name="outgoing_loop socket task"
        )
        self.logger.info("Socket connected, starting handshake")

        data = await self._handshake(user_agent)
        self.logger.debug("Handshake location: %s", data.get("payload", {}).get("location"))
        return data

    def _ssl_read_exactly(self, sock: socket.socket, n: int) -> bytes:
        while len(self._read_buffer) < n:
            chunk = sock.recv(8192)
            if not chunk:
                raise ConnectionResetError("SSL socket closed")
            self._read_buffer.extend(chunk)

        data = self._read_buffer[:n]
        del self._read_buffer[:n]
        return bytes(data)

    async def _parse_header(self, loop, sock):
        async with self._sock_lock:
            header = await loop.run_in_executor(None, lambda: self._ssl_read_exactly(sock, 10))
        return header

    async def _recv_data(self, loop, header, sock):
        packed_len = int.from_bytes(header[6:10], "big")
        payload_length = packed_len & 0xFFFFFF

        if payload_length == 0:
            raw = header
        else:
            async with self._sock_lock:
                payload = await loop.run_in_executor(
                    None, lambda: self._ssl_read_exactly(sock, payload_length)
                )
            raw = header + payload

        data = self._unpack_packet(raw)
        if not data:
            self.logger.warning(
                "Failed to unpack packet (possibly corrupted or unsupported compression)"
            )
            return None

        payload_objs = data.get("payload")
        return (
            [{**data, "payload": payload_objs}]
            if not isinstance(payload_objs, list)
            else [{**data, "payload": obj} for obj in payload_objs]
        )

    async def _recv_loop(self) -> None:
        if self._socket is None:
            self.logger.warning("Recv loop started without socket instance")
            return

        loop = asyncio.get_running_loop()
        consecutive_errors = 0
        max_consecutive_errors = 3

        while True:
            try:
                sock = self._socket
                if sock is None:
                    self.logger.warning("Socket became None, exiting recv loop")
                    break

                header = await self._parse_header(loop, sock)

                self.logger.debug("Received header: %s", header)

                if not header:
                    self.logger.error("No header received, exiting recv loop")
                    break

                datas = await self._recv_data(loop, header, sock)

                if not datas:
                    self.logger.warning("No data received, continuing recv loop")
                    await asyncio.sleep(RECV_LOOP_BACKOFF_DELAY)
                    continue

                consecutive_errors = 0

                for data_item in datas:
                    seq = data_item.get("seq")

                    if self._handle_pending(seq, data_item):
                        continue

                    if self._incoming is not None:
                        await self._handle_incoming_queue(data_item)

                    await self._dispatch_incoming(data_item)

            except asyncio.CancelledError:
                self.logger.debug("Recv loop cancelled")
                break
            except (
                ssl.SSLError,
                ssl.SSLEOFError,
                ConnectionResetError,
                BrokenPipeError,
            ) as ssl_err:
                consecutive_errors += 1
                self.logger.exception(
                    "SSL/Connection error in recv_loop (error %d/%d): %s",
                    consecutive_errors,
                    max_consecutive_errors,
                    ssl_err,
                )
                self.is_connected = False

                for fut in list(self._pending.values()):
                    if not fut.done():
                        fut.set_exception(SocketNotConnectedError())

                self._pending.clear()

                await self._close_socket()

                if self.reconnect and consecutive_errors < max_consecutive_errors:
                    self.logger.info(
                        "Reconnect enabled — exiting recv_loop to allow outer loop to reconnect"
                    )
                    break
                else:
                    self.logger.warning(...)
                    break
            except socket.timeout:
                self.logger.debug("Socket timeout, continuing recv loop")
                continue
            except Exception as e:
                consecutive_errors += 1
                self.logger.exception("Error in recv_loop: %s", e)
                self.is_connected = False

                await self._close_socket()

                if self.reconnect and consecutive_errors < max_consecutive_errors:
                    self.logger.info(
                        "Reconnect enabled — exiting recv_loop to allow outer loop to reconnect"
                    )
                    break
                else:
                    self.logger.warning("Max consecutive errors reached, exiting recv_loop")
                    break

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

        msg = self._make_message(opcode, payload, cmd)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        seq_key = msg["seq"]

        old_fut = self._pending.get(seq_key)
        if old_fut and not old_fut.done():
            old_fut.cancel()

        self._pending[seq_key] = fut
        try:
            self.logger.debug(
                "Sending frame msg=%s",
                json.dumps(msg, ensure_ascii=False, indent=4),
            )
            packet = self._pack_packet(
                msg["ver"],
                msg["cmd"],
                msg["seq"],
                msg["opcode"],
                msg["payload"],
            )
            async with self._sock_lock:
                if not self.is_connected or self._socket is None:
                    raise SocketNotConnectedError

                sock = self._socket
                try:
                    await loop.run_in_executor(None, lambda: sock.sendall(packet))
                except OSError as e:
                    if e.errno in (errno.EBADF, errno.EPIPE, errno.ENOTCONN):
                        self.logger.debug("Socket closed during send (errno=%s)", e.errno)
                        self.is_connected = False
                        await self._close_socket()
                        raise SocketNotConnectedError from e
                    raise

            data = await asyncio.wait_for(fut, timeout=timeout)
            self.logger.debug(
                "Received frame for seq=%s opcode=%s",
                data.get("seq"),
                data.get("opcode"),
            )
            return data

        except (ssl.SSLEOFError, ssl.SSLError, ConnectionError, BrokenPipeError) as conn_err:
            self.logger.warning("Connection lost while sending: %s", conn_err)
            self.is_connected = False
            for pending_fut in list(self._pending.values()):
                if not pending_fut.done():
                    pending_fut.set_exception(SocketNotConnectedError())
            self._pending.clear()

            if not fut.done():
                fut.set_exception(SocketSendError("connection lost during send"))

            await self._close_socket()
            raise SocketSendError("Connection lost during send") from conn_err

        except asyncio.TimeoutError:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise SocketSendError from None
        except Exception as exc:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise SocketSendError from exc

        finally:
            self._pending.pop(seq_key, None)

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

    async def _send_only(self, opcode: Opcode, payload: dict[str, Any], cmd: int = 0) -> None:
        async def send_task():
            try:
                async with self._sock_lock:
                    if not self.is_connected or self._socket is None:
                        self.logger.debug("Socket not connected in _send_only, skipping")
                        return
                    msg = self._make_message(opcode, payload, cmd)
                    packet = self._pack_packet(
                        msg["ver"],
                        msg["cmd"],
                        msg["seq"],
                        msg["opcode"],
                        msg["payload"],
                    )
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: self._socket.sendall(packet))
            except (ssl.SSLEOFError, ssl.SSLError, ConnectionError, BrokenPipeError) as e:
                self.logger.debug("Connection error in _send_only (fire-and-forget): %s", e)
                self.is_connected = False
                await self._close_socket()
            except Exception as e:
                self.logger.warning("Unexpected error in _send_only: %s", e, exc_info=True)

        task = self._create_safe_task(send_task(), name="_send_only_task")
        task.add_done_callback(lambda t: self._log_task_exception(t))

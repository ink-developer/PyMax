import asyncio
import json
from typing import Any

import websockets
from typing_extensions import override

from pymax.exceptions import WebSocketNotConnectedError
from pymax.interfaces import BaseTransport
from pymax.payloads import UserAgentPayload
from pymax.static.constant import (
    DEFAULT_TIMEOUT,
    RECV_LOOP_BACKOFF_DELAY,
    WEBSOCKET_ORIGIN,
)
from pymax.static.enum import Opcode
from pymax.types import (
    Chat,
)


class WebSocketMixin(BaseTransport):
    @property
    def ws(self) -> websockets.ClientConnection:
        if self._ws is None or not self.is_connected:
            self.logger.critical("WebSocket not connected when access attempted")
            raise WebSocketNotConnectedError
        return self._ws

    async def connect(self, user_agent: UserAgentPayload | None = None) -> dict[str, Any] | None:
        """
        Устанавливает соединение WebSocket с сервером и выполняет handshake.

        :param user_agent: Пользовательский агент для handshake. Если None, используется значение по умолчанию.
        :type user_agent: UserAgentPayload | None
        :return: Результат handshake.
        :rtype: dict[str, Any] | None
        """
        if user_agent is None or self.headers is None:
            user_agent = UserAgentPayload() or self.headers

        self.logger.info("Connecting to WebSocket %s", self.uri)

        if self._ws is not None or self.is_connected:
            self.logger.warning("WebSocket already connected")
            return

        self._ws = await websockets.connect(
            self.uri,
            origin=WEBSOCKET_ORIGIN,
            user_agent_header=user_agent.header_user_agent,
            proxy=self.proxy,
        )

        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(WebSocketNotConnectedError())
        self._pending.clear()

        self.is_connected = True
        self._incoming = asyncio.Queue()
        self._outgoing = asyncio.Queue()
        self._pending = {}
        self._recv_task = self._create_safe_task(
            self._recv_loop(), name="recv_loop websocket task"
        )
        self._outgoing_task = self._create_safe_task(
            self._outgoing_loop(), name="outgoing_loop websocket task"
        )
        self.logger.debug("is_connected=%s before starting ping", self.is_connected)
        ping_task = self._create_safe_task(
            self._send_interactive_ping(),
            name="interactive_ping",
        )
        self.logger.info("WebSocket connected, starting handshake")
        return await self._handshake(user_agent)

    async def _recv_loop(self) -> None:
        if self._ws is None:
            self.logger.warning("Recv loop started without websocket instance")
            return

        self.logger.debug("Receive loop started")
        while True:
            try:
                raw = await self._ws.recv()
                data = self._parse_json(raw)

                if data is None:
                    continue

                seq = data.get("seq")
                if self._handle_pending(seq, data):
                    continue

                await self._handle_incoming_queue(data)
                await self._dispatch_incoming(data)

            except websockets.exceptions.ConnectionClosed as e:
                self.logger.info(
                    f"WebSocket connection closed with error: {e.code}, {e.reason}; exiting recv loop"
                )
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(WebSocketNotConnectedError)
                self._pending.clear()

                self.is_connected = False
                self._ws = None
                self._recv_task = None

                break
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
        ws = self.ws
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
            await ws.send(json.dumps(msg))
            data = await asyncio.wait_for(fut, timeout=timeout)
            self.logger.debug(
                "Received frame for seq=%s opcode=%s",
                data.get("seq"),
                data.get("opcode"),
            )
            return data
        except asyncio.TimeoutError:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise RuntimeError("Send and wait failed")
        except Exception:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise RuntimeError("Send and wait failed")
        finally:
            self._pending.pop(seq_key, None)

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

    async def _send_only(self, opcode: Opcode, payload: dict[str, Any], cmd: int = 0) -> None:
        msg = self._make_message(opcode, payload, cmd)
        packet = json.dumps(msg)

        asyncio.create_task(self.ws.send(packet))

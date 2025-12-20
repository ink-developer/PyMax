import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

import websockets
from typing_extensions import override

from pymax.exceptions import LoginError, WebSocketNotConnectedError
from pymax.filters import BaseFilter
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import BaseWebSocketMessage, SyncPayload, UserAgentPayload
from pymax.static.constant import (
    DEFAULT_PING_INTERVAL,
    DEFAULT_TIMEOUT,
    RECV_LOOP_BACKOFF_DELAY,
    WEBSOCKET_ORIGIN,
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
)


class WebSocketMixin(ClientProtocol):
    @property
    def ws(self) -> websockets.ClientConnection:
        if self._ws is None or not self.is_connected:
            self.logger.critical("WebSocket not connected when access attempted")
            raise WebSocketNotConnectedError
        return self._ws

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

        self.logger.debug("make_message opcode=%s cmd=%s seq=%s", opcode, cmd, self._seq)
        return msg

    async def _send_interactive_ping(self) -> None:
        while self.is_connected:
            try:
                await self._send_and_wait(
                    opcode=Opcode.PING,
                    payload={"interactive": True},
                    cmd=0,
                )
                self.logger.debug("Interactive ping sent successfully")
            except Exception:
                self.logger.warning("Interactive ping failed", exc_info=True)
            await asyncio.sleep(DEFAULT_PING_INTERVAL)

    async def connect(self, user_agent: UserAgentPayload | None = None) -> dict[str, Any] | None:
        """
        Устанавливает соединение WebSocket с сервером и выполняет handshake.

        :param user_agent: Пользовательский агент для handshake. Если None, используется значение по умолчанию.
        :type user_agent: UserAgentPayload | None
        :return: Результат handshake.
        :rtype: dict[str, Any] | None
        """
        if user_agent is None:
            user_agent = UserAgentPayload()

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
        self.is_connected = True
        self._incoming = asyncio.Queue()
        self._outgoing = asyncio.Queue()
        self._pending = {}
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._outgoing_task = asyncio.create_task(self._outgoing_loop())
        self.logger.info("WebSocket connected, starting handshake")
        return await self._handshake(user_agent)

    async def _handshake(self, user_agent: UserAgentPayload) -> dict[str, Any]:
        self.logger.debug(
            "Sending handshake with user_agent keys=%s",
            user_agent.model_dump(by_alias=True).keys(),
        )

        user_agent_json = user_agent.model_dump(by_alias=True)
        resp = await self._send_and_wait(
            opcode=Opcode.SESSION_INIT,
            payload={"deviceId": str(self._device_id), "userAgent": user_agent_json},
        )

        if resp.get("payload", {}).get("error"):
            MixinsUtils.handle_error(resp)

        self.logger.info("Handshake completed")
        return resp

    async def _process_message_handler(
        self,
        handler: Callable[[Message], Any],
        filter: BaseFilter[Message] | None,
        message: Message,
    ):
        result = None
        if filter:
            if filter(message):
                result = handler(message)
            else:
                return
        else:
            result = handler(message)
        if asyncio.iscoroutine(result):
            self._create_safe_task(result, name=f"handler-{handler.__name__}")

    def _parse_json(self, raw: Any) -> dict[str, Any] | None:
        try:
            return json.loads(raw)
        except Exception:
            self.logger.warning("JSON parse error", exc_info=True)
            return None

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
        if msg.status is None:
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

    def _log_task_exception(self, fut: asyncio.Future[Any]) -> None:
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception("Error retrieving task exception: %s", e)

    async def _queue_message(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        if self._outgoing is None:
            self.logger.warning("Outgoing queue not initialized")
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
        self.logger.debug("Message queued for sending")

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
        self._pending[msg["seq"]] = fut

        try:
            self.logger.debug(
                "Sending frame opcode=%s cmd=%s seq=%s",
                opcode,
                cmd,
                msg["seq"],
            )
            await ws.send(json.dumps(msg))
            data = await asyncio.wait_for(fut, timeout=timeout)
            self.logger.debug(
                "Received frame for seq=%s opcode=%s",
                data.get("seq"),
                data.get("opcode"),
            )
            return data
        except Exception:
            self.logger.exception("Send and wait failed (opcode=%s, seq=%s)", opcode, msg["seq"])
            raise RuntimeError("Send and wait failed")
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
                        self.logger.info("Circuit breaker reset")
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
                        timeout=message.get("timeout", DEFAULT_TIMEOUT),
                    )
                    self.logger.debug("Message sent successfully from queue")
                    self._error_count = max(0, self._error_count - 1)
                except Exception as e:
                    self._error_count += 1
                    self._last_error_time = time.time()

                    if self._error_count > 10:
                        self._circuit_breaker = True
                        self.logger.warning(
                            "Circuit breaker activated due to %d consecutive errors",
                            self._error_count,
                        )
                        await self._outgoing.put(message)
                        continue

                    retry_delay = self._get_retry_delay(e, retry_count)
                    self.logger.warning(
                        "Failed to send message from queue: %s (delay: %ds)",
                        e,
                        retry_delay,
                    )

                    if retry_count < max_retries:
                        message["retry_count"] = retry_count + 1
                        await asyncio.sleep(retry_delay)
                        await self._outgoing.put(message)
                    else:
                        self.logger.error(
                            "Message failed after %d retries, dropping",
                            max_retries,
                        )

            except Exception:
                self.logger.exception("Error in outgoing loop")
                await asyncio.sleep(1)

    def _get_retry_delay(self, error: Exception, retry_count: int) -> float:
        if isinstance(error, (ConnectionError, OSError)):
            return 1.0
        elif isinstance(error, TimeoutError):
            return 5.0
        elif isinstance(error, WebSocketNotConnectedError):
            return 2.0
        else:
            return float(2**retry_count)

    async def _sync(self, user_agent: UserAgentPayload) -> None:
        self.logger.info("Starting initial sync")

        payload = SyncPayload(
            interactive=True,
            token=self._token,
            chats_sync=0,
            contacts_sync=0,
            presence_sync=0,
            drafts_sync=0,
            chats_count=40,
            user_agent=user_agent,
        ).model_dump(by_alias=True)
        try:
            data = await self._send_and_wait(opcode=Opcode.LOGIN, payload=payload)
            raw_payload = data.get("payload", {})

            if error := raw_payload.get("error"):
                MixinsUtils.handle_error(data)

            for raw_chat in raw_payload.get("chats", []):
                try:
                    if raw_chat.get("type") == ChatType.DIALOG.value:
                        self.dialogs.append(Dialog.from_dict(raw_chat))
                    elif raw_chat.get("type") == ChatType.CHAT.value:
                        self.chats.append(Chat.from_dict(raw_chat))
                    elif raw_chat.get("type") == ChatType.CHANNEL.value:
                        self.channels.append(Channel.from_dict(raw_chat))
                except Exception:
                    self.logger.exception("Error parsing chat entry")

            if raw_payload.get("profile", {}).get("contact"):
                self.me = Me.from_dict(raw_payload.get("profile", {}).get("contact", {}))

            self.logger.info(
                "Sync completed: dialogs=%d chats=%d channels=%d",
                len(self.dialogs),
                len(self.chats),
                len(self.channels),
            )

        except Exception as e:
            self.logger.exception("Sync failed")
            self.is_connected = False
            if self._ws:
                await self._ws.close()
            self._ws = None
            raise e

    @override
    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

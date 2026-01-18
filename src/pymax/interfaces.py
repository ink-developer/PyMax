import asyncio
import contextlib
import json
import logging
import time
import traceback
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from typing_extensions import Self

from pymax.exceptions import SocketNotConnectedError, WebSocketNotConnectedError
from pymax.filters import BaseFilter
from pymax.formatter import ColoredFormatter
from pymax.payloads import BaseWebSocketMessage, SyncPayload, UserAgentPayload
from pymax.protocols import ClientProtocol
from pymax.static.constant import DEFAULT_PING_INTERVAL, DEFAULT_TIMEOUT
from pymax.static.enum import Opcode
from pymax.types import (
    Channel,
    Chat,
    ChatType,
    Dialog,
    Me,
    Message,
    MessageStatus,
    ReactionCounter,
    ReactionInfo,
    User,
)
from pymax.utils import MixinsUtils


class BaseClient(ClientProtocol):
    def _setup_logger(self) -> None:
        if not self.logger.handlers:
            if not self.logger.level:
                self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = ColoredFormatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def _safe_execute(self, coro, *, context: str = "unknown") -> Any:
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Unhandled exception in {context}: {e}\n{traceback.format_exc()}")

    def _create_safe_task(
        self, coro: Awaitable[Any], name: str | None = None
    ) -> asyncio.Task[Any | None]:
        async def runner():
            try:
                return await coro
            except asyncio.CancelledError:
                raise
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(f"Unhandled exception in task {name or coro}: {e}\n{tb}")
                raise

        task = asyncio.create_task(runner(), name=name)
        self._background_tasks.add(task)
        return task

    async def _cleanup_client(self) -> None:
        for task in list(self._background_tasks):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.debug("Background task raised during cancellation", exc_info=True)
            self._background_tasks.discard(task)

        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
            self._recv_task = None

        if self._outgoing_task:
            self._outgoing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._outgoing_task
            self._outgoing_task = None

        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(WebSocketNotConnectedError())
        self._pending.clear()

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                self.logger.debug("Error closing ws during cleanup", exc_info=True)
            self._ws = None

        self.is_connected = False
        self.logger.info("Client start() cleaned up")

    async def idle(self):
        """
        Поддерживает клиента в «ожидающем» состоянии до закрытия клиента или иного прерывающего события.

        :return: Никогда не возвращает значение; функция блокирует выполнение.
        :rtype: None
        """
        await asyncio.Event().wait()

    def inspect(self) -> None:
        """
        Выводит в лог текущий статус клиента для отладки.
        """
        self.logger.info("Pymax")
        self.logger.info("---------")
        self.logger.info(f"Connected: {self.is_connected}")
        if self.me is not None:
            self.logger.info(f"Me: {self.me.names[0].first_name} ({self.me.id})")
        else:
            self.logger.info("Me: N/A")
        self.logger.info(f"Dialogs: {len(self.dialogs)}")
        self.logger.info(f"Chats: {len(self.chats)}")
        self.logger.info(f"Channels: {len(self.channels)}")
        self.logger.info(f"Users cached: {len(self._users)}")
        self.logger.info(f"Background tasks: {len(self._background_tasks)}")
        self.logger.info(f"Scheduled tasks: {len(self._scheduled_tasks)}")
        self.logger.info("---------")

    async def __aenter__(self) -> Self:
        self._create_safe_task(self.start(), name="start")
        while not self.is_connected:
            await asyncio.sleep(0.05)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @abstractmethod
    async def login_with_code(self, temp_token: str, code: str, start: bool = False) -> None:
        pass

    @abstractmethod
    async def _post_login_tasks(self, sync: bool = True) -> None:
        pass

    @abstractmethod
    async def _wait_forever(self) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class BaseTransport(ClientProtocol):
    @abstractmethod
    async def connect(
        self, user_agent: UserAgentPayload | None = None
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    async def _send_and_wait(
        self,
        opcode: Opcode,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def _recv_loop(self) -> None: ...

    def _make_message(
        self, opcode: Opcode, payload: dict[str, Any], cmd: int = 0
    ) -> dict[str, Any]:
        self._seq += 1

        msg = BaseWebSocketMessage(
            ver=11,
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
            except SocketNotConnectedError:
                self.logger.debug("Socket disconnected, exiting ping loop")
                break
            except Exception:
                self.logger.warning("Interactive ping failed")
            await asyncio.sleep(DEFAULT_PING_INTERVAL)

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

    async def _send_notification_response(self, chat_id: int, message_id: str) -> None:
        if self._socket is not None and self.is_connected:
            return
        await self._send_and_wait(
            opcode=Opcode.NOTIF_MESSAGE,
            payload={"chatId": chat_id, "messageId": message_id},
            cmd=0,
        )
        self.logger.debug(
            "Sent NOTIF_MESSAGE_RECEIVED for chat_id=%s message_id=%s", chat_id, message_id
        )

    async def _handle_message_notifications(self, data: dict) -> None:
        if data.get("opcode") != Opcode.NOTIF_MESSAGE.value:
            return
        payload = data.get("payload", {})
        msg = Message.from_dict(payload)
        if not msg:
            return

        if msg.chat_id and msg.id:
            await self._send_notification_response(msg.chat_id, str(msg.id))

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

    async def _sync(self, user_agent: UserAgentPayload | None = None) -> None:
        self.logger.info("Starting initial sync")

        if user_agent is None:
            user_agent = self.headers or UserAgentPayload()

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

            # Очищаем списки перед sync, чтобы избежать дублирования при повторном вызове
            self.dialogs.clear()
            self.chats.clear()
            self.channels.clear()
            self.contacts.clear()

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

            for raw_user in raw_payload.get("contacts", []):
                try:
                    user = User.from_dict(raw_user)
                    if user:
                        self.contacts.append(user)
                except Exception:
                    self.logger.exception("Error parsing contact entry")

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
            raise

    async def _get_chat(self, chat_id: int) -> Chat | None:
        for chat in self.chats:
            if chat.id == chat_id:
                return chat
        return None

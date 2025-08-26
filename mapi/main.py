import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import websockets

from .chats import Channel, Chat, Dialog, Message
from .crud import Database
from .enum import AuthType, ChatType, Constants, Opcode


class InvalidPhoneError(Exception):
    def __init__(self, phone: str) -> None:
        super().__init__(f"Invalid phone number format: {phone}")


class WebSocketNotConnectedError(Exception):
    def __init__(self) -> None:
        super().__init__("WebSocket is not connected")


class MaxClient:
    def __init__(
        self, phone: str, uri: str = Constants.WEBSOCKET_URI.value, work_dir: str = "."
    ) -> None:
        self.uri: str = uri
        self.is_connected: bool = False
        self.phone: str = phone
        self.chats: list[Chat] = []
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []

        if not self._check_phone():
            raise InvalidPhoneError(self.phone)

        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / "session.db"
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path.touch(exist_ok=True)

        self._database = Database(self._work_dir)
        self._ws: websockets.ClientConnection | None = None
        self._seq: int = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] | None = None
        self._device_id = self._database.get_device_id()
        self._token = self._database.get_auth_token()
        self.user_agent = Constants.DEFAULT_USER_AGENT.value
        self._on_message_handler: Callable[[Message], Any] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @property
    def ws(self) -> websockets.ClientConnection:
        if self._ws is None or not self.is_connected:
            raise WebSocketNotConnectedError
        return self._ws

    def on_message(
        self, handler: Callable[[Message], Any | Awaitable[Any]]
    ) -> Callable[[Message], Any | Awaitable[Any]]:
        self._on_message_handler = handler
        return handler

    def _check_phone(self) -> bool:
        return bool(re.match(Constants.PHONE_REGEX.value, self.phone))

    def _make_message(self, opcode: int, payload: dict[str, Any], cmd: int = 0) -> dict[str, Any]:
        self._seq += 1
        return {"ver": 11, "cmd": cmd, "seq": self._seq, "opcode": opcode, "payload": payload}

    async def _connect(self, user_agent: dict[str, Any]) -> dict[str, Any]:
        try:
            self._ws = await websockets.connect(self.uri)
            self.is_connected = True
            self._incoming = asyncio.Queue()
            self._pending = {}
            self._recv_task = asyncio.create_task(self._recv_loop())
            return await self._handshake(user_agent)
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

    async def _handshake(self, user_agent: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self._send_and_wait(
                opcode=Opcode.HANDSHAKE,
                payload={"deviceId": str(self._device_id), "userAgent": user_agent},
            )
        except Exception as e:
            raise ConnectionError(f"Handshake failed: {e}")

    async def _request_code(self, phone: str, language: str = "ru") -> dict[str, int | str]:
        try:
            payload = {"phone": phone, "type": AuthType.START_AUTH.value, "language": language}
            data = await self._send_and_wait(opcode=Opcode.REQUEST_CODE, payload=payload)
            return data.get("payload")
        except Exception as e:
            raise RuntimeError(f"Request code failed: {e}")

    async def _send_code(self, code: str, token: str) -> dict[str, Any]:
        try:
            payload = {
                "token": token,
                "verifyCode": code,
                "authTokenType": AuthType.CHECK_CODE.value,
            }
            data = await self._send_and_wait(opcode=Opcode.SEND_CODE, payload=payload)
            return data.get("payload")
        except Exception as e:
            raise RuntimeError(f"Send code failed: {e}")

    async def _recv_loop(self) -> None:
        if self._ws is None:
            return

        while True:
            try:
                raw = await self._ws.recv()
                try:
                    data = json.loads(raw)
                except Exception as e:
                    print("JSON parse error:", e)
                    continue

                seq = data.get("seq")
                fut = self._pending.get(seq) if isinstance(seq, int) else None

                if fut and not fut.done():
                    fut.set_result(data)
                else:
                    if self._incoming is not None:
                        try:
                            self._incoming.put_nowait(data)
                        except asyncio.QueueFull:
                            pass

                    if data.get("opcode") == Opcode.NEW_MESSAGE and self._on_message_handler:
                        try:
                            payload = data.get("payload", {})
                            msg = Message.from_dict(payload.get("message"))
                            if msg:
                                result = self._on_message_handler(msg)
                                if asyncio.iscoroutine(result):
                                    task = asyncio.create_task(result)
                                    self._background_tasks.add(task)
                                    task.add_done_callback(
                                        lambda t: self._background_tasks.discard(t)
                                        or self._log_task_exception(t)
                                    )
                        except Exception as e:
                            print("Error in on_message_handler:", e)

            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print("Error in recv_loop:", e)
                await asyncio.sleep(0.5)

    def _log_task_exception(self, task: asyncio.Task[Any]) -> None:
        try:
            exc = task.exception()
            if exc:
                print("Background task exception:", exc)
        except Exception:
            pass

    async def _send_and_wait(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = Constants.DEFAULT_TIMEOUT.value,
    ) -> dict[str, Any]:
        if not self.ws:
            raise WebSocketNotConnectedError

        msg = self._make_message(opcode, payload, cmd)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[msg["seq"]] = fut

        try:
            await self.ws.send(json.dumps(msg))
            data = await asyncio.wait_for(fut, timeout=timeout)
            return data
        except Exception as e:
            raise RuntimeError(f"Send and wait failed: {e}")
        finally:
            self._pending.pop(msg["seq"], None)

    async def _sync(self) -> None:
        try:
            payload = {
                "interactive": True,
                "token": self._token,
                "chatsSync": 0,
                "contactsSync": 0,
                "presenceSync": 0,
                "draftsSync": 0,
                "chatsCount": 40,
            }
            data = await self._send_and_wait(opcode=19, payload=payload)
            if error := data.get("payload", {}).get("error"):
                print("Sync error:", error)
                return

            for raw_chat in data.get("payload", {}).get("chats", []):
                try:
                    if raw_chat.get("type") == ChatType.DIALOG.value:
                        self.dialogs.append(Dialog.from_dict(raw_chat))
                    elif raw_chat.get("type") == ChatType.CHAT.value:
                        self.chats.append(Chat.from_dict(raw_chat))
                    elif raw_chat.get("type") == ChatType.CHANNEL.value:
                        self.channels.append(Channel.from_dict(raw_chat))
                except Exception as e:
                    print("Error parsing chat:", e)
        except Exception as e:
            print("Sync failed:", e)

    async def send_message(self, text: str, chat_id: int, notify: bool) -> Message | None:
        try:
            payload = {
                "chatId": chat_id,
                "message": {
                    "text": text,
                    "cid": int(time.time() * 1000),
                    "elements": [],
                    "attaches": [],
                },
                "notify": notify,
            }
            data = await self._send_and_wait(opcode=Opcode.SEND_MESSAGE, payload=payload)
            if error := data.get("payload", {}).get("error"):
                print("Send message error:", error)
            return Message.from_dict(data["payload"]["message"])
        except Exception as e:
            print("Send message failed:", e)
            return None

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> Message | None:
        try:
            payload = {
                "chatId": chat_id,
                "messageId": message_id,
                "text": text,
                "elements": [],
                "attaches": [],
            }
            data = await self._send_and_wait(opcode=Opcode.EDIT_MESSAGE, payload=payload)
            if error := data.get("payload", {}).get("error"):
                print("Edit message error:", error)
            return Message.from_dict(data["payload"]["message"])
        except Exception as e:
            print("Edit message failed:", e)
            return None

    async def delete_message(self, chat_id: int, message_ids: list[int], for_me: bool) -> bool:
        try:
            payload = {"chatId": chat_id, "messageIds": message_ids, "forMe": for_me}
            data = await self._send_and_wait(opcode=Opcode.DELETE_MESSAGE, payload=payload)
            if error := data.get("payload", {}).get("error"):
                print("Delete message error:", error)
                return False
            return True
        except Exception as e:
            print("Delete message failed:", e)
            return False

    async def close(self) -> None:
        try:
            if self._recv_task:
                self._recv_task.cancel()
                try:
                    await self._recv_task
                except asyncio.CancelledError:
                    pass
            if self._ws:
                await self._ws.close()
            self.is_connected = False
        except Exception as e:
            print("Error closing client:", e)

    async def start(self) -> None:
        try:
            await self._connect(self.user_agent)
            if self._token is None:
                request_code_payload = await self._request_code(self.phone)
                temp_token = request_code_payload.get("token")
                if not temp_token or not isinstance(temp_token, str):
                    raise ValueError("Failed to request code")

                code = await asyncio.to_thread(input, "Введите код: ")
                if len(code) != 6 or not code.isdigit():
                    raise ValueError("Invalid code format")

                login_resp = await self._send_code(code, temp_token)
                token: str | None = login_resp.get("tokenAttrs", {}).get("LOGIN", {}).get("token")
                if not token:
                    raise ValueError("Failed to login, token not received")

                self._token = token
                self._database.update_auth_token(self._device_id, self._token)
                print("Login successful, token saved to database")
            else:
                await self._sync()

            if self._ws:
                try:
                    await self._ws.wait_closed()
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            print("Client start failed:", e)

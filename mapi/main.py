import asyncio
import json
import re
import time

from pathlib import Path
from typing import Any

import websockets

from .chats import Channel, Chat, Dialog, Message
from .crud import Database
from .enum import Opcode, ChatType, Constants, AuthType

# from .profile import MaxProfile

class InvalidPhoneError(Exception):
    def __init__(self, phone: str) -> None:
        super().__init__(f"Invalid phone number format: {phone}")


class WebSocketNotConnectedError(Exception):
    def __init__(self) -> None:
        super().__init__("WebSocket is not connected")


class MaxClient:
    def __init__(
        self,
        phone: str,
        uri: str = Constants.WEBSOCKET_URI.value,
        work_dir: str = ".",
    ) -> None:
        self.uri: str = uri
        self.is_connected: bool = False
        self.phone: str = phone
        self.chats: list[Chat] = []
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []

        if self._check_phone() is False:
            raise InvalidPhoneError(self.phone)

        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / "session.db"

        if not self._database_path.exists():
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            self._database_path.touch()
        self._database = Database(self._work_dir)
        self._ws: websockets.ClientConnection | None = None
        self._seq: int = 0

        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] | None = None

        self._device_id = self._database.get_device_id()

        self._token = self._database.get_auth_token()

        self.user_agent = Constants.DEFAULT_USER_AGENT.value

    @property
    def ws(self) -> websockets.ClientConnection:
        if self._ws is None:
            raise WebSocketNotConnectedError
        return self._ws

    def _check_socket_con(self) -> bool:
        return bool(self._ws)

    def _check_phone(self) -> bool:
        return re.match(Constants.PHONE_REGEX.value, self.phone) is not None

    def _make_message(self, opcode: int, payload: dict[str, Any], cmd: int = 0) -> dict[str, Any]:
        self._seq += 1
        return {
            "ver": 11,
            "cmd": cmd,
            "seq": self._seq,
            "opcode": opcode,
            "payload": payload,
        }

    async def _connect(self, user_agent: dict[str, Any]) -> dict[str, Any]:
        self._ws = await websockets.connect(self.uri)
        self.is_connected = True

        self._incoming = asyncio.Queue()
        self._pending = {}
        self._recv_task = asyncio.create_task(self._recv_loop())

        return await self._handshake(user_agent)

    async def _handshake(self, user_agent: dict[str, Any]) -> dict[str, Any]:
        return await self._send_and_wait(
            opcode=Opcode.HANDSHAKE,
            payload={
                "deviceId": str(self._device_id),
                "userAgent": user_agent,
            },
        )

    async def _request_code(self, phone: str, language: str = "ru") -> dict[str, int | str]:
        payload = {"phone": phone, "type": AuthType.START_AUTH.value, "language": language}
        data = await self._send_and_wait(opcode=Opcode.REQUEST_CODE, payload=payload)
        return data.get("payload")

    async def _send_code(self, code: str, token: str) -> dict[str, Any]:
        payload = {
            "token": token,
            "verifyCode": code,
            "authTokenType": AuthType.CHECK_CODE.value,
        }
        data = await self._send_and_wait(opcode=Opcode.SEND_CODE, payload=payload)
        return data.get("payload")

    async def _recv(self) -> dict[str, Any] | None:
        if self._ws:
            resp = await self._ws.recv()
            return json.loads(resp)
        return None

    async def _recv_loop(self) -> None:
        ws = self._ws
        if ws is None:
            return

        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                break
            try:
                data = json.loads(raw)
            except Exception:
                continue

            seq = data.get("seq")
            fut = None
            if isinstance(seq, int):
                fut = self._pending.get(seq)

            if fut:
                if not fut.done():
                    fut.set_result(data)
            else:
                if self._incoming is not None:
                    try:  # noqa: SIM105
                        self._incoming.put_nowait(data)
                    except asyncio.QueueFull:
                        pass

    async def _send(self, opcode: int, payload: dict[str, Any], cmd: int = 0) -> None:
        msg = self._make_message(opcode=opcode, payload=payload, cmd=cmd)
        if self.ws:
            await self.ws.send(json.dumps(msg))

    async def _send_and_wait(
        self, opcode: int, payload: dict[str, Any], cmd: int = 0, timeout: float = Constants.DEFAULT_TIMEOUT.value
    ) -> dict[str, Any]:
        if not self.ws:
            raise WebSocketNotConnectedError

        msg = self._make_message(opcode=opcode, payload=payload, cmd=cmd)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[msg["seq"]] = fut

        try:
            await self.ws.send(json.dumps(msg))
        except Exception:
            self._pending.pop(msg["seq"], None)
            raise

        try:
            data = await asyncio.wait_for(fut, timeout=timeout)
            return data
        finally:
            self._pending.pop(msg["seq"], None)

    async def _sync(self) -> None:
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

        if data.get("payload", {}).get("error"):
            print("Sync error:", data["payload"]["error"])
            return

        raw_chats = data.get("payload", {}).get("chats", [])

        for raw_chat in raw_chats:
            if raw_chat.get("type") == ChatType.DIALOG.value:
                self.dialogs.append(Dialog.from_dict(raw_chat))
            elif raw_chat.get("type") == ChatType.CHAT.value:
                self.chats.append(Chat.from_dict(raw_chat))
            elif raw_chat.get("type") == ChatType.CHANNEL.value:
                self.channels.append(Channel.from_dict(raw_chat))

    async def send_message(self, text: str, chat_id: int, notify: bool) -> Message:
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

        if data.get("payload", {}).get("error"):
            print("Send message error:", data["payload"]["error"])

        return Message.from_dict(data["payload"]["message"])

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> Message:
        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "text": text,
            "elements": [],
            "attaches": [],
        }
        data = await self._send_and_wait(opcode=Opcode.EDIT_MESSAGE, payload=payload)

        if data.get("payload", {}).get("error"):
            print("Edit message error:", data["payload"]["error"])

        return Message.from_dict(data["payload"]["message"])

    async def delete_message(self, chat_id: int, message_ids: list[int], for_me: bool) -> bool:
        payload = {
            "chatId": chat_id,
            "messageIds": message_ids,
            "forMe": for_me,
        }
        data = await self._send_and_wait(opcode=Opcode.DELETE_MESSAGE, payload=payload)

        if data.get("payload", {}).get("error"):
            print("Delete message error:", data["payload"]["error"])
            return False

        return True

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()

        if self._recv_task is not None:
            self._recv_task.cancel()

    async def start(self) -> None:
        await self._connect(self.user_agent)

        if self._token is None:
            request_code_payload = await self._request_code(self.phone)
            temp_token = request_code_payload.get("token")

            if not temp_token or not isinstance(temp_token, str):
                raise ValueError("Failed to request code")

            code = input("Введите код: ")
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

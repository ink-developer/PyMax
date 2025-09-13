import time

from pymax.interfaces import ClientProtocol
from pymax.payloads import (
    DeleteMessagePayload,
    EditMessagePayload,
    FetchHistoryPayload,
    PinMessagePayload,
    ReplyLink,
    SendMessagePayload,
    SendMessagePayloadMessage,
)
from pymax.static import Opcode
from pymax.types import Message


class MessageMixin(ClientProtocol):
    async def send_message(
        self, text: str, chat_id: int, notify: bool, reply_to: int | None = None
    ) -> Message | None:
        """
        Отправляет сообщение в чат.
        """
        try:
            self.logger.info("Sending message to chat_id=%s notify=%s", chat_id, notify)
            payload = SendMessagePayload(
                chat_id=chat_id,
                message=SendMessagePayloadMessage(
                    text=text,
                    cid=int(time.time() * 1000),
                    elements=[],
                    attaches=[],
                    link=ReplyLink(message_id=str(reply_to)) if reply_to else None,
                ),
                notify=notify,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.SEND_MESSAGE, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Send message error: %s", error)
            msg = (
                Message.from_dict(data["payload"]["message"])
                if data.get("payload")
                else None
            )
            self.logger.debug("send_message result: %r", msg)
            return msg
        except Exception:
            self.logger.exception("Send message failed")
            return None

    async def edit_message(
        self, chat_id: int, message_id: int, text: str
    ) -> Message | None:
        """
        Редактирует сообщение.
        """
        try:
            self.logger.info(
                "Editing message chat_id=%s message_id=%s", chat_id, message_id
            )
            payload = EditMessagePayload(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                elements=[],
                attaches=[],
            ).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.EDIT_MESSAGE, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Edit message error: %s", error)
            msg = (
                Message.from_dict(data["payload"]["message"])
                if data.get("payload")
                else None
            )
            self.logger.debug("edit_message result: %r", msg)
            return msg
        except Exception:
            self.logger.exception("Edit message failed")
            return None

    async def delete_message(
        self, chat_id: int, message_ids: list[int], for_me: bool
    ) -> bool:
        """
        Удаляет сообщения.
        """
        try:
            self.logger.info(
                "Deleting messages chat_id=%s ids=%s for_me=%s",
                chat_id,
                message_ids,
                for_me,
            )

            payload = DeleteMessagePayload(
                chat_id=chat_id, message_ids=message_ids, for_me=for_me
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.DELETE_MESSAGE, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Delete message error: %s", error)
                return False
            self.logger.debug("delete_message success")
            return True
        except Exception:
            self.logger.exception("Delete message failed")
            return False

    async def pin_message(
        self, chat_id: int, message_id: int, notify_pin: bool
    ) -> bool:
        """
        Закрепляет сообщение.

        Args:
            chat_id (int): ID чата
            message_id (int): ID сообщения
            notify_pin (bool): Оповещать о закреплении

        Returns:
            bool: True, если сообщение закреплено
        """
        try:
            payload = PinMessagePayload(
                chat_id=chat_id,
                notify_pin=notify_pin,
                pin_message_id=message_id,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.GROUP_ACTION, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Pin message error: %s", error)
                return False
            self.logger.debug("pin_message success")
            return True
        except Exception:
            self.logger.exception("Pin message failed")
            return False

    async def fetch_history(
        self,
        chat_id: int,
        from_time: int | None = None,
        forward: int = 0,
        backward: int = 200,
    ) -> list[Message] | None:
        """
        Получает историю сообщений чата.
        """
        if from_time is None:
            from_time = int(time.time() * 1000)

        try:
            self.logger.info(
                "Fetching history chat_id=%s from=%s forward=%s backward=%s",
                chat_id,
                from_time,
                forward,
                backward,
            )

            payload = FetchHistoryPayload(
                chat_id=chat_id,
                from_time=from_time,  # pyright: ignore[reportCallIssue] FIXME: Pydantic Field alias
                forward=forward,
                backward=backward,
            ).model_dump(by_alias=True)

            self.logger.debug("Payload dict keys: %s", list(payload.keys()))

            data = await self._send_and_wait(
                opcode=Opcode.FETCH_HISTORY, payload=payload, timeout=10
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Fetch history error: %s", error)
                return None

            messages = [
                Message.from_dict(msg) for msg in data["payload"].get("messages", [])
            ]
            self.logger.debug("History fetched: %d messages", len(messages))
            return messages
        except Exception:
            self.logger.exception("Fetch history failed")
            return None

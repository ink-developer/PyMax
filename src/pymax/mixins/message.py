import time
from typing import Any

import aiohttp
from aiohttp import ClientSession

from pymax.files import Photo
from pymax.interfaces import ClientProtocol
from pymax.payloads import (
    AddReactionPayload,
    AttachPhotoPayload,
    DeleteMessagePayload,
    EditMessagePayload,
    FetchHistoryPayload,
    GetFilePayload,
    GetReactionsPayload,
    GetVideoPayload,
    ReactionObject,
    RemoveReactionPayload,
    PinMessagePayload,
    ReplyLink,
    SendMessagePayload,
    SendMessagePayloadMessage,
    UploadPhotoPayload,
)
from pymax.static import AttachType, Opcode
from pymax.types import Attach, FileRequest, Message, VideoRequest


class MessageMixin(ClientProtocol):
    async def _upload_photo(self, photo: Photo) -> None | Attach:
        try:
            self.logger.info("Uploading photo")
            payload = UploadPhotoPayload().model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.PHOTO_UPLOAD,
                payload=payload,
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Upload photo error: %s", error)
                return None

            url = data.get("payload", {}).get("url")
            if not url:
                self.logger.error("No upload URL received")
                return None

            photo_data = photo.validate_photo()
            if not photo_data:
                self.logger.error("Photo validation failed")
                return None

            form = aiohttp.FormData()
            form.add_field(
                name="file",
                value=await photo.read(),
                filename=f"image.{photo_data[0]}",
                content_type=photo_data[1],
            )

            async with (
                ClientSession() as session,
                session.post(
                    url=url,
                    data=form,
                ) as response,
            ):
                if response.status != 200:
                    self.logger.error(f"Upload failed with status {response.status}")
                    return None

                result = await response.json()

                if not result.get("photos"):
                    self.logger.error("No photos in response")
                    return None

                photo_data = next(iter(result["photos"].values()), None)
                if not photo_data or "token" not in photo_data:
                    self.logger.error("No token in response")
                    return None

                return Attach(
                    _type=AttachType.PHOTO,
                    photo_token=photo_data["token"],
                )

        except Exception as e:
            self.logger.exception("Upload photo failed: %s", str(e))
            return None

    async def send_message(
        self,
        text: str,
        chat_id: int,
        notify: bool,
        photo: Photo | None = None,
        photos: list[Photo] | None = None,
        reply_to: int | None = None,
    ) -> Message | None:
        """
        Отправляет сообщение в чат.
        """
        try:
            self.logger.info("Sending message to chat_id=%s notify=%s", chat_id, notify)
            if photos and photo:
                self.logger.warning("Both photo and photos provided; using photos")
                photo = None
            attaches = []
            if photo:
                self.logger.info("Uploading photo for message")
                attach = await self._upload_photo(photo)
                if not attach or not attach.photo_token:
                    self.logger.error("Photo upload failed, message not sent")
                    return None
                attaches = [
                    AttachPhotoPayload(photo_token=attach.photo_token).model_dump(
                        by_alias=True
                    )
                ]
            elif photos:
                self.logger.info("Uploading multiple photos for message")
                for p in photos:
                    attach = await self._upload_photo(p)
                    if attach and attach.photo_token:
                        attaches.append(
                            AttachPhotoPayload(
                                photo_token=attach.photo_token
                            ).model_dump(by_alias=True)
                        )
                if not attaches:
                    self.logger.error("All photo uploads failed, message not sent")
                    return None

            payload = SendMessagePayload(
                chat_id=chat_id,
                message=SendMessagePayloadMessage(
                    text=text,
                    cid=int(time.time() * 1000),
                    elements=[],
                    attaches=attaches,
                    link=ReplyLink(message_id=str(reply_to)) if reply_to else None,
                ),
                notify=notify,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.MSG_SEND, payload=payload)
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Send message error: %s", error)
                return None
            msg = Message.from_dict(data["payload"]) if data.get("payload") else None
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
            data = await self._send_and_wait(opcode=Opcode.MSG_EDIT, payload=payload)
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Edit message error: %s", error)
            msg = Message.from_dict(data["payload"]) if data.get("payload") else None
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

            data = await self._send_and_wait(opcode=Opcode.MSG_DELETE, payload=payload)
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

            data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)
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
                opcode=Opcode.CHAT_HISTORY, payload=payload, timeout=10
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

    async def get_video_by_id(
        self,
        chat_id: int,
        message_id: int,
        video_id: int,
    ) -> VideoRequest | None:
        """
        Получает видео

        Args:
            chat_id (int): ID чата
            message_id (int): ID сообщения
            video_id (int): ID видео

        Returns:
            external (str): Странная ссылка из апи
            cache (bool): True, если видео кэшировано
            url (str): Ссылка на видео
        """
        try:
            self.logger.info("Getting video_id=%s message_id=%s", video_id, message_id)

            if self.is_connected and self._socket is not None:
                payload = GetVideoPayload(
                    chat_id=chat_id, message_id=message_id, video_id=video_id
                ).model_dump(by_alias=True)
            else:
                payload = GetVideoPayload(
                    chat_id=chat_id, message_id=str(message_id), video_id=video_id
                ).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.VIDEO_PLAY, payload=payload)

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get video error: %s", error)
                return

            video = (
                VideoRequest.from_dict(data["payload"]) if data.get("payload") else None
            )
            self.logger.debug("result: %r", video)
            return video
        except Exception:
            self.logger.exception("Get video error")
            return None

    async def get_file_by_id(
        self,
        chat_id: int,
        message_id: int,
        file_id: int,
    ) -> FileRequest | None:
        """
        Получает файл

        Args:
            chat_id (int): ID чата
            message_id (int): ID сообщения
            file_id (int): ID видео

        Returns:
            unsafe (bool): Проверка файла на безопасность максом
            url (str): Ссылка на скачивание файла
        """
        try:
            self.logger.info("Getting file_id=%s message_id=%s", file_id, message_id)
            if self.is_connected and self._socket is not None:
                payload = GetFilePayload(
                    chat_id=chat_id, message_id=message_id, file_id=file_id
                ).model_dump(by_alias=True)
            else:
                payload = GetFilePayload(
                    chat_id=chat_id, message_id=str(message_id), file_id=file_id
                ).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.FILE_DOWNLOAD, payload=payload
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get file error: %s", error)
                return

            file = (
                FileRequest.from_dict(data["payload"]) if data.get("payload") else None
            )
            self.logger.debug(" result: %r", file)
            return file
        except Exception:
            self.logger.exception("Get video error")
            return None

    async def add_reaction(self, chat_id: int, message_id: int, emoji: str) -> bool:
        try:
            self.logger.info(
                "Adding reaction chat_id=%s message_id=%s emoji=%s",
                chat_id,
                message_id,
                emoji,
            )
            payload = AddReactionPayload(
                chat_id=chat_id,
                message_id=message_id,
                reaction=ReactionObject(id=emoji),
            ).model_dump(by_alias=True)
            data = await self._send_and_wait(opcode=Opcode.MSG_REACTION, payload=payload)
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Add reaction error: %s", error)
                return False
            return True
        except Exception:
            self.logger.exception("Add reaction failed")
            return False

    async def remove_reaction(self, chat_id: int, message_id: int) -> bool:
        try:
            self.logger.info(
                "Removing reaction chat_id=%s message_id=%s", chat_id, message_id
            )
            payload = RemoveReactionPayload(
                chat_id=chat_id,
                message_id=message_id,
            ).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.MSG_CANCEL_REACTION, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Remove reaction error: %s", error)
                return False
            return True
        except Exception:
            self.logger.exception("Remove reaction failed")
            return False

    async def get_reactions(
        self, chat_id: int, message_ids: list[str]
    ) -> dict[str, Any] | None:
        """
        Получает реакции на несколько сообщений.

        Args:
            chat_id (int): ID чата
            message_ids (list[str]): Список ID сообщений

        Returns:
            dict[str, Any] | None: Данные о реакциях или None при ошибке
        """
        try:
            self.logger.info(
                "Getting reactions chat_id=%s message_ids=%s", chat_id, message_ids
            )
            payload = GetReactionsPayload(
                chat_id=chat_id, message_ids=message_ids
            ).model_dump(by_alias=True)
            data = await self._send_and_wait(opcode=Opcode.MSG_GET_REACTIONS, payload=payload)
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get reactions error: %s", error)
                return None
            self.logger.debug("get_reactions success")
            return data.get("payload")
        except Exception:
            self.logger.exception("Get reactions failed")
            return None


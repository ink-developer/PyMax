import asyncio
import time

import aiohttp
from aiohttp import ClientSession

from pymax.files import File, Photo
from pymax.formatting import Formatting
from pymax.interfaces import ClientProtocol
from pymax.payloads import (
    AddReactionPayload,
    AttachFilePayload,
    AttachPhotoPayload,
    DeleteMessagePayload,
    EditMessagePayload,
    FetchHistoryPayload,
    GetFilePayload,
    GetReactionsPayload,
    GetVideoPayload,
    MessageElement,
    PinMessagePayload,
    ReactionInfoPayload,
    RemoveReactionPayload,
    ReplyLink,
    SendMessagePayload,
    SendMessagePayloadMessage,
    UploadPayload,
)
from pymax.static.constant import DEFAULT_TIMEOUT
from pymax.static.enum import AttachType, Opcode
from pymax.types import (
    Attach,
    FileRequest,
    Message,
    ReactionInfo,
    VideoRequest,
)


class MessageMixin(ClientProtocol):
    async def _upload_file(self, file: File) -> None | Attach:
        try:
            self.logger.info("Uploading file")
            payload = UploadPayload().model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.FILE_UPLOAD,
                payload=payload,
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Upload file error: %s", error)
                return None

            url = (
                data.get("payload", {}).get("info", [None])[0].get("url", None)
            )
            file_id = (
                data.get("payload", {})
                .get("info", [None])[0]
                .get("fileId", None)
            )
            if not url or not file_id:
                self.logger.error("No upload URL or file ID received")
                return None

            file_bytes = await file.read()

            headers = {
                "Content-Disposition": f"attachment; filename={file.file_name}",
                "Content-Range": f"0-{len(file_bytes) - 1}/{len(file_bytes)}",
            }

            loop = asyncio.get_running_loop()
            fut: asyncio.Future[dict] = loop.create_future()
            try:
                self._file_upload_waiters[int(file_id)] = fut
            except Exception:
                self.logger.exception("Failed to register file upload waiter")

            async with (
                ClientSession() as session,
                session.post(
                    url=url,
                    headers=headers,
                    data=file_bytes,
                ) as response,
            ):
                if response.status != 200:
                    self.logger.error(
                        f"Upload failed with status {response.status}"
                    )
                    # cleanup waiter
                    self._file_upload_waiters.pop(int(file_id), None)
                    return None

                try:
                    await asyncio.wait_for(fut, timeout=DEFAULT_TIMEOUT)
                    return Attach(_type=AttachType.FILE, file_id=file_id)
                except asyncio.TimeoutError:
                    self.logger.error(
                        "Timed out waiting for file processing notification for fileId=%s",
                        file_id,
                    )
                    self._file_upload_waiters.pop(int(file_id), None)
                    return None
        except Exception as e:
            self.logger.exception("Upload file failed: %s", str(e))
            return None

    async def _upload_photo(self, photo: Photo) -> None | Attach:
        try:
            self.logger.info("Uploading photo")
            payload = UploadPayload().model_dump(by_alias=True)

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
                    self.logger.error(
                        f"Upload failed with status {response.status}"
                    )
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

    async def _upload_attachment(self, attach: Photo | File) -> dict | None:
        if isinstance(attach, Photo):
            uploaded = await self._upload_photo(attach)
            if uploaded and uploaded.photo_token:
                return AttachPhotoPayload(
                    photo_token=uploaded.photo_token
                ).model_dump(by_alias=True)
        elif isinstance(attach, File):
            uploaded = await self._upload_file(attach)
            if uploaded and uploaded.file_id:
                return AttachFilePayload(file_id=uploaded.file_id).model_dump(
                    by_alias=True
                )
        self.logger.error(f"Attachment upload failed for {attach}")
        return None

    async def send_message(
        self,
        text: str,
        chat_id: int,
        notify: bool,
        attachment: Photo | File | None = None,
        attachments: list[Photo | File] | None = None,
        reply_to: int | None = None,
        use_queue: bool = False,
    ) -> Message | None:
        """
        Отправляет сообщение в чат.
        """
        try:
            self.logger.info(
                "Sending message to chat_id=%s notify=%s", chat_id, notify
            )
            if attachments and attachment:
                self.logger.warning(
                    "Both photo and photos provided; using photos"
                )
                attachment = None
            attaches = []
            if attachment:
                self.logger.info("Uploading attachment for message")
                result = await self._upload_attachment(attachment)
                if not result:
                    self.logger.error(
                        "Attachment upload failed, message not sent"
                    )
                    return None
                attaches.append(result)

            elif attachments:
                self.logger.info("Uploading multiple attachments for message")
                for p in attachments:
                    result = await self._upload_attachment(p)
                    if result:
                        attaches.append(result)
                    else:
                        self.logger.error("One of attachments upload failed")

                if not attaches:
                    self.logger.error(
                        "All attachments uploads failed, message not sent"
                    )
                    return None

            elements = []
            clean_text = None
            raw_elements = Formatting.get_elements_from_markdown(text)[0]
            if raw_elements:
                clean_text = Formatting.get_elements_from_markdown(text)[1]
            elements = [
                MessageElement(type=e.type, length=e.length, from_=e.from_)
                for e in raw_elements
            ]

            payload = SendMessagePayload(
                chat_id=chat_id,
                message=SendMessagePayloadMessage(
                    text=clean_text if clean_text else text,
                    cid=int(time.time() * 1000),
                    elements=elements,
                    attaches=attaches,
                    link=(
                        ReplyLink(message_id=str(reply_to))
                        if reply_to
                        else None
                    ),
                ),
                notify=notify,
            ).model_dump(by_alias=True)

            if use_queue:
                await self._queue_message(
                    opcode=Opcode.MSG_SEND, payload=payload
                )
                self.logger.debug("Message queued for sending")
                return None
            else:
                data = await self._send_and_wait(
                    opcode=Opcode.MSG_SEND, payload=payload
                )
                if error := data.get("payload", {}).get("error"):
                    self.logger.error("Send message error: %s", error)
                    return None
                msg = (
                    Message.from_dict(data["payload"])
                    if data.get("payload")
                    else None
                )
                self.logger.debug("send_message result: %r", msg)
                return msg
        except Exception:
            self.logger.exception("Send message failed")
            return None

    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        attachment: Photo | None = None,
        attachments: list[Photo] | None = None,
        use_queue: bool = False,
    ) -> Message | None:
        try:
            self.logger.info(
                "Editing message chat_id=%s message_id=%s", chat_id, message_id
            )

            if attachments and attachment:
                self.logger.warning(
                    "Both photo and photos provided; using photos"
                )
                attachment = None
            attaches = []
            if attachment:
                self.logger.info("Uploading attachment for message")
                result = await self._upload_attachment(attachment)
                if not result:
                    self.logger.error(
                        "Attachment upload failed, message not sent"
                    )
                    return None
                attaches.append(result)

            elif attachments:
                self.logger.info("Uploading multiple attachments for message")
                for p in attachments:
                    result = await self._upload_attachment(p)
                    if result:
                        attaches.append(result)
                    else:
                        self.logger.error("One of attachments upload failed")

                if not attaches:
                    self.logger.error(
                        "All attachments uploads failed, message not sent"
                    )
                    return None

            elements = []
            clean_text = None
            raw_elements = Formatting.get_elements_from_markdown(text)[0]
            if raw_elements:
                clean_text = Formatting.get_elements_from_markdown(text)[1]
            elements = [
                MessageElement(type=e.type, length=e.length, from_=e.from_)
                for e in raw_elements
            ]

            payload = EditMessagePayload(
                chat_id=chat_id,
                message_id=message_id,
                text=clean_text if clean_text else text,
                elements=elements,
                attaches=attaches,
            ).model_dump(by_alias=True)

            if use_queue:
                await self._queue_message(
                    opcode=Opcode.MSG_EDIT, payload=payload
                )
                self.logger.debug("Edit message queued for sending")
                return None
            else:
                data = await self._send_and_wait(
                    opcode=Opcode.MSG_EDIT, payload=payload
                )
                if error := data.get("payload", {}).get("error"):
                    self.logger.error("Edit message error: %s", error)
                msg = (
                    Message.from_dict(data["payload"])
                    if data.get("payload")
                    else None
                )
                self.logger.debug("edit_message result: %r", msg)
                return msg
        except Exception:
            self.logger.exception("Edit message failed")
            return None

    async def delete_message(
        self,
        chat_id: int,
        message_ids: list[int],
        for_me: bool,
        use_queue: bool = False,
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

            if use_queue:
                await self._queue_message(
                    opcode=Opcode.MSG_DELETE, payload=payload
                )
                self.logger.debug("Delete message queued for sending")
                return True
            else:
                data = await self._send_and_wait(
                    opcode=Opcode.MSG_DELETE, payload=payload
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
                opcode=Opcode.CHAT_UPDATE, payload=payload
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
                from_time=from_time,
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
                Message.from_dict(msg)
                for msg in data["payload"].get("messages", [])
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
            self.logger.info(
                "Getting video_id=%s message_id=%s", video_id, message_id
            )

            if self.is_connected and self._socket is not None:
                payload = GetVideoPayload(
                    chat_id=chat_id, message_id=message_id, video_id=video_id
                ).model_dump(by_alias=True)
            else:
                payload = GetVideoPayload(
                    chat_id=chat_id,
                    message_id=str(message_id),
                    video_id=video_id,
                ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.VIDEO_PLAY, payload=payload
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get video error: %s", error)
                return None

            video = (
                VideoRequest.from_dict(data["payload"])
                if data.get("payload")
                else None
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
            self.logger.info(
                "Getting file_id=%s message_id=%s", file_id, message_id
            )
            if self.is_connected and self._socket is not None:
                payload = GetFilePayload(
                    chat_id=chat_id, message_id=message_id, file_id=file_id
                ).model_dump(by_alias=True)
            else:
                payload = GetFilePayload(
                    chat_id=chat_id,
                    message_id=str(message_id),
                    file_id=file_id,
                ).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.FILE_DOWNLOAD, payload=payload
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get file error: %s", error)
                return None

            file = (
                FileRequest.from_dict(data["payload"])
                if data.get("payload")
                else None
            )
            self.logger.debug(" result: %r", file)
            return file
        except Exception:
            self.logger.exception("Get video error")
            return None

    async def add_reaction(
        self,
        chat_id: int,
        message_id: str,
        reaction: str,
    ) -> ReactionInfo | None:
        """
        Добавляет реакцию к сообщению.

        Args:
            chat_id (int): ID чата
            message_id (int): ID сообщения
            reaction (str): Реакция (эмодзи)

        Returns:
            ReactionInfo | None: Информация о реакции или None при ошибке.
        """
        try:
            self.logger.info(
                "Adding reaction to message chat_id=%s message_id=%s reaction=%s",
                chat_id,
                message_id,
                reaction,
            )

            payload = AddReactionPayload(
                chat_id=chat_id,
                message_id=message_id,
                reaction=ReactionInfoPayload(id=reaction),
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.MSG_REACTION, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Add reaction error: %s", error)
                return None

            self.logger.debug("add_reaction success")
            return (
                ReactionInfo.from_dict(data["payload"]["reactionInfo"])
                if data.get("payload")
                else None
            )
        except Exception:
            self.logger.exception("Add reaction failed")
            return None

    async def get_reactions(
        self, chat_id: int, message_ids: list[str]
    ) -> dict[str, ReactionInfo] | None:
        """
        Получает реакции на сообщения.

        Args:
            chat_id (int): ID чата
            message_ids (list[str]): Список ID сообщений

        Returns:
            dict[str, ReactionInfo] | None: Словарь с ID сообщений и информацией о реакциях или None при ошибке.
        """
        try:
            self.logger.info(
                "Getting reactions for messages chat_id=%s message_ids=%s",
                chat_id,
                message_ids,
            )

            payload = GetReactionsPayload(
                chat_id=chat_id, message_ids=message_ids
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.MSG_GET_REACTIONS, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Get reactions error: %s", error)
                return None

            reactions = {}
            for msg_id, reaction_data in (
                data.get("payload", {}).get("messagesReactions", {}).items()
            ):
                reactions[msg_id] = ReactionInfo.from_dict(reaction_data)

            self.logger.debug("get_reactions success")

            return reactions

        except Exception:
            self.logger.exception("Get reactions failed")
            return None

    async def remove_reaction(
        self,
        chat_id: int,
        message_id: str,
    ) -> ReactionInfo | None:
        """
        Удаляет реакцию с сообщения.

        Args:
            chat_id (int): ID чата
            message_id (str): ID сообщения

        Returns:
            ReactionInfo | None: Информация о реакции или None при ошибке.
        """
        try:
            self.logger.info(
                "Removing reaction from message chat_id=%s message_id=%s",
                chat_id,
                message_id,
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
                return None

            self.logger.debug("remove_reaction success")
            return (
                ReactionInfo.from_dict(data["payload"]["reactionInfo"])
                if data.get("payload")
                else None
            )
        except Exception:
            self.logger.exception("Remove reaction failed")
            return None

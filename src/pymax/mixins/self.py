import urllib.parse
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import aiohttp

from pymax.exceptions import Error
from pymax.files import Photo
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import (
    ChangeProfilePayload,
    CreateFolderPayload,
    DeleteFolderPayload,
    GetFolderPayload,
    UpdateFolderPayload,
    UploadPayload,
)
from pymax.static.enum import Opcode
from pymax.types import Folder, FolderList, FolderUpdate, Me


class SelfMixin(ClientProtocol):
    async def _request_photo_upload_url(self) -> str:
        self.logger.info("Requesting profile photo upload URL")

        data = await self._send_and_wait(
            opcode=Opcode.PHOTO_UPLOAD,
            payload=UploadPayload(profile=True).model_dump(by_alias=True),
        )

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return data["payload"]["url"]

    async def _upload_profile_photo(self, upload_url: str, photo: Photo) -> str:
        self.logger.info("Uploading profile photo")

        parsed_url = urlparse(upload_url)
        photo_id = parse_qs(parsed_url.query)["photoIds"][0]

        form = aiohttp.FormData()
        form.add_field(
            "file",
            await photo.read(),
            filename=photo.file_name,
        )

        async with (
            aiohttp.ClientSession() as session,
            session.post(upload_url, data=form) as response,
        ):
            if response.status != HTTPStatus.OK:
                raise Error(
                    "Failed to upload profile photo.", message="UploadError", title="Upload Error"
                )

            self.logger.info("Upload successful")
            data = await response.json()
            return data["photos"][photo_id][
                "token"
            ]  # TODO: сделать нормальную типизацию и чекнинг ответа

    async def change_profile(
        self,
        first_name: str,
        last_name: str | None = None,
        description: str | None = None,
        photo: Photo | None = None,
    ) -> bool:
        """
        Изменяет информацию профиля текущего пользователя.

        :param first_name: Имя пользователя.
        :type first_name: str
        :param last_name: Фамилия пользователя. По умолчанию None.
        :type last_name: str | None
        :param description: Описание профиля. По умолчанию None.
        :type description: str | None
        :return: True, если профиль успешно изменен.
        :rtype: bool
        """

        if photo:
            upload_url = await self._request_photo_upload_url()
            photo_token = await self._upload_profile_photo(upload_url, photo)

            payload = ChangeProfilePayload(
                first_name=first_name,
                last_name=last_name,
                description=description,
                photo_token=photo_token,
            ).model_dump(
                by_alias=True,
                exclude_none=True,
            )
        else:
            payload = ChangeProfilePayload(
                first_name=first_name,
                last_name=last_name,
                description=description,
            ).model_dump(
                by_alias=True,
                exclude_none=True,
            )

        data = await self._send_and_wait(opcode=Opcode.PROFILE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        self.me = Me.from_dict(data["payload"]["profile"]["contact"])

        return True

    async def create_folder(
        self, title: str, chat_include: list[int], filters: list[Any] | None = None
    ) -> FolderUpdate:
        """
        Создает новую папку для группировки чатов.

        :param title: Название папки.
        :type title: str
        :param chat_include: Список ID чатов для включения в папку.
        :type chat_include: list[int]
        :param filters: Список фильтров для папки (опциональный параметр).
        :type filters: list[Any] | None
        :return: Объект FolderUpdate с информацией о созданной папке.
        :rtype: FolderUpdate
        """
        self.logger.info("Creating folder")

        payload = CreateFolderPayload(
            id=str(uuid4()),
            title=title,
            include=chat_include,
            filters=filters or [],
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.FOLDERS_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return FolderUpdate.from_dict(data.get("payload", {}))

    async def get_folders(self, folder_sync: int = 0) -> FolderList:
        """
        Получает список всех папок пользователя.

        :param folder_sync: Синхронизационный маркер папок. По умолчанию 0.
        :type folder_sync: int
        :return: Объект FolderList с информацией о папках.
        :rtype: FolderList
        """
        self.logger.info("Fetching folders")

        payload = GetFolderPayload(folder_sync=folder_sync).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.FOLDERS_GET, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return FolderList.from_dict(data.get("payload", {}))

    async def update_folder(
        self,
        folder_id: str,
        title: str,
        chat_include: list[int] | None = None,
        filters: list[Any] | None = None,
        options: list[Any] | None = None,
    ) -> FolderUpdate | None:
        """
        Обновляет параметры существующей папки.

        :param folder_id: Идентификатор папки.
        :type folder_id: str
        :param title: Название папки.
        :type title: str
        :param chat_include: Список ID чатов для включения в папку.
        :type chat_include: list[int] | None
        :param filters: Список фильтров для папки.
        :type filters: list[Any] | None
        :param options: Список опций для папки.
        :type options: list[Any] | None
        :return: Объект FolderUpdate с результатом или None.
        :rtype: FolderUpdate | None
        """
        self.logger.info("Updating folder")

        payload = UpdateFolderPayload(
            id=folder_id,
            title=title,
            include=chat_include or [],
            filters=filters or [],
            options=options or [],
        ).model_dump(by_alias=True, exclude_none=True)

        data = await self._send_and_wait(opcode=Opcode.FOLDERS_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return FolderUpdate.from_dict(data.get("payload", {}))

    async def delete_folder(self, folder_id: str) -> FolderUpdate | None:
        """
        Удаляет папку.

        :param folder_id: Идентификатор папки для удаления.
        :type folder_id: str
        :return: Объект FolderUpdate с результатом операции или None.
        :rtype: FolderUpdate | None
        """
        self.logger.info("Deleting folder")

        payload = DeleteFolderPayload(folder_ids=[folder_id]).model_dump(by_alias=True)
        data = await self._send_and_wait(opcode=Opcode.FOLDERS_DELETE, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return FolderUpdate.from_dict(data.get("payload", {}))

    async def close_all_sessions(self) -> bool:
        """
        Закрывает все активные сессии, кроме текущей.

        :return: True, если операция выполнена успешно.
        :rtype: bool
        """
        self.logger.info("Closing all other sessions")

        data = await self._send_and_wait(opcode=Opcode.SESSIONS_CLOSE, payload={})

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return True

    async def logout(self) -> bool:
        """
        Выполняет выход из текущей сессии.

        :return: True, если выход выполнен успешно.
        :rtype: bool
        """
        self.logger.info("Logging out")

        data = await self._send_and_wait(opcode=Opcode.LOGOUT, payload={})

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return True

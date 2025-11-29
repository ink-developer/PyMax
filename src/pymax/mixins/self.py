from typing import Any
from uuid import uuid4

from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import (
    ChangeProfilePayload,
    CreateFolderPayload,
    DeleteFolderPayload,
    GetFolderPayload,
    UpdateFolderPayload,
)
from pymax.static.enum import Opcode
from pymax.types import Folder, FolderList, FolderUpdate


class SelfMixin(ClientProtocol):
    async def change_profile(
        self,
        first_name: str,
        last_name: str | None = None,
        description: str | None = None,
    ) -> bool:
        """
        Изменяет профиль

        Args:
            first_name (str): Имя.
            last_name (str | None, optional): Фамилия. Defaults to None.
            description (str | None, optional): Описание. Defaults to None.

        Returns:
            bool: True, если профиль изменен
        """

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

        return True

    async def create_folder(
        self, title: str, chat_include: list[int], filters: list[Any] | None = None
    ) -> FolderUpdate:
        """
        Создает папку для чатов

        Args:
            title (str): Название папки
            chat_include (list[int]): Список ID чатов для включения в папку
            filters (list[Any] | None, optional): Список фильтров для папки (Неизвестный параметр, использование на свой страх и риск)

        Returns:
            bool: True, если папка создана
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
        Получает список папок
        Args:
            folder_sync (int, optional): Синхронизационный маркер папок. По умолчанию 0. (Неизвестный параметр, использование на свой страх и риск)
        Returns:
            FolderList: Список папок
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
    ):
        """
        Обновляет папку для чатов

        Args:
            folder_id (str): ID папки
            title (str): Название папки
            chat_include (list[int] | None, optional): Список ID чатов для включения в папку. По умолчанию None.
            filters (list[Any] | None, optional): Список фильтров для папки. По умолчанию None.
            options (list[Any] | None, optional): Список опций для папки. По умолчанию None.
        Returns:
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

    async def delete_folder(self, folder_id: str) -> FolderUpdate:
        """
        Удаляет папку для чатов

        Args:
            folder_id (str): ID папки

        Returns:
            bool: True, если папка удалена
        """
        self.logger.info("Deleting folder")

        payload = DeleteFolderPayload(folder_ids=[folder_id]).model_dump(by_alias=True)
        data = await self._send_and_wait(opcode=Opcode.FOLDERS_DELETE, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return FolderUpdate.from_dict(data.get("payload", {}))

import time

from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import (
    ChangeGroupProfilePayload,
    ChangeGroupSettingsOptions,
    ChangeGroupSettingsPayload,
    CreateGroupAttach,
    CreateGroupMessage,
    CreateGroupPayload,
    FetchChatsPayload,
    GetChatInfoPayload,
    InviteUsersPayload,
    JoinChatPayload,
    LeaveChatPayload,
    RemoveUsersPayload,
    ReworkInviteLinkPayload,
)
from pymax.static.enum import Opcode
from pymax.types import Chat, Message


class GroupMixin(ClientProtocol):
    async def create_group(
        self,
        name: str,
        participant_ids: list[int] | None = None,
        notify: bool = True,
    ) -> tuple[Chat, Message] | None:
        """
        Создает группу

        Args:
            name (str): Название группы.
            participant_ids (list[int] | None, optional): Список идентификаторов участников. Defaults to None.
            notify (bool, optional): Флаг оповещения. Defaults to True.

        Returns:
            tuple[Chat, Message] | None: Объект Chat и Message или None при ошибке.
        """
        payload = CreateGroupPayload(
            message=CreateGroupMessage(
                cid=int(time.time() * 1000),
                attaches=[
                    CreateGroupAttach(
                        _type="CONTROL",
                        title=name,
                        user_ids=(participant_ids if participant_ids else []),
                    )
                ],
            ),
            notify=notify,
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.MSG_SEND, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        message = Message.from_dict(data["payload"])

        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return chat, message

    async def invite_users_to_group(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        """
        Приглашает пользователей в группу

        Args:
            chat_id (int): ID группы.
            user_ids (list[int]): Список идентификаторов пользователей.
            show_history (bool, optional): Флаг оповещения. Defaults to True.

        Returns:
            Chat | None: Объект Chat или None при ошибке.
        """
        payload = InviteUsersPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            show_history=show_history,
            operation="add",
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_MEMBERS_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return chat

    async def invite_users_to_channel(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        """
        Приглашает пользователей в канал

        Args:
            chat_id (int): ID канала.
            user_ids (list[int]): Список идентификаторов пользователей.
            show_history (bool, optional): Флаг оповещения. Defaults to True.

        Returns:
            Chat | None: Объект Chat или None при ошибке.
        """
        return await self.invite_users_to_group(chat_id, user_ids, show_history)

    async def remove_users_from_group(
        self,
        chat_id: int,
        user_ids: list[int],
        clean_msg_period: int,
    ) -> bool:
        """
        Удаляет пользователей из группы

        Args:
            chat_id (int): ID группы.
            user_ids (list[int]): Список идентификаторов пользователей.
            clean_msg_period (int): Период очистки сообщений.

        Returns:
            bool: True, если удаление прошло успешно, иначе False.
        """
        payload = RemoveUsersPayload(
            chat_id=chat_id,
            user_ids=user_ids,
            clean_msg_period=clean_msg_period,
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_MEMBERS_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return True

    async def change_group_settings(
        self,
        chat_id: int,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ) -> None:
        """
        Изменяет настройки группы

        Args:
            chat_id (int): ID группы.
            all_can_pin_message (bool | None, optional): Все могут закреплять сообщения. Defaults to None.
            only_owner_can_change_icon_title (bool | None, optional): Только владелец может менять иконку и название. Defaults to None.
            only_admin_can_add_member (bool | None, optional): Только администраторы могут добавлять участников. Defaults to None.
            only_admin_can_call (bool | None, optional): Только администраторы могут звонить. Defaults to None.
            members_can_see_private_link (bool | None, optional): Участники могут видеть приватную ссылку. Defaults to None.
        Returns:
            None
        """
        payload = ChangeGroupSettingsPayload(
            chat_id=chat_id,
            options=ChangeGroupSettingsOptions(
                ALL_CAN_PIN_MESSAGE=all_can_pin_message,
                ONLY_OWNER_CAN_CHANGE_ICON_TITLE=only_owner_can_change_icon_title,
                ONLY_ADMIN_CAN_ADD_MEMBER=only_admin_can_add_member,
                ONLY_ADMIN_CAN_CALL=only_admin_can_call,
                MEMBERS_CAN_SEE_PRIVATE_LINK=members_can_see_private_link,
            ),
        ).model_dump(by_alias=True, exclude_none=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

    async def change_group_profile(
        self,
        chat_id: int,
        name: str | None,
        description: str | None = None,
    ) -> None:
        """
        Изменяет профиль группы

        Args:
            chat_id (int): ID группы.
            name (str | None): Название группы.
            description (str | None, optional): Описание группы. Defaults to None.

        Returns:
            None
        """
        payload = ChangeGroupProfilePayload(
            chat_id=chat_id,
            theme=name,
            description=description,
        ).model_dump(by_alias=True, exclude_none=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

    def _process_chat_join_link(self, link: str) -> str | None:
        idx = link.find("join/")
        return link[idx:] if idx != -1 else None

    async def join_group(self, link: str) -> Chat:
        """
        Вступает в группу по ссылке

        Args:
            link (str): Ссылка на группу.

        Returns:
            Chat: Объект чата группы
        """
        proceed_link = self._process_chat_join_link(link)
        if proceed_link is None:
            raise ValueError("Invalid group link")

        payload = JoinChatPayload(link=proceed_link).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_JOIN, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"]["chat"])
        if chat:
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return chat

    async def resolve_group_by_link(self, link: str) -> Chat | None:
        """
        Разрешает группу по ссылке

        Args:
            link (str): Ссылка на группу.

        Returns:
            Chat | None: Объект чата группы или None, если не найдено.
        """
        proceed_link = self._process_chat_join_link(link)
        if proceed_link is None:
            raise ValueError("Invalid group link")

        data = await self._send_and_wait(
            opcode=Opcode.LINK_INFO,
            payload={
                "link": proceed_link,
            },
        )

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"].get("chat", {}))
        return chat

    async def rework_invite_link(self, chat_id: int) -> Chat:
        """
        Пересоздает ссылку для приглашения в группу

        Args:
            chat_id (int): ID группы.

        Returns:
            Chat: Обновленный объект чата с новой ссылкой.
        """
        payload = ReworkInviteLinkPayload(chat_id=chat_id).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chat = Chat.from_dict(data["payload"].get("chat"))
        if not chat:
            raise Error("no_chat", "Chat data missing in response", "Chat Error")

        return chat

    async def get_chats(self, chat_ids: list[int]) -> list[Chat]:
        """
        Получает информацию о группах по их ID

        :param chat_ids: Список идентификаторов групп.
        :type chat_ids: list[int]
        :return: Список объектов Chat.
        :rtype: list[Chat]
        """
        missed_chat_ids = [
            chat_id for chat_id in chat_ids if await self._get_chat(chat_id) is None
        ]
        if missed_chat_ids:
            payload = GetChatInfoPayload(chat_ids=missed_chat_ids).model_dump(by_alias=True)
        else:
            chats: list[Chat] = [
                chat for chat_id in chat_ids if (chat := await self._get_chat(chat_id)) is not None
            ]
            return chats

        data = await self._send_and_wait(opcode=Opcode.CHAT_INFO, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chats_data = data["payload"].get("chats", [])
        chats: list[Chat] = []
        for chat_dict in chats_data:
            chat = Chat.from_dict(chat_dict)
            chats.append(chat)
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return chats

    async def get_chat(self, chat_id: int) -> Chat:
        """
        Получает информацию о группе по ее ID

        Args:
            chat_id (int): Идентификатор группы.

        Returns:
            Chat: Объект Chat.
        """
        chats = await self.get_chats([chat_id])
        if not chats:
            raise Error("no_chat", "Chat not found in response", "Chat Error")
        return chats[0]

    async def leave_group(self, chat_id: int) -> None:
        """
        Покидает группу

        :param chat_id: Идентификатор группы.
        :type chat_id: int
        :return: None
        :rtype: None
        """
        payload = LeaveChatPayload(chat_id=chat_id).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_LEAVE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        cached_chat = await self._get_chat(chat_id)
        if cached_chat is not None:
            self.chats.remove(cached_chat)

    async def leave_channel(self, chat_id: int) -> None:
        """
        Покидает канал

        :param chat_id: Идентификатор канала.
        :type chat_id: int
        :return: None
        :rtype: None
        """
        await self.leave_group(chat_id)

    async def fetch_chats(self, marker: int | None = None) -> list[Chat]:
        """
        Загружает список чатов

        :param marker: Маркер для пагинации, по умолчанию None
        :type marker: int | None
        :return: Список объектов Chat
        :rtype: list[Chat]
        """
        if marker is None:
            marker = int(time.time() * 1000)

        payload = FetchChatsPayload(marker=marker).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHATS_LIST, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        chats_data = data["payload"].get("chats", [])
        chats: list[Chat] = []
        for chat_dict in chats_data:
            chat = Chat.from_dict(chat_dict)
            chats.append(chat)
            cached_chat = await self._get_chat(chat.id)
            if cached_chat is None:
                self.chats.append(chat)
            else:
                idx = self.chats.index(cached_chat)
                self.chats[idx] = chat

        return chats

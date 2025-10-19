import time

from pymax.interfaces import ClientProtocol
from pymax.payloads import (
    ChangeGroupProfilePayload,
    ChangeGroupSettingsOptions,
    ChangeGroupSettingsPayload,
    CreateGroupAttach,
    CreateGroupMessage,
    CreateGroupPayload,
    InviteUsersPayload,
    JoinGroupPayload,
    RemoveUsersPayload,
    ReworkInviteLinkPayload,
)
from pymax.static import Opcode
from pymax.types import Chat, Message


class GroupMixin(ClientProtocol):
    async def create_group(
        self, name: str, participant_ids: list[int] | None = None, notify: bool = True
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
        try:
            payload = CreateGroupPayload(
                message=CreateGroupMessage(
                    cid=int(time.time() * 1000),
                    attaches=[
                        CreateGroupAttach(
                            _type="CONTROL",
                            title=name,
                            user_ids=participant_ids if participant_ids else [],
                        )
                    ],
                ),
                notify=notify,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.MSG_SEND, payload=payload)
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Create group error: %s", error)
                return None

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

        except Exception:
            self.logger.exception("Create group failed")

    async def invite_users_to_group(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> bool:
        """
        Приглашает пользователей в группу

        Args:
            chat_id (int): ID группы.
            user_ids (list[int]): Список идентификаторов пользователей.
            show_history (bool, optional): Флаг оповещения. Defaults to True.

        Returns:
            bool: True, если пользователи успешно приглашены
        """
        try:
            payload = InviteUsersPayload(
                chat_id=chat_id,
                user_ids=user_ids,
                show_history=show_history,
                operation="add",
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.CHAT_MEMBERS_UPDATE, payload=payload
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Create group error: %s", error)
                return False

            chat = Chat.from_dict(data["payload"]["chat"])
            if chat:
                cached_chat = await self._get_chat(chat.id)
                if cached_chat is None:
                    self.chats.append(chat)
                else:
                    idx = self.chats.index(cached_chat)
                    self.chats[idx] = chat

            return True

        except Exception:
            self.logger.exception("Invite users to group failed")
            return False

    async def remove_users_from_group(
        self,
        chat_id: int,
        user_ids: list[int],
        clean_msg_period: int,
    ) -> bool:
        try:
            payload = RemoveUsersPayload(
                chat_id=chat_id,
                user_ids=user_ids,
                clean_msg_period=clean_msg_period,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.CHAT_MEMBERS_UPDATE, payload=payload
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Remove users from group error: %s", error)
                return False

            chat = Chat.from_dict(data["payload"]["chat"])
            if chat:
                cached_chat = await self._get_chat(chat.id)
                if cached_chat is None:
                    self.chats.append(chat)
                else:
                    idx = self.chats.index(cached_chat)
                    self.chats[idx] = chat

            return True
        except Exception:
            self.logger.exception("Remove users from group failed")
            return False

    async def change_group_settings(
        self,
        chat_id: int,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ):
        try:
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

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Change group settings error: %s", error)
                return

            chat = Chat.from_dict(data["payload"]["chat"])
            if chat:
                cached_chat = await self._get_chat(chat.id)
                if cached_chat is None:
                    self.chats.append(chat)
                else:
                    idx = self.chats.index(cached_chat)
                    self.chats[idx] = chat

        except Exception:
            self.logger.exception("Change group settings failed")

    async def change_group_profile(
        self,
        chat_id: int,
        name: str | None,
        description: str | None = None,
    ):
        try:
            payload = ChangeGroupProfilePayload(
                chat_id=chat_id,
                theme=name,
                description=description,
            ).model_dump(by_alias=True, exclude_none=True)

            data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Change group profile error: %s", error)
                return

            chat = Chat.from_dict(data["payload"]["chat"])
            if chat:
                cached_chat = await self._get_chat(chat.id)
                if cached_chat is None:
                    self.chats.append(chat)
                else:
                    idx = self.chats.index(cached_chat)
                    self.chats[idx] = chat

        except Exception:
            self.logger.exception("Change group profile failed")

    def _process_chat_join_link(self, link: str) -> str | None:
        idx = link.find("join/")
        return link[idx:] if idx != -1 else None

    async def join_group(self, link: str) -> Chat | None:
        """
        Вступает в группу по ссылке

        Args:
            link (str): Ссылка на группу.

        Returns:
            bool: True, если успешно вступил в группу
        """
        try:
            proceed_link = self._process_chat_join_link(link)
            if proceed_link is None:
                self.logger.error("Invalid group link: %s", link)
                return None

            payload = JoinGroupPayload(link=proceed_link).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.CHAT_JOIN, payload=payload)

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Join group error: %s", error)
                return None

            chat = Chat.from_dict(data["payload"]["chat"])
            if chat:
                cached_chat = await self._get_chat(chat.id)
                if cached_chat is None:
                    self.chats.append(chat)
                else:
                    idx = self.chats.index(cached_chat)
                    self.chats[idx] = chat

            return chat

        except Exception:
            self.logger.exception("Join group failed")
            return None

    async def rework_invite_link(self, chat_id: int) -> Chat | None:
        """
        Пересоздает ссылку для приглашения в группу

        Args:
            chat_id (int): ID группы.

        Returns:
            str | None: Новая ссылка или None при ошибке.
        """
        try:
            payload = ReworkInviteLinkPayload(chat_id=chat_id).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.CHAT_UPDATE, payload=payload)

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Rework invite link error: %s", error)
                return None

            return Chat.from_dict(data["payload"].get("chat"))

        except Exception:
            self.logger.exception("Rework invite link failed")
            return None

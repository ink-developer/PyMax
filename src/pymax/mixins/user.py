from typing import Any, Literal

from pymax.exceptions import ResponseError, ResponseStructureError
from pymax.interfaces import ClientProtocol
from pymax.payloads import (
    ContactActionPayload,
    FetchContactsPayload,
    SearchByPhonePayload,
)
from pymax.static.enum import ContactAction, Opcode
from pymax.types import Contact, Session, User


class UserMixin(ClientProtocol):
    def get_cached_user(self, user_id: int) -> User | None:
        """
        Получает юзера из кеша по его ID

        Args:
            user_id (int): ID пользователя.

        Returns:
            User | None: Объект User или None при ошибке.
        """
        user = self._users.get(user_id)
        self.logger.debug("get_cached_user id=%s hit=%s", user_id, bool(user))
        return user

    async def get_users(self, user_ids: list[int]) -> list[User]:
        """
        Получает информацию о пользователях по их ID (с кешем).
        """
        self.logger.debug("get_users ids=%s", user_ids)
        cached = {
            uid: self._users[uid] for uid in user_ids if uid in self._users
        }
        missing_ids = [uid for uid in user_ids if uid not in self._users]

        if missing_ids:
            self.logger.debug("Fetching missing users: %s", missing_ids)
            fetched_users = await self.fetch_users(missing_ids)
            if fetched_users:
                for user in fetched_users:
                    self._users[user.id] = user
                    cached[user.id] = user

        ordered = [cached[uid] for uid in user_ids if uid in cached]
        self.logger.debug("get_users result_count=%d", len(ordered))
        return ordered

    async def get_user(self, user_id: int) -> User | None:
        """
        Получает информацию о пользователе по его ID (с кешем).
        """
        self.logger.debug("get_user id=%s", user_id)
        if user_id in self._users:
            return self._users[user_id]

        users = await self.fetch_users([user_id])
        if users:
            self._users[user_id] = users[0]
            return users[0]
        return None

    async def fetch_users(self, user_ids: list[int]) -> None | list[User]:
        """
        Получает информацию о пользователях по их ID.
        """
        try:
            self.logger.info("Fetching users count=%d", len(user_ids))

            payload = FetchContactsPayload(contact_ids=user_ids).model_dump(
                by_alias=True
            )

            data = await self._send_and_wait(
                opcode=Opcode.CONTACT_INFO, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Fetch users error: %s", error)
                return None

            users = [
                User.from_dict(u) for u in data["payload"].get("contacts", [])
            ]
            for user in users:
                self._users[user.id] = user

            self.logger.debug("Fetched users: %d", len(users))
            return users
        except Exception:
            self.logger.exception("Fetch users failed")
            return []

    async def search_by_phone(self, phone: str) -> User | None:
        """
        Ищет пользователя по номеру телефона.

        Args:
            phone (str): Номер телефона.

        Returns:
            User | None: Объект User или None при ошибке.
        """
        try:
            self.logger.info("Searching user by phone: %s", phone)

            payload = SearchByPhonePayload(phone=phone).model_dump(
                by_alias=True
            )

            data = await self._send_and_wait(
                opcode=Opcode.CONTACT_INFO_BY_PHONE, payload=payload
            )
            if error := data.get("payload", {}).get("error"):
                self.logger.error("Search by phone error: %s", error)
                return None

            user = (
                User.from_dict(data["payload"]["contact"])
                if data.get("payload")
                else None
            )
            if user:
                self._users[user.id] = user
                self.logger.debug("Found user by phone: %s", user)
            return user
        except Exception:
            self.logger.exception("Search by phone failed")
            return None

    async def get_sessions(self) -> list[Session] | None:
        try:
            self.logger.info("Fetching sessions")

            data = await self._send_and_wait(
                opcode=Opcode.SESSIONS_INFO, payload={}
            )

            if error := data.get("payload", {}).get("error"):
                self.logger.error("Fetching sessions error: %s", error)
                return None

            return [
                Session.from_dict(s)
                for s in data["payload"].get("sessions", [])
            ]

        except Exception:
            self.logger.exception("Fetching sessions failed")
            return None

    async def _contact_action(
        self, payload: ContactActionPayload
    ) -> dict[str, Any]:
        """
        Действия с контактом

        Args:
            payload (ContactActionPayload): Полезная нагрузка

        Return:
            Полезная нагрузка ответа
        """
        data = await self._send_and_wait(
            opcode=Opcode.CONTACT_UPDATE,  # 34
            payload=payload.model_dump(by_alias=True),
        )
        response_payload = data.get("payload")
        if not isinstance(response_payload, dict):
            raise ResponseStructureError("Invalid response structure")
        if error := response_payload.get("error"):
            raise ResponseError(error)
        return response_payload

    async def add_contact(self, contact_id: int) -> Contact:
        """
        Добавляет контакт в список контактов

        Args:
            contact_id (int): ID контакта

        Returns:
            Contact: Объект контакта, иначе будут выброшены исключения
        """
        payload = await self._contact_action(
            ContactActionPayload(
                contact_id=contact_id, action=ContactAction.ADD
            )
        )
        contact_dict = payload.get("contact")
        if isinstance(contact_dict, dict):
            return Contact.from_dict(contact_dict)
        raise ResponseStructureError("Wrong contact structure in response")

    async def remove_contact(self, contact_id: int) -> Literal[True]:
        """
        Удаляет контакт из списка контактов

        Args:
            contact_id (int): ID контакта

        Returns:
            True если успешно, иначе будут выброшены исключения
        """
        await self._contact_action(
            ContactActionPayload(
                contact_id=contact_id, action=ContactAction.REMOVE
            )
        )
        return True

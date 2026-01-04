from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Literal

from pymax.exceptions import Error, ResponseError, ResponseStructureError
from pymax.payloads import (
    AddContactByPhonePayload,
    ContactActionPayload,
    ContactPresencePayload,
    FetchContactsPayload,
    SearchByPhonePayload,
    SetTypingPayload,
)
from pymax.protocols import ClientProtocol
from pymax.static.enum import ContactAction, Opcode, TypingType
from pymax.types import Contact, Presence, Session, User
from pymax.utils import MixinsUtils


class UserMixin(ClientProtocol):
    def get_cached_user(self, user_id: int) -> User | None:
        """
        Получает пользователя из кеша по его идентификатору.

        Проверяет внутренний кеш пользователей и возвращает объект User
        если пользователь был ранее загружен.

        :param user_id: Идентификатор пользователя.
        :type user_id: int
        :return: Объект User из кеша или None, если пользователь не найден.
        :rtype: User | None
        """
        user = self._users.get(user_id)
        self.logger.debug("get_cached_user id=%s hit=%s", user_id, bool(user))
        return user

    async def get_users(self, user_ids: list[int]) -> list[User]:
        """
        Получает информацию о пользователях по их идентификаторам.

        Метод использует внутренний кеш для избежания повторных запросов.
        Если пользователь уже загружен, берется из кеша, иначе выполняется
        сетевой запрос к серверу.

        :param user_ids: Список идентификаторов пользователей.
        :type user_ids: list[int]
        :return: Список объектов User в порядке, соответствующем входному списку.
        :rtype: list[User]
        """
        self.logger.debug("get_users ids=%s", user_ids)
        cached = {uid: self._users[uid] for uid in user_ids if uid in self._users}
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
        Получает информацию о пользователе по его идентификатору.

        Метод использует внутренний кеш. Если пользователь уже загружен,
        возвращает его из кеша, иначе выполняет запрос к серверу.

        :param user_id: Идентификатор пользователя.
        :type user_id: int
        :return: Объект User или None, если пользователь не найден.
        :rtype: User | None
        """
        self.logger.debug("get_user id=%s", user_id)
        if user_id in self._users:
            return self._users[user_id]

        users = await self.fetch_users([user_id])
        if users:
            self._users[user_id] = users[0]
            return users[0]
        return None

    async def fetch_users(self, user_ids: list[int]) -> list[User]:
        """
        Загружает информацию о пользователях с сервера.

        Запрашивает данные о пользователях по их идентификаторам и добавляет
        их в внутренний кеш.

        :param user_ids: Список идентификаторов пользователей для загрузки.
        :type user_ids: list[int]
        :return: Список загруженных объектов User.
        :rtype: list[User]
        """
        self.logger.info("Fetching users count=%d", len(user_ids))

        payload = FetchContactsPayload(contact_ids=user_ids).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CONTACT_INFO, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        users = [User.from_dict(u) for u in data["payload"].get("contacts", [])]
        for user in users:
            self._users[user.id] = user

        self.logger.debug("Fetched users: %d", len(users))
        return users

    async def search_by_phone(self, phone: str) -> User:
        """
        Выполняет поиск пользователя по номеру телефона.

        :param phone: Номер телефона пользователя.
        :type phone: str
        :return: Объект User с найденными данными пользователя.
        :rtype: User
        :raises Error: Если пользователь не найден или произошла ошибка.
        """
        self.logger.info("Searching user by phone: %s", phone)

        payload = SearchByPhonePayload(phone=phone).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CONTACT_INFO_BY_PHONE, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        if not data.get("payload"):
            raise Error("no_payload", "No payload in response", "User Error")

        user = User.from_dict(data["payload"]["contact"])
        if not user:
            raise Error("no_user", "User data missing in response", "User Error")

        self._users[user.id] = user
        self.logger.debug("Found user by phone: %s", user)
        return user

    async def get_sessions(self) -> list[Session]:
        """
        Получает информацию о всех активных сессиях пользователя.

        Возвращает список всех сессий, в которых авторизован пользователь.

        :return: Список объектов Session.
        :rtype: list[Session]
        :raises Error: Если произошла ошибка при получении данных.
        """
        self.logger.info("Fetching sessions")

        data = await self._send_and_wait(opcode=Opcode.SESSIONS_INFO, payload={})

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        if not data.get("payload"):
            raise Error("no_payload", "No payload in response", "Session Error")

        return [Session.from_dict(s) for s in data["payload"].get("sessions", [])]

    async def _contact_action(self, payload: ContactActionPayload) -> dict[str, Any]:
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

        :param contact_id: ID контакта
        :type contact_id: int
        :return: Объект контакта
        :rtype: Contact
        :raises ResponseStructureError: Если структура ответа неверна
        """
        payload = await self._contact_action(
            ContactActionPayload(contact_id=contact_id, action=ContactAction.ADD)
        )
        contact_dict = payload.get("contact")
        if isinstance(contact_dict, dict):
            return Contact.from_dict(contact_dict)
        raise ResponseStructureError("Wrong contact structure in response")

    async def add_contact_by_phone(self, phone: str, first_name: str) -> Contact:
        """
        Добавляет контакт в список контактов по номеру телефона

        :param phone: Номер телефона контакта
        :type phone: str
        :param first_name: Имя контакта
        :type first_name: str
        :return: Объект контакта
        :rtype: Contact
        :raises ResponseStructureError: Если структура ответа неверна

        """

        payload = AddContactByPhonePayload(phone=phone, first_name=first_name).model_dump(
            by_alias=True
        )

        data = await self._send_and_wait(
            opcode=Opcode.CONTACT_ADD_BY_PHONE,
            payload=payload,
        )

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        return Contact.from_dict(data["payload"]["contact"])

    async def remove_contact(self, contact_id: int) -> Literal[True]:
        """
        Удаляет контакт из списка контактов

        :param contact_id: ID контакта
        :type contact_id: int
        :return: True если успешно
        :rtype: Literal[True]
        :raises ResponseStructureError: Если структура ответа неверна
        """
        await self._contact_action(
            ContactActionPayload(contact_id=contact_id, action=ContactAction.REMOVE)
        )
        return True

    def get_chat_id(self, first_user_id: int, second_user_id: int) -> int:
        """
        Получение айди лс (диалога)

        :param first_user_id: ID первого пользователя
        :type first_user_id: int
        :param second_user_id: ID второго пользователя
        :type second_user_id: int
        :return: Айди диалога
        :rtype: int
        """
        return first_user_id ^ second_user_id

    async def get_contact_presence(self, contact_ids: list[int]) -> list[Presence]:
        """
        Получение информации о присутствии контактов в сети.

        :param contact_ids: Список идентификаторов контактов.
        :type contact_ids: list[int]
        """
        payload = ContactPresencePayload(contact_ids=contact_ids).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CONTACT_PRESENCE, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        presence = data["payload"].get("presence", {})

        return [
            Presence(user_id=int(contact_id), last_seen=info.get("seen"))
            for contact_id, info in presence.items()
        ]

    @asynccontextmanager
    async def typing(
        self, chat_id: int, typing_type: TypingType = TypingType.TEXT
    ) -> AsyncGenerator[None, Any]:
        """
        Устанавливает состояние "печатает" для указанного чата.

        :param chat_id: ID чата.
        :type chat_id: int
        :param typing_type: Тип состояния "печатает".
        :type typing_type: TypingType
        :yields: None
        :rtype: None
        """
        self.logger.debug("Set typing for chat %s", chat_id)

        payload = SetTypingPayload(
            chat_id=chat_id,
            type=typing_type,
        ).model_dump(by_alias=True)
        await self._send_only(opcode=Opcode.MSG_TYPING, payload=payload)
        self.logger.debug("Set typing for chat %s success (maybe?)", chat_id)
        yield
        self.logger.debug("Set typing for chat %s done", chat_id)

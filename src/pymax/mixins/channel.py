from pymax.exceptions import Error, ResponseError, ResponseStructureError
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import (
    GetGroupMembersPayload,
    JoinChatPayload,
    ResolveLinkPayload,
    SearchGroupMembersPayload,
)
from pymax.static.constant import (
    DEFAULT_CHAT_MEMBERS_LIMIT,
    DEFAULT_MARKER_VALUE,
)
from pymax.static.enum import Opcode
from pymax.types import Member


class ChannelMixin(ClientProtocol):
    async def resolve_channel_by_name(self, name: str) -> bool:
        """
        Пытается найти канал по его имени

        Args:
            name (str): Имя канала

        Exceptions:
            ResponseError: Ошибка в ответе сервера
            ResponseStructureError: Ошибка структуры ответа сервера

        Returns:
            bool: True, если канал найден
        """
        payload = ResolveLinkPayload(
            link=f"https://max.ru/{name}",
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.LINK_INFO, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)
        return True

    async def join_channel(self, link: str) -> bool:
        """
        Присоединяется к каналу по ссылке

        Args:
            link (str): Ссылка на канал

        Exceptions:
            ResponseError: Ошибка в ответе сервера
            ResponseStructureError: Ошибка структуры ответа сервера

        Returns:
            bool: True, если присоединение прошло успешно
        """
        payload = JoinChatPayload(
            link=link,
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.CHAT_JOIN, payload=payload)
        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)
        return True

    async def _query_members(
        self, payload: GetGroupMembersPayload | SearchGroupMembersPayload
    ) -> tuple[list[Member], int | None]:
        data = await self._send_and_wait(
            opcode=Opcode.CHAT_MEMBERS,
            payload=payload.model_dump(by_alias=True),
        )
        response_payload = data.get("payload", {})
        if error := response_payload.get("error"):
            raise ResponseError(error)
        marker = response_payload.get("marker")
        if isinstance(marker, str):
            marker = int(marker)
        elif isinstance(marker, int):
            pass
        elif marker is None:
            # маркер может отсутствовать
            pass
        else:
            raise ResponseStructureError("Invalid marker type in response")
        members = response_payload.get("members")
        member_list = []
        if isinstance(members, list):
            for item in members:
                if not isinstance(item, dict):
                    raise ResponseStructureError("Invalid member structure in response")
                member_list.append(Member.from_dict(item))
        else:
            raise ResponseStructureError("Invalid members type in response")
        return member_list, marker

    async def load_members(
        self,
        chat_id: int,
        marker: int = DEFAULT_MARKER_VALUE,
        count: int = DEFAULT_CHAT_MEMBERS_LIMIT,
    ) -> tuple[list[Member], int | None]:
        """
        Загружает членов канала

        Args:
            chat_id (int): Идентификатор канала
            marker (int, optional): Маркер для пагинации. По умолчанию DEFAULT_MARKER_VALUE
            count (int, optional): Количество членов для загрузки. По умолчанию DEFAULT_CHAT_MEMBERS_LIMIT.
            Данное значение лучше не менять, так как веб-клиент загружает именно столько.

        Returns:
            list[Member]: Список участников канала
        """
        payload = GetGroupMembersPayload(chat_id=chat_id, marker=marker, count=count)
        return await self._query_members(payload)

    async def find_members(
        self, chat_id: int, query: str
    ) -> tuple[list[Member], int | None]:
        """
        Поиск участников канала по строке
        Внимание! веб-клиент всегда возвращает только определённое количество пользователей,
        тоесть пагинация здесь не реализована!

        Args:
            chat_id (int): Идентификатор канала
            query (str): Строка для поиска участников

        Returns:
            list[Member]: Список участников канала
        """
        payload = SearchGroupMembersPayload(chat_id=chat_id, query=query)
        return await self._query_members(payload)

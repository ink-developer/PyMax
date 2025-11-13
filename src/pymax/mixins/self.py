from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import ChangeProfilePayload
from pymax.static.enum import Opcode


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

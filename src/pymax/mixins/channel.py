from pymax.interfaces import ClientProtocol
from pymax.payloads import ResolveLinkPayload
from pymax.static.enum import Opcode


class ChannelMixin(ClientProtocol):
    async def resolve_channel_by_name(self, name: str) -> bool:
        """
        Пытается найти канал по его имени

        Args:
            name (str): Имя канала

        Returns:
            bool: True, если канал найден
        """
        payload = ResolveLinkPayload(
            link=f"https://max.ru/{name}",
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(
            opcode=Opcode.LINK_INFO, payload=payload
        )
        if error := data.get("payload", {}).get("error"):
            self.logger.error("Resolve link error: %s", error)
            return False
        return True

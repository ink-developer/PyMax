from re import Pattern, compile
from typing import Final

from websockets.typing import Origin

from pymax.payloads import UserAgentPayload

PHONE_REGEX: Final[Pattern[str]] = compile(r"^\+?\d{10,15}$")
WEBSOCKET_URI: Final[str] = "wss://ws-api.oneme.ru/websocket"
WEBSOCKET_ORIGIN: Final[Origin] = Origin("https://web.max.ru")
HOST: Final[str] = "api.oneme.ru"
PORT: Final[int] = 443
DEFAULT_TIMEOUT: Final[float] = 10.0
DEFAULT_USER_AGENT: Final[UserAgentPayload] = UserAgentPayload()

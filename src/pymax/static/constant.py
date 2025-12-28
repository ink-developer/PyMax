from re import Pattern, compile
from typing import Final

from websockets.typing import Origin

PHONE_REGEX: Final[Pattern[str]] = compile(r"^\+?\d{10,15}$")
WEBSOCKET_URI: Final[str] = "wss://ws-api.oneme.ru/websocket"
WEBSOCKET_ORIGIN: Final[Origin] = Origin("https://web.max.ru")
HOST: Final[str] = "api.oneme.ru"
PORT: Final[int] = 443
DEFAULT_TIMEOUT: Final[float] = 20.0
DEFAULT_DEVICE_TYPE: Final[str] = "DESKTOP"
DEFAULT_LOCALE: Final[str] = "ru"
DEFAULT_DEVICE_LOCALE: Final[str] = "ru"
DEFAULT_DEVICE_NAME: Final[str] = "Chrome"
DEFAULT_APP_VERSION: Final[str] = "25.12.14"
DEFAULT_SCREEN: Final[str] = "1080x1920 1.0x"
DEFAULT_OS_VERSION: Final[str] = "Linux"
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
DEFAULT_BUILD_NUMBER: Final[int] = 0x97CB
DEFAULT_CLIENT_SESSION_ID: Final[int] = 14
DEFAULT_TIMEZONE: Final[str] = "Europe/Moscow"
DEFAULT_CHAT_MEMBERS_LIMIT: Final[int] = 50
DEFAULT_MARKER_VALUE: Final[int] = 0
DEFAULT_PING_INTERVAL: Final[float] = 30.0
RECV_LOOP_BACKOFF_DELAY: Final[float] = 0.5

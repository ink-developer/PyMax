from random import choice, randint
from re import Pattern, compile
from typing import Final

import ua_generator
from websockets.typing import Origin

from pymax.utils import MixinsUtils

DEVICE_NAMES: Final[list[str]] = [
    "Chrome",
    "Firefox",
    "Edge",
    "Safari",
    "Opera",
    "Vivaldi",
    "Brave",
    "Chromium",
    # os
    "Windows 10",
    "Windows 11",
    "macOS Big Sur",
    "macOS Monterey",
    "macOS Ventura",
    "Ubuntu 20.04",
    "Ubuntu 22.04",
    "Fedora 35",
    "Fedora 36",
    "Debian 11",
]
SCREEN_SIZES: Final[list[str]] = [
    "1920x1080 1.0x",
    "1366x768 1.0x",
    "1440x900 1.0x",
    "1536x864 1.0x",
    "1280x720 1.0x",
    "1600x900 1.0x",
    "1680x1050 1.0x",
    "2560x1440 1.0x",
    "3840x2160 1.0x",
]
OS_VERSIONS: Final[list[str]] = [
    "Windows 10",
    "Windows 11",
    "macOS Big Sur",
    "macOS Monterey",
    "macOS Ventura",
    "Ubuntu 20.04",
    "Ubuntu 22.04",
    "Fedora 35",
    "Fedora 36",
    "Debian 11",
]
TIMEZONES: Final[list[str]] = [
    "Europe/Moscow",
    "Europe/Kaliningrad",
    "Europe/Samara",
    "Asia/Yekaterinburg",
    "Asia/Omsk",
    "Asia/Krasnoyarsk",
    "Asia/Irkutsk",
    "Asia/Yakutsk",
    "Asia/Vladivostok",
    "Asia/Kamchatka",
]


PHONE_REGEX: Final[Pattern[str]] = compile(r"^\+?\d{10,15}$")
WEBSOCKET_URI: Final[str] = "wss://ws-api.oneme.ru/websocket"
SESSION_STORAGE_DB = "session.db"
WEBSOCKET_ORIGIN: Final[Origin] = Origin("https://web.max.ru")
HOST: Final[str] = "api.oneme.ru"
PORT: Final[int] = 443
DEFAULT_TIMEOUT: Final[float] = 20.0
DEFAULT_DEVICE_TYPE: Final[str] = "DESKTOP"
DEFAULT_LOCALE: Final[str] = "ru"
DEFAULT_DEVICE_LOCALE: Final[str] = "ru"
DEFAULT_DEVICE_NAME: Final[str] = choice(DEVICE_NAMES)
DEFAULT_APP_VERSION: Final[str] = "25.12.14"
DEFAULT_SCREEN: Final[str] = "1080x1920 1.0x"
DEFAULT_OS_VERSION: Final[str] = choice(OS_VERSIONS)
DEFAULT_USER_AGENT: Final[str] = ua_generator.generate().text
DEFAULT_BUILD_NUMBER: Final[int] = 0x97CB
DEFAULT_CLIENT_SESSION_ID: Final[int] = randint(1, 15)
DEFAULT_TIMEZONE: Final[str] = choice(TIMEZONES)
DEFAULT_CHAT_MEMBERS_LIMIT: Final[int] = 50
DEFAULT_MARKER_VALUE: Final[int] = 0
DEFAULT_PING_INTERVAL: Final[float] = 30.0
RECV_LOOP_BACKOFF_DELAY: Final[float] = 0.5

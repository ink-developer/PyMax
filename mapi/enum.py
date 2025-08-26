from enum import Enum, IntEnum


class Opcode(IntEnum):
    PING = 1
    STATS = 5
    HANDSHAKE = 6
    PROFILE = 16
    REQUEST_CODE = 17
    SEND_CODE = 18
    SYNC = 19
    UNKNOWN_26 = 26
    SYNC_STICKERS_EMOJIS = 27
    GET_EMOJIS_BY_ID = 28
    GET_CONTACTS_INFO = 32
    GET_LAST_SEEN = 35
    GET_CHATS_DATA = 48
    FETCH_HISTORY = 49

    GET_HISTORY = 79

    SEND_MESSAGE = 64
    EDIT_MESSAGE = 67
    DELETE_MESSAGE = 68

    NEW_MESSAGE = 128


class ChatType(str, Enum):
    DIALOG = "DIALOG"
    CHAT = "CHAT"
    CHANNEL = "CHANNEL"


class MessageType(str, Enum):
    TEXT = "TEXT"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"


class MessageStatus(str, Enum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    ERROR = "ERROR"


class ElementType(str, Enum):
    TEXT = "text"
    MENTION = "mention"
    LINK = "link"
    EMOJI = "emoji"


class AuthType(str, Enum):
    START_AUTH = "START_AUTH"
    CHECK_CODE = "CHECK_CODE"


class AccessType(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SECRET = "SECRET"


class DeviceType(str, Enum):
    WEB = "WEB"
    ANDROID = "ANDROID"
    IOS = "IOS"


class Constants(Enum):
    PHONE_REGEX = r"^\+?\d{10,15}$"
    WEBSOCKET_URI = "wss://ws-api.oneme.ru/websocket"
    DEFAULT_TIMEOUT = 10.0
    DEFAULT_USER_AGENT = {
        "deviceType": "WEB",
        "locale": "ru",
        "deviceLocale": "ru",
        "osVersion": "Linux",
        "deviceName": "Chrome",
        "headerUserAgent": "Mozilla/5.0 ...",
        "appVersion": "25.8.5",
        "screen": "1080x1920 1.0x",
        "timezone": "Europe/Moscow",
    }

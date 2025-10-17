"""
Python wrapper для API мессенджера Max
"""

from .core import (
    MaxClient,
    SocketMaxClient,
)
from .exceptions import (
    InvalidPhoneError,
    LoginError,
    WebSocketNotConnectedError,
)
from .static.enum import (
    AccessType,
    AuthType,
    ChatType,
    DeviceType,
    ElementType,
    MessageStatus,
    MessageType,
    Opcode,
)
from .types import (
    Channel,
    Chat,
    Dialog,
    Element,
    Message,
    User,
)

__author__ = "noxzion"

__all__ = [
    # Перечисления и константы
    "AccessType",
    "AuthType",
    # Типы данных
    "Channel",
    "Chat",
    "ChatType",
    "DeviceType",
    "Dialog",
    "Element",
    "ElementType",
    # Исключения
    "InvalidPhoneError",
    "LoginError",
    "WebSocketNotConnectedError",
    # Клиент
    "MaxClient",
    "Message",
    "MessageStatus",
    "MessageType",
    "Opcode",
    "SocketMaxClient",
    "User",
]

"""
Python wrapper для API мессенджера Max
"""

from .core import (
    InvalidPhoneError,
    MaxClient,
    SocketMaxClient,
    WebSocketNotConnectedError,
)
from .static import (
    AccessType,
    AuthType,
    ChatType,
    Constants,
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

__author__ = "ink-developer"

__all__ = [
    # Перечисления и константы
    "AccessType",
    "AuthType",
    # Типы данных
    "Channel",
    "Chat",
    "ChatType",
    "Constants",
    "DeviceType",
    "Dialog",
    "Element",
    "ElementType",
    # Исключения
    "InvalidPhoneError",
    # Клиент
    "MaxClient",
    "Message",
    "MessageStatus",
    "MessageType",
    "Opcode",
    "SocketMaxClient",
    "User",
    "WebSocketNotConnectedError",
]

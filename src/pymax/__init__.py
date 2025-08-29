"""
Python wrapper для API мессенджера Max
"""

from .core import (
    MaxClient,
    InvalidPhoneError,
    WebSocketNotConnectedError,
)
from .types import (
    Channel,
    Chat,
    Dialog,
    Element,
    Message,
    User,
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

__author__ = "noxzion"

__all__ = [
    # Клиент
    "MaxClient",
    
    # Исключения
    "InvalidPhoneError",
    "WebSocketNotConnectedError",
    
    # Типы данных
    "Channel",
    "Chat", 
    "Dialog",
    "Element",
    "Message",
    "User",
    
    # Перечисления и константы
    "AccessType",
    "AuthType",
    "ChatType",
    "Constants",
    "DeviceType",
    "ElementType",
    "MessageStatus",
    "MessageType",
    "Opcode",
]
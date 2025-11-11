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
    ResponseError,
    ResponseStructureError,
    SocketNotConnectedError,
    SocketSendError,
    WebSocketNotConnectedError,
)
from .static.enum import (
    AccessType,
    AttachType,
    AuthType,
    ChatType,
    ContactAction,
    DeviceType,
    ElementType,
    FormattingType,
    MarkupType,
    MessageStatus,
    MessageType,
    Opcode,
)
from .types import (
    Channel,
    Chat,
    Contact,
    ControlAttach,
    Dialog,
    Element,
    FileAttach,
    FileRequest,
    Me,
    Member,
    Message,
    MessageLink,
    Name,
    Names,
    PhotoAttach,
    Presence,
    ReactionCounter,
    ReactionInfo,
    Session,
    User,
    VideoAttach,
    VideoRequest,
)

__author__ = "ink-developer"

__all__ = [
    # Перечисления и константы
    "AccessType",
    "AttachType",
    "AuthType",
    "ContactAction",
    "FormattingType",
    "MarkupType",
    # Типы данных
    "Channel",
    "Chat",
    "ChatType",
    "Contact",
    "ControlAttach",
    "DeviceType",
    "Dialog",
    "Element",
    "ElementType",
    "FileAttach",
    "FileRequest",
    "Me",
    "Member",
    "MessageLink",
    "Name",
    "Names",
    "PhotoAttach",
    "Presence",
    "ReactionCounter",
    "ReactionInfo",
    "Session",
    "VideoAttach",
    "VideoRequest",
    # Исключения
    "InvalidPhoneError",
    "LoginError",
    "WebSocketNotConnectedError",
    "ResponseError",
    "ResponseStructureError",
    "SocketNotConnectedError",
    "SocketSendError",
    # Клиент
    "MaxClient",
    "Message",
    "MessageStatus",
    "MessageType",
    "Opcode",
    "SocketMaxClient",
    "User",
]

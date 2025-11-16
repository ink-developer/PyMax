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
from .files import (
    File,
    Photo,
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
    # Типы данных
    "Channel",
    "Chat",
    "ChatType",
    "Contact",
    "ContactAction",
    "ControlAttach",
    "DeviceType",
    "Dialog",
    "Element",
    "ElementType",
    "File",
    "FileAttach",
    "FileRequest",
    "FormattingType",
    # Исключения
    "InvalidPhoneError",
    "LoginError",
    "MarkupType",
    # Клиент
    "MaxClient",
    "Me",
    "Member",
    "Message",
    "MessageLink",
    "MessageStatus",
    "MessageType",
    "Name",
    "Names",
    "Opcode",
    "Photo",
    "PhotoAttach",
    "Presence",
    "ReactionCounter",
    "ReactionInfo",
    "ResponseError",
    "ResponseStructureError",
    "Session",
    "SocketMaxClient",
    "SocketNotConnectedError",
    "SocketSendError",
    "User",
    "VideoAttach",
    "VideoRequest",
    "WebSocketNotConnectedError",
]

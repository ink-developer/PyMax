from .auth import AuthMixin
from .channel import ChannelMixin
from .handler import HandlerMixin
from .message import MessageMixin
from .self import SelfMixin
from .socket import SocketMixin
from .telemetry import TelemetryMixin
from .user import UserMixin
from .websocket import WebSocketMixin


class ApiMixin(
    AuthMixin,
    HandlerMixin,
    UserMixin,
    ChannelMixin,
    SelfMixin,
    MessageMixin,
    TelemetryMixin,
):
    pass


__all__ = [
    "ApiMixin",
    "AuthMixin",
    "ChannelMixin",
    "HandlerMixin",
    "MessageMixin",
    "SelfMixin",
    "SocketMixin",
    "TelemetryMixin",
    "UserMixin",
    "WebSocketMixin",
]

import asyncio
import socket
import ssl
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import websockets

from pymax.static.constant import DEFAULT_USER_AGENT

from .filters import Filter
from .payloads import UserAgentPayload
from .static.constant import DEFAULT_TIMEOUT
from .static.enum import Opcode
from .types import Channel, Chat, Dialog, Me, Message, User

if TYPE_CHECKING:
    from uuid import UUID

    from .crud import Database


class ClientProtocol(ABC):
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self.logger = logger
        self._users: dict[int, User] = {}
        self.chats: list[Chat] = []
        self._database: Database
        self._device_id: UUID
        self.uri: str
        self.is_connected: bool = False
        self.phone: str
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []
        self.me: Me | None = None
        self.host: str
        self.port: int
        self.proxy: str | Literal[True] | None
        self.registration: bool
        self.first_name: str
        self.last_name: str | None
        self._work_dir: str
        self._database_path: Path
        self._ws: websockets.ClientConnection | None = None
        self._seq: int = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] | None = None
        self._file_upload_waiters: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self.user_agent = UserAgentPayload()
        self._outgoing: asyncio.Queue[dict[str, Any]] | None = None
        self._outgoing_task: asyncio.Task[Any] | None = None
        self._error_count: int = 0
        self._circuit_breaker: bool = False
        self._last_error_time: float = 0.0
        self.user_agent = DEFAULT_USER_AGENT
        self._session_id: int
        self._action_id: int = 0
        self._current_screen: str = "chats_list_tab"
        self._on_message_handlers: list[
            tuple[Callable[[Message], Any], Filter | None]
        ] = []
        self._on_message_edit_handlers: list[
            tuple[Callable[[Message], Any], Filter | None]
        ] = []
        self._on_message_delete_handlers: list[
            tuple[Callable[[Message], Any], Filter | None]
        ] = []
        self._on_start_handler: Callable[[], Any | Awaitable[Any]] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._ssl_context: ssl.SSLContext
        self._socket: socket.socket | None = None

    @abstractmethod
    async def _send_and_wait(
        self,
        opcode: Opcode,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def _get_chat(self, chat_id: int) -> Chat | None:
        pass

    @abstractmethod
    async def _queue_message(
        self,
        opcode: int,
        payload: dict[str, Any],
        cmd: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> Message | None:
        pass

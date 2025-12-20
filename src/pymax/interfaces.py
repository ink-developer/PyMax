import asyncio
import contextlib
import logging
import socket
import ssl
import traceback
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from logging import Logger
from typing import TYPE_CHECKING, Any, Literal

from typing_extensions import Self

from pymax.exceptions import WebSocketNotConnectedError
from pymax.formatter import ColoredFormatter

from .payloads import UserAgentPayload
from .static.constant import DEFAULT_TIMEOUT
from .static.enum import Opcode
from .types import Channel, Chat, Dialog, Me, Message, User

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    import websockets

    from pymax import AttachType
    from pymax.types import ReactionInfo

    from .crud import Database
    from .filters import BaseFilter


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
        self._token: str | None
        self._work_dir: str
        self.reconnect: bool
        self._database_path: Path
        self._ws: websockets.ClientConnection | None = None
        self._seq: int = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] | None = None
        self._file_upload_waiters: dict[
            int,
            asyncio.Future[dict[str, Any]],
        ] = {}
        self.user_agent = UserAgentPayload()
        self._outgoing: asyncio.Queue[dict[str, Any]] | None = None
        self._outgoing_task: asyncio.Task[Any] | None = None
        self._error_count: int = 0
        self._circuit_breaker: bool = False
        self._last_error_time: float = 0.0
        self._session_id: int
        self._action_id: int = 0
        self._current_screen: str = "chats_list_tab"
        self._on_message_handlers: list[
            tuple[Callable[[Message], Any], BaseFilter[Message] | None]
        ] = []
        self._on_message_edit_handlers: list[
            tuple[Callable[[Message], Any], BaseFilter[Message] | None]
        ] = []
        self._on_message_delete_handlers: list[
            tuple[Callable[[Message], Any], BaseFilter[Message] | None]
        ] = []
        self._on_reaction_change_handlers: list[Callable[[str, int, ReactionInfo], Any]] = []
        self._on_chat_update_handlers: list[Callable[[Chat], Any | Awaitable[Any]]] = []
        self._on_raw_receive_handlers: list[Callable[[dict[str, Any]], Any | Awaitable[Any]]] = []
        self._scheduled_tasks: list[tuple[Callable[[], Any | Awaitable[Any]], float]] = []
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

    @abstractmethod
    def _create_safe_task(
        self, coro: Awaitable[Any], name: str | None = None
    ) -> asyncio.Task[Any]:
        pass


class BaseClient(ClientProtocol):
    def _setup_logger(self) -> None:
        if not self.logger.handlers:
            if not self.logger.level:
                self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = ColoredFormatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def _safe_execute(self, coro, *, context: str = "unknown") -> Any:
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Unhandled exception in {context}: {e}\n{traceback.format_exc()}")

    def _create_safe_task(
        self, coro: Awaitable[Any], name: str | None = None
    ) -> asyncio.Task[Any | None]:
        async def runner():
            try:
                return await coro
            except asyncio.CancelledError:
                raise
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(f"Unhandled exception in task {name or coro}: {e}\n{tb}")
                raise

        task = asyncio.create_task(runner(), name=name)
        self._background_tasks.add(task)
        return task

    async def _cleanup_client(self) -> None:
        for task in list(self._background_tasks):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.debug("Background task raised during cancellation", exc_info=True)
            self._background_tasks.discard(task)

        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
            self._recv_task = None

        if self._outgoing_task:
            self._outgoing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._outgoing_task
            self._outgoing_task = None

        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(WebSocketNotConnectedError())
        self._pending.clear()

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                self.logger.debug("Error closing ws during cleanup", exc_info=True)
            self._ws = None

        self.is_connected = False
        self.logger.info("Client start() cleaned up")

    async def idle(self):
        """
        Поддерживает клиента в «ожидающем» состоянии до закрытия клиента или иного прерывающего события.

        :return: Никогда не возвращает значение; функция блокирует выполнение.
        :rtype: None
        """
        await asyncio.Event().wait()

    def inspect(self) -> None:
        """
        Выводит в лог текущий статус клиента для отладки.
        """
        self.logger.info("Pymax")
        self.logger.info("---------")
        self.logger.info(f"Connected: {self.is_connected}")
        if self.me is not None:
            self.logger.info(f"Me: {self.me.names[0].first_name} ({self.me.id})")
        else:
            self.logger.info("Me: N/A")
        self.logger.info(f"Dialogs: {len(self.dialogs)}")
        self.logger.info(f"Chats: {len(self.chats)}")
        self.logger.info(f"Channels: {len(self.channels)}")
        self.logger.info(f"Users cached: {len(self._users)}")
        self.logger.info(f"Background tasks: {len(self._background_tasks)}")
        self.logger.info(f"Scheduled tasks: {len(self._scheduled_tasks)}")
        self.logger.info("---------")

    async def __aenter__(self) -> Self:
        self._create_safe_task(self.start(), name="start")
        while not self.is_connected:
            await asyncio.sleep(0.05)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @abstractmethod
    async def login_with_code(self, temp_token: str, code: str, start: bool = False) -> None:
        pass

    @abstractmethod
    async def _post_login_tasks(self, sync: bool = True) -> None:
        pass

    @abstractmethod
    async def _wait_forever(self) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

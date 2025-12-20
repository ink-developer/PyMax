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
        """
        Initialize the client with the provided logger and prepare internal state.
        
        Sets up internal caches, connection and session fields, placeholders for WebSocket,
        queues and tasks, event handler registries, and default control flags used by the
        client lifecycle.
        """
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
        """
        Create and schedule a background task that runs the given coroutine with guarded exception handling.
        
        The returned task is added to the client's internal background task set. Any exception raised by the coroutine (other than cancellation) is logged along with the task name and traceback; cancellation is propagated so callers can cancel the task normally.
        
        Parameters:
            coro (Awaitable[Any]): Coroutine or awaitable to run in the background.
            name (str | None): Optional human-readable name used in logs to identify the task.
        
        Returns:
            asyncio.Task[Any]: The scheduled background task.
        """
        pass


class BaseClient(ClientProtocol):
    def _setup_logger(self) -> None:
        """
        Configure the client's logger when no handlers are present.
        
        Sets the logger level to INFO if it is unset and attaches a StreamHandler using a ColoredFormatter
        with a timestamped "[LEVEL] name: message" format.
        """
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
        """
        Execute the given coroutine and log any unhandled exceptions with context.
        
        Parameters:
            coro: The awaitable to execute.
            context (str): Short label used in the logged message to identify where the error occurred.
        
        Returns:
            The value returned by `coro`, or `None` if an exception was raised (the exception is logged).
        """
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Unhandled exception in {context}: {e}\n{traceback.format_exc()}")

    def _create_safe_task(
        self, coro: Awaitable[Any], name: str | None = None
    ) -> asyncio.Task[Any | None]:
        """
        Create and schedule a background task that captures and logs unhandled exceptions.
        
        Parameters:
            coro (Awaitable[Any]): The awaitable to run inside the created background task.
            name (str | None): Optional name for the task used for identification in logs and the event loop.
        
        Returns:
            asyncio.Task[Any | None]: The scheduled task instance; it is tracked in the client's background task set. The task returns the result of `coro`. If the task raises an exception (other than `asyncio.CancelledError`), the exception is logged and re-raised. 
        """
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
        """
        Cleanly shuts down the client's background work and resets connection state.
        
        Cancels and awaits all tracked background tasks as well as the receive and outgoing tasks, sets any unresolved pending futures to WebSocketNotConnectedError, closes the active WebSocket if present, marks the client as disconnected, and logs completion.
        """
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
                fut.set_exception(WebSocketNotConnectedError)
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
        Block indefinitely until the client is closed or the task is cancelled.
        
        Awaiting this coroutine suspends the caller and keeps the client in a waiting state; it does not return under normal operation.
        """
        await asyncio.Event().wait()

    def inspect(self) -> None:
        """
        Log a brief diagnostic summary of the client's current runtime state.
        
        Logs the connection status, the current user's identity when available, and counts for dialogs,
        chats, channels, cached users, background tasks, and scheduled tasks to aid debugging.
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
        """
        Start the client in a background task and wait until it becomes connected for use as an async context manager.
        
        Returns:
            Self: The client instance once a connection is established.
        """
        self._create_safe_task(self.start(), name="start")
        while not self.is_connected:
            await asyncio.sleep(0.05)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """
        Exit the asynchronous context by closing the client.
        
        Calls and awaits self.close() when the context manager exits. Does not suppress any exception raised within the context.
        
        Parameters:
            exc_type: The exception type if an exception was raised inside the context, otherwise None.
            exc: The exception instance if an exception was raised inside the context, otherwise None.
            tb: The traceback object associated with the exception, otherwise None.
        """
        await self.close()

    @abstractmethod
    async def login_with_code(self, temp_token: str, code: str, start: bool = False) -> None:
        """
        Authenticate the client using a temporary token and a verification code.
        
        Parameters:
            temp_token (str): Temporary authentication token issued by the server for this login attempt.
            code (str): Verification code (e.g., SMS or two-factor code) required to complete authentication.
            start (bool): If True, begin the client's session lifecycle (call start) after successful authentication.
        """
        pass

    @abstractmethod
    async def _post_login_tasks(self, sync: bool = True) -> None:
        """
        Perform client initialization tasks that must run immediately after a successful login.
        
        When `sync` is True, wait for all critical post-login tasks to complete before returning.
        When `sync` is False, schedule noncritical tasks to run in the background and return immediately.
        
        Parameters:
            sync (bool): If True, run post-login tasks to completion before returning; if False, run noncritical tasks asynchronously.
        
        Returns:
            None
        """
        pass

    @abstractmethod
    async def _wait_forever(self) -> None:
        """
        Block until the client should terminate.
        
        Concrete implementations must suspend execution until the client is requested to stop (for example via close() or an external shutdown signal) and return only when shutdown has begun.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Start the client's lifecycle: establish connection, initialize session state, and run until closed.
        
        This method is responsible for bringing the client to an operational state (e.g., connecting to the server, performing any login or post-login initialization, and starting background tasks) and keeping it running until close() is invoked or the client shuts down.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Shut down the client and release its resources, ensuring any active connections are closed and background tasks are stopped.
        """
        pass
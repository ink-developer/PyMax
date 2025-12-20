from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import ssl
import time
from collections.abc import Awaitable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from typing_extensions import override

from .crud import Database
from .exceptions import (
    InvalidPhoneError,
    SocketNotConnectedError,
)
from .interfaces import BaseClient
from .mixins import ApiMixin, SocketMixin, WebSocketMixin
from .payloads import UserAgentPayload
from .static.constant import (
    HOST,
    PORT,
    WEBSOCKET_URI,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import websockets

    from pymax.filters import BaseFilter

    from .filters import Filters
    from .types import Channel, Chat, Dialog, Me, Message, ReactionInfo, User


logger = logging.getLogger(__name__)


class MaxClient(ApiMixin, WebSocketMixin, BaseClient):
    """
    Основной клиент для работы с WebSocket API сервиса Max.

    :param phone: Номер телефона для авторизации.
    :type phone: str
    :param uri: URI WebSocket сервера.
    :type uri: str, optional
    :param work_dir: Рабочая директория для хранения базы данных.
    :type work_dir: str, optional
    :param logger: Пользовательский логгер. Если не передан, используется логгер модуля с именем f"{__name__}.MaxClient".
    :type logger: logging.Logger | None
    :param headers: Заголовки для подключения к WebSocket.
    :type headers: UserAgentPayload
    :param token: Токен авторизации. Если не передан, будет выполнен процесс логина по номеру телефона.
    :type token: str | None, optional
    :param host: Хост API сервера.
    :type host: str, optional
    :param port: Порт API сервера.
    :type port: int, optional
    :param registration: Флаг регистрации нового пользователя.
    :type registration: bool, optional
    :param first_name: Имя пользователя для регистрации. Требуется, если registration=True.
    :type first_name: str, optional
    :param last_name: Фамилия пользователя для регистрации.
    :type last_name: str | None, optional
    :param send_fake_telemetry: Флаг отправки фейковой телеметрии.
    :type send_fake_telemetry: bool, optional
    :param proxy: Прокси для подключения к WebSocket (см. https://websockets.readthedocs.io/en/stable/topics/proxies.html).
    :type proxy: str | Literal[True] | None, optional
    :param reconnect: Флаг автоматического переподключения при потере соединения.
    :type reconnect: bool, optional

    :raises InvalidPhoneError: Если формат номера телефона неверный.
    """

    def __init__(
        self,
        phone: str,
        uri: str = WEBSOCKET_URI,
        headers: UserAgentPayload = UserAgentPayload(),
        token: str | None = None,
        send_fake_telemetry: bool = True,
        host: str = HOST,
        port: int = PORT,
        proxy: str | Literal[True] | None = None,
        work_dir: str = ".",
        registration: bool = False,
        first_name: str = "",
        last_name: str | None = None,
        device_id: UUID | None = None,
        logger: logging.Logger | None = None,
        reconnect: bool = True,
        reconnect_delay: float = 1.0,
    ) -> None:
        """
        Initialize a MaxClient instance and set up connection, state, storage, and background task containers.
        
        Parameters:
        	phone (str): Phone number for the account; validated on init and will raise on invalid format.
        	uri (str): WebSocket URI to connect to.
        	headers (UserAgentPayload): User agent payload sent to the server.
        	token (str | None): Optional authentication token to use or persist.
        	send_fake_telemetry (bool): Whether to emit fake telemetry events after login.
        	host (str): Host for socket connections.
        	port (int): Port for socket connections.
        	proxy (str | True | None): Proxy URL or True to enable proxy discovery; None to disable.
        	work_dir (str): Directory used to store session database and files.
        	registration (bool): If True, client will perform a registration flow on start.
        	first_name (str): First name used during registration; required when registration is True.
        	last_name (str | None): Optional last name used during registration.
        	device_id (UUID | None): Device identifier to use; if None one is loaded from the session database.
        	logger (logging.Logger | None): Logger to use; a default logger is created when None.
        	reconnect (bool): Whether the client should attempt automatic reconnects after disconnect.
        	reconnect_delay (float): Seconds to wait between reconnect attempts.
        
        Raises:
        	InvalidPhoneError: If the provided phone number fails validation.
        """
        self.logger = logger or logging.getLogger(f"{__name__}")
        self.uri: str = uri
        self.phone: str = phone
        if not self._check_phone():
            raise InvalidPhoneError(self.phone)
        self.host: str = host
        self.port: int = port
        self.registration: bool = registration
        self.first_name: str = first_name
        self.last_name: str | None = last_name
        self.proxy: str | Literal[True] | None = proxy
        self.reconnect: bool = reconnect
        self.reconnect_delay: float = reconnect_delay

        self.is_connected: bool = False

        self.chats: list[Chat] = []
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []
        self.me: Me | None = None
        self._users: dict[int, User] = {}

        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / "session.db"
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path.touch(exist_ok=True)
        self._database = Database(self._work_dir)

        self._incoming: asyncio.Queue[dict[str, Any]] | None = None
        self._outgoing: asyncio.Queue[dict[str, Any]] | None = None
        self._recv_task: asyncio.Task[Any] | None = None
        self._outgoing_task: asyncio.Task[Any] | None = None
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._file_upload_waiters: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._background_tasks: set[asyncio.Task[Any]] = set()

        self._seq: int = 0
        self._error_count: int = 0
        self._circuit_breaker: bool = False
        self._last_error_time: float = 0.0

        self._device_id = device_id if device_id is not None else self._database.get_device_id()
        self._file_upload_waiters: dict[int, asyncio.Future[dict[str, Any]]] = {}

        self._token = self._database.get_auth_token() or token
        self.user_agent = headers
        self._send_fake_telemetry: bool = send_fake_telemetry
        self._session_id: int = int(time.time() * 1000)
        self._action_id: int = 1
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
        self._on_start_handler: Callable[[], Any | Awaitable[Any]] | None = None
        self._on_stop_handler: Callable[[], Any | Awaitable[Any]] | None = None
        self._on_reaction_change_handlers: list[Callable[[str, int, ReactionInfo], Any]] = []
        self._on_chat_update_handlers: list[Callable[[Chat], Any | Awaitable[Any]]] = []
        self._on_raw_receive_handlers: list[Callable[[dict[str, Any]], Any | Awaitable[Any]]] = []
        self._scheduled_tasks: list[tuple[Callable[[], Any | Awaitable[Any]], float]] = []

        self._ssl_context = ssl.create_default_context()
        self._ssl_context.set_ciphers("DEFAULT")
        self._ssl_context.check_hostname = True
        self._ssl_context.verify_mode = ssl.CERT_REQUIRED
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._ssl_context.load_default_certs()
        self._socket: socket.socket | None = None
        self._ws: websockets.ClientConnection | None = None

        self._setup_logger()
        self.logger.debug(
            "Initialized MaxClient uri=%s work_dir=%s",
            self.uri,
            self._work_dir,
        )

    async def _wait_forever(self) -> None:
        """
        Block until the WebSocket connection is closed.
        
        If the wait is cancelled, a debug message is logged.
        """
        try:
            await self.ws.wait_closed()
        except asyncio.CancelledError:
            self.logger.debug("wait_closed cancelled")

    async def close(self) -> None:
        """
        Close the client and release connection resources.
        
        Cancels any active receive and outgoing tasks, closes the WebSocket if open, and marks the client as not connected. Errors encountered during shutdown are logged.
        """
        try:
            self.logger.info("Closing client")
            if self._recv_task:
                self._recv_task.cancel()
                try:
                    await self._recv_task
                except asyncio.CancelledError:
                    self.logger.debug("recv_task cancelled")
            if self._outgoing_task:
                self._outgoing_task.cancel()
                try:
                    await self._outgoing_task
                except asyncio.CancelledError:
                    self.logger.debug("outgoing_task cancelled")
            if self._ws:
                await self._ws.close()
            self.is_connected = False
            self.logger.info("Client closed")
        except Exception:
            self.logger.exception("Error closing client")

    async def _post_login_tasks(self, sync: bool = True) -> None:
        """
        Run post-login work: optionally synchronize state, start recurring background jobs, and invoke the configured start handler.
        
        Parameters:
            sync (bool): If True, perform a full synchronization before scheduling background tasks.
        
        Details:
            - Schedules an interactive ping loop and the scheduled-task runner as background tasks.
            - If fake telemetry is enabled, schedules the telemetry sender as a background task.
            - If an on-start handler is configured, calls it; if it returns a coroutine, the coroutine is executed and awaited.
        """
        if sync:
            await self._sync()

        self.logger.debug("is_connected=%s before starting ping", self.is_connected)
        ping_task = asyncio.create_task(self._send_interactive_ping())
        ping_task.add_done_callback(self._log_task_exception)
        self._background_tasks.add(ping_task)

        start_scheduled_task = asyncio.create_task(self._start_scheduled_tasks())
        start_scheduled_task.add_done_callback(self._log_task_exception)

        if self._send_fake_telemetry:
            telemetry_task = asyncio.create_task(self._start())
            telemetry_task.add_done_callback(self._log_task_exception)
            self._background_tasks.add(telemetry_task)

        if self._on_start_handler:
            self.logger.debug("Calling on_start handler")
            result = self._on_start_handler()
            if asyncio.iscoroutine(result):
                await self._safe_execute(result, context="on_start handler")

    async def login_with_code(self, temp_token: str, code: str, start: bool = False) -> None:
        """
        Complete a login using a verification code, persist the resulting auth token, and optionally start post-login tasks and keep the client running.
        
        Parameters:
            temp_token (str): Temporary token obtained from a prior request_code call.
            code (str): Verification code (expected to be 6 digits).
            start (bool): If True, run post-login tasks and enter the client's run loop; if False, only save the token.
        
        Raises:
            ValueError: If the login response does not contain the expected token.
        """
        resp = await self._send_code(code, temp_token)
        token = resp.get("tokenAttrs", {}).get("LOGIN", {}).get("token")
        if not token:
            raise ValueError("Login response did not contain tokenAttrs.LOGIN.token")
        self._token = token
        self._database.update_auth_token(self._device_id, token)
        if start:
            while True:
                try:
                    await self._post_login_tasks()
                    await self._wait_forever()
                except Exception:
                    self.logger.exception("Error during post-login tasks")
                finally:
                    await self._cleanup_client()

                self.logger.info("Reconnecting after post-login tasks failure")
                await asyncio.sleep(self.reconnect_delay)
        else:
            self.logger.info("Login successful, token saved to database, exiting...")

    async def start(self) -> None:
        """
        Run the client lifecycle: connect to the WebSocket, perform registration or login if needed, synchronize state, start post-login background tasks, and keep the connection open with optional automatic reconnect.
        
        If registration is enabled, a missing `first_name` raises a ValueError. Other exceptions raised during a start iteration are propagated after cleanup.
        """

        while True:
            try:
                self.logger.info("Client starting")
                await self.connect(self.user_agent)

                if self.registration:
                    if not self.first_name:
                        raise ValueError("First name is required for registration")
                    await self._register(self.first_name, self.last_name)

                if self._token and self._database.get_auth_token() is None:
                    self._database.update_auth_token(self._device_id, self._token)

                if self._token is None:
                    await self._login()

                await self._sync()

                await self._post_login_tasks(sync=False)

                await self._wait_forever()
                self.logger.info("WebSocket closed (wait_forever exited)")
            except Exception as e:
                self.logger.exception("Client start iteration failed")
                raise e

            finally:
                self.logger.debug("Cleaning up background tasks and pending futures")

                await self._cleanup_client()

            if not self.reconnect:
                self.logger.info("Reconnect disabled — exiting start()")
                return

            self.logger.info("Reconnect enabled — restarting client")
            await asyncio.sleep(self.reconnect_delay)


class SocketMaxClient(SocketMixin, MaxClient):
    @override
    async def _wait_forever(self):
        if self._recv_task:
            try:
                await self._recv_task
            except asyncio.CancelledError:
                self.logger.debug("Socket recv_task cancelled")
            except Exception as e:
                self.logger.exception("Socket recv_task failed: %s", e)

    @override
    async def _cleanup_client(self):
        """
        Cancel background and I/O tasks, fail pending requests, close the socket, and mark the client disconnected.
        
        This method cancels and awaits all registered background tasks and the receive/outgoing tasks (suppressing cancellation errors), sets a SocketNotConnectedError on any unresolved pending futures, attempts to close the underlying socket, clears related resources, and sets the client's connection state to disconnected. It logs debug information for errors encountered while cancelling tasks or closing the socket and an informational message when cleanup completes.
        """
        for task in list(self._background_tasks):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.debug(
                    "Background task raised during cancellation (socket)",
                    exc_info=True,
                )
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
                fut.set_exception(SocketNotConnectedError())
        self._pending.clear()

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                self.logger.debug("Error closing socket during cleanup", exc_info=True)
            self._socket = None

        self.is_connected = False
        self.logger.info("Client start() cleaned up (socket)")
import asyncio
import contextlib
import logging
import socket
import ssl
import time
import traceback
from collections.abc import Awaitable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from typing_extensions import Self, override

from pymax.filters import BaseFilter

from .crud import Database
from .exceptions import (
    InvalidPhoneError,
    SocketNotConnectedError,
    WebSocketNotConnectedError,
)
from .formatter import ColoredFormatter
from .mixins import ApiMixin, SocketMixin, WebSocketMixin
from .payloads import UserAgentPayload
from .static.constant import (
    HOST,
    PORT,
    WEBSOCKET_URI,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any
    from uuid import UUID

    import websockets

    from .filters import filters
    from .types import Channel, Chat, Dialog, Me, Message, ReactionInfo, User


logger = logging.getLogger(__name__)


class MaxClient(ApiMixin, WebSocketMixin):
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
        device_id: str | None = None,
        logger: logging.Logger | None = None,
        reconnect: bool = True,
        reconnect_delay: float = 1.0,
    ) -> None:
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

        self._device_id = (
            device_id if device_id is not None else self._database.get_device_id()
        )
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
        self._on_reaction_change_handlers: list[
            tuple[Callable[[str, int, ReactionInfo], Any]]
        ] = []
        self._on_chat_update_handlers: list[tuple[Callable[[Chat], Any]]] = []
        self._on_raw_receive_handlers: list[
            Callable[[dict[str, Any]], Any | Awaitable[Any]]
        ] = []
        self._scheduled_tasks: list[
            tuple[Callable[[], Any | Awaitable[Any]], float]
        ] = []

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

    async def _wait_forever(self) -> None:
        try:
            await self.ws.wait_closed()
        except asyncio.CancelledError:
            self.logger.debug("wait_closed cancelled")

    async def _safe_execute(self, coro, *, context: str = "unknown") -> Any:
        """
        Безопасно выполняет пользовательскую корутину.
        Логирует traceback, но не роняет event loop.
        """
        try:
            return await coro
        except Exception as e:
            self.logger.error(
                f"Unhandled exception in {context}: {e}\n{traceback.format_exc()}"
            )

    async def close(self) -> None:
        """
        Закрывает клиент и освобождает ресурсы.

        :return: None
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

    @override
    def _create_safe_task(
        self, coro: Awaitable[Any], *, name: str | None = None
    ) -> asyncio.Task[Any | None]:
        async def runner():
            try:
                return await coro
            except asyncio.CancelledError:
                raise
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(
                    f"Unhandled exception in task {name or coro}: {e}\n{tb}"
                )
                raise

        task = asyncio.create_task(runner(), name=name)
        self._background_tasks.add(task)
        return task

    async def _post_login_tasks(self, sync: bool = True) -> None:
        if sync:
            await self._sync()

        if self._on_start_handler:
            self.logger.debug("Calling on_start handler")
            result = self._on_start_handler()
            if asyncio.iscoroutine(result):
                await self._safe_execute(result, context="on_start handler")

        ping_task = asyncio.create_task(self._send_interactive_ping())
        ping_task.add_done_callback(self._log_task_exception)
        self._background_tasks.add(ping_task)

        start_scheduled_task = asyncio.create_task(self._start_scheduled_tasks())
        start_scheduled_task.add_done_callback(self._log_task_exception)

        if self._send_fake_telemetry:
            telemetry_task = asyncio.create_task(self._start())
            telemetry_task.add_done_callback(self._log_task_exception)
            self._background_tasks.add(telemetry_task)

    async def _cleanup_client(self) -> None:
        for task in list(self._background_tasks):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.debug(
                    "Background task raised during cancellation", exc_info=True
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

    async def login_with_code(
        self, temp_token: str, code: str, start: bool = False
    ) -> None:
        """
        Завершает кастомный login flow: отправляет код, сохраняет токен и запускает пост-логин задачи.

        :param temp_token: Временный токен, полученный из request_code.
        :type temp_token: str
        :param code: Код верификации (6 цифр).
        :type code: str
        :param start: Флаг запуска пост-логин задач и ожидания навсегда. Если False, только сохраняет токен.
        :type start: bool, optional
        :return: None
        :rtype: None
        """
        resp = await self._send_code(code, temp_token)
        token = resp.get("tokenAttrs", {}).get("LOGIN", {}).get("token")
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
        Запускает клиент, подключается к WebSocket, авторизует
        пользователя (если нужно) и запускает фоновый цикл.
        Теперь включает безопасный reconnect-loop, если self.reconnect=True.

        :return: None
        :rtype: None
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
                else:
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
        self.logger.info(f"Me: {self.me.names[0].first_name} ({self.me.id})")
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
        Socket-specific cleanup: cancel background tasks, set pending futures
        exceptions to SocketNotConnectedError, and close socket.
        """
        from .exceptions import SocketNotConnectedError

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

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
    Error,
    InvalidPhoneError,
    SocketNotConnectedError,
    WebSocketNotConnectedError,
)
from .interfaces import BaseClient
from .mixins import ApiMixin, SocketMixin, WebSocketMixin
from .payloads import UserAgentPayload
from .static.constant import HOST, PORT, SESSION_STORAGE_DB, WEBSOCKET_URI

if TYPE_CHECKING:
    from collections.abc import Callable

    import websockets

    from pymax.filters import BaseFilter

    from .types import Channel, Chat, Dialog, Me, Message, ReactionInfo, User


logger = logging.getLogger(__name__)


class MaxClient(ApiMixin, WebSocketMixin, BaseClient):
    allowed_device_types: set[str] = {"WEB"}
    """
    Основной клиент для работы с WebSocket API сервиса Max.

    :param phone: Номер телефона для авторизации.
    :type phone: str
    :param uri: URI WebSocket сервера.
    :type uri: str, optional
    :param session_name: Название сессии для хранения базы данных.
    :type session_name: str, optional
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
    :param reconnect_delay: Начальная задержка между попытками переподключения в секундах. По умолчанию 1.0.
        Задержка увеличивается экспоненциально при каждой неудачной попытке.
    :type reconnect_delay: float, optional
    :param max_reconnect_attempts: Максимальное количество попыток переподключения.
        None (по умолчанию) означает бесконечное количество попыток.
    :type max_reconnect_attempts: int | None, optional
    :param verify_ssl: Флаг проверки SSL сертификатов. По умолчанию True.
        Установите False для отключения проверки (не рекомендуется для production).
    :type verify_ssl: bool, optional

    :raises InvalidPhoneError: Если формат номера телефона неверный.
    """

    def __init__(
        self,
        phone: str,
        uri: str = WEBSOCKET_URI,
        session_name: str = SESSION_STORAGE_DB,
        headers: UserAgentPayload | None = None,
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
        max_reconnect_attempts: int | None = None,
        verify_ssl: bool = True,
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
        self.max_reconnect_attempts: int | None = max_reconnect_attempts
        self._reconnect_attempt: int = 0

        self.is_connected: bool = False

        self.chats: list[Chat] = []
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []
        self.me: Me | None = None
        self.contacts: list[User] = []
        self._users: dict[int, User] = {}

        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / session_name
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
        self._stop_event = asyncio.Event()

        self._seq: int = 0
        self._error_count: int = 0
        self._circuit_breaker: bool = False
        self._last_error_time: float = 0.0

        self._device_id = device_id if device_id is not None else self._database.get_device_id()
        self._file_upload_waiters: dict[int, asyncio.Future[dict[str, Any]]] = {}

        self._token = self._database.get_auth_token() or token
        if headers is None:
            headers = self._default_headers()
        self.user_agent = headers
        self._validate_device_type()
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
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        if verify_ssl:
            self._ssl_context.check_hostname = True
            self._ssl_context.verify_mode = ssl.CERT_REQUIRED
            self._ssl_context.load_default_certs()
        else:
            self.logger.warning("SSL certificate verification is disabled - this is insecure!")
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

        self._socket: socket.socket | None = None
        self._socket_lock: asyncio.Lock | None = None
        self._reconnecting: bool = False
        self._ws: websockets.ClientConnection | None = None

        self._setup_logger()
        self.logger.debug(
            "Initialized MaxClient uri=%s work_dir=%s",
            self.uri,
            self._work_dir,
        )

    @staticmethod
    def _default_headers() -> UserAgentPayload:
        return UserAgentPayload(device_type="WEB")

    def _validate_device_type(self) -> None:
        if self.user_agent.device_type not in self.allowed_device_types:
            raise ValueError(
                f"{self.__class__.__name__} does not support "
                f"device_type={self.user_agent.device_type}"
            )

    async def _wait_forever(self) -> None:
        try:
            await self.ws.wait_closed()
        except asyncio.CancelledError:
            self.logger.debug("wait_closed cancelled")
        except WebSocketNotConnectedError:
            self.logger.info("WebSocket not connected, exiting wait_forever")

    async def close(self) -> None:
        """
        Закрывает клиент и освобождает ресурсы.

        :return: None
        """
        try:
            self.logger.info("Closing client")
            self._stop_event.set()
        except Exception:
            self.logger.exception("Error closing client")

    async def _post_login_tasks(self, sync: bool = True) -> None:
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

        login_attrs = resp.get("tokenAttrs", {}).get("LOGIN", {})
        password_challenge = resp.get("passwordChallenge")

        if password_challenge and not login_attrs:
            token = await self._two_factor_auth(password_challenge)
        else:
            token = login_attrs.get("token")

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
        Запускает клиент, подключается к WebSocket, авторизует
        пользователя (если нужно) и запускает фоновый цикл.
        Теперь включает безопасный reconnect-loop, если self.reconnect=True.

        :return: None
        :rtype: None
        """
        self.logger.debug(
            "start() called: reconnect=%s, stop_event=%s, token=%s",
            self.reconnect,
            self._stop_event.is_set(),
            "present" if self._token else "None"
        )
        while not self._stop_event.is_set():
            try:
                if self._reconnect_attempt > 0:
                    self.logger.info(
                        "Client starting (reconnect attempt %d/%s)",
                        self._reconnect_attempt,
                        self.max_reconnect_attempts or "∞",
                    )
                else:
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

                await self._sync(self.user_agent)
                await self._post_login_tasks(sync=False)

                # Successfully connected - reset reconnect counter
                if self._reconnect_attempt > 0:
                    self.logger.info(
                        "Successfully reconnected after %d attempts",
                        self._reconnect_attempt,
                    )
                self._reconnect_attempt = 0

                self.logger.debug("Entering wait loop: ws=%s, is_connected=%s", self._ws, self.is_connected)
                wait_task = asyncio.create_task(self._wait_forever())
                stop_task = asyncio.create_task(self._stop_event.wait())

                done, pending = await asyncio.wait(
                    [wait_task, stop_task], return_when=asyncio.FIRST_COMPLETED
                )

                # Log which task completed
                if wait_task in done:
                    self.logger.info("Wait loop exited: WebSocket closed or _wait_forever() completed")
                if stop_task in done:
                    self.logger.info("Wait loop exited: stop_event was set")
                self.logger.debug("Wait loop completed: done=%s", done)

                for task in pending:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

            except (InvalidPhoneError, ValueError) as e:
                # Critical configuration errors - don't retry
                self.logger.error("Fatal configuration error: %s", e)
                raise

            except Error as auth_err:
                # Authentication errors - clear token and stop reconnect
                error_code = getattr(auth_err, 'error', '')

                # Список кодов ошибок авторизации, при которых не нужен reconnect
                auth_error_codes = [
                    "FAIL_LOGIN_TOKEN",
                    "FAIL_WRONG_PASSWORD",
                    "FAIL_LOGOUT_ALL",
                    "FAIL_FORBIDDEN"
                ]

                if any(code in str(auth_err) for code in auth_error_codes):
                    self.logger.error(
                        "Authentication error detected: %s - clearing token and stopping",
                        error_code or str(auth_err)
                    )

                    # Очищаем токен из памяти и базы данных
                    self._token = None
                    try:
                        self._database.update_auth_token(self._device_id, None)
                        self.logger.info("Token cleared from database")
                    except Exception as db_err:
                        self.logger.error("Failed to clear token from database: %s", db_err)

                    # Останавливаем reconnect loop
                    self.reconnect = False
                    self.logger.warning("Reconnect disabled due to authentication failure")

                    # Вызываем пользовательский обработчик, если есть
                    if hasattr(self, '_on_error_handler') and self._on_error_handler:
                        try:
                            result = self._on_error_handler(auth_err)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as handler_err:
                            self.logger.error("Error handler failed: %s", handler_err)

                    break  # Выходим из reconnect loop
                else:
                    # Другие ошибки Error - пробуем reconnect
                    self.logger.exception("Non-auth Error occurred: %s", e)
                    self._reconnect_attempt += 1

            except asyncio.CancelledError:
                self.logger.info("Client task cancelled, stopping")
                break
            except Exception as e:
                # Network/temporary errors - attempt reconnect
                self.logger.exception("Client start iteration failed: %s", e)
                self._reconnect_attempt += 1
            finally:
                self.logger.debug("Cleaning up background tasks and pending futures")

                try:
                    await self._cleanup_client()
                    # Verify cleanup was successful
                    if self._recv_task is not None or self._outgoing_task is not None:
                        self.logger.warning(
                            "Cleanup incomplete: recv_task=%s, outgoing_task=%s",
                            self._recv_task,
                            self._outgoing_task,
                        )
                    if len(self._background_tasks) > 0:
                        self.logger.warning(
                            "Cleanup incomplete: %d background tasks still running",
                            len(self._background_tasks),
                        )
                    self.logger.debug("Cleanup verification passed")
                except Exception as cleanup_err:
                    self.logger.error("Cleanup failed: %s", cleanup_err, exc_info=True)

            if not self.reconnect or self._stop_event.is_set():
                self.logger.info(
                    "Reconnect disabled or stop requested — exiting start() (reconnect=%s, stop_event=%s)",
                    self.reconnect,
                    self._stop_event.is_set()
                )
                break

            # Check max reconnect attempts
            if (
                self.max_reconnect_attempts is not None
                and self._reconnect_attempt >= self.max_reconnect_attempts
            ):
                self.logger.error(
                    "Max reconnect attempts (%d) reached, exiting",
                    self.max_reconnect_attempts,
                )
                return

            # Exponential backoff with cap at 60 seconds
            delay = min(self.reconnect_delay * (2 ** (self._reconnect_attempt - 1)), 60.0)
            self.logger.info(
                "Reconnect enabled — restarting client in %.1f seconds (attempt %d/%s)",
                delay,
                self._reconnect_attempt + 1,
                self.max_reconnect_attempts or "∞",
            )
            await asyncio.sleep(delay)

        self.logger.info("Client exited cleanly")


class SocketMaxClient(SocketMixin, MaxClient):
    allowed_device_types = {"ANDROID", "IOS", "DESKTOP"}

    @staticmethod
    def _default_headers() -> UserAgentPayload:
        return UserAgentPayload(device_type="DESKTOP")

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

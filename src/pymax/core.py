import asyncio
import logging
import socket
import ssl
import time
from pathlib import Path

from typing_extensions import override

from .crud import Database
from .exceptions import InvalidPhoneError
from .mixins import ApiMixin, SocketMixin, WebSocketMixin
from .payloads import UserAgentPayload
from .static.constant import DEFAULT_USER_AGENT, HOST, PORT, WEBSOCKET_URI

logger = logging.getLogger(__name__)


class MaxClient(ApiMixin, WebSocketMixin):
    """
    Основной клиент для работы с WebSocket API сервиса Max.


    Args:
        phone (str): Номер телефона для авторизации.
        uri (str, optional): URI WebSocket сервера. По умолчанию Constants.WEBSOCKET_URI.value.
        work_dir (str, optional): Рабочая директория для хранения базы данных. По умолчанию ".".
        logger (logging.Logger | None): Пользовательский логгер. Если не передан — используется
            логгер модуля с именем f"{__name__}.MaxClient".
        headers (dict[str, Any] | None): Заголовки для подключения к WebSocket. По умолчанию
            Constants.DEFAULT_USER_AGENT.value.
        token (str | None, optional): Токен авторизации. Если не передан, будет выполнен
            процесс логина по номеру телефона.
        host (str, optional): Хост API сервера. По умолчанию Constants.HOST.value.
        port (int, optional): Порт API сервера. По умолчанию Constants.PORT.value.

    Raises:
        InvalidPhoneError: Если формат номера телефона неверный.
    """

    def __init__(
        self,
        phone: str,
        uri: str = WEBSOCKET_URI,
        headers: UserAgentPayload = DEFAULT_USER_AGENT,
        token: str | None = None,
        send_fake_telemetry: bool = True,
        host: str = HOST,
        port: int = PORT,
        work_dir: str = ".",
        logger: logging.Logger | None = None,
    ) -> None:
        logger = logger or logging.getLogger(f"{__name__}.MaxClient")
        ApiMixin.__init__(self, token=token, logger=logger)
        WebSocketMixin.__init__(self, token=token, logger=logger)
        self.uri: str = uri
        self.phone: str = phone
        if not self._check_phone():
            raise InvalidPhoneError(self.phone)
        self.host: str = host
        self.port: int = port
        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / "session.db"
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path.touch(exist_ok=True)
        self._database = Database(self._work_dir)
        self._device_id = self._database.get_device_id()
        self._token = self._database.get_auth_token() or token
        self.user_agent = headers
        self._send_fake_telemetry: bool = send_fake_telemetry
        self._session_id: int = int(time.time() * 1000)
        self._action_id: int = 1
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.set_ciphers("DEFAULT")
        self._ssl_context.check_hostname = True
        self._ssl_context.verify_mode = ssl.CERT_REQUIRED
        self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._ssl_context.load_default_certs()
        self._socket: socket.socket | None = None
        self._setup_logger()
        self.logger.debug(
            "Initialized MaxClient uri=%s work_dir=%s",
            self.uri,
            self._work_dir,
        )

    def _setup_logger(self) -> None:
        self.logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    async def _wait_forever(self):
        try:
            await self.ws.wait_closed()
        except asyncio.CancelledError:
            self.logger.debug("wait_closed cancelled")

    async def close(self) -> None:
        try:
            self.logger.info("Closing client")
            if self._recv_task:
                self._recv_task.cancel()
                try:
                    await self._recv_task
                except asyncio.CancelledError:
                    self.logger.debug("recv_task cancelled")
            if self._ws:
                await self._ws.close()
            self.is_connected = False
            self.logger.info("Client closed")
        except Exception:
            self.logger.exception("Error closing client")

    async def start(self) -> None:
        """
        Запускает клиент, подключается к WebSocket, авторизует
        пользователя (если нужно) и запускает фоновый цикл.
        """
        try:
            self.logger.info("Client starting")
            await self._connect(self.user_agent)

            if self._token and self._database.get_auth_token() is None:
                self._database.update_auth_token(self._device_id, self._token)

            if self._token is None:
                await self._login()
            else:
                await self._sync()

            if self._on_start_handler:
                self.logger.debug("Calling on_start handler")
                result = self._on_start_handler()
                if asyncio.iscoroutine(result):
                    await result

            ping_task = asyncio.create_task(self._send_interactive_ping())
            self._background_tasks.add(ping_task)
            if self._send_fake_telemetry:
                telemetry_task = asyncio.create_task(self._start())
                self._background_tasks.add(telemetry_task)
                telemetry_task.add_done_callback(
                    lambda t: self._background_tasks.discard(t)  # type: ignore[func-returns-value]
                    or self._log_task_exception(t)  # type: ignore[func-returns-value]
                )
            ping_task.add_done_callback(
                lambda t: self._background_tasks.discard(t)  # type: ignore[func-returns-value]
                or self._log_task_exception(t)  # type: ignore[func-returns-value]
            )
            await self._wait_forever()
        except Exception:
            self.logger.exception("Client start failed")


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

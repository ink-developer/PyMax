import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import websockets

from .crud import Database
from .exceptions import InvalidPhoneError, WebSocketNotConnectedError
from .mixins import ApiMixin, WebSocketMixin
from .payloads import (
    BaseWebSocketMessage,
    SyncPayload,
)
from .static import ChatType, Constants, Opcode
from .types import Channel, Chat, Dialog, Me, Message, User, override

if TYPE_CHECKING:
    from .filters import Filter

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

    Raises:
        InvalidPhoneError: Если формат номера телефона неверный.
    """

    def __init__(
        self,
        phone: str,
        uri: str = Constants.WEBSOCKET_URI.value,
        headers: dict[str, Any] | None = Constants.DEFAULT_USER_AGENT.value,
        token: str | None = None,
        work_dir: str = ".",
        logger: logging.Logger | None = None,
    ) -> None:
        self.uri: str = uri
        self.is_connected: bool = False
        self.phone: str = phone
        self.chats: list[Chat] = []
        self.dialogs: list[Dialog] = []
        self.channels: list[Channel] = []
        self.me: Me | None = None
        self._users: dict[int, User] = {}
        if not self._check_phone():
            raise InvalidPhoneError(self.phone)
        self._work_dir: str = work_dir
        self._database_path: Path = Path(work_dir) / "session.db"
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path.touch(exist_ok=True)
        self._database = Database(self._work_dir)
        self._ws: websockets.ClientConnection | None = None
        self._seq: int = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._incoming: asyncio.Queue[dict[str, Any]] | None = None
        self._device_id = self._database.get_device_id()
        self._token = self._database.get_auth_token() or token
        self.user_agent = headers
        self._on_message_handlers: list[
            tuple[Callable[[Message], Any], Filter | None]
        ] = []
        self._on_start_handler: Callable[[], Any | Awaitable[Any]] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self.logger = logger or logging.getLogger(f"{__name__}.MaxClient")
        self._setup_logger()

        self.logger.debug(
            "Initialized MaxClient uri=%s work_dir=%s", self.uri, self._work_dir
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

            if self._ws:
                ping_task = asyncio.create_task(self._send_interactive_ping())
                self._background_tasks.add(ping_task)
                ping_task.add_done_callback(
                    lambda t: self._background_tasks.discard(t)
                    or self._log_task_exception(t)
                )

                try:
                    await self._ws.wait_closed()
                except asyncio.CancelledError:
                    self.logger.debug("wait_closed cancelled")
        except Exception:
            self.logger.exception("Client start failed")


class SocketMaxClient:
    pass  # нокс займись
    # нет не займусь 

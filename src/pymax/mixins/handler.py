from collections.abc import Awaitable, Callable
from typing import Any

from pymax.interfaces import ClientProtocol, Filter
from pymax.types import Message


class HandlerMixin(ClientProtocol):
    def on_message(self, *, filter: Filter | None = None) -> Callable[
        [Callable[[Any], Any | Awaitable[Any]]],
        Callable[[Any], Any | Awaitable[Any]],
    ]:
        """
        Декоратор для установки обработчика входящих сообщений.

        Args:
            filter: Фильтр для обработки сообщений.

        Returns:
            Декоратор.
        """

        def decorator(
            handler: Callable[[Any], Any | Awaitable[Any]],
        ) -> Callable[[Any], Any | Awaitable[Any]]:
            self._on_message_handlers.append((handler, filter))
            self.logger.info(
                f"on_message handler set: {handler}, filter: {filter}"
            )
            return handler

        return decorator

    def on_start(
        self, handler: Callable[[], Any | Awaitable[Any]]
    ) -> Callable[[], Any | Awaitable[Any]]:
        """
        Устанавливает обработчик, вызываемый при старте клиента.

        Args:
            handler: Функция или coroutine без аргументов.

        Returns:
            Установленный обработчик.
        """
        self._on_start_handler = handler
        self.logger.debug("on_start handler set: %r", handler)
        return handler

    def add_message_handler(
        self,
        handler: Callable[[Message], Any | Awaitable[Any]],
        filter: Filter | None,
    ) -> Callable[[Message], Any | Awaitable[Any]]:
        self.logger.debug("add_message_handler (alias) used")
        self._on_message_handlers.append((handler, filter))
        return handler

    def add_on_start_handler(
        self, handler: Callable[[], Any | Awaitable[Any]]
    ) -> Callable[[], Any | Awaitable[Any]]:
        self.logger.debug("add_on_start_handler (alias) used")
        self._on_start_handler = handler
        return handler

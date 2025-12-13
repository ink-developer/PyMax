from collections.abc import Awaitable, Callable
from typing import Any

from pymax.filters import BaseFilter
from pymax.interfaces import ClientProtocol
from pymax.types import Chat, Message, ReactionInfo


class HandlerMixin(ClientProtocol):
    def on_message(
        self, filter: BaseFilter[Message] | None = None
    ) -> Callable[
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
            self.logger.debug(f"on_message handler set: {handler}, filter: {filter}")
            return handler

        return decorator

    def on_message_edit(
        self, filter: BaseFilter[Message] | None = None
    ) -> Callable[
        [Callable[[Any], Any | Awaitable[Any]]],
        Callable[[Any], Any | Awaitable[Any]],
    ]:
        """
        Декоратор для установки обработчика отредактированных сообщений.

        Args:
            filter: Фильтр для обработки сообщений.

        Returns:
            Декоратор.
        """

        def decorator(
            handler: Callable[[Any], Any | Awaitable[Any]],
        ) -> Callable[[Any], Any | Awaitable[Any]]:
            self._on_message_edit_handlers.append((handler, filter))
            self.logger.debug(
                f"on_message_edit handler set: {handler}, filter: {filter}"
            )
            return handler

        return decorator

    def on_message_delete(
        self, filter: BaseFilter[Message] | None = None
    ) -> Callable[
        [Callable[[Any], Any | Awaitable[Any]]],
        Callable[[Any], Any | Awaitable[Any]],
    ]:
        """
        Декоратор для установки обработчика удаленных сообщений.

        Args:
            filter: Фильтр для обработки сообщений.

        Returns:
            Декоратор.
        """

        def decorator(
            handler: Callable[[Any], Any | Awaitable[Any]],
        ) -> Callable[[Any], Any | Awaitable[Any]]:
            self._on_message_delete_handlers.append((handler, filter))
            self.logger.debug(
                f"on_message_delete handler set: {handler}, filter: {filter}"
            )
            return handler

        return decorator

    def on_reaction_change(
        self,
        handler: Callable[[str, int, ReactionInfo], Any | Awaitable[Any]],
    ) -> Callable[[str, int, ReactionInfo], Any | Awaitable[Any]]:
        """
        Устанавливает обработчик изменения реакций на сообщения.

        Args:
            handler: Функция или coroutine с аргументами (message_id: str, chat_id: int, reaction_info: ReactionInfo).

        Returns:
            Установленный обработчик.
        """
        self._on_reaction_change_handlers.append(handler)
        self.logger.debug("on_reaction_change handler set: %r", handler)
        return handler

    def on_chat_update(
        self, handler: Callable[[Chat], Any | Awaitable[Any]]
    ) -> Callable[[Chat], Any | Awaitable[Any]]:
        """
        Устанавливает обработчик обновления информации о чате.

        Args:
            handler: Функция или coroutine с аргументом (chat: Chat).

        Returns:
            Установленный обработчик.
        """
        self._on_chat_update_handlers.append(handler)
        self.logger.debug("on_chat_update handler set: %r", handler)
        return handler

    def on_raw_receive(
        self, handler: Callable[[dict[str, Any]], Any | Awaitable[Any]]
    ) -> Callable[[dict[str, Any]], Any | Awaitable[Any]]:
        """
        Устанавливает обработчик для получения необработанных данных от сервера.

        Args:
            handler: Функция или coroutine с аргументом (data: dict).

        Returns:
            Установленный обработчик.
        """
        self._on_raw_receive_handlers.append(handler)
        self.logger.debug("on_raw_receive handler set: %r", handler)
        return handler

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

    def task(self, seconds: float, minutes: float = 0, hours: float = 0):
        """
        Декоратор для планирования периодической задачи.

        Args:
            seconds (float): Интервал в секундах.
            minutes (float, optional): Интервал в минутах. По умолчанию 0.
            hours (float, optional): Интервал в часах. По умолчанию 0.

        Returns:
            Декоратор.
        """

        def decorator(
            handler: Callable[[], Any | Awaitable[Any]],
        ) -> Callable[[], Any | Awaitable[Any]]:
            self._scheduled_tasks.append(
                (handler, seconds + minutes * 60 + hours * 3600)
            )
            self.logger.debug(
                f"task scheduled: {handler}, interval: {seconds + minutes * 60 + hours * 3600}s"
            )
            return handler

        return decorator

    def add_message_handler(
        self,
        handler: Callable[[Message], Any | Awaitable[Any]],
        filter: BaseFilter[Message] | None = None,
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

    def add_reaction_change_handler(
        self,
        handler: Callable[[str, int, ReactionInfo], Any | Awaitable[Any]],
    ) -> Callable[[str, int, ReactionInfo], Any | Awaitable[Any]]:
        self.logger.debug("add_reaction_change_handler (alias) used")
        self._on_reaction_change_handlers.append(
            handler,
        )
        return handler

    def add_chat_update_handler(
        self, handler: Callable[[Chat], Any | Awaitable[Any]]
    ) -> Callable[[Chat], Any | Awaitable[Any]]:
        self.logger.debug("add_chat_update_handler (alias) used")
        self._on_chat_update_handlers.append(handler)
        return handler

    def add_raw_receive_handler(
        self, handler: Callable[[dict[str, Any]], Any | Awaitable[Any]]
    ) -> Callable[[dict[str, Any]], Any | Awaitable[Any]]:
        self.logger.debug("add_raw_receive_handler (alias) used")
        self._on_raw_receive_handlers.append(handler)
        return handler

    def add_scheduled_task(
        self,
        handler: Callable[[], Any | Awaitable[Any]],
        interval: float,
    ) -> Callable[[], Any | Awaitable[Any]]:
        self.logger.debug("add_scheduled_task (alias) used")
        self._scheduled_tasks.append((handler, interval))
        return handler

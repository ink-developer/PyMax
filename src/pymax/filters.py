from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pymax.static.enum import AttachType, ChatType, MessageStatus
from pymax.types import Message

T_co = TypeVar("T_co")


class BaseFilter(ABC, Generic[T_co]):
    event_type: type[T_co]

    @abstractmethod
    def __call__(self, event: T_co) -> bool: ...

    def __and__(self, other: BaseFilter[T_co]) -> BaseFilter[T_co]:
        return AndFilter(self, other)

    def __or__(self, other: BaseFilter[T_co]) -> BaseFilter[T_co]:
        return OrFilter(self, other)

    def __invert__(self) -> BaseFilter[T_co]:
        return NotFilter(self)


class AndFilter(BaseFilter[T_co]):
    def __init__(self, *filters: BaseFilter[T_co]) -> None:
        self.filters = filters
        self.event_type = filters[0].event_type

    def __call__(self, event: T_co) -> bool:
        return all(f(event) for f in self.filters)


class OrFilter(BaseFilter[T_co]):
    def __init__(self, *filters: BaseFilter[T_co]) -> None:
        self.filters = filters
        self.event_type = filters[0].event_type

    def __call__(self, event: T_co) -> bool:
        return any(f(event) for f in self.filters)


class NotFilter(BaseFilter[T_co]):
    def __init__(self, base_filter: BaseFilter[T_co]) -> None:
        self.base_filter = base_filter
        self.event_type = base_filter.event_type

    def __call__(self, event: T_co) -> bool:
        return not self.base_filter(event)


class ChatFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id

    def __call__(self, message: Message) -> bool:
        return message.chat_id == self.chat_id


class TextFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, text: str) -> None:
        self.text = text

    def __call__(self, message: Message) -> bool:
        return self.text in message.text


class SenderFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    def __call__(self, message: Message) -> bool:
        return message.sender == self.user_id


class StatusFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, status: MessageStatus) -> None:
        self.status = status

    def __call__(self, message: Message) -> bool:
        return message.status == self.status


class TextContainsFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, substring: str) -> None:
        self.substring = substring

    def __call__(self, message: Message) -> bool:
        return self.substring in message.text


class RegexTextFilter(BaseFilter[Message]):
    event_type = Message

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self.regex = re.compile(pattern)

    def __call__(self, message: Message) -> bool:
        return bool(self.regex.search(message.text))


class MediaFilter(BaseFilter[Message]):
    event_type = Message

    def __call__(self, message: Message) -> bool:
        return message.attaches is not None and len(message.attaches) > 0


class FileFilter(BaseFilter[Message]):
    event_type = Message

    def __call__(self, message: Message) -> bool:
        if message.attaches is None:
            return False
        return any(attach.type == AttachType.FILE for attach in message.attaches)


class Filters:
    @staticmethod
    def chat(chat_id: int) -> BaseFilter[Message]:
        return ChatFilter(chat_id)

    @staticmethod
    def text(text: str) -> BaseFilter[Message]:
        return TextFilter(text)

    @staticmethod
    def sender(user_id: int) -> BaseFilter[Message]:
        return SenderFilter(user_id)

    @staticmethod
    def status(status: MessageStatus) -> BaseFilter[Message]:
        return StatusFilter(status)

    @staticmethod
    def text_contains(substring: str) -> BaseFilter[Message]:
        return TextContainsFilter(substring)

    @staticmethod
    def text_matches(pattern: str) -> BaseFilter[Message]:
        return RegexTextFilter(pattern)

    @staticmethod
    def has_media() -> BaseFilter[Message]:
        return MediaFilter()

    @staticmethod
    def has_file() -> BaseFilter[Message]:
        return FileFilter()

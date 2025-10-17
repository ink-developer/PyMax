from .static.enum import MessageStatus, MessageType
from .types import Message


class Filter:
    def __init__(
        self,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: list[str] | None = None,
        status: MessageStatus | str | None = None,
        type: MessageType | str | None = None,
        text_contains: str | None = None,
        reaction_info: bool | None = None,
    ) -> None:
        self.chat_id = chat_id
        self.user_id = user_id
        self.text = text
        self.status = status
        self.type = type
        self.reaction_info = reaction_info
        self.text_contains = text_contains

    def match(self, message: Message) -> bool:
        if self.chat_id is not None and message.chat_id != self.chat_id:
            return False
        if self.user_id is not None and message.sender != self.user_id:
            return False
        if self.text is not None and any(
            text not in message.text for text in self.text
        ):
            return False
        if (
            self.text_contains is not None
            and self.text_contains not in message.text
        ):
            return False
        if self.status is not None and message.status != self.status:
            return False
        if self.type is not None and message.type != self.type:
            return False
        if (
            self.reaction_info is not None and message.reactionInfo is None
        ):  # noqa: SIM103
            return False

        return True

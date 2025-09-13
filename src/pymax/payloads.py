from typing import Any, Literal

from pydantic import BaseModel, Field

from .static import AuthType


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
    }


class BaseWebSocketMessage(BaseModel):
    ver: int = 11
    cmd: int
    seq: int
    opcode: int
    payload: dict[str, Any]


class RequestCodePayload(CamelModel):
    phone: str
    type: AuthType = AuthType.START_AUTH
    language: str = "ru"


class SendCodePayload(CamelModel):
    token: str
    verify_code: str
    auth_token_type: AuthType = AuthType.CHECK_CODE


class SyncPayload(CamelModel):
    interactive: bool = True
    token: str
    chats_sync: int = 0
    contacts_sync: int = 0
    presence_sync: int = 0
    drafts_sync: int = 0
    chats_count: int = 40


class ReplyLink(CamelModel):
    type: str = "REPLY"
    message_id: str


class SendMessagePayloadMessage(CamelModel):
    text: str
    cid: int
    elements: list[Any]
    attaches: list[Any]
    link: ReplyLink | None = None


class SendMessagePayload(CamelModel):
    chat_id: int
    message: SendMessagePayloadMessage
    notify: bool = False


class EditMessagePayload(CamelModel):
    chat_id: int
    message_id: int
    text: str
    elements: list[Any]
    attaches: list[Any]


class DeleteMessagePayload(CamelModel):
    chat_id: int
    message_ids: list[int]
    for_me: bool = False


class FetchContactsPayload(CamelModel):
    contact_ids: list[int]


class FetchHistoryPayload(CamelModel):
    chat_id: int
    from_time: int = Field(alias="from")
    forward: int
    backward: int = 200
    get_messages: bool = True


class ChangeProfilePayload(CamelModel):
    first_name: str
    last_name: str | None = None
    description: str | None = None


class ResolveLinkPayload(CamelModel):
    link: str


class PinMessagePayload(CamelModel):
    chat_id: int
    notify_pin: bool
    pin_message_id: int


class CreateGroupAttach(CamelModel):
    type: Literal["CONTROL"] = Field("CONTROL", alias="_type")
    event: str = "new"
    chat_type: str = "CHAT"
    title: str
    user_ids: list[int]


class CreateGroupMessage(CamelModel):
    cid: int
    attaches: list[CreateGroupAttach]


class CreateGroupPayload(CamelModel):
    message: CreateGroupMessage
    notify: bool = True


class InviteUsersPayload(CamelModel):
    chat_id: int
    user_ids: list[int]
    show_history: bool
    operation: str = "add"


class RemoveUsersPayload(CamelModel):
    chat_id: int
    user_ids: list[int]
    operation: str = "remove"
    clean_msg_period: int


class ChangeGroupSettingsOptions(BaseModel):
    ONLY_OWNER_CAN_CHANGE_ICON_TITLE: bool | None
    ALL_CAN_PIN_MESSAGE: bool | None
    ONLY_ADMIN_CAN_ADD_MEMBER: bool | None
    ONLY_ADMIN_CAN_CALL: bool | None
    MEMBERS_CAN_SEE_PRIVATE_LINK: bool | None


class ChangeGroupSettingsPayload(CamelModel):
    chat_id: int
    options: ChangeGroupSettingsOptions


class ChangeGroupProfilePayload(CamelModel):
    chat_id: int
    theme: str | None
    description: str | None


class GetGroupMembersPayload(CamelModel):
    type: str = "MEMBER"
    marker: int
    chat_id: int
    count: int

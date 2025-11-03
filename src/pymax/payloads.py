from typing import Any, Final, Literal

from pydantic import AliasChoices, BaseModel, Field

from pymax.static.constant import (
    DEFAULT_APP_VERSION,
    DEFAULT_DEVICE_LOCALE,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_LOCALE,
    DEFAULT_OS_VERSION,
    DEFAULT_SCREEN,
    DEFAULT_TIMEZONE,
    DEFAULT_USER_AGENT,
)
from pymax.static.enum import AttachType, AuthType


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


class BaseWebSocketMessage(BaseModel):
    ver: Final[int] = 11
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


class UploadPhotoPayload(CamelModel):
    count: int = 1


class AttachPhotoPayload(CamelModel):
    type: AttachType = Field(default=AttachType.PHOTO, alias="_type")
    photo_token: str


class MessageElement(CamelModel):
    type: str
    from_: int = Field(..., alias="from")
    length: int


class SendMessagePayloadMessage(CamelModel):
    text: str
    cid: int
    elements: list[MessageElement]
    attaches: list[AttachPhotoPayload]
    link: ReplyLink | None = None


class SendMessagePayload(CamelModel):
    chat_id: int
    message: SendMessagePayloadMessage
    notify: bool = False


class EditMessagePayload(CamelModel):
    chat_id: int
    message_id: int
    text: str
    elements: list[MessageElement]
    attaches: list[AttachPhotoPayload]


class DeleteMessagePayload(CamelModel):
    chat_id: int
    message_ids: list[int]
    for_me: bool = False


class FetchContactsPayload(CamelModel):
    contact_ids: list[int]


class FetchHistoryPayload(CamelModel):
    chat_id: int
    from_time: int = Field(
        validation_alias=AliasChoices("from_time", "from"),
        serialization_alias="from",
    )
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
    type: Final[str] = "MEMBER"
    marker: int
    chat_id: int
    count: int


class SearchGroupMembersPayload(CamelModel):
    type: Final[str] = "MEMBER"
    query: str
    chat_id: int


class NavigationEventParams(BaseModel):
    action_id: int
    screen_to: int
    screen_from: int | None = None
    source_id: int
    session_id: int


class NavigationEventPayload(CamelModel):
    event: str
    time: int
    type: str = "NAV"
    user_id: int
    params: NavigationEventParams


class NavigationPayload(CamelModel):
    events: list[NavigationEventPayload]


class GetVideoPayload(CamelModel):
    chat_id: int
    message_id: int | str
    video_id: int


class GetFilePayload(CamelModel):
    chat_id: int
    message_id: str | int
    file_id: int


class SearchByPhonePayload(CamelModel):
    phone: str


class JoinGroupPayload(CamelModel):
    link: str


class ReactionInfoPayload(CamelModel):
    reaction_type: str = "EMOJI"
    id: str


class AddReactionPayload(CamelModel):
    chat_id: int
    message_id: str
    reaction: ReactionInfoPayload


class GetReactionsPayload(CamelModel):
    chat_id: int
    message_ids: list[str]


class RemoveReactionPayload(CamelModel):
    chat_id: int
    message_id: str


class UserAgentPayload(CamelModel):
    device_type: str = Field(default=DEFAULT_DEVICE_TYPE)
    locale: str = Field(default=DEFAULT_LOCALE)
    device_locale: str = Field(default=DEFAULT_DEVICE_LOCALE)
    os_version: str = Field(default=DEFAULT_OS_VERSION)
    device_name: str = Field(default=DEFAULT_DEVICE_NAME)
    header_user_agent: str = Field(default=DEFAULT_USER_AGENT)
    app_version: str = Field(default=DEFAULT_APP_VERSION)
    screen: str = Field(default=DEFAULT_SCREEN)
    timezone: str = Field(default=DEFAULT_TIMEZONE)


class ReworkInviteLinkPayload(CamelModel):
    revoke_private_link: bool = True
    chat_id: int


class RegisterPayload(CamelModel):
    last_name: str | None = None
    first_name: str
    token: str
    token_type: AuthType = AuthType.REGISTER

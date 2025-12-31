from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field

from pymax.static.constant import (
    DEFAULT_APP_VERSION,
    DEFAULT_BUILD_NUMBER,
    DEFAULT_CLIENT_SESSION_ID,
    DEFAULT_DEVICE_LOCALE,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_LOCALE,
    DEFAULT_OS_VERSION,
    DEFAULT_SCREEN,
    DEFAULT_TIMEZONE,
    DEFAULT_USER_AGENT,
)
from pymax.static.enum import AttachType, AuthType, Capability, ContactAction, ReadAction


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
    ver: Literal[10, 11] = 11
    cmd: int
    seq: int
    opcode: int
    payload: dict[str, Any]


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
    client_session_id: int = Field(default=DEFAULT_CLIENT_SESSION_ID)
    build_number: int = Field(default=DEFAULT_BUILD_NUMBER)


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
    user_agent: UserAgentPayload = Field(
        default_factory=lambda: UserAgentPayload(
            device_type=DEFAULT_DEVICE_TYPE,
            locale=DEFAULT_LOCALE,
            device_locale=DEFAULT_DEVICE_LOCALE,
            os_version=DEFAULT_OS_VERSION,
            device_name=DEFAULT_DEVICE_NAME,
            header_user_agent=DEFAULT_USER_AGENT,
            app_version=DEFAULT_APP_VERSION,
            screen=DEFAULT_SCREEN,
            timezone=DEFAULT_TIMEZONE,
            client_session_id=DEFAULT_CLIENT_SESSION_ID,
            build_number=DEFAULT_BUILD_NUMBER,
        ),
    )


class ReplyLink(CamelModel):
    type: str = "REPLY"
    message_id: str


class UploadPayload(CamelModel):
    count: int = 1
    profile: bool = False


class AttachPhotoPayload(CamelModel):
    type: AttachType = Field(default=AttachType.PHOTO, alias="_type")
    photo_token: str


class VideoAttachPayload(CamelModel):
    type: AttachType = Field(default=AttachType.VIDEO, alias="_type")
    video_id: int
    token: str


class AttachFilePayload(CamelModel):
    type: AttachType = Field(default=AttachType.FILE, alias="_type")
    file_id: int


class MessageElement(CamelModel):
    type: str
    from_: int = Field(..., alias="from")
    length: int


class SendMessagePayloadMessage(CamelModel):
    text: str
    cid: int
    elements: list[MessageElement]
    attaches: list[AttachPhotoPayload | AttachFilePayload | VideoAttachPayload]
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
    attaches: list[AttachPhotoPayload | AttachFilePayload | VideoAttachPayload]


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
    photo_token: str | None = None
    avatar_type: str = "USER_AVATAR"  # TODO: вынести гада в энам


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
    type: Literal["MEMBER"] = "MEMBER"
    marker: int | None = None
    chat_id: int
    count: int


class SearchGroupMembersPayload(CamelModel):
    type: Literal["MEMBER"] = "MEMBER"
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


class JoinChatPayload(CamelModel):
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


class ReworkInviteLinkPayload(CamelModel):
    revoke_private_link: bool = True
    chat_id: int


class ContactActionPayload(CamelModel):
    contact_id: int
    action: ContactAction


class RegisterPayload(CamelModel):
    last_name: str | None = None
    first_name: str
    token: str
    token_type: AuthType = AuthType.REGISTER


class CreateFolderPayload(CamelModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any] = []


class GetChatInfoPayload(CamelModel):
    chat_ids: list[int]


class GetFolderPayload(CamelModel):
    folder_sync: int = 0


class UpdateFolderPayload(CamelModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any] = []
    options: list[Any] = []


class DeleteFolderPayload(CamelModel):
    folder_ids: list[str]


class LeaveChatPayload(CamelModel):
    chat_id: int


class FetchChatsPayload(CamelModel):
    marker: int


class ReadMessagesPayload(CamelModel):
    type: ReadAction
    chat_id: int
    message_id: str
    mark: int


class CheckPasswordChallengePayload(CamelModel):
    track_id: str
    password: str


class CreateTrackPayload(CamelModel):
    type: int = 0


class SetPasswordPayload(CamelModel):
    track_id: str
    password: str


class SetHintPayload(CamelModel):
    track_id: str
    hint: str


class SetTwoFactorPayload(CamelModel):
    expected_capabilities: list[Capability]
    track_id: str
    password: str
    hint: str | None = None


class RequestEmailCodePayload(CamelModel):
    track_id: str
    email: str


class SendEmailCodePayload(CamelModel):
    track_id: str
    verify_code: str

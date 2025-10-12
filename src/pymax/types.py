from typing import Any

from typing_extensions import override

from .static import (
    AccessType,
    AttachType,
    ChatType,
    ElementType,
    MessageStatus,
    MessageType,
)


class Names:
    def __init__(
        self, name: str, first_name: str, last_name: str | None, type: str
    ) -> None:
        self.name = name
        self.first_name = first_name
        self.last_name = last_name
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Names":
        return cls(
            name=data["name"],
            first_name=data["firstName"],
            last_name=data.get("lastName"),
            type=data["type"],
        )

    @override
    def __repr__(self) -> str:
        return f"Names(name={self.name!r}, first_name={self.first_name!r}, last_name={self.last_name!r}, type={self.type!r})"

    @override
    def __str__(self) -> str:
        return self.name


class PhotoAttach:
    def __init__(
        self,
        base_url: str,
        height: int,
        width: int,
        photo_id: int,
        photo_token: str,
        preview_data: str | None,
        type: AttachType,
    ) -> None:
        self.base_url = base_url
        self.height = height
        self.width = width
        self.photo_id = photo_id
        self.photo_token = photo_token
        self.preview_data = preview_data
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhotoAttach":
        return cls(
            base_url=data["baseUrl"],
            height=data["height"],
            width=data["width"],
            photo_id=data["photoId"],
            photo_token=data["photoToken"],
            preview_data=data.get("previewData"),
            type=AttachType(data["_type"]),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"PhotoAttach(photo_id={self.photo_id!r}, base_url={self.base_url!r}, "
            f"height={self.height!r}, width={self.width!r}, photo_token={self.photo_token!r}, "
            f"preview_data={self.preview_data!r}, type={self.type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"PhotoAttach: {self.photo_id}"


class VideoAttach:
    def __init__(
        self,
        height: int,
        width: int,
        video_id: int,
        duration: int,
        preview_data: str,
        type: AttachType,
        thumbnail: str,
        token: str,
        video_type: int,
    ) -> None:
        self.height = height
        self.width = width
        self.video_id = video_id
        self.duration = duration
        self.preview_data = preview_data
        self.type = type
        self.thumbnail = thumbnail
        self.token = token
        self.video_type = video_type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoAttach":
        return cls(
            height=data["height"],
            width=data["width"],
            video_id=data["videoId"],
            duration=data["duration"],
            preview_data=data["previewData"],
            type=AttachType(data["_type"]),
            thumbnail=data["thumbnail"],
            token=data["token"],
            video_type=data["videoType"],
        )

    @override
    def __repr__(self) -> str:
        return (
            f"VideoAttach(video_id={self.video_id!r}, height={self.height!r}, "
            f"width={self.width!r}, duration={self.duration!r}, "
            f"preview_data={self.preview_data!r}, type={self.type!r}, "
            f"thumbnail={self.thumbnail!r}, token={self.token!r}, "
            f"video_type={self.video_type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"VideoAttach: {self.video_id}"


class FileAttach:
    def __init__(
        self, file_id: int, name: str, size: int, token: str, type: AttachType
    ) -> None:
        self.file_id = file_id
        self.name = name
        self.size = size
        self.token = token
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileAttach":
        return cls(
            file_id=data["fileId"],
            name=data["name"],
            size=data["size"],
            token=data["token"],
            type=AttachType(data["_type"]),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"FileAttach(file_id={self.file_id!r}, name={self.name!r}, "
            f"size={self.size!r}, token={self.token!r}, type={self.type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"FileAttach: {self.file_id}"


class FileRequest:
    def __init__(
        self,
        unsafe: bool,
        url: str,
    ) -> None:
        self.unsafe = unsafe
        self.url = url

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRequest":
        return cls(
            unsafe=data["unsafe"],
            url=data["url"],
        )


class VideoRequest:
    def __init__(
        self,
        external: str,
        cache: bool,
        url: str,
    ) -> None:
        self.external = external
        self.cache = cache
        self.url = url

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoRequest":
        # listdata = list(data.values()) # Костыль ✅
        url = [v for k, v in data.items() if k not in ("EXTERNAL", "cache")][
            0
        ]  # Еще больший костыль ✅
        return cls(
            external=data["EXTERNAL"],
            cache=data["cache"],
            url=url,
        )


class Me:
    def __init__(
        self,
        id: int,
        account_status: int,
        phone: str,
        names: list[Names],
        update_time: int,
        options: list[str] | None = None,
    ) -> None:
        self.id = id
        self.account_status = account_status
        self.phone = phone
        self.update_time = update_time
        self.options = options
        self.names = names

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Me":
        return cls(
            id=data["id"],
            account_status=data["accountStatus"],
            phone=data["phone"],
            names=[Names.from_dict(n) for n in data["names"]],
            update_time=data["updateTime"],
            options=data.get("options"),
        )

    @override
    def __repr__(self) -> str:
        return f"Me(id={self.id!r}, account_status={self.account_status!r}, phone={self.phone!r}, names={self.names!r}, update_time={self.update_time!r}, options={self.options!r})"

    @override
    def __str__(self) -> str:
        return f"Me {self.id}: {', '.join(str(n) for n in self.names)}"


class Element:
    def __init__(
        self, type: ElementType | str, length: int, from_: int | None = None
    ) -> None:
        self.type = type
        self.length = length
        self.from_ = from_

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> "Element":
        return cls(type=data["type"], length=data["length"], from_=data.get("from"))

    @override
    def __repr__(self) -> str:
        return (
            f"Element(type={self.type!r}, length={self.length!r}, from_={self.from_!r})"
        )

    @override
    def __str__(self) -> str:
        return f"{self.type}({self.length})"


class Message:
    def __init__(
        self,
        chat_id: int | None,
        sender: int | None,
        elements: list[Element] | None,
        reaction_info: dict[str, Any] | None,
        options: int | None,
        id: int,
        time: int,
        text: str,
        status: MessageStatus | str | None,
        type: MessageType | str,
        attaches: list[PhotoAttach | VideoAttach | FileAttach],
    ) -> None:
        self.chat_id = chat_id
        self.sender = sender
        self.elements = elements
        self.options = options
        self.id = id
        self.time = time
        self.text = text
        self.type = type
        self.attaches = attaches
        self.status = status
        self.reactionInfo = reaction_info

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> "Message":
        message = data["message"] if data.get("message") else data
        attaches = []
        for a in message.get("attaches", []):
            if a["_type"] == AttachType.PHOTO:
                attaches.append(PhotoAttach.from_dict(a))
            elif a["_type"] == AttachType.VIDEO:
                attaches.append(VideoAttach.from_dict(a))
            elif a["_type"] == AttachType.FILE:
                attaches.append(FileAttach.from_dict(a))
        return cls(
            chat_id=data.get("chatId"),
            sender=message.get("sender"),
            elements=[Element.from_dict(e) for e in message.get("elements", [])],
            options=message.get("options"),
            id=message["id"],
            time=message["time"],
            text=message["text"],
            type=message["type"],
            attaches=attaches,
            status=message.get("status"),
            reaction_info=message.get("reactionInfo"),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"Message(id={self.id!r}, sender={self.sender!r}, text={self.text!r}, "
            f"type={self.type!r}, status={self.status!r}, elements={self.elements!r})"
            f"attaches={self.attaches!r}, chat_id={self.chat_id!r}, time={self.time!r}, options={self.options!r}, reactionInfo={self.reactionInfo!r})"
        )

    @override
    def __str__(self) -> str:
        return f"Message {self.id} from {self.sender}: {self.text}"


class Dialog:
    def __init__(
        self,
        cid: int | None,
        owner: int,
        has_bots: bool | None,
        join_time: int,
        created: int,
        last_message: Message | None,
        type: ChatType | str,
        last_fire_delayed_error_time: int,
        last_delayed_update_time: int,
        prev_message_id: str | None,
        options: dict[str, bool],
        modified: int,
        last_event_time: int,
        id: int,
        status: str,
        participants: dict[str, int],
    ) -> None:
        self.cid = cid
        self.owner = owner
        self.has_bots = has_bots
        self.join_time = join_time
        self.created = created
        self.last_message = last_message
        self.type = type
        self.last_fire_delayed_error_time = last_fire_delayed_error_time
        self.last_delayed_update_time = last_delayed_update_time
        self.prev_message_id = prev_message_id
        self.options = options
        self.modified = modified
        self.last_event_time = last_event_time
        self.id = id
        self.status = status
        self.participants = participants

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> "Dialog":
        return cls(
            cid=data.get("cid"),
            owner=data["owner"],
            has_bots=data.get("hasBots"),
            join_time=data["joinTime"],
            created=data["created"],
            last_message=Message.from_dict(data["lastMessage"])
            if data.get("lastMessage")
            else None,
            type=ChatType(data["type"]),
            last_fire_delayed_error_time=data["lastFireDelayedErrorTime"],
            last_delayed_update_time=data["lastDelayedUpdateTime"],
            prev_message_id=data.get("prevMessageId"),
            options=data.get("options", {}),
            modified=data["modified"],
            last_event_time=data["lastEventTime"],
            id=data["id"],
            status=data["status"],
            participants=data["participants"],
        )

    @override
    def __repr__(self) -> str:
        return f"Dialog(id={self.id!r}, owner={self.owner!r}, type={self.type!r}, last_message={self.last_message!r})"

    @override
    def __str__(self) -> str:
        return f"Dialog {self.id} ({self.type})"


class Chat:
    def __init__(
        self,
        participants_count: int,
        access: AccessType | str,
        invited_by: int | None,
        link: str | None,
        chat_type: ChatType | str,
        title: str | None,
        last_fire_delayed_error_time: int,
        last_delayed_update_time: int,
        options: dict[str, bool],
        base_raw_icon_url: str | None,
        base_icon_url: str | None,
        description: str | None,
        modified: int,
        id_: int,
        admin_participants: dict[int, dict[Any, Any]],
        participants: dict[int, int],
        owner: int,
        join_time: int,
        created: int,
        last_message: Message | None,
        prev_message_id: str | None,
        last_event_time: int,
        messages_count: int,
        admins: list[int],
        restrictions: int | None,
        status: str,
        cid: int,
    ) -> None:
        self.participants_count = participants_count
        self.access = access
        self.invited_by = invited_by
        self.link = link
        self.type = chat_type
        self.title = title
        self.last_fire_delayed_error_time = last_fire_delayed_error_time
        self.last_delayed_update_time = last_delayed_update_time
        self.options = options
        self.base_raw_icon_url = base_raw_icon_url
        self.base_icon_url = base_icon_url
        self.description = description
        self.modified = modified
        self.id = id_
        self.admin_participants = admin_participants
        self.participants = participants
        self.owner = owner
        self.join_time = join_time
        self.created = created
        self.last_message = last_message
        self.prev_message_id = prev_message_id
        self.last_event_time = last_event_time
        self.messages_count = messages_count
        self.admins = admins
        self.restrictions = restrictions
        self.status = status
        self.cid = cid

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> "Chat":
        raw_admins = data.get("adminParticipants", {}) or {}
        admin_participants: dict[int, dict[Any, Any]] = {
            int(k): v for k, v in raw_admins.items()
        }
        raw_participants = data.get("participants", {}) or {}
        participants: dict[int, int] = {int(k): v for k, v in raw_participants.items()}
        last_msg = (
            Message.from_dict(data["lastMessage"]) if data.get("lastMessage") else None
        )
        return cls(
            participants_count=data.get("participantsCount", 0),
            access=AccessType(data.get("access", AccessType.PUBLIC.value)),
            invited_by=data.get("invitedBy"),
            link=data.get("link"),
            base_raw_icon_url=data.get("baseRawIconUrl"),
            base_icon_url=data.get("baseIconUrl"),
            description=data.get("description"),
            chat_type=ChatType(data.get("type", ChatType.CHAT.value)),
            title=data.get("title"),
            last_fire_delayed_error_time=data.get("lastFireDelayedErrorTime", 0),
            last_delayed_update_time=data.get("lastDelayedUpdateTime", 0),
            options=data.get("options", {}),
            modified=data.get("modified", 0),
            id_=data.get("id", 0),
            admin_participants=admin_participants,
            participants=participants,
            owner=data.get("owner", 0),
            join_time=data.get("joinTime", 0),
            created=data.get("created", 0),
            last_message=last_msg,
            prev_message_id=data.get("prevMessageId"),
            last_event_time=data.get("lastEventTime", 0),
            messages_count=data.get("messagesCount", 0),
            admins=data.get("admins", []),
            restrictions=data.get("restrictions"),
            status=data.get("status", ""),
            cid=data.get("cid", 0),
        )

    @override
    def __repr__(self) -> str:
        return f"Chat(id={self.id!r}, title={self.title!r}, type={self.type!r})"

    @override
    def __str__(self) -> str:
        return f"{self.title} ({self.type})"


class Channel(Chat):
    @override
    def __repr__(self) -> str:
        return f"Channel(id={self.id!r}, title={self.title!r})"

    @override
    def __str__(self) -> str:
        return f"Channel: {self.title}"


class User:
    def __init__(
        self,
        account_status: int,
        update_time: int,
        id: int,
        names: list[Names],
        options: list[str] | None = None,
        base_url: str | None = None,
        base_raw_url: str | None = None,
        photo_id: int | None = None,
        description: str | None = None,
        gender: int | None = None,
        link: str | None = None,
        web_app: str | None = None,
        menu_button: dict[str, Any] | None = None,
    ) -> None:
        self.account_status = account_status
        self.update_time = update_time
        self.id = id
        self.names = names
        self.options = options or []
        self.base_url = base_url
        self.base_raw_url = base_raw_url
        self.photo_id = photo_id
        self.description = description
        self.gender = gender
        self.link = link
        self.web_app = web_app
        self.menu_button = menu_button

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        return cls(
            account_status=data["accountStatus"],
            update_time=data["updateTime"],
            id=data["id"],
            names=[Names.from_dict(n) for n in data.get("names", [])],
            options=data.get("options"),
            base_url=data.get("baseUrl"),
            base_raw_url=data.get("baseRawUrl"),
            photo_id=data.get("photoId"),
            description=data.get("description"),
            gender=data.get("gender"),
            link=data.get("link"),
            web_app=data.get("webApp"),
            menu_button=data.get("menuButton"),
        )

    @override
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, names={self.names!r}, status={self.account_status!r})"

    @override
    def __str__(self) -> str:
        return f"User {self.id}: {', '.join(str(n) for n in self.names)}"


class Attach:  # УБРАТЬ ГАДА!!! или нет...
    def __init__(
        self,
        _type: AttachType,
        video_id: int | None = None,
        photo_token: str | None = None,
        file_id: int | None = None,
        token: str | None = None,
    ) -> None:
        self.type = _type
        self.video_id = video_id
        self.photo_token = photo_token
        self.file_id = file_id
        self.token = token

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attach":
        return cls(
            _type=AttachType(data["type"]),
            video_id=data.get("videoId"),
            photo_token=data.get("photoToken"),
            file_id=data.get("fileId"),
            token=data.get("token"),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"Attach(type={self.type!r}, video_id={self.video_id!r}, "
            f"photo_token={self.photo_token!r}, file_id={self.file_id!r}, token={self.token!r})"
        )

    @override
    def __str__(self) -> str:
        return f"Attach: {self.type}"

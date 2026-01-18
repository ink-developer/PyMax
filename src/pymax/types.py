from typing import Any

from typing_extensions import Self, override

from .static.enum import (
    AccessType,
    AttachType,
    ChatType,
    FormattingType,
    MessageStatus,
    MessageType,
)

# TODO: все это нужно переделать на pydantic модели.
# Я просто придерживаюсь текущего стиля.
# - 6RUN0
# Хз, а в чем аргументация, так контроля больше и пайдентик модели явного преимущества не дают.
# - ink-developer


class Presence:
    def __init__(self, seen: int | None) -> None:
        """
        Присутствие пользователя.

        {
            "seen": {{ unix timestamp }}
        },
        """
        # TODO надо сделать пребразование в datetime с учетом таймзоны
        self.seen = seen

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(seen=data.get("seen"))

    @override
    def __repr__(self) -> str:
        return f"Presence(seen={self.seen!r})"

    @override
    def __str__(self) -> str:
        return f"{self.seen}"


class Name:
    def __init__(
        self,
        name: str | None,
        first_name: None | str,
        last_name: str | None,
        type: str | None,
    ) -> None:
        """
        Структура имени пользователя.

        Структура может поменяться, ничего не гарантируется.
        На данный момент она такая:
        {
            "name": "Василий",
            "firstName": "Пупкин",
            "lastName": "Чеевич",
            "type": "ONEME"
        }
        """
        self.name = name
        self.first_name = first_name
        self.last_name = last_name
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data.get("name"),
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            type=data.get("type"),
        )

    @override
    def __repr__(self) -> str:
        return f"Name(name={self.name!r}, first_name={self.first_name!r}, last_name={self.last_name!r}, type={self.type!r})"

    @override
    def __str__(self) -> str:
        return self.name or ""


class Names(Name):
    def __init__(
        self,
        name: str | None,
        first_name: None | str,
        last_name: str | None,
        type: str | None,
    ) -> None:
        """
        Синоним для класса Name.
        """
        super().__init__(name=name, first_name=first_name, last_name=last_name, type=type)


class Contact:
    def __init__(
        self,
        id: int | None,
        account_status: int | None,
        base_raw_url: str | None,
        base_url: str | None,
        names: list[Name] | None,
        options: list[str] | None,
        photo_id: int | None,
        update_time: int | None,
    ) -> None:
        """
        Контакт.

        Сруктура:
        {
            "accountStatus": 0,
            "baseUrl": "https://i.oneme.ru/i?r=...",
            "names": [
                Name{},
            ],
            "options": [
                "TT",
                "ONEME"
            ],
            "photoId": {{ file id }},
            "updateTime": 0,
            "id": {{ user id }},
            "baseRawUrl": "https://i.oneme.ru/i?r=..."
        }
        """
        self.id = id
        self.account_status = account_status
        self.base_raw_url = base_raw_url
        self.base_url = base_url
        self.names = names
        self.options = options or []
        self.photo_id = photo_id
        # TODO надо сделать пребразование в datetime с учетом таймзоны
        self.update_time = update_time

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            account_status=data.get("accountStatus"),
            update_time=data.get("updateTime"),
            id=data.get("id"),
            names=[Name.from_dict(n) for n in data.get("names", [])],
            options=data.get("options"),
            base_url=data.get("baseUrl"),
            base_raw_url=data.get("baseRawUrl"),
            photo_id=data.get("photoId"),
        )

    @override
    def __repr__(self) -> str:
        return f"Contact(id={self.id!r}, names={self.names!r}, status={self.account_status!r})"

    @override
    def __str__(self) -> str:
        return f"Contact {self.id}: {', '.join(str(n) for n in self.names or [])}"


class Member:
    def __init__(
        self,
        contact: Contact,
        presence: Presence,
        read_mark: int | None,
    ) -> None:
        """
        Участник чата.

        Структура:
        {
            "presence": Presence{}
            "readMark": {{ timestamp with milliseconds }},
            "contact": Contact{}
        },
        """
        self.presence = presence
        # TODO надо сделать пребразование в datetime с учетом таймзоны
        self.read_mark = read_mark
        self.contact = contact

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        presence_value = data.get("presence")
        if isinstance(presence_value, dict):
            presence = Presence.from_dict(presence_value)
        else:
            presence = Presence.from_dict({})
        contact_value = data.get("contact")
        if isinstance(contact_value, dict):
            contact = Contact.from_dict(contact_value)
        else:
            contact = Contact.from_dict({})
        return cls(
            contact=contact,
            presence=presence,
            read_mark=data.get("readMark"),
        )

    @override
    def __repr__(self) -> str:
        return f"Member(presence={self.presence!r}, read_mark={self.read_mark!r}, contact={self.contact!r})"

    @override
    def __str__(self) -> str:
        return f"Member {self.contact.id}: {', '.join(str(n) for n in self.contact.names or [])}"


class StickerAttach:
    def __init__(
        self,
        author_type: str,
        lottie_url: str | None,
        url: str,
        sticker_id: int,
        tags: list[str] | None,
        width: int,
        set_id: int,
        time: int,
        sticker_type: str,
        audio: bool,
        height: int,
        type: AttachType,
    ):
        self.author_type = author_type
        self.lottie_url = lottie_url
        self.url = url
        self.sticker_id = sticker_id
        self.tags = tags
        self.width = width
        self.set_id = set_id
        self.time = time
        self.sticker_type = sticker_type
        self.audio = audio
        self.height = height
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            author_type=data["authorType"],
            lottie_url=data.get("lottieUrl"),
            url=data["url"],
            sticker_id=data["stickerId"],
            tags=data.get("tags"),
            width=data["width"],
            set_id=data["setId"],
            time=data["time"],
            sticker_type=data["stickerType"],
            audio=data["audio"],
            height=data["height"],
            type=AttachType(data["_type"]),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"StickerAttach(author_type={self.author_type!r}, lottie_url={self.lottie_url!r}, "
            f"url={self.url!r}, sticker_id={self.sticker_id!r}, tags={self.tags!r}, "
            f"width={self.width!r}, set_id={self.set_id!r}, time={self.time!r}, "
            f"sticker_type={self.sticker_type!r}, audio={self.audio!r}, height={self.height!r}, "
            f"type={self.type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"StickerAttach: {self.sticker_id}"


class ControlAttach:
    def __init__(self, type: AttachType, event: str, **kwargs: dict[str, Any]) -> None:
        self.type = type
        self.event = event
        self.extra = kwargs

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        data = dict(data)
        attach_type = AttachType(data.pop("_type"))
        event = data.pop("event")
        return cls(
            type=attach_type,
            event=event,
            **data,
        )

    @override
    def __repr__(self) -> str:
        return f"ControlAttach(type={self.type!r}, event={self.event!r}, extra={self.extra!r})"

    @override
    def __str__(self) -> str:
        return f"ControlAttach: {self.event}"


class AudioAttach:
    def __init__(
        self,
        duration: int,
        audio_id: int,
        url: str,
        wave: str,
        transcription_status: str,  # TODO: сделать энам
        token: str,
        type: AttachType,
    ) -> None:
        self.duration = duration
        self.audio_id = audio_id
        self.url = url
        self.wave = wave
        self.transcription_status = transcription_status
        self.token = token
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            duration=data["duration"],
            audio_id=data["audioId"],
            url=data["url"],
            wave=data["wave"],
            transcription_status=data["transcriptionStatus"],
            token=data["token"],
            type=AttachType(data["_type"]),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"AudioAttach(duration={self.duration!r}, audio_id={self.audio_id!r}, "
            f"url={self.url!r}, wave={self.wave!r}, transcription_status={self.transcription_status!r}, "
            f"token={self.token!r}, type={self.type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"AudioAttach: {self.audio_id}"


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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def __init__(self, file_id: int, name: str, size: int, token: str, type: AttachType) -> None:
        self.file_id = file_id
        self.name = name
        self.size = size
        self.token = token
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def __init__(self, type: FormattingType | str, length: int, from_: int | None = None) -> None:
        self.type = type
        self.length = length
        self.from_ = from_

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> Self:
        return cls(type=data["type"], length=data["length"], from_=data.get("from"))

    @override
    def __repr__(self) -> str:
        return f"Element(type={self.type!r}, length={self.length!r}, from_={self.from_!r})"

    @override
    def __str__(self) -> str:
        return f"{self.type}({self.length})"


class MessageLink:
    def __init__(self, chat_id: int, message: "Message", type: str) -> None:
        self.chat_id = chat_id
        self.message = message
        self.type = type

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            chat_id=data["chatId"],
            message=Message.from_dict(data["message"]),
            type=data["type"],
        )

    @override
    def __repr__(self) -> str:
        return (
            f"MessageLink(chat_id={self.chat_id!r}, message={self.message!r}, type={self.type!r})"
        )

    @override
    def __str__(self) -> str:
        return f"MessageLink: {self.chat_id}/{self.message.id}"


class ReactionCounter:
    def __init__(self, count: int, reaction: str) -> None:
        self.count = count
        self.reaction = reaction

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(count=data["count"], reaction=data["reaction"])

    @override
    def __repr__(self) -> str:
        return f"ReactionCounter(count={self.count!r}, reaction={self.reaction!r})"

    @override
    def __str__(self) -> str:
        return f"{self.reaction}: {self.count}"


class ReactionInfo:
    def __init__(
        self,
        total_count: int,
        counters: list[ReactionCounter],
        your_reaction: str | None = None,
    ) -> None:
        self.total_count = total_count
        self.counters = counters
        self.your_reaction = your_reaction

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            total_count=data.get("totalCount", 0),
            counters=[ReactionCounter.from_dict(c) for c in data.get("counters", [])],
            your_reaction=data.get("yourReaction"),
        )


class ContactAttach:
    def __init__(
        self, contact_id: int, first_name: str, last_name: str, name: str, photo_url: str
    ) -> None:
        self.contact_id = contact_id
        self.first_name = first_name
        self.last_name = last_name
        self.name = name
        self.photo_url = photo_url
        self.type = AttachType.CONTACT

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            contact_id=data["contactId"],
            first_name=data["firstName"],
            last_name=data["lastName"],
            name=data["name"],
            photo_url=data["photoUrl"],
        )

    @override
    def __repr__(self) -> str:
        return f"ContactAttach(contact_id={self.contact_id!r}, first_name={self.first_name!r}, last_name={self.last_name!r}, name={self.name!r}, photo_url={self.photo_url!r})"

    @override
    def __str__(self) -> str:
        return f"ContactAttach: {self.name}"


class Message:
    def __init__(
        self,
        chat_id: int | None,
        sender: int | None,
        elements: list[Element] | None,
        reaction_info: ReactionInfo | None,
        options: int | None,
        id: int,
        time: int,
        link: MessageLink | None,
        text: str,
        status: MessageStatus | None,
        type: MessageType | str,
        attaches: (
            list[
                PhotoAttach
                | VideoAttach
                | FileAttach
                | ControlAttach
                | StickerAttach
                | AudioAttach
                | ContactAttach
            ]
            | None
        ),
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
        self.link = link
        self.reactionInfo = reaction_info

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> Self:
        message = data["message"] if data.get("message") else data

        # Handle case where message is a string instead of dict
        if isinstance(message, str):
            # Return a minimal Message object with just the text
            # Use current timestamp if time is not provided
            import time as time_module
            return cls(
                chat_id=data.get("chatId"),
                sender=data.get("senderId"),
                elements=None,
                options=None,
                id=data.get("messageId"),
                time=data.get("time") or int(time_module.time() * 1000),
                text=message,
                type=None,
                attaches=[],
                status=data.get("status"),
                link=None,
                reaction_info=None
            )

        attaches: list[
            PhotoAttach
            | VideoAttach
            | FileAttach
            | ControlAttach
            | StickerAttach
            | AudioAttach
            | ContactAttach
        ] = []
        for a in message.get("attaches", []):
            if a["_type"] == AttachType.PHOTO:
                attaches.append(PhotoAttach.from_dict(a))
            elif a["_type"] == AttachType.VIDEO:
                attaches.append(VideoAttach.from_dict(a))
            elif a["_type"] == AttachType.FILE:
                attaches.append(FileAttach.from_dict(a))
            elif a["_type"] == AttachType.CONTROL:
                attaches.append(ControlAttach.from_dict(a))
            elif a["_type"] == AttachType.STICKER:
                attaches.append(StickerAttach.from_dict(a))
            elif a["_type"] == AttachType.AUDIO:
                attaches.append(AudioAttach.from_dict(a))
            elif a["_type"] == AttachType.CONTACT:
                attaches.append(ContactAttach.from_dict(a))
        link_value = message.get("link")
        if isinstance(link_value, dict):
            link = MessageLink.from_dict(link_value)
        else:
            link = None
        reaction_info_value = message.get("reactionInfo")
        if isinstance(reaction_info_value, dict):
            reaction_info = ReactionInfo.from_dict(reaction_info_value)
        else:
            reaction_info = None
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
            link=link,
            reaction_info=reaction_info,
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
    def from_dict(cls, data: dict[Any, Any]) -> Self:
        return cls(
            cid=data.get("cid"),
            owner=data["owner"],
            has_bots=data.get("hasBots"),
            join_time=data["joinTime"],
            created=data["created"],
            last_message=(
                Message.from_dict(data["lastMessage"]) if data.get("lastMessage") else None
            ),
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
    def from_dict(cls, data: dict[Any, Any]) -> Self:
        raw_admins = data.get("adminParticipants", {}) or {}
        admin_participants: dict[int, dict[Any, Any]] = {int(k): v for k, v in raw_admins.items()}
        raw_participants = data.get("participants", {}) or {}
        participants: dict[int, int] = {int(k): v for k, v in raw_participants.items()}
        last_msg = Message.from_dict(data["lastMessage"]) if data.get("lastMessage") else None
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
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


class Session:
    def __init__(
        self,
        client: str,
        info: str,
        location: str,
        time: int,
        current: bool | None = None,
    ) -> None:
        self.client = client
        self.info = info
        self.location = location
        self.time = time
        self.current = current if current is not None else False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            client=data["client"],
            info=data["info"],
            location=data["location"],
            time=data["time"],
            current=data.get("current"),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"Session(client={self.client!r}, info={self.info!r}, "
            f"location={self.location!r}, time={self.time!r}, current={self.current!r})"
        )

    @override
    def __str__(self) -> str:
        return (
            f"Session: {self.client} from {self.location} at {self.time} (current={self.current})"
        )


class Folder:
    def __init__(
        self,
        source_id: int,
        include: list[int],
        options: list[Any],
        update_time: int,
        id: str,
        filters: list[Any],
        title: str,
    ) -> None:
        self.source_id = source_id
        self.include = include
        self.options = options
        self.update_time = update_time
        self.id = id
        self.filters = filters
        self.title = title

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            source_id=data.get("sourceId", 0),
            include=data.get("include", []),
            options=data.get("options", []),
            update_time=data.get("updateTime", 0),
            id=data.get("id", ""),
            filters=data.get("filters", []),
            title=data.get("title", ""),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"Folder(id={self.id!r}, title={self.title!r}, source_id={self.source_id!r}, "
            f"include={self.include!r}, options={self.options!r}, "
            f"update_time={self.update_time!r}, filters={self.filters!r})"
        )

    @override
    def __str__(self) -> str:
        return f"Folder: {self.title} ({self.id})"


class FolderUpdate:
    def __init__(
        self, folder_order: list[str] | None, folder: Folder | None, folder_sync: int
    ) -> None:
        self.folder_order = folder_order
        self.folder = folder
        self.folder_sync = folder_sync

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        folder_order = data.get("foldersOrder", [])
        folder_sync = data.get("folderSync", 0)
        folder_data = data.get("folder", {})
        folder = Folder.from_dict(folder_data)
        return cls(
            folder_order=folder_order,
            folder=folder,
            folder_sync=folder_sync,
        )

    @override
    def __repr__(self) -> str:
        return (
            f"FolderUpdate(folder_order={self.folder_order!r}, "
            f"folder={self.folder!r}, folder_sync={self.folder_sync!r})"
        )

    @override
    def __str__(self) -> str:
        return f"FolderUpdate: {self.folder.title} ({self.folder.id})"


class FolderList:
    def __init__(
        self,
        folders_order: list[str],
        folders: list[Folder],
        folder_sync: int,
        all_filter_exclude_folders: list[Any] | None = None,
    ) -> None:
        self.folders_order = folders_order
        self.folders = folders
        self.all_filter_exclude_folders = all_filter_exclude_folders or []
        self.folder_sync = folder_sync

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            folders_order=data.get("foldersOrder", []),
            folders=[Folder.from_dict(f) for f in data.get("folders", [])],
            all_filter_exclude_folders=data.get("allFilterExcludeFolders", []),
            folder_sync=data.get("folderSync", 0),
        )

    @override
    def __repr__(self) -> str:
        return (
            f"FolderList(folders_order={self.folders_order!r}, "
            f"folders={self.folders!r}, "
            f"all_filter_exclude_folders={self.all_filter_exclude_folders!r}, "
            f"folder_sync={self.folder_sync!r})"
        )

    @override
    def __str__(self) -> str:
        return f"FolderList: {len(self.folders)} folders"


class ReadState:
    def __init__(
        self,
        unread: int,
        mark: int,
    ) -> None:
        self.unread = unread
        self.mark = mark

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            unread=data["unread"],
            mark=data["mark"],
        )

    @override
    def __repr__(self) -> str:
        return f"ReadState(unread={self.unread!r}, mark={self.mark!r})"

    @override
    def __str__(self) -> str:
        return f"ReadState: unread={self.unread}, mark={self.mark}"

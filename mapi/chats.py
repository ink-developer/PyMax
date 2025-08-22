from typing import Any
from .enum import ChatType, MessageType, MessageStatus, ElementType, AccessType


class Element:
    def __init__(
        self,
        type: ElementType | str,
        length: int,
        from_: int | None = None,
    ) -> None:
        self.type = type
        self.length = length
        self.from_ = from_

    @classmethod
    def from_dict(
        cls,
        data: dict[Any, Any],
    ) -> "Element":
        return cls(type=data["type"], length=data["length"], from_=data.get("from"))


class Message:
    def __init__(
        self,
        sender: int | None,
        elements: list[Element] | None,
        reaction_info: dict[str, Any] | None,
        options: int | None,
        id: int,
        time: int,
        text: str,
        status: MessageStatus | str | None,
        type: MessageType | str,
        attaches: list[Any],
    ) -> None:
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
        return cls(
            sender=data.get("sender"),
            elements=[Element.from_dict(e) for e in data.get("elements", [])],
            options=data.get("options"),
            id=data["id"],
            time=data["time"],
            text=data["text"],
            type=data["type"],
            attaches=data.get("attaches", []),
            status=data.get("status"),
            reaction_info=data.get("reactionInfo"),
        )


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


class Channel:
    def __init__(
        self,
        participants_count: int,
        access: AccessType | str,
        invited_by: int | None,
        base_raw_icon_url: str | None,
        link: str | None,
        description: str | None,
        channel_type: ChatType | str,
        title: str | None,
        last_fire_delayed_error_time: int,
        last_delayed_update_time: int,
        options: dict[str, bool],
        modified: int,
        id_: int,
        participants: dict[int, int],
        owner: int,
        join_time: int,
        created: int,
        last_message: Message | None,
        prev_message_id: str | None,
        last_event_time: int,
        messages_count: int,
        base_icon_url: str | None,
        status: str,
        cid: int,
        restrictions: int | None = None,
    ) -> None:
        self.participants_count = participants_count
        self.access = access
        self.invited_by = invited_by
        self.base_raw_icon_url = base_raw_icon_url
        self.link = link
        self.description = description
        self.type = channel_type
        self.title = title
        self.last_fire_delayed_error_time = last_fire_delayed_error_time
        self.last_delayed_update_time = last_delayed_update_time
        self.options = options
        self.modified = modified
        self.id = id_
        self.participants = participants
        self.owner = owner
        self.join_time = join_time
        self.created = created
        self.last_message = last_message
        self.prev_message_id = prev_message_id
        self.last_event_time = last_event_time
        self.messages_count = messages_count
        self.base_icon_url = base_icon_url
        self.status = status
        self.cid = cid
        self.restrictions = restrictions

    @classmethod
    def from_dict(cls, data: dict[Any, Any]) -> "Channel":
        raw_participants = data.get("participants", {}) or {}
        participants: dict[int, int] = {int(k): v for k, v in raw_participants.items()}

        last_msg = Message.from_dict(data["lastMessage"]) if data.get("lastMessage") else None

        return cls(
            participants_count=data.get("participantsCount", 0),
            access=AccessType(data.get("access", AccessType.PUBLIC.value)),
            invited_by=data.get("invitedBy"),
            base_raw_icon_url=data.get("baseRawIconUrl"),
            link=data.get("link"),
            description=data.get("description"),
            channel_type=ChatType(data.get("type", ChatType.CHANNEL.value)),
            title=data.get("title"),
            last_fire_delayed_error_time=data.get("lastFireDelayedErrorTime", 0),
            last_delayed_update_time=data.get("lastDelayedUpdateTime", 0),
            options=data.get("options", {}),
            modified=data.get("modified", 0),
            id_=data.get("id", 0),
            participants=participants,
            owner=data.get("owner", 0),
            join_time=data.get("joinTime", 0),
            created=data.get("created", 0),
            last_message=last_msg,
            prev_message_id=data.get("prevMessageId"),
            last_event_time=data.get("lastEventTime", 0),
            messages_count=data.get("messagesCount", 0),
            base_icon_url=data.get("baseIconUrl"),
            status=data.get("status", ""),
            cid=data.get("cid", 0),
            restrictions=data.get("restrictions"),
        )

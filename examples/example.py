import asyncio
import datetime
import logging
from time import time
from typing import Any

import pymax
from pymax import MaxClient, Message, ReactionInfo, SocketMaxClient, filters
from pymax.files import File, Photo, Video
from pymax.filters import Filters
from pymax.payloads import UserAgentPayload
from pymax.static.enum import AttachType, Opcode
from pymax.types import Chat

phone = "+79991234567"
headers = UserAgentPayload(device_type="WEB")

client = MaxClient(
    phone=phone,
    work_dir="cache",
    reconnect=False,
    logger=None,
    headers=headers,
)
client.logger.setLevel(logging.INFO)


@client.on_start
async def handle_start() -> None:
    print(f"Client started as {client.me.names[0].first_name}!")


@client.on_raw_receive
async def handle_raw_receive(data: dict[str, Any]) -> None:
    print(f"Raw data received: {data}")


@client.on_reaction_change
async def handle_reaction_change(
    message_id: str, chat_id: int, reaction_info: ReactionInfo
) -> None:
    print(
        f"Reaction changed on message {message_id} in chat {chat_id}: "
        f"Total count: {reaction_info.total_count}, "
        f"Your reaction: {reaction_info.your_reaction}, "
        f"Counters: {reaction_info.counters[0].reaction}={reaction_info.counters[0].count}"
    )


@client.on_chat_update
async def handle_chat_update(chat: Chat) -> None:
    print(f"Chat updated: {chat.id}, new title: {chat.title}")


@client.on_message(Filters.chat(0) & Filters.text("hello"))
async def handle_message(message: Message) -> None:
    print(f"New message in chat {message.chat_id} from {message.sender}: {message.text}")


@client.on_message_edit()
async def handle_edited_message(message: Message) -> None:
    print(f"Edited message in chat {message.chat_id}: {message.text}")


@client.on_message_delete()
async def handle_deleted_message(message: Message) -> None:
    print(f"Deleted message in chat {message.chat_id}: {message.id}")


if __name__ == "__main__":
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("Client stopped by user")

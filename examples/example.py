import asyncio
import datetime

from pymax import MaxClient, Message, ReactionInfo, SocketMaxClient
from pymax.files import File, Video
from pymax.filters import Filter
from pymax.static.enum import AttachType, Opcode
from pymax.types import Chat

phone = "+7903223423"


client = MaxClient(phone=phone, work_dir="cache", reconnect=False, logger=None)


@client.on_start
async def handle_start() -> None:
    print(f"Client started as {client.me.names[0].first_name}!")
    folder_list = await client.get_folders()
    for folder in folder_list.folders:
        if folder.title == "My Folder Renamed":
            folder_update = await client.delete_folder(folder_id=folder.id)
            print(f"Folder deleted: {folder_update.folder_sync}")
    # folder_update = await client.create_folder(
    #     title="My Folder",
    #     chat_include=[0],
    # )
    # print(f"Folder created: {folder_update.folder.title}")
    # video_path = "tests2/test.mp4"
    # video_file = Video(path=video_path)

    # await client.send_message(
    #     text="Here is the video you requested.",
    #     chat_id=0,
    #     attachment=video_file,
    #     notify=True,
    # )
    # chat_id = -6970655
    # for chat in client.chats:
    #     if chat.id == chat_id:
    #         print(f"Found chat: {chat.title}, ID: {chat.id}")
    #         members_count = chat.participants_count
    #         marker = 0
    #         member_list = []
    #         while len(member_list) < members_count:
    #             await asyncio.sleep(10)
    #             r = await client.load_members(
    #                 chat_id=chat_id,
    #                 marker=marker,
    #                 count=200,
    #             )
    #             members, marker = r
    #             member_list.extend(members)
    #             print(f"Loaded {len(member_list)}/{members_count} members...")
    #         for member in member_list:
    #             print(
    #                 f"Member {member.contact.names[0].first_name}, ID: {member.contact.id}"
    #             )
    # r = await client.load_members(chat_id=chat_id, count=50)
    # print(f"Loaded {len(r)} members from chat {chat_id}")
    # member_list, marker = r
    # for member in member_list:
    #     print(f"Member {member.contact.names[0].first_name}, ID: {member.contact.id}")


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


# async def login_flow_test():
#     await client.connect()
#     temp_token = await client.request_code(phone)
#     code = input("Введите код: ").strip()
#     await client.login_with_code(temp_token, code)


# asyncio.run(login_flow_test())

# @client.on_message(filter=Filter(chat_id=0))
# async def handle_message(message: Message) -> None:
#     print(str(message.sender) + ": " + message.text)


# @client.on_message_edit()
# async def handle_edited_message(message: Message) -> None:
#     print(f"Edited message in chat {message.chat_id}: {message.text}")


# @client.on_message_delete()
# async def handle_deleted_message(message: Message) -> None:
#     print(f"Deleted message in chat {message.chat_id}: {message.id}")


# @client.on_start
# async def handle_start() -> None:
#     print(f"Client started successfully at {datetime.datetime.now()}!")
#     print(client.me.id)

# await client.send_message(
#     "Hello, this is a test message sent upon client start!",
#     chat_id=23424,
#     notify=True,
# )
# file_path = "ruff.toml"
# file = File(path=file_path)
# msg = await client.send_message(
#     text="Here is the file you requested.",
#     chat_id=0,
#     attachment=file,
#     notify=True,
# )
# if msg:
#     print(f"File sent successfully in message ID: {msg.id}")
# history = await client.fetch_history(chat_id=0)
# if history:
#     for message in history:
#         if message.attaches:
#             for attach in message.attaches:
#                 if attach.type == AttachType.AUDIO:
#                     print(attach.url)
# chat = await client.rework_invite_link(chat_id=0)
# print(chat.link)
# text = """
# **123**
# *123*
# __123__
# ~~123~~
# """
# message = await client.send_message(text, chat_id=0, notify=True)
# react_info = await client.add_reaction(
#     chat_id=0, message_id="115368067020359151", reaction="👍"
# )
# if react_info:
#     print("Reaction added!")
#     print(react_info.total_count)
# react_info = await client.get_reactions(
#     chat_id=0, message_ids=["115368067020359151"]
# )
# if react_info:
#     print("Reactions fetched!")
#     for msg_id, info in react_info.items():
#         print(f"Message ID: {msg_id}, Total Reactions: {info.total_count}")
# react_info = await client.remove_reaction(
#     chat_id=0, message_id="115368067020359151"
# )
# if react_info:
#     print("Reaction removed!")
#     print(react_info.total_count)
# print(client.dialogs)

# if history:
#     for message in history:
#         if message.link:
#             print(message.link.chat_id)
#             print(message.link.message.text)
# for attach in message.attaches:
#     if attach.type == AttachType.CONTROL:
#         print(attach.event)
#         print(attach.extra)
# if attach.type == AttachType.VIDEO:
#     print(message)
#     vid = await client.get_video_by_id(
#         chat_id=0,
#         video_id=attach.video_id,
#         message_id=message.id,
#     )
#     print(vid.url)
# elif attach.type == AttachType.FILE:
#     file = await client.get_file_by_id(
#         chat_id=0,
#         file_id=attach.file_id,
#         message_id=message.id,
#     )
#     print(file.url)
# print(client.me.names[0].first_name)
# user = await client.get_user(client.me.id)

# photo1 = Photo(path="tests/test.jpeg")
# photo2 = Photo(path="tests/test.jpg")

# await client.send_message(
#     "Hello with photo!", chat_id=0, photos=[photo1, photo2], notify=True
# )


if __name__ == "__main__":
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("Client stopped by user")

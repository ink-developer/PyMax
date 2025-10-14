import asyncio
import logging

from pymax import MaxClient, Message, SocketMaxClient
from pymax.files import Photo
from pymax.filters import Filter
from pymax.static import AttachType

phone = "+1234567890"


client = MaxClient(phone=phone, work_dir="cache")
# client = SocketMaxClient(phone=phone, work_dir="cache")


@client.on_message(filter=Filter(chat_id=0))
async def handle_message(message: Message) -> None:
    print(str(message.sender) + ": " + message.text)


@client.on_start
async def handle_start() -> None:
    print("Client started successfully!")
    react_info = await client.add_reaction(
        chat_id=0, message_id="115368067020359151", reaction="👍"
    )
    if react_info:
        print("Reaction added!")
        print(react_info.total_count)
    react_info = await client.get_reactions(
        chat_id=0, message_ids=["115368067020359151"]
    )
    if react_info:
        print("Reactions fetched!")
        for msg_id, info in react_info.items():
            print(f"Message ID: {msg_id}, Total Reactions: {info.total_count}")
    react_info = await client.remove_reaction(
        chat_id=0, message_id="115368067020359151"
    )
    if react_info:
        print("Reaction removed!")
        print(react_info.total_count)
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

    # print(user.names[0].first_name)

    # photo1 = Photo(path="tests/test.jpeg")
    # photo2 = Photo(path="tests/test.jpg")

    # await client.send_message(
    #     "Hello with photo!", chat_id=0, photos=[photo1, photo2], notify=True
    # )


if __name__ == "__main__":
    asyncio.run(client.start())

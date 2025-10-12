import asyncio
import logging

from pymax import MaxClient, Message, SocketMaxClient
from pymax.files import Photo
from pymax.filters import Filter
from pymax.static import AttachType

phone = "+1234567890"


client = MaxClient(phone=phone, work_dir="cache")
# client = SocketMaxClient(phone=phone, work_dir="cache")


async def main() -> None:
    for chat in client.chats:
        print(chat.title)

        message = await client.send_message(
            "Hello from MaxClient!", chat.id, notify=True
        )

        await asyncio.sleep(5)
        message = await client.edit_message(
            chat.id, message.id, "Hello from MaxClient! (edited)"
        )
        await asyncio.sleep(5)

        await client.delete_message(chat.id, [message.id], for_me=False)

    for dialog in client.dialogs:
        print(dialog.last_message.text)

    for channel in client.channels:
        print(channel.title)

    await client.close()


@client.on_message(filter=Filter(chat_id=0))
async def handle_message(message: Message) -> None:
    print(str(message.sender) + ": " + message.text)


@client.on_start
async def handle_start() -> None:
    print("Client started successfully!")
    history = await client.fetch_history(chat_id=0)
    if history:
        for message in history:
            if message.attaches:
                for attach in message.attaches:
                    if attach.type == AttachType.VIDEO:
                        vid = await client.get_video_by_id(
                            chat_id=0,
                            video_id=attach.video_id,
                            message_id=message.id,
                        )
                        print(vid.url)
                    elif attach.type == AttachType.FILE:
                        file = await client.get_file_by_id(
                            chat_id=0,
                            file_id=attach.file_id,
                            message_id=message.id,
                        )
                        print(file.url)
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

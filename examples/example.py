import asyncio
import logging

from pymax import MaxClient, Message, SocketMaxClient
from pymax.files import Photo
from pymax.filters import Filter

phone = "+1234567890"


client = SocketMaxClient(phone=phone, work_dir="cache")


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


@client.on_message(filter=Filter(text=["Привет"]))
async def handle_message(message: Message) -> None:
    print(str(message.sender) + ": " + message.text)


@client.on_start
async def handle_start() -> None:
    print("Client started successfully!")
    # history = await client.fetch_history(chat_id=0)
    # if history:
    #     for message in history:
    #         user_id = message.sender
    #         user = await client.get_user(user_id)

    #         if user:
    #             print(f"{user.names[0].name}: {message.text}")

    # print(client.me.names[0].first_name)
    # user = await client.get_user(client.me.id)

    # print(user.names[0].first_name)
    photo1 = Photo(path="tests/test.jpeg")
    photo2 = Photo(path="tests/test.jpg")

    await client.send_message(
        "Hello with photo!", chat_id=0, photos=[photo1, photo2], notify=True
    )


if __name__ == "__main__":
    asyncio.run(client.start())

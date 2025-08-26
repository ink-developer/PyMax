import asyncio

from mapi import MaxClient, Message

phone = "+1234567890"

client = MaxClient(phone=phone, work_dir="cache")


async def main() -> None:
    await client.start()

    for chat in client.chats:
        print(chat.title)

        message = await client.send_message("Hello from MaxClient!", chat.id, notify=True)

        await asyncio.sleep(5)
        message = await client.edit_message(chat.id, message.id, "Hello from MaxClient! (edited)")
        await asyncio.sleep(5)

        await client.delete_message(chat.id, [message.id], for_me=False)

    for dialog in client.dialogs:
        print(dialog.last_message.text)

    for channel in client.channels:
        print(channel.title)

    await client.close()


@client.on_message
async def handle_message(message: Message) -> None:
    print(str(message.sender) + ": " + message.text)


@client.on_start
async def handle_start() -> None:
    print("Client started successfully!")
    history = await client.fetch_history(chat_id=0)
    if history:
        for message in history:
            print(f"[{message.id}] {message.sender}: {message.text}")


if __name__ == "__main__":
    asyncio.run(client.start())

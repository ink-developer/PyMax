import asyncio

from pymax import MaxClient, Message
from pymax.filters import Filters

client = MaxClient(
    phone="+1234567890",
    work_dir="cache",
)


@client.on_message(Filters.chat(0))
async def on_message(msg: Message):
    print(f"[{msg.sender}] {msg.text}")
    await client.send_message(chat_id=msg.chat_id, text="Привет!")
    await client.add_reaction(
        chat_id=msg.chat_id, message_id=str(msg.id), reaction="👍"
    )


@client.on_start
async def on_start():
    print(f"Клиент запущен. Ваш ID: {client.me.id}")
    history = await client.fetch_history(chat_id=0)
    for m in history:
        print(f"- {m.text}")


async def main():
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())

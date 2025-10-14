import asyncio

from pymax import MaxClient, Message
from pymax.filters import Filter

phone = "+79326313810"
client = MaxClient(phone=phone, work_dir="cache")


@client.on_message(filter=Filter(chat_id=-68650840820415))
async def on_message(message: Message):
    print(f"New message from chat {message.chat_id}: {message.text}")
    print(f"Message ID: {message.id}")

    # Добавляем реакцию
    reaction = await client.add_reaction(message.chat_id, message.id, "👍")
    if reaction:
        print(f"Reaction added to message {message.id}")
    else:
        print(f"Failed to add reaction to message {message.id}")

    reactions = await client.get_reactions(message.chat_id, [str(message.id)])
    print(reactions)

@client.on_start
async def on_start():
    print("Client started! Waiting for messages to react...")


if __name__ == "__main__":
    asyncio.run(client.start())

import asyncio

import pymax
from pymax import MaxClient
from pymax.filters import Filters
from pymax.payloads import UserAgentPayload

phone = "+7903223423"
headers = UserAgentPayload(device_type="WEB")

client = MaxClient(
    phone=phone,
    work_dir="cache",
    reconnect=False,
    logger=None,
    headers=headers,
)


@client.on_message(Filters.text("test") & ~Filters.chat(0))
async def handle_message(message: pymax.Message) -> None:
    print(f"New message from {message.sender}: {message.text}")


asyncio.run(client.start())

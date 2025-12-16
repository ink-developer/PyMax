import asyncio
import logging

import pymax
import pymax.static
from pymax import MaxClient
from pymax.filters import Filters
from pymax.payloads import UserAgentPayload
from pymax.static.enum import Opcode

phone = "+7903223423"
headers = UserAgentPayload(device_type="WEB")

client = MaxClient(
    phone=phone,
    work_dir="cache",
    reconnect=False,
    logger=None,
    headers=headers,
)
client.logger.setLevel(logging.DEBUG)


@client.task(seconds=10)
async def periodic_task() -> None:
    client.logger.info("Periodic task executed")


@client.on_message(Filters.text("test") & ~Filters.chat(0))
async def handle_message(message: pymax.Message) -> None:
    print(f"New message from {message.sender}: {message.text}")


@client.on_start
async def on_start():
    print("Client started")
    data = await client._send_and_wait(
        opcode=Opcode.FILE_UPLOAD,
        payload={"count": 1},
    )
    print("File upload response:", data)
    #     opcode=pymax.static.enum.Opcode.CHATS_LIST,
    #     payload={
    #         "marker": 1765721869777,
    #     },
    # )

    # print("Chats list:", data)


asyncio.run(client.start())

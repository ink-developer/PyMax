import asyncio

from pymax import MaxClient, SocketMaxClient
from pymax.payloads import UserAgentPayload
from pymax.static.enum import Opcode

client = MaxClient(
    phone="+79911111111",
    work_dir="cache",
)


@client.on_start
async def on_start() -> None:
    print(f"MaxClient started as {client.me.names[0].first_name}!")


asyncio.run(client.start())

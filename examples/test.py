import asyncio

from pymax import MaxClient
from pymax.payloads import UserAgentPayload

ua = UserAgentPayload(device_type="DESKTOP", app_version="25.12.13")

client = MaxClient(
    phone="+79116290861",
    work_dir="cache",
    headers=ua,
)


@client.on_start
async def on_start() -> None:
    print(f"MaxClient started as {client.me.names[0].first_name}!")


asyncio.run(client.start())

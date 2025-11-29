import asyncio

from pymax import MaxClient, SocketMaxClient

phone = "+79"


client = MaxClient(
    phone=phone,
    work_dir="cache",
)

asyncio.run(client.start())

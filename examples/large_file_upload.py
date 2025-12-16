import asyncio
import logging
from pathlib import Path

from pymax import MaxClient
from pymax.files import File, Video

client = MaxClient(phone="+1234567890", work_dir="cache", reconnect=False)
client.logger.setLevel(logging.INFO)


def create_big_file(file_path: Path, size_in_mb: int) -> None:
    with open(file_path, "wb") as f:
        f.seek(size_in_mb * 1024 * 1024 - 1)
        f.write(b"\0")


@client.on_start
async def upload_large_file_example():
    await asyncio.sleep(2)

    file_path = Path("tests2/large_file.dat")

    if not file_path.exists():
        create_big_file(file_path, size_in_mb=300)
    file_size = file_path.stat().st_size
    client.logger.info(f"File size: {file_size / (1024 * 1024):.2f} MB")

    file = File(path=str(file_path))
    chat_id = 0

    client.logger.info("Starting file upload...")

    try:
        await client.send_message(
            chat_id=chat_id,
            text="📎 Вот большой файл",
            attachment=file,
        )
        client.logger.info("File uploaded successfully!")

    except OSError as e:
        if "malloc failure" in str(e):
            client.logger.error("Memory error - file too large for current memory")
            client.logger.info("Recommendation: Upload smaller files or free up memory")
        else:
            raise


if __name__ == "__main__":
    asyncio.run(client.start())

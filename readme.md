## MApi - Python api wrapper для Max'a

## Установка

> [!IMPORTANT]
> Нужно иметь git для установки из репозитория

```bash
pip install git+https://github.com/noxzion/PyMax
```

## Пример использования:

```python
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
            user_id = message.sender
            user = await client.get_user(user_id)

            if user:
                print(f"{user.names[0].name}: {message.text}")


if __name__ == "__main__":
    asyncio.run(client.start())
```

## Разработка

Сборка пакета:

```bash
python scripts/build.py
```

## Лицензия

[MIT](LICENSE)

## Авторы

- [noxzion](https://github.com/noxzion) - исходный код пакета
- [ink](https://github.com/ink-developer) - вскрытие API и документация
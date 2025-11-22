# PyMax
Лёгкая и удобная библиотека для создания ботов в мессенджере Max.

## Быстрый старт

```python
import asyncio
from pymax import MaxClient

async def main():
    client = MaxClient(phone="+79001234567")

    @client.on_message()
    async def handle_message(message):
        user = await client.get_user(message.sender)
        user_name = user.names[0].first_name if user and user.names else "User"
        await client.send_message(
            chat_id=message.chat_id,
            text=f"Привет, {user_name}! {message.text}"
        )

    await client.start()

asyncio.run(main())
```

## Установка

```bash
# через pip
pip install -U maxapi-python
# или uv
uv add -U maxapi-python
```

## Полезные ссылки

- **[API](api.md)** - полная документация всех методов и типов
- **[Примеры](examples.md)** - готовые примеры и решения

## Ссылки

- [GitHub](https://github.com/ink-developer/PyMax)
- [PyPI](https://pypi.org/project/maxapi-python/)
- [Issues](https://github.com/ink-developer/PyMax/issues)

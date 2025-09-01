# PyMax - Python wrapper для API мессенджера Max

Быстрый и простой способ авоматизации работы в мессенджере Max.

## Быстрый старт

```python
import asyncio
from pymax import MaxClient

async def main():
    client = MaxClient(phone="+79001234567")
    
    @client.on_message
    async def handle_message(message):
        await client.send_message(
            chat_id=message.chat_id,
            text=f"Привет, {message.author.username}! {message.text}"
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

## Документация

- **[API Reference](api.md)** - документация классов и методов
- **[Примеры](examples.md)** - готовые примеры ботов

## Ссылки

- [GitHub](https://github.com/noxzion/PyMax)
- [PyPI](https://pypi.org/project/pymax/)
- [Issues](https://github.com/noxzion/PyMax/issues)

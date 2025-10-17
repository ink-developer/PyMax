# Примеры использования

## Простой эхо-бот

```python
import asyncio
from pymax import MaxClient

async def main():
    client = MaxClient(phone="+79001234567")

    @client.on_message
    async def echo_handler(message):
        await client.send_message(
            chat_id=message.chat_id,
            text=f"Эхо: {message.text}"
        )

    await client.start()

asyncio.run(main())
```

## Автоматические ответы

```python
import asyncio
from pymax import MaxClient

async def main():
    client = MaxClient(phone="+79001234567")

    # Словарь ключевых слов и ответов
    auto_replies = {
        'привет': 'Привет! Как дела?',
        'пока': 'До свидания!',
        'спасибо': 'Пожалуйста!',
        'время': 'Время ответить на ваш вопрос!',
    }

    @client.on_message
    async def auto_reply_handler(message):
        text = message.text.lower()

        for keyword, reply in auto_replies.items():
            if keyword in text:
                await client.send_message(
                    chat_id=message.chat_id,
                    text=reply
                )
                break

    await client.start()

asyncio.run(main())
```

## Модерация чата

```python
import asyncio
from pymax import MaxClient

async def main():
    client = MaxClient(phone="+79001234567")

    # Запрещенные слова
    forbidden_words = ['спам', 'реклама', 'взлом']

    @client.on_message
    async def moderation_handler(message):
        text = message.text.lower()

        for word in forbidden_words:
            if word in text:
                # Удаляем сообщение
                await client.delete_message(
                    chat_id=message.chat_id,
                    message_id=message.id
                )

                # Предупреждаем пользователя
                await client.send_message(
                    chat_id=message.chat_id,
                    text=f"@{message.author.username}, использование запрещенных слов недопустимо!"
                )
                break

    await client.start()

asyncio.run(main())
```

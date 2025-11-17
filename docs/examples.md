# Примеры кода

Практические примеры для разных сценариев — от базовых ботов до сложных функций.

## Пример 1: Базовая инициализация и отправка сообщения

Самый простой пример - инициализация клиента и отправка сообщения при подключении.

```python
import asyncio
from pymax import MaxClient

async def main():
    phone = "+1234567890"
    client = MaxClient(phone=phone, work_dir="cache")

    async with client:
        @client.on_start
        async def handle_start() -> None:
            print("✓ Клиент запущен!")

            # Получаем информацию о текущем пользователе
            if client.me:
                print(f"✓ Ваш ID: {client.me.id}")

            # Отправляем приветственное сообщение
            msg = await client.send_message(
                text="Привет! Это тестовое сообщение.",
                chat_id=0,
                notify=True,
            )
            if msg:
                print(f"✓ Сообщение отправлено, ID: {msg.id}")

        await client.idle()

asyncio.run(main())
```

## Пример 2: Обработка входящих сообщений

Обработка сообщений с использованием фильтров и событий редактирования/удаления.

```python
import asyncio
from pymax import MaxClient, Message
from pymax.filters import Filter

async def main():
    phone = "+1234567890"
    client = MaxClient(phone=phone, work_dir="cache")

    async with client:
        # Обработка сообщений из конкретного чата
        @client.on_message(filter=Filter(chat_id=0))
        async def handle_message(message: Message) -> None:
            print(f"💬 Новое сообщение от {message.sender}:")
            print(f"   Текст: {message.text}")
            print(f"   Статус: {message.status}")

            # Отправляем ответ
            await client.send_message(
                text=f"Я получил ваше сообщение: {message.text}",
                chat_id=message.chat_id,
                reply_to=message.id,
                notify=True,
            )

        # Обработка отредактированных сообщений
        @client.on_message_edit()
        async def handle_edited_message(message: Message) -> None:
            print(f"✏️  Отредактировано сообщение в чате {message.chat_id}")
            print(f"   Новый текст: {message.text}")

        # Обработка удалённых сообщений
        @client.on_message_delete()
        async def handle_deleted_message(message: Message) -> None:
            print(f"🗑️  Удалено сообщение (ID: {message.id})")

        await client.idle()

asyncio.run(main())
```

## Пример 3: Работа с файлами и вложениями

Отправка файлов, фотографий и получение истории сообщений с вложениями.

```python
import asyncio
from pymax import MaxClient
from pymax.files import File, Photo
from pymax.static.enum import AttachType

async def main():
    phone = "+1234567890"
    client = MaxClient(phone=phone, work_dir="cache")

    async with client:
        @client.on_start
        async def handle_start() -> None:
            # Отправка файла
            file = File(path="config.toml")
            msg = await client.send_message(
                text="Вот ваш файл конфигурации",
                chat_id=0,
                attachment=file,
                notify=True,
            )
            if msg:
                print(f"✓ Файл отправлен в сообщении {msg.id}")

            # Отправка нескольких фотографий
            photos = [
                Photo(path="photo1.jpg"),
                Photo(path="photo2.jpg"),
            ]
            msg = await client.send_message(
                text="Пакет фотографий",
                chat_id=0,
                attachments=photos,
                notify=True,
            )
            if msg:
                print(f"✓ Фотографии отправлены")

            # Получение истории сообщений и поиск вложений
            history = await client.fetch_history(chat_id=0, backward=50)
            if history:
                for message in history:
                    if message.attaches:
                        for attach in message.attaches:
                            if attach.type == AttachType.FILE:
                                print(f"📄 Найден файл: {attach.url}")
                            elif attach.type == AttachType.AUDIO:
                                print(f"🎵 Найден аудиофайл: {attach.url}")
                            elif attach.type == AttachType.VIDEO:
                                print(f"🎬 Найдено видео: {attach.url}")

        await client.idle()

asyncio.run(main())
```

## Пример 4: Форматирование текста и реакции

Использование форматирования в сообщениях и работа с реакциями.

```python
import asyncio
from pymax import MaxClient

async def main():
    phone = "+1234567890"
    client = MaxClient(phone=phone, work_dir="cache")

    async with client:
        @client.on_start
        async def handle_start() -> None:
            # Отправка сообщения с форматированием
            formatted_text = """**Жирный текст**
*Курсивный текст*
__Подчёркнутый текст__
~~Зачёркнутый текст~~"""

            msg = await client.send_message(
                text=formatted_text,
                chat_id=0,
                notify=True,
            )

            if msg:
                print(f"✓ Форматированное сообщение отправлено: {msg.id}")

                # Добавление реакции к сообщению
                reaction = await client.add_reaction(
                    chat_id=0,
                    message_id=str(msg.id),
                    reaction="👍",
                )
                if reaction:
                    print(
                        f"✓ Реакция добавлена! Всего реакций: {reaction.total_count}"
                    )

                # Получение информации о реакциях
                reactions = await client.get_reactions(
                    chat_id=0,
                    message_ids=[str(msg.id)],
                )
                if reactions:
                    for msg_id, info in reactions.items():
                        print(f"📊 Сообщение {msg_id}: {info.total_count} реакций")

                # Удаление реакции
                removed = await client.remove_reaction(
                    chat_id=0,
                    message_id=str(msg.id),
                )
                if removed:
                    print(f"✓ Реакция удалена! Осталось: {removed.total_count}")

        await client.idle()

asyncio.run(main())
```

## Пример 5: Работа с пользователями и группами

Получение информации о пользователях, создание групп и работа с приглашениями.

```python
import asyncio
from pymax import MaxClient

async def main():
    phone = "+1234567890"
    client = MaxClient(phone=phone, work_dir="cache")

    async with client:
        @client.on_start
        async def handle_start() -> None:
            # Получение информации о текущем пользователе
            if client.me:
                names = client.me.names[0]
                print(f"👤 Ваше имя: {names.first_name} {names.last_name}")
                print(f"👤 Ваш ID: {client.me.id}")

            # Получение информации о другом пользователе
            user = await client.get_user(user_id=123456)
            if user:
                user_name = user.names[0]
                print(f"👥 Найден пользователь: {user_name.first_name}")

            # Создание новой группы
            group_chat, message = await client.create_group(
                name="Новая группа",
                participant_ids=[123456, 789012],
            )
            if group_chat:
                print(f"✓ Группа создана! ID: {group_chat.id}")
                print(f"✓ Название: {group_chat.title}")

            # Обновление ссылки-приглашения для группы
            if group_chat:
                chat = await client.rework_invite_link(chat_id=group_chat.id)
                if chat and chat.link:
                    print(f"🔗 Ссылка-приглашение: {chat.link}")

            # Приглашение пользователей в существующую группу
            success = await client.invite_users_to_group(
                chat_id=0,
                user_ids=[987654, 654321],
            )
            if success:
                print("✓ Пользователи приглашены в группу")

            # Просмотр всех диалогов
            print(f"💬 У вас {len(client.dialogs)} диалогов")
            for dialog in client.dialogs[:5]:  # Первые 5 диалогов
                if dialog.last_message:
                    print(f"   - {dialog.last_message.text[:30]}...")

        await client.idle()

asyncio.run(main())
```

## Пример 6: Полный бот с обработкой ошибок

Комплексный пример с обработкой ошибок, логированием и различными функциями.

```python
import asyncio
import logging
from pymax import MaxClient, Message
from pymax.filters import Filter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    phone = "+1234567890"

    try:
        client = MaxClient(
            phone=phone,
            work_dir="cache",
            reconnect=True,
            reconnect_delay=1.0,
        )

        async with client:

            @client.on_start
            async def handle_start() -> None:
                logger.info("Клиент подключился!")
                try:
                    # Отправка тестового сообщения
                    msg = await client.send_message(
                        text="🤖 Бот запущен и готов к работе",
                        chat_id=0,
                        notify=True,
                    )
                    if msg:
                        logger.info(f"Тест пройден, сообщение ID: {msg.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке тестового сообщения: {e}")

            @client.on_message(filter=Filter(chat_id=0))
            async def handle_message(message: Message) -> None:
                try:
                    logger.info(
                        f"Сообщение от {message.sender}: {message.text[:50]}"
                    )

                    # Простая логика обработки
                    if "привет" in message.text.lower():
                        await client.send_message(
                            text="Привет! Как дела? 👋",
                            chat_id=message.chat_id,
                            reply_to=message.id,
                            notify=True,
                        )
                    elif "помощь" in message.text.lower():
                        await client.send_message(
                            text="""Доступные команды:
- привет - поздравление
- помощь - показать эту помощь
- время - показать текущее время""",
                            chat_id=message.chat_id,
                            reply_to=message.id,
                            notify=True,
                        )
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения: {e}")

            await client.idle()

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Советы и рекомендации

### Использование фильтров

Фильтры позволяют обрабатывать только нужные сообщения:

```python
from pymax.filters import Filter

# Сообщения из конкретного чата
@client.on_message(filter=Filter(chat_id=123))

# Сообщения от конкретного пользователя
@client.on_message(filter=Filter(user_id=456))

# Сообщения, содержащие определённый текст
@client.on_message(filter=Filter(text_contains="важное"))

# Комбинирование фильтров
@client.on_message(filter=Filter(chat_id=123, text_contains="важное"))
```

### Работа с контекстным менеджером

Всегда используйте `async with` для правильного управления ресурсами:

```python
async with client:
    # Ваш код здесь
    await client.idle()
```

### Обработка ошибок

Рекомендуется оборачивать критические операции в `try-except`:

```python
try:
    msg = await client.send_message(
        text="Сообщение",
        chat_id=0,
        notify=True,
    )
except Exception as e:
    logger.error(f"Ошибка при отправке: {e}")
```

### Задержка между операциями

Для избежания rate-limiting используйте `asyncio.sleep`:

```python
import asyncio

for chat_id in chat_ids:
    await client.send_message(
        text="Сообщение",
        chat_id=chat_id,
        notify=True,
    )
    await asyncio.sleep(1)  # Задержка между отправками
```

## Дополнительные ресурсы

- **[API](api.md)** - полная документация всех методов
- **[Типы данных](types.md)** - описание всех типов данных
- **[GitHub](https://github.com/ink-developer/PyMax)** - исходный код

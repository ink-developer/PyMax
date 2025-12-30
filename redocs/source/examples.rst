Examples
=========

Готовые примеры для различных сценариев.

Echo Bot
--------

Простейший бот - повторяет сообщения:

.. code-block:: python

    import asyncio
    from pymax import MaxClient

    client = MaxClient(phone="+79001234567")

    @client.on_message()
    async def echo(message):
        if message.text:
            await client.send_message(
                chat_id=message.chat_id,
                text=f"Echo: {message.text}"
            )

    asyncio.run(client.start())

Greeter Bot
-----------

Приветствует новых пользователей:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    @client.on_message(Filters.chat(123))
    async def greet(message):
        user = await client.get_user(message.sender)
        if user and user.names:
            name = user.names[0].first_name
            await client.send_message(
                chat_id=message.chat_id,
                text=f"Привет, {name}! 👋"
            )

    @client.on_start
    async def on_start():
        print(f"Greeter запущен! ID: {client.me.id}")

    asyncio.run(client.start())

Command Handler
---------------

Обработка команд с префиксом:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from datetime import datetime
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    commands = {
        "/привет": "Привет! 👋",
        "/помощь": "Доступные команды: /привет, /время, /помощь",
        "/время": lambda: f"Время: {datetime.now().strftime('%H:%M:%S')} ⏰",
    }

    @client.on_message()
    async def handle_command(message):
        if not message.text or not message.text.startswith("/"):
            return

        command = message.text.split()[0]

        if command in commands:
            response = commands[command]
            if callable(response):
                response = response()

            await client.send_message(
                chat_id=message.chat_id,
                text=response
            )

    asyncio.run(client.start())

Broadcast Bot
-------------

Отправляет сообщение во все чаты:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    @client.on_message(Filters.text("рассылка"))
    async def broadcast(message):
        text = message.text.replace("рассылка ", "")

        for chat in client.chats:
            try:
                await client.send_message(
                    chat_id=chat.id,
                    text=text,
                    notify=False
                )
            except Exception as e:
                print(f"Ошибка в чате {chat.title}: {e}")

        await client.send_message(
            chat_id=message.chat_id,
            text="✅ Рассылка завершена"
        )

    asyncio.run(client.start())

File Manager
------------

Работа с файлами и вложениями:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.files import File
    from pymax.static.enum import AttachType
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    @client.on_message()
    async def handle_files(message):
        if not message.attaches:
            return

        for attach in message.attaches:
            if attach.type == AttachType.PHOTO:
                print("Получено фото!")

                print(f"URL: {attach.base_url}")

    @client.on_message(Filters.text("файл"))
    async def send_file(message):
        file = File(path="document.pdf")
        await client.send_message(
            chat_id=message.chat_id,
            text="Вот файл",
            attachment=file
        )

    asyncio.run(client.start())

Message Counter
---------------

Считает сообщения от каждого пользователя:

.. code-block:: python

    import asyncio
    from collections import defaultdict
    from pymax import MaxClient
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")
    user_messages = defaultdict(int)

    @client.on_message()
    async def count_messages(message):
        user_messages[message.sender] += 1

    @client.on_message(Filters.text("статистика"))
    async def show_stats(message):
        # Топ-5 активные пользователи
        top = sorted(user_messages.items(), key=lambda x: x[1], reverse=True)[:5]

        text = "📊 Топ активные:\n"
        for user_id, count in top:
            user = await client.get_user(user_id)
            name = user.names[0].first_name if user and user.names else "Неизвестно"
            text += f"{name}: {count}\n"

        await client.send_message(
            chat_id=message.chat_id,
            text=text
        )

    asyncio.run(client.start())

Auto-Replier
------------

Автоматический ответ на определённые фразы:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    auto_replies = {
        "привет": "И тебе привет! 👋",
        "как дела": "Спасибо, отлично! 😊",
        "спасибо": "Пожалуйста! 🙏",
        "пока": "До свидания! 👋",
    }

    @client.on_message()
    async def auto_reply(message):
        if not message.text:
            return

        text_lower = message.text.lower()

        for trigger, response in auto_replies.items():
            if trigger in text_lower:
                await client.send_message(
                    chat_id=message.chat_id,
                    text=response
                )
                return

    asyncio.run(client.start())

Scheduled Messages
------------------

Отправка сообщений по расписанию:

.. code-block:: python

    import asyncio
    from datetime import datetime, timedelta

    client = MaxClient(phone="+79001234567")

    async def scheduled_sender():
        while True:
            now = datetime.now()

            # Отправить сообщение в 12:00
            if now.hour == 12 and now.minute == 0:
                await client.send_message(
                    chat_id=123456,
                    text="🕐 Обеденный перерыв!",
                    notify=False
                )
                await asyncio.sleep(60)  # Не отправлять дважды в одну минуту

            await asyncio.sleep(1)

    @client.on_start
    async def on_start():
        asyncio.create_task(scheduled_sender())

    asyncio.run(client.start())

Error Handling
--------------

Правильная обработка ошибок:

.. code-block:: python

    import asyncio
    import logging
    from pymax import MaxClient

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bot")

    client = MaxClient(phone="+79001234567", logger=logger)

    @client.on_message()
    async def safe_handler(message):
        try:
            if not message.text:
                return

            result = await client.send_message(
                chat_id=message.chat_id,
                text=f"Получено: {message.text}"
            )

            logger.info(f"Сообщение отправлено в чат {message.chat_id}")

        except Exception as e:
            logger.error(f"Ошибка в обработчике: {e}")

    asyncio.run(client.start())

Context Manager
---------------

Использование клиента как контекстного менеджера:

.. code-block:: python

    import asyncio
    from pymax import MaxClient

    client = MaxClient(phone="+79001234567")

    async def main():
        async with client:
            # Клиент автоматически подключён и синхронизирован
            await client.send_message(
                chat_id=123456,
                text="Контекстный менеджер работает!"
            )

            # Блокировать и ждать событий
            await client.idle()

    asyncio.run(main())

Filter Combinations
-------------------

Комбинирование фильтров:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.filters import Filters

    client = MaxClient(phone="+79001234567")

    # AND - оба условия должны быть верны
    @client.on_message(Filters.chat(123456) & Filters.text("важное"))
    async def important_in_chat(message):
        await client.send_message(
            chat_id=message.chat_id,
            text="Это важно в нашем чате!"
        )

    # OR - одно из условий должно быть верно
    @client.on_message(Filters.chat(123456) | Filters.chat(789012))
    async def in_my_chats(message):
        print("Это в одном из моих чатов")

    # NOT - условие должно быть неверно
    @client.on_message(~Filters.text("реклама"))
    async def not_ads(message):
        print("Это не реклама")

    asyncio.run(client.start())

Дополнительно
--------------

Смотрите раздел :doc:`guides` для подробных гайдов и больше примеров.

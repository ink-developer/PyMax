Quick Start
===========

За 5 минут до первого работающего бота.

Установка
---------

.. code-block:: bash

    pip install -U maxapi-python

Первый бот: Echo
----------------

Самый простой бот — повторяет сообщения пользователя:

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.types import Message

    client = MaxClient(phone="+79001234567")

    @client.on_message()
    async def echo(message: Message) -> None:
        if message.text:
            await client.send_message(
                chat_id=message.chat_id,
                text=f"Echo: {message.text}"
            )

    if __name__ == "__main__":
        asyncio.run(client.start())

Запуск:

.. code-block:: bash

    python bot.py

При первом запуске вам потребуется ввести код подтверждения из приложения Max.

Фильтры сообщений
------------------

Обрабатывать только определённые сообщения:

.. code-block:: python

    from pymax.filters import Filters
    from pymax.types import Message

    # Только из конкретного чата
    @client.on_message(Filters.chat(123456))
    async def handle_chat(message: Message) -> None:
        await client.send_message(
            chat_id=message.chat_id,
            text="Это из моего чата!"
        )

    # Только с определённым текстом
    @client.on_message(Filters.text("привет"))
    async def greet(message: Message) -> None:
        await client.send_message(
            chat_id=message.chat_id,
            text="И тебе привет!"
        )


Обработчики событий
--------------------

Реагировать на события клиента:

.. code-block:: python

    from pymax.types import Message, Chat

    @client.on_start()
    async def startup() -> None:
        print(f"Клиент запущен! ID: {client.me.id}")

    @client.on_message_delete()
    async def message_deleted(message: Message) -> None:
        print(f"Сообщение удалено: {message.id}")

    @client.on_chat_update()
    async def chat_changed(chat: Chat) -> None:
        print(f"Чат обновлен: {chat.title}")

Получение информации
---------------------

Информация о пользователе:

.. code-block:: python

    from pymax.types import Message, User

    @client.on_message()
    async def get_user_info(message: Message) -> None:
        user: User | None = await client.get_user(message.sender)
        if user:
            name = user.names[0].first_name if user.names else "Неизвестно"
            await client.send_message(
                chat_id=message.chat_id,
                text=f"Привет, {name}!"
            )

Информация о чате:

.. code-block:: python

    from pymax.types import Message, Chat

    @client.on_message()
    async def get_chat_info(message: Message) -> None:
        chat: Chat | None = await client.get_chat(message.chat_id)
        if chat:
            await client.send_message(
                chat_id=message.chat_id,
                text=f"Название чата: {chat.title}"
            )

История сообщений:

.. code-block:: python

    from pymax.filters import Filters
    from pymax.types import Message

    @client.on_message(Filters.text("история"))
    async def fetch_history(message: Message) -> None:
        history = await client.fetch_history(
            chat_id=message.chat_id,
            limit=10
        )

        text = "Последние 10 сообщений:\n"
        for msg in history:
            text += f"- {msg.text}\n"

        await client.send_message(
            chat_id=message.chat_id,
            text=text
        )

Отправка файлов
----------------

.. code-block:: python

    from pymax.filters import Filters
    from pymax.files import File
    from pymax.types import Message

    @client.on_message(Filters.text("файл"))
    async def send_file(message: Message) -> None:
        file = File(path="document.pdf")
        await client.send_message(
            chat_id=message.chat_id,
            text="Вот документ",
            attachment=file
        )

Полный пример: простой помощник
--------------------------------

.. code-block:: python

    import asyncio
    from pymax import MaxClient
    from pymax.filters import Filters
    from pymax.types import Message, User

    client = MaxClient(
        phone="+79001234567",
        work_dir="./cache"
    )

    @client.on_start()
    async def on_start() -> None:
        print(f"Помощник запущен! ID: {client.me.id}")
        await client.send_message(
            chat_id=123456,
            text="Я запустился!",
            notify=False
        )

    @client.task(minutes=1)
    async def status_check() -> None:
        """Проверка статуса каждую минуту"""
        print("Помощник все еще работает!")

    @client.on_message(Filters.text("привет"))
    async def hello(message: Message) -> None:
        user: User | None = await client.get_user(message.sender)
        name = user.names[0].first_name if user and user.names else "друг"

        await client.send_message(
            chat_id=message.chat_id,
            text=f"Привет, {name}! 👋"
        )

    @client.on_message(Filters.text("помощь"))
    async def help_command(message: Message) -> None:
        help_text = """Доступные команды:
    - привет — приветствие
    - помощь — показать эту справку
    - время — текущее время
        """
        await client.send_message(
            chat_id=message.chat_id,
            text=help_text
        )

    @client.on_message(Filters.text("время"))
    async def time_command(message: Message) -> None:
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")

        await client.send_message(
            chat_id=message.chat_id,
            text=f"Текущее время: {current_time} ⏰"
        )


    if __name__ == "__main__":
        asyncio.run(client.start())

Дальше
------

- Смотрите :doc:`guides` для подробных гайдов
- Смотрите :doc:`examples` для больше примеров
- Смотрите :doc:`clients` для полного справочника методов

.. note::

    Обратитесь к :doc:`installation` если у вас есть проблемы с установкой.

Clients
=======

MaxClient
---------

Основной асинхронный WebSocket клиент для взаимодействия с Max API.

Инициализация:

.. code-block:: python

    from pymax import MaxClient

    client = MaxClient(
        phone="+79001234567",           # Номер телефона (обязательно)
        work_dir="./cache",             # Папка для кэша сессии
        reconnect=True,                 # Автоматическое переподключение
        send_fake_telemetry=True,       # Отправлять телеметрию
        logger=None,                    # Пользовательский логгер
    )

Основные методы:

.. code-block:: python

    # Запустить клиент
    await client.start()

    # Закрыть клиент
    await client.close()

    # Получить информацию о чате
    chat = await client.get_chat(chat_id=123456)
    chats = await client.get_chats([123, 456])

    # Получить информацию о пользователе
    user = await client.get_user(user_id=789012)

    # Отправить сообщение
    result = await client.send_message(
        chat_id=123456,
        text="Сообщение"
    )

    # Редактировать сообщение
    await client.edit_message(
        chat_id=123456,
        message_id=msg_id,
        text="Новый текст"
    )

    # Удалить сообщение
    await client.delete_message(
        chat_id=123456,
        message_id=msg_id
    )

    # Получить историю сообщений
    history = await client.fetch_history(
        chat_id=123456,
        limit=50
    )

Свойства:

.. code-block:: python

    client.me                   # Информация о себе (Me)
    client.is_connected         # Статус подключения (bool)
    client.chats                # Список всех чатов (list[Chat])
    client.dialogs              # Список диалогов (list[Dialog])
    client.channels             # Список каналов (list[Channel])
    client.phone                # Номер телефона (str)
    client.token                # Токен сессии (str | None)

Обработчики событий:

.. code-block:: python

    @client.on_start
    async def on_start():
        """При запуске клиента"""
        pass


    @client.on_message()
    async def on_message(message: Message):
        """При получении сообщения"""
        pass


Контекстный менеджер:

.. code-block:: python

    async with MaxClient(phone="+79001234567") as client:
        # Клиент автоматически подключён
        await client.send_message(chat_id=123456, text="Привет!")
        # Клиент автоматически закроется

Автоматическое подключение/отключение:

.. code-block:: python

    client = MaxClient(phone="+79001234567", reconnect=True)

    # Клиент автоматически переподключится при разрыве соединения
    await client.start()

Документация API
----------------

.. autoclass:: pymax.MaxClient
   :members:
   :inherited-members:

SocketMaxClient
---------------

Низкоуровневый WebSocket клиент для прямого взаимодействия с API.
Обычно не требуется использовать напрямую - используйте MaxClient вместо этого.

.. note::

    Если вам нужны низкоуровневые детали, смотрите исходный код библиотеки.

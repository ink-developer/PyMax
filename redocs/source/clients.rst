Clients
=======

Выбор между MaxClient и SocketMaxClient
----------------------------------------

PyMax предоставляет два клиента с разной функциональностью в зависимости от выбранного протокола подключения:

.. list-table:: Сравнение клиентов
   :widths: 30 35 35
   :header-rows: 1

   * - Функция
     - MaxClient (WebSocket)
     - SocketMaxClient (Socket)
   * - Протокол подключения
     - WebSocket
     - TCP Socket
   * - Способ авторизации
     - Вход по QR-коду
     - Вход/регистрация по номеру телефона
   * - Регистрация новых пользователей
     - ❌ Не поддерживается
     - ✅ Поддерживается
   * - Скорость подключения
     - Быстрое
     - Медленнее
   * - Рекомендуемое использование
     - Базовые боты и приложения
     - Массовая регистрация, системная авторизация

MaxClient
---------

Основной асинхронный WebSocket клиент для взаимодействия с Max API.

**Поддерживаемые методы авторизации:**
    - ✅ Вход по QR-коду (WEB device_type)
    - ❌ Вход по номеру телефона (больше не поддерживается)
    - ❌ Регистрация по номеру телефона

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

.. note::

    MaxClient по умолчанию использует **WEB** device_type и поддерживает только вход по QR-коду.
    Это является рекомендуемым способом авторизации для большинства приложений.

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

    # Изменить профиль с загрузкой фото
    result = await client.change_profile(
        first_name="Иван",
        last_name="Петров",
        description="Привет!",
        photo=Photo(...)  # Новая фотография профиля
    )

    # Разрешить группу по ссылке
    group = await client.resolve_group_by_link(
        link="https://max.app/g/ABC123"
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
    client.contacts             # Список контактов (list[User])

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

Асинхронный TCP Socket клиент для взаимодействия с Max API. Используется для входа и регистрации по номеру телефона.

**Поддерживаемые методы авторизации:**
    - ✅ Вход по номеру телефона (DESKTOP, ANDROID, IOS device_types)
    - ✅ Регистрация нового пользователя по номеру телефона

**Когда использовать SocketMaxClient:**
    - Необходимо зарегистрировать новых пользователей
    - Требуется вход по номеру телефона (без QR-кода)
    - Необходимо использовать DESKTOP, ANDROID или IOS device_types
    - Разрабатываете системы массовой регистрации или авторизации
    - Нужна автоматизация входа (вход по номеру телефона удобнее для автоматизации, чем сканирование QR-кода)

.. note::

    **SocketMaxClient — это полноценный и рекомендуемый способ авторизации!**

    Не воспринимайте Socket клиент как что-то вспомогательное или альтернативное.
    Вход по номеру телефона — это основной способ авторизации в Max, и ``SocketMaxClient`` обеспечивает надежный доступ к этому функционалу.

    Для многих сценариев (особенно для автоматизации и интеграции) вход по номеру телефона **удобнее и практичнее**, чем сканирование QR-кода.

Инициализация и вход:

.. code-block:: python

    from pymax import SocketMaxClient
    from pymax.payloads import UserAgentPayload

    # Для входа по номеру телефона
    client = SocketMaxClient(
        phone="+79001234567",
        work_dir="./cache",
        headers=UserAgentPayload(device_type="DESKTOP"),
    )

    await client.start()  # Потребуется ввести код подтверждения

Регистрация нового пользователя:

.. code-block:: python

    from pymax import SocketMaxClient
    from pymax.payloads import UserAgentPayload

    client = SocketMaxClient(
        phone="+79001234567",
        registration=True,                      # Флаг регистрации
        first_name="Иван",
        last_name="Петров",
        headers=UserAgentPayload(device_type="DESKTOP"),
    )

    await client.start()  # Потребуется ввести код подтверждения

.. important::

    SocketMaxClient должен использоваться для:

    1. **Регистрации новых пользователей** — MaxClient не поддерживает регистрацию
    2. **Входа по номеру телефона** — требуется phone verification код
    3. **Системной авторизации** — когда QR-код недоступен или неудобен
    4. **Автоматизации** — вход по номеру телефона легче автоматизировать

.. note::

    После успешной авторизации через SocketMaxClient вы можете сохранить токен и использовать его с MaxClient для более быстрого подключения к WebSocket API.

    .. code-block:: python

        # Первый раз: получаем токен через Socket
        socket_client = SocketMaxClient(phone="+79001234567")
        await socket_client.start()
        token = socket_client.token

        # Сохраняем токен

        # Следующие разы: используем токен с WebSocket клиентом
        ws_client = MaxClient(phone="+79001234567", token=token)
        await ws_client.start()

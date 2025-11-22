# Как пользоваться MaxClient

## Содержание

- [Установка и Настройка](#установка-и-настройка)
- [Основные Возможности](#основные-возможности)
- [Управление Подключением](#управление-подключением)
- [Работа с Данными](#работа-с-данными)
- [Лучшие Практики](#лучшие-практики)

## ⚙️ Установка и настройка {#установка-и-настройка}

### Инициализация Клиента

!!! info "MaxClient"
    Основной класс для взаимодействия с WebSocket API сервиса Max.

```python
client = MaxClient(
    phone: str,
    uri: str = Constants.WEBSOCKET_URI.value,
    headers: dict[str, Any] | None = Constants.DEFAULT_USER_AGENT_PAYLOAD.value,
    token: str | None = None,
    send_fake_telemetry: bool = True,
    host: str = Constants.HOST.value,
    port: int = Constants.PORT.value,
    work_dir: str = ".",
    logger: logging.Logger | None = None,
)
```

**Параметры конфигурации**

| Параметр | Тип | Описание | По умолчанию |
|----------|-----|----------|---------------|
| `phone` | `str` | Номер телефона для авторизации | - |
| `uri` | `str` | URI WebSocket сервера | `Constants.WEBSOCKET_URI.value` |
| `headers` | `dict[str, Any] | None` | Заголовки для соединения | `Constants.DEFAULT_USER_AGENT_PAYLOAD.value` |
| `token` | `str | None` | Токен авторизации | `None` |
| `send_fake_telemetry` | `bool` | Отправка телеметрии | `True` |
| `host` | `str` | Хост API сервера | `Constants.HOST.value` |
| `port` | `int` | Порт API сервера | `Constants.PORT.value` |
| `work_dir` | `str` | Директория для БД | `"."` |
| `logger` | `logging.Logger | None` | Пользовательский логгер | `None` |

**Пример базовой инициализации**
```python
from pymax import MaxClient

client = MaxClient(
    phone="+79001234567",
    work_dir="./data"
)
```

**Пример расширенной конфигурации**
```python
import logging

# Настройка логгера
logger = logging.getLogger("max_bot")
logger.setLevel(logging.DEBUG)

# Инициализация с дополнительными параметрами
client = MaxClient(
    phone="+79001234567",
    token="your_saved_token",  # Если есть сохраненный токен
    work_dir="./data",
    logger=logger,
    send_fake_telemetry=False
)
```

##  Основные возможности {#основные-возможности}

### Свойства Клиента

#### Аутентификация и Подключение

!!! info "Статус и авторизация"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `is_connected` | `bool` | Статус подключения |
    | `phone` | `str` | Номер телефона |
    | `me` | `Me | None` | Информация о пользователе |

#### Доступ к Данным

!!! info "Чаты и пользователи"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `chats` | `list[Chat]` | Все чаты |
    | `dialogs` | `list[Dialog]` | Личные диалоги |
    | `channels` | `list[Channel]` | Каналы |

##  Управление подключением {#управление-подключением}

### Запуск и Остановка

```python
async def start() -> None
```

!!! info "Запуск клиента"
    Метод выполняет:
    1. Подключение к WebSocket
    2. Авторизацию пользователя
    3. Инициализацию фоновых задач
    4. Синхронизацию данных

**Пример использования**
```python
async def main():
    client = MaxClient(phone="+79001234567")
    try:
        await client.start()
        print("Клиент успешно запущен")
    except Exception as e:
        print(f"Ошибка запуска: {e}")

asyncio.run(main())
```

```python
async def close() -> None
```

!!! warning "Закрытие клиента"
    Метод выполняет:
    1. Остановку фоновых задач
    2. Закрытие WebSocket соединения
    3. Очистку ресурсов

**Пример корректного закрытия**
```python
async def main():
    async with MaxClient(phone="+79001234567") as client:
        # Ваш код здесь
    # Клиент автоматически закроется
```

##  Работа с Сообщениями

### Обработка Сообщений

!!! tip "Регистрация обработчиков"
    ```python
    @client.on_message()
    async def handle_message(message: Message):
        print(f"Получено сообщение: {message.text}")

        if message.attaches:
            print("Есть вложения!")

        if message.sender:
            user = await client.get_user(message.sender)
            if user:
                print(f"От: {user.names[0].name}")
    ```

### Фильтрация Сообщений

!!! example "Примеры фильтров"
    ```python
    # Только из конкретного чата
    @client.on_message(Filter(chat_id=123456))
    async def handle_chat(message: Message):
        print(f"Сообщение в чате: {message.text}")
    ```

##  Работа с данными {#работа-с-данными}

### Доступ к Чатам

!!! info "Типы чатов"
    ```python
    # Все чаты
    for chat in client.chats:
        print(f"Чат: {chat.title}")

    # Личные диалоги
    for dialog in client.dialogs:
        user = await client.get_user(dialog.owner)
        if user:
            print(f"Диалог с {user.names[0].name}")

    # Каналы
    for channel in client.channels:
        print(f"Канал: {channel.title}")
    ```

### Информация о Пользователе

!!! example "Работа с текущим пользователем"
    ```python
    me = client.me
    if me:
        name = me.names[0] if me.names else None
        print(f"Авторизован как: {name.first_name if name else me.phone}")
        print(f"ID: {me.id}")
        print(f"Статус: {me.account_status}")
    ```

##  Хранение Данных

### База Данных

!!! info "Локальное хранилище"
    - **Расположение**: `{work_dir}/session.db`
    - **Хранит**:
        - Токены авторизации
        - Информацию об устройстве
        - Данные сессии
    - **Особенности**:
        - Автоматическое управление
        - Персистентное хранение
        - Безопасное сохранение токенов

##  Лучшие практики {#лучшие-практики}

### Безопасное Использование

!!! tip "Контекстный менеджер"
    ```python
    async def main():
        async with MaxClient(phone="+79001234567") as client:
            # Ваш код здесь
        # Клиент автоматически закроется
    ```

### Обработка Ошибок

!!! warning "Обработка исключений"
    ```python
    try:
        await client.start()
    except WebSocketNotConnectedError:
        print("Ошибка подключения")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    ```

### Оптимизация

!!! tip "Советы по оптимизации"
    1. Используйте фильтры сообщений для снижения нагрузки
    2. Применяйте кэширование пользователей через `get_cached_user`
    3. Группируйте операции с сообщениями
    4. Правильно закрывайте ресурсы

### Структура Бота

!!! example "Рекомендуемая структура"
    ```python
    from pymax import MaxClient

    class MyBot:
        def __init__(self, phone: str):
            self.client = MaxClient(phone=phone)

        async def setup(self):
            # Регистрация обработчиков
            @self.client.on_message()
            async def handle_message(message: Message):
                await self.process_message(message)

            @self.client.on_start
            async def handle_start():
                await self.on_ready()

        async def process_message(self, message: Message):
            # Ваша логика обработки сообщений
            pass

        async def on_ready(self):
            print("Бот готов к работе!")

        async def run(self):
            await self.client.start()

    # Использование
    bot = MyBot(phone="+79001234567")
    asyncio.run(bot.run())
    ```

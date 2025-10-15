# 📚 Справочник Типов PyMax

## 📋 Содержание

- [Перечисления (Enums)](#перечисления-enums)
- [Основные Классы](#основные-классы)
- [Вложения](#вложения)
- [Служебные Типы](#служебные-типы)

## 🔍 Перечисления (Enums) {#перечисления-enums}

### ChatType

!!! info "Типы чатов"
    | Значение | Описание |
    |----------|----------|
    | `DIALOG` | Личный диалог между двумя пользователями |
    | `CHAT` | Групповой чат |
    | `CHANNEL` | Канал |

### MessageType

!!! info "Типы сообщений"
    | Значение | Описание |
    |----------|----------|
    | `TEXT` | Обычное текстовое сообщение |
    | `SYSTEM` | Системное сообщение |
    | `SERVICE` | Сервисное сообщение |

### ElementType

!!! info "Типы элементов сообщения"
    | Значение | Описание |
    |----------|----------|
    | `text` | Текстовый элемент |
    | `mention` | Упоминание пользователя |
    | `link` | URL-ссылка |
    | `emoji` | Эмодзи |

### AccessType

!!! info "Типы доступа"
    | Значение | Описание |
    |----------|----------|
    | `PUBLIC` | Публичный доступ |
    | `PRIVATE` | Приватный доступ |
    | `SECRET` | Секретный доступ |

### AttachType

!!! info "Типы вложений"
    | Значение | Описание |
    |----------|----------|
    | `PHOTO` | Фотография |
    | `VIDEO` | Видео |
    | `FILE` | Файл |
    | `STICKER` | Стикер |
    | `CONTROL` | Управляющий элемент |

!!! tip "Использование перечислений"
    ```python
    from pymax.static import MessageType, MessageStatus

    # Проверка типа сообщения
    if message.type == MessageType.TEXT:
        print("Это текстовое сообщение")

    # Проверка статуса
    if message.status == MessageStatus.DELIVERED:
        print("Сообщение доставлено")
    ```

## 📦 Основные классы {#основные-классы}

### Names

!!! info "Информация об именах пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `name` | `str` | Полное имя |
    | `first_name` | `str` | Имя |
    | `last_name` | `str \| None` | Фамилия (опционально) |
    | `type` | `str` | Тип имени |

**Пример использования**
```python
if user.names:
    name = user.names[0]
    print(f"Привет, {name.first_name}!")
```

### Message

!!! info "Представление сообщения"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID сообщения |
    | `chat_id` | `int \| None` | ID чата |
    | `sender` | `int \| None` | ID отправителя |
    | `text` | `str` | Текст сообщения |
    | `time` | `int` | Временная метка |
    | `status` | `MessageStatus \| str \| None` | Статус сообщения |
    | `type` | `MessageType \| str` | Тип сообщения |
    | `elements` | `list[Element] \| None` | Элементы форматирования |
    | `reaction_info` | `ReactionInfo \| None` | Информация о реакциях |
    | `attaches` | `list[PhotoAttach \| VideoAttach \| FileAttach \| ControlAttach] \| None` | Вложения |
    | `link` | `MessageLink \| None` | Связанное сообщение |
    | `options` | `int \| None` | Опции сообщения |

**Пример работы с сообщением**
```python
async def handle_message(message: Message):
    # Проверяем тип сообщения
    if message.type == MessageType.TEXT:
        # Работаем с текстом
        print(f"Получено: {message.text}")

        # Проверяем вложения
        if message.attaches:
            for attach in message.attaches:
                if isinstance(attach, PhotoAttach):
                    print(f"Фото: {attach.photo_id}")

        # Проверяем реакции
        if message.reaction_info:
            print(f"Реакций: {message.reaction_info.total_count}")
```

### Chat

!!! info "Представление чата или группы"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID чата |
    | `type` | `ChatType \| str` | Тип чата |
    | `title` | `str \| None` | Название |
    | `description` | `str \| None` | Описание |
    | `owner` | `int` | ID владельца |
    | `access` | `AccessType \| str` | Тип доступа |
    | `participants_count` | `int` | Кол-во участников |
    | `admins` | `list[int]` | ID администраторов |
    | `participants` | `dict[int, int]` | Участники |
    | `link` | `str \| None` | Ссылка-приглашение |
    | `base_icon_url` | `str \| None` | URL иконки |
    | `invited_by` | `int \| None` | Кто пригласил |

!!! tip "Работа с чатами"
    ```python
    if chat.type == ChatType.CHAT:
        # Групповой чат
        print(f"Участников: {chat.participants_count}")

        # Проверяем права
        if client.me.id in chat.admins:
            print("Вы администратор")
    ```

### User

!!! info "Представление пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID пользователя |
    | `names` | `list[Names]` | Имена |
    | `account_status` | `int` | Статус аккаунта |
    | `update_time` | `int` | Время обновления |
    | `options` | `list[str] \| None` | Опции |
    | `base_url` | `str \| None` | URL профиля |
    | `photo_id` | `int \| None` | ID фото |
    | `description` | `str \| None` | Описание |
    | `link` | `str \| None` | Ссылка на профиль |

**Пример работы с пользователем**
```python
user = await client.get_user(123456)
if user:
    name = user.names[0] if user.names else None
    print(f"Профиль: {name.first_name if name else 'Неизвестно'}")
    if user.photo_id:
        print("Есть фото профиля")
```

## 📎 Вложения {#вложения}

### PhotoAttach

!!! info "Фотография-вложение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `photo_id` | `int` | ID фотографии |
    | `base_url` | `str` | URL фотографии |
    | `height` | `int` | Высота |
    | `width` | `int` | Ширина |
    | `photo_token` | `str` | Токен |
    | `type` | `AttachType` | Всегда `PHOTO` |

**Пример отправки фото**
```python
with open("photo.jpg", "rb") as f:
    photo = Photo(f)
    message = await client.send_message(
        chat_id=123456,
        text="Смотри, какое фото!",
        photo=photo
    )
    if message and message.attaches:
        photo_attach = message.attaches[0]
        print(f"Фото {photo_attach.photo_id} отправлено")
```

### VideoAttach

!!! info "Видео-вложение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `video_id` | `int` | ID видео |
    | `height` | `int` | Высота |
    | `width` | `int` | Ширина |
    | `duration` | `int` | Длительность (сек) |
    | `token` | `str` | Токен |
    | `type` | `AttachType` | Всегда `VIDEO` |

!!! tip "Получение видео"
    ```python
    if isinstance(attach, VideoAttach):
        video_info = await client.get_video_by_id(
            chat_id=message.chat_id,
            message_id=message.id,
            video_id=attach.video_id
        )
        if video_info:
            print(f"URL видео: {video_info.url}")
    ```

### FileAttach

!!! info "Файл-вложение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `file_id` | `int` | ID файла |
    | `name` | `str` | Имя файла |
    | `size` | `int` | Размер (байт) |
    | `token` | `str` | Токен |
    | `type` | `AttachType` | Всегда `FILE` |

!!! warning "Безопасность файлов"
    ```python
    if isinstance(attach, FileAttach):
        file_info = await client.get_file_by_id(
            chat_id=message.chat_id,
            message_id=message.id,
            file_id=attach.file_id
        )
        if file_info and not file_info.unsafe:
            print(f"Безопасный файл: {attach.name}")
    ```

## 🔧 Служебные типы {#служебные-типы}

### Element

!!! info "Элемент форматирования сообщения"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `type` | `ElementType \| str` | Тип элемента |
    | `length` | `int` | Длина |
    | `from_` | `int \| None` | ID для упоминаний |

**Пример работы с элементами**
```python
for element in message.elements:
    if element.type == ElementType.MENTION:
        user = await client.get_user(element.from_)
        if user:
            print(f"Упомянут: {user.names[0].name}")
```

### ReactionInfo

!!! info "Информация о реакциях"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `total_count` | `int` | Всего реакций |
    | `counters` | `list[ReactionCounter]` | Счётчики реакций |
    | `your_reaction` | `str \| None` | Ваша реакция |

**Работа с реакциями**
```python
if message.reaction_info:
    print(f"Всего реакций: {message.reaction_info.total_count}")
    for counter in message.reaction_info.counters:
        print(f"{counter.reaction}: {counter.count}")
```

### Session

!!! info "Сессия пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `client` | `str` | Название клиента |
    | `info` | `str` | Информация |
    | `location` | `str` | Местоположение |
    | `time` | `int` | Временная метка |
    | `current` | `bool` | Текущая сессия |

!!! tip "Управление сессиями"
    ```python
    sessions = await client.get_sessions()
    for session in sessions:
        print(
            f"{'Текущая' if session.current else 'Активная'} "
            f"сессия: {session.client} из {session.location}"
        )
    ```

# Типы данных

## Содержание

- [Перечисления (Enums)](#перечисления-enums)
- [Основные Классы](#основные-классы)
- [Вложения](#вложения)
- [Служебные Типы](#служебные-типы)

##  Перечисления (Enums) {#перечисления-enums}

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
    | `AUDIO` | Аудио/голосовое сообщение |
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

##  Основные классы {#основные-классы}

### Names

!!! info "Информация об именах пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `name` | `str` | Полное имя |
    | `first_name` | `str` | Имя |
    | `last_name` | `str | None` | Фамилия (опционально) |
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
    | `chat_id` | `int | None` | ID чата |
    | `sender` | `int | None` | ID отправителя |
    | `text` | `str` | Текст сообщения |
    | `time` | `int` | Временная метка |
    | `status` | `MessageStatus | str | None` | Статус сообщения |
    | `type` | `MessageType | str` | Тип сообщения |
    | `elements` | `list[Element] | None` | Элементы форматирования |
    | `reaction_info` | `ReactionInfo | None` | Информация о реакциях |
    | `attaches` | `list[PhotoAttach | VideoAttach | FileAttach | StickerAttach | AudioAttach | ControlAttach] | None` | Вложения |
    | `link` | `MessageLink | None` | Связанное сообщение |
    | `options` | `int | None` | Опции сообщения |

### Chat

!!! info "Представление чата или группы"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID чата |
    | `type` | `ChatType | str` | Тип чата |
    | `title` | `str | None` | Название |
    | `description` | `str | None` | Описание |
    | `owner` | `int` | ID владельца |
    | `access` | `AccessType | str` | Тип доступа |
    | `participants_count` | `int` | Кол-во участников |
    | `admins` | `list[int]` | ID администраторов |
    | `participants` | `dict[int, int]` | Участники |
    | `link` | `str | None` | Ссылка-приглашение |
    | `base_icon_url` | `str | None` | URL иконки |
    | `invited_by` | `int | None` | Кто пригласил |
    | `base_raw_icon_url` | `str | None` | Внутренний URL иконки |
    | `admin_participants` | `dict[int, dict[Any, Any]]` | Структура админов |
    | `last_message` | `Message | None` | Последнее сообщение |
    | `last_event_time` | `int` | Время последнего события |
    | `last_fire_delayed_error_time` | `int` | Время последней отложенной ошибки |
    | `modified` | `int` | Время последнего изменения |
    | `options` | `dict[str, bool]` | Опции чата |
    | `prev_message_id` | `str | None` | ID предыдущего сообщения |
    | `status` | `str` | Статус чата |
    | `cid` | `int` | Внутренний CID чата |
    | `created` | `int` | Время создания чата |
    | `join_time` | `int` | Время присоединения |
    | `last_delayed_update_time` | `int` | Время последнего отложенного обновления |
    | `messages_count` | `int` | Кол-во сообщений в чате |
    | `restrictions` | `int | None` | Ограничения в чате |

!!! tip "Работа с чатами"
    ```python
    if chat.type == ChatType.CHAT:
        # Групповой чат
        print(f"Участников: {chat.participants_count}")

        # Проверяем права
        if client.me.id in chat.admins:
            print("Вы администратор")
    ```

### Me

!!! info "Информация о текущем пользователе"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID пользователя |
    | `phone` | `str` | Номер телефона |
    | `names` | `list[Names]` | Имена профиля |
    | `account_status` | `int` | Код статуса аккаунта |
    | `update_time` | `int` | Время последнего обновления |
    | `options` | `list[str] | None` | Опции профиля |

### Contact

!!! info "Запись в адресной книге"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID контакта |
    | `names` | `list[Names]` | Список имён |
    | `account_status` | `int` | Код статуса аккаунта |
    | `base_url` | `str | None` | URL ресурса для изображений |
    | `base_raw_url` | `str | None` | Внутренний URL для изображений |
    | `options` | `list[str] | None` | Дополнительные параметры |
    | `photo_id` | `int | None` | ID фото профиля/контакта |
    | `update_time` | `int` | Время обновления записи |

### User

!!! info "Представление пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `id` | `int` | ID пользователя |
    | `names` | `list[Names]` | Имена |
    | `account_status` | `int` | Статус аккаунта |
    | `update_time` | `int` | Время обновления |
    | `options` | `list[str] | None` | Опции |
    | `base_url` | `str | None` | URL профиля |
    | `base_raw_url` | `str | None` | Внутренний URL профиля |
    | `gender` | `int | None` | Пол пользователя (опционально) |
    | `web_app` | `str | None` | URL веб-приложения пользователя |
    | `menu_button` | `dict[str, Any] | None` | Конфигурация меню кнопки |
    | `photo_id` | `int | None` | ID фото |
    | `description` | `str | None` | Описание |
    | `link` | `str | None` | Ссылка на профиль |

**Пример работы с пользователем**
```python
user = await client.get_user(123456)
if user:
    name = user.names[0] if user.names else None
    print(f"Профиль: {name.first_name if name else 'Неизвестно'}")
    if user.photo_id:
        print("Есть фото профиля")
```

##  Вложения {#вложения}

### Attach

!!! note "Общий тип вложения (внутренний, используется для упрощённого парсинга)"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `type` | `AttachType` | Тип вложения |
    | `video_id` | `int | None` | ID видео (если применимо) |
    | `photo_token` | `str | None` | Токен фотографии |
    | `file_id` | `int | None` | ID файла |
    | `token` | `str | None` | Токен доступа |


### PhotoAttach

!!! info "Фотография-вложение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `photo_id` | `int` | ID фотографии |
    | `base_url` | `str` | URL фотографии |
    | `height` | `int` | Высота |
    | `width` | `int` | Ширина |
    | `photo_token` | `str` | Токен |
    | `preview_data` | `str | None` | Данные превью (если есть) |
    | `type` | `AttachType` | Всегда `PHOTO` |

**Пример отправки фото**
```python
photo = Photo(path="photo.jpg")
message = await client.send_message(
    chat_id=123456,
    text="Смотри, какое фото!",
    attachment=photo
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
    | `preview_data` | `str` | Данные превью |
    | `thumbnail` | `str` | URL миниатюры |
    | `token` | `str` | Токен для доступа |
    | `video_type` | `int` | Тип видео |
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

### StickerAttach

!!! info "Стикер-вложение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `sticker_id` | `int` | ID стикера |
    | `set_id` | `int` | ID набора стикеров |
    | `url` | `str` | URL стикера |
    | `lottie_url` | `str` | URL Lottie анимации |
    | `width` | `int` | Ширина |
    | `height` | `int` | Высота |
    | `author_type` | `str` | Тип автора |
    | `sticker_type` | `str` | Тип стикера |
    | `audio` | `bool` | Содержит ли звук |
    | `tags` | `list[str] | None` | Теги стикера |
    | `time` | `int` | Временная метка |
    | `type` | `AttachType` | Всегда `STICKER` |

**Пример использования**
```python
if isinstance(attach, StickerAttach):
    print(f"Стикер: {attach.sticker_id}")
    print(f"Набор: {attach.set_id}")
    if attach.audio:
        print("Стикер с звуком!")
```

### AudioAttach

!!! info "Аудио/голосовое сообщение"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `audio_id` | `int` | ID аудио |
    | `duration` | `int` | Длительность (сек) |
    | `url` | `str` | URL аудиофайла |
    | `wave` | `str` | Данные волны (для визуализации) |
    | `transcription_status` | `str` | Статус транскрипции |
    | `token` | `str` | Токен для доступа |
    | `type` | `AttachType` | Всегда `AUDIO` |

**Пример получения аудио**
```python
if isinstance(attach, AudioAttach):
    print(f"Голосовое сообщение: {attach.duration}с")
    print(f"Транскрипция: {attach.transcription_status}")
```

### ControlAttach

!!! info "Управляющее вложение (внутренний тип)"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `type` | `AttachType` | Всегда `CONTROL` |
    | `event` | `str` | Тип события |
    | `extra` | `dict` | Дополнительные данные события |

!!! note "Служебный тип"
    ControlAttach используется внутренне для системных событий. Обычно не требует обработки в пользовательском коде.

##  Служебные типы {#служебные-типы}

### Element

!!! info "Элемент форматирования сообщения"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `type` | `ElementType | str` | Тип элемента (text, mention, link, emoji) |
    | `length` | `int` | Длина элемента |
    | `from_` | `int | None` | ID пользователя (для упоминаний) |

**Пример работы с элементами**
```python
for element in message.elements or []:
    if element.type == ElementType.MENTION:
        user = await client.get_user(element.from_)
        if user:
            print(f"Упомянут: {user.names[0].name}")
```
!!! note "Пояснение"
    В JSON API поле называется `from`, в Python оно доступно как `from_` (с нижним подчёркиванием), чтобы избежать конфликтов с ключевым словом `from`.

### ReactionInfo

!!! info "Информация о реакциях"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `total_count` | `int` | Всего реакций |
    | `counters` | `list[ReactionCounter]` | Счётчики реакций |
    | `your_reaction` | `str | None` | Ваша реакция |

**Работа с реакциями**
```python
if message.reaction_info:
    print(f"Всего реакций: {message.reaction_info.total_count}")
    for counter in message.reaction_info.counters:
        print(f"{counter.reaction}: {counter.count}")
```

### MessageLink

!!! info "Ссылка на сообщение в другом чате/диалоге"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `chat_id` | `int` | ID чата, в котором находится сообщение |
    | `message` | `Message` | Объект сообщения |
    | `type` | `str` | Тип ссылки |

### ReactionCounter

!!! info "Запись о количестве реакций определённого типа"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `count` | `int` | Кол-во реакций |
    | `reaction` | `str` | Символ/тип реакции |


### Presence

!!! info "Информация о присутствии пользователя"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `seen` | `int | None` | Временная метка последнего появления в системе |

### FileRequest

!!! info "Запрос файла/запрос загрузки"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `unsafe` | `bool` | Флаг небезопасного файла |
    | `url` | `str` | URL файла |

### VideoRequest

!!! info "Запрос видео"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `external` | `str` | Внешний идентификатор источника |
    | `cache` | `bool` | Флаг кеширования |
    | `url` | `str` | URL видео |

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

### Folder

!!! info "Папка (фильтр чатов)"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `source_id` | `int` | ID источника/регистратора папки |
    | `include` | `list[int]` | Список ID чатов, включённых в папку |
    | `options` | `list[Any]` | Дополнительные опции папки |
    | `update_time` | `int` | Временная метка последнего обновления папки |
    | `id` | `str` | Уникальный идентификатор папки |
    | `filters` | `list[Any]` | Правила/фильтры папки |
    | `title` | `str` | Название папки |

**Пример использования**
```python
folders = await client.get_folders()
if folders and folders.folders:
    folder = folders.folders[0]
    print("Folder:", folder.title, folder.id)
```

### FolderUpdate

!!! info "Результат создания/обновления/удаления папки"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `folder_order` | `list[str] | None` | Порядок ID папок после операции |
    | `folder` | `Folder | None` | Данные папки, если присутствуют |
    | `folder_sync` | `int` | Синхронизационный маркер папок |

**Пример использования**
```python
result = await client.create_folder(title="Friends", chat_include=[1, 2, 3])
print(result.folder.id, result.folder.title)
```

### FolderList

!!! info "Список папок"
    | Свойство | Тип | Описание |
    |----------|-----|----------|
    | `folders_order` | `list[str]` | Порядок ID папок |
    | `folders` | `list[Folder]` | Список объектов `Folder` |
    | `folder_sync` | `int` | Синхронизационный маркер |
    | `all_filter_exclude_folders` | `list[Any] | None` | Исключённые папки для фильтров |

**Пример использования**
```python
folders = await client.get_folders()
for f in folders.folders:
    print(f.title, f.id)
```

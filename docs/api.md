# Полная документация API

Всё, что нужно знать о методах, типах и возможностях PyMax — асинхронный WebSocket клиент для мессенджера Max.

## Содержание

- [Клиент](#client)
- [Типы данных](#data-types)
- [Исключения](#exceptions)
- [Перечисления](#enumerations)

---

## Клиент {#client}

### MaxClient

Основной асинхронный WebSocket клиент для взаимодействия с сервисом мессенджера Max.

#### Конструктор

```python
MaxClient(
    phone: str,
    uri: str = "wss://...",
    headers: UserAgentPayload = UserAgentPayload(),
    token: str | None = None,
    send_fake_telemetry: bool = True,
    host: str = "...",
    port: int = ...,
    proxy: str | Literal[True] | None = None,
    work_dir: str = ".",
    registration: bool = False,
    first_name: str = "",
    last_name: str | None = None,
    logger: logging.Logger | None = None,
    reconnect: bool = True,
    reconnect_delay: float = 1.0,
)
```

**Параметры:**

| Параметр | Тип | Описание |
|----------|-----|---------|
| `phone` | `str` | Номер телефона для авторизации (обязательно) |
| `uri` | `str` | URI WebSocket сервера |
| `headers` | `UserAgentPayload` | Заголовки User-Agent для подключения |
| `token` | `str | None` | Токен для восстановления сессии |
| `send_fake_telemetry` | `bool` | Отправлять ли фейковую телеметрию (по умолчанию True) |
| `host` | `str` | Хост API сервера |
| `port` | `int` | Порт API сервера |
| `proxy` | `str | Literal[True] | None` | Прокси для WebSocket подключения |
| `work_dir` | `str` | Директория для хранения БД сессии |
| `registration` | `bool` | Регистрировать ли новый аккаунт |
| `first_name` | `str` | Имя для регистрации (если registration=True) |
| `last_name` | `str | None` | Фамилия для регистрации |
| `logger` | `logging.Logger | None` | Пользовательский логгер |
| `reconnect` | `bool` | Автоматическое переподключение при разрыве |
| `reconnect_delay` | `float` | Задержка переподключения в секундах |

#### Основные методы

##### async start() -> None

Запускает клиент, подключается к WebSocket и авторизует пользователя.

```python
client = MaxClient(phone="+1234567890")
await client.start()
```

##### async close() -> None

Корректно закрывает клиент и завершает все фоновые задачи.

```python
await client.close()
```

##### async get_chats(chat_ids: list[int]) -> list[Chat]

Получает информацию о нескольких чатах по их ID.

```python
chats = await client.get_chats([123, 456])
```

##### async get_chat(chat_id: int) -> Chat

Получает информацию об одном чате по его ID.

```python
chat = await client.get_chat(123)
```

##### async create_folder(title: str, chat_include: list[int], filters: list[Any] | None = None) -> FolderUpdate

Создаёт новую папку (фильтр) и возвращает результат операции.

```python
res = await client.create_folder(title="Friends", chat_include=[111,222])
```

##### async get_folders(folder_sync: int = 0) -> FolderList

Возвращает список папок текущего пользователя.

```python
folders = await client.get_folders()
```

##### async update_folder(folder_id: str, title: str, chat_include: list[int] | None = None, filters: list[Any] | None = None, options: list[Any] | None = None) -> FolderUpdate

Обновляет существующую папку.

```python
updated = await client.update_folder(folder_id=res.folder.id, title="Best")
```

##### async delete_folder(folder_id: str) -> FolderUpdate

Удаляет папку и возвращает информацию об обновлении порядка папок.

```python
await client.delete_folder(folder_id=res.folder.id)
```

#### Свойства

| Свойство | Тип | Описание |
|----------|-----|---------|
| `is_connected` | `bool` | Статус подключения к WebSocket |
| `phone` | `str` | Номер телефона клиента |
| `me` | `Me | None` | Информация о текущем пользователе |
| `chats` | `list[Chat]` | Список всех чатов и групп |
| `dialogs` | `list[Dialog]` | Список личных диалогов |
| `channels` | `list[Channel]` | Список каналов |
| `logger` | `logging.Logger` | Логгер клиента |

#### Обработчики событий

##### @on_message(filter: Filter | None = None)

Регистрирует обработчик входящих сообщений.

```python
@client.on_message()
async def handle_message(msg: Message):
    print(f"Сообщение от {msg.sender}: {msg.text}")
```

##### @on_message_edit(filter: Filter | None = None)

Регистрирует обработчик редактированных сообщений.

```python
@client.on_message_edit()
async def handle_edited(msg: Message):
    print(f"Сообщение {msg.id} отредактировано")
```

##### @on_message_delete(filter: Filter | None = None)

Регистрирует обработчик удаленных сообщений.

```python
@client.on_message_delete()
async def handle_deleted(msg: Message):
    print(f"Сообщение {msg.id} удалено")
```

##### @on_reaction_change

Регистрирует обработчик изменения реакций.

```python
@client.on_reaction_change
async def handle_reaction(reaction: str, message_id: int, info: ReactionInfo):
    print(f"Реакция: {reaction}")
```

##### @on_chat_update

Регистрирует обработчик обновлений чата.

```python
@client.on_chat_update
async def handle_chat_update(chat: Chat):
    print(f"Чат {chat.id} обновлен")
```

##### @on_start()

Регистрирует обработчик события запуска клиента.

```python
@client.on_start()
async def on_startup():
    print("Клиент запущен!")
```

### SocketMaxClient

Вариант клиента на основе TCP сокета, наследует все методы и свойства MaxClient.

```python
client = SocketMaxClient(phone="+1234567890")
```

---

## Типы данных {#data-types}

### Me

Информация о профиле текущего пользователя.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID пользователя |
| `phone` | `str` | Номер телефона |
| `names` | `list[Names]` | Список имен профиля |
| `account_status` | `int` | Код статуса аккаунта |
| `update_time` | `int` | Время последнего обновления профиля |
| `options` | `list[str] | None` | Дополнительные параметры |

### User

Информация о пользователе.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID пользователя |
| `names` | `list[Names]` | Список имен |
| `account_status` | `int` | Статус аккаунта |
| `update_time` | `int` | Время обновления профиля |
| `options` | `list[str] | None` | Опции |
| `base_url` | `str | None` | URL профиля |
| `base_raw_url` | `str | None` | Внутренний URL профиля |
| `photo_id` | `int | None` | ID фото профиля |
| `description` | `str | None` | Биография/описание |
| `gender` | `int | None` | Пол пользователя |
| `link` | `str | None` | Ссылка на профиль |
| `web_app` | `str | None` | URL веб-приложения пользователя |
| `menu_button` | `dict[str, Any] | None` | Конфигурация меню-кнопки |

### Message

Сообщение в чате.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID сообщения |
| `chat_id` | `int | None` | ID чата/диалога |
| `sender` | `int | None` | ID отправителя |
| `text` | `str` | Текст сообщения |
| `time` | `int` | Unix timestamp |
| `type` | `MessageType | str` | Тип сообщения |
| `elements` | `list[Element] | None` | Элементы форматирования |
| `attaches` | `list[PhotoAttach | VideoAttach | FileAttach | StickerAttach | AudioAttach | ControlAttach] | None` | Вложенные файлы/медиа |
| `status` | `MessageStatus | None` | Статус сообщения |
| `reaction_info` | `ReactionInfo | None` | Данные реакций |
| `link` | `MessageLink | None` | Связанное сообщение |
| `options` | `int | None` | Опции сообщения |

### MessageLink

Связь на сообщение в другом чате/диалоге.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `chat_id` | `int` | ID чата |
| `message` | `Message` | Объект сообщения |
| `type` | `str` | Тип ссылки |

### ReactionCounter

Счётчик конкретной реакции.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `count` | `int` | Количество реакций |
| `reaction` | `str` | Символ/тип реакции |

### Presence

Информация о присутствии пользователя.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `seen` | `int | None` | Временная метка последнего посещения |

### FileRequest

Запрос файла (метаданные).

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `unsafe` | `bool` | Небезопасен ли файл |
| `url` | `str` | Ссылка на файл |

### VideoRequest

Запрос видео (метаданные).

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `external` | `str` | Внешний источник video |
| `cache` | `bool` | Использовать кеш |
| `url` | `str` | Ссылка на видео |

### Chat

Информация о чате или группе.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID чата |
| `type` | `ChatType | str` | Тип: DIALOG, CHAT, CHANNEL |
| `title` | `str | None` | Название чата |
| `owner` | `int` | ID владельца |
| `access` | `AccessType | str` | Тип доступа (PUBLIC, PRIVATE, SECRET) |
| `participants_count` | `int` | Количество участников |
| `admins` | `list[int]` | Список ID администраторов |
| `description` | `str | None` | Описание чата |
| `link` | `str | None` | Ссылка-приглашение |
| `base_icon_url` | `str | None` | URL иконки чата |
| `base_raw_icon_url` | `str | None` | Внутренний URL иконки |
| `cid` | `int` | Внутренний CID чата |
| `created` | `int` | Время создания чата |
| `join_time` | `int` | Время присоединения |
| `last_message` | `Message | None` | Последнее сообщение |
| `last_event_time` | `int` | Время последнего события |
| `last_delayed_update_time` | `int` | Время последнего отложенного обновления |
| `last_fire_delayed_error_time` | `int` | Время последней отложенной ошибки |
| `messages_count` | `int` | Количество сообщений |
| `modified` | `int` | Время последнего изменения |
| `admin_participants` | `dict[int, dict[Any, Any]]` | Структура администраторов |
| `options` | `dict[str, bool]` | Опции чата |
| `prev_message_id` | `str | None` | ID предыдущего сообщения |
| `restrictions` | `int | None` | Ограничения в чате |
| `status` | `str` | Статус чата |

### Folder

Папка (фильтр для чатов пользователя).

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `source_id` | `int` | ID источника папки |
| `include` | `list[int]` | Список ID чатов, включённых в папку |
| `options` | `list[Any]` | Опции папки |
| `update_time` | `int` | Время последнего обновления папки |
| `id` | `str` | Уникальный ID папки |
| `filters` | `list[Any]` | Правила/фильтры папки |
| `title` | `str` | Название папки |

### FolderUpdate

Результат операций обновления/создания/удаления папки.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `folder_order` | `list[str] | None` | Порядок ID папок после операции |
| `folder` | `Folder | None` | Обновлённый объект папки, если присутствует |
| `folder_sync` | `int` | Синхронизационный маркер папок |

### FolderList

Список папок пользователя.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `folders_order` | `list[str]` | Порядок ID папок |
| `folders` | `list[Folder]` | Список объектов `Folder` |
| `folder_sync` | `int` | Синхронизационный маркер |
| `all_filter_exclude_folders` | `list[Any] | None` | Исключённые папки для фильтров |

### Dialog

Личный диалог между двумя пользователями.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID диалога |
| `owner` | `int` | ID собеседника |
| `type` | `ChatType` | Всегда `ChatType.DIALOG` |
| `last_message` | `Message | None` | Последнее сообщение |
| `cid` | `int | None` | Внутренний CID диалога |
| `has_bots` | `bool | None` | Наличие ботов в диалоге |
| `join_time` | `int` | Время присоединения |
| `created` | `int` | Время создания |
| `last_fire_delayed_error_time` | `int` | Время последней отложенной ошибки |
| `last_delayed_update_time` | `int` | Время последнего отложенного обновления |
| `prev_message_id` | `str | None` | ID предыдущего сообщения |
| `options` | `dict` | Опции диалога |
| `modified` | `int` | Время последнего изменения |
| `last_event_time` | `int` | Время последнего события |
| `participants` | `dict[str, int]` | Список участников |
| `status` | `str` | Статус диалога |

### Channel

Канал (наследуется от Chat). Специализированный тип чата для трансляции информации.

### Contact

Запись в адресной книге.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID контакта |
| `names` | `list[Names]` | Имена контакта |
| `account_status` | `int` | Код статуса |
| `photo_id` | `int | None` | ID фото контакта |
| `base_url` | `str | None` | URL для изображений |
| `base_raw_url` | `str | None` | Внутренний URL для изображений |
| `options` | `list[str] | None` | Дополнительные параметры |
| `update_time` | `int` | Время обновления контакта |

### Member

Участник чата.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `contact` | `Contact` | Информация о контакте участника |
| `presence` | `Presence | None` | Статус онлайна |
| `read_mark` | `int` | Последнее прочитанное сообщение |

### Типы вложений

#### PhotoAttach

Вложение с фотографией.

```python
PhotoAttach(photo_id: int, base_url: str, width: int, height: int, preview_data: str | None, ...)
```

#### VideoAttach

Вложение с видео.

```python
VideoAttach(id: int, width: int, height: int, duration: int, ...)
```

#### FileAttach

Вложение с файлом.

```python
FileAttach(id: int, name: str, size: int, ...)
```

#### StickerAttach

Вложение со стикером.

```python
StickerAttach(sticker_id: int, set_id: int, ...)
```

#### AudioAttach

Вложение с аудио/голосовым сообщением.

```python
AudioAttach(audio_id: int, duration: int, ...)
```

#### ControlAttach

Вложение с управляющим сообщением (специальный внутренний тип).

---

## Исключения {#exceptions}

### Error

Базовое исключение для всех ошибок PyMax.

```python
try:
    await client.start()
except pymax.Error as e:
    print(f"Ошибка: {e.message}")
```

**Свойства:**

- `error`: Код ошибки
- `message`: Сообщение об ошибке
- `title`: Заголовок ошибки
- `localized_message`: Локализованное сообщение

### InvalidPhoneError

Возникает, когда формат номера телефона неверный.

```python
except pymax.InvalidPhoneError:
    print("Неверный номер телефона")
```

### LoginError

Возникает при ошибке авторизации.

```python
except pymax.LoginError:
    print("Ошибка входа")
```

### WebSocketNotConnectedError

Возникает, когда WebSocket не подключен.

```python
except pymax.WebSocketNotConnectedError:
    print("WebSocket отключен")
```

### SocketNotConnectedError

Возникает, когда TCP сокет не подключен (SocketMaxClient).

```python
except pymax.SocketNotConnectedError:
    print("Сокет отключен")
```

### RateLimitError

Возникает при превышении лимита запросов.

```python
except pymax.RateLimitError as e:
    print(f"Лимит превышен")
```

### ResponseError

Возникает, когда ответ сервера указывает на ошибку.

```python
except pymax.ResponseError as e:
    print(f"Ошибка сервера: {e.error}")
```

---

## Перечисления {#enumerations}

### ChatType

Тип классификации чата.

| Значение | Описание |
|----------|---------|
| `DIALOG` | Личная переписка (1:1) |
| `CHAT` | Групповой чат |
| `CHANNEL` | Канал/трансляция |

```python
from pymax import ChatType

if chat.type == ChatType.DIALOG:
    print("Личный чат")
```

### MessageType

Тип классификации сообщения.

| Значение | Описание |
|----------|---------|
| `TEXT` | Обычное текстовое сообщение |
| `SYSTEM` | Системное сообщение |
| `SERVICE` | Сервисное сообщение |

### MessageStatus

Флаги статуса сообщения.

| Значение | Описание |
|----------|---------|
| `EDITED` | Сообщение отредактировано |
| `REMOVED` | Сообщение удалено |

### AccessType

Уровень доступа для чатов/каналов.

| Значение | Описание |
|----------|---------|
| `PUBLIC` | Открытый доступ |
| `PRIVATE` | Приватный (только по приглашению) |
| `SECRET` | Секретный/зашифрованный |

### AttachType

Тип вложения файла.

| Значение | Описание |
|----------|---------|
| `PHOTO` | Фотография/изображение |
| `VIDEO` | Видеофайл |
| `FILE` | Документ/файл |
| `STICKER` | Стикер/эмодзи |
| `AUDIO` | Аудио/голосовое сообщение |
| `CONTROL` | Управляющее/системное вложение |

### DeviceType

Тип устройства платформы.

| Значение | Описание |
|----------|---------|
| `WEB` | Веб-приложение |
| `ANDROID` | Приложение Android |
| `IOS` | Приложение iOS |
| `DESKTOP` | Десктопный клиент |

### AuthType

Тип метода аутентификации.

| Значение | Описание |
|----------|---------|
| `START_AUTH` | Начало процесса аутентификации |
| `CHECK_CODE` | Проверка кода OTP |
| `REGISTER` | Регистрация нового аккаунта |

### ElementType

Тип элемента форматированного текста.

| Значение | Описание |
|----------|---------|
| `text` | Простой текст |
| `mention` | Упоминание пользователя @user |
| `link` | Гиперссылка |
| `emoji` | Эмодзи/эмотикон |

### FormattingType

Тип форматирования текста.

| Значение | Описание |
|----------|---------|
| `STRONG` | Жирный текст |
| `EMPHASIZED` | Курсив |
| `UNDERLINE` | Подчеркивание |
| `STRIKETHROUGH` | Зачеркивание |

### MarkupType

Тип разметки сообщения.

| Значение | Описание |
|----------|---------|
| `TEXT` | Простой текст |
| `HTML` | Разметка HTML |
| `MARKDOWN` | Разметка Markdown |

### ContactAction

Действие взаимодействия с контактом.

| Значение | Описание |
|----------|---------|
| `ADDED` | Контакт добавлен |
| `REMOVED` | Контакт удален |
| `CHANGED` | Информация контакта изменена |

### Opcode

Коды операций протокола WebSocket (150+ значений).

Коды низкоуровневого общения для внутреннего использования.

---

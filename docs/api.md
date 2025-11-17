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
    uri: str = "...",
    token: str | None = None,
    work_dir: str = "...",
    reconnect: bool = True,
    reconnect_delay: float = 5.0,
    ...
)
```

**Параметры:**

| Параметр | Тип | Описание |
|----------|-----|---------|
| `phone` | `str` | Номер телефона для авторизации (обязательно) |
| `uri` | `str` | URI WebSocket сервера |
| `token` | `str | None` | Токен для восстановления сессии |
| `work_dir` | `str` | Директория для БД сессии |
| `reconnect` | `bool` | Включить автоматическое переподключение |
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
| `options` | `dict` | Дополнительные параметры |

### User

Информация о пользователе.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID пользователя |
| `names` | `list[Names]` | Список имен |
| `account_status` | `int` | Статус аккаунта |
| `photo_id` | `int | None` | ID фото профиля |
| `description` | `str | None` | Биография/описание |

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
| `attaches` | `list` | Вложенные файлы/медиа |
| `reaction_info` | `ReactionInfo | None` | Данные реакций |
| `edit_time` | `int | None` | Время редактирования |

### Chat

Информация о чате или группе.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID чата |
| `type` | `ChatType | str` | Тип: DIALOG, CHAT, CHANNEL |
| `title` | `str | None` | Название чата |
| `owner` | `int` | ID владельца |
| `participants_count` | `int` | Количество участников |
| `admins` | `list[int]` | Список ID администраторов |
| `description` | `str | None` | Описание чата |
| `rules` | `str | None` | Правила чата |

### Dialog

Личный диалог между двумя пользователями.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID диалога |
| `owner` | `int` | ID собеседника |
| `type` | `ChatType` | Всегда `ChatType.DIALOG` |
| `last_message` | `Message | None` | Последнее сообщение |

### Channel

Канал (наследуется от Chat). Специализированный тип чата для трансляции информации.

### Contact

Запись в адресной книге.

**Свойства:**

| Свойство | Тип | Описание |
|----------|-----|---------|
| `id` | `int` | ID контакта |
| `names` | `list[Names]` | Имена контакта |
| `status` | `int` | Код статуса |
| `photos` | `list` | Фотографии контакта |

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
PhotoAttach(id: int, width: int, height: int, ...)
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
StickerAttach(id: int, sticker_id: int, ...)
```

#### AudioAttach

Вложение с аудио/голосовым сообщением.

```python
AudioAttach(id: int, duration: int, ...)
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
    print(f"Лимит превышен на {e.retry_after} секунд")
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
| `bold` | Жирное форматирование |
| `italic` | Курсивное форматирование |

### FormattingType

Тип форматирования текста.

| Значение | Описание |
|----------|---------|
| `BOLD` | Жирный текст |
| `ITALIC` | Курсив |
| `UNDERLINE` | Подчеркивание |
| `STRIKETHROUGH` | Зачеркивание |
| `MONOSPACE` | Моноширинный/код |

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

Коды низкоуровневого общения для внутреннего использования. Основные примеры:

| Значение | Код | Описание |
|----------|-----|---------|
| 1 | `PING` | Проверка соединения |
| 2 | `PONG` | Ответ на проверку |
| 3 | `LOGIN` | Запрос аутентификации |
| 4 | `MSG_SEND` | Отправка сообщения |
| 5 | `MSG_READ` | Отметить сообщение прочитанным |

---

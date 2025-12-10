<p align="center">
    <img src="assets/logo.svg" alt="PyMax" width="400">
</p>

<p align="center">
    <strong>Python wrapper для API мессенджера Max</strong>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-3776AB.svg" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/License-MIT-2f9872.svg" alt="License: MIT">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
    <img src="https://img.shields.io/badge/packaging-uv-D7FF64.svg" alt="Packaging">
</p>

---
> ⚠️ **Дисклеймер**
>
> *   Это **неофициальная** библиотека для работы с внутренним API Max.
> *   Использование может **нарушать условия предоставления услуг** сервиса.
> *   **Вы используете её исключительно на свой страх и риск.**
> *   **Разработчики и контрибьюторы не несут никакой ответственности** за любые последствия использования этого пакета, включая, но не ограничиваясь: блокировку аккаунтов, утерю данных, юридические риски и любые другие проблемы.
> *   API может быть изменен в любой момент без предупреждения.
---

## Описание

**`pymax`** — асинхронная Python библиотека для работы с API мессенджера Max. Предоставляет интерфейс для отправки сообщений, управления чатами, каналами и диалогами через WebSocket соединение.

### Основные возможности

- Вход по номеру телефона
- Отправка, редактирование и удаление сообщений
- Работа с чатами и каналами
- История сообщений

## Установка

> [!IMPORTANT]
> Для работы библиотеки требуется Python 3.10 или выше

### Установка через pip

```bash
pip install -U maxapi-python
```

### Установка через uv

```bash
uv add -U maxapi-python
```

## Быстрый старт

### Базовый пример использования

```python
import asyncio

from pymax import MaxClient, Message
from pymax.filters import Filter

client = MaxClient(
    phone="+1234567890",
    work_dir="cache",  # директория для сессий
)


# Обработка входящих сообщений
@client.on_message(filter=Filter(text=["!hello"]))
async def on_message(msg: Message) -> None:
    print(f"[{msg.sender}] {msg.text}")

    await client.send_message(
        chat_id=msg.chat_id,
        text="Привет, я бот на PyMax!",
    )

    await client.add_reaction(
        chat_id=msg.chat_id,
        message_id=str(msg.id),
        reaction="👍",
    )


@client.on_start
async def on_start() -> None:
    print(f"Клиент запущен. Ваш ID: {client.me.id}")

    # Получение истории
    history = await client.fetch_history(chat_id=0)
    print("Последние сообщения из чата 0:")
    for m in history:
        print(f"- {m.text}")


async def main():
    await client.start()  # подключение и авторизация


if __name__ == "__main__":
    asyncio.run(main())
```

## Документация

[Click (WIP)](https://maxapiteam.github.io/PyMax/)

## Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для получения информации.

## Новости

[Telegram](https://t.me/pymax_news)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ink-developer/PyMax&type=date&legend=top-left)](https://www.star-history.com/#ink-developer/PyMax&type=date&legend=top-left)

## Авторы
- **[ink](https://github.com/ink-developer)** — Главный разработчик, исследование API и его документация
- **[noxzion](https://github.com/noxzion)** — Оригинальный автор проекта


## Контрибьюторы

Спасибо всем за помощь в разработке!

<a href="https://github.com/ink-developer/PyMax/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ink-developer/PyMax" />
</a>

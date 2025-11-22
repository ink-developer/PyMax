# Примеры использования

Ниже — небольшие и наглядные примеры, которые можно вставить прямо в проект.
Все примеры используют реальные методы библиотеки (см. исходники).

## Быстрый старт: запуск клиента и обработчики

Классический пример: регистрируем обработчики и запускаем клиента через `start()`.

```python
import asyncio
from pymax import MaxClient
from pymax.filters import Filter
from pymax.types import Message

client = MaxClient(phone="+79000000000", work_dir="cache", reconnect=False)


@client.on_start
async def on_start() -> None:
	# Метаданные пользователя доступны после синхронизации
	print("Client started, me id:", client.me.id)
	await client.send_message("Бот запущен!", chat_id=0, notify=True)


@client.on_message(filter=Filter(chat_id=0))
async def on_message(message: Message) -> None:
	print("New message:", message.text)
	# Отправка простого ответа
	await client.send_message(f"Echo: {message.text}", chat_id=message.chat_id, notify=False)


if __name__ == "__main__":
	asyncio.run(client.start())
```

## Контекстный менеджер и .idle()

Используем `async with` (реализован в `__aenter__/__aexit__`) и `idle()` для ожидания событий.

```python
import asyncio
from pymax import MaxClient
from pymax.files import File

client = MaxClient(phone="+79000000000", work_dir="cache")


async def run():
	async with client:
		# внутри блока клиент подключён и синхронизирован
		await client.send_message("Привет от контекстного менеджера!", chat_id=0, notify=True)

		# отправка файла (локальный файл)
		file = File(path="ruff.toml")
		await client.send_message("Вот файл", chat_id=0, notify=True, attachment=file)

		# блокируемся и ждём событий
		await client.idle()


if __name__ == "__main__":
	asyncio.run(run())
```

## Отправка вложений и работа с историей

Короткий пример: отправляем файл/фото, получаем историю и скачиваем файл по id.

```python
from pymax import MaxClient, File
from pymax.static.enum import AttachType

client = MaxClient(phone="+79000000000")

@client.on_start
async def _():
	# отправить один файл
	f = File(path="tests/test.txt")
	msg = await client.send_message("Файл", chat_id=0, notify=True, attachment=f)
	if msg:
		print("Отправлено сообщение id=", msg.id)

	# получить историю и найти вложения
	history = await client.fetch_history(chat_id=0)
	if history:
		for m in history:
			if m.attaches:
				# Пример: если в сообщении есть вложение типа FILE
				for a in m.attaches:
					if a.type == AttachType.FILE:
						file_info = await client.get_file_by_id(chat_id=m.chat_id, message_id=m.id, file_id=a.file_id)
						print("Файл для скачивания:", file_info.url)

```

## Кастомный login flow

Если нужно реализовать кастомный вход (без автоматического интерфейса), используйте `request_code` и `login_with_code`.

```python
import asyncio
from pymax import MaxClient

phone = "+79000000000"
client = MaxClient(phone=phone, work_dir="cache", reconnect=False)


async def login_flow_test():
	# Подключение к WS для отправки запроса к API
	await client.connect()

	# Запрашиваем временный токен (в сервис уходит SMS с кодом)
	temp_token = await client.request_code(phone)

	# Вводим код вручную
	code = input("Введите код: ").strip()

	# Отправляем код и сохраняем токен. start=False — не запускать пост-логин задачи автоматически
	await client.login_with_code(temp_token, code, start=False)

	# Токен сохранён в БД, теперь можно запустить обычный старт клиента
	await client.start()


if __name__ == "__main__":
	asyncio.run(login_flow_test())
```
## Короткие полезные примеры

Ниже — ещё пара компактных сценариев, которые удобно вставлять прямо в проект.

### Редактирование и закрепление сообщения

```python
from pymax import MaxClient
from pymax.filters import Filter
from pymax.types import Message

client = MaxClient(phone="+79000000000")

@client.on_message(filter=Filter(chat_id=0))
async def edit_and_pin(message: Message) -> None:
	# Обновляем текст
	await client.edit_message(chat_id=message.chat_id, message_id=message.id, text="Обновлённый текст")
	# Закрепляем сообщение
	await client.pin_message(chat_id=message.chat_id, message_id=message.id, notify_pin=True)

```

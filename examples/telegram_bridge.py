# УСТАНОВИТЬ ЗАВИСИМОСТИ - pip install maxapi-python aiogram==3.22.0
import asyncio # Для асинхронности
import aiohttp # Для асинхронных реквестов
from io import BytesIO # Для хранения ответов файлом в RAM
from aiogram import Bot, Dispatcher, types # Для ТГ

# Импорты библиотеки PyMax
from pymax import MaxClient, Message
from pymax.types import FileAttach, PhotoAttach, VideoAttach

PHONE = "+79998887766"  # Номер телефона Max
telegram_bot_TOKEN = "token"  # Токен TG-бота

# Формат: id чата в Max: id чата в Tg
# (Id чата в Max можно узнать из ссылки на чат в веб версии web.max.ru)
chats = {
    -68690734055662: -1003177746657,
}

# Создаём зеркальный словарь для отправки из Telegram в Max
chats_telegram = {value: key for key, value in chats.items()}

max_client = MaxClient(phone=PHONE, work_dir="cache", reconnect=True) # Инициализация клиента Max

telegram_bot = Bot(token=telegram_bot_TOKEN) # Инициализация TG-бота
dp = Dispatcher()

async def download_file_bytes(url: str) -> BytesIO:
    """Загружает файл по URL и возвращает его в виде BytesIO."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status() # Кидаем exception в случае ошибки HTTP
            file_bytes = BytesIO(await response.read()) # Читаем ответ в файлоподобный объект
            file_bytes.name = response.headers.get("X-File-Name") # Ставим "файлу" имя из заголовков ответа
            return file_bytes

# Обработчик входящих сообщений MAX
@max_client.on_message()
async def handle_message(message: Message) -> None:
    try:
        tg_id = chats[message.chat_id]  # pyright: ignore[reportArgumentType]
    except KeyError:
        return

    sender = await max_client.get_user(user_id=message.sender) # pyright: ignore[reportArgumentType]

    if message.attaches: # Проверка на наличие вложений
        for attach in message.attaches: # Перебор всех вложений
            if isinstance(attach, VideoAttach): # Проверка на видео
                try:
                    # Получаем видео из max по айди
                    video = await max_client.get_video_by_id(
                        chat_id=message.chat_id, # pyright: ignore[reportArgumentType]
                        message_id=message.id,
                        video_id=attach.video_id
                    )
                        
                    # Загружаем видео по URL
                    video_bytes = await download_file_bytes(video.url) # pyright: ignore[reportOptionalMemberAccess]

                    # Отправляем видео через тг
                    await telegram_bot.send_video(
                        chat_id=tg_id,
                        caption=f"{sender.names[0].name}: {message.text}", # pyright: ignore[reportOptionalMemberAccess]
                        video=types.BufferedInputFile(video_bytes.getvalue(), filename=video_bytes.name)
                    )

                    video_bytes.close() # Удаляем видео из памяти

                except aiohttp.ClientError as e:
                    print(f"Ошибка при загрузке видео: {e}")
                except Exception as e:
                    print(f"Ошибка при отправке видео: {e}")

            elif isinstance(attach, PhotoAttach): # Проверка на фото
                try:
                    # Загружаем изображение по URL
                    photo_bytes = await download_file_bytes(attach.base_url) # pyright: ignore[reportOptionalMemberAccess]

                    # Отправляем фото через тг бота
                    await telegram_bot.send_photo(
                        chat_id=tg_id,
                        caption=f"{sender.names[0].name}: {message.text}", # pyright: ignore[reportOptionalMemberAccess]
                        photo=types.BufferedInputFile(photo_bytes.getvalue(), filename=photo_bytes.name)
                    )

                    photo_bytes.close() # Удаляем фото из памяти

                except aiohttp.ClientError as e:
                    print(f"Ошибка при загрузке изображения: {e}")
                except Exception as e:
                    print(f"Ошибка при отправке фото: {e}")

            elif isinstance(attach, FileAttach): # Проверка на файл
                try:
                    # Получаем файл по айди
                    file = await max_client.get_file_by_id(
                        chat_id=message.chat_id, # pyright: ignore[reportArgumentType]
                        message_id=message.id,
                        file_id=attach.file_id
                    )

                    # Загружаем файл по URL
                    file_bytes = await download_file_bytes(file.url) # pyright: ignore[reportOptionalMemberAccess]

                    # Отправляем файл через тг бота
                    await telegram_bot.send_document(
                        chat_id=tg_id,
                        caption=f"{sender.names[0].name}: {message.text}", # pyright: ignore[reportOptionalMemberAccess]
                        document=types.BufferedInputFile(file_bytes.getvalue(), filename=file_bytes.name)
                    )

                    file_bytes.close() # Удаляем файл из памяти

                except aiohttp.ClientError as e:
                    print(f"Ошибка при загрузке файла: {e}")
                except Exception as e:
                    print(f"Ошибка при отправке файла: {e}")
    else:
        await telegram_bot.send_message(
            chat_id=tg_id, 
            text=f"{sender.names[0].name}: {message.text}" # pyright: ignore[reportOptionalMemberAccess]
        )


# Обработчик запуска клиента, функция выводит все сообщения из чата "Избранное"
@max_client.on_start
async def handle_start() -> None:
    print("Клиент запущен")

    # Получение истории сообщений
    history = await max_client.fetch_history(chat_id=0)
    if history:
        for message in history:
            user = await max_client.get_user(message.sender) # pyright: ignore[reportArgumentType]
            if user:
                print(f"{user.names[0].name}: {message.text}")


# Обработчик сообщений из Telegram
@dp.message()
async def handle_tg_message(message: types.Message, bot: Bot) -> None:
    try:
        max_id = chats_telegram[message.chat.id]
        await max_client.send_message(
            chat_id=max_id,
            text=f"{message.from_user.first_name}: {message.text}", # pyright: ignore[reportOptionalMemberAccess]
        )
    except KeyError:
        return

# Раннер ботов
async def main() -> None:
    # TG-бот в фоне
    telegram_bot_task = asyncio.create_task(dp.start_polling(telegram_bot))

    try:
        await max_client.start()
    finally:
        await max_client.close()
        telegram_bot_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Программа остановлена пользователем.")
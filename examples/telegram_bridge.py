import asyncio
from pymax import MaxClient, Message, Chat, User
from pymax.types import VideoAttach, PhotoAttach, FileAttach
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
import aiohttp
from io import BytesIO

"""
Зависимости:

pip install maxapi-python==1.1.13 aiogram==3.22.0 python-dotenv

"""




"""
В .env нужно указать:

PHONE = "+7123456789"  # Твой номер для Max
BOT_TOKEN = "23456789:AAH0cJ3SNzZ2zzD0uF8HOqmxtKpwsKwggM"  # Твой токен Telegram-бота

"""

chats = { # В формате айди чата в Max: айди чата в Telegram
    -68690734055662: -1003177746657,
}


# Создаём зеркальный массив для отправки из Telegram в Max
chats_telegram = {value: key for key, value in chats.items()}


# Загружаем .env
load_dotenv(override=True)


# Настройки из .env
PHONE = os.getenv("PHONE") # Номер телефона Max
telegram_bot_TOKEN = os.getenv("BOT_TOKEN") # Токен TG-бота


client = MaxClient(phone=PHONE, work_dir="cache")


# Инициализация TG-бота
telegram_bot = Bot(token=telegram_bot_TOKEN)
dp = Dispatcher()



# Обработчик входящих сообщений MAX
@client.on_message()
async def handle_message(message: Message) -> None:

    tg_id = chats[message.chat_id]

    sender = await client.get_user(user_id=message.sender)

    if message.attaches:
        for attach in message.attaches:

            # Проверка на видео
            if isinstance(attach, VideoAttach):
                async with aiohttp.ClientSession() as session:
                    try:
                        # Получаем видео по айди
                        video = await client.get_video_by_id(
                            chat_id=message.chat_id,
                            message_id=message.id,
                            video_id=attach.video_id
                            )


                        # Загружаем видео по URL
                        async with session.get(video.url) as response:
                            response.raise_for_status()  # Проверка на ошибки HTTP
                            video_bytes = BytesIO(await response.read())
                            video_bytes.name = response.headers.get("X-File-Name")

                        # Отправляем видео через телеграм бота
                        await telegram_bot.send_video(
                            chat_id=tg_id,
                            caption=f"{sender.names[0].name}: {message.text}",
                            video=types.BufferedInputFile(video_bytes.getvalue(), filename=video_bytes.name)
                        )

                        # Очищаем память
                        video_bytes.close()

                    except aiohttp.ClientError as e:
                        print(f"Ошибка при загрузке видео: {e}")
                    except Exception as e:
                        print(f"Ошибка при отправке видео: {e}")

            # Проверка на изображение
            elif isinstance(attach, PhotoAttach):
                async with aiohttp.ClientSession() as session:
                    try:
                        # Загружаем изображение по URL
                        async with session.get(attach.base_url) as response:
                            response.raise_for_status()  # Проверка на ошибки HTTP
                            photo_bytes = BytesIO(await response.read())
                            photo_bytes.name = response.headers.get("X-File-Name")

                        # Отправляем фото через телеграм бота
                        await telegram_bot.send_photo(
                            chat_id=tg_id,
                            caption=f"{sender.names[0].name}: {message.text}",
                            photo=types.BufferedInputFile(photo_bytes.getvalue(), filename=photo_bytes.name)
                        )

                        # Очищаем память
                        photo_bytes.close()

                    except aiohttp.ClientError as e:
                        print(f"Ошибка при загрузке изображения: {e}")
                    except Exception as e:
                        print(f"Ошибка при отправке фото: {e}")
                        
            # Проверка на файл
            elif isinstance(attach, FileAttach):
                async with aiohttp.ClientSession() as session:
                    try:
                        # Получаем файл по айди
                        file = await client.get_file_by_id(
                            chat_id=message.chat_id,
                            message_id=message.id,
                            file_id=attach.file_id
                            )

                        # Загружаем файл по URL
                        async with session.get(file.url) as response:
                            response.raise_for_status()  # Проверка на ошибки HTTP
                            file_bytes = BytesIO(await response.read())
                            file_bytes.name = response.headers.get("X-File-Name")

                        # Отправляем файл через телеграм бота
                        await telegram_bot.send_document(
                            chat_id=tg_id,
                            caption=f"{sender.names[0].name}: {message.text}",
                            document=types.BufferedInputFile(file_bytes.getvalue(), filename=file_bytes.name)
                        )

                        # Очищаем память
                        file_bytes.close()

                    except aiohttp.ClientError as e:
                        print(f"Ошибка при загрузке файла: {e}")
                    except Exception as e:
                        print(f"Ошибка при отправке файла: {e}")
    else:
        await telegram_bot.send_message(
            chat_id=tg_id,
            text=f"{sender.names[0].name}: {message.text}"
        )


# Обработчик запуска клиента, функция выводит все сообщения из чата "Избранное"
@client.on_start
async def handle_start() -> None:
    print("Клиент запущен")
    
    # Получение истории сообщений
    history = await client.fetch_history(chat_id=0)
    if history:
        for message in history:
            user = await client.get_user(message.sender)
            if user:
                print(f"{user.names[0].name}: {message.text}")


# Обработчик сообщений Telegram
@dp.message()
async def handle_message(message: types.Message, bot: Bot) -> None:
    max_id = chats_telegram[message.chat.id]
    await client.send_message(chat_id=max_id, text=message.text, notify=True)


# Раннер ботов
async def main() -> None:
    # TG-бот в фоне
    telegram_bot_task = asyncio.create_task(dp.start_polling(telegram_bot))

    try:
        while True: # Не спрашивайте 😃
            await client.start()

    finally:
        await client.close()
        telegram_bot_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Программа остановлена пользователем.")
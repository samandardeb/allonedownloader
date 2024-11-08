import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
import yt_dlp



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TELEGRAM_BOT_TOKEN = '7460633845:AAGfA3olX55jgenyDZX23HgQlE6RfL-ChIk'


bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)


async def download_media(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply(
        "Assalomu Alaykum! Bizni botni tanlaganingiz uchun tashakkur! Endi (YouTube, Instagram, Twitter) "
        "platformalaridan 'ссылка' yuboring"
    )

# Handler for receiving links
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_message(message: types.Message):
    url = message.text
    await message.reply("Sizning faylingiz yuklanmoqda, iltimos kuting...")

    try:
        # Download the media
        file_path = await download_media(url)
        # Send the file to the user
        with open(file_path, 'rb') as file:
            await message.answer_document(file)
        # Clean up the file after sending
        os.remove(file_path)
    except Exception as e:
        await message.reply(f"Error downloading media: {e}")
        logger.error(f"Error downloading media: {e}")

# Error handler
@dp.errors_handler()
async def handle_errors(update, exception):
    logger.warning(f"Update {update} caused error {exception}")
    return True

if __name__ == '__main__':
    # Ensure a "downloads" folder exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    # Start polling
    executor.start_polling(dp, skip_updates=True)

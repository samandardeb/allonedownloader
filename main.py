import logging
import os
import uuid
import yt_dlp
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your bot token
TELEGRAM_BOT_TOKEN = '7460633845:AAGfA3olX55jgenyDZX23HgQlE6RfL-ChIk'

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

# User preferences storage
user_languages = {}
user_platforms = {}
user_music_results = {}
user_current_indexes = {}

# Directory for downloads
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


def is_valid_url(url):
    """Validate if the URL belongs to supported platforms."""
    platforms = ["instagram.com", "tiktok.com", "youtube.com", "twitter.com", "pinterest.com"]
    return any(platform in url for platform in platforms)


async def download_media(url):
    """Download media using yt_dlp and return the file path."""
    unique_id = uuid.uuid4()  # Generate unique ID for each file

    if "pinterest.com" in url:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/Pinterest_{unique_id}.%(ext)s",
            "quiet": True,
        }
    else:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s_{unique_id}.%(ext)s",
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


def search_music(query, limit=5):
    """Search for music using the iTunes API."""
    base_url = "https://itunes.apple.com/search"
    params = {"term": query, "media": "music", "limit": limit}
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []


async def download_music(preview_url, track_name):
    """Download music preview and return the file path."""
    file_path = f"{DOWNLOAD_DIR}/{track_name}.mp3"
    response = requests.get(preview_url)
    with open(file_path, "wb") as file:
        file.write(response.content)
    return file_path


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    """Handle the /start command."""
    language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    language_keyboard.add(
        KeyboardButton("🇺🇿 Uzbek"),
        KeyboardButton("🇷🇺 Russian"),
        KeyboardButton("🇬🇧 English"),
    )
    await message.reply(
        "Tilni tanlang | Выберите язык | Choose a language:",
        reply_markup=language_keyboard,
    )


@dp.message_handler(lambda message: message.text in ["🇺🇿 Uzbek", "🇷🇺 Russian", "🇬🇧 English"])
async def set_language(message: types.Message):
    """Set user language and prompt for platform selection."""
    selected_language = message.text

    if selected_language == "🇺🇿 Uzbek":
        user_languages[message.from_user.id] = "uz"
        await message.reply("Til tanlandi: O'zbek 🇺🇿. Endi platformani tanlang.")
    elif selected_language == "🇷🇺 Russian":
        user_languages[message.from_user.id] = "ru"
        await message.reply("Язык выбран: Русский 🇷🇺. Теперь выберите платформу.")
    elif selected_language == "🇬🇧 English":
        user_languages[message.from_user.id] = "en"
        await message.reply("Language selected: English 🇬🇧. Now choose a platform.")

    platform_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    platform_keyboard.add(
        KeyboardButton("📸 Instagram"),
        KeyboardButton("🎵 TikTok"),
        KeyboardButton("📹 YouTube"),
        KeyboardButton("🐦 Twitter"),
        KeyboardButton("📌 Pinterest"),
        KeyboardButton("🎧 MP3 Platform"),
    )
    await message.reply("Select a platform:", reply_markup=platform_keyboard)


@dp.message_handler(lambda message: message.text == "🎧 MP3 Platform")
async def mp3_search_prompt(message: types.Message):
    """Prompt user to enter a music search query."""
    language = user_languages.get(message.from_user.id, "en")
    messages = {
        "uz": "Qaysi musiqani qidiryapsiz? Qidiruv so'zini kiriting.",
        "ru": "Какую музыку вы ищете? Введите запрос.",
        "en": "What music are you looking for? Enter a search query.",
    }
    await message.reply(messages[language])


@dp.message_handler(lambda message: message.text not in ["📸 Instagram", "🎵 TikTok", "📹 YouTube", "🐦 Twitter", "📌 Pinterest", "🎧 MP3 Platform"])
async def handle_music_search(message: types.Message):
    """Handle music search queries and display results."""
    query = message.text
    search_results = search_music(query)

    if not search_results:
        await message.reply("No results found. Please try a different query.")
        return

    user_music_results[message.from_user.id] = search_results
    user_current_indexes[message.from_user.id] = 0

    await display_music_results(message.chat.id, message.from_user.id)


async def display_music_results(chat_id, user_id):
    """Display music results with navigation buttons."""
    current_index = user_current_indexes.get(user_id, 0)
    music_results = user_music_results.get(user_id, [])

    if current_index >= len(music_results):
        await bot.send_message(chat_id, "No more results.")
        return

    track = music_results[current_index]
    track_name = track.get("trackName", "Unknown")
    artist_name = track.get("artistName", "Unknown")
    preview_url = track.get("previewUrl", "N/A")

    buttons = InlineKeyboardMarkup()
    buttons.add(
        InlineKeyboardButton("🎵 Download", callback_data=f"download_{current_index}"),
        InlineKeyboardButton("➡️ Next", callback_data="next"),
    )
    buttons.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel"))

    await bot.send_message(
        chat_id,
        f"🎵 *{track_name}* by {artist_name}\nPreview: [Listen]({preview_url})",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=buttons,
    )


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith("download_"))
async def handle_download(callback_query: types.CallbackQuery):
    """Handle music download."""
    user_id = callback_query.from_user.id
    index = int(callback_query.data.split("_")[1])
    music_results = user_music_results.get(user_id, [])

    if index >= len(music_results):
        await bot.answer_callback_query(callback_query.id, text="Invalid selection.")
        return

    track = music_results[index]
    track_name = track.get("trackName", "Unknown")
    preview_url = track.get("previewUrl", None)

    if not preview_url:
        await bot.answer_callback_query(callback_query.id, text="No preview available.")
        return

    await bot.answer_callback_query(callback_query.id, text="Downloading...")
    file_path = await download_music(preview_url, track_name)

    await bot.send_audio(callback_query.from_user.id, audio=open(file_path, "rb"), title=track_name)
    os.remove(file_path)


@dp.callback_query_handler(lambda callback_query: callback_query.data == "next")
async def handle_next(callback_query: types.CallbackQuery):
    """Show the next music result."""
    user_id = callback_query.from_user.id
    user_current_indexes[user_id] += 1
    await display_music_results(callback_query.from_user.id, user_id)


@dp.callback_query_handler(lambda callback_query: callback_query.data == "cancel")
async def handle_cancel(callback_query: types.CallbackQuery):
    """Cancel the music search."""
    await bot.answer_callback_query(callback_query.id, text="Search canceled.")
    user_music_results.pop(callback_query.from_user.id, None)
    user_current_indexes.pop(callback_query.from_user.id, None)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

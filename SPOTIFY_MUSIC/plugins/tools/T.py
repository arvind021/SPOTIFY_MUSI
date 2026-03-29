import os
import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from py_yt import VideosSearch

from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# 🔍 SONG SEARCH COMMAND
@app.on_message(filters.command("song") & ~BANNED_USERS)
async def song_search(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /song song name")

    query = " ".join(message.command[1:])
    search = VideosSearch(query, limit=10)
    results = (await search.next())["result"]

    buttons = []
    for i, r in enumerate(results):
        title = r["title"][:40]
        vid = r["id"]

        buttons.append(
            [InlineKeyboardButton(f"{i+1}. {title}", callback_data=f"song_{vid}")]
        )

    await message.reply(
        "🎵 **Select a song:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# 🎯 CALLBACK HANDLER
@app.on_callback_query(filters.regex("^song_"))
async def song_download(client, query: CallbackQuery):
    vid = query.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={vid}"
    file_path = f"{DOWNLOAD_DIR}/{vid}.mp3"

    await query.answer("⏳ Processing...")

    # ✅ 1. Check local file
    if os.path.exists(file_path):
        return await send_song(client, query.message, file_path, vid)

    # ✅ 2. API CALL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.BASE_URL}/api/song?query={vid}&download=true&api={config.API_KEY}"
            ) as resp:
                data = await resp.json()

        stream = data.get("stream")

        if not stream:
            return await query.message.reply("❌ Download failed")

        # ✅ 3. Download file
        async with aiohttp.ClientSession() as session:
            async with session.get(stream) as r:
                if r.status == 200:
                    with open(file_path, "wb") as f:
                        f.write(await r.read())

    except Exception as e:
        return await query.message.reply(f"❌ Error: {e}")

    # ✅ 4. Send file
    await send_song(client, query.message, file_path, vid)


# 📤 SEND SONG FUNCTION
async def send_song(client, message, file_path, vid):
    # 🎯 Get real title
    try:
        search = VideosSearch(vid, limit=1)
        data = (await search.next())["result"][0]
        title = data["title"]
    except:
        title = f"Song - {vid}"

    await message.reply_audio(
        audio=file_path,
        performer="BabiesIQ",   # ✅ Performer name
        title=title             # ✅ Song title
    )

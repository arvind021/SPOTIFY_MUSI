import os
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from py_yt import VideosSearch

from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# 🔍 SONG SEARCH
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


# 🎯 CALLBACK
@app.on_callback_query(filters.regex("^song_"))
async def song_download(client, query: CallbackQuery):
    vid = query.data.split("_")[1]
    file_path = f"{DOWNLOAD_DIR}/{vid}.mp3"

    await query.answer("⏳ Processing...")

    # ✅ DEBUG
    print(f"[DEBUG] VID: {vid}")
    print(f"[DEBUG] FILE PATH: {file_path}")

    # ✅ 1. Local check
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        print("[DEBUG] Using cached file")
        return await send_song(query.message, file_path, vid)

    # ✅ 2. API direct download (CURL)
    try:
        url = f"{config.BASE_URL}/api/song?query={vid}&download=true&api={config.API_KEY}"

        print(f"[DEBUG] CURL URL: {url}")

        cmd = f'curl -L "{url}" -o "{file_path}"'
        proc = await asyncio.create_subprocess_shell(cmd)
        await proc.communicate()

        # verify file
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return await query.message.reply("❌ Download failed (empty file)")

    except Exception as e:
        return await query.message.reply(f"❌ Error: {e}")

    # ✅ 3. Send
    await send_song(query.message, file_path, vid)


# 📤 SEND SONG
async def send_song(message, file_path, vid):
    print(f"[DEBUG] Sending file: {file_path}")

    # 🎯 Title fetch
    try:
        search = VideosSearch(vid, limit=1)
        data = (await search.next())["result"][0]
        title = data["title"]
    except:
        title = f"Song - {vid}"

    # ✅ IMPORTANT FIX
    with open(file_path, "rb") as audio_file:
        await message.reply_audio(
            audio=audio_file,   # 🔥 FIXED
            performer="BabiesIQ",
            title=title,
            caption=f"{title}\n\n⚡ Powered by @BabiesIQ"
        )

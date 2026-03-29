import os
import asyncio
import aiohttp
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
        "🎵 Select a song:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# 🎯 CALLBACK
@app.on_callback_query(filters.regex("^song_"))
async def song_download(client, query: CallbackQuery):
    vid = query.data.split("_")[1]
    file_path = f"{DOWNLOAD_DIR}/{vid}.mp3"

    await query.answer("⏳ Processing...")

    # ✅ cache check
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return await send_song(query.message, file_path, vid)

    try:
        async with aiohttp.ClientSession() as session:

            # ✅ STEP 1: API call
            api_url = f"{config.BASE_URL}/api/song?query={vid}&download=true&api={config.API_KEY}"
            async with session.get(api_url) as resp:
                res = await resp.json()

            stream = res.get("stream")
            media_type = res.get("type")

            if not stream:
                return await query.message.reply("❌ Stream not found")

            print(f"[DEBUG] STREAM: {stream}")

            # ✅ STEP 2: WAIT until ready
            wait_time = 60  # total attempts

            for i in range(wait_time):
                async with session.get(stream) as r:
                    print(f"[DEBUG] Attempt {i+1} → Status: {r.status}")

                    if r.status == 200:
                        print("[DEBUG] Stream ready ✅")
                        break

                    if r.status in (423, 404, 410):
                        await asyncio.sleep(2)
                        continue

                    if r.status in (401, 403, 429):
                        txt = await r.text()
                        return await query.message.reply(
                            f"❌ Blocked {r.status}"
                        )

                    return await query.message.reply(f"❌ Failed {r.status}")
            else:
                return await query.message.reply("❌ Processing timeout")

        # ✅ STEP 3: DOWNLOAD AFTER READY
        cmd = f'curl -L "{stream}" -o "{file_path}"'
        proc = await asyncio.create_subprocess_shell(cmd)
        await proc.communicate()

        # verify
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return await query.message.reply("❌ Download failed")

    except Exception as e:
        return await query.message.reply(f"❌ Error: {e}")

    # ✅ SEND
    await send_song(query.message, file_path, vid)


# 📤 SEND SONG
async def send_song(message, file_path, vid):
    try:
        search = VideosSearch(vid, limit=1)
        data = (await search.next())["result"][0]
        title = data["title"]
    except:
        title = f"Song - {vid}"

    with open(file_path, "rb") as audio_file:
        await message.reply_audio(
            audio=audio_file,
            performer="BabiesIQ",
            title=title
        )

import os
import asyncio
import aiohttp

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from py_yt import VideosSearch
from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS

D = "downloads"
os.makedirs(D, exist_ok=True)


# --- DEBUG: ALL MESSAGES ---
@app.on_message(filters.all & filters.private, group=1)
async def debug_all(_, m: Message):
    print(f"[DEBUG MSG] {m.chat.id} | {m.from_user.id} | {m.text or m.command}")


# --- DEBUG: ALL CALLBACKS ---
@app.on_callback_query()
async def debug_cb(_, q: CallbackQuery):
    print(f"[DEBUG CB] {q.message.chat.id} | {q.message.message_id} | {q.data}")
    await q.answer("Debug: callback received")


@app.on_message(filters.command("song") & ~BANNED_USERS, group=10)
async def s(_, m: Message):
    print(f"[DEBUG] /song command triggered: {m.text}")
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /song song name")

    try:
        r = (await VideosSearch(" ".join(m.command[1:]), limit=10).next())["result"]
    except Exception as e:
        print(f"[DEBUG] VideosSearch failed: {e}")
        return await m.reply("❌ Search failed.")

    b = [
        [InlineKeyboardButton(
            f"{i+1}. {x['title'][:40]}",
            callback_data=f"song_{x['id']}"
        )]
        for i, x in enumerate(r)
    ]
    txt = f"🎧 {m.from_user.mention}\n\n✨ Here is your song list\nTap below to download & enjoy smooth offline vibes 💫"
    await m.reply(
        txt,
        reply_markup=InlineKeyboardMarkup(b)
    )


@app.on_callback_query(filters.regex("^song_"))
async def d(_, q: CallbackQuery):
    print(f"[DEBUG] Callback: {q.data}")
    await q.answer("⏳ Processing...")

    try:
        await q.message.delete()
    except Exception as e:
        print(f"[DEBUG] Failed to delete: {e}")

    v = q.data.split("_")[1]
    p = f"{D}/{v}.mp3"

    # Check if file already exists and is big enough
    if os.path.exists(p) and os.path.getsize(p) > 50_000:
        return await f(q.message, p, v)

    try:
        async with aiohttp.ClientSession() as s:
            url = f"{config.BASE_URL}/api/song?query={v}&download=true&api={config.API_KEY}"
            print(f"[DEBUG] Fetching: {url}")
            async with s.get(url) as r:
                res = await r.json()
            print(f"[DEBUG] API response: {res}")
            u = res.get("stream")
            if not u:
                return await q.message.reply("❌ Stream not found")

            for _ in range(60):
                async with s.get(u) as r:
                    print(f"[DEBUG] Stream HEAD: {r.status}")
                    if r.status == 200:
                        break
                    if r.status in (423, 404, 410):
                        await asyncio.sleep(2)
                        continue
                    if r.status in (401, 403, 429):
                        return await q.message.reply(f"❌ Blocked {r.status}")
                    return await q.message.reply(f"❌ Failed {r.status}")
            else:
                return await q.message.reply("🚫 Server Busy, Try Again Later")

        cmd = f'curl -L "{u}" -o "{p}" --max-time 120'
        proc = await asyncio.create_subprocess_shell(cmd)
        print(f"[DEBUG] Running cmd: {cmd}")
        await proc.communicate()
        if proc.returncode != 0:
            return await q.message.reply("❌ Download process failed")

        if not os.path.exists(p) or os.path.getsize(p) < 50_000:
            return await q.message.reply("❌ Download failed")

    except Exception as e:
        print(f"[DEBUG] Download/Proc error: {e}")
        return await q.message.reply(f"❌ {str(e)[:100]}")

    await f(q.message, p, v)


async def f(m: Message, p: str, v: str):
    try:
        t = (await VideosSearch(v, limit=1).next())["result"][0]["title"]
    except Exception as e1:
        print(f"[DEBUG] VideosSearch title failed: {e1}")
        t = f"Song - {v}"

    caption = f"🎵 **{t[:90]}**\n\n💫 **BabiesIQ Music Bot**"

    try:
        with open(p, "rb") as audio:
            msg = await m.reply_audio(
                audio=audio,
                caption=caption,
                title=t[:70],
                performer="BabiesIQ"
            )
        await msg.delete()  # audio ke baad delete
        if os.path.exists(p):
            os.remove(p)
        print("[DEBUG] Audio sent & deleted.")
    except Exception as e:
        print(f"[DEBUG] Audio send failed: {e}")
        await m.reply("❌ Audio send failed. Check file size/permissions.")
        if os.path.exists(p):
            os.remove(p)

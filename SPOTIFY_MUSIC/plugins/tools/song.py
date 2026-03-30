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


# --- DEBUG: SAB MESSAGES HOOK ---
@app.on_message(filters.all, group=1)
async def debug_all_msgs(_, m: Message):
    chat_type = m.chat.type
    usr = m.from_user
    print(f"[DEBUG MSG] {usr.id} | {chat_type} | {m.chat.id} | {m.text or m.command}")


# --- DEBUG: SAB CALLBACKS HOOK (fallback + regex dono) ---
@app.on_callback_query(~filters.regex("^song_"), group=2)
async def debug_cb_catchall_non_song(_, q: CallbackQuery):
    print(f"[DEBUG CB ALL] NOT song_: {q.data}")
    await q.answer("DEBUG: non-song callback")


@app.on_callback_query(filters.regex("^song_"), group=2)
async def debug_cb_song(_, q: CallbackQuery):
    print(f"[DEBUG CB SONG] {q.data}")
    await q.answer("📡 Callback: parsing...")  # confirm callback hit


@app.on_message(filters.command("song") & ~BANNED_USERS, group=10)
async def s(_, m: Message):
    print(f"[DEBUG /song] {m.chat.id} | {m.text}")
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /song song name")

    try:
        r = (await VideosSearch(" ".join(m.command[1:]), limit=10).next())["result"]
    except Exception as e:
        print(f"[DEBUG] VideosSearch failed: {e}")
        return await m.reply("❌ Search failed.")

    # Force clean callback_data: start with "song_"
    b = [
        [InlineKeyboardButton(
            f"{i+1}. {x['title'][:40]}",
            callback_data=f"song_{x['id']}"  # MUST start with "song_"
        )]
        for i, x in enumerate(r)
    ]

    txt = f"🎧 {m.from_user.mention}\n\n✨ Here is your song list\nTap below to download & enjoy smooth offline vibes 💫"
    await m.reply(
        txt,
        reply_markup=InlineKeyboardMarkup(b)
    )


# --- KAAM KARNE WALA CALLBACK HANDLER (with debug) ---
@app.on_callback_query(filters.regex("^song_"), group=3)
async def d(_, q: CallbackQuery):
    print(f"[DEBUG] ENTERING d(): {q.data}")
    v = q.data.split("_")[1]
    p = f"{D}/{v}.mp3"

    await q.answer("⏳ Processing...")

    try:
        await q.message.delete()
    except Exception as e2:
        print(f"[DEBUG] Failed to delete query msg: {e2}")

    # Check if already downloaded
    if os.path.exists(p) and os.path.getsize(p) > 50_000:
        print(f"[DEBUG] Using cached: {p}")
        return await f(q.message, p, v)

    # --- DOWNLOAD PHASE ---
    try:
        url = f"{config.BASE_URL}/api/song?query={v}&download=true&api={config.API_KEY}"
        print(f"[DEBUG] API URL: {url}")

        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                res = await r.json()
            print(f"[DEBUG] API res keys: {list(res.keys())}")
            u = res.get("stream")
            if not u:
                return await q.message.reply("❌ Stream not found")

            for _ in range(60):
                async with s.get(u, timeout=10) as r:
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
        print(f"[DEBUG] CMD: {cmd}")
        proc = await asyncio.create_subprocess_shell(cmd)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"[DEBUG] curl failed: {stdout} | {stderr}")
            return await q.message.reply("❌ Download process failed")

        if not os.path.exists(p) or os.path.getsize(p) < 50_000:
            print(f"[DEBUG] File missing or tiny: {p} {os.path.getsize(p) if os.path.exists(p) else 0}")
            return await q.message.reply("❌ Download failed")

    except Exception as e:
        print(f"[DEBUG] DOWNLOAD ERROR: {e}")
        return await q.message.reply(f"❌ {str(e)[:100]}")

    # --- SEND AUDIO + DELETE MESSAGE ---
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
        await msg.delete()
        if os.path.exists(p):
            os.remove(p)
        print("[DEBUG] Audio sent & delete done.")
    except Exception as e:
        print(f"[DEBUG] Audio send failed: {e}")
        await m.reply("❌ Audio send failed. Check file size/permissions/timeout.")
        if os.path.exists(p):
            os.remove(p)

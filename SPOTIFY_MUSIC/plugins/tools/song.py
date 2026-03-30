import os,asyncio,aiohttp,time,io
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery,Message
from py_yt import VideosSearch
from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS
from SPOTIFY_MUSIC.utils.thumbnails import get_thumb

D="downloads";os.makedirs(D,exist_ok=True)

def kb(r,p):
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"{i+1}. {x['title'][:40]}",callback_data=f"{p}_{x['id']}")] for i,x in enumerate(r)])

@app.on_message(filters.command("song")&~BANNED_USERS,group=5)
async def song(_,m:Message):
    if len(m.command)<2:return await m.reply("❌ Usage: /song name")
    r=(await VideosSearch(" ".join(m.command[1:]),limit=10).next())["result"]
    await m.reply(f"🎧 {m.from_user.mention}\n\n✨ Select song\nSmooth offline vibes 💫",reply_markup=kb(r,"song"))

@app.on_message(filters.command("video")&~BANNED_USERS,group=5)
async def video(_,m:Message):
    if len(m.command)<2:return await m.reply("❌ Usage: /video name")
    r=(await VideosSearch(" ".join(m.command[1:]),limit=10).next())["result"]
    await m.reply(f"🎬 {m.from_user.mention}\n\n✨ Select video\nTap to download ⚡",reply_markup=kb(r,"video"))

@app.on_callback_query(filters.regex("^(song|video)_"),group=5)
async def dl(c,q:CallbackQuery):
    typ,vid=q.data.split("_")
    ext="mp3" if typ=="song" else "mp4"
    p=f"{D}/{vid}.{ext}"
    await q.answer()

    start=time.time()
    stop=False
    percent=0

    async def anim():
        nonlocal percent
        while not stop:
            try:
                elapsed=time.time()-start
                speed=min(4,1+elapsed/4)
                percent=min(95,int(percent+speed))
                bar="▰"*(percent//10)+"▱"*(10-(percent//10))
                await q.message.edit(f"⏳ Downloading {typ}...\n\n{bar} {percent}%")
            except:pass
            await asyncio.sleep(0.35)

    asyncio.create_task(anim())

    if os.path.exists(p)and os.path.getsize(p)>0:
        stop=True
        return await send(c,q.message,p,vid,typ)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{config.BASE_URL}/api/{typ}?query={vid}&download=true&api={config.API_KEY}") as r:
                res=await r.json()
            u=res.get("stream")
            if not u:
                stop=True
                return await q.message.edit("❌ Stream not found")

            for _ in range(60):
                async with s.get(u) as r:
                    if r.status==200:break
                    if r.status in (423,404,410):await asyncio.sleep(2);continue
                    if r.status in (401,403,429):
                        stop=True
                        return await q.message.edit(f"❌ Blocked {r.status}")
                    stop=True
                    return await q.message.edit(f"❌ Failed {r.status}")
            else:
                stop=True
                return await q.message.edit("🚫 Server Busy, Try Again Later")

        proc=await asyncio.create_subprocess_shell(f'curl -L "{u}" -o "{p}" --max-time 120')
        await proc.communicate()

        if not os.path.exists(p)or os.path.getsize(p)<50000:
            stop=True
            return await q.message.edit("❌ Download failed")

    except Exception as e:
        stop=True
        return await q.message.edit(f"❌ {str(e)[:80]}")

    percent=100
    stop=True
    await asyncio.sleep(0.6)

    await send(c,q.message,p,vid,typ)

async def send(c,m,p,vid,typ):
    try:t=(await VideosSearch(vid,limit=1).next())["result"][0]["title"]
    except:t=f"{typ} - {vid}"

    try:await m.edit("📤 Uploading...\n\n▰▰▰▰▰▰▰▰▰▰ 100%")
    except:pass

    await asyncio.sleep(0.4)

    thumb_url=get_thumb(vid)

    thumb_bytes=None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(thumb_url) as r:
                if r.status==200:
                    thumb_bytes=io.BytesIO(await r.read())
                    thumb_bytes.name="thumb.jpg"
    except:pass

    try:await m.delete()
    except:pass

    with open(p,"rb") as f:
        if typ=="song":
            await c.send_audio(
                m.chat.id,
                f,
                performer="BabiesIQ",
                title=t,
                thumb=thumb_bytes
            )
        else:
            await c.send_video(
                m.chat.id,
                f,
                caption=f"🎬 {t}",
                thumb=thumb_bytes
            )

    if os.path.exists(p):os.remove(p)

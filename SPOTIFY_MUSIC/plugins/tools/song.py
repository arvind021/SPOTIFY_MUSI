import os,asyncio,aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery,Message
from py_yt import VideosSearch
from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS

D="downloads";os.makedirs(D,exist_ok=True)

# 🔄 animation frames
FRAMES=["▱▱▱▱▱","▰▱▱▱▱","▰▰▱▱▱","▰▰▰▱▱","▰▰▰▰▱","▰▰▰▰▰"]

@app.on_message(filters.command("song")&~BANNED_USERS)
async def s(_,m:Message):
    if len(m.command)<2:return await m.reply("❌ Usage: /song song name")
    r=(await VideosSearch(" ".join(m.command[1:]),limit=10).next())["result"]
    b=[[InlineKeyboardButton(f"{i+1}. {x['title'][:40]}",callback_data=f"song_{x['id']}")] for i,x in enumerate(r)]
    txt=f"🎧 {m.from_user.mention}\n\n✨ Here is your song list\nTap below to download & enjoy smooth offline vibes 💫"
    await m.reply(txt,reply_markup=InlineKeyboardMarkup(b))

@app.on_callback_query(filters.regex("^song_"))
async def d(c,q:CallbackQuery):
    v=q.data.split("_")[1];p=f"{D}/{v}.mp3"
    await q.answer()

    # 🔥 start animation task
    stop=False
    async def anim():
        i=0
        while not stop:
            try:
                bar=FRAMES[i%len(FRAMES)]
                await q.message.edit(f"⏳ Downloading...\n\n{bar}")
                i+=1
            except:pass
            await asyncio.sleep(0.7)

    task=asyncio.create_task(anim())

    if os.path.exists(p)and os.path.getsize(p)>0:
        stop=True
        await asyncio.sleep(1)
        return await send(c,q.message,p,v)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{config.BASE_URL}/api/song?query={v}&download=true&api={config.API_KEY}") as r:
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

    stop=True
    await asyncio.sleep(1)
    await send(c,q.message,p,v)

async def send(c,m,p,v):
    try:t=(await VideosSearch(v,limit=1).next())["result"][0]["title"]
    except:t=f"Song - {v}"

    try:await m.delete()
    except:pass

    with open(p,"rb") as a:
        await c.send_audio(
            m.chat.id,
            a,
            performer="BabiesIQ",
            title=t
        )

    if os.path.exists(p):os.remove(p)

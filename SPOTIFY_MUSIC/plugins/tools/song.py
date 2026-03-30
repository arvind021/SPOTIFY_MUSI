import os,asyncio,aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery,Message
from py_yt import VideosSearch
from SPOTIFY_MUSIC import app
import config
from config import BANNED_USERS

D="downloads";os.makedirs(D,exist_ok=True)

@app.on_message(filters.command(["song"])&~BANNED_USERS)
async def s(c,m:Message):
    if not m.text:return
    if len(m.command)<2:return await m.reply("❌ Usage: /song song name")
    try:
        r=(await VideosSearch(" ".join(m.command[1:]),limit=10).next())["result"]
    except:
        return await m.reply("❌ Search failed")
    if not r:return await m.reply("❌ No results found")
    b=[[InlineKeyboardButton(f"{i+1}. {x['title'][:40]}",callback_data=f"song_{x['id']}")] for i,x in enumerate(r)]
    txt=f"🎧 {m.from_user.mention}\n\n✨ Here is your song list\nTap below to download & enjoy smooth offline vibes 💫"
    await m.reply(txt,reply_markup=InlineKeyboardMarkup(b))

@app.on_callback_query(filters.regex("^song_"))
async def d(c,q:CallbackQuery):
    v=q.data.split("_")[1];p=f"{D}/{v}.mp3";cid=q.message.chat.id
    await q.answer("⏳ Processing...")
    try:await q.message.delete()
    except:pass

    if os.path.exists(p)and os.path.getsize(p)>0:
        return await f(c,cid,p,v)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{config.BASE_URL}/api/song?query={v}&api={config.API_KEY}") as r:
                if r.status!=200:return await c.send_message(cid,"❌ API Error")
                res=await r.json()

            u=res.get("stream")
            if not u:return await c.send_message(cid,"❌ Stream not found")

            for _ in range(60):
                try:
                    async with s.get(u) as r:
                        if r.status==200:break
                        if r.status in (423,404,410):await asyncio.sleep(2);continue
                        if r.status in (401,403,429):return await c.send_message(cid,f"❌ Blocked {r.status}")
                        return await c.send_message(cid,f"❌ Failed {r.status}")
                except:
                    await asyncio.sleep(2)
            else:
                return await c.send_message(cid,"🚫 Server Busy, Try Again Later")

        proc=await asyncio.create_subprocess_shell(f'curl -L "{u}" -o "{p}"')
        await proc.communicate()

        if not os.path.exists(p)or os.path.getsize(p)==0:
            return await c.send_message(cid,"❌ Download failed")

    except Exception as e:
        return await c.send_message(cid,f"❌ {str(e)[:100]}")

    await f(c,cid,p,v)

async def f(c,cid,p,v):
    try:
        t=(await VideosSearch(v,limit=1).next())["result"][0]["title"]
    except:
        t=f"Song - {v}"
    with open(p,"rb") as a:
        await c.send_audio(cid,a,performer="BabiesIQ",title=t)

import os,asyncio,aiohttp  
from pyrogram import filters  
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery,Message  
from py_yt import VideosSearch  
from SPOTIFY_MUSIC import app  
import config  
from config import BANNED_USERS  
  
D="downloads";os.makedirs(D,exist_ok=True)  
  
@app.on_message(filters.command("song")&~BANNED_USERS)  
async def s(_,m:Message):  
    if len(m.command)<2:return await m.reply("❌ Usage: /song song name")  
    r=(await VideosSearch(" ".join(m.command[1:]),limit=10).next())["result"]  
    b=[[InlineKeyboardButton(f"{i+1}. {x['title'][:40]}",callback_data=f"song_{x['id']}")] for i,x in enumerate(r)]  
    txt=f"🎧 {m.from_user.mention}\n\n✨ Here is your song list\nTap below to download & enjoy smooth offline vibes 💫"  
    await m.reply(txt,reply_markup=InlineKeyboardMarkup(b))  
  
@app.on_callback_query(filters.regex("^song_"))  
async def d(_,q:CallbackQuery):  
    v=q.data.split("_")[1];p=f"{D}/{v}.mp3"  
    await q.answer("⏳ Processing...")  
    try:await q.message.delete()  
    except:pass  
    if os.path.exists(p)and os.path.getsize(p)>50_000:return await f(q.message,p,v)  
    try:  
        async with aiohttp.ClientSession() as s:  
            async with s.get(f"{config.BASE_URL}/api/song?query={v}&download=true&api={config.API_KEY}") as r:res=await r.json()  
            u=res.get("stream")  
            if not u:return await q.message.reply("❌ Stream not found")  
            for _ in range(60):  
                async with s.get(u) as r:  
                    if r.status==200:break  
                    if r.status in (423,404,410):await asyncio.sleep(2);continue  
                    if r.status in (401,403,429):return await q.message.reply(f"❌ Blocked {r.status}")  
                    return await q.message.reply(f"❌ Failed {r.status}")  
            else:return await q.message.reply("🚫 Server Busy, Try Again Later")  
        proc=await asyncio.create_subprocess_shell(f'curl -L "{u}" -o "{p}" --max-time 120')  
        await proc.communicate()  
        if proc.returncode != 0:return await q.message.reply("❌ Download process failed")  
        if not os.path.exists(p)or os.path.getsize(p)<50_000:return await q.message.reply("❌ Download failed")  
    except Exception as e:return await q.message.reply(f"❌ {str(e)[:100]}")  
    await f(q.message,p,v)  
  
async def f(m:Message,p:str,v:str):  
    try:  
        t=(await VideosSearch(v,limit=1).next())["result"][0]["title"]  
    except:  
        t=f"Song - {v}"  
    caption=f"🎵 **{t[:90]}**\n\n💫 **BabiesIQ Music Bot**"  
    try:  
        with open(p,"rb") as audio_file:  
            msg = await m.reply_audio(  
                audio=audio_file,  
                caption=caption,  
                title=t[:70],  
                performer="BabiesIQ"  
            )  
        await msg.delete()  # Audio message delete after sending  
        if os.path.exists(p): os.remove(p)  
    except Exception as e:  
        await m.reply(f"❌ Audio send failed: {str(e)[:50]}")  
        if os.path.exists(p): os.remove(p)

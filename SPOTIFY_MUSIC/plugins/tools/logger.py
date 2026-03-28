import asyncio
from logging import getLogger
from typing import Dict, Set
import random

from pyrogram import filters, handlers
from pyrogram.types import Message
from pyrogram.raw import functions, types
from SPOTIFY_MUSIC import app
from SPOTIFY_MUSIC.utils.database import get_assistant
from SPOTIFY_MUSIC.core.mongo import mongodb

LOGGER = getLogger(__name__)

# Databases and Memory
vcloggerdb = mongodb.vclogger
vc_logging_status: Dict[int, bool] = {}
vc_active_users: Dict[int, Set[int]] = {}

prefixes = [".", "!", "/", "@", "?", "'"]

# --- Helper Functions ---

def to_small_caps(text):
    mapping = {
        "a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ",
        "k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ","q":"ǫ","r":"ʀ","s":"s","t":"ᴛ",
        "u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ",
        "A":"ᴀ","B":"ʙ","C":"ᴄ","D":"ᴅ","E":"ᴇ","F":"ꜰ","G":"ɢ","H":"ʜ","I":"ɪ","J":"ᴊ",
        "K":"ᴋ","L":"ʟ","M":"ᴍ","N":"ɴ","O":"ᴏ","P":"ᴘ","Q":"ǫ","R":"ʀ","S":"s","T":"ᴛ",
        "U":"ᴜ","V":"ᴠ","W":"ᴡ","X":"x","Y":"ʏ","Z":"ᴢ"
    }
    return "".join(mapping.get(c,c) for c in text)

async def get_vc_status(chat_id: int) -> bool:
    if chat_id in vc_logging_status:
        return vc_logging_status[chat_id]
    doc = await vcloggerdb.find_one({"chat_id": chat_id})
    status = doc["status"] if doc else False
    vc_logging_status[chat_id] = status
    return status

# --- Core Logic: The "Smart" Part ---

@app.on_raw_update()
async def vc_update_handler(client, update, users, chats):
    """
    Ye function tabhi trigger hota hai jab Telegram VC mein koi badlav bhejta hai.
    """
    if isinstance(update, types.UpdateGroupCallParticipants):
        chat_id = -1002667870369 # Default (Actual ID niche fetch hoga)
        
        # Chat ID nikalne ke liye logic (depend karta hai update type par)
        # Note: Raw updates mein Peer mapping zaroori hoti hai.
        # Isko simple rakhne ke liye hum isse trigger point ki tarah use karenge.
        pass

# Service Message Detection (When VC Starts/Invites)
@app.on_message(filters.video_chat_started | filters.video_chat_members_invited)
async def auto_activate_vc(client, message: Message):
    chat_id = message.chat.id
    if await get_vc_status(chat_id):
        if chat_id not in vc_active_users:
            vc_active_users[chat_id] = set()
            asyncio.create_task(monitor_vc_chat(chat_id))

async def monitor_vc_chat(chat_id):
    """
    Smart Monitor: Ye tabhi chalta hai jab VC active ho.
    Agar VC khali ho jaye, to ye khud ko stop kar leta hai.
    """
    userbot = await get_assistant(chat_id)
    if not userbot:
        return

    LOGGER.info(f"Smart Monitoring started for {chat_id}")
    
    empty_count = 0
    while chat_id in vc_active_users:
        if not await get_vc_status(chat_id):
            break
            
        try:
            full_chat = await userbot.invoke(functions.channels.GetFullChannel(channel=await userbot.resolve_peer(chat_id)))
            call = full_chat.full_chat.call
            
            if not call: # VC band ho gayi
                break

            participants = await userbot.invoke(functions.phone.GetGroupParticipants(
                call=call, ids=[], sources=[], offset="", limit=100
            ))
            
            new_users = {p.peer.user_id for p in participants.participants if hasattr(p.peer, 'user_id')}
            current_users = vc_active_users.get(chat_id, set())

            # Join/Leave Logic
            joined = new_users - current_users
            left = current_users - new_users

            for u_id in joined:
                await handle_user_join(chat_id, u_id, userbot)
            for u_id in left:
                await handle_user_leave(chat_id, u_id, userbot)

            vc_active_users[chat_id] = new_users

            # Smart Stop: Agar 5 minute tak VC khali rahe to loop band kar do
            if not new_users:
                empty_count += 1
            else:
                empty_count = 0

            if empty_count > 60: # 5 minutes of inactivity
                break

        except Exception as e:
            LOGGER.error(f"Error in monitor: {e}")
            break
            
        await asyncio.sleep(5) # Optimization: Check interval

    vc_active_users.pop(chat_id, None)
    LOGGER.info(f"Smart Monitoring stopped for {chat_id}")

# --- Event Handlers (Join/Leave) ---

async def handle_user_join(chat_id, user_id, userbot):
    try:
        user = await userbot.get_users(user_id)
        name = to_small_caps(user.first_name or "Someone")
        msg = random.choice([
            f"🎤 <a href='tg://user?id={user_id}'><b>{name}</b></a> ᴊᴜsᴛ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴠᴄ! 🎶",
            f"✨ <a href='tg://user?id={user_id}'><b>{name}</b></a> ɪs ʜᴇʀᴇ ᴛᴏ ᴠɪʙᴇ! 💫"
        ])
        sent = await app.send_message(chat_id, msg)
        await asyncio.sleep(10)
        await sent.delete()
    except: pass

async def handle_user_leave(chat_id, user_id, userbot):
    try:
        user = await userbot.get_users(user_id)
        name = to_small_caps(user.first_name or "Someone")
        msg = f"👋 <a href='tg://user?id={user_id}'><b>{name}</b></a> ʟᴇғᴛ ᴛʜᴇ ᴠᴄ."
        sent = await app.send_message(chat_id, msg)
        await asyncio.sleep(10)
        await sent.delete()
    except: pass

# --- Command to Enable/Disable ---

@app.on_message(filters.command("vclogger", prefixes=prefixes) & filters.group)
async def vclogger_toggle(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply("Use: `/vclogger on` or `off`")
    
    state = message.command[1].lower() in ["on", "enable", "yes"]
    await vcloggerdb.update_one({"chat_id": chat_id}, {"$set": {"status": state}}, upsert=True)
    vc_logging_status[chat_id] = state
    
    if state:
        await message.reply("✅ VC Logger Enabled! It will activate when someone joins VC.")
        # Manual trigger check
        vc_active_users[chat_id] = set()
        asyncio.create_task(monitor_vc_chat(chat_id))
    else:
        vc_active_users.pop(chat_id, None)
        await message.reply("🚫 VC Logger Disabled.")

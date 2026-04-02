import os
import subprocess
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

from config import MONGO_DB_URI
from SPOTIFY_MUSIC import app
from SPOTIFY_MUSIC import YouTube


# ================ DEBUG LOG ===================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("STREAM-DEBUG")


# ================ DATABASE ===================
mongo_client = MongoClient(MONGO_DB_URI)
db = mongo_client["streambot"]
rtmp_col = db["group_rtmp"]

PID_FILE = "/tmp/ffmpeg_{chat_id}.pid"


# ================ HELPERS ===================
def get_rtmp(group_id: int):
    data = rtmp_col.find_one({"group_id": group_id})
    return data.get("rtmp") if data else None


def set_rtmp(user_id: int, group_id: int, link: str, group_name: str):
    rtmp_col.update_one(
        {"group_id": group_id},
        {"$set": {"user_id": user_id, "rtmp": link, "group_name": group_name}},
        upsert=True
    )


def kill_ffmpeg(chat_id: int):
    pid_path = PID_FILE.format(chat_id=chat_id)
    try:
        if os.path.exists(pid_path):
            with open(pid_path) as f:
                pid = int(f.read().strip())
            os.kill(pid, 9)
            os.remove(pid_path)
        else:
            os.system("pkill -9 ffmpeg")
    except Exception as e:
        logger.error(f"FFMPEG kill error: {e}")


# ================ RTMP ===================
@app.on_message(filters.command("setrtmp"))
async def set_rtmp_cmd(client, message):
    if message.chat.type != ChatType.PRIVATE:
        return await message.reply("⚠️ Use private chat")

    if len(message.command) < 3:
        return await message.reply("❌ /setrtmp group_id rtmp_link")

    group_id = int(message.command[1])
    link = message.command[2]

    try:
        chat = await client.get_chat(group_id)
        name = chat.title
    except:
        name = "Unknown"

    kill_ffmpeg(group_id)
    set_rtmp(message.from_user.id, group_id, link, name)

    await message.reply(f"✅ RTMP set for {name}")


# ================ STREAM ===================
@app.on_message(filters.command("playstream"))
async def play_stream(client, message):
    chat = message.chat
    user = message.from_user

    if chat.type == ChatType.PRIVATE:
        return await message.reply("⚠️ Use in group")

    group_id = chat.id
    rtmp = get_rtmp(group_id)

    if not rtmp:
        return await message.reply("⚠️ RTMP not set")

    if len(message.command) < 2:
        return await message.reply("❌ /playstream song name")

    query = " ".join(message.command[1:])
    status = await message.reply(f"🔎 Searching: {query}")

    logger.info(f"[SEARCH] Query: {query}")

    try:
        # ================= YOUTUBE CORE =================
        details, track_id = await YouTube.track(query)

        logger.info(f"[YT RESPONSE] details: {details}")
        logger.info(f"[YT RESPONSE] track_id: {track_id}")

        if not details:
            return await status.edit("❌ No track found")

        # ================= DEBUG STREAM EXTRACTION =================
        video_url = None
        title = "Unknown"

        if isinstance(details, dict):
            title = details.get("title") or query

            video_url = (
                details.get("stream_url")
                or details.get("url")
                or details.get("source")
                or details.get("video_url")
            )

            logger.info(f"[EXTRACT] Dict URL: {video_url}")

        elif isinstance(details, str):
            video_url = details
            title = query
            logger.info(f"[EXTRACT] String URL: {video_url}")

        # fallback logic (IMPORTANT)
        if not video_url and track_id:
            video_url = track_id
            logger.info(f"[FALLBACK] Using track_id as URL: {video_url}")

        if not video_url:
            logger.error("[ERROR] No stream URL found")
            return await status.edit("❌ Stream URL not found (check logs)")

        logger.info(f"[FINAL STREAM URL] {video_url}")

    except Exception as e:
        logger.error(f"[YT ERROR] {e}")
        return await status.edit(f"❌ YouTube Error: {e}")

    # ================ FFMPEG DEBUG ===================
    ffmpeg_command = [
        "ffmpeg",
        "-re",
        "-i", video_url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        rtmp
    ]

    logger.info(f"[FFMPEG CMD] {' '.join(ffmpeg_command)}")

    try:
        process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        pid_path = PID_FILE.format(chat_id=group_id)
        with open(pid_path, "w") as f:
            f.write(str(process.pid))

        await status.delete()

        await message.reply(
            f"📡 Streaming Started\n\n"
            f"🎵 {title}\n"
            f"🙋 {user.mention}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "➕ Add Me",
                    url=f"https://t.me/{app.username}?startgroup=true"
                )]
            ])
        )

        logger.info("[STATUS] Streaming started successfully")

    except Exception as e:
        logger.error(f"[FFMPEG ERROR] {e}")
        await message.reply(f"❌ FFmpeg Error: {e}")


# ================ END STREAM ===================
@app.on_message(filters.command("endstream"))
async def end_stream(client, message):
    chat = message.chat
    user = message.from_user

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            member = await client.get_chat_member(chat.id, user.id)
            if member.status not in [
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER
            ]:
                return await message.reply("⚠️ Only admins can stop stream")
        except:
            return await message.reply("❌ Error checking permission")

    kill_ffmpeg(chat.id)

    logger.info(f"[STOP] Stream stopped by {user.id}")

    await message.reply(f"🛑 Stream stopped by {user.mention}")

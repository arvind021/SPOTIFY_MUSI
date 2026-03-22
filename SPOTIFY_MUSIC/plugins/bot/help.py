
# ======================================================================
# ||                                                               ||
# ||   ██████╗  █████╗ ██████╗ ██╗   ██╗███████╗███████╗██╗ ██████╗  ||
# ||   ██╔══██╗██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝██║██╔═══██╗ ||
# ||   ██████╔╝███████║██████╔╝██║   ██║█████╗  ███████╗██║██║   ██║ ||
# ||   ██╔══██╗██╔══██║██╔══██╗██║   ██║██╔══╝  ╚════██║██║██║▄▄ ██║ ||
# ||   ██████╔╝██║  ██║██████╔╝╚██████╔╝███████╗███████║██║╚██████╔╝ ||
# ||   ╚═════╝ ╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝ ╚══▀▀═╝  ||
# ║    ▓▒░ ʙ ᴀ ʙ ɪ ᴇ sＩＱ ░▒▓  s ᴇ ᴄ ᴜ ʀ ᴇ  ▓▒░ ɴ ᴇ ᴛ ᴡ ᴏ ʀ ᴋ ░▒▓    ║
# ||                                                               ||
# ======================================================================
# || PROJECT  : SPOTIFY_MUSIC Public Music Repository                  ||
# || AUTHOR   : BabiesIQ Team                                      ||
# || REPO     : github.com/BABY-MUSIC/SPOTIFY_MUSIC                ||
# || API      : www.babyapi.pro                                    ||
# || TELEGRAM : t.me/BabiesIQ                                      ||
# ----------------------------------------------------------------------
# || LEGAL NOTICE                                                  ||
# || Use / upload / modify at your own risk.                       ||
# || Only config /.env edit allowed.                               ||
# || Do not modify core files.                                     ||
# || Keep this header if forked.                                   ||
# || Dev not responsible for ban / damage / api block.             ||
# ----------------------------------------------------------------------
# || SECURITY                                                      ||
# || Internal protection may exist.                                ||
# || Unauthorized change may stop system.                          ||
# || Use official API only -> www.babyapi.pro                      ||
# ======================================================================


# ======================================================================
# HEADER SAME
# ======================================================================

from typing import Union
from pyrogram import filters, types, enums
from pyrogram.types import InlineKeyboardMarkup, Message, InlineKeyboardButton

from SPOTIFY_MUSIC import app
from SPOTIFY_MUSIC.utils import help_pannel
from SPOTIFY_MUSIC.utils.database import get_lang
from SPOTIFY_MUSIC.utils.decorators.language import LanguageStart, languageCB
from SPOTIFY_MUSIC.utils.inline.help import help_back_markup, private_help_panel
from config import BANNED_USERS, START_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers
from SPOTIFY_MUSIC.utils.stuffs.helper import Helper


# ================= CACHE =================

LANG_CACHE = {}
STRING_CACHE = {}
KEYBOARD_CACHE = {}

# ==========================================


HELP_MAP = {
    "1": helpers.HELP_1,
    "3": helpers.HELP_3,
    "6": helpers.HELP_6,
    "7": helpers.HELP_7,
    "10": helpers.HELP_10,
    "11": helpers.HELP_11,
    "12": helpers.HELP_12,
    "13": helpers.HELP_13,
    "15": helpers.HELP_15,
}


# ================= FAST LANG =================

async def get_lang_cached(chat_id):

    if chat_id in LANG_CACHE:
        return LANG_CACHE[chat_id]

    lang = await get_lang(chat_id)
    LANG_CACHE[chat_id] = lang
    return lang


def get_string_cached(lang):

    if lang in STRING_CACHE:
        return STRING_CACHE[lang]

    s = get_string(lang)
    STRING_CACHE[lang] = s
    return s


def get_keyboard_cached(lang, back=False):

    key = f"{lang}_{back}"

    if key in KEYBOARD_CACHE:
        return KEYBOARD_CACHE[key]

    _ = get_string_cached(lang)
    kb = help_pannel(_, back)

    KEYBOARD_CACHE[key] = kb
    return kb


# ===========================================


@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(client: app, update: Union[types.Message, types.CallbackQuery]):

    is_callback = isinstance(update, types.CallbackQuery)

    if is_callback:

        try:
            await update.answer(cache_time=60)
        except:
            pass

        chat_id = update.message.chat.id

        language = await get_lang_cached(chat_id)
        _ = get_string_cached(language)

        keyboard = get_keyboard_cached(language, True)

        await update.edit_message_text(
            _["help_1"].format(SUPPORT_CHAT),
            reply_markup=keyboard
        )

    else:

        try:
            await update.delete()
        except:
            pass

        chat_id = update.chat.id

        language = await get_lang_cached(chat_id)
        _ = get_string_cached(language)

        keyboard = get_keyboard_cached(language, False)

        await update.reply_photo(
            photo=START_IMG_URL,
            caption=_["help_1"].format(SUPPORT_CHAT),
            reply_markup=keyboard,
        )


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):

    keyboard = private_help_panel(_)

    await message.reply_text(
        _["help_2"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@app.on_callback_query(filters.regex("^h:") & ~BANNED_USERS)
@languageCB
async def helper_cb(_, CallbackQuery, language):

    await CallbackQuery.answer(cache_time=60)

    try:
        _, key = CallbackQuery.data.split(":")
    except:
        return await CallbackQuery.answer("Invalid!", show_alert=True)

    text = HELP_MAP.get(key)

    if not text:
        return await CallbackQuery.answer("Invalid!", show_alert=True)

    keyboard = help_back_markup(language)

    await CallbackQuery.edit_message_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@app.on_callback_query(filters.regex('managebot123'))
async def on_back_button(client, query):

    await query.answer(cache_time=60)

    parts = query.data.split(None, 1)

    if len(parts) < 2:
        return

    cb = parts[1]

    chat_id = query.message.chat.id

    language = await get_lang_cached(chat_id)
    _ = get_string_cached(language)

    keyboard = get_keyboard_cached(language, True)

    if cb == "settings_back_helper":

        await query.edit_message_text(
            _["help_1"].format(SUPPORT_CHAT),
            reply_markup=keyboard
        )


@app.on_callback_query(filters.regex('mplus'))
async def mb_plugin_button(client, query):

    await query.answer(cache_time=60)

    parts = query.data.split(None, 1)

    if len(parts) < 2:
        return

    cb = parts[1]

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="mbot_cb")]]
    )

    if cb == "Okieeeeee":

        await query.edit_message_text(
            "`something errors`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN,
        )

    else:

        await query.edit_message_text(
            getattr(Helper, cb),
            reply_markup=keyboard
        )

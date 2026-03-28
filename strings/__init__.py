
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


import os
import yaml

languages = {}
languages_present = {}

# ✅ Absolute path (har VPS me safe)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_PATH = os.path.join(BASE_DIR, "strings", "langs")


def get_string(lang: str):
    # ✅ fallback to english if lang missing
    return languages.get(lang, languages.get("en", {}))


# ✅ Load English FIRST (mandatory)
try:
    en_file = os.path.join(LANG_PATH, "en.yml")
    with open(en_file, encoding="utf8") as f:
        languages["en"] = yaml.safe_load(f) or {}

    if not isinstance(languages["en"], dict):
        raise Exception("en.yml is not valid")

    languages_present["en"] = languages["en"].get("name", "English")

except Exception as e:
    print(f"❌ Critical Error: en.yml load failed -> {e}")
    exit()


# ✅ Load other languages safely
for filename in os.listdir(LANG_PATH):

    # ❌ skip non-yml files (VERY IMPORTANT)
    if not filename.endswith(".yml"):
        continue

    language_name = filename[:-4]

    # skip english (already loaded)
    if language_name == "en":
        continue

    try:
        file_path = os.path.join(LANG_PATH, filename)

        with open(file_path, encoding="utf8") as f:
            data = yaml.safe_load(f) or {}

        # ❌ invalid yaml structure
        if not isinstance(data, dict):
            raise Exception("Invalid YAML format")

        # ✅ fallback missing keys from english
        for key in languages["en"]:
            if key not in data:
                data[key] = languages["en"][key]

        languages[language_name] = data

        # ✅ safe name handling
        languages_present[language_name] = data.get("name", language_name)

    except Exception as e:
        print(f"⚠️ Skipping {filename} بسبب error: {e}")
        continue  # ❌ exit mat karo, next file load karo

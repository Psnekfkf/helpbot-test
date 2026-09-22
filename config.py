# -*- coding: utf-8 -*-
"""
Конфигурация бота: загрузка переменных окружения и общие константы.
Больше никаких секретов и chat_id прямо в коде — всё берётся из
переменных окружения (или из variables.txt для локального запуска).
"""
import os
import pytz

# ============ ПУТИ ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# ============ ЧАСОВОЙ ПОЯС ============
MSK = pytz.timezone("Europe/Moscow")


def load_variables_file(path="variables.txt"):
    """Читает файл вида 'КЛЮЧ значение' (по одному на строку) и подставляет
    их в os.environ, если такая переменная ещё не задана в самом окружении.
    Реальные переменные окружения (например, заданные хостингом) всегда
    имеют приоритет над файлом."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            key, value = parts
            os.environ.setdefault(key, value)


load_variables_file()


def _parse_id_list(value: str):
    return [int(x) for x in value.split(",") if x.strip()]


# ============ ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ============
# Никаких значений по умолчанию — бот не запустится, пока их не зададут.
# Так безопаснее, особенно если репозиторий когда-нибудь станет публичным.
TOKEN = os.environ["TOKEN"]
OPENWEATHER_KEY = os.environ["OPENWEATHER_KEY"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Необязательные ключи для точного поиска трека в Spotify (Client
# Credentials Flow — без входа пользователя). Если не заданы, бот
# просто даст ссылку на поиск в Spotify вместо ссылки на конкретный трек.
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Распознавание речи (локально, faster-whisper) — для голосовых команд
# по ключевым словам и краткого пересказа пересланных голосовых.
# Без ключей и аккаунтов вообще — модель скачивается один раз при
# первом запуске. Размер модели: tiny / base / small / medium — чем
# больше, тем точнее, но и медленнее/тяжелее для слабого сервера.
STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "base")

# ============ НАСТРОЙКИ ============
CITY = os.getenv("CITY", "Rostov-na-Donu")

# Кому приходят плановые сообщения (утро/день/вечер/тренировка/ночь).
# Поддерживается и старое имя переменной (MOM_CHAT_ID) для совместимости
# с прежним variables.txt, и новое MOM_CHAT_IDS через запятую.
_raw_mom_ids = os.getenv("MOM_CHAT_IDS") or os.getenv("MOM_CHAT_ID") or "549864131,8987266887"
MOM_CHAT_IDS = _parse_id_list(_raw_mom_ids)

# Чьи ОТВЕТЫ БОТУ дублируются в канал, и сам канал.
_raw_watch_ids = os.getenv("WATCH_USER_IDS") or "549864131,8987266887"
WATCH_USER_IDS = _parse_id_list(_raw_watch_ids)
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "-1004360677978"))

# Консольный ввод (main.py: console_input_loop) шлёт мамой в Telegram
# всё, что напишешь в STDIN процесса. На хостингах вроде Amvera "консоль"
# в панели — это и есть STDIN бота, а не отдельный shell, поэтому там
# легко случайно отправить мамe команду вместо того, чтобы её выполнить.
# Выключено по умолчанию — включить явно: CONSOLE_INPUT_ENABLED=true.
CONSOLE_INPUT_ENABLED = os.getenv("CONSOLE_INPUT_ENABLED", "false").strip().lower() in ("1", "true", "yes")

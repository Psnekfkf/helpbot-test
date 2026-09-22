# -*- coding: utf-8 -*-
"""
Хендлер распознавания песни («🎵 Угадать песню» в категории «Медиа»).

Срабатывает на ЛЮБОЕ голосовое сообщение или аудиофайл — не только
после нажатия кнопки, точно так же, как ссылка на Instagram работает
без похода в меню (handlers/instagram.py). Кнопка нужна только чтобы
объяснить, что именно прислать — а ещё выставляет флаг AWAITING_SONG,
чтобы handlers/voice.py понял: следующее голосовое нужно сразу отдать
сюда, а не пытаться распознавать в нём речь/команду.

Ссылки на Spotify/YouTube/Apple Music/Яндекс.Музыку показываются НЕ как
голый текст (длинная ссылка с кучей символов выглядит подозрительно —
будто фишинг/вирус), а как кнопки под сообщением (инлайн-кнопки).
Кнопка, ведущая на «поиск», а не точно на этот трек, помечена лупой 🔎
в подписи кнопки — коротко и понятно, без страшных ссылок в тексте.

ВАЖНО про Telegram API:
  - reply_markup с ReplyKeyboardMarkup (обычная клавиатура снизу) можно
    передавать ТОЛЬКО в новое сообщение (reply_text/reply_photo), но не
    в edit_text/edit_message_text — для редактирования существующего
    сообщения Telegram принимает только инлайн-клавиатуру. Поэтому
    статусное сообщение мы не редактируем клавиатурой, а удаляем и
    шлём новое.
  - Кнопка с НЕ-http(s) ссылкой (например, кастомный диплинк) валит
    отправку всего сообщения целиком — поэтому все ссылки на кнопках
    дополнительно проверяются (см. services/shazam_service.py).
"""
import os
import shutil
import tempfile
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.shazam_service import recognize_track
from keyboards import media_menu_keyboard

logger = logging.getLogger(__name__)

# Ключ в context.user_data: следующее голосовое — точно попытка
# распознать песню (мама явно нажала кнопку), пропускаем распознавание
# речи/команд в handlers/voice.py.
AWAITING_SONG = "awaiting_song"

NOT_FOUND_TEXT = (
    "😔 Не смог распознать трек.\n"
    "Попробуй записать более чистый и долгий отрывок (10+ секунд), "
    "по возможности без разговоров и лишнего шума."
)


async def ask_shazam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Пришли голосовое сообщение или аудиофайл с отрывком песни "
        "(хотя бы 5–10 секунд, чем чище звук — тем лучше) — я попробую угадать, что играет, "
        "и пришлю ссылки на неё.",
        reply_markup=media_menu_keyboard(),
    )
    context.user_data[AWAITING_SONG] = True


def _is_http_url(url: str | None) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


def _label(base: str, is_exact: bool) -> str:
    # 🔎 = это ссылка на поиск, а не точно на этот трек (короче и не
    # так тревожно, чем дописывать слово "поиск" в самой ссылке).
    return base if is_exact else f"{base} 🔎"


def _build_track_keyboard(track) -> InlineKeyboardMarkup:
    """Собирает инлайн-кнопки только из настоящих http(s)-ссылок —
    невалидная ссылка на кнопке ломает отправку всего сообщения."""
    row1, row2, extra = [], [], []

    if _is_http_url(track.spotify_url):
        row1.append(InlineKeyboardButton(_label("🟢 Spotify", track.spotify_exact), url=track.spotify_url))
    if _is_http_url(track.youtube_url):
        row1.append(InlineKeyboardButton(_label("▶️ YouTube", track.youtube_exact), url=track.youtube_url))
    if _is_http_url(track.apple_music_url):
        row2.append(InlineKeyboardButton(_label("🍎 Apple Music", track.apple_music_exact), url=track.apple_music_url))
    if _is_http_url(track.yandex_music_url):
        row2.append(InlineKeyboardButton("🟡 Яндекс.Музыка 🔎", url=track.yandex_music_url))
    if _is_http_url(track.shazam_url):
        extra.append(InlineKeyboardButton("🔷 Открыть в Shazam", url=track.shazam_url))

    rows = [r for r in (row1, row2) if r]
    if extra:
        rows.append(extra)
    return InlineKeyboardMarkup(rows) if rows else None


def _build_caption(track) -> str:
    return (
        f"🎧 Нашёл!\n\n"
        f"🎵 {track.artist} — {track.title}\n\n"
        f"Слушать — кнопки ниже 👇\n"
        f"(🔎 значит это ссылка на поиск, а не точно на этот трек)"
    )


async def _send_result(message, text: str, photo_url: str = None, keyboard=None):
    """Шлёт финальный ответ. Если по какой-то причине отправка с
    кнопками/картинкой не удалась — не молчим, а всё равно шлём хотя бы
    текст с обычной клавиатурой меню, чтобы мама точно получила ответ."""
    reply_markup = keyboard if keyboard is not None else media_menu_keyboard()

    if photo_url:
        try:
            await message.reply_photo(photo=photo_url, caption=text, reply_markup=reply_markup)
            return
        except Exception as e:
            logger.warning(f"Не удалось отправить с обложкой/кнопками, пробую текстом: {e}")

    try:
        await message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Не удалось отправить даже текстовый ответ с кнопками: {e}")
        # Последний рубеж — совсем без клавиатуры/кнопок, лишь бы дошло.
        await message.reply_text(text)


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    audio_obj = message.voice or message.audio
    if audio_obj is None:
        return

    status_msg = await message.reply_text("🎧 Слушаю... это может занять несколько секунд")

    tmp_dir = tempfile.mkdtemp(prefix="shazam_")
    track = None
    recognize_error = None
    try:
        tg_file = await context.bot.get_file(audio_obj.file_id)
        ext = ".ogg" if message.voice else (
            os.path.splitext(getattr(audio_obj, "file_name", "") or "")[1] or ".mp3"
        )
        local_path = os.path.join(tmp_dir, f"track{ext}")
        await tg_file.download_to_drive(local_path)
        track = await recognize_track(local_path)
    except Exception as e:
        logger.error(f"Ошибка распознавания трека: {e}")
        recognize_error = e
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        await status_msg.delete()
    except Exception:
        pass

    if recognize_error is not None:
        await _send_result(message, text=f"😔 Что-то пошло не так при распознавании.\n\nОшибка: {str(recognize_error)[:150]}")
        return

    if not track:
        await _send_result(message, text=NOT_FOUND_TEXT)
        return

    await _send_result(
        message,
        text=_build_caption(track),
        photo_url=track.cover_url,
        keyboard=_build_track_keyboard(track),
    )

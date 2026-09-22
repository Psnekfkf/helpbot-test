# -*- coding: utf-8 -*-
"""
Главный хендлер голосовых/аудио сообщений. Решает, что делать с
присланным голосовым:

  1. Пересланное сообщение (мама переслала боту голосовое от подруги
     или родственника) -> считаем, что это тот самый длинный ГС, и
     делаем краткий пересказ через ИИ.
  2. Явно нажата «🎵 Угадать песню» (services/shazam_service, флаг
     AWAITING_SONG) -> сразу Shazam, распознавание речи не нужно.
  3. Обычное голосовое от мамы самому боту -> распознаём речь и:
     - находим ключевое слово -> открываем нужный раздел меню;
     - речь распознана, но слово не найдено -> отдаём текст в ИИ как
       обычный вопрос (можно просто "поговорить" с ботом голосом);
     - речь не распознана вообще (пусто) -> вероятно, это музыка ->
       пробуем Shazam, как и раньше.

ВАЖНО: сопоставление по ключевым словам — это простой поиск подстроки
в распознанном тексте, а не полноценное понимание смысла. Иногда будет
случайное совпадение (например, "цвет" в середине незнакомого слова).
Для голосового помощника мамы это ок — цена ошибки минимальна (просто
откроется не тот раздел), а сложность в разы меньше, чем у настоящего
NLU.
"""
import os
import shutil
import asyncio
import tempfile
import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import stt_service
from services.ai_service import summarize_text
from keyboards import media_menu_keyboard
from handlers import shazam as shazam_handlers
from handlers import style, weather, ai, instagram

logger = logging.getLogger(__name__)

# Порядок важен: более специфичные ключевые слова — раньше общих.
# "завтра" проверяем раньше общего "цвет", чтобы "какие цвета завтра"
# уводило на цвета НА ЗАВТРА, а не на сегодня.
KEYWORD_ROUTES = [
    (["погод"], weather.weather),
    (["очист", "с чистого листа", "заново начн"], ai.clear_history),
    (["аффирмац", "поддержи", "вдохнов"], style.affirmation),
    (["завтра"], style.colors_tomorrow),
    (["цвет"], style.colors_today),
    (["инстаграм", "инсту", "рилс", "скачай видео", "скачай фото"], instagram.ask_instagram),
]


def _is_forwarded(message) -> bool:
    """Работает и с новым Bot API (forward_origin), и со старым
    (forward_date) — на случай другой версии python-telegram-bot."""
    return bool(getattr(message, "forward_origin", None) or getattr(message, "forward_date", None))


async def _download_audio(context: ContextTypes.DEFAULT_TYPE, audio_obj, tmp_dir: str) -> str:
    tg_file = await context.bot.get_file(audio_obj.file_id)
    ext = os.path.splitext(getattr(audio_obj, "file_name", "") or "")[1] or ".ogg"
    local_path = os.path.join(tmp_dir, f"audio{ext}")
    await tg_file.download_to_drive(local_path)
    return local_path


async def _handle_forwarded_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_obj):
    message = update.message
    status_msg = await message.reply_text("📝 Слушаю и делаю краткий пересказ...")
    tmp_dir = tempfile.mkdtemp(prefix="summary_")
    try:
        local_path = await _download_audio(context, audio_obj, tmp_dir)
        text = await stt_service.transcribe(local_path)

        if not text.strip():
            await status_msg.edit_text(
                "😔 Не расслышал речь в этом сообщении — возможно, там музыка или очень тихо."
            )
            return

        import asyncio
        summary = await asyncio.to_thread(summarize_text, text)

        await status_msg.delete()
        await message.reply_text(f"📝 Краткий пересказ:\n\n{summary}", reply_markup=media_menu_keyboard())
    except Exception as e:
        logger.error(f"Ошибка пересказа голосового: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.reply_text(
            f"😔 Не получилось сделать пересказ.\n\nОшибка: {str(e)[:150]}",
            reply_markup=media_menu_keyboard(),
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    audio_obj = message.voice or message.audio
    if audio_obj is None:
        return

    # 1. Переслано -> краткий пересказ.
    if _is_forwarded(message):
        await _handle_forwarded_summary(update, context, audio_obj)
        return

    # 2. Явно попросил(а) угадать песню -> сразу Shazam, без распознавания речи.
    if context.user_data.get(shazam_handlers.AWAITING_SONG):
        context.user_data[shazam_handlers.AWAITING_SONG] = False
        await shazam_handlers.handle_audio_message(update, context)
        return

    # 3. Пробуем распознать речь и найти команду.
    status_msg = await message.reply_text("🎙 Слушаю...")
    tmp_dir = tempfile.mkdtemp(prefix="voice_")
    text = ""
    try:
        local_path = await _download_audio(context, audio_obj, tmp_dir)
        text = await stt_service.transcribe(local_path)
    except Exception as e:
        logger.error(f"Ошибка распознавания речи: {e}")
        text = ""
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    lowered = text.lower()
    for keywords, handler_func in KEYWORD_ROUTES:
        if any(kw in lowered for kw in keywords):
            try:
                await status_msg.delete()
            except Exception:
                pass
            await handler_func(update, context)
            return

    if text.strip():
        # Ключевое слово не нашли, но речь есть -> обычный вопрос к ИИ.
        try:
            await status_msg.delete()
        except Exception:
            pass
        await ai.answer_question_from_voice(update, context, text)
        return

    # Речи не распознано вообще -> вероятно, музыка -> пробуем Shazam.
    try:
        await status_msg.delete()
    except Exception:
        pass
    await shazam_handlers.handle_audio_message(update, context)

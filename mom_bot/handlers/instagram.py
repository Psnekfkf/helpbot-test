# -*- coding: utf-8 -*-
"""
Хендлеры категории «Медиа»: скачивание из Instagram по ссылке.
"""
import os
import shutil
import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.instagram_service import INSTAGRAM_URL_RE, download_instagram_media
from keyboards import media_menu_keyboard

logger = logging.getLogger(__name__)

# Ключ в context.user_data, помечающий, что следующее сообщение мамы —
# это ссылка на Instagram, а не команда/кнопка.
AWAITING_INSTA_LINK = "awaiting_insta_link"


async def ask_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Скинь ссылку на рилс, видео или фото из Instagram — я скачаю и пришлю сюда.\n\n"
        "Подходят ссылки вида:\n"
        "• instagram.com/reel/...\n"
        "• instagram.com/p/...\n"
        "• instagram.com/tv/...",
        reply_markup=media_menu_keyboard(),
    )
    context.user_data[AWAITING_INSTA_LINK] = True


async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вызывается роутером как для явно ожидаемой ссылки (после кнопки
    «Скачать из Инсты»), так и для ссылки, присланной без похода в меню."""
    context.user_data[AWAITING_INSTA_LINK] = False
    url_text = update.message.text.strip()
    match = INSTAGRAM_URL_RE.search(url_text)
    if not match:
        await update.message.reply_text(
            "😅 Это не похоже на ссылку из Instagram.\nПришли ссылку на рилс/пост, например: https://www.instagram.com/reel/...",
            reply_markup=media_menu_keyboard(),
        )
        return

    url = match.group(0)
    status_msg = await update.message.reply_text("⏳ Скачиваю, секунду...")

    temp_dir = None
    try:
        files, temp_dir = await download_instagram_media(url)
        if not files:
            raise RuntimeError("Файлы не найдены после загрузки")

        for path in files:
            ext = os.path.splitext(path)[1].lower()
            with open(path, "rb") as f:
                if ext in (".mp4", ".mov", ".webm", ".mkv"):
                    await update.message.reply_video(video=f, reply_markup=media_menu_keyboard())
                elif ext in (".jpg", ".jpeg", ".png", ".webp"):
                    await update.message.reply_photo(photo=f, reply_markup=media_menu_keyboard())
                else:
                    await update.message.reply_document(document=f, reply_markup=media_menu_keyboard())

        await status_msg.delete()
    except Exception as e:
        logger.error(f"Ошибка скачивания из Instagram: {e}")
        await status_msg.edit_text(
            f"😔 Не получилось скачать.\nВозможно, пост приватный, удалён, либо Instagram временно блокирует загрузку.\n\nОшибка: {str(e)[:150]}"
        )
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

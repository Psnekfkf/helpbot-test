# -*- coding: utf-8 -*-
"""
Хендлеры категории «Стиль дня»: цвета на сегодня/завтра, аффирмации.
"""
import random
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from config import MSK
from content import AFFIRMATIONS
from colors_repo import get_colors_for_date, get_month_name
from colors_image import generate_colors_image
from keyboards import style_menu_keyboard

logger = logging.getLogger(__name__)

NO_DATA_TEXT = "😅 Нет данных для этой даты.\nДоступны: июнь–ноябрь 2026"


async def _send_colors(update: Update, date_obj: datetime, label: str, hint: str):
    colors = get_colors_for_date(date_obj)
    if not colors:
        await update.message.reply_text(NO_DATA_TEXT, reply_markup=style_menu_keyboard())
        return

    try:
        photo_buf = generate_colors_image(colors)
        await update.message.reply_photo(photo=photo_buf)
    except Exception as e:
        logger.error(f"Не удалось сгенерировать картинку цветов: {e}")

    await update.message.reply_text(
        f"📅 {label} {date_obj.day} {get_month_name(date_obj.month)}\n"
        f"✨ Твои цвета удачи:\n👉 {colors}\n\n{hint}",
        reply_markup=style_menu_keyboard(),
    )


async def colors_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(MSK)
    await _send_colors(
        update, today, "Сегодня",
        "💡 Выбирай одежду в этих цветах — и день пройдёт отлично! 💖",
    )


async def colors_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tomorrow = datetime.now(MSK) + timedelta(days=1)
    await _send_colors(
        update, tomorrow, "Завтра",
        "💡 Можешь подготовить одежду уже сегодня!",
    )


async def affirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aff = random.choice(AFFIRMATIONS)
    await update.message.reply_text(
        f"💫 {aff}\n\nЗапомни: ты удивительная! ❤️",
        reply_markup=style_menu_keyboard(),
    )

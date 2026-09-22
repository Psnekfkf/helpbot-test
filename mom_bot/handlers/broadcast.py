# -*- coding: utf-8 -*-
"""
Плановые сообщения маме (через JobQueue) и пересылка её ответов в канал.
"""
import random
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import MSK, MOM_CHAT_IDS, WATCH_USER_IDS, TARGET_CHANNEL_ID
from colors_repo import get_colors_for_date, get_month_name
from content import HOW_ARE_YOU, GOODNIGHT_MESSAGES
from keyboards import main_menu_keyboard, ALL_BUTTONS

logger = logging.getLogger(__name__)


async def send_to_mom(app_bot, message_text: str):
    for chat_id in MOM_CHAT_IDS:
        try:
            await app_bot.send_message(chat_id=chat_id, text=message_text, reply_markup=main_menu_keyboard())
            logger.info(f"📨 Сообщение отправлено в {chat_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в {chat_id}: {e}")


async def forward_reply_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настоящее сообщение (не команда и не нажатие кнопки меню) от
    отслеживаемого пользователя дублируется в канал."""
    user_id = update.effective_user.id
    if user_id not in WATCH_USER_IDS:
        return
    if update.message.text in ALL_BUTTONS:
        return

    forward_text = (
        f"[Сообщение] {update.effective_user.full_name} (id {user_id}):\n\n"
        f"{update.message.text}"
    )
    try:
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=forward_text)
        logger.info(f"Переслано сообщение от {user_id} в канал {TARGET_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Не удалось переслать сообщение в канал: {e}")


async def job_morning(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(MSK)
    colors = get_colors_for_date(today)
    colors_msg = f"\n✨ Цвета дня: {colors}" if colors else ""
    message = (
        f"🌅 Доброе утро, мамуля! 💖\n\nКак ты спала? 😊\n"
        f"📅 Сегодня {today.day} {get_month_name(today.month)}{colors_msg}"
    )
    await send_to_mom(context.bot, message)


async def job_midday(context: ContextTypes.DEFAULT_TYPE):
    await send_to_mom(context.bot, f"☀️ {random.choice(HOW_ARE_YOU)}")


async def job_evening(context: ContextTypes.DEFAULT_TYPE):
    message = "🌅 Добрый вечер, мамуля!\n\nКак прошёл твой день? 😊\nТы сегодня многое сделала — я горжусь! 💫"
    await send_to_mom(context.bot, message)


async def job_training(context: ContextTypes.DEFAULT_TYPE):
    await send_to_mom(context.bot, "Удачной тренировки! 💪")


async def job_goodnight(context: ContextTypes.DEFAULT_TYPE):
    await send_to_mom(context.bot, f"{random.choice(GOODNIGHT_MESSAGES)}")

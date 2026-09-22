# -*- coding: utf-8 -*-
"""
Хендлер категории «Погода» (без подменю — единственное действие).
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import CITY
from services.weather_service import get_weather
from keyboards import main_menu_keyboard


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weather_data = await get_weather()
    if weather_data:
        await update.message.reply_text(
            f"🌤 Погода в {CITY}:\n{weather_data}\n\nОдевайся по погоде, мамуля! 💕",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await update.message.reply_text(
            "😅 Не удалось получить погоду.\nНо ты всё равно красивая в любую погоду! 💖",
            reply_markup=main_menu_keyboard(),
        )

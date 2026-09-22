# -*- coding: utf-8 -*-
"""
Навигация по меню: /start, /help и переключение между категориями.
"""
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import ASSETS_DIR
from keyboards import (
    main_menu_keyboard,
    style_menu_keyboard,
    ai_menu_keyboard,
    media_menu_keyboard,
)

logger = logging.getLogger(__name__)

# Картинка-приветствие, которая шлётся вместе с /start.
# Если файла нет (не скопировали на хостинг) — бот просто пришлёт текст без неё.
WELCOME_IMAGE_PATH = os.path.join(ASSETS_DIR, "welcome.png")

WELCOME_TEXT = (
    "👋 Привет, мамуля! 💖\n\n"
    "Я твой личный помощник! Выбирай категорию на клавиатуре снизу:\n\n"
    "🔹 🎨 Стиль дня — цвета на сегодня/завтра и аффирмации\n"
    "🔹 🧠 Помощник — любой вопрос к ИИ\n"
    "🔹 🌤 Погода — что на улице прямо сейчас\n"
    "🔹 📥 Медиа — скачать рилс/фото из Instagram и угадать песню по голосовому\n\n"
    "🎙 Со мной можно и голосом: просто скажи, например, «погода» или "
    "«цвета на завтра» в голосовом — открою нужный раздел. А если "
    "перешлёшь мне длинное голосовое от подруги — сделаю краткий пересказ.\n\n"
    "Всё то же самое работает и командами — набери /help, если забудешь.\n\n"
    "Я всегда рядом и люблю тебя! ❤️"
)

HELP_TEXT = (
    "📋 Команды:\n"
    "/start — начать / показать меню\n"
    "/menu — вернуться в главное меню\n"
    "/colors — цвета дня\n"
    "/colors_tomorrow — цвета на завтра\n"
    "/affirmation — аффирмация\n"
    "/weather — погода\n"
    "/ai — спросить ИИ\n"
    "/insta — скачать из Instagram\n"
    "/song — угадать песню по голосовому/аудио\n"
    "/clear — очистить историю ИИ\n\n"
    "Либо просто пользуйся кнопками снизу 💖\n\n"
    "🎙 Голосом: скажи ключевое слово («погода», «цвета», «аффирмация», "
    "«очисти», «инстаграм») в голосовом — открою нужный раздел. Просто "
    "поговорить — тоже можно, отвечу как ИИ. А перешлёшь мне голосовое "
    "от кого-то — сделаю краткий пересказ."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(WELCOME_IMAGE_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=WELCOME_TEXT,
                reply_markup=main_menu_keyboard(),
            )
    except FileNotFoundError:
        logger.warning(f"Картинка приветствия не найдена: {WELCOME_IMAGE_PATH}")
        await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, reply_markup=main_menu_keyboard())


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())


async def show_style_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎨 Стиль дня:", reply_markup=style_menu_keyboard())


async def show_ai_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 Помощник:", reply_markup=ai_menu_keyboard())


async def show_media_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Медиа:", reply_markup=media_menu_keyboard())

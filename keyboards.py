# -*- coding: utf-8 -*-
"""
Клавиатуры бота: главное меню (категории) + подменю внутри каждой
категории. Между подменю и главным меню можно переключаться кнопкой
«◀️ Назад». У «Погоды» подменю нет — это единственное действие в своей
категории, поэтому нажатие сразу выполняет его.
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton

BACK = "◀️ Назад"

# ---- Главное меню (категории) ----
CAT_STYLE = "🎨 Стиль дня"
CAT_AI = "🧠 Помощник"
CAT_WEATHER = "🌤 Погода"
CAT_MEDIA = "📥 Медиа"

MAIN_MENU_BUTTONS = {CAT_STYLE, CAT_AI, CAT_WEATHER, CAT_MEDIA}

# ---- Категория «Стиль дня» ----
BTN_COLORS_TODAY = "🎨 Цвета дня"
BTN_COLORS_TOMORROW = "📅 Цвета на завтра"
BTN_AFFIRMATION = "💪 Аффирмация"

STYLE_MENU_BUTTONS = {BTN_COLORS_TODAY, BTN_COLORS_TOMORROW, BTN_AFFIRMATION}

# ---- Категория «Помощник» (ИИ) ----
BTN_ASK_AI = "🧠 Спросить ИИ"
BTN_CLEAR_HISTORY = "🗑 Очистить историю"

AI_MENU_BUTTONS = {BTN_ASK_AI, BTN_CLEAR_HISTORY}

# ---- Категория «Медиа» ----
BTN_INSTAGRAM = "📥 Скачать из Инсты"
BTN_SHAZAM = "🎵 Угадать песню"

MEDIA_MENU_BUTTONS = {BTN_INSTAGRAM, BTN_SHAZAM}

# Все "листовые" кнопки-действия (без категорий и "Назад") — нужны,
# чтобы отличать нажатия кнопок меню от обычных сообщений мамы
# (например, при пересылке её ответов в канал).
ACTION_BUTTONS = STYLE_MENU_BUTTONS | AI_MENU_BUTTONS | MEDIA_MENU_BUTTONS | {CAT_WEATHER}
ALL_BUTTONS = MAIN_MENU_BUTTONS | ACTION_BUTTONS | {BACK}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(CAT_STYLE), KeyboardButton(CAT_AI)],
        [KeyboardButton(CAT_WEATHER), KeyboardButton(CAT_MEDIA)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def style_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_COLORS_TODAY), KeyboardButton(BTN_COLORS_TOMORROW)],
        [KeyboardButton(BTN_AFFIRMATION)],
        [KeyboardButton(BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def ai_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_ASK_AI)],
        [KeyboardButton(BTN_CLEAR_HISTORY)],
        [KeyboardButton(BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def media_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_INSTAGRAM)],
        [KeyboardButton(BTN_SHAZAM)],
        [KeyboardButton(BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

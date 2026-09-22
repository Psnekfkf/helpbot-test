# -*- coding: utf-8 -*-
"""
Главный роутер входящих текстовых сообщений: сначала проверяются
FSM-состояния (ждём ответ для ИИ / ссылку на Инсту), затем — кнопки
меню (категории, действия, «Назад»), и в конце — просто текст.
"""
from telegram import Update
from telegram.ext import ContextTypes

from keyboards import (
    main_menu_keyboard,
    CAT_STYLE, CAT_AI, CAT_WEATHER, CAT_MEDIA, BACK,
    BTN_COLORS_TODAY, BTN_COLORS_TOMORROW, BTN_AFFIRMATION,
    BTN_ASK_AI, BTN_CLEAR_HISTORY, BTN_INSTAGRAM, BTN_SHAZAM,
)
from services.instagram_service import INSTAGRAM_URL_RE

from handlers.menu import show_main_menu, show_style_menu, show_ai_menu, show_media_menu
from handlers.style import colors_today, colors_tomorrow, affirmation
from handlers.ai import ask_ai, clear_history, handle_ai_query, AWAITING_AI_QUERY
from handlers.weather import weather
from handlers.instagram import ask_instagram, handle_instagram_link, AWAITING_INSTA_LINK
from handlers.shazam import ask_shazam
from handlers.broadcast import forward_reply_to_channel

# Категории главного меню -> что показать/сделать при нажатии.
# У «Погоды» нет подменю, поэтому она сразу указывает на свой хендлер.
CATEGORY_ROUTES = {
    CAT_STYLE: show_style_menu,
    CAT_AI: show_ai_menu,
    CAT_MEDIA: show_media_menu,
    CAT_WEATHER: weather,
}

# Кнопки-действия внутри подменю -> хендлер, который их выполняет.
ACTION_ROUTES = {
    BTN_COLORS_TODAY: colors_today,
    BTN_COLORS_TOMORROW: colors_tomorrow,
    BTN_AFFIRMATION: affirmation,
    BTN_ASK_AI: ask_ai,
    BTN_CLEAR_HISTORY: clear_history,
    BTN_INSTAGRAM: ask_instagram,
    BTN_SHAZAM: ask_shazam,
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Дублируем в канал, если это обычное сообщение от отслеживаемого пользователя
    await forward_reply_to_channel(update, context)

    # FSM: ожидаем ответ на вопрос для ИИ
    if context.user_data.get(AWAITING_AI_QUERY):
        await handle_ai_query(update, context)
        return

    # FSM: ожидаем ссылку на Instagram
    if context.user_data.get(AWAITING_INSTA_LINK):
        await handle_instagram_link(update, context)
        return

    if text == BACK:
        await show_main_menu(update, context)
        return

    if text in CATEGORY_ROUTES:
        await CATEGORY_ROUTES[text](update, context)
        return

    if text in ACTION_ROUTES:
        await ACTION_ROUTES[text](update, context)
        return

    if text and INSTAGRAM_URL_RE.search(text):
        # Ссылку на инсту можно скинуть и без похода в меню «Медиа»
        await handle_instagram_link(update, context)
        return

    await update.message.reply_text(
        "👋 Я твой помощник, мамуля!\nИспользуй кнопки или напиши /start",
        reply_markup=main_menu_keyboard(),
    )

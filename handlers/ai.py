# -*- coding: utf-8 -*-
"""
Хендлеры категории «Помощник»: вопрос к ИИ и очистка истории.
"""
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import MSK
from colors_repo import get_colors_for_date, get_month_name
from services.weather_service import get_weather
from services.ai_service import conversations, ai_client
from keyboards import ai_menu_keyboard

logger = logging.getLogger(__name__)

# Ключ в context.user_data, помечающий, что следующее сообщение мамы —
# это вопрос для ИИ, а не команда/кнопка.
AWAITING_AI_QUERY = "awaiting_ai_query"


async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 Напиши одним сообщением, что тебя волнует или о чём ты хочешь спросить.\n\n"
        "Я передам это нейросети и пришлю тебе ответ ✨\n\n"
        "Примеры:\n"
        "• «Как мне лучше одеться на прогулку?»\n"
        "• «У меня грустное настроение, поддержи»\n"
        "• «Что приготовить из курицы?»",
        reply_markup=ai_menu_keyboard(),
    )
    context.user_data[AWAITING_AI_QUERY] = True


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversations.clear(update.effective_user.id)
    await update.message.reply_text(
        "🗑 История диалога очищена! Начнём с чистого листа. 💫",
        reply_markup=ai_menu_keyboard(),
    )


async def handle_ai_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вызывается роутером, когда AWAITING_AI_QUERY выставлен в True —
    то есть мама только что прислала свой вопрос текстом."""
    context.user_data[AWAITING_AI_QUERY] = False
    await answer_ai_question(update, context, update.message.text)


async def answer_question_from_voice(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """То же самое, но вопрос пришёл из распознанного голосового
    (handlers/voice.py) — вызывается, когда ключевые слова ни на одну
    категорию меню не сработали, но речь распозналась: значит, мама
    просто разговаривает с ботом голосом."""
    await answer_ai_question(update, context, text)


async def answer_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
    user_id = update.effective_user.id

    today = datetime.now(MSK)
    colors = get_colors_for_date(today)
    colors_text = f"Сегодня {today.day} {get_month_name(today.month)}: {colors}" if colors else "Цветов нет"
    weather_data = await get_weather()
    weather_text = f"Погода: {weather_data}" if weather_data else "Погода не определена"
    context_info = f"[КОНТЕКСТ: {colors_text} | {weather_text}]"

    conversations.append(user_id, "user", f"{context_info}\n\nВопрос мамы: {user_message}")

    await update.message.reply_text("🤔 Думаю... это может занять несколько секунд")
    try:
        bot_reply = ai_client.ask(conversations.get(user_id))
        conversations.append(user_id, "assistant", bot_reply)
        await update.message.reply_text(
            f"🧠 Ответ:\n\n{bot_reply}\n\n✨ Надеюсь, это помогло!",
            reply_markup=ai_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        await update.message.reply_text(
            f"😔 Все нейросети сейчас недоступны.\nПопробуйте через минуту.\n\nОшибка: {str(e)[:100]}",
            reply_markup=ai_menu_keyboard(),
        )

# -*- coding: utf-8 -*-
"""
Точка входа: сборка Application, регистрация хендлеров (команды +
кнопки) и планировщика плановых сообщений.

Запуск: python main.py
"""
import asyncio
import logging
from datetime import time as dtime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import (
    TOKEN, CITY, MSK, MOM_CHAT_IDS, TARGET_CHANNEL_ID, WATCH_USER_IDS,
    CONSOLE_INPUT_ENABLED, STT_MODEL_SIZE,
)
from services.ai_service import ai_client
from handlers import menu, style, ai, weather, instagram, shazam, voice, broadcast
from handlers.router import handle_message

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def console_input_loop(application):
    """Читает строки из терминала, где запущен бот, и отправляет их
    маме как обычное сообщение. Работает в фоне и не блокирует остальную
    работу бота (input() выполняется в отдельном потоке).
    Команда /exit останавливает только этот слушатель консоли."""
    loop = asyncio.get_event_loop()
    logger.info("⌨️  Консольный ввод активен. Печатай текст и жми Enter — уйдёт маме.")
    while True:
        try:
            text = await loop.run_in_executor(None, input, "💬 > ")
        except (EOFError, KeyboardInterrupt):
            logger.info("⌨️  Консольный ввод остановлен (нет stdin).")
            break

        text = text.strip()
        if not text:
            continue
        if text == "/exit":
            logger.info("⌨️  Консольный ввод остановлен по команде /exit.")
            break

        try:
            await broadcast.send_to_mom(application.bot, text)
            print(f"✅ Отправлено: {text}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение из консоли: {e}")


async def start_console_input(application):
    """post_init-хук: запускает console_input_loop как фоновую задачу,
    как только бот стартовал — но ТОЛЬКО если явно включено
    (CONSOLE_INPUT_ENABLED=true). На хостингах вроде Amvera "консоль" в
    панели — это STDIN самого бота, а не отдельный shell, так что
    что угодно, набранное туда по привычке (например, команда для
    системы), на самом деле уйдёт маме в Telegram. По умолчанию эта
    фича выключена именно поэтому."""
    if not CONSOLE_INPUT_ENABLED:
        logger.info("⌨️  Консольный ввод отключён (CONSOLE_INPUT_ENABLED=false).")
        return
    asyncio.create_task(console_input_loop(application))


def main():
    logger.info("=" * 60)
    logger.info("🚀 БОТ ЗАПУЩЕН!")
    logger.info("=" * 60)
    logger.info(f"👤 Chat IDs (мама): {MOM_CHAT_IDS}")
    logger.info(f"🌆 Город: {CITY}")
    logger.info(f"🧠 OpenRouter: ✅ подключён ({len(ai_client.models)} моделей)")
    logger.info("🌤 OpenWeather: ✅ подключён")
    logger.info(f"📡 Пересылка ответов в канал {TARGET_CHANNEL_ID} для ID: {WATCH_USER_IDS}")
    logger.info(f"🎙 Распознавание речи: локально (faster-whisper, модель '{STT_MODEL_SIZE}')")
    logger.info("⏰ Рассылка (МСК): 8:00, 12:00, 18:00, 19:00 (ср/пт — тренировка), 22:00 (ночь)")
    logger.info("=" * 60)

    app = Application.builder().token(TOKEN).post_init(start_console_input).build()

    # ---- Команды (дублируют кнопки меню) ----
    app.add_handler(CommandHandler("start", menu.start))
    app.add_handler(CommandHandler("menu", menu.show_main_menu))
    app.add_handler(CommandHandler("help", menu.help_cmd))
    app.add_handler(CommandHandler(["colors", "colors_today"], style.colors_today))
    app.add_handler(CommandHandler("colors_tomorrow", style.colors_tomorrow))
    app.add_handler(CommandHandler("affirmation", style.affirmation))
    app.add_handler(CommandHandler("weather", weather.weather))
    app.add_handler(CommandHandler("ai", ai.ask_ai))
    app.add_handler(CommandHandler("clear", ai.clear_history))
    app.add_handler(CommandHandler("insta", instagram.ask_instagram))
    app.add_handler(CommandHandler("song", shazam.ask_shazam))

    # ---- Кнопки меню и обычный текст ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ---- Голосовые/аудио: команды по ключевым словам, вопрос к ИИ,
    # пересказ форварднутых ГС, а если ничего не подошло — Shazam ----
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice.handle_voice_message))

    # ---- Плановые сообщения ----
    jq = app.job_queue
    # days: 0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб, 6=Вс
    jq.run_daily(broadcast.job_morning, time=dtime(hour=8, minute=0, tzinfo=MSK))
    jq.run_daily(broadcast.job_midday, time=dtime(hour=12, minute=0, tzinfo=MSK))
    jq.run_daily(broadcast.job_evening, time=dtime(hour=18, minute=0, tzinfo=MSK))
    jq.run_daily(broadcast.job_training, time=dtime(hour=19, minute=0, tzinfo=MSK), days=(2, 4))
    jq.run_daily(broadcast.job_goodnight, time=dtime(hour=22, minute=0, tzinfo=MSK))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

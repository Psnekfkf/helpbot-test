# -*- coding: utf-8 -*-
"""
Распознавание речи (Speech-to-Text) — локально, через faster-whisper.
Никаких ключей и аккаунтов не нужно: модель скачивается один раз при
первом запуске (нужен интернет на хостинге, но не нужен API-ключ) и
дальше работает прямо на сервере бота.

Используется для:
  - голосовых команд по ключевым словам (handlers/voice.py)
  - краткого пересказа длинных пересланных голосовых

Формат аудио: faster-whisper сам decode'ит файл через PyAV (внутри
которого статически собран ffmpeg), поэтому OGG/Opus из Telegram
голосовых читает без дополнительной конвертации — в отличие от
shazamio, отдельный ffmpeg через imageio-ffmpeg тут не нужен.
"""
from __future__ import annotations

import asyncio
import logging

from config import STT_MODEL_SIZE

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Модель грузится один раз и переиспользуется дальше (лениво —
    при первом реальном голосовом, а не при старте бота)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info(f"⏳ Загружаю модель распознавания речи ({STT_MODEL_SIZE})... это разово")
        _model = WhisperModel(STT_MODEL_SIZE, device="cpu", compute_type="int8")
        logger.info("✅ Модель распознавания речи готова")
    return _model


def _transcribe_sync(audio_path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(audio_path, language="ru", vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe(audio_path: str) -> str:
    """Возвращает распознанный текст. Пустая строка — в записи не было
    разборчивой речи (например, играла музыка или было очень тихо)."""
    return await asyncio.to_thread(_transcribe_sync, audio_path)

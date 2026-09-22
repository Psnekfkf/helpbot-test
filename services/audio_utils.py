# -*- coding: utf-8 -*-
"""
Общие утилиты для работы с аудио: конвертация в WAV через ffmpeg.

Бинарник ffmpeg берётся из pip-пакета imageio-ffmpeg (сам скачивает
статический бинарник при установке — не нужен root/apt/Dockerfile),
с запасным вариантом на системный ffmpeg из PATH.

Используется и распознаванием песен (services/shazam_service.py), и
распознаванием речи (services/stt_service.py) — поэтому вынесено сюда,
а не продублировано в обоих местах.
"""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def resolve_ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.warning(f"imageio-ffmpeg недоступен ({e}), пробую системный ffmpeg из PATH")
        return "ffmpeg"


def convert_to_wav(src_path: str, sample_rate: int = 44100) -> str:
    """Конвертирует входной аудиофайл в WAV. Для Shazam используем
    44100 Гц (стандарт для аудио-фингерпринтинга), для распознавания
    речи достаточно и 16000 Гц — вызывающий код сам указывает нужное.

    Работает синхронно — вызывающий код сам решает, оборачивать ли в
    asyncio.to_thread (чтобы не блокировать event loop бота)."""
    wav_path = f"{src_path}.{sample_rate}.wav"
    ffmpeg_bin = resolve_ffmpeg_binary()
    try:
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", src_path, "-ar", str(sample_rate), "-ac", "1", wav_path],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Не нашёл рабочий ffmpeg (ни через imageio-ffmpeg, ни в системе). "
            "Проверь: pip install -r requirements.txt"
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode(errors="ignore")[:200]
        raise RuntimeError(f"ffmpeg не смог обработать аудио: {stderr}")
    return wav_path

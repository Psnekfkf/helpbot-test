# -*- coding: utf-8 -*-
"""
Скачивание медиа (рилсы/фото/видео) из Instagram по ссылке через yt-dlp.
"""
import os
import re
import shutil
import tempfile
import asyncio

import yt_dlp

INSTAGRAM_URL_RE = re.compile(r"https?://(www\.)?(instagram\.com|instagr\.am)/\S+", re.IGNORECASE)


def _download_sync(url: str, dest_dir: str):
    """Синхронная загрузка через yt-dlp (сам yt-dlp не async, поэтому
    вызывается через asyncio.to_thread). Возвращает список путей к
    скачанным файлам (для каруселей — несколько файлов)."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(dest_dir, "%(id)s_%(autonumber)s.%(ext)s"),
        "format": "best",
        "noplaylist": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    files = []
    entries = info.get("entries") if info.get("entries") is not None else [info]
    for entry in entries:
        if entry is None:
            continue
        try:
            filename = ydl.prepare_filename(entry)
        except Exception:
            continue
        if os.path.exists(filename):
            files.append(filename)
    if not files:
        # На случай каруселей ydl.prepare_filename мог промахнуться —
        # просто забираем всё, что реально оказалось в папке.
        files = [os.path.join(dest_dir, f) for f in os.listdir(dest_dir)]
    return files


async def download_instagram_media(url: str):
    """Скачивает пост/рилс/фото по ссылке во временную папку.
    Возвращает (список_путей, temp_dir) — temp_dir нужно удалить после отправки."""
    temp_dir = tempfile.mkdtemp(prefix="insta_")
    try:
        files = await asyncio.to_thread(_download_sync, url, temp_dir)
        return files, temp_dir
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

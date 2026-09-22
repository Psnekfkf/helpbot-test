# -*- coding: utf-8 -*-
"""
Распознавание трека по аудио (Shazam через неофициальную библиотеку
shazamio) и подбор ссылок на него в разных сервисах.

Какие ссылки — ТОЧНОЕ совпадение, а какие — просто ссылка на поиск:
  - Shazam        — точная ссылка (её отдаёт сам Shazam).
  - Apple Music   — точная ссылка, если Shazam её вернул (обычно да,
                    т.к. Shazam принадлежит Apple); иначе — ссылка-поиск.
  - Spotify       — точная ссылка на трек, ЕСЛИ заданы переменные
                    SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET (официальный
                    Spotify Web API, Client Credentials Flow — без входа
                    пользователя, только поиск). Без ключей — ссылка-поиск.
  - YouTube       — первый результат поиска через yt-dlp (ключи не
                    нужны), но это не "официальное" совпадение.
  - Яндекс.Музыка — только ссылка-поиск: у сервиса нет публичного
                    бесплатного API для точного поиска трека.

ВАЖНО: Rust-декодер внутри shazamio (Symphonia) надёжно понимает WAV,
но НЕ умеет нормально читать OGG/Opus — а именно в этом формате
Telegram присылает голосовые. Поэтому перед распознаванием мы сами
конвертируем присланный файл в WAV (см. services/audio_utils.py —
там же лежит и резолвинг самого бинарника ffmpeg через pip-пакет
imageio-ffmpeg, без root/apt/Dockerfile).
"""
from __future__ import annotations

import os
import time
import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import quote

import requests
from shazamio import Shazam

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from services.audio_utils import convert_to_wav

logger = logging.getLogger(__name__)


@dataclass
class RecognizedTrack:
    title: str
    artist: str
    cover_url: str | None
    shazam_url: str | None
    apple_music_url: str
    apple_music_exact: bool
    spotify_url: str
    spotify_exact: bool
    youtube_url: str
    youtube_exact: bool
    yandex_music_url: str


async def recognize_track(audio_path: str) -> RecognizedTrack | None:
    """Распознаёт трек по аудиофайлу. Возвращает None, если Shazam не
    смог найти совпадение (тихая/слишком короткая/зашумлённая запись).

    ВАЖНО: не все версии shazamio поддерживают `async with Shazam()` —
    поэтому используем самый простой и совместимый вариант вызова:
    просто создаём клиент и зовём recognize() напрямую.

    Оборачиваем сетевой вызов к Shazam в таймаут: серверы Shazam иногда
    подвисают, и без этого асинхронная задача может зависнуть надолго
    вместо понятной ошибки."""
    wav_path = await asyncio.to_thread(convert_to_wav, audio_path, 44100)
    try:
        shazam = Shazam()
        result = await asyncio.wait_for(shazam.recognize(wav_path), timeout=25)
    except asyncio.TimeoutError:
        raise RuntimeError("Shazam долго не отвечает — попробуй ещё раз через минуту")
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass

    track = result.get("track") if result else None
    if not track:
        return None

    title = track.get("title") or "Неизвестный трек"
    artist = track.get("subtitle") or "Неизвестный исполнитель"
    cover_url = (track.get("images") or {}).get("coverart")
    shazam_url = track.get("url")
    query = f"{artist} {title}"

    apple_url = _extract_apple_music_url(track)
    spotify_url = _spotify_track_url(query)
    youtube_url = await _youtube_first_result(query)

    return RecognizedTrack(
        title=title,
        artist=artist,
        cover_url=cover_url,
        shazam_url=shazam_url,
        apple_music_url=apple_url or _apple_music_search_url(query),
        apple_music_exact=bool(apple_url),
        spotify_url=spotify_url or _spotify_search_url(query),
        spotify_exact=bool(spotify_url),
        youtube_url=youtube_url or _youtube_search_url(query),
        youtube_exact=bool(youtube_url),
        yandex_music_url=_yandex_search_url(query),
    )


# ---------------- Apple Music (из ответа Shazam) ----------------
def _is_valid_link_url(url: str | None) -> bool:
    """Telegram принимает в инлайн-кнопке ТОЛЬКО http(s)-ссылки. Shazam
    иногда отдаёт диплинки другого вида (например, itms-apps://...) —
    если пропустить такую ссылку в кнопку, Telegram откажется
    отправлять всё сообщение целиком. Поэтому проверяем схему явно."""
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


def _extract_apple_music_url(track: dict) -> str | None:
    """Ищет прямую ссылку на Apple Music/iTunes в ответе Shazam — обычно
    лежит в track.hub.options[].actions[].uri. Возвращаем только
    настоящие http(s)-ссылки (см. _is_valid_link_url) — иначе кнопка с
    ней сломает отправку всего сообщения."""
    hub = track.get("hub") or {}
    for option in hub.get("options", []):
        for action in option.get("actions", []):
            uri = action.get("uri", "")
            if ("music.apple.com" in uri or "itunes.apple.com" in uri) and _is_valid_link_url(uri):
                return uri
    return None


def _apple_music_search_url(query: str) -> str:
    return f"https://music.apple.com/search?term={quote(query)}"


# ---------------- Spotify (официальный Web API, Client Credentials) ----------------
_spotify_token_cache = {"token": None, "expires_at": 0.0}


def _get_spotify_token() -> str | None:
    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET):
        return None
    if _spotify_token_cache["token"] and time.time() < _spotify_token_cache["expires_at"]:
        return _spotify_token_cache["token"]
    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        _spotify_token_cache["token"] = data["access_token"]
        _spotify_token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 30
        return _spotify_token_cache["token"]
    except Exception as e:
        logger.error(f"Не удалось получить токен Spotify: {e}")
        return None


def _spotify_track_url(query: str) -> str | None:
    token = _get_spotify_token()
    if not token:
        return None
    try:
        response = requests.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": 1},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            return items[0]["external_urls"]["spotify"]
    except Exception as e:
        logger.error(f"Ошибка поиска в Spotify: {e}")
    return None


def _spotify_search_url(query: str) -> str:
    return f"https://open.spotify.com/search/{quote(query)}"


# ---------------- YouTube (через yt-dlp, без ключей) ----------------
async def _youtube_first_result(query: str) -> str | None:
    import yt_dlp

    def _search():
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries") if info and info.get("entries") is not None else [info]
            for entry in entries:
                if entry and entry.get("webpage_url"):
                    return entry["webpage_url"]
        return None

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.error(f"Ошибка поиска на YouTube: {e}")
        return None


def _youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote(query)}"


# ---------------- Яндекс.Музыка (только поиск) ----------------
def _yandex_search_url(query: str) -> str:
    return f"https://music.yandex.ru/search?text={quote(query)}"

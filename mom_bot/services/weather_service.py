# -*- coding: utf-8 -*-
"""
Обёртка над OpenWeather API.
"""
from __future__ import annotations

import aiohttp

from config import OPENWEATHER_KEY, CITY


async def get_weather(city: str = None) -> str | None:
    """Возвращает готовую строку с погодой или None при любой ошибке."""
    city = city or CITY
    try:
        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_KEY}&units=metric&lang=ru"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                desc = data["weather"][0]["description"]
                wind = data["wind"]["speed"]
                return (
                    f"🌡 {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
                    f"{desc.capitalize()}\n💨 Ветер {wind} м/с"
                )
    except Exception:
        return None

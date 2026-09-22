# -*- coding: utf-8 -*-
"""
Работа с OpenRouter: получение списка бесплатных моделей, отправка
запросов с автоматическим переключением между моделями при ошибках,
и хранение истории диалогов по пользователям (в памяти процесса).
"""
from __future__ import annotations

import logging
import requests

from config import OPENROUTER_KEY, OPENROUTER_URL
from content import AI_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "google/gemma-3-27b-it:free",
    "google/gemini-2.5-flash-preview:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


def get_free_models():
    """Получает список бесплатных моделей с OpenRouter, либо запасной
    список, если API недоступен."""
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            timeout=5,
        )
        if response.status_code == 200:
            models = response.json()
            free_models = [
                m["id"] for m in models.get("data", []) if ":free" in m.get("id", "")
            ]
            free_models.sort(key=lambda x: (
                0 if "google" in x else
                1 if "meta" in x else
                2 if "mistral" in x else 3
            ))
            logger.info(f"✅ Найдено {len(free_models)} бесплатных моделей")
            return free_models
    except Exception as e:
        logger.error(f"Не удалось получить список моделей: {e}")

    return FALLBACK_MODELS


class ConversationStore:
    """Хранит историю переписки с ИИ по каждому пользователю (в памяти).

    ВАЖНО: при перезапуске бота история теряется (это было и в исходной
    версии) — см. пункт про сохранение истории в идеях по улучшению.
    """

    MAX_MESSAGES = 20

    def __init__(self):
        self._histories: dict[int, list[dict]] = {}

    def get(self, user_id: int) -> list[dict]:
        if user_id not in self._histories:
            self._histories[user_id] = [AI_SYSTEM_PROMPT.copy()]
        return self._histories[user_id]

    def append(self, user_id: int, role: str, content: str):
        history = self.get(user_id)
        history.append({"role": role, "content": content})
        if len(history) > self.MAX_MESSAGES:
            self._histories[user_id] = [AI_SYSTEM_PROMPT.copy()] + history[-(self.MAX_MESSAGES - 1):]

    def clear(self, user_id: int):
        self._histories.pop(user_id, None)


class OpenRouterClient:
    """Пробует бесплатные модели по очереди, пока одна не ответит."""

    def __init__(self):
        self.models = get_free_models()
        self.current_index = 0

    def ask(self, messages: list[dict]) -> str:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "MomAssistantBot",
            "Content-Type": "application/json",
        }
        errors = []
        for i in range(len(self.models)):
            model_index = (self.current_index + i) % len(self.models)
            model = self.models[model_index]
            data = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 1000}
            try:
                logger.info(f"🔄 Пробую модель: {model}")
                response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=15)
                if response.status_code == 200:
                    self.current_index = model_index
                    logger.info(f"✅ Успех: {model}")
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code == 429:
                    errors.append(f"⏳ {model}: лимит")
                    logger.warning(f"⏳ {model}: лимит исчерпан")
                    continue
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", str(response.status_code))
                    except Exception:
                        error_msg = f"HTTP {response.status_code}"
                    errors.append(f"❌ {model}: {error_msg}")
                    logger.error(f"❌ {model}: {error_msg}")
                    continue
            except Exception as e:
                errors.append(f"💥 {model}: {str(e)[:50]}")
                logger.error(f"💥 {model}: {e}")
                continue

        raise RuntimeError("Все модели недоступны:\n" + "\n".join(errors[:5]))


# Единые на весь процесс инстансы — используются во всех хендлерах.
conversations = ConversationStore()
ai_client = OpenRouterClient()


SUMMARY_SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты помогаешь маме быстро понять суть длинного голосового "
        "сообщения от подруги или родственника, не слушая его целиком. "
        "Сделай короткий пересказ на русском языке, 3-5 предложений: "
        "главная суть, важные детали (даты, время, просьбы, имена), "
        "настроение сообщения. Без лишних вступлений типа 'В сообщении "
        "говорится, что' — пиши сразу по делу."
    ),
}


def summarize_text(text: str) -> str:
    """Короткий пересказ длинного текста (уже распознанного из
    голосового) через тот же OpenRouter-клиент. Это одноразовый вызов,
    без привязки к истории диалога конкретного пользователя."""
    messages = [SUMMARY_SYSTEM_PROMPT, {"role": "user", "content": text}]
    return ai_client.ask(messages)

# -*- coding: utf-8 -*-
"""
Работа с данными о «цветах дня»: загрузка из colors_data.json (183 даты,
июнь–ноябрь 2026) и подбор цветов/названия месяца по дате.

Сами цвета вынесены из кода в отдельный JSON-файл — редактировать
календарь (добавить новый месяц, поправить одну дату) теперь можно без
переписывания Python.
"""
import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.join(_BASE_DIR, "colors_data.json")

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    COLORS = json.load(_f)

_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def get_colors_for_date(date_obj):
    """date_obj — любой объект с .strftime (datetime/date)."""
    date_str = date_obj.strftime("%Y-%m-%d")
    return COLORS.get(date_str)


def get_month_name(month: int) -> str:
    return _MONTHS.get(month, "")

from datetime import datetime

from langchain_core.tools import tool

_WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


@tool
def get_current_datetime() -> dict:
    """Текущие дата и время. Схема для модели — schemas/get_current_datetime.json."""
    now = datetime.now().astimezone()
    return {"datetime": now.isoformat(timespec="seconds"), "weekday": _WEEKDAYS[now.weekday()]}

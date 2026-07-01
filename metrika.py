"""
Модуль для получения статистики из Яндекс.Метрика API отчётов
Документация: https://yandex.ru/dev/metrika/doc/api2/api_v1/intro.html
"""

import requests

METRIKA_API_URL = "https://api-metrika.yandex.net/stat/v1/data"
METRIKA_GOALS_API_URL = "https://api-metrika.yandex.net/management/v1/counter/{counter_id}/goals"


def list_goals(token: str, counter_id: str) -> list[dict]:
    headers = {"Authorization": f"OAuth {token}"}
    resp = requests.get(METRIKA_GOALS_API_URL.format(counter_id=counter_id), headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Метрика API ошибка {resp.status_code} при получении целей: {resp.text}")
    data = resp.json()
    return data.get("goals", [])


def get_stats(token: str, counter_id: str, date_from: str, date_to: str,
              goal_id: str = None) -> list[dict]:
    """
    Запрашивает сессии и отказы из Метрики по дням.
    Возвращает список словарей: date, sessions, bounce_rate
    """
    headers = {"Authorization": f"OAuth {token}"}
    metrics_list = ["ym:s:visits", "ym:s:bounceRate"]

    if goal_id:
        goal_exists = any(str(goal.get("id")) == str(goal_id) for goal in list_goals(token, counter_id))
        if not goal_exists:
            raise Exception(
                f"Цель {goal_id} не найдена в счётчике {counter_id}. Проверьте ID цели в Метрике."
            )
        metrics_list.append(f"ym:s:goal{goal_id}reaches")

    params = {
        "id":         counter_id,
        "date1":      date_from,
        "date2":      date_to,
        "dimensions": "ym:s:date",
        "metrics":    ",".join(metrics_list),
        "limit":      365,
    }

    resp = requests.get(METRIKA_API_URL, headers=headers, params=params)
    if resp.status_code != 200:
        raise Exception(f"Метрика API ошибка {resp.status_code}: {resp.text}")

    data = resp.json()
    rows = []
    for item in data.get("data", []):
        date_val = item["dimensions"][0]["name"]  # "2025-12-16"
        metrics  = item["metrics"]
        row = {
            "date":        date_val,
            "sessions":    int(metrics[0]) if len(metrics) > 0 else 0,
            "bounce_rate": round(float(metrics[1]), 1) if len(metrics) > 1 else 0.0,
        }
        if goal_id:
            row["goal_conversions"] = int(metrics[2]) if len(metrics) > 2 else 0
        rows.append(row)

    return rows

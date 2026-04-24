"""
Модуль для получения статистики из Яндекс.Метрика API отчётов
Документация: https://yandex.ru/dev/metrika/doc/api2/api_v1/intro.html
"""

import requests

METRIKA_API_URL = "https://api-metrika.yandex.net/stat/v1/data"

def get_stats(token: str, counter_id: str, date_from: str, date_to: str, goal_id: str = None) -> dict:
    """
    Запрашивает сессии, отказы и конкретную цель из Метрики по её ID
    """
    headers = {"Authorization": f"OAuth {token}"}
    metrics_list = ["ym:s:visits", "ym:s:bounceRate"]
    
    if goal_id:
        metrics_list.append(f"ym:s:goal{goal_id}reaches")

    params = {
        "id":      counter_id,
        "date1":   date_from,
        "date2":   date_to,
        "metrics": ",".join(metrics_list),
        "limit":   1,
    }

    resp = requests.get(METRIKA_API_URL, headers=headers, params=params)
    if resp.status_code != 200:
        raise Exception(f"Метрика API ошибка {resp.status_code}: {resp.text}")

    data = resp.json()
    totals = data.get("totals", [0]*len(metrics_list))
    
    result = {
        "sessions":   int(totals[0]) if len(totals) > 0 else 0,
        "bounceRate": round(float(totals[1]), 1) if len(totals) > 1 else 0.0,
    }
    
    if goal_id:
        result["goal_conversions"] = int(totals[2]) if len(totals) > 2 else 0
        
    return result

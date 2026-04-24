import requests
import json
import time
from datetime import date, timedelta

DIRECT_API_URL = "https://api.direct.yandex.com/json/v5/reports"

def get_stats(token: str, client_login: str, date_from: str, date_to: str,
              campaign_ids: list = None) -> dict:
    """
    Запрашивает статистику из Яндекс.Директ.
    Возвращает словарь: impressions, clicks, cost, conversions
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "ru",
        "Content-Type": "application/json",
        "processingMode": "auto",
    }
    if client_login:
        headers["Client-Login"] = client_login

    selection = {"DateFrom": date_from, "DateTo": date_to}
    if campaign_ids:
        selection["CampaignIds"] = campaign_ids

    body = {
        "params": {
            "SelectionCriteria": selection,
            "FieldNames": ["Impressions", "Clicks", "Cost", "Conversions"],
            "ReportName": f"report_{date_from}",
            "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
            "IncludeDiscount": "NO",
        }
    }

    for attempt in range(5):
        resp = requests.post(DIRECT_API_URL, headers=headers, data=json.dumps(body))
        if resp.status_code == 200:
            return _parse_tsv(resp.text)
        elif resp.status_code == 201 or resp.status_code == 202:
            time.sleep(10)
            continue
        else:
            raise Exception(f"Директ API ошибка {resp.status_code}: {resp.text}")

    raise Exception("Директ API: превышено время ожидания отчёта")


def _parse_tsv(tsv_text: str) -> dict:
    lines = [l for l in tsv_text.strip().splitlines() if l and not l.startswith("Report")]
    result = {"impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0}
    if len(lines) < 2:
        return result

    headers = lines[0].split("\t")
    col = {h: i for i, h in enumerate(headers)}

    for line in lines[1:]:
        if line.startswith("Total") or line.startswith("Итого"):
            parts = line.split("\t")
            result["impressions"]  += int(parts[col.get("Impressions", 0)] or 0)
            result["clicks"]       += int(parts[col.get("Clicks", 0)] or 0)
            result["cost"]         += float(parts[col.get("Cost", 0)] or 0) / 1_000_000
            result["conversions"]  += int(parts[col.get("Conversions", 0)] or 0)
            break

    return result

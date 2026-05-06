import requests
import json
import time

DIRECT_API_URL = "https://api.direct.yandex.com/json/v5/reports"


def get_stats(token: str, client_login: str, date_from: str, date_to: str,
              campaign_ids: list = None) -> list[dict]:
    """
    Запрашивает статистику из Яндекс.Директ по дням.
    Возвращает список словарей: date, impressions, clicks, cost, conversions
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
            "FieldNames": ["Date", "Impressions", "Clicks", "Cost", "Conversions"],
            "ReportName": f"report_{client_login}_{date_from}_{date_to}",
            "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
            "IncludeDiscount": "NO",
        }
    }

    for attempt in range(5):
        resp = requests.post(DIRECT_API_URL, headers=headers, data=json.dumps(body))
        resp.encoding = "utf-8"

        if resp.status_code == 200:
            return _parse_tsv(resp.text)
        elif resp.status_code in (201, 202):
            time.sleep(10)
            continue
        else:
            raise Exception(f"Директ API ошибка {resp.status_code}: {resp.text}")

    raise Exception("Директ API: превышено время ожидания отчёта")


def _parse_tsv(tsv_text: str) -> list[dict]:
    lines = tsv_text.strip().splitlines()

    # Ищем строку заголовков по наличию "Impressions"
    header_idx = next((i for i, l in enumerate(lines) if "Impressions" in l), None)
    if header_idx is None:
        return []

    headers = lines[header_idx].split("\t")
    col = {h: i for i, h in enumerate(headers)}

    # Агрегируем по дате — несколько кампаний за один день суммируются в одну строку
    by_date: dict[str, dict] = {}

    for line in lines[header_idx + 1:]:
        if not line or line.startswith("Total rows:") or \
                line.startswith("Total") or line.startswith("Итого"):
            continue

        parts = line.split("\t")
        try:
            if parts[col["Impressions"]] == "Impressions":
                continue
            date_val = parts[col["Date"]]
            if date_val not in by_date:
                by_date[date_val] = {"date": date_val, "impressions": 0,
                                     "clicks": 0, "cost": 0.0, "conversions": 0}
            by_date[date_val]["impressions"] += int(parts[col["Impressions"]] or 0)
            by_date[date_val]["clicks"]      += int(parts[col["Clicks"]] or 0)
            by_date[date_val]["cost"]        += float(parts[col["Cost"]] or 0) / 1_000_000
            by_date[date_val]["conversions"] += int(parts[col["Conversions"]] or 0)
        except (IndexError, ValueError, KeyError):
            continue

    return sorted(by_date.values(), key=lambda r: r["date"])

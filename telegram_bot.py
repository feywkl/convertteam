"""
Простой Telegram-бот для запуска выгрузки отчётов.

Примеры:
  /report metall-cvt 2026-05-01
  /report metall-cvt 2026-05
  /report metall-cvt 01.01.2026-02.01.2026

Период:
  - одна дата => один день
  - YYYY-MM => весь месяц
  - диапазон дат => inclusive range
"""

from __future__ import annotations

import calendar
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests

import config
from report_core import collect_data, write_rows_to_sheet


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_CHAT_IDS = {
    x.strip() for x in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if x.strip()
}

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@dataclass
class Period:
    date_from: str
    date_to: str
    label: str


def _send_message(chat_id: int | str, text: str):
    requests.post(f"{API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text})


def _parse_client(client_token: str) -> tuple[str, str]:
    normalized = re.sub(r"[\s_-]+", "", client_token.strip().lower())

    for client_key, client_cfg in config.PROJECTS.items():
        key_norm = re.sub(r"[\s_-]+", "", client_key.lower())
        sheet_norm = re.sub(r"[\s_-]+", "", str(client_cfg.get("worksheet_name", "")).lower())
        if normalized == key_norm or normalized == sheet_norm:
            return client_key, client_cfg.get("worksheet_name", client_key)

    raise KeyError(f"Клиент '{client_token}' не найден в clients.json")


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Неверный формат даты")


def _parse_period(period_token: str) -> Period:
    token = period_token.strip().lower()
    today = date.today()

    if token in {"today", "day", "сегодня"}:
        return Period(today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), today.strftime("%d.%m.%Y"))

    if token in {"yesterday", "вчера"}:
        y = today - timedelta(days=1)
        return Period(y.strftime("%Y-%m-%d"), y.strftime("%Y-%m-%d"), y.strftime("%d.%m.%Y"))

    month_match = re.fullmatch(r"month:(\d{4})-(\d{2})", token)
    if token == "month":
        year, month = today.year, today.month
    elif month_match:
        year, month = int(month_match.group(1)), int(month_match.group(2))
    else:
        year = month = None

    if year is not None and month is not None:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        label = f"{start.strftime('%d.%m.%Y')}–{end.strftime('%d.%m.%Y')}"
        return Period(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), label)

    range_match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})\s*[-:]\s*(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})",
        period_token.strip(),
    )
    if range_match:
        start_date = _parse_date(range_match.group(1))
        end_date = _parse_date(range_match.group(2))
        if start_date > end_date:
            raise ValueError("Дата начала не может быть позже даты конца")
        label = f"{start_date.strftime('%d.%m.%Y')}–{end_date.strftime('%d.%m.%Y')}"
        return Period(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), label)

    single_date = _parse_date(period_token)
    return Period(single_date.strftime("%Y-%m-%d"), single_date.strftime("%Y-%m-%d"), single_date.strftime("%d.%m.%Y"))


def _help_text() -> str:
    return (
        "Команда:\n"
        "/report <client_id> <period>\n\n"
        "Период можно задавать так:\n"
        "- одна дата: 2026-05-06 или 06.05.2026\n"
        "- месяц: 2026-05 или month:2026-05\n"
        "- диапазон: 01.01.2026-02.01.2026 или 2026-01-01:2026-01-31\n\n"
        "Пример:\n"
        "/report metall-cvt 01.01.2026-02.01.2026"
    )


def _is_allowed_chat(chat_id: int | str) -> bool:
    return not TELEGRAM_ALLOWED_CHAT_IDS or str(chat_id) in TELEGRAM_ALLOWED_CHAT_IDS


def _handle_report(chat_id: int, args: list[str]):
    if len(args) < 2:
        _send_message(chat_id, _help_text())
        return

    client_token = args[0]
    period_token = " ".join(args[1:]).strip()

    try:
        client_key, worksheet_name = _parse_client(client_token)
        period = _parse_period(period_token)
    except Exception as exc:
        _send_message(chat_id, f"Ошибка: {exc}\n\n{_help_text()}")
        return

    try:
        _send_message(chat_id, f"Запускаю отчёт для {client_key} за {period.label}...")
        rows = collect_data(period.date_from, period.date_to, client_key=client_key)
        written = write_rows_to_sheet(rows)
        _send_message(
            chat_id,
            f"Готово. Клиент: {client_key} ({worksheet_name})\nПериод: {period.label}\nВыгружено строк: {written}",
        )
    except Exception as exc:
        _send_message(chat_id, f"Не удалось сформировать отчёт: {exc}")


def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    offset = 0

    while True:
        try:
            response = requests.get(
                f"{API_BASE}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=40,
            )
            response.raise_for_status()
            payload = response.json()

            for update in payload.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if not message:
                    continue

                chat = message.get("chat", {})
                chat_id = chat.get("id")
                if chat_id is None or not _is_allowed_chat(chat_id):
                    continue

                text = (message.get("text") or "").strip()
                if not text:
                    continue

                if text.startswith("/start") or text.startswith("/help"):
                    _send_message(chat_id, _help_text())
                    continue

                if text.startswith("/report"):
                    parts = text.split(maxsplit=2)
                    _handle_report(chat_id, parts[1:])
                    continue

                fallback_parts = text.split(maxsplit=1)
                if len(fallback_parts) == 2:
                    _handle_report(chat_id, fallback_parts)
                    continue

                _send_message(chat_id, _help_text())

        except Exception as exc:
            print(f"Telegram bot error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
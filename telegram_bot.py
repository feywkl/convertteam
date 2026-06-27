"""
Telegram-бот для запуска выгрузки отчётов с управлением администраторами.

Команды пользователя:
  /report <client_id> <period>  — запустить отчёт

Админ-команды:
  /myid                        — показать свой chat_id и username
  /addadmin <chat_id|@ник>     — добавить администратора
  /removeadmin <chat_id>       — удалить администратора
  /admins                      — список администраторов
"""

from __future__ import annotations

import calendar
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

import config
from report_core import collect_data, write_rows_to_sheet


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_CHAT_IDS = {
    x.strip() for x in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if x.strip()
}

ALLOWLIST_FILE = Path(__file__).with_name("telegram_allowlist.json")
ADMINS_FILE = Path(__file__).with_name("admins.json")
USERS_REGISTRY_FILE = Path(__file__).with_name("users_registry.json")

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@dataclass
class Period:
    date_from: str
    date_to: str
    label: str


@dataclass
class Admin:
    chat_id: str
    username: str = ""


def _send_message(chat_id: int | str, text: str):
    requests.post(f"{API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text})


def _load_admins() -> dict[str, Admin]:
    """Загрузить список администраторов из файла."""
    if ADMINS_FILE.exists():
        try:
            data = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
            return {str(k): Admin(**v) if isinstance(v, dict) else v for k, v in data.items()}
        except Exception:
            pass
    return {}


def _save_admins(admins: dict[str, Admin]):
    """Сохранить список администраторов."""
    data = {k: asdict(v) for k, v in admins.items()}
    ADMINS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_allowlist() -> set[str]:
    """Загрузить разрешённые chat_id."""
    file_ids: set[str] = set()
    if ALLOWLIST_FILE.exists():
        try:
            data = json.loads(ALLOWLIST_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                file_ids = {str(item) for item in data}
        except Exception:
            file_ids = set()
    return file_ids | TELEGRAM_ALLOWED_CHAT_IDS


def _save_allowlist(chat_ids: set[str]):
    """Сохранить разрешённые chat_id."""
    ALLOWLIST_FILE.write_text(json.dumps(sorted(chat_ids), ensure_ascii=False, indent=2), encoding="utf-8")


def _load_users_registry() -> dict[str, str]:
    """Загрузить маппинг username -> chat_id."""
    if USERS_REGISTRY_FILE.exists():
        try:
            return json.loads(USERS_REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_users_registry(registry: dict[str, str]):
    """Сохранить маппинг username -> chat_id."""
    USERS_REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _register_user(chat_id: str, username: str = ""):
    """Зарегистрировать пользователя."""
    if not username:
        return
    registry = _load_users_registry()
    registry[f"@{username.lstrip('@')}"] = chat_id
    _save_users_registry(registry)


def _is_admin(chat_id: int | str) -> bool:
    """Проверить, является ли пользователь администратором."""
    return str(chat_id) in _load_admins()


def _is_allowed_chat(chat_id: int | str) -> bool:
    """Проверить, разрешён ли доступ пользователю."""
    return str(chat_id) in _load_allowlist() or _is_admin(chat_id)


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
        "📋 Команда:\n"
        "/report <client_id> <period>\n\n"
        "📅 Период:\n"
        "- одна дата: 2026-05-06 или 06.05.2026\n"
        "- месяц: 2026-05 или month:2026-05\n"
        "- диапазон: 01.01.2026-02.01.2026\n\n"
        "Пример:\n"
        "/report metall-cvt 01.01.2026-02.01.2026"
    )


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
        _send_message(chat_id, f"❌ Ошибка: {exc}\n\n{_help_text()}")
        return

    try:
        _send_message(chat_id, f"⏳ Запускаю отчёт для {client_key} за {period.label}...")
        rows = collect_data(period.date_from, period.date_to, client_key=client_key)
        written = write_rows_to_sheet(rows)
        _send_message(
            chat_id,
            f"✅ Готово!\n📊 Клиент: {client_key} ({worksheet_name})\n📅 Период: {period.label}\n📈 Выгружено строк: {written}",
        )
    except Exception as exc:
        _send_message(chat_id, f"❌ Ошибка: {exc}")


def _handle_admin(chat_id: int, command: str, args: list[str]):
    if not _is_admin(chat_id):
        _send_message(chat_id, "❌ У вас нет прав администратора.")
        return

    command = command.lower()

    if command == "/myid":
        _send_message(chat_id, f"👤 Ваш chat_id: `{chat_id}`")
        return

    if command == "/admins":
        admins = _load_admins()
        if not admins:
            _send_message(chat_id, "📭 Список администраторов пуст.")
            return
        lines = ["👨‍💼 Администраторы:"]
        for admin_id, admin in sorted(admins.items()):
            username_str = f" (@{admin.username})" if admin.username else ""
            lines.append(f"  • {admin_id}{username_str}")
        _send_message(chat_id, "\n".join(lines))
        return

    if command == "/addadmin":
        if not args:
            _send_message(chat_id, "❌ Укажите chat_id или @ник\n\nПример:\n/addadmin 123456789\nили\n/addadmin @username")
            return
        identifier = args[0].strip()
        admins = _load_admins()
        username = ""

        if identifier.startswith("@"):
            registry = _load_users_registry()
            found_chat_id = registry.get(identifier)
            if not found_chat_id:
                _send_message(chat_id, f"❌ Пользователь {identifier} не найден. Попросите его написать боту хотя бы один раз.")
                return
            identifier = found_chat_id
            username = identifier.lstrip("@")

        if identifier in admins:
            _send_message(chat_id, f"ℹ️ chat_id {identifier} уже администратор.")
            return

        admins[identifier] = Admin(chat_id=identifier, username=username)
        _save_admins(admins)
        _send_message(chat_id, f"✅ chat_id {identifier} добавлен в администраторы.")
        return

    if command == "/removeadmin":
        if not args:
            _send_message(chat_id, "❌ Укажите chat_id\n\nПример:\n/removeadmin 123456789")
            return
        admin_id = args[0].strip()
        admins = _load_admins()

        if admin_id not in admins:
            _send_message(chat_id, f"❌ chat_id {admin_id} не является администратором.")
            return

        del admins[admin_id]
        _save_admins(admins)
        _send_message(chat_id, f"✅ chat_id {admin_id} удалён из администраторов.")
        return


def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN не задан")

    offset = 0
    print("🤖 Telegram-бот запущен...")

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
                chat_username = chat.get("username", "")

                if chat_id is None:
                    continue

                # Регистрируем пользователя
                _register_user(str(chat_id), chat_username)

                # Проверяем доступ
                if not _is_allowed_chat(chat_id):
                    continue

                text = (message.get("text") or "").strip()
                if not text:
                    continue

                if text.startswith("/start") or text.startswith("/help"):
                    _send_message(chat_id, _help_text())
                    continue

                if text.startswith("/myid") or text.startswith("/addadmin") or text.startswith("/removeadmin") or text.startswith("/admins"):
                    parts = text.split(maxsplit=1)
                    command = parts[0]
                    args = parts[1].split() if len(parts) > 1 else []
                    _handle_admin(chat_id, command, args)
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
            print(f"❌ Telegram bot error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()

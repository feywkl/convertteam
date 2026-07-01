import os
import json
import re
from datetime import date, timedelta
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Токены управляющего аккаунта (из .env / GitHub Secrets)
DIRECT_TOKEN  = os.getenv("DIRECT_TOKEN", "")
METRIKA_TOKEN = os.getenv("METRIKA_TOKEN", "")
METRIKA_COUNTER_ID = os.getenv("METRIKA_COUNTER_ID", "").strip()

# Период отчёта — по умолчанию за вчерашний день (для ежедневного запуска)
yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
DATE_FROM = os.getenv("DATE_FROM") or yesterday
DATE_TO   = os.getenv("DATE_TO") or yesterday

_clients_file = os.path.join(os.path.dirname(__file__), "clients.json")
PROJECTS = {}

if os.path.exists(_clients_file):
    try:
        with open(_clients_file, encoding="utf-8") as _f:
            _content = _f.read().strip()
        if _content:
            data = json.loads(_content)
            if isinstance(data, list):
                PROJECTS = {c["name"]: c for c in data}
            elif isinstance(data, dict):
                PROJECTS = data
    except Exception as e:
        print(f"ОШИБКА при чтении clients.json: {e}")


def _normalize_client_token(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value.strip().lower())


def resolve_project(client_token: str | None):
    if not client_token:
        raise KeyError("Клиент не указан")

    normalized = _normalize_client_token(client_token)

    for client_key, client_cfg in PROJECTS.items():
        key_norm = _normalize_client_token(client_key)
        sheet_norm = _normalize_client_token(str(client_cfg.get("worksheet_name", "")))
        direct_login_norm = _normalize_client_token(str(client_cfg.get("direct_login", "")))
        if normalized == key_norm or normalized == sheet_norm or normalized == direct_login_norm:
            return client_key, client_cfg

    if not METRIKA_COUNTER_ID:
        raise KeyError(
            f"Клиент '{client_token}' не найден, а METRIKA_COUNTER_ID не задан"
        )

    return client_token.strip(), {
        "direct_login": client_token.strip(),
        "metrika_counter": METRIKA_COUNTER_ID,
        "worksheet_name": client_token.strip(),
    }

# Настройки Google Sheets
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")

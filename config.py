import os
import json
from datetime import date, timedelta
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Токены управляющего аккаунта (из .env / GitHub Secrets)
DIRECT_TOKEN  = os.getenv("DIRECT_TOKEN", "")
METRIKA_TOKEN = os.getenv("METRIKA_TOKEN", "")

# Период отчёта — по умолчанию за вчерашний день (для ежедневного запуска)
yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
DATE_FROM = yesterday
DATE_TO   = yesterday

_clients_file = os.path.join(os.path.dirname(__file__), "clients.json")
try:
    with open(_clients_file, encoding="utf-8") as _f:
        _content = _f.read()
        if not _content.strip():
            print("ОШИБКА: Файл clients.json пуст! Проверьте секрет CLIENTS в GitHub Actions.")
            PROJECTS = {}
        else:
            PROJECTS = {c["name"]: c for c in json.loads(_content)}
except Exception as e:
    print(f"ОШИБКА при чтении файла clients.json: {e}")
    PROJECTS = {}

# Настройки Google Sheets
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")

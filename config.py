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

# Список клиентов читается из clients.json — добавляй туда новых клиентов,
# не трогая код. Формат каждого клиента:
# { "name", "direct_login", "metrika_counter", "metrika_goal_id" }
_clients_file = os.path.join(os.path.dirname(__file__), "clients.json")
with open(_clients_file, encoding="utf-8") as _f:
    PROJECTS = {c["name"]: c for c in json.load(_f)}

# Настройки Google Sheets
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")

"""
Главный скрипт: собирает данные из Яндекс.Директ и Яндекс.Метрики
и выгружает их в Google Таблицу.

Запуск:  python3 generate_report.py
"""

import os

import config
from report_core import collect_data, write_rows_to_sheet


REPORT_CLIENT = os.getenv("REPORT_CLIENT", "").strip() or None


def main():
    print(f"Период отчёта: {config.DATE_FROM} → {config.DATE_TO}")
    print("✅ Яндекс.Директ: боевой режим")
    print("✅ Яндекс.Метрика: боевой режим\n")

    if not config.GOOGLE_SHEET_URL:
        print("⚠️  Ссылка на Google Таблицу (GOOGLE_SHEET_URL) не заполнена в config.py")
        print("   Будут выведены только результаты работы в консоль.\n")

    print("Сбор данных...")
    rows = collect_data(config.DATE_FROM, config.DATE_TO, client_key=REPORT_CLIENT)

    if not config.GOOGLE_SHEET_URL:
        print("\n📝 Данные для выгрузки (Google Sheet не настроен):")
        for row in rows:
            print(row)
        return

    print("\nПодключение к Google Таблицам...")
    try:
        written = write_rows_to_sheet(rows)
        print(f"✅ Успешно выгружено {written} строк в таблицу")
    except Exception as exc:
        print(f"❌ Ошибка выгрузки: {exc}")


if __name__ == "__main__":
    main()
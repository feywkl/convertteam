"""
Главный скрипт: собирает данные из Яндекс.Директ и Яндекс.Метрики
и выгружает их в Google Таблицу.

Запуск:  python3 generate_report.py
"""

import sys
import os
from datetime import date
import gspread

sys.path.insert(0, os.path.dirname(__file__))
import config
import direct
import metrika

GOOGLE_READY = bool(config.GOOGLE_SHEET_URL)

print(f"Период отчёта: {config.DATE_FROM} → {config.DATE_TO}")
print("✅ Яндекс.Директ: боевой режим")
print("✅ Яндекс.Метрика: боевой режим\n")

if not GOOGLE_READY:
    print("⚠️  Ссылка на Google Таблицу (GOOGLE_SHEET_URL) не заполнена в config.py")
    print("   Будут выведены только результаты работы в консоль.\n")


def collect_data() -> list[dict]:
    """Собирает данные по всем проектам из конфига."""
    rows = []
    for project_name in config.PROJECTS:
        print(f"  → {project_name} ...", end=" ")

        d = direct.get_stats(
            token=config.DIRECT_TOKEN,
            client_login=config.DIRECT_CLIENT_LOGIN,
            date_from=config.DATE_FROM,
            date_to=config.DATE_TO,
        )

        m = metrika.get_stats(
            token=config.METRIKA_TOKEN,
            counter_id=config.METRIKA_COUNTER_ID,
            date_from=config.DATE_FROM,
            date_to=config.DATE_TO,
            goal_id=config.METRIKA_GOAL_ID
        )

        rows.append({
            "project":     project_name,
            "impressions": d["impressions"],
            "clicks":      d["clicks"],
            "cost":        d["cost"],
            "conversions": d["conversions"],
            "sessions":    m["sessions"],
            "bounce_rate": m["bounceRate"],
        })
        print("OK")

    return rows


def export_to_google_sheets(rows: list[dict]):
    if not GOOGLE_READY:
        print("\n📝 Данные для выгрузки (Google Sheet не настроен):")
        for r in rows:
            print(r)
        return

    print("\nПодключение к Google Таблицам...")
    try:
        gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)
        sh = gc.open_by_url(config.GOOGLE_SHEET_URL)
        ws = sh.sheet1  # Берём первый лист, либо можно по имени: sh.worksheet("Название")
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        print("Убедитесь, что файл credentials.json лежит в папке, а в таблице выдан доступ email'у из этого файла-ключа.")
        return

    export_dt = date.today().strftime('%d.%m.%Y')
    
    # Проверяем, есть ли уже заголовки в таблице. Если таблица пустая - добавляем их.
    existing_data = ws.get_all_values()
    # gspread может вернуть [[]] для пустой таблицы
    if not existing_data or not any(existing_data[0]):
        print("Таблица пустая, добавляем заголовки...")
        headers = [
            "Дата", 
            "Расход, в руб,", 
            "Количество показов", 
            "Кол-во кликов", 
            "CPC", 
            "CTR (количество показов к кликам)", 
            "Кол-во конверсий", 
            "Стоимость конверсии (CPA)",
            "Конверсия сайта % (CR)"
        ]
        ws.append_row(headers)

    print("Добавление новых строк: ")
    # Собираем все строки для выгрузки массивом
    data_to_append = []
    
    for row in rows:
        imp = row["impressions"]
        clk = row["clicks"]
        cost = row["cost"]
        conv = row["conversions"]
        sess = row["sessions"]
        bnc = row["bounce_rate"]

        ctr = round((clk / imp * 100) if imp > 0 else 0, 2)
        cpc = round((cost / clk) if clk > 0 else 0, 2)
        # Рассчитываем CPA и CR (если конверсии берем из Директа: row["conversions"])
        conv = row["conversions"]
        sess = row["sessions"]
        cpa = round((cost / conv) if conv > 0 else 0, 2)
        cr = round((conv / sess * 100) if sess > 0 else 0, 2)

        # Новая структура: 1 колонка конверсии
        data_to_append.append([
            export_dt,                   # Дата
            f"р.{cost}".replace('.', ','), # Расход, в руб,
            imp,                         # Количество показов
            clk,                         # Кол-во кликов
            f"р.{cpc}".replace('.', ','),  # CPC
            f"{ctr}%".replace('.', ','),   # CTR (количество показов к кликам)
            conv,                        # Кол-во конверсий
            f"р.{cpa}".replace('.', ','),  # Стоимость конверсии (CPA)
            f"{cr}%".replace('.', ',')     # Конверсия сайта % (CR)
        ])

    # Пакетная выгрузка
    ws.append_rows(data_to_append, value_input_option='USER_ENTERED')
    print(f"✅ Успешно выгружено {len(data_to_append)} строк в таблицу: {sh.title}")


if __name__ == "__main__":
    print("Сбор данных...")
    rows = collect_data()
    export_to_google_sheets(rows)

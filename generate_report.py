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
    """Собирает данные по всем клиентам из конфига, по дням."""
    rows = []

    for project_name, cfg in config.PROJECTS.items():
        print(f"  → {project_name} ...", end=" ")

        try:
            direct_rows  = direct.get_stats(
                token=config.DIRECT_TOKEN,
                client_login=cfg["direct_login"],
                date_from=config.DATE_FROM,
                date_to=config.DATE_TO,
            )

            metrika_rows = metrika.get_stats(
                token=config.METRIKA_TOKEN,
                counter_id=cfg["metrika_counter"],
                date_from=config.DATE_FROM,
                date_to=config.DATE_TO,
                goal_id=cfg["metrika_goal_id"]
            )

            # Индексируем Метрику по дате для быстрого поиска
            metrika_by_date = {r["date"]: r for r in metrika_rows}

            for d in direct_rows:
                m = metrika_by_date.get(d["date"], {"sessions": 0, "bounce_rate": 0.0})
                rows.append({
                    "project":     project_name,
                    "date":        d["date"],
                    "impressions": d["impressions"],
                    "clicks":      d["clicks"],
                    "cost":        d["cost"],
                    "conversions": d["conversions"],
                    "sessions":    m["sessions"],
                })

            print(f"OK ({len(direct_rows)} дней)")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            continue

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
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        print("Убедитесь, что файл credentials.json лежит в папке, а в таблице выдан доступ email'у из этого файла-ключа.")
        return

    # Группируем строки по проектам
    from collections import defaultdict
    projects_data = defaultdict(list)
    for r in rows:
        projects_data[r["project"]].append(r)

    for project_name, proj_rows in projects_data.items():
        # Определяем имя листа
        cfg = config.PROJECTS.get(project_name, {})
        sheet_name = cfg.get("worksheet_name", project_name)

        print(f"\nВыгрузка клиента '{project_name}' на лист '{sheet_name}'...")
        
        # Пытаемся открыть лист. Если его нет - создаем
        try:
            ws = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  Лист '{sheet_name}' не найден, создаю новый...")
            ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="10")

        _export_to_worksheet(sh, ws, proj_rows)


def _export_to_worksheet(sh, ws, rows: list[dict]):
    # Проверяем, есть ли уже заголовки в таблице. Если таблица пустая - добавляем их.
    existing_data = ws.get_all_values()
    # gspread может вернуть [[]] для пустой таблицы
    if not existing_data or not any(existing_data[0]):
        print("  Таблица пустая, добавляем заголовки...")
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
        existing_data = [headers]

    print("Добавление новых строк: ")
    # Собираем все строки для выгрузки массивом
    data_to_append = []
    
    for row in rows:
        # Переводим дату из YYYY-MM-DD в DD.MM.YYYY
        y, m, d = row["date"].split("-")
        date_str = f"{d}.{m}.{y}"

        imp  = row["impressions"]
        clk  = row["clicks"]
        cost = row["cost"]
        conv = row["conversions"]

        ctr = round((clk / imp * 100) if imp > 0 else 0, 2)
        cpc = round((cost / clk) if clk > 0 else 0, 2)
        cpa = round((cost / conv) if conv > 0 else 0, 2)
        cr  = round((conv / clk * 100) if clk > 0 else 0, 2)

        data_to_append.append([
            date_str,                                          # Дата
            "р." + str(round(cost, 2)).replace('.', ','),     # Расход, в руб
            imp,                                              # Количество показов
            clk,                                              # Кол-во кликов
            "р." + str(round(cpc, 2)).replace('.', ','),      # CPC
            str(round(ctr, 2)).replace('.', ',') + "%",       # CTR
            conv,                                             # Кол-во конверсий
            "р." + str(round(cpa, 2)).replace('.', ','),      # CPA
            str(round(cr, 2)).replace('.', ',') + "%",        # CR
        ])

    # Пакетная выгрузка
    dates_to_replace = {r[0] for r in data_to_append if r and len(r) > 0}
    rows_to_delete = []
    
    for idx, r in enumerate(existing_data[1:], start=2):  # пропускаем заголовок
        if r and len(r) > 0:
            if r[0] in dates_to_replace or str(r[0]).upper() == "ИТОГ":
                rows_to_delete.append(idx)

    remaining_rows = []
    for idx, r in enumerate(existing_data[1:], start=2):
        if idx not in rows_to_delete:
            remaining_rows.append(r)

    if rows_to_delete:
        print(f"Найдено {len(rows_to_delete)} существующих строк (Итог или за те же даты) — перезаписываем...")
        for idx in sorted(rows_to_delete, reverse=True):
            ws.delete_rows(idx)

    # Группируем все данные (старые + новые) по месяцам (Формат: MM.YYYY)
    from collections import defaultdict
    months_data = defaultdict(list)
    
    for r in remaining_rows + data_to_append:
        if not r or len(r) == 0:
            continue
        date_val = r[0]
        # Извлекаем месяц и год из формата DD.MM.YYYY
        parts = date_val.split('.')
        if len(parts) == 3:
            # Унифицируем месяц (например, 4 и 04 -> 04), чтобы группировало корректно:
            month_key = f"{int(parts[1]):02d}.{parts[2]}"
            # (Опционально) приводим формат даты тоже к стандартному DD.MM.YYYY:
            r[0] = f"{int(parts[0]):02d}.{int(parts[1]):02d}.{parts[2]}"
            months_data[month_key].append(r)

    # Очищаем таблицу от старых данных (оставляя только шапку)
    # Это необходимо для ровной перезаписи по месяцам
    ws.clear()
    header_row = existing_data[0] if len(existing_data) > 0 else []
    
    current_row_idx = 1
    bold_rows = []
    all_final_rows = []

    # Функция очистки чисел
    def clean_num(v, is_float=False):
        v = str(v).replace('р.', '').replace('p.', '').replace('%', '').replace('\xa0', '').replace(' ', '').replace(',', '.')
        try:
            return float(v) if is_float else int(float(v))
        except:
            return 0.0 if is_float else 0

    # Сортируем месяцы (например, хронологически по году и месяцу)
    def month_sort_key(m_str):
        m, y = m_str.split('.')
        return (int(y), int(m))
        
    sorted_months = sorted(months_data.keys(), key=month_sort_key)

    for m_key in sorted_months:
        # Добавляем шапку таблицы перед каждым новым месяцем и делаем ее жирной
        if header_row:
            all_final_rows.append(header_row)
            bold_rows.append(current_row_idx)
            current_row_idx += 1
            
        month_rows = months_data[m_key]
        
        # Сортируем строки внутри месяца по дате (дню)
        month_rows.sort(key=lambda r: int(r[0].split('.')[0]) if len(r[0].split('.'))==3 else 0)
        
        total_cost = 0.0
        total_imp = 0
        total_clk = 0
        total_conv = 0
        
        for r in month_rows:
            all_final_rows.append(r)
            current_row_idx += 1
            if len(r) >= 7:
                total_cost += clean_num(r[1], True)
                total_imp  += clean_num(r[2], False)
                total_clk  += clean_num(r[3], False)
                total_conv += clean_num(r[6], False)

        # Считаем итог по месяцу
        ctr = round((total_clk / total_imp * 100) if total_imp > 0 else 0, 2)
        cpc = round((total_cost / total_clk) if total_clk > 0 else 0, 2)
        cpa = round((total_cost / total_conv) if total_conv > 0 else 0, 2)
        cr  = round((total_conv / total_clk * 100) if total_clk > 0 else 0, 2)

        # Форматирование чисел с разделителями тысяч (пробел) и запятой для дробных
        def format_num(val, is_currency=False):
            if val == 0 and is_currency:
                return "р.0,00"
            elif val == 0:
                return "0,00"
            # Форматируем с запятой как разделитель тысяч, потом меняем запятую на пробел, а точку на запятую
            # Для целых чисел (показы, клики) можно просто возвращать int, Google Sheets сам с ними справится
            s = f"{val:,.2f}"
            parts = s.split('.')
            int_part = parts[0].replace(',', ' ')
            dec_part = parts[1]
            res = f"{int_part},{dec_part}"
            if is_currency:
                return f"р.{res}"
            return res

        itog_row = [
            "ИТОГ",
            format_num(total_cost, True),
            total_imp,
            total_clk,
            format_num(cpc, True),
            format_num(ctr).replace(',00', '') if ctr.is_integer() else format_num(ctr) + "%", # Упрощенно
            total_conv,
            format_num(cpa, True),
            format_num(cr).replace(',00', '') if cr.is_integer() else format_num(cr) + "%"
        ]
        
        # Исправляем формат % более надежно
        itog_row[5] = f"{ctr:,.2f}".replace(',', ' ').replace('.', ',') + "%"
        itog_row[8] = f"{cr:,.2f}".replace(',', ' ').replace('.', ',') + "%"

        all_final_rows.append(itog_row)
        bold_rows.append(current_row_idx)
        current_row_idx += 1
        
        # Делаем отступ в 2 пустые строчки после итога каждого месяца
        all_final_rows.append([])
        all_final_rows.append([])
        current_row_idx += 2

    # Пакетно добавляем все отсортированные строки с итогами
    ws.append_rows(all_final_rows, value_input_option='USER_ENTERED')
    
    # Форматирование: сбрасываем старое и рисуем жирные границы ("полоски по бокам") вместо жирного текста
    try:
        requests = []
        
        # 1. Убираем старый жирный шрифт везде, чтобы новые строки случайно не становились жирными
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 10
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": False}
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold"
            }
        })
        
        # 2. Очищаем все старые границы, чтобы они не наслаивались
        requests.append({
            "updateBorders": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 10
                },
                "top": {"style": "NONE"},
                "bottom": {"style": "NONE"},
                "left": {"style": "NONE"},
                "right": {"style": "NONE"},
                "innerHorizontal": {"style": "NONE"},
                "innerVertical": {"style": "NONE"},
            }
        })

        # 3. Делаем выделение нужных строк (Заголовок и Итог) через прямоугольную границу
        for b_idx in bold_rows:
            requests.append({
                "updateBorders": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": b_idx - 1,
                        "endRowIndex": b_idx,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9
                    },
                    "top": {"style": "SOLID_MEDIUM"},
                    "bottom": {"style": "SOLID_MEDIUM"},
                    "left": {"style": "SOLID_MEDIUM"},
                    "right": {"style": "SOLID_MEDIUM"}
                }
            })
            
        if requests:
            sh.batch_update({"requests": requests})
    except Exception as e:
        print(f"⚠️  Не удалось применить форматирование рамок: {e}")

    print(f"✅ Успешно выгружено {len(data_to_append)} строк + ИТОГИ по месяцам на лист: {ws.title}")


if __name__ == "__main__":
    print("Сбор данных...")
    rows = collect_data()
    export_to_google_sheets(rows)

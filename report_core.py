from __future__ import annotations

import os
from collections import defaultdict

import gspread

import config
import direct
import metrika


HEADER_ROW = [
    "Дата",
    "Расход, в руб,",
    "Количество показов",
    "Кол-во кликов",
    "CPC",
    "CTR (количество показов к кликам)",
    "Конверсии Директ",
    "Конверсии Метрика",
    "Стоимость конверсии (CPA)",
    "Конверсия сайта % (CR)",
]


def _select_projects(client_key: str = None):
    if not client_key:
        return list(config.PROJECTS.items())

    project_name, project_cfg = config.resolve_project(client_key)
    return [(project_name, project_cfg)]


def collect_data(date_from: str, date_to: str, client_key: str = None, goal_id: str | None = None) -> list[dict]:
    rows = []

    for project_name, cfg in _select_projects(client_key):
        resolved_goal_id = goal_id or cfg.get("metrika_goal_id") or config.METRIKA_GOAL_ID or ""

        direct_rows = direct.get_stats(
            token=config.DIRECT_TOKEN,
            client_login=cfg["direct_login"],
            date_from=date_from,
            date_to=date_to,
        )

        metrika_rows = metrika.get_stats(
            token=config.METRIKA_TOKEN,
            counter_id=cfg["metrika_counter"],
            date_from=date_from,
            date_to=date_to,
            goal_id=resolved_goal_id,
        )

        metrika_by_date = {row["date"]: row for row in metrika_rows}

        for direct_row in direct_rows:
            metrika_row = metrika_by_date.get(direct_row["date"], {"sessions": 0, "bounce_rate": 0.0})
            direct_conversions = direct_row["conversions"]
            goal_conversions = metrika_row.get("goal_conversions") if resolved_goal_id else None
            selected_conversions = goal_conversions if resolved_goal_id else direct_conversions
            rows.append({
                "project": project_name,
                "worksheet_name": cfg.get("worksheet_name") or project_name,
                "date": direct_row["date"],
                "impressions": direct_row["impressions"],
                "clicks": direct_row["clicks"],
                "cost": direct_row["cost"],
                "conversions": selected_conversions,
                "direct_conversions": direct_conversions,
                "goal_conversions": goal_conversions,
                "sessions": metrika_row["sessions"],
                "bounce_rate": metrika_row.get("bounce_rate", 0.0),
                "goal_id": resolved_goal_id,
            })

    return rows


def _format_money(value: float) -> str:
    return "р." + str(round(value, 2)).replace(".", ",")


def _format_percent(value: float) -> str:
    return str(round(value, 2)).replace(".", ",") + "%"


def _clean_num(value, is_float: bool = False):
    text = str(value).replace("р.", "").replace("p.", "").replace("%", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(text) if is_float else int(float(text))
    except Exception:
        return 0.0 if is_float else 0


def _prepare_rows_for_sheet(rows: list[dict]) -> tuple[list[list], list[int]]:
    if not rows:
        return [HEADER_ROW], [1]

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["date"][:7]].append(row)

    final_rows = []
    bold_row_indexes = []
    current_row_idx = 1

    for month_key in sorted(grouped.keys()):
        month_rows = sorted(grouped[month_key], key=lambda r: r["date"])

        final_rows.append(HEADER_ROW)
        bold_row_indexes.append(current_row_idx)
        current_row_idx += 1

        for row in month_rows:
            y, m, d = row["date"].split("-")
            date_str = f"{d}.{m}.{y}"

            imp = row["impressions"]
            clk = row["clicks"]
            cost = row["cost"]
            conv = row["conversions"]
            direct_conv = row.get("direct_conversions", 0)
            goal_conv = row.get("goal_conversions")
            goal_conv_cell = goal_conv if goal_conv is not None else ""

            ctr = round((clk / imp * 100) if imp > 0 else 0, 2)
            cpc = round((cost / clk) if clk > 0 else 0, 2)
            cpa = round((cost / conv) if conv > 0 else 0, 2)
            cr = round((conv / clk * 100) if clk > 0 else 0, 2)

            final_rows.append([
                date_str,
                _format_money(cost),
                imp,
                clk,
                _format_money(cpc),
                _format_percent(ctr),
                direct_conv,
                goal_conv_cell,
                _format_money(cpa),
                _format_percent(cr),
            ])
            current_row_idx += 1

        total_cost = sum(row["cost"] for row in month_rows)
        total_imp = sum(row["impressions"] for row in month_rows)
        total_clk = sum(row["clicks"] for row in month_rows)
        total_conv = sum(row["conversions"] for row in month_rows)
        total_direct_conv = sum(row.get("direct_conversions", 0) for row in month_rows)
        total_goal_conv = sum(row.get("goal_conversions", 0) or 0 for row in month_rows)

        ctr = round((total_clk / total_imp * 100) if total_imp > 0 else 0, 2)
        cpc = round((total_cost / total_clk) if total_clk > 0 else 0, 2)
        cpa = round((total_cost / total_conv) if total_conv > 0 else 0, 2)
        cr = round((total_conv / total_clk * 100) if total_clk > 0 else 0, 2)

        final_rows.append([
            "ИТОГ",
            _format_money(total_cost),
            total_imp,
            total_clk,
            _format_money(cpc),
            _format_percent(ctr),
            total_direct_conv,
            total_goal_conv if any(row.get("goal_id") for row in month_rows) else "",
            _format_money(cpa),
            _format_percent(cr),
        ])
        bold_row_indexes.append(current_row_idx)
        current_row_idx += 1

        final_rows.append([])
        final_rows.append([])
        current_row_idx += 2

    return final_rows, bold_row_indexes


def _ensure_worksheet(sh, worksheet_name: str):
    try:
        return sh.worksheet(worksheet_name)
    except Exception:
        return sh.add_worksheet(title=worksheet_name, rows=100, cols=20)


def get_worksheet_url(worksheet_name: str) -> str:
    """Вернуть прямую ссылку на лист Google Sheets по имени вкладки."""
    gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)
    sh = gc.open_by_url(config.GOOGLE_SHEET_URL)
    ws = _ensure_worksheet(sh, worksheet_name)
    base_url = config.GOOGLE_SHEET_URL.split("#", 1)[0]
    return f"{base_url}#gid={ws.id}"


def write_rows_to_sheet(rows: list[dict]):
    if not rows:
        return 0

    gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)
    sh = gc.open_by_url(config.GOOGLE_SHEET_URL)

    grouped_by_sheet = defaultdict(list)
    for row in rows:
        grouped_by_sheet[row["worksheet_name"]].append(row)

    total_written = 0

    for worksheet_name, sheet_rows in grouped_by_sheet.items():
        ws = _ensure_worksheet(sh, worksheet_name)
        prepared_rows, bold_rows = _prepare_rows_for_sheet(sheet_rows)

        ws.clear()
        ws.append_rows(prepared_rows, value_input_option="USER_ENTERED")

        requests = []
        
        # Форматирование заголовков (жирный текст и выравнивание)
        for bold_row in bold_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": bold_row - 1,
                        "endRowIndex": bold_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 10,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                        }
                    },
                    "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment",
                }
            })

        # Выравнивание данных (вправо для цифр)
        if prepared_rows:
            total_rows = len(prepared_rows)
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 0,
                        "endRowIndex": total_rows,
                        "startColumnIndex": 1,
                        "endColumnIndex": 10,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "RIGHT",
                        }
                    },
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            })

        if requests:
            sh.batch_update({"requests": requests})

        total_written += len(sheet_rows)

    return total_written

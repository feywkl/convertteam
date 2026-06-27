# ✅ Чек-лист перед деплоем на Aeza VPS

## Безопасность ✓
- [x] Все токены в переменных окружения (`.env` / GitHub Secrets)
- [x] Нет захардкоженных токенов в коде
- [x] `.env` в `.gitignore`
- [x] `credentials.json` в `.gitignore`
- [x] `admins.json` в `.gitignore`
- [x] `users_registry.json` в `.gitignore`
- [x] `telegram_allowlist.json` в `.gitignore`

## Функционал ✓
- [x] Telegram-бот с командами `/report`, `/myid`, `/addadmin`, `/removeadmin`, `/admins`
- [x] Парсинг периодов (одна дата, месяц, диапазон)
- [x] Сбор данных из Яндекс.Директа и Метрики
- [x] Форматирование и расчет метрик (CPC, CTR, CPA, CR)
- [x] Выгрузка в Google Sheets с месячными заголовками
- [x] Форматирование ячеек (жирный текст, выравнивание)
- [x] Обработка ошибок (сеть, API)

## Деплой ✓
- [x] `requirements.txt` содержит все зависимости
- [x] README.md с инструкциями для VPS/Aeza
- [x] GitHub Actions workflow для регулярного запуска

## Что делать для деплоя на Aeza VPS

### 1. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

Или используйте обычного пользователя с `sudo`.

### 2. Установите зависимости на сервере

Для Ubuntu/Debian:

```bash
apt update
apt install -y python3 python3-venv python3-pip git
```

### 3. Склонируйте проект

```bash
git clone https://github.com/your-user/convertteam.git
cd convertteam
```

### 4. Создайте виртуальное окружение и установите зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Создайте `.env` на сервере

```bash
cp .env.example .env
nano .env
```

Заполните в `.env`:

- `DIRECT_TOKEN`
- `METRIKA_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `GOOGLE_SHEET_URL`
- `TELEGRAM_ALLOWED_CHAT_IDS`
- `DATE_FROM` и `DATE_TO`, если нужен ручной период по умолчанию

`credentials.json` тоже нужно положить рядом с кодом, если бот будет писать в Google Sheets.

### 6. Проверьте запуск вручную

```bash
source .venv/bin/activate
python telegram_bot.py
```

### 7. Сделайте автозапуск через systemd

Создайте файл `/etc/systemd/system/convertteam-bot.service`:

```ini
[Unit]
Description=Convertteam Telegram Bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/convertteam
EnvironmentFile=/opt/convertteam/.env
ExecStart=/opt/convertteam/.venv/bin/python /opt/convertteam/telegram_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:

```bash
systemctl daemon-reload
systemctl enable convertteam-bot
systemctl start convertteam-bot
systemctl status convertteam-bot
```

### 8. Смотрите логи

```bash
journalctl -u convertteam-bot -f
```

### 9. Если нужен ручной отчёт по расписанию

Используйте cron или GitHub Actions. На сервере можно добавить cron-задачу:

```bash
crontab -e
```

Пример:

```cron
0 * * * * cd /opt/convertteam && /opt/convertteam/.venv/bin/python generate_report.py >> /var/log/convertteam-report.log 2>&1
```

## Файлы в репозитории (за исключением секретов)
- `config.py` — конфигурация (токены из env)
- `direct.py` — API Яндекс.Директа
- `metrika.py` — API Яндекс.Метрики
- `report_core.py` — общая логика отчетов
- `generate_report.py` — CLI для запуска отчетов
- `telegram_bot.py` — основной бот с обработкой команд
- `requirements.txt` — зависимости
- `Procfile` — запасной вариант для платформ с worker-моделью
- `clients.json` — описание клиентов (без токенов)
- `.github/workflows/report.yml` — автоматический запуск по расписанию
- `README.md` — документация

## Что НЕ в репозитории (в .gitignore)
- `.env` — локальные переменные
- `credentials.json` — Google сервисный аккаунт
- `admins.json` — список администраторов (обновляется в боте)
- `users_registry.json` — маппинг username -> chat_id
- `telegram_allowlist.json` — разрешённые пользователи

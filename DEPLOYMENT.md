# ✅ Чек-лист перед деплоем на Heroku

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
- [x] `Procfile` готов (`worker: python3 telegram_bot.py`)
- [x] `requirements.txt` содержит все зависимости
- [x] README.md с инструкциями Heroku
- [x] GitHub Actions workflow для регулярного запуска

## Что делать для деплоя на Heroku

### 1. Создайте приложение
```bash
heroku create your-app-name
git push heroku main
```

### 2. Установите Config Vars (переменные окружения)
```bash
heroku config:set DIRECT_TOKEN="..."
heroku config:set METRIKA_TOKEN="..."
heroku config:set TELEGRAM_BOT_TOKEN="..."
heroku config:set GOOGLE_SHEET_URL="..."
heroku config:set GOOGLE_CREDENTIALS='{"type":"service_account",...}'
heroku config:set TELEGRAM_ALLOWED_CHAT_IDS="693673743"
```

### 3. Запустите worker
```bash
heroku ps:scale worker=1
```

### 4. Проверьте логи
```bash
heroku logs --tail
```

## Файлы в репозитории (за исключением секретов)
- `config.py` — конфигурация (токены из env)
- `direct.py` — API Яндекс.Директа
- `metrika.py` — API Яндекс.Метрики
- `report_core.py` — общая логика отчетов
- `generate_report.py` — CLI для запуска отчетов
- `telegram_bot.py` — основной бот с обработкой команд
- `requirements.txt` — зависимости
- `Procfile` — инструкция для Heroku
- `clients.json` — описание клиентов (без токенов)
- `.github/workflows/report.yml` — автоматический запуск по расписанию
- `README.md` — документация

## Что НЕ в репозитории (в .gitignore)
- `.env` — локальные переменные
- `credentials.json` — Google сервисный аккаунт
- `admins.json` — список администраторов (обновляется в боте)
- `users_registry.json` — маппинг username -> chat_id
- `telegram_allowlist.json` — разрешённые пользователи

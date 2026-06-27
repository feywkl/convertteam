# 📊 Отчёты Яндекс.Директ + Метрика → Google Sheets через Telegram-бота

Этот проект собирает статистику из Яндекс.Директа и Яндекс.Метрики, считает основные метрики и выгружает результат в Google Таблицу.

Основной сценарий работы теперь такой: в Telegram-бот отправляется `id клиента` и `период`, после чего отчёт автоматически записывается в нужный лист Google Sheets.

Важно: если токен Telegram-бота уже был отправлен в чат или сохранён где-то открыто, его нужно сразу отозвать в BotFather и выпустить новый.

## Как это работает

1. В Telegram отправляется команда вида:

```text
/report metall-cvt 01.01.2026-02.01.2026
```

2. Бот находит клиента в `clients.json`.
3. Бот разбирает период.
4. Скрипт забирает данные из API Яндекс.Директа и Яндекс.Метрики.
5. Данные агрегируются по дням и считаются итоговые значения.
6. Результат выгружается в Google Sheets с оформлением и строкой `ИТОГ`.

## Как задавать период

Период можно указать тремя способами:

- Одна дата: `2026-05-06` или `06.05.2026`
- Месяц: `2026-05` или `month:2026-05`
- Диапазон: `01.01.2026-02.01.2026` или `2026-01-01:2026-01-31`

Правило простое:

- одна дата = один день
- месяц = весь месяц целиком
- диапазон = от первой даты до второй включительно

## Команды Telegram-бота

### Пример 1: один день

```text
/report metall-cvt 2026-05-06
```

### Пример 2: месяц

```text
/report metall-cvt 2026-05
```

### Пример 3: диапазон

```text
/report metall-cvt 01.01.2026-02.01.2026
```

Если команда введена без периода или с ошибкой, бот покажет подсказку с форматом.

## Что такое `client_id`

`client_id` — это ключ клиента в файле `clients.json`.

Пример:

```json
{
  "metall-cvt": {
    "direct_login": "metall-cvt",
    "metrika_counter": "53749281",
    "worksheet_name": "metall-cvt"
  }
}
```

В этом примере:

- `metall-cvt` — идентификатор клиента для бота
- `direct_login` — логин в Яндекс.Директе
- `metrika_counter` — счётчик Метрики
- `worksheet_name` — название листа в Google Sheets

## Что выгружается в таблицу

В таблицу попадают такие колонки:

1. Дата
2. Расход
3. Количество показов
4. Кол-во кликов
5. CPC
6. CTR
7. Кол-во конверсий
8. CPA
9. CR

Также добавляется строка `ИТОГ`, а итоговые строки выделяются жирным шрифтом.

## Настройка в GitHub

Все чувствительные данные хранятся в GitHub Secrets.

### Обязательные секреты

- `DIRECT_TOKEN` — токен Яндекс.Директа
- `METRIKA_TOKEN` — токен Яндекс.Метрики
- `GOOGLE_SHEET_URL` — ссылка на Google Таблицу
- `GOOGLE_CREDENTIALS` — JSON сервисного аккаунта Google
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота

Все значения вводятся только в GitHub Secrets или в локальный `.env` для тестового запуска. В коде токены и доступы не хранятся.

### Опциональные секреты

- `TELEGRAM_ALLOWED_CHAT_IDS` — список разрешённых chat_id через запятую
- `TELEGRAM_ADMIN_CHAT_IDS` — список chat_id администраторов через запятую

### Как ограничен доступ к боту

Бот отвечает только тем chat_id, которые есть в allowlist.

Allowlist формируется из двух источников:

- GitHub Secret `TELEGRAM_ALLOWED_CHAT_IDS`
- локальный файл `telegram_allowlist.json`, если бот запущен на вашей машине или сервере

Файл `telegram_allowlist.json` добавлен в `.gitignore`, чтобы одобренные chat_id не попали в репозиторий.

Администраторы могут управлять allowlist прямо в Telegram:

- `/allow <chat_id>` — добавить пользователя
- `/block <chat_id>` — убрать пользователя
- `/users` — посмотреть текущий список

Админ-команды доступны только chat_id из `TELEGRAM_ADMIN_CHAT_IDS`.

Если `TELEGRAM_ALLOWED_CHAT_IDS` пустой, а `telegram_allowlist.json` тоже пустой, бот не будет пускать никого, пока админ не добавит первого пользователя.

### Как поменять секрет

1. Откройте репозиторий на GitHub.
2. Перейдите в `Settings`.
3. Откройте `Secrets and variables` → `Actions`.
4. Найдите нужный секрет и нажмите редактирование.
5. Вставьте новое значение и сохраните.

После обновления секретов новый запуск workflow или бота сразу возьмёт актуальные значения.

## Как добавлять нового клиента

Клиенты описываются в `clients.json`.

Нужно добавить новый объект в файл с тремя полями:

- `direct_login`
- `metrika_counter`
- `worksheet_name`

После обновления `clients.json` новый клиент сразу доступен в боте как `client_id`.

## Ручной запуск через GitHub Actions

Если нужно выгрузить отчёт вручную без Telegram-бота, в репозитории есть workflow в папке `.github/workflows`.

Там можно задать даты через поля `date_from` и `date_to` и запустить отчёт вручную из вкладки `Actions`.

## Локальный запуск

Для локальной отладки:

```bash
pip install -r requirements.txt
python generate_report.py
```

Для запуска Telegram-бота:

```bash
python telegram_bot.py
```

Перед запуском локально нужно задать переменные окружения для токенов и ссылки на таблицу.

## Частые вопросы

### Бот ничего не делает

Проверьте, что задан `TELEGRAM_BOT_TOKEN`, что ваш `chat_id` добавлен в allowlist, и что админский чат указан в `TELEGRAM_ADMIN_CHAT_IDS`.

### Отчёт пустой

Это обычно значит, что за выбранный период в Директе нет данных или не указан правильный клиент.

### Данные не попадают в таблицу

Проверьте, что у сервисного аккаунта есть доступ на редактирование к Google Sheets, и что `GOOGLE_CREDENTIALS` заполнен корректно.

## 🚀 Деплой на Heroku

Проект готов к запуску на Heroku. Вот полная инструкция:

### 1. Установите Heroku CLI

```bash
brew tap heroku/brew && brew install heroku
heroku login
```

### 2. Создайте приложение на Heroku

```bash
heroku create your-app-name
```

или используйте существующее:

```bash
heroku git:remote -a your-app-name
```

### 3. Установите все секреты в Heroku Config Vars

```bash
heroku config:set DIRECT_TOKEN="your_token"
heroku config:set METRIKA_TOKEN="your_token"
heroku config:set TELEGRAM_BOT_TOKEN="your_bot_token"
heroku config:set GOOGLE_SHEET_URL="https://docs.google.com/..."
heroku config:set GOOGLE_CREDENTIALS='{"type": "service_account", ...}'
heroku config:set TELEGRAM_ALLOWED_CHAT_IDS="693673743,123456789"
```

**Важно:** `GOOGLE_CREDENTIALS` должен быть JSON-строкой без переносов. Если на macOS, используйте одинарные кавычки:

```bash
heroku config:set GOOGLE_CREDENTIALS='{"type":"service_account","project_id":"..."}'
```

### 4. Деплойте приложение

```bash
git push heroku main
```

### 5. Запустите worker

```bash
heroku ps:scale worker=1
```

### 6. Проверьте логи

```bash
heroku logs --tail
```

### Отключение бота

```bash
heroku ps:scale worker=0
```

### Проверка текущих переменных

```bash
heroku config
```

### Важные моменты для Heroku

- **Procfile** уже включен в репозиторий (`worker: python3 telegram_bot.py`)
- **requirements.txt** содержит все зависимости
- Бот использует long-polling (не нужны вебхуки и входящие соединения)
- Все токены хранятся в `Config Vars`, не в коде
- Данные администраторов и пользователей хранятся в локальных JSON-файлах (обнулятся при рестарте Heroku, но можно добавить S3 для персистентности)

### После деплоя

1. Напишите боту в Telegram `/help`
2. Выполните `/myid` чтобы узнать ваш chat_id
3. Используйте `/addadmin <chat_id>` чтобы добавить администраторов
4. Команда `/report` будет работать как обычно

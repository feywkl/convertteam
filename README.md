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
- `DATE_FROM` и `DATE_TO` — дефолтный период для CLI/cron, если нужен

### Как ограничен доступ к боту

Бот отвечает только тем chat_id, которые есть в allowlist.

Allowlist формируется из двух источников:

- GitHub Secret `TELEGRAM_ALLOWED_CHAT_IDS`
- локальный файл `telegram_allowlist.json`, если бот запущен на вашей машине или сервере

Файл `telegram_allowlist.json` добавлен в `.gitignore`, чтобы одобренные chat_id не попали в репозиторий.

Администраторы управляются через файл `admins.json` и команды бота:

- `/myid` — показать свой `chat_id`
- `/addadmin <chat_id|@ник>` — добавить администратора
- `/removeadmin <chat_id>` — удалить администратора
- `/admins` — показать список администраторов

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

Проверьте, что задан `TELEGRAM_BOT_TOKEN`, что ваш `chat_id` добавлен в allowlist, и что вы добавлены в `admins.json`, если используете админские команды.

### Отчёт пустой

Это обычно значит, что за выбранный период в Директе нет данных или не указан правильный клиент.

### Данные не попадают в таблицу

Проверьте, что у сервисного аккаунта есть доступ на редактирование к Google Sheets, и что `GOOGLE_CREDENTIALS` заполнен корректно.

## 🚀 Деплой на Aeza VPS

Проект рассчитан на обычный VPS: бот запускается как `systemd`-сервис и слушает Telegram через long-polling.

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

Если отчёты будут запускаться по расписанию на сервере, можно добавить `DATE_FROM` и `DATE_TO`.

`credentials.json` с сервисным аккаунтом Google нужно положить рядом с кодом и не добавлять в Git.

### 6. Проверьте запуск вручную

```bash
source .venv/bin/activate
python telegram_bot.py
```

### 7. Настройте автозапуск через systemd

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

### 9. Если нужен отчет по расписанию

Используйте `cron` или GitHub Actions. Пример задачи:

```bash
crontab -e
```

```cron
0 * * * * cd /opt/convertteam && /opt/convertteam/.venv/bin/python generate_report.py >> /var/log/convertteam-report.log 2>&1
```

### После деплоя

1. Напишите боту `/help`
2. Выполните `/myid`, чтобы узнать свой `chat_id`
3. Добавьте себя в `admins.json` один раз на сервере, если нужно, или через уже существующий админский доступ
4. Используйте `/addadmin <chat_id>` для новых администраторов

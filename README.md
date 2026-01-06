# TelBot 2.0 — Серверный бот автопостинга

Автоматический постинг контента в Telegram-каналы по расписанию.

## 🚀 Быстрая установка на сервер (Ubuntu)

### Вариант 1: Автоматическая установка с вашего компьютера

```bash
bash install_on_server.sh root@ваш_сервер
```

### Вариант 2: Установка прямо на сервере

1. Загрузите файлы на сервер
2. Запустите одну команду:

```bash
cd telbot
sudo bash deploy.sh
```

**Всё! Бот установлен, настроен и запущен автоматически.**

📖 Подробная инструкция: [QUICK_START.md](QUICK_START.md)

---

## 📋 Управление ботом на сервере

```bash
systemctl status telbot      # Статус
systemctl restart telbot     # Перезапуск
journalctl -u telbot -f      # Логи в реальном времени
```

---

## Быстрый старт (локально)

```bash
cd telbot
python telbot.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/status` | Текущий статус бота |
| `/stats` | Статистика контента |
| `/posting_start` | Запустить автопостинг |
| `/posting_stop` | Остановить автопостинг |
| `/post_now` | Опубликовать сейчас |
| `/post_now atla` | Опубликовать в конкретный канал |
| `/channels` | Список каналов |
| `/test` | Тест подключения к каналам |
| `/help` | Справка |

## Папки

| Папка | Назначение |
|-------|------------|
| `content/` | Контент для публикации |
| `archives/` | Архив опубликованного |
| `config/` | Конфигурация |
| `logs/` | Журналы работы |

## Структура content/

```
content/
├── atla/              # Avatar: The Last Airbender
│   ├── Azula/
│   ├── Katara/
│   └── ...
├── naruto/            # Naruto
├── harry_potter/      # Harry Potter
└── mpa_disney/        # Disney
```

## Настройка

### Расписание (config_custom.json)

```json
{
  "schedule": {
    "post_interval_minutes": 30,
    "first_post_hour": 0,
    "last_post_hour": 24
  }
}
```

### Токен бота

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "admin_ids": [123456789]
  }
}
```

## Systemd сервис

`/etc/systemd/system/telbot.service`:
```ini
[Unit]
Description=TelBot 2.0
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telbot
ExecStart=/usr/bin/python3 telbot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telbot
sudo systemctl start telbot
sudo systemctl status telbot
```

## Обновление контента

1. Подготовьте пакет на локальном компьютере через `content_manager.py`
2. Загрузите на сервер:
   ```bash
   scp -r upload/2025-01/* user@server:/opt/telbot/content/
   ```
3. Бот автоматически найдёт новый контент

## Проверка работы

```bash
# Логи в реальном времени
tail -f logs/telbot_*.log

# Статус сервиса
systemctl status telbot

# Журнал systemd
journalctl -u telbot -f
```

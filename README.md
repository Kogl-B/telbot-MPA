# TelBot 2.0 — Серверный бот автопостинга

Автоматический постинг контента в Telegram-каналы по расписанию.

## 🚀 Супербыстрая установка на Ubuntu (одна команда!)

Просто выполните на вашем Ubuntu сервере:

```bash
curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

или

```bash
wget -qO- https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

**Вот и всё!** 🎉 Бот автоматически установится и запустится.

### Что делает установщик?

✅ Устанавливает все зависимости (Python, git и т.д.)
✅ Создает пользователя для бота
✅ Клонирует репозиторий в `/opt/telbot`
✅ Настраивает виртуальное окружение
✅ Создает systemd сервис
✅ Запускает бота автоматически

---

## 🎮 Управление ботом

```bash
# Статус бота
sudo systemctl status telbot

# Перезапуск
sudo systemctl restart telbot

# Остановить
sudo systemctl stop telbot

# Запустить
sudo systemctl start telbot

# Логи в реальном времени
sudo journalctl -u telbot -f

# Или логи бота
sudo tail -f /opt/telbot/logs/telbot_*.log
```

---

## 📂 Структура после установки

```
/opt/telbot/
├── telbot.py              # Основной скрипт
├── config_custom.json     # Конфигурация (уже готова!)
├── content/               # Сюда добавляйте контент
│   ├── mpa_disney/
│   ├── harry_potter/
│   ├── atla/
│   └── naruto/
├── logs/                  # Логи
└── venv/                  # Python окружение
```

## 📸 Добавление контента

```bash
# Создайте папки для контента
sudo mkdir -p /opt/telbot/content/mpa_disney/"Princess Jasmin"

# Скопируйте изображения
sudo cp ваши_картинки/* /opt/telbot/content/mpa_disney/"Princess Jasmin"/

# Установите права
sudo chown -R telbot:telbot /opt/telbot/content/
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

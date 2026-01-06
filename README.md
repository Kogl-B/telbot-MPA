# TelBot 2.0 — Telegram Auto-Posting Bot

Бот для автоматического постинга контента в Telegram-каналы.

## Установка на сервере (Ubuntu)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Kogl-B/telbot-MPA.git
cd telbot-MPA

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Запустите бота
python3 telbot.py
```

## Структура контента

Контент должен быть в папке `content/` в формате:
```
content/
├── 2026-01/           # Месяц
│   ├── naruto/        # Канал
│   │   ├── Sakura/    # Категория
│   │   │   ├── img1.jpg
│   │   │   └── img2.png
│   │   └── Hinata/
│   ├── atla/
│   └── harry_potter/
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/status` | Статус бота |
| `/stats` | Статистика контента |
| `/posting_start` | Запустить автопостинг |
| `/posting_stop` | Остановить |
| `/post_now` | Опубликовать сейчас |
| `/channels` | Список каналов |
| `/test` | Тест подключения |

## Запуск как systemd сервис

```bash
# Создайте файл сервиса
sudo nano /etc/systemd/system/telbot.service
```

Содержимое:
```ini
[Unit]
Description=TelBot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telbot
ExecStart=/usr/bin/python3 /opt/telbot/telbot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Активируйте и запустите
sudo systemctl daemon-reload
sudo systemctl enable telbot
sudo systemctl start telbot

# Проверьте статус
sudo systemctl status telbot
```

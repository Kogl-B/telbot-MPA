#!/bin/bash

# Скрипт для обновления service файла после загрузки на сервер

echo "🔄 Обновление telbot service..."

# Остановить сервис
systemctl stop telbot

# Скопировать новый service файл
cp /opt/telbot/telbot.service /etc/systemd/system/telbot.service

# Создать симлинк python3 если нужно
cd /opt/telbot/venv/bin
if [ ! -f python3 ]; then
    ln -sf python python3
    echo "✅ Создан симлинк python3"
fi

# Установить зависимости
echo "📦 Установка зависимостей..."
/opt/telbot/venv/bin/pip install -r /opt/telbot/requirements.txt

# Установить права
chmod +x /opt/telbot/telbot.py
chown -R telbot:telbot /opt/telbot

# Перезагрузить systemd
systemctl daemon-reload

# Запустить сервис
systemctl start telbot

# Показать статус
sleep 2
systemctl status telbot

echo ""
echo "📊 Логи:"
journalctl -u telbot -n 20 --no-pager

echo ""
echo "✅ Готово! Для просмотра логов в реальном времени:"
echo "   journalctl -u telbot -f"

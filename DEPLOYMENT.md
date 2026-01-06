# TelBot 2.0 - Развертывание на Ubuntu Server

## 📋 Требования

- Ubuntu Server 20.04 или выше
- Python 3.8+
- Права root (sudo)
- Минимум 512 MB RAM
- 1 GB свободного места на диске

## 🚀 Быстрая установка

### 1. Подключитесь к серверу по SSH

```bash
ssh user@your-server-ip
```

### 2. Загрузите файлы бота на сервер

**Вариант A: Через SCP (с вашего компьютера)**
```bash
scp -r "d:\TelBot 2.0\telbot" user@your-server-ip:/tmp/telbot
```

**Вариант B: Через Git**
```bash
# На сервере
cd /tmp
git clone your-repo-url telbot
```

**Вариант C: Создать архив и загрузить**
```bash
# На Windows
cd "d:\TelBot 2.0\telbot"
tar -czf telbot.tar.gz *

# Загрузить на сервер через SCP
scp telbot.tar.gz user@your-server-ip:/tmp/

# На сервере
cd /tmp
mkdir telbot
tar -xzf telbot.tar.gz -C telbot
```

### 3. Запустите скрипт установки

```bash
cd /tmp/telbot
sudo bash deploy.sh
```

### 4. Настройте конфигурацию

```bash
sudo nano /opt/telbot/config_custom.json
```

Пример минимальной конфигурации:
```json
{
  "channels": {
    "your_channel": {
      "channel_id": "-1001234567890",
      "name": "Your Channel Name",
      "enabled": true,
      "categories": {
        "category1": {
          "folder_name": "Category1",
          "hashtags": ["#hashtag1"]
        }
      }
    }
  }
}
```

### 5. Загрузите контент

```bash
# Создайте структуру папок
sudo mkdir -p /opt/telbot/content/2026-01/your_channel/Category1

# Загрузите изображения через SCP
scp -r /path/to/images/* user@server:/tmp/images/
sudo mv /tmp/images/* /opt/telbot/content/2026-01/your_channel/Category1/
sudo chown -R telbot:telbot /opt/telbot/content
```

### 6. Запустите бота

```bash
# Запуск
sudo systemctl start telbot

# Автозапуск при загрузке системы
sudo systemctl enable telbot

# Проверка статуса
sudo systemctl status telbot
```

## 📊 Управление ботом

### Основные команды

```bash
# Запустить бота
sudo systemctl start telbot

# Остановить бота
sudo systemctl stop telbot

# Перезапустить бота
sudo systemctl restart telbot

# Статус бота
sudo systemctl status telbot

# Отключить автозапуск
sudo systemctl disable telbot
```

### Просмотр логов

```bash
# Логи в реальном времени
sudo journalctl -u telbot -f

# Последние 100 строк
sudo journalctl -u telbot -n 100

# Логи за сегодня
sudo journalctl -u telbot --since today

# Файлы логов
sudo tail -f /var/log/telbot/telbot.log
sudo tail -f /var/log/telbot/telbot_error.log
```

## 🔧 Обслуживание

### Обновление бота

```bash
# Остановить бота
sudo systemctl stop telbot

# Загрузить новую версию
cd /tmp
# ... загрузите новые файлы ...

# Скопировать файлы
sudo cp /tmp/telbot/telbot.py /opt/telbot/
sudo chown telbot:telbot /opt/telbot/telbot.py

# Обновить зависимости (если нужно)
sudo -u telbot /opt/telbot/venv/bin/pip install -r /opt/telbot/requirements.txt

# Запустить бота
sudo systemctl start telbot
```

### Добавление контента

```bash
# Создать папку для нового месяца
sudo mkdir -p /opt/telbot/content/2026-02/channel_name/category

# Загрузить изображения
sudo cp /path/to/images/* /opt/telbot/content/2026-02/channel_name/category/

# Установить права
sudo chown -R telbot:telbot /opt/telbot/content
```

### Резервное копирование

```bash
# Backup конфигурации
sudo cp /opt/telbot/config_custom.json ~/telbot_config_backup.json

# Backup состояния
sudo cp /opt/telbot/posting_state.json ~/telbot_state_backup.json

# Backup всей папки
sudo tar -czf ~/telbot_backup_$(date +%Y%m%d).tar.gz /opt/telbot
```

## 🐛 Решение проблем

### Бот не запускается

```bash
# Проверить логи
sudo journalctl -u telbot -n 50

# Проверить права доступа
ls -la /opt/telbot

# Проверить конфигурацию
python3 -c "import json; json.load(open('/opt/telbot/config_custom.json'))"

# Запустить вручную для отладки
sudo -u telbot /opt/telbot/venv/bin/python3 /opt/telbot/telbot.py
```

### Проблемы с правами доступа

```bash
# Восстановить права
sudo chown -R telbot:telbot /opt/telbot
sudo chmod 755 /opt/telbot
sudo chmod 644 /opt/telbot/*.json
sudo chmod 644 /opt/telbot/*.py
```

### Бот перезапускается постоянно

```bash
# Увеличить лимит памяти в service файле
sudo nano /etc/systemd/system/telbot.service
# Измените: MemoryLimit=1G

# Перезагрузить конфигурацию
sudo systemctl daemon-reload
sudo systemctl restart telbot
```

## 🔐 Безопасность

### Рекомендации

1. **Не используйте root** - бот работает от пользователя `telbot`
2. **Защитите конфигурацию** - токены и ID каналов конфиденциальны
3. **Настройте firewall** - закройте ненужные порты
4. **Регулярные обновления** - держите систему и зависимости актуальными

```bash
# Ограничить доступ к конфигурации
sudo chmod 600 /opt/telbot/config_custom.json

# Настроить firewall (если используется)
sudo ufw allow ssh
sudo ufw enable
```

## 📈 Мониторинг

### Проверка работы бота

```bash
# Последний пост
sudo journalctl -u telbot | grep "Отправлено" | tail -1

# Статистика за сегодня
sudo journalctl -u telbot --since today | grep "Отправлено" | wc -l

# Проверка памяти
ps aux | grep telbot
```

### Настройка мониторинга через cron

```bash
# Добавить в crontab для отправки уведомлений
sudo crontab -e

# Проверка каждые 5 минут
*/5 * * * * systemctl is-active telbot || systemctl start telbot
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo journalctl -u telbot -n 100`
2. Проверьте статус: `sudo systemctl status telbot`
3. Проверьте конфигурацию: формат JSON, токен бота, ID каналов

## 🔄 Автоматические обновления

Создать скрипт для автоматической перезагрузки в 00:00 (уже встроено в бота):

```bash
# Бот автоматически перезапускается в полночь
# Дополнительная проверка через systemd (опционально)
sudo systemctl edit telbot --full
# Добавьте: Restart=always, RestartSec=10
```

## ✅ Проверка установки

После установки выполните:

```bash
# 1. Проверка статуса
sudo systemctl status telbot

# 2. Проверка логов
sudo journalctl -u telbot -n 20

# 3. Проверка контента
ls -la /opt/telbot/content/

# 4. Проверка через Telegram
# Отправьте боту команду /status
```

Если всё работает, вы увидите:
- ✅ Service active (running)
- ✅ Логи показывают "Запущен цикл автопостинга"
- ✅ Бот отвечает на команды в Telegram

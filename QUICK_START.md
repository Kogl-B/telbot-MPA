# 🚀 Быстрый старт TelBot 2.0 на Ubuntu Timeweb

## Одна команда для установки и запуска

### 1. Загрузите файлы на сервер

```bash
# Подключитесь к серверу
ssh root@ваш_сервер

# Создайте директорию и загрузите файлы
mkdir -p /tmp/telbot
cd /tmp/telbot
```

**Важно!** Загрузите ВСЕ файлы через SCP, SFTP или Git:
- telbot.py
- requirements.txt
- telbot.service
- deploy.sh
- **config/** (папку целиком с config.json внутри!)
- **content/** (папку с контентом)

### 2. Запустите установку одной командой

```bash
cd /tmp/telbot
sudo bash deploy.sh
```

**ВСЁ!** Скрипт автоматически:
- ✅ Установит все пакеты
- ✅ Создаст пользователя
- ✅ Создаст виртуальное окружение
- ✅ Установит зависимости
- ✅ Создаст шаблон config_custom.json
- ✅ Настроит systemd
- ✅ Попытается запустить бота

### 3. Настройте конфигурацию

Бот НЕ ЗАПУСТИТСЯ пока вы не настроите токены:

```bash
nano /opt/telbot/config_custom.json
```

Измените:
```json
{
    "telegram": {
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "admin_id": 123456789
    }
}
```

### 4. Перезапустите бота

```bash
systemctl restart telbot
systemctl status telbot
```

Должно быть: `Active: active (running)`

---

## 📋 Полезные команды

```bash
# Смотреть логи в реальном времени
journalctl -u telbot -f

# Перезапустить бота
systemctl restart telbot

# Остановить
systemctl stop telbot

# Запустить
systemctl start telbot

# Последние 50 строк логов
journalctl -u telbot -n 50
```

---

## 🔧 Если что-то пошло не так

### Бот не запускается?

```bash
# Проверьте логи
journalctl -u telbot -n 100

# Запустите вручную для диагностики
sudo -u telbot /opt/telbot/venv/bin/python /opt/telbot/telbot.py
```

### Нет конфигурации?

```bash
# Отредактируйте конфигурацию
nano /opt/telbot/config_custom.json

# Добавьте ваши токены и настройки
```

### Переустановка

```bash
# Остановите сервис
systemctl stop telbot

# Удалите старую установку
rm -rf /opt/telbot

# Запустите deploy.sh снова
cd /tmp/telbot_deploy
sudo bash deploy.sh
```

---

## 📂 Структура файлов

```
/opt/telbot/                    # Основная директория
├── telbot.py                   # Главный скрипт
├── config_custom.json          # Ваша конфигурация
├── content/                    # Контент для постинга
│   └── 2026-01/               # Папки по месяцам
├── venv/                       # Виртуальное окружение
└── logs/                       # Локальные логи (если есть)

/etc/systemd/system/telbot.service  # Systemd сервис
```

---

## 🎯 Для Timeweb Cloud

### Оптимальная конфигурация сервера:
- **ОС:** Ubuntu 22.04 LTS
- **RAM:** минимум 512MB (рекомендуется 1GB)
- **CPU:** 1 ядро достаточно
- **Диск:** 10GB

### После первого запуска:

1. Настройте конфигурацию:
```bash
nano /opt/telbot/config_custom.json
```

2. Загрузите контент:
```bash
# Используйте SCP или создайте архив
scp -r content/* root@сервер:/opt/telbot/content/
```

3. Перезапустите:
```bash
systemctl restart telbot
```

---

## 🔒 Безопасность

Бот работает от отдельного пользователя `telbot` с ограниченными правами.

```bash
# Проверить пользователя
id telbot

# Проверить права
ls -la /opt/telbot
```

---

## 📞 Мониторинг

```bash
# Проверка каждые 5 секунд
watch -n 5 'systemctl status telbot --no-pager'

# Статистика по памяти
ps aux | grep telbot

# Автоматический мониторинг логов
journalctl -u telbot -f | grep -E "ERROR|SUCCESS|Опубликовано"
```

---

**Готово! Бот работает автоматически 24/7** 🎉

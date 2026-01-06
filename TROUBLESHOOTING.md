# 🔧 Устранение проблем при установке TelBot

## Проблема: apt-get генерирует ошибки зависимостей

### Симптомы:
```
E: Error, pkgProblemResolver::Resolve generated breaks
```

### Решение 1: Исправление проблем с пакетами

```bash
# Очистка кеша
sudo apt-get clean

# Исправление сломанных зависимостей
sudo apt-get install -f

# Настройка незавершенных пакетов
sudo dpkg --configure -a

# Обновление списка пакетов
sudo apt-get update

# Попробуйте установку снова
curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

### Решение 2: Ручная установка зависимостей

```bash
# Установите пакеты по одному
sudo apt-get install python3
sudo apt-get install python3-pip
sudo apt-get install python3-venv
sudo apt-get install git

# Теперь используйте простой установщик
wget https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install_simple.sh
sudo bash install_simple.sh
```

### Решение 3: Полностью ручная установка

```bash
# 1. Установите минимальные зависимости
sudo apt-get install python3 git

# 2. Создайте пользователя
sudo useradd -r -s /bin/false -d /opt/telbot telbot

# 3. Клонируйте репозиторий
sudo git clone https://github.com/Kogl-B/telbot-MPA.git /opt/telbot
cd /opt/telbot

# 4. Создайте виртуальное окружение
sudo python3 -m venv venv

# 5. Установите зависимости Python
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt

# 6. Создайте директории
sudo mkdir -p content logs config
sudo chown -R telbot:telbot /opt/telbot

# 7. Создайте systemd сервис
sudo nano /etc/systemd/system/telbot.service
```

Содержимое `/etc/systemd/system/telbot.service`:
```ini
[Unit]
Description=TelBot - Telegram Auto-Posting Bot
After=network.target

[Service]
Type=simple
User=telbot
WorkingDirectory=/opt/telbot
Environment="PATH=/opt/telbot/venv/bin"
ExecStart=/opt/telbot/venv/bin/python /opt/telbot/telbot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# 8. Запустите сервис
sudo systemctl daemon-reload
sudo systemctl enable telbot
sudo systemctl start telbot

# 9. Проверьте статус
sudo systemctl status telbot
```

---

## Проблема: Python3 не найден

### Решение:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

# Проверка
python3 --version
```

---

## Проблема: Git не найден

### Решение:

```bash
# Ubuntu/Debian
sudo apt-get install git

# Проверка
git --version
```

---

## Проблема: Бот не запускается

### Диагностика:

```bash
# Проверьте статус
sudo systemctl status telbot

# Посмотрите логи
sudo journalctl -u telbot -n 50

# Или полные логи
sudo journalctl -u telbot -f
```

### Частые причины:

1. **Нет прав на файлы:**
```bash
sudo chown -R telbot:telbot /opt/telbot
```

2. **Python зависимости не установлены:**
```bash
cd /opt/telbot
sudo venv/bin/pip install -r requirements.txt
sudo systemctl restart telbot
```

3. **Неправильный путь к Python:**
```bash
# Проверьте путь
which python3
ls -la /opt/telbot/venv/bin/python

# Пересоздайте venv если нужно
cd /opt/telbot
sudo rm -rf venv
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R telbot:telbot /opt/telbot
sudo systemctl restart telbot
```

---

## Проблема: Нет контента для постинга

Это не ошибка! Бот ждет контента. Добавьте:

```bash
# Создайте структуру
sudo mkdir -p /opt/telbot/content/mpa_disney/"Princess Jasmin"

# Скопируйте изображения
sudo cp ваши_картинки/* /opt/telbot/content/mpa_disney/"Princess Jasmin"/

# Установите права
sudo chown -R telbot:telbot /opt/telbot/content/
```

---

## Проблема: Бот установлен, но нужно переустановить

```bash
# Остановите и удалите
sudo systemctl stop telbot
sudo systemctl disable telbot
sudo rm /etc/systemd/system/telbot.service
sudo rm -rf /opt/telbot
sudo userdel telbot

# Установите заново
curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

---

## Проблема: Нет доступа к серверу

### Если используете облачный сервер (VPS):

1. Убедитесь что подключены по SSH
2. Проверьте что у вас есть права root: `sudo -i`
3. Проверьте что сервер имеет доступ в интернет: `ping google.com`

---

## Получить помощь

Если ничего не помогает:

1. Соберите логи:
```bash
sudo journalctl -u telbot -n 100 > telbot_error.log
```

2. Проверьте конфигурацию:
```bash
cat /opt/telbot/config_custom.json
```

3. Проверьте версию системы:
```bash
cat /etc/os-release
python3 --version
```

---

## Быстрые команды для диагностики

```bash
# Всё в одном
sudo systemctl status telbot
sudo journalctl -u telbot -n 20
ls -la /opt/telbot/
python3 --version
git --version
```

---

**Совет:** Используйте `install_simple.sh` если основной установщик не работает из-за проблем с apt.

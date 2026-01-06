#!/bin/bash

# TelBot 2.0 - Скрипт развертывания на Ubuntu Server
# Использование: sudo bash deploy.sh

set -e

echo "🚀 TelBot 2.0 - Полное развертывание на Ubuntu Server"
echo "======================================================"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите скрипт с правами root: sudo bash deploy.sh${NC}"
    exit 1
fi

# Переменные
INSTALL_DIR="/opt/telbot"
USER="telbot"
GROUP="telbot"
LOG_DIR="/var/log/telbot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}📦 Установка системных пакетов...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv git rsync

echo -e "${YELLOW}👤 Создание пользователя telbot...${NC}"
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$USER"
    echo -e "${GREEN}✅ Пользователь $USER создан${NC}"
else
    echo -e "${GREEN}✅ Пользователь $USER уже существует${NC}"
fi

echo -e "${YELLOW}📁 Создание директорий...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"

echo -e "${YELLOW}⏹️  Остановка сервиса (если запущен)...${NC}"
systemctl stop telbot 2>/dev/null || true
systemctl disable telbot 2>/dev/null || true

echo -e "${YELLOW}🧹 Очистка старой установки...${NC}"
rm -rf "$INSTALL_DIR/venv"

echo -e "${YELLOW}📋 Копирование файлов...${NC}"
rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' "$SCRIPT_DIR/" "$INSTALL_DIR/" || cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

chown -R $USER:$GROUP "$INSTALL_DIR"
chown -R $USER:$GROUP "$LOG_DIR"

echo -e "${YELLOW}🐍 Создание виртуального окружения...${NC}"
cd "$INSTALL_DIR"
sudo -u $USER python3 -m venv venv

if [ ! -f "$INSTALL_DIR/venv/bin/python" ]; then
    echo -e "${RED}❌ Ошибка создания виртуального окружения!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"

echo -e "${YELLOW}📦 Установка Python зависимостей...${NC}"
sudo -u $USER "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
sudo -u $USER "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo -e "${GREEN}✅ Зависимости установлены${NC}"

echo -e "${YELLOW}⚙️ Проверка конфигурации...${NC}"

# Проверяем наличие базового конфига
if [ ! -f "$INSTALL_DIR/config/config.json" ]; then
    echo -e "${RED}❌ Базовый файл config/config.json не найден!${NC}"
    echo -e "${RED}Убедитесь, что папка config/ с config.json была скопирована на сервер${NC}"
    exit 1
fi

# Создаем config_custom.json если его нет
if [ ! -f "$INSTALL_DIR/config_custom.json" ]; then
    echo -e "${YELLOW}⚠️  Файл config_custom.json не найден. Создаю из примера...${NC}"
    
    # Создаем минимальный config_custom.json
    cat > "$INSTALL_DIR/config_custom.json" << 'EOF'
{
    "telegram": {
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "admin_id": 0
    },
    "channels": {
        "atla": {
            "enabled": false,
            "chat_id": "@your_channel"
        },
        "naruto": {
            "enabled": false,
            "chat_id": "@your_channel"
        },
        "harry_potter": {
            "enabled": false,
            "chat_id": "@your_channel"
        },
        "mpa_disney": {
            "enabled": false,
            "chat_id": "@your_channel"
        }
    },
    "settings": {
        "timezone": "Europe/Moscow"
    }
}
EOF
    
    chown $USER:$GROUP "$INSTALL_DIR/config_custom.json"
    chmod 600 "$INSTALL_DIR/config_custom.json"
    
    echo -e "${GREEN}✅ Создан шаблон config_custom.json${NC}"
    echo -e "${RED}⚠️  ВАЖНО: Отредактируйте $INSTALL_DIR/config_custom.json${NC}"
    echo -e "${RED}   и добавьте ваш bot_token и admin_id!${NC}"
else
    echo -e "${GREEN}✅ Файл config_custom.json найден${NC}"
fi

echo -e "${GREEN}✅ Конфигурация проверена${NC}"

echo -e "${YELLOW}🔧 Установка systemd service...${NC}"
cp "$INSTALL_DIR/telbot.service" /etc/systemd/system/telbot.service
chmod 644 /etc/systemd/system/telbot.service
systemctl daemon-reload

echo -e "${YELLOW}🔐 Установка прав доступа...${NC}"
chmod 755 "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/telbot.py"
chmod +x "$INSTALL_DIR/venv/bin/python" 2>/dev/null || true
chmod +x "$INSTALL_DIR/venv/bin/python3" 2>/dev/null || true

echo -e "${YELLOW}🧪 Тестовый запуск бота...${NC}"
cd "$INSTALL_DIR"
if sudo -u $USER timeout 5 "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/telbot.py" --test 2>&1 | grep -q "Error\|Traceback"; then
    echo -e "${YELLOW}⚠️  Возможны проблемы с конфигурацией, но продолжаем...${NC}"
else
    echo -e "${GREEN}✅ Тестовый запуск успешен${NC}"
fi

echo -e "${YELLOW}🚀 Включение и запуск сервиса...${NC}"
systemctl enable telbot
systemctl start telbot

echo -e "${YELLOW}⏳ Ожидание запуска (5 секунд)...${NC}"
sleep 5

echo ""
echo "========================================"
if systemctl is-active --quiet telbot; then
    echo -e "${GREEN}✅✅✅ УСПЕШНО! Бот запущен и работает! ✅✅✅${NC}"
    echo ""
    echo -e "${GREEN}📊 Статус сервиса:${NC}"
    systemctl status telbot --no-pager -l
else
    echo -e "${RED}⚠️  Бот установлен, но не запущен${NC}"
    echo -e "${YELLOW}Проверьте логи:${NC}"
    journalctl -u telbot -n 20 --no-pager
    echo ""
    echo -e "${YELLOW}Попробуйте запустить вручную:${NC}"
    echo "sudo -u telbot /opt/telbot/venv/bin/python /opt/telbot/telbot.py"
fi

echo ""
echo "========================================"
echo -e "${GREEN}📝 Полезные команды:${NC}"
echo "  systemctl status telbot   - Статус бота"
echo "  systemctl restart telbot  - Перезапустить"
echo "  systemctl stop telbot     - Остановить"
echo "  journalctl -u telbot -f   - Логи в реальном времени"
echo "  journalctl -u telbot -n 50 - Последние 50 строк"
echo ""
echo -e "${YELLOW}📂 Расположение файлов:${NC}"
echo "  Конфигурация: $INSTALL_DIR/config_custom.json"
echo "  Базовый конфиг: $INSTALL_DIR/config/config.json"
echo "  Контент: $INSTALL_DIR/content/"
echo "  Логи: journalctl -u telbot"
echo ""
echo -e "${YELLOW}⚙️  Следующие шаги:${NC}"
echo "  1. Отредактируйте конфигурацию:"
echo "     nano $INSTALL_DIR/config_custom.json"
echo "  2. Добавьте bot_token и admin_id"
echo "  3. Перезапустите бота:"
echo "     systemctl restart telbot"
echo ""

#!/bin/bash

# TelBot 2.0 - Скрипт для автоматической загрузки и установки на сервер
# Использование: bash install_on_server.sh ваш_сервер
# Пример: bash install_on_server.sh root@123.45.67.89

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ -z "$1" ]; then
    echo -e "${RED}❌ Укажите адрес сервера!${NC}"
    echo "Использование: bash install_on_server.sh root@ваш_сервер"
    echo "Пример: bash install_on_server.sh root@123.45.67.89"
    exit 1
fi

SERVER="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}🚀 TelBot 2.0 - Автоматическая установка на сервер${NC}"
echo "Сервер: $SERVER"
echo "========================================"

# Проверка SSH доступа
echo -e "${YELLOW}🔐 Проверка подключения к серверу...${NC}"
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo Connected" &>/dev/null; then
    echo -e "${RED}❌ Не удалось подключиться к серверу!${NC}"
    echo "Проверьте адрес и SSH ключи"
    exit 1
fi
echo -e "${GREEN}✅ Подключение успешно${NC}"

# Создание временной директории на сервере
echo -e "${YELLOW}📁 Создание директории на сервере...${NC}"
ssh "$SERVER" "mkdir -p /tmp/telbot_deploy"

# Копирование файлов
echo -e "${YELLOW}📋 Копирование файлов на сервер...${NC}"
rsync -avz --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='archives' \
    --exclude='temp' \
    "$SCRIPT_DIR/" "$SERVER:/tmp/telbot_deploy/"

echo -e "${GREEN}✅ Файлы скопированы${NC}"

# Запуск установки
echo ""
echo -e "${YELLOW}🚀 Запуск установки на сервере...${NC}"
echo "========================================"
ssh -t "$SERVER" "cd /tmp/telbot_deploy && bash deploy.sh"

echo ""
echo -e "${GREEN}✅✅✅ УСТАНОВКА ЗАВЕРШЕНА! ✅✅✅${NC}"
echo ""
echo -e "${YELLOW}📋 Полезные команды для управления:${NC}"
echo "  ssh $SERVER 'systemctl status telbot'    - Проверить статус"
echo "  ssh $SERVER 'journalctl -u telbot -f'    - Смотреть логи"
echo "  ssh $SERVER 'systemctl restart telbot'   - Перезапустить"
echo ""

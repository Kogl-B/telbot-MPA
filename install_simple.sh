#!/bin/bash
#
# Простой установщик TelBot для Ubuntu (без apt)
# Используйте этот скрипт если основной установщик не работает
#

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/telbot"
SERVICE_NAME="telbot"
REPO_URL="https://github.com/Kogl-B/telbot-MPA.git"

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TelBot - Простой установщик"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверка root
if [[ $EUID -ne 0 ]]; then
    print_error "Запустите с правами root: sudo bash install_simple.sh"
    exit 1
fi

# Проверка Python3
if ! command -v python3 &> /dev/null; then
    print_error "Python3 не найден. Установите: apt-get install python3 python3-pip python3-venv"
    exit 1
fi

# Проверка Git
if ! command -v git &> /dev/null; then
    print_error "Git не найден. Установите: apt-get install git"
    exit 1
fi

print_success "Python3 и Git найдены"

# Создание пользователя
if ! id "$SERVICE_NAME" &>/dev/null; then
    print_info "Создание пользователя $SERVICE_NAME..."
    useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_NAME"
fi

# Удаление старой установки
if [ -d "$INSTALL_DIR" ]; then
    print_info "Удаление старой установки..."
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    rm -rf "$INSTALL_DIR"
fi

# Клонирование
print_info "Клонирование репозитория..."
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Создание venv
print_info "Создание виртуального окружения..."
python3 -m venv venv

# Установка зависимостей
print_info "Установка зависимостей Python..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

# Создание директорий
mkdir -p content logs config
chown -R $SERVICE_NAME:$SERVICE_NAME "$INSTALL_DIR"

# Создание сервиса
print_info "Создание systemd сервиса..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
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
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    print_success "Бот успешно установлен и запущен!"
    echo ""
    echo "Управление:"
    echo "  systemctl status telbot"
    echo "  systemctl restart telbot"
    echo "  journalctl -u telbot -f"
else
    print_error "Ошибка запуска. Проверьте: journalctl -u telbot -n 50"
fi

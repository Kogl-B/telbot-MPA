#!/bin/bash
#
# Автоматический установщик TelBot для Ubuntu
# 
# Использование:
#   curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | bash
#   или
#   wget -qO- https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | bash
#

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переменные
INSTALL_DIR="/opt/telbot"
SERVICE_NAME="telbot"
REPO_URL="https://github.com/Kogl-B/telbot-MPA.git"
PYTHON_VERSION="3.10"

# Функции вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Проверка прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Этот скрипт должен быть запущен с правами root"
        print_info "Используйте: sudo bash install.sh"
        exit 1
    fi
}

# Определение пользователя
get_real_user() {
    if [ -n "$SUDO_USER" ]; then
        echo "$SUDO_USER"
    else
        echo "root"
    fi
}

# Проверка системы
check_system() {
    print_header "Проверка системы"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        print_info "ОС: $NAME $VERSION"
        
        if [[ ! "$ID" =~ ^(ubuntu|debian)$ ]]; then
            print_warning "Скрипт тестировался на Ubuntu/Debian"
            print_info "Продолжить установку? (y/n)"
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                exit 0
            fi
        fi
    fi
    
    print_success "Система поддерживается"
}

# Исправление проблем с пакетами
fix_package_issues() {
    print_header "Исправление проблем с пакетами"
    
    print_info "Очистка кеша пакетов..."
    apt-get clean > /dev/null 2>&1 || true
    
    print_info "Исправление сломанных зависимостей..."
    apt-get install -f -y > /dev/null 2>&1 || true
    
    print_info "Настройка незавершенных пакетов..."
    dpkg --configure -a > /dev/null 2>&1 || true
    
    print_info "Обновление списка пакетов..."
    apt-get update -qq 2>&1 | grep -v "^Get:" | grep -v "^Hit:" | grep -v "^Reading" || true
    
    print_success "Проблемы с пакетами исправлены"
}

# Установка зависимостей
install_dependencies() {
    print_header "Установка зависимостей"
    
    print_info "Обновление списка пакетов..."
    apt-get update -qq
    
    print_info "Исправление возможных проблем с пакетами..."
    apt-get install -f -y > /dev/null 2>&1 || true
    dpkg --configure -a > /dev/null 2>&1 || true
    
    print_info "Установка необходимых пакетов..."
    
    # Устанавливаем пакеты по одному для лучшей диагностики
    PACKAGES="python3 python3-pip python3-venv git curl wget"
    
    for pkg in $PACKAGES; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            print_info "Установка $pkg..."
            if ! apt-get install -y -qq "$pkg" 2>/dev/null; then
                print_warning "Не удалось установить $pkg через apt, пробуем альтернативный метод..."
                apt-get install -y --fix-broken "$pkg" 2>/dev/null || apt-get install -y "$pkg" || true
            fi
        else
            print_info "$pkg уже установлен"
        fi
    done
    
    # Проверка критичных пакетов
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 не установлен. Установите вручную: apt-get install python3"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git не установлен. Установите вручную: apt-get install git"
        exit 1
    fi
    
    print_success "Зависимости установлены"
}

# Создание пользователя для бота
create_bot_user() {
    print_header "Создание пользователя для бота"
    
    if id "$SERVICE_NAME" &>/dev/null; then
        print_info "Пользователь $SERVICE_NAME уже существует"
    else
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_NAME"
        print_success "Пользователь $SERVICE_NAME создан"
    fi
}

# Клонирование репозитория
clone_repository() {
    print_header "Клонирование репозитория"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Директория $INSTALL_DIR уже существует"
        print_info "Удалить и переустановить? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            systemctl stop $SERVICE_NAME 2>/dev/null || true
            rm -rf "$INSTALL_DIR"
            print_info "Старая версия удалена"
        else
            print_info "Обновление существующей установки..."
            cd "$INSTALL_DIR"
            sudo -u $SERVICE_NAME git pull
            print_success "Репозиторий обновлен"
            return
        fi
    fi
    
    print_info "Клонирование из $REPO_URL..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    
    # Установка прав
    chown -R $SERVICE_NAME:$SERVICE_NAME "$INSTALL_DIR"
    
    print_success "Репозиторий клонирован в $INSTALL_DIR"
}

# Создание виртуального окружения и установка зависимостей Python
setup_python_env() {
    print_header "Настройка Python окружения"
    
    cd "$INSTALL_DIR"
    
    # Проверка наличия python3-venv
    if ! python3 -m venv --help &> /dev/null; then
        print_warning "python3-venv не найден, устанавливаем..."
        apt-get install -y python3-venv > /dev/null 2>&1 || true
    fi
    
    print_info "Создание виртуального окружения..."
    if ! sudo -u $SERVICE_NAME python3 -m venv venv 2>/dev/null; then
        print_warning "Не удалось создать venv стандартным способом, пробуем альтернативу..."
        python3 -m venv venv
        chown -R $SERVICE_NAME:$SERVICE_NAME venv
    fi
    
    print_info "Обновление pip..."
    sudo -u $SERVICE_NAME venv/bin/pip install --upgrade pip -q 2>/dev/null || \
        venv/bin/pip install --upgrade pip -q
    
    print_info "Установка Python зависимостей (это может занять минуту)..."
    if ! sudo -u $SERVICE_NAME venv/bin/pip install -r requirements.txt -q 2>/dev/null; then
        print_warning "Установка от пользователя telbot не удалась, пробуем от root..."
        venv/bin/pip install -r requirements.txt -q
        chown -R $SERVICE_NAME:$SERVICE_NAME venv
    fi
    
    print_success "Python окружение настроено"
}

# Создание необходимых директорий
create_directories() {
    print_header "Создание директорий"
    
    cd "$INSTALL_DIR"
    
    mkdir -p content logs config
    chown -R $SERVICE_NAME:$SERVICE_NAME content logs config
    
    print_success "Директории созданы"
}

# Создание systemd сервиса
create_systemd_service() {
    print_header "Создание systemd сервиса"
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=TelBot - Telegram Auto-Posting Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_NAME
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/telbot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    
    print_success "Systemd сервис создан"
}

# Запуск бота
start_bot() {
    print_header "Запуск бота"
    
    print_info "Включение автозапуска..."
    systemctl enable $SERVICE_NAME
    
    print_info "Запуск сервиса..."
    systemctl start $SERVICE_NAME
    
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Бот успешно запущен!"
    else
        print_error "Ошибка запуска бота"
        print_info "Проверьте логи: journalctl -u $SERVICE_NAME -f"
        exit 1
    fi
}

# Показ информации после установки
show_info() {
    print_header "Установка завершена!"
    
    echo -e "${GREEN}✅ TelBot успешно установлен и запущен!${NC}\n"
    
    echo "📁 Директория установки: $INSTALL_DIR"
    echo "👤 Пользователь: $SERVICE_NAME"
    echo "🔧 Сервис: $SERVICE_NAME.service"
    echo ""
    echo "📝 Полезные команды:"
    echo "  • Проверить статус:     systemctl status $SERVICE_NAME"
    echo "  • Остановить бота:      systemctl stop $SERVICE_NAME"
    echo "  • Запустить бота:       systemctl start $SERVICE_NAME"
    echo "  • Перезапустить бота:   systemctl restart $SERVICE_NAME"
    echo "  • Посмотреть логи:      journalctl -u $SERVICE_NAME -f"
    echo "  • Логи бота:            tail -f $INSTALL_DIR/logs/telbot_*.log"
    echo ""
    echo "📂 Для добавления контента используйте:"
    echo "   $INSTALL_DIR/content/"
    echo ""
    echo "⚙️  Конфигурация:"
    echo "   $INSTALL_DIR/config_custom.json"
    echo ""
    
    print_info "Для просмотра логов в реальном времени:"
    echo "   journalctl -u $SERVICE_NAME -f"
}

# Основная функция
main() {
    clear
    
    print_header "🤖 TelBot - Установщик для Ubuntu"
    echo "Версия: 2.0"
    echo "Репозиторий: $REPO_URL"
    echo ""
    
    check_root
    check_system
    fix_package_issues
    install_dependencies
    create_bot_user
    clone_repository
    setup_python_env
    create_directories
    create_systemd_service
    start_bot
    show_info
    
    echo ""
    print_success "Готово! Бот работает! 🚀"
}

# Запуск
main "$@"

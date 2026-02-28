#!/bin/bash

# Быстрое исправление конфигурации TelBot 2.0
# Использование: bash fix_config.sh

echo "🔧 TelBot 2.0 - Быстрое исправление конфигурации"
echo "================================================"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="/opt/telbot"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите с правами root: sudo bash fix_config.sh${NC}"
    exit 1
fi

# Проверка существования базового конфига
if [ ! -f "$INSTALL_DIR/config/config.json" ]; then
    echo -e "${RED}❌ Базовый конфиг не найден: $INSTALL_DIR/config/config.json${NC}"
    echo -e "${YELLOW}Убедитесь, что папка config/ была скопирована на сервер${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Базовый конфиг найден${NC}"

# Создание config_custom.json
echo -e "${YELLOW}📝 Создание config_custom.json...${NC}"

cat > "$INSTALL_DIR/config_custom.json" << 'EOF'
{
    "telegram": {
        "bot_token": "ЗАМЕНИТЕ_НА_ВАШ_ТОКЕН",
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

chown telbot:telbot "$INSTALL_DIR/config_custom.json"
chmod 600 "$INSTALL_DIR/config_custom.json"

echo -e "${GREEN}✅ Файл config_custom.json создан${NC}"
echo ""
echo -e "${YELLOW}⚠️  СЛЕДУЮЩИЕ ШАГИ:${NC}"
echo ""
echo "1. Отредактируйте конфигурацию:"
echo "   nano $INSTALL_DIR/config_custom.json"
echo ""
echo "2. Замените:"
echo "   - bot_token: получите у @BotFather"
echo "   - admin_id: ваш Telegram ID"
echo ""
echo "3. Перезапустите бота:"
echo "   systemctl restart telbot"
echo "   systemctl status telbot"
echo ""
echo "4. Смотрите логи:"
echo "   journalctl -u telbot -f"
echo ""

#!/bin/bash

# Скрипт для создания архива для развертывания

echo "📦 Создание архива TelBot 2.0 для развертывания..."

# Создаем временную директорию
TEMP_DIR=$(mktemp -d)
DEPLOY_DIR="$TEMP_DIR/telbot"
mkdir -p "$DEPLOY_DIR"

# Копируем необходимые файлы
echo "📋 Копирование файлов..."
cp telbot.py "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"
cp telbot.service "$DEPLOY_DIR/"
cp deploy.sh "$DEPLOY_DIR/"
cp DEPLOYMENT.md "$DEPLOY_DIR/"
cp README.md "$DEPLOY_DIR/" 2>/dev/null || true

# Копируем конфигурацию
cp -r config "$DEPLOY_DIR/"
cp config_custom.json "$DEPLOY_DIR/" 2>/dev/null || echo "⚠️ config_custom.json не найден, создайте его на сервере"

# Создаем пустые папки
mkdir -p "$DEPLOY_DIR/content"
mkdir -p "$DEPLOY_DIR/logs"
mkdir -p "$DEPLOY_DIR/temp"

# Создаем README для контента
cat > "$DEPLOY_DIR/content/README.md" << 'EOF'
# Структура контента

Поместите контент в следующую структуру:

```
content/
├── 2026-01/
│   ├── channel1/
│   │   ├── category1/
│   │   │   ├── image1.jpg
│   │   │   ├── image2.jpg
│   │   └── category2/
│   └── channel2/
└── 2026-02/
    └── ...
```

Каждые 30 минут бот публикует 1 изображение в один из каналов по очереди.
После публикации изображение удаляется.
EOF

# Создаем архив
ARCHIVE_NAME="telbot_deploy_$(date +%Y%m%d_%H%M%S).tar.gz"
echo "📦 Создание архива $ARCHIVE_NAME..."
cd "$TEMP_DIR"
tar -czf "$ARCHIVE_NAME" telbot/

# Перемещаем архив в текущую директорию
mv "$ARCHIVE_NAME" "$OLDPWD/"
cd "$OLDPWD"

# Очищаем временные файлы
rm -rf "$TEMP_DIR"

echo "✅ Архив создан: $ARCHIVE_NAME"
echo ""
echo "📤 Загрузите архив на сервер:"
echo "   scp $ARCHIVE_NAME user@server:/tmp/"
echo ""
echo "📥 На сервере выполните:"
echo "   cd /tmp"
echo "   tar -xzf $ARCHIVE_NAME"
echo "   cd telbot"
echo "   sudo bash deploy.sh"

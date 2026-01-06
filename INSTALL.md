# 🚀 Установка TelBot на Ubuntu - Один Клик!

## Супербыстрая установка

Подключитесь к вашему Ubuntu серверу и выполните **одну команду**:

```bash
curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

**Готово!** 🎉 Бот установлен и работает!

---

## Что произошло?

Установщик автоматически:
- ✅ Установил все необходимые зависимости (Python, git и т.д.)
- ✅ Создал пользователя `telbot` для безопасности
- ✅ Клонировал репозиторий в `/opt/telbot`
- ✅ Настроил Python виртуальное окружение
- ✅ Создал systemd сервис для автозапуска
- ✅ Запустил бота как службу

---

## Управление ботом

### Основные команды

```bash
# Проверить статус
sudo systemctl status telbot

# Перезапустить
sudo systemctl restart telbot

# Остановить
sudo systemctl stop telbot

# Запустить
sudo systemctl start telbot
```

### Просмотр логов

```bash
# Логи в реальном времени (systemd)
sudo journalctl -u telbot -f

# Логи самого бота
sudo tail -f /opt/telbot/logs/telbot_*.log
```

---

## Добавление контента

Бот ожидает контент в папке `/opt/telbot/content/`

### Структура папок

```
/opt/telbot/content/
├── mpa_disney/
│   ├── Princess Jasmin/
│   ├── Elsa Frozzen/
│   └── ...
├── harry_potter/
│   ├── Hermione Grander/
│   └── ...
├── atla/
│   ├── Katara/
│   └── ...
└── naruto/
    ├── Sakura/
    └── ...
```

### Как добавить контент

```bash
# Создайте папку для персонажа
sudo mkdir -p /opt/telbot/content/mpa_disney/"Princess Jasmin"

# Скопируйте изображения (с вашего компьютера на сервер)
scp ваши_изображения/* user@server:/tmp/
sudo mv /tmp/*.jpg /opt/telbot/content/mpa_disney/"Princess Jasmin"/

# Установите правильные права
sudo chown -R telbot:telbot /opt/telbot/content/
```

---

## Telegram команды

В чате с ботом доступны команды:

- `/start` - Начало работы
- `/status` - Статус бота
- `/help` - Справка

Админ команды (только для ID: 1980584772):
- `/start_posting` - Запустить постинг
- `/stop_posting` - Остановить постинг

---

## Настроенные каналы

Бот уже настроен для работы с 4 каналами:

1. **Universe Disney Ero Art +18** (mpa_disney)
2. **Universe Harry Potter Erotic Art +18** (harry_potter)
3. **Universe The Avatar Legend of AANG Ero Art +18** (atla)
4. **Universe Naruto Ero Art +18** (naruto)

---

## Расписание постинга

По умолчанию:
- ⏱ Интервал между постами: **30 минут**
- 🔄 Автоматический перезапуск: **00:00 каждый день**

Изменить можно в файле `/opt/telbot/config_custom.json`

---

## Проблемы?

### Бот не запускается

```bash
# Проверьте статус
sudo systemctl status telbot

# Посмотрите логи
sudo journalctl -u telbot -n 50
```

### Нет контента для постинга

```bash
# Проверьте наличие файлов
ls -la /opt/telbot/content/

# Проверьте права
sudo chown -R telbot:telbot /opt/telbot/content/
```

### Переустановка

```bash
# Остановите бота
sudo systemctl stop telbot

# Удалите папку
sudo rm -rf /opt/telbot

# Запустите установщик снова
curl -fsSL https://raw.githubusercontent.com/Kogl-B/telbot-MPA/main/install.sh | sudo bash
```

---

## Обновление бота

```bash
cd /opt/telbot
sudo -u telbot git pull
sudo systemctl restart telbot
```

---

## Безопасность

- ✅ Бот работает от отдельного пользователя `telbot` (не root)
- ✅ Токен бота зашит в код (не нужен внешний конфиг)
- ✅ Доступ к админ-командам только для ID: 1980584772

---

## Поддержка

Если что-то пошло не так, проверьте:

1. Статус сервиса: `sudo systemctl status telbot`
2. Логи systemd: `sudo journalctl -u telbot -f`
3. Логи бота: `sudo tail -f /opt/telbot/logs/telbot_*.log`

---

**Готово к работе! 🚀**

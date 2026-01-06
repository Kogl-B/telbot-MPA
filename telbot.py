#!/usr/bin/env python3
"""
TelBot 2.0 - Telegram Auto-Posting Bot (Server Version)
=======================================================
Серверная версия бота для автоматического постинга контента в Telegram-каналы.

Эта версия работает ТОЛЬКО с готовым контентом в папке content/
Сортировка и подготовка контента выполняется отдельной программой (content_manager.py)

Структура папки content/:
    content/
    ├── atla/           # Avatar: The Last Airbender
    │   ├── Azula/
    │   ├── Katara/
    │   └── ...
    ├── naruto/
    ├── harry_potter/
    └── mpa_disney/

Использование:
    python telbot.py                    # Запуск бота
    python telbot.py --status           # Показать статус
    python telbot.py --help            # Справка
"""

import os
import sys
import json
import random
import shutil
import asyncio
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps

# ============================================
# БАЗОВАЯ КОНФИГУРАЦИЯ
# ============================================

BASE_DIR = Path(__file__).parent

# Пути к папкам (относительно BASE_DIR)
PATHS = {
    "content": BASE_DIR / "content",      # Контент для постинга
    "logs": BASE_DIR / "logs",
    "config": BASE_DIR / "config",
}

# Создаём папки
for path in PATHS.values():
    path.mkdir(parents=True, exist_ok=True)

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

log_file = PATHS["logs"] / f"telbot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# ============================================

def load_config() -> dict:
    """Загружает конфигурацию из файлов"""
    # Токен бота зашит в код
    BOT_TOKEN = "7601569334:AAGGST1To37UzoIfw1z34X1wytqS71Z1nnA"
    
    config_file = PATHS["config"] / "config.json"
    custom_config_file = BASE_DIR / "config_custom.json"
    
    # Если config.json не существует, создаем базовую конфигурацию
    if not config_file.exists():
        config = {
            "telegram": {
                "bot_token": BOT_TOKEN,
                "admin_ids": []
            },
            "channels": {},
            "settings": {
                "supported_formats": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm"]
            }
        }
    else:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    
    # Всегда устанавливаем токен из кода
    if "telegram" not in config:
        config["telegram"] = {}
    config["telegram"]["bot_token"] = BOT_TOKEN
    
    # Устанавливаем пустой список admin_ids, если его нет
    if "admin_ids" not in config["telegram"]:
        config["telegram"]["admin_ids"] = []
    
    # Загружаем пользовательские настройки
    if custom_config_file.exists():
        with open(custom_config_file, "r", encoding="utf-8") as f:
            custom = json.load(f)
            # Глубокое обновление конфига
            deep_update(config, custom)
        logger.info("✅ Загружена пользовательская конфигурация")
    
    return config

def deep_update(base: dict, update: dict) -> dict:
    """Рекурсивное обновление словаря"""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base

CONFIG = load_config()

# Убедимся что supported_formats доступен на верхнем уровне
if "supported_formats" not in CONFIG:
    CONFIG["supported_formats"] = CONFIG.get("settings", {}).get("supported_formats", [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm"])

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_enabled_channels() -> Dict:
    """Возвращает только включенные каналы"""
    return {
        key: cfg for key, cfg in CONFIG["channels"].items()
        if cfg.get("enabled", True)
    }

def generate_unique_filename(directory: Path, filename: str) -> str:
    """Генерирует уникальное имя файла"""
    path = directory / filename
    if not path.exists():
        return filename
    
    stem = path.stem
    suffix = path.suffix
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        if not (directory / new_name).exists():
            return new_name
        counter += 1

def find_category_by_hashtag(hashtag: str) -> Optional[Dict]:
    """Находит категорию по хештегу"""
    hashtag_lower = hashtag.lower()
    
    for channel_key, channel_config in CONFIG["channels"].items():
        for cat_key, cat_config in channel_config.get("categories", {}).items():
            for tag in cat_config.get("hashtags", []):
                if tag.lower() == hashtag_lower:
                    return {
                        "channel_key": channel_key,
                        "category": cat_config.get("folder_name", cat_key),
                        "hashtags": cat_config.get("hashtags", [])
                    }
    return None

# ============================================
# ПРОВЕРКА ДОСТУПА
# ============================================

def admin_only(func):
    """Декоратор для проверки админских прав"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in CONFIG["telegram"]["admin_ids"]:
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ============================================
# СТАТИСТИКА КОНТЕНТА
# ============================================

def get_content_stats() -> Dict:
    """Собирает статистику по контенту из месячных папок"""
    stats = {
        "total_images": 0,
        "channels": {},
        "by_channel": {}
    }
    
    content_path = PATHS["content"]
    if not content_path.exists():
        return stats
    
    # Ищем месячные папки (YYYY-MM)
    month_folders = [d for d in content_path.iterdir() 
                    if d.is_dir() and re.match(r'\d{4}-\d{2}', d.name)]
    
    enabled_channels = get_enabled_channels()
    
    for channel_key, channel_config in enabled_channels.items():
        channel_stats = {"total": 0, "categories": {}}
        
        # Собираем контент из всех месяцев
        for month_folder in month_folders:
            channel_path = month_folder / channel_key
            if channel_path.exists():
                for cat_dir in channel_path.iterdir():
                    if cat_dir.is_dir():
                        supported_formats = CONFIG.get("supported_formats") or CONFIG.get("settings", {}).get("supported_formats", [".jpg", ".jpeg", ".png", ".gif", ".webp"])
                        count = sum(1 for f in cat_dir.iterdir() 
                                   if f.suffix.lower() in supported_formats)
                        if cat_dir.name not in channel_stats["categories"]:
                            channel_stats["categories"][cat_dir.name] = 0
                        channel_stats["categories"][cat_dir.name] += count
                        channel_stats["total"] += count
        
        stats["channels"][channel_key] = channel_stats
        stats["total_images"] += channel_stats["total"]
    
    return stats

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_stats_message() -> str:
    """Форматирует статистику для сообщения"""
    stats = get_content_stats()
    
    lines = ["📊 *Статистика контента*\n"]
    lines.append(f"📁 Всего изображений: *{stats['total_images']}*\n")
    
    # Прогноз
    schedule = CONFIG.get("schedule", {})
    interval = schedule.get("post_interval_minutes", 30)
    # Каждые N минут = 1 пост в 1 канал (по очереди)
    posts_per_day = (24 * 60) // interval  # Всего постов в день
    enabled_count = len(get_enabled_channels())
    
    if stats['total_images'] > 0:
        days_left = stats['total_images'] / posts_per_day if posts_per_day > 0 else 0
        lines.append(f"⏱ Контента хватит на: *{days_left:.1f}* дней")
        lines.append(f"📊 Постов в день: *{posts_per_day}* ({interval} мин интервал)")
        if enabled_count > 0:
            posts_per_channel = posts_per_day / enabled_count
            lines.append(f"📺 На канал: *{posts_per_channel:.1f}* постов/день\n")
        else:
            lines.append("")
    
    # По каналам
    lines.append("*По каналам:*")
    for channel_key, channel_stats in stats["channels"].items():
        channel_name = CONFIG["channels"][channel_key].get("name", channel_key)
        # Экранируем имя канала
        safe_name = escape_markdown(channel_name)
        lines.append(f"\n📺 *{safe_name}*: {channel_stats['total']} шт\\.")
        
        if channel_stats["categories"]:
            for cat, count in sorted(channel_stats["categories"].items()):
                # Экранируем имя категории
                safe_cat = escape_markdown(cat)
                lines.append(f"   • {safe_cat}: {count}")
    
    return "\n".join(lines)

# ============================================
# ЗАГРУЗКА КОНТЕНТА ЧЕРЕЗ БОТА
# ============================================

class PhotoUploader:
    """Обработка загрузки фото через бота"""
    
    def __init__(self):
        self.content_path = PATHS["content"]
        self.temp_path = BASE_DIR / "temp"
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
    async def process_photos(self, photos: list, caption: str, bot) -> dict:
        """Обрабатывает загруженные фото по хештегу в подписи"""
        result = {"saved": 0, "errors": 0, "category": None, "channel": None}
        
        # Ищем хештег в подписи
        hashtag = None
        if caption:
            words = caption.split()
            for word in words:
                if word.startswith("#"):
                    hashtag = word
                    break
        
        if not hashtag:
            return {"error": "Не найден хештег в подписи. Добавьте хештег, например #azula"}
        
        # Находим категорию по хештегу
        cat_info = find_category_by_hashtag(hashtag)
        if not cat_info:
            return {"error": f"Хештег {hashtag} не найден. Проверьте правильность написания."}
        
        result["category"] = cat_info["category"]
        result["channel"] = cat_info["channel_key"]
        
        # Путь для сохранения
        target_dir = self.content_path / cat_info["channel_key"] / cat_info["category"]
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Скачиваем и сохраняем фото
        import random
        from datetime import datetime
        
        for idx, photo in enumerate(photos, 1):
            try:
                # Получаем файл (берём самый большой размер)
                if hasattr(photo, 'photo'):
                    file = await bot.get_file(photo.photo[-1].file_id)
                else:
                    file = await bot.get_file(photo[-1].file_id)
                
                # Генерируем имя файла
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                random_id = random.randint(1000, 9999)
                filename = f"{cat_info['category']}_{ts}_{random_id}_{idx}.jpg"
                
                # Убеждаемся в уникальности
                filename = generate_unique_filename(target_dir, filename)
                
                # Скачиваем
                file_path = target_dir / filename
                await file.download_to_drive(str(file_path))
                
                result["saved"] += 1
                logger.info(f"📥 Сохранено: {file_path}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения фото {idx}: {e}")
                result["errors"] += 1
        
        return result


# ============================================
# КЛАСС ПОСТЕРА
# ============================================

class TelegramPoster:
    """Публикация в Telegram"""
    
    def __init__(self):
        self.bot_token = CONFIG["telegram"]["bot_token"]
        self.content_path = PATHS["content"]
        self.current_channel_index = 0
        self.channels_list = list(get_enabled_channels().keys())
        self.is_posting = False
        self.state_file = BASE_DIR / "posting_state.json"
        self.last_post_time = None
        self._load_state()
    
    def _load_state(self):
        """Загружает состояние постинга из файла"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self.current_channel_index = state.get("current_channel_index", 0)
                    # При загрузке всегда сбрасываем is_posting (постинг запустится автоматически)
                    self.is_posting = False
                    last_post = state.get("last_post_time")
                    if last_post:
                        self.last_post_time = datetime.fromisoformat(last_post)
            except:
                pass
    
    def _save_state(self):
        """Сохраняет состояние постинга"""
        state = {
            "current_channel_index": self.current_channel_index,
            "is_posting": self.is_posting,
            "last_update": datetime.now().isoformat(),
            "last_post_time": self.last_post_time.isoformat() if self.last_post_time else None
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)
    
    def get_next_channel(self) -> str:
        """Возвращает следующий канал для постинга (циклически)"""
        if not self.channels_list:
            return None
        
        channel_key = self.channels_list[self.current_channel_index]
        self.current_channel_index = (self.current_channel_index + 1) % len(self.channels_list)
        self._save_state()
        return channel_key
    
    def get_random_image(self, channel_key: str) -> Optional[Dict]:
        """Выбирает случайное изображение из контента канала (из месячных папок)"""
        # Ищем в месячных папках (YYYY-MM)
        month_folders = [d for d in self.content_path.iterdir() 
                        if d.is_dir() and re.match(r'\d{4}-\d{2}', d.name)]
        
        if not month_folders:
            logger.warning(f"Нет месячных папок в {self.content_path}")
            return None
        
        all_images = []
        channel_config = CONFIG["channels"][channel_key]
        
        # Перебираем все месячные папки
        for month_folder in month_folders:
            channel_content = month_folder / channel_key
            if not channel_content.exists():
                continue
                
            for cat_path in channel_content.iterdir():
                if cat_path.is_dir():
                    for img_path in cat_path.iterdir():
                        supported_formats = CONFIG.get("supported_formats") or CONFIG.get("settings", {}).get("supported_formats", [".jpg", ".jpeg", ".png", ".gif", ".webp"])
                        if img_path.suffix.lower() in supported_formats:
                            # Находим хештеги для категории
                            hashtags = []
                            for cat_cfg in channel_config.get("categories", {}).values():
                                if cat_cfg.get("folder_name") == cat_path.name:
                                    hashtags = cat_cfg.get("hashtags", [])[:1]  # Первый хештег
                                    break
                            
                            all_images.append({
                                "path": img_path,
                                "category": cat_path.name,
                                "hashtags": hashtags
                            })
        
        if not all_images:
            return None
        
        return random.choice(all_images)
    
    async def post_image(self, channel_id: str, image_path: Path, caption: str = "") -> bool:
        """Отправляет изображение или видео в канал"""
        try:
            from telegram import Bot
            bot = Bot(token=self.bot_token)
            
            suffix = image_path.suffix.lower()
            with open(image_path, "rb") as f:
                if suffix == ".gif":
                    await bot.send_animation(chat_id=channel_id, animation=f, caption=caption)
                elif suffix in [".mp4", ".mov", ".avi", ".mkv"]:
                    await bot.send_video(chat_id=channel_id, video=f, caption=caption)
                else:
                    await bot.send_photo(chat_id=channel_id, photo=f, caption=caption)
            
            logger.info(f"📤 Отправлено в {channel_id}: {image_path.name}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return False
    
    async def post_and_delete(self, channel_key: str) -> bool:
        """Публикует изображение и удаляет его"""
        channel_config = CONFIG["channels"][channel_key]
        channel_id = channel_config["channel_id"]
        
        # Получаем случайное изображение
        img_info = self.get_random_image(channel_key)
        if not img_info:
            logger.warning(f"⚠️ Нет изображений для канала {channel_key}")
            return False
        
        # Формируем подпись
        caption = " ".join(img_info["hashtags"]) if img_info["hashtags"] else ""
        
        # Отправляем
        success = await self.post_image(channel_id, img_info["path"], caption)
        
        if success:
            # Удаляем опубликованное изображение
            try:
                img_info["path"].unlink()
                logger.info(f"🗑️ Удалено: {img_info['path'].name}")
            except Exception as e:
                logger.error(f"❌ Ошибка удаления: {e}")
            
            # Запоминаем время последнего поста
            self.last_post_time = datetime.now()
            self._save_state()
        
        return success
    
    async def run_posting_cycle(self, bot_instance=None, admin_ids=None):
        """Запускает цикл автоматического постинга"""
        self.is_posting = True
        self._save_state()
        
        logger.info("🚀 Запущен цикл автопостинга")
        
        interval_minutes = CONFIG["schedule"].get("post_interval_minutes", 30)
        first_hour = CONFIG["schedule"].get("first_post_hour", 0)
        last_hour = CONFIG["schedule"].get("last_post_hour", 24)
        
        while self.is_posting:
            now = datetime.now()
            
            # Проверяем активное время (если задано)
            if first_hour <= now.hour < last_hour:
                channel_key = self.get_next_channel()
                
                if channel_key:
                    logger.info(f"⏰ Постинг в канал: {channel_key}")
                    success = await self.post_and_delete(channel_key)
                    
                    if not success and bot_instance and admin_ids:
                        for admin_id in admin_ids:
                            try:
                                await bot_instance.send_message(
                                    chat_id=admin_id,
                                    text=f"⚠️ Не удалось опубликовать пост в {channel_key}\nВозможно, закончился контент."
                                )
                            except:
                                pass
            else:
                logger.debug(f"💤 Вне активного времени ({first_hour}:00-{last_hour}:00)")
            
            await asyncio.sleep(interval_minutes * 60)
        
        logger.info("⏹️ Цикл постинга остановлен")
    
    def stop_posting(self):
        """Останавливает цикл постинга"""
        self.is_posting = False
        self._save_state()


# ============================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ПОСТЕРА
# ============================================

poster = TelegramPoster()
posting_task = None

# ============================================
# КОМАНДЫ БОТА
# ============================================

@admin_only
async def cmd_start(update, context):
    """Команда /start"""
    await update.message.reply_text(
        "👋 *TelBot 2.0* — бот автопостинга\n\n"
        "Используйте /help для списка команд.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_help(update, context):
    """Команда /help"""
    help_text = """
📖 *Справка по командам TelBot 2.0*

*Основные команды:*
/status — текущий статус бота
/stats — статистика контента

*Управление постингом:*
/posting\\_start — запустить автопостинг
/posting\\_stop — остановить автопостинг
/post\\_now — опубликовать пост сейчас

*Каналы:*
/channels — список каналов

*Тестирование:*
/test — тест подключения

*Загрузка контента:*
📥 *Через бота:* Отправьте фото с хештегом
   Пример: отправьте фото с подписью #Sakura
   
📦 *Через пакеты:* content\\_manager.py
   Сформируйте пакет и скопируйте в content/
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

@admin_only
async def cmd_status(update, context):
    """Команда /status"""
    global poster
    
    status_lines = ["📊 *Статус бота*\n"]
    
    # Статус постинга
    if poster.is_posting:
        status_lines.append("🟢 Автопостинг: *активен*")
    else:
        status_lines.append("🔴 Автопостинг: *остановлен*")
    
    # Расписание
    schedule = CONFIG.get("schedule", {})
    interval = schedule.get("post_interval_minutes", 30)
    status_lines.append(f"⏱ Интервал: *{interval}* мин")
    
    # Время до следующего поста
    if poster.is_posting and poster.last_post_time:
        next_post_time = poster.last_post_time + timedelta(minutes=interval)
        time_remaining = next_post_time - datetime.now()
        
        if time_remaining.total_seconds() > 0:
            minutes = int(time_remaining.total_seconds() / 60)
            seconds = int(time_remaining.total_seconds() % 60)
            status_lines.append(f"⏳ До следующего поста: *{minutes}м {seconds}с*")
        else:
            status_lines.append(f"⏳ До следующего поста: *скоро...*")
    
    # Активные каналы
    enabled = get_enabled_channels()
    status_lines.append(f"📺 Активных каналов: *{len(enabled)}*")
    
    # Следующий канал
    if poster.channels_list:
        next_channel = poster.channels_list[poster.current_channel_index]
        channel_name = CONFIG["channels"][next_channel].get("name", next_channel)
        status_lines.append(f"➡️ Следующий: *{channel_name}*")
    
    # Контент
    stats = get_content_stats()
    status_lines.append(f"\n📁 Контента: *{stats['total_images']}* шт.")
    
    await update.message.reply_text("\n".join(status_lines), parse_mode="Markdown")

@admin_only
async def cmd_stats(update, context):
    """Команда /stats"""
    await update.message.reply_text(format_stats_message(), parse_mode="Markdown")

@admin_only
async def cmd_channels(update, context):
    """Команда /channels"""
    lines = ["📺 *Список каналов*\n"]
    
    for key, cfg in CONFIG["channels"].items():
        enabled = "🟢" if cfg.get("enabled", True) else "🔴"
        name = cfg.get("name", key)
        cat_count = len(cfg.get("categories", {}))
        lines.append(f"{enabled} *{name}*\n   Категорий: {cat_count}")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@admin_only
async def cmd_posting_start(update, context):
    """Команда /posting_start"""
    global poster, posting_task
    
    if poster.is_posting:
        await update.message.reply_text("⚠️ Постинг уже запущен")
        return
    
    posting_task = asyncio.create_task(
        poster.run_posting_cycle(
            bot_instance=context.bot,
            admin_ids=CONFIG["telegram"]["admin_ids"]
        )
    )
    
    await update.message.reply_text("✅ Автопостинг запущен!")

@admin_only
async def cmd_posting_stop(update, context):
    """Команда /posting_stop"""
    global poster, posting_task
    
    if not poster.is_posting:
        await update.message.reply_text("⚠️ Постинг не запущен")
        return
    
    poster.stop_posting()
    
    if posting_task:
        posting_task.cancel()
        posting_task = None
    
    await update.message.reply_text("⏹ Автопостинг остановлен")

@admin_only
async def cmd_post_now(update, context):
    """Команда /post_now"""
    global poster
    
    # Определяем канал
    args = context.args
    if args:
        channel_key = args[0].lower()
        if channel_key not in CONFIG["channels"]:
            await update.message.reply_text(f"❌ Канал '{channel_key}' не найден")
            return
    else:
        channel_key = poster.get_next_channel()
        if not channel_key:
            await update.message.reply_text("❌ Нет доступных каналов")
            return
    
    await update.message.reply_text(f"📤 Публикация в {channel_key}...")
    
    success = await poster.post_and_delete(channel_key)
    
    if success:
        await update.message.reply_text("✅ Опубликовано!")
    else:
        await update.message.reply_text("❌ Ошибка публикации. Проверьте наличие контента.")

@admin_only
async def cmd_test(update, context):
    """Команда /test"""
    lines = ["🧪 *Тест подключения*\n"]
    
    # Проверяем каналы
    from telegram import Bot
    bot = Bot(token=CONFIG["telegram"]["bot_token"])
    
    for key, cfg in get_enabled_channels().items():
        try:
            chat = await bot.get_chat(cfg["channel_id"])
            lines.append(f"✅ {cfg.get('name', key)}: OK")
        except Exception as e:
            lines.append(f"❌ {cfg.get('name', key)}: {str(e)[:30]}")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ============================================
# ЗАПУСК БОТА
# ============================================

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="TelBot 2.0 - Telegram Auto-Posting Bot")
    parser.add_argument("--status", action="store_true", help="Показать статус")
    args = parser.parse_args()
    
    if args.status:
        stats = get_content_stats()
        print(f"📊 Контент: {stats['total_images']} изображений")
        for ch, st in stats["channels"].items():
            print(f"   {ch}: {st['total']}")
        return
    
    # Запускаем бота
    try:
        from telegram.ext import Application, CommandHandler
    except ImportError:
        logger.error("❌ Не установлена библиотека python-telegram-bot")
        logger.error("   Установите: pip install python-telegram-bot")
        sys.exit(1)
    
    logger.info("🤖 Запуск TelBot 2.0...")
    
    app = Application.builder().token(CONFIG["telegram"]["bot_token"]).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("posting_start", cmd_posting_start))
    app.add_handler(CommandHandler("posting_stop", cmd_posting_stop))
    app.add_handler(CommandHandler("post_now", cmd_post_now))
    app.add_handler(CommandHandler("test", cmd_test))
    
    # Обработчики загрузки контента
    from telegram.ext import MessageHandler, filters
    from telegram import Update
    
    photo_uploader = PhotoUploader()
    
    @admin_only
    async def handle_photo(update: Update, context):
        """Обработка загруженных фото"""
        try:
            photos = [update.message.photo]
            caption = update.message.caption or ""
            
            result = await photo_uploader.process_photos(photos, caption, context.bot)
            
            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
            else:
                channel_name = CONFIG['channels'][result['channel']].get('name', result['channel'])
                await update.message.reply_text(
                    f"✅ Сохранено {result['saved']} фото\n"
                    f"📺 Канал: {channel_name}\n"
                    f"📁 Категория: {result['category']}"
                )
        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("✅ Бот готов к работе")
    logger.info(f"📁 Папка контента: {PATHS['content']}")
    
    # Автозапуск постинга по умолчанию
    async def delayed_start_posting(application):
        """Отложенный запуск постинга"""
        await asyncio.sleep(5)
        
        # Проверяем, не запущен ли уже постинг
        if not poster.is_posting:
            logger.info("🚀 Автоматический запуск постинга...")
            asyncio.create_task(
                poster.run_posting_cycle(
                    bot_instance=application.bot,
                    admin_ids=CONFIG["telegram"]["admin_ids"]
                )
            )
        else:
            logger.info("ℹ️ Постинг уже запущен, пропускаем автозапуск")
    
    async def post_init(application):
        """Инициализация после запуска бота"""
        logger.info("🚀 Инициализация бота...")
        logger.info(f"📊 Состояние постинга: {'активен' if poster.is_posting else 'остановлен'}")
        
        # Всегда пытаемся запустить автопостинг
        asyncio.create_task(delayed_start_posting(application))
        
        # Запускаем задачу для перезапуска в полночь
        asyncio.create_task(midnight_restart_loop(application))
    
    # Задача для автоматического перезапуска в 00:00
    async def midnight_restart_loop(application):
        """Перезапускает бот каждый день в 00:00"""
        while True:
            now = datetime.now()
            # Вычисляем время до следующей полуночи
            next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
            seconds_until_midnight = (next_midnight - now).total_seconds()
            
            logger.info(f"⏰ Следующий перезапуск в {next_midnight.strftime('%Y-%m-%d %H:%M:%S')}")
            
            await asyncio.sleep(seconds_until_midnight)
            
            logger.info("🔄 Полночь! Выполняю перезапуск...")
            
            # Останавливаем постинг
            if poster.is_posting:
                poster.stop_posting()
            
            # Отправляем уведомление админам
            for admin_id in CONFIG["telegram"]["admin_ids"]:
                try:
                    await application.bot.send_message(
                        chat_id=admin_id,
                        text="🔄 Автоматический перезапуск бота (00:00)\nПостинг будет возобновлён через несколько секунд..."
                    )
                except:
                    pass
            
            await asyncio.sleep(5)
            
            # Перезапускаем постинг
            asyncio.create_task(
                poster.run_posting_cycle(
                    bot_instance=application.bot,
                    admin_ids=CONFIG["telegram"]["admin_ids"]
                )
            )
            
            logger.info("✅ Постинг перезапущен")
    
    # Регистрируем callback для запуска после инициализации
    app.post_init = post_init
    
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

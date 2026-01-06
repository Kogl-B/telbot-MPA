#!/usr/bin/env python3
"""
TelBot 2.0 - Telegram Auto-Posting Bot
Один файл со всеми настройками
"""

import os
import sys
import random
import asyncio
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from functools import wraps

# ============================================
# КОНФИГУРАЦИЯ (ХАРДКОД)
# ============================================

BOT_TOKEN = "7601569334:AAGGST1To37UzoIfw1z34X1wytqS71Z1nnA"
ADMIN_IDS = [0]  # Добавь свой ID через @userinfobot

# Каналы
CHANNELS = {
    "mpa_disney": {
        "channel_id": "-1002444770130",
        "name": "Universe Disney Ero Art +18",
        "enabled": True,
        "categories": {
            "princess_jasmin": {"folder_name": "Princess Jasmin", "hashtags": ["#Jasmin"]},
            "elsa": {"folder_name": "Elsa Frozzen", "hashtags": ["#Elsa"]},
            "anna": {"folder_name": "Anna Frozzen", "hashtags": ["#Anna"]},
            "group": {"folder_name": "Group", "hashtags": ["#Group"]},
            "alice": {"folder_name": "Alice", "hashtags": ["#Alice_in_Wonderland"]},
            "elsa_and_anna": {"folder_name": "Elsa and Anna", "hashtags": ["#ElsaAnna"]},
        }
    },
    "harry_potter": {
        "channel_id": "-1002504735486",
        "name": "Universe Harry Potter Erotic Art +18",
        "enabled": True,
        "categories": {
            "hermione": {"folder_name": "Hermione Grander", "hashtags": ["#Hermione_Granger"]},
            "ginny": {"folder_name": "Ginny_Weasley", "hashtags": ["#Ginny_Weasley"]},
            "luna": {"folder_name": "Luna_Lovegood", "hashtags": ["#Luna_Lovegood"]},
            "hermione_and_ginny": {"folder_name": "Hermione and Ginny", "hashtags": ["#hermione_ginny"]},
        }
    },
    "atla": {
        "channel_id": "-1002583181711",
        "name": "Universe The Avatar Legend of AANG Ero Art +18",
        "enabled": True,
        "categories": {
            "katara": {"folder_name": "Katara", "hashtags": ["#Katara"]},
            "azula": {"folder_name": "Azula", "hashtags": ["#Azula"]},
            "tai_le": {"folder_name": "Tai Le", "hashtags": ["#Tai_Le"]},
            "mai": {"folder_name": "Mai", "hashtags": ["#Mai"]},
            "yui": {"folder_name": "Yui", "hashtags": ["#Yui"]},
            "toph": {"folder_name": "Toph", "hashtags": ["#Toph"]},
            "korra": {"folder_name": "Korra", "hashtags": ["#Korra"]},
        }
    },
    "naruto": {
        "channel_id": "-1002156790012",
        "name": "Universe Naruto Ero Art +18",
        "enabled": True,
        "categories": {
            "sakura": {"folder_name": "Sakura", "hashtags": ["#Sakura"]},
            "hinata": {"folder_name": "Hinata", "hashtags": ["#Hinata"]},
            "tsunade": {"folder_name": "Tsunade", "hashtags": ["#Tsunade"]},
            "hanabi": {"folder_name": "Hanabi", "hashtags": ["#Hanabi"]},
            "ino": {"folder_name": "Ino", "hashtags": ["#Ino"]},
            "tenten": {"folder_name": "TenTen", "hashtags": ["#TenTen"]},
            "temari": {"folder_name": "Temari", "hashtags": ["#Temari"]},
            "kushina": {"folder_name": "Kushina", "hashtags": ["#Kushina"]},
        }
    }
}

# Настройки постинга
POST_INTERVAL_MINUTES = 30
FIRST_POST_HOUR = 0
LAST_POST_HOUR = 24
SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm"]

# ============================================
# ПУТИ
# ============================================

BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "content"
LOGS_DIR = BASE_DIR / "logs"
STATE_FILE = BASE_DIR / "posting_state.json"

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

log_file = LOGS_DIR / f"telbot_{datetime.now().strftime('%Y%m%d')}.log"
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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_enabled_channels() -> Dict:
    return {k: v for k, v in CHANNELS.items() if v.get("enabled", True)}

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if ADMIN_IDS and ADMIN_IDS[0] != 0 and user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def get_content_stats() -> Dict:
    stats = {"total_images": 0, "channels": {}}
    if not CONTENT_DIR.exists():
        return stats
    
    month_folders = [d for d in CONTENT_DIR.iterdir() 
                    if d.is_dir() and re.match(r'\d{4}-\d{2}', d.name)]
    
    for channel_key in get_enabled_channels():
        channel_stats = {"total": 0, "categories": {}}
        
        for month_folder in month_folders:
            channel_path = month_folder / channel_key
            if channel_path.exists():
                for cat_dir in channel_path.iterdir():
                    if cat_dir.is_dir():
                        count = sum(1 for f in cat_dir.iterdir() 
                                   if f.suffix.lower() in SUPPORTED_FORMATS)
                        if cat_dir.name not in channel_stats["categories"]:
                            channel_stats["categories"][cat_dir.name] = 0
                        channel_stats["categories"][cat_dir.name] += count
                        channel_stats["total"] += count
        
        stats["channels"][channel_key] = channel_stats
        stats["total_images"] += channel_stats["total"]
    
    return stats

# ============================================
# КЛАСС ПОСТЕРА
# ============================================

class TelegramPoster:
    def __init__(self):
        self.current_channel_index = 0
        self.channels_list = list(get_enabled_channels().keys())
        self.is_posting = False
        self.last_post_time = None
        self._load_state()
    
    def _load_state(self):
        import json
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.current_channel_index = state.get("current_channel_index", 0)
                    self.is_posting = False
                    last_post = state.get("last_post_time")
                    if last_post:
                        self.last_post_time = datetime.fromisoformat(last_post)
            except:
                pass
    
    def _save_state(self):
        import json
        state = {
            "current_channel_index": self.current_channel_index,
            "is_posting": self.is_posting,
            "last_update": datetime.now().isoformat(),
            "last_post_time": self.last_post_time.isoformat() if self.last_post_time else None
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    
    def get_next_channel(self) -> str:
        if not self.channels_list:
            return None
        channel_key = self.channels_list[self.current_channel_index]
        self.current_channel_index = (self.current_channel_index + 1) % len(self.channels_list)
        self._save_state()
        return channel_key
    
    def get_random_image(self, channel_key: str) -> Optional[Dict]:
        month_folders = [d for d in CONTENT_DIR.iterdir() 
                        if d.is_dir() and re.match(r'\d{4}-\d{2}', d.name)]
        
        if not month_folders:
            return None
        
        all_images = []
        channel_config = CHANNELS[channel_key]
        
        for month_folder in month_folders:
            channel_content = month_folder / channel_key
            if not channel_content.exists():
                continue
                
            for cat_path in channel_content.iterdir():
                if cat_path.is_dir():
                    for img_path in cat_path.iterdir():
                        if img_path.suffix.lower() in SUPPORTED_FORMATS:
                            hashtags = []
                            for cat_cfg in channel_config.get("categories", {}).values():
                                if cat_cfg.get("folder_name") == cat_path.name:
                                    hashtags = cat_cfg.get("hashtags", [])[:1]
                                    break
                            
                            all_images.append({
                                "path": img_path,
                                "category": cat_path.name,
                                "hashtags": hashtags
                            })
        
        return random.choice(all_images) if all_images else None
    
    async def post_image(self, channel_id: str, image_path: Path, caption: str = "") -> bool:
        try:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            
            suffix = image_path.suffix.lower()
            with open(image_path, "rb") as f:
                if suffix == ".gif":
                    await bot.send_animation(chat_id=channel_id, animation=f, caption=caption)
                elif suffix in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                    await bot.send_video(chat_id=channel_id, video=f, caption=caption)
                else:
                    await bot.send_photo(chat_id=channel_id, photo=f, caption=caption)
            
            logger.info(f"📤 Отправлено в {channel_id}: {image_path.name}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return False
    
    async def post_and_delete(self, channel_key: str) -> bool:
        channel_config = CHANNELS[channel_key]
        channel_id = channel_config["channel_id"]
        
        img_info = self.get_random_image(channel_key)
        if not img_info:
            logger.warning(f"⚠️ Нет изображений для канала {channel_key}")
            return False
        
        caption = " ".join(img_info["hashtags"]) if img_info["hashtags"] else ""
        success = await self.post_image(channel_id, img_info["path"], caption)
        
        if success:
            try:
                img_info["path"].unlink()
                logger.info(f"🗑️ Удалено: {img_info['path'].name}")
            except Exception as e:
                logger.error(f"❌ Ошибка удаления: {e}")
            
            self.last_post_time = datetime.now()
            self._save_state()
        
        return success
    
    async def run_posting_cycle(self, bot_instance=None):
        self.is_posting = True
        self._save_state()
        
        logger.info("🚀 Запущен цикл автопостинга")
        
        while self.is_posting:
            now = datetime.now()
            
            if FIRST_POST_HOUR <= now.hour < LAST_POST_HOUR:
                channel_key = self.get_next_channel()
                
                if channel_key:
                    logger.info(f"⏰ Постинг в канал: {channel_key}")
                    success = await self.post_and_delete(channel_key)
                    
                    if not success and bot_instance and ADMIN_IDS[0] != 0:
                        for admin_id in ADMIN_IDS:
                            try:
                                await bot_instance.send_message(
                                    chat_id=admin_id,
                                    text=f"⚠️ Не удалось опубликовать в {channel_key}"
                                )
                            except:
                                pass
            else:
                logger.debug(f"💤 Вне активного времени ({FIRST_POST_HOUR}:00-{LAST_POST_HOUR}:00)")
            
            await asyncio.sleep(POST_INTERVAL_MINUTES * 60)
        
        logger.info("⏹️ Цикл постинга остановлен")
    
    def stop_posting(self):
        self.is_posting = False
        self._save_state()

# ============================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================

poster = TelegramPoster()
posting_task = None

# ============================================
# КОМАНДЫ БОТА
# ============================================

@admin_only
async def cmd_start(update, context):
    await update.message.reply_text(
        "👋 *TelBot 2.0* — бот автопостинга\n\n"
        "Используйте /help для списка команд.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_help(update, context):
    help_text = """
📖 *Справка по командам TelBot 2.0*

/status — текущий статус бота
/stats — статистика контента
/posting\\_start — запустить автопостинг
/posting\\_stop — остановить автопостинг
/post\\_now — опубликовать пост сейчас
/channels — список каналов
/test — тест подключения
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

@admin_only
async def cmd_status(update, context):
    lines = ["📊 *Статус бота*\n"]
    
    if poster.is_posting:
        lines.append("🟢 Автопостинг: *активен*")
    else:
        lines.append("🔴 Автопостинг: *остановлен*")
    
    lines.append(f"⏱ Интервал: *{POST_INTERVAL_MINUTES}* мин")
    
    if poster.is_posting and poster.last_post_time:
        next_post_time = poster.last_post_time + timedelta(minutes=POST_INTERVAL_MINUTES)
        time_remaining = next_post_time - datetime.now()
        
        if time_remaining.total_seconds() > 0:
            minutes = int(time_remaining.total_seconds() / 60)
            seconds = int(time_remaining.total_seconds() % 60)
            lines.append(f"⏳ До следующего поста: *{minutes}м {seconds}с*")
    
    enabled = get_enabled_channels()
    lines.append(f"📺 Активных каналов: *{len(enabled)}*")
    
    if poster.channels_list:
        next_channel = poster.channels_list[poster.current_channel_index]
        channel_name = CHANNELS[next_channel].get("name", next_channel)
        lines.append(f"➡️ Следующий: *{channel_name}*")
    
    stats = get_content_stats()
    lines.append(f"\n📁 Контента: *{stats['total_images']}* шт.")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@admin_only
async def cmd_stats(update, context):
    stats = get_content_stats()
    lines = [f"📊 *Статистика контента*\n", f"📁 Всего: *{stats['total_images']}* изображений\n"]
    
    for channel_key, channel_stats in stats["channels"].items():
        channel_name = CHANNELS[channel_key].get("name", channel_key)
        lines.append(f"📺 *{channel_name}*: {channel_stats['total']}")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@admin_only
async def cmd_channels(update, context):
    lines = ["📺 *Список каналов*\n"]
    
    for key, cfg in CHANNELS.items():
        enabled = "🟢" if cfg.get("enabled", True) else "🔴"
        name = cfg.get("name", key)
        lines.append(f"{enabled} *{name}*")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@admin_only
async def cmd_posting_start(update, context):
    global posting_task
    
    if poster.is_posting:
        await update.message.reply_text("⚠️ Постинг уже запущен")
        return
    
    posting_task = asyncio.create_task(poster.run_posting_cycle(context.bot))
    await update.message.reply_text("✅ Автопостинг запущен!")

@admin_only
async def cmd_posting_stop(update, context):
    global posting_task
    
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
    args = context.args
    if args:
        channel_key = args[0].lower()
        if channel_key not in CHANNELS:
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
        await update.message.reply_text("❌ Ошибка. Проверьте наличие контента.")

@admin_only
async def cmd_test(update, context):
    lines = ["🧪 *Тест подключения*\n"]
    
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    
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
    try:
        from telegram.ext import Application, CommandHandler
    except ImportError:
        logger.error("❌ pip install python-telegram-bot")
        sys.exit(1)
    
    logger.info("🤖 Запуск TelBot 2.0...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("posting_start", cmd_posting_start))
    app.add_handler(CommandHandler("posting_stop", cmd_posting_stop))
    app.add_handler(CommandHandler("post_now", cmd_post_now))
    app.add_handler(CommandHandler("test", cmd_test))
    
    async def post_init(application):
        logger.info("🚀 Инициализация бота...")
        await asyncio.sleep(5)
        if not poster.is_posting:
            logger.info("🚀 Автоматический запуск постинга...")
            asyncio.create_task(poster.run_posting_cycle(application.bot))
    
    app.post_init = post_init
    
    logger.info("✅ Бот готов к работе")
    logger.info(f"📁 Папка контента: {CONTENT_DIR}")
    
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

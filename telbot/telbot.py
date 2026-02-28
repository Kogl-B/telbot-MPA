#!/usr/bin/env python3
"""
TelBot 2.0 — Telegram Auto-Posting Bot
=======================================
Автоматический постинг контента в Telegram-каналы по расписанию.

Используется JobQueue из python-telegram-bot для точного таймера без дрейфа.
Токен бота хранится ТОЛЬКО в bot_token.txt (не в git).

Роли:
  - admin  — полный доступ (управление, постинг, загрузка, статистика)
  - user   — просмотр статуса и загрузка фото

Использование:
    python telbot.py              # Запуск бота
    python telbot.py --status     # Статус контента в консоль
"""

import os
import sys
import json
import random
import logging
import argparse
import re
import traceback
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from functools import wraps

# ============================================
# ПУТИ И КОНСТАНТЫ
# ============================================

BASE_DIR = Path(__file__).parent

PATHS = {
    "content": BASE_DIR / "content",
    "logs": BASE_DIR / "logs",
    "config": BASE_DIR / "config",
    "temp": BASE_DIR / "temp",
}

TOKEN_FILE = BASE_DIR / "bot_token.txt"
STATE_FILE = BASE_DIR / "posting_state.json"

SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov"]

# Порог «мало контента» (по умолчанию, переопределяется в config)
DEFAULT_LOW_CONTENT_THRESHOLD = 10

for p in PATHS.values():
    p.mkdir(parents=True, exist_ok=True)

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

log_file = PATHS["logs"] / f"telbot_{datetime.now().strftime('%Y%m%d')}.log"

# Основной формат
_log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Файловый хендлер — DEBUG и выше (ловим всё)
_fh = logging.FileHandler(log_file, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_log_formatter)

# Консольный хендлер — INFO и выше
_sh = logging.StreamHandler()
_sh.setLevel(logging.INFO)
_sh.setFormatter(_log_formatter)

logger = logging.getLogger("telbot")
logger.setLevel(logging.DEBUG)
logger.addHandler(_fh)
logger.addHandler(_sh)

# ============================================
# УПРАВЛЕНИЕ ТОКЕНОМ
# ============================================

def load_token() -> str:
    """
    Загружает токен бота. Порядок:
      1. Файл bot_token.txt
      2. Переменная окружения BOT_TOKEN
      3. Интерактивный ввод (если терминал)
    """
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            logger.info("🔑 Токен загружен из bot_token.txt")
            return token

    token = os.environ.get("BOT_TOKEN", "").strip()
    if token:
        logger.info("🔑 Токен загружен из переменной окружения BOT_TOKEN")
        _save_token(token)
        return token

    if sys.stdin.isatty():
        print("\n" + "=" * 50)
        print("  🔑  НАСТРОЙКА ТОКЕНА БОТА")
        print("=" * 50)
        print("Файл bot_token.txt не найден.")
        print("Введите токен Telegram-бота (от @BotFather):\n")
        token = input("Токен: ").strip()
        if not token:
            print("❌ Токен не может быть пустым!")
            sys.exit(1)
        _save_token(token)
        print(f"\n✅ Токен сохранён в {TOKEN_FILE.name}")
        print("⚠️  Не добавляйте этот файл в git!\n")
        return token

    logger.error("❌ Токен бота не найден!")
    logger.error("   Создайте файл bot_token.txt с токеном")
    logger.error("   или задайте переменную окружения BOT_TOKEN")
    sys.exit(1)


def _save_token(token: str):
    TOKEN_FILE.write_text(token.strip(), encoding="utf-8")

# ============================================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# ============================================

def _deep_update(base: dict, update: dict) -> dict:
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict:
    config_file = PATHS["config"] / "config.json"
    custom_file = BASE_DIR / "config_custom.json"

    if not config_file.exists():
        logger.error(f"❌ Конфигурация не найдена: {config_file}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    if custom_file.exists():
        with open(custom_file, "r", encoding="utf-8") as f:
            _deep_update(config, json.load(f))
        logger.info("✅ Загружена пользовательская конфигурация")

    return config


CONFIG = load_config()


def reload_config():
    """Перезагружает конфигурацию из файлов без перезапуска бота."""
    global CONFIG, ADMIN_IDS, USER_IDS
    CONFIG.clear()
    CONFIG.update(load_config())
    ADMIN_IDS.clear()
    ADMIN_IDS.extend(CONFIG.get("telegram", {}).get("admin_ids", []))
    USER_IDS.clear()
    USER_IDS.extend(CONFIG.get("telegram", {}).get("user_ids", []))
    logger.info("🔄 Конфигурация перезагружена")

# ============================================
# СИСТЕМА РОЛЕЙ
# ============================================
# Конфиг:
#   "telegram": {
#     "admin_ids": [123],       <-- полный доступ
#     "user_ids":  [456, 789],  <-- ограниченный доступ
#   }
#
# admin  — всё
# user   — /start, /help, /status, /stats, /channels, /history + загрузка фото
# чужой  — ⛔

ADMIN_IDS: List[int] = CONFIG.get("telegram", {}).get("admin_ids", [])
USER_IDS: List[int] = CONFIG.get("telegram", {}).get("user_ids", [])


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _is_known_user(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id in USER_IDS


def admin_only(func):
    """Декоратор: только для администраторов"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        uid = update.effective_user.id
        if not _is_admin(uid):
            logger.warning(
                f"⛔ Отказ в доступе (admin_only): "
                f"{update.effective_user.username} id={uid}"
            )
            await update.message.reply_text("⛔ Доступ запрещён. Требуются права администратора.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def user_only(func):
    """Декоратор: для админов и обычных пользователей"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        uid = update.effective_user.id
        if not _is_known_user(uid):
            logger.warning(
                f"⛔ Отказ в доступе (user_only): "
                f"{update.effective_user.username} id={uid}"
            )
            await update.message.reply_text("⛔ Доступ запрещён. Обратитесь к администратору.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_enabled_channels() -> Dict:
    return {k: v for k, v in CONFIG["channels"].items() if v.get("enabled", True)}


def get_supported_formats() -> list:
    return (
        CONFIG.get("supported_formats")
        or CONFIG.get("settings", {}).get("supported_formats", SUPPORTED_FORMATS)
    )


def find_category_by_hashtag(hashtag: str) -> Optional[Dict]:
    h = hashtag.lower()
    for ch_key, ch_cfg in CONFIG["channels"].items():
        for cat_key, cat_cfg in ch_cfg.get("categories", {}).items():
            if any(t.lower() == h for t in cat_cfg.get("hashtags", [])):
                return {
                    "channel_key": ch_key,
                    "category": cat_cfg.get("folder_name", cat_key),
                    "hashtags": cat_cfg.get("hashtags", []),
                }
    return None


def generate_unique_filename(directory: Path, filename: str) -> str:
    if not (directory / filename).exists():
        return filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    c = 1
    while (directory / f"{stem}_{c}{suffix}").exists():
        c += 1
    return f"{stem}_{c}{suffix}"


def escape_md(text: str) -> str:
    for ch in r"_*[`":
        text = text.replace(ch, f"\\{ch}")
    return text

# ============================================
# СТАТИСТИКА КОНТЕНТА
# ============================================

def get_content_stats() -> Dict:
    stats = {"total": 0, "channels": {}}
    content = PATHS["content"]
    if not content.exists():
        return stats

    months = [d for d in content.iterdir()
              if d.is_dir() and re.match(r"\d{4}-\d{2}", d.name)]
    fmt = get_supported_formats()

    for ch_key in get_enabled_channels():
        ch_stats = {"total": 0, "categories": {}}
        for month in months:
            ch_path = month / ch_key
            if not ch_path.exists():
                continue
            for cat_dir in ch_path.iterdir():
                if not cat_dir.is_dir():
                    continue
                count = sum(1 for f in cat_dir.iterdir() if f.suffix.lower() in fmt)
                ch_stats["categories"][cat_dir.name] = (
                    ch_stats["categories"].get(cat_dir.name, 0) + count
                )
                ch_stats["total"] += count
        stats["channels"][ch_key] = ch_stats
        stats["total"] += ch_stats["total"]
    return stats


def get_low_content_channels(threshold: int = None) -> Dict[str, int]:
    """Возвращает каналы, в которых меньше threshold файлов."""
    if threshold is None:
        threshold = CONFIG.get("settings", {}).get(
            "low_content_threshold", DEFAULT_LOW_CONTENT_THRESHOLD
        )
    stats = get_content_stats()
    low = {}
    for ch_key, ch_stats in stats["channels"].items():
        if ch_stats["total"] < threshold:
            low[ch_key] = ch_stats["total"]
    return low


def format_stats_message(channel_filter: str = None) -> str:
    """Формирует сообщение со статистикой.
    Если channel_filter указан — детальная статистика по одному каналу.
    """
    stats = get_content_stats()
    schedule = CONFIG.get("schedule", {})
    interval = schedule.get("post_interval_minutes", 30)
    posts_per_day = (24 * 60) // interval if interval > 0 else 0
    enabled_count = len(get_enabled_channels())

    # --- Детальная статистика по одному каналу ---
    if channel_filter:
        ch_key = channel_filter.lower()
        if ch_key not in CONFIG["channels"]:
            return f"❌ Канал `{escape_md(channel_filter)}` не найден.\n\nДоступные: {', '.join(CONFIG['channels'].keys())}"
        ch_cfg = CONFIG["channels"][ch_key]
        ch_stats = stats["channels"].get(ch_key, {"total": 0, "categories": {}})
        ch_name = escape_md(ch_cfg.get("name", ch_key))

        # Постов в день для этого канала: round-robin делит поровну
        posts_per_day_ch = posts_per_day / enabled_count if enabled_count > 0 else 0

        lines = [f"📊 *Детальная статистика: {ch_name}*\n"]
        lines.append(f"📁 Всего файлов: *{ch_stats['total']}*")
        if ch_stats['total'] > 0 and posts_per_day_ch > 0:
            days_left = ch_stats['total'] / posts_per_day_ch
            lines.append(f"⏱ Хватит на: *{days_left:.1f}* дней")
            lines.append(f"📊 Постов/день: *{posts_per_day_ch:.1f}*\n")

        lines.append("*По категориям:*")
        cat_names = {c.get("folder_name", k): k for k, c in ch_cfg.get("categories", {}).items()}
        for cat, count in sorted(ch_stats.get("categories", {}).items(), key=lambda x: -x[1]):
            cat_days = count / posts_per_day_ch if posts_per_day_ch > 0 else 0
            bar_len = min(count, 20)
            bar = "█" * bar_len
            days_str = f" (~{cat_days:.0f}д)" if cat_days > 0 else ""
            lines.append(f"   • {escape_md(cat)}: *{count}*{days_str}")
            lines.append(f"     {bar}")

        # Категории с 0 файлов
        existing_cats = set(ch_stats.get("categories", {}).keys())
        for cat_cfg in ch_cfg.get("categories", {}).values():
            fname = cat_cfg.get("folder_name", "")
            if fname and fname not in existing_cats:
                lines.append(f"   • {escape_md(fname)}: *0* ⚠️")

        return "\n".join(lines)

    # --- Общая статистика ---
    lines = ["📊 *Статистика контента*\n"]
    lines.append(f"📁 Всего файлов: *{stats['total']}*\n")

    if stats["total"] > 0 and posts_per_day > 0:
        days = stats["total"] / posts_per_day
        lines.append(f"⏱ Хватит на: *{days:.1f}* дней")
        lines.append(f"📊 Постов/день: *{posts_per_day}* (каждые {interval} мин)")
        if enabled_count > 0:
            lines.append(f"📺 На канал: *{posts_per_day / enabled_count:.1f}*/день\n")

    lines.append("*По каналам:*")
    for ch_key, ch_stats in stats["channels"].items():
        name = escape_md(CONFIG["channels"][ch_key].get("name", ch_key))
        lines.append(f"\n📺 *{name}*: {ch_stats['total']} шт.")
        for cat, count in sorted(ch_stats["categories"].items()):
            lines.append(f"   • {escape_md(cat)}: {count}")

    return "\n".join(lines)

# ============================================
# ИСТОРИЯ ПОСТИНГА (парсинг логов)
# ============================================

def parse_posting_history(days: int = 7, by_channel: bool = False) -> Dict:
    """
    Парсит логи за указанное количество дней.
    by_channel=False: {дата_str: количество_постов}
    by_channel=True:  {дата_str: {channel_id: count}}
    """
    history: Dict[str, any] = defaultdict(lambda: defaultdict(int) if by_channel else 0)
    today = datetime.now().date()

    # Паттерн: "📤 Отправлено в <channel_id>: <filename>"
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}) .+📤 Отправлено в (-?\d+): ")

    for i in range(days):
        day = today - timedelta(days=i)
        log_path = PATHS["logs"] / f"telbot_{day.strftime('%Y%m%d')}.log"
        if not log_path.exists():
            continue
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = pattern.match(line)
                    if m:
                        date_str = m.group(1)
                        if by_channel:
                            channel_id = m.group(2)
                            history[date_str][channel_id] += 1
                        else:
                            history[date_str] += 1
        except Exception:
            pass

    return dict(history)


def cleanup_empty_dirs(base_path: Path = None):
    """Удаляет пустые папки категорий и месяцев в content/."""
    content = base_path or PATHS["content"]
    removed = 0
    for month_dir in sorted(content.iterdir()):
        if not month_dir.is_dir() or not re.match(r"\d{4}-\d{2}", month_dir.name):
            continue
        for ch_dir in list(month_dir.iterdir()):
            if not ch_dir.is_dir():
                continue
            for cat_dir in list(ch_dir.iterdir()):
                if cat_dir.is_dir() and not any(cat_dir.iterdir()):
                    cat_dir.rmdir()
                    removed += 1
                    logger.debug(f"🧹 Удалена пустая папка: {cat_dir}")
            # Удаляем пустую папку канала
            if ch_dir.is_dir() and not any(ch_dir.iterdir()):
                ch_dir.rmdir()
                removed += 1
                logger.debug(f"🧹 Удалена пустая папка: {ch_dir}")
        # Удаляем пустую месячную папку (но оставляем если есть package_info.json)
        remaining = list(month_dir.iterdir())
        if not remaining or (len(remaining) == 1 and remaining[0].name == "package_info.json"):
            for f in remaining:
                f.unlink()
            month_dir.rmdir()
            removed += 1
            logger.debug(f"🧹 Удалена пустая месячная папка: {month_dir}")
    if removed > 0:
        logger.info(f"🧹 Очистка: удалено {removed} пустых папок")
    return removed

# ============================================
# ЗАГРУЗКА КОНТЕНТА ЧЕРЕЗ БОТА
# ============================================

class ContentUploader:
    """Приём фото и документов через Telegram (включая медиагруппы)."""

    def __init__(self):
        # Буфер для медиагрупп: media_group_id -> [message, ...]
        self._album_buffer: Dict[str, List] = {}
        self._album_timers: Dict[str, object] = {}

    # ---------- Сохранение одного файла ----------

    async def save_file(self, file_id: str, caption: str, bot,
                        ext_hint: str = ".jpg") -> dict:
        """Скачивает файл по file_id и сохраняет по хештегу из caption."""
        hashtag = None
        if caption:
            for word in caption.split():
                if word.startswith("#"):
                    hashtag = word
                    break
        if not hashtag:
            return {"error": "Нет хештега в подписи. Пример: #Sakura"}

        cat_info = find_category_by_hashtag(hashtag)
        if not cat_info:
            return {"error": f"Хештег {hashtag} не найден в конфигурации."}

        target = PATHS["content"] / cat_info["channel_key"] / cat_info["category"]
        target.mkdir(parents=True, exist_ok=True)

        try:
            tg_file = await bot.get_file(file_id)
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            rid = random.randint(1000, 9999)

            # Определяем расширение из file_path от Telegram
            if tg_file.file_path:
                tg_ext = Path(tg_file.file_path).suffix.lower()
                if tg_ext:
                    ext_hint = tg_ext

            fname = generate_unique_filename(
                target, f"{cat_info['category']}_{ts}_{rid}{ext_hint}"
            )
            await tg_file.download_to_drive(str(target / fname))
            logger.info(f"📥 Сохранено: {target / fname}")
            return {
                "saved": 1,
                "category": cat_info["category"],
                "channel": cat_info["channel_key"],
            }
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения файла: {e}\n{traceback.format_exc()}")
            return {"error": str(e)}

    # ---------- Обработка медиагруппы ----------

    async def handle_album_message(self, update, context):
        """
        Собирает сообщения одной медиагруппы в буфер.
        Через 2 секунды после последнего сообщения — обрабатывает пачку.
        """
        msg = update.message
        group_id = msg.media_group_id

        if group_id not in self._album_buffer:
            self._album_buffer[group_id] = []

        self._album_buffer[group_id].append(msg)

        # Сбрасываем/ставим таймер на обработку
        if group_id in self._album_timers:
            self._album_timers[group_id].schedule_removal()

        self._album_timers[group_id] = context.application.job_queue.run_once(
            callback=self._process_album,
            when=2,  # 2 секунды после последнего сообщения в группе
            data=group_id,
            name=f"album_{group_id}",
        )

    async def _process_album(self, context):
        """Callback: обрабатывает накопленный альбом."""
        group_id = context.job.data
        messages = self._album_buffer.pop(group_id, [])
        self._album_timers.pop(group_id, None)

        if not messages:
            return

        # Берём caption из первого сообщения (Telegram присылает caption только в первом)
        caption = ""
        for m in messages:
            if m.caption:
                caption = m.caption
                break

        saved = 0
        errors = 0
        last_result = {}

        for m in messages:
            file_id, ext = self._extract_file_info(m)
            if not file_id:
                continue
            result = await self.save_file(file_id, caption, context.bot, ext)
            if "error" in result:
                errors += 1
                last_result = result
            else:
                saved += 1
                last_result = result

        # Отправляем один ответ на весь альбом
        first_msg = messages[0]
        if saved > 0:
            ch_name = CONFIG["channels"].get(last_result.get("channel"), {}).get(
                "name", last_result.get("channel", "?")
            )
            await first_msg.reply_text(
                f"✅ Сохранено {saved} файлов"
                + (f" ({errors} ошибок)" if errors else "")
                + f"\n📺 Канал: {ch_name}"
                + f"\n📁 Категория: {last_result.get('category', '?')}"
            )
        else:
            err_text = last_result.get("error", "Неизвестная ошибка")
            await first_msg.reply_text(f"❌ {err_text}")

    # ---------- Извлечение file_id ----------

    @staticmethod
    def _extract_file_info(msg) -> tuple:
        """Возвращает (file_id, ext_hint) из сообщения."""
        if msg.photo:
            return msg.photo[-1].file_id, ".jpg"
        if msg.document:
            doc = msg.document
            mime = (doc.mime_type or "").lower()
            ext = ".jpg"
            if doc.file_name:
                ext = Path(doc.file_name).suffix.lower() or ext
            elif "video" in mime or "mp4" in mime:
                ext = ".mp4"
            elif "gif" in mime:
                ext = ".gif"
            elif "png" in mime:
                ext = ".png"
            elif "webp" in mime:
                ext = ".webp"
            return doc.file_id, ext
        if msg.video:
            return msg.video.file_id, ".mp4"
        if msg.animation:
            return msg.animation.file_id, ".gif"
        return None, None

# ============================================
# TELEGRAM POSTER (JobQueue)
# ============================================

class TelegramPoster:
    """
    Управление автопостингом.
    JobQueue.run_repeating() — точный таймер без дрейфа.
    Уведомляет админов при низком остатке контента.
    """

    def __init__(self):
        self.content_path = PATHS["content"]
        self.channels_list = list(get_enabled_channels().keys())
        self.current_channel_index = 0
        self.is_posting = False
        self.last_post_time: Optional[datetime] = None
        self.posting_job = None
        self._low_content_warned: set = set()  # уже предупреждённые каналы
        self._last_send_error: Optional[str] = None  # последняя ошибка отправки
        self._load_state()

    # --- Состояние ---

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.current_channel_index = state.get("current_channel_index", 0)
                if self.current_channel_index >= len(self.channels_list):
                    self.current_channel_index = 0
                ts = state.get("last_post_time")
                if ts:
                    self.last_post_time = datetime.fromisoformat(ts)
            except Exception:
                logger.debug(f"Не удалось загрузить state: {traceback.format_exc()}")

    def _save_state(self):
        STATE_FILE.write_text(
            json.dumps({
                "current_channel_index": self.current_channel_index,
                "is_posting": self.is_posting,
                "last_update": datetime.now().isoformat(),
                "last_post_time": (
                    self.last_post_time.isoformat() if self.last_post_time else None
                ),
            }),
            encoding="utf-8",
        )

    # --- Ротация каналов ---

    def get_next_channel(self) -> Optional[str]:
        if not self.channels_list:
            return None
        ch = self.channels_list[self.current_channel_index]
        self.current_channel_index = (self.current_channel_index + 1) % len(
            self.channels_list
        )
        self._save_state()
        return ch

    # --- Выбор контента ---

    def get_random_image(self, channel_key: str) -> Optional[Dict]:
        month_dirs = [
            d for d in self.content_path.iterdir()
            if d.is_dir() and re.match(r"\d{4}-\d{2}", d.name)
        ]
        if not month_dirs:
            return None

        ch_cfg = CONFIG["channels"][channel_key]
        fmt = get_supported_formats()
        images = []

        for month in month_dirs:
            ch_path = month / channel_key
            if not ch_path.exists():
                continue
            for cat_dir in ch_path.iterdir():
                if not cat_dir.is_dir():
                    continue
                hashtags = []
                for cat_cfg in ch_cfg.get("categories", {}).values():
                    if cat_cfg.get("folder_name") == cat_dir.name:
                        hashtags = cat_cfg.get("hashtags", [])[:1]
                        break
                for f in cat_dir.iterdir():
                    if f.suffix.lower() in fmt:
                        images.append({
                            "path": f,
                            "category": cat_dir.name,
                            "hashtags": hashtags,
                        })
        return random.choice(images) if images else None

    # --- Публикация ---

    async def send_file(self, bot, channel_id: str, file_path: Path,
                        caption: str = "") -> bool:
        try:
            ext = file_path.suffix.lower()
            with open(file_path, "rb") as f:
                if ext == ".gif":
                    await bot.send_animation(chat_id=channel_id, animation=f, caption=caption)
                elif ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                    await bot.send_video(chat_id=channel_id, video=f, caption=caption)
                else:
                    await bot.send_photo(chat_id=channel_id, photo=f, caption=caption)
            logger.info(f"📤 Отправлено в {channel_id}: {file_path.name}")
            self._last_send_error = None
            return True
        except Exception as e:
            self._last_send_error = str(e)
            logger.error(f"❌ Ошибка отправки {file_path.name}: {e}\n{traceback.format_exc()}")
            return False

    async def post_and_delete(self, bot, channel_key: str) -> Dict:
        """
        Возвращает dict с результатом:
          {"ok": True}  — успех
          {"ok": False, "reason": str, "details": str} — провал
        """
        ch_cfg = CONFIG["channels"][channel_key]
        img = self.get_random_image(channel_key)
        if not img:
            logger.warning(f"⚠️ Нет контента для {channel_key}")
            return {"ok": False, "reason": "no_content",
                    "details": "Нет файлов поддерживаемых форматов в папках контента"}

        caption = " ".join(img["hashtags"]) if img["hashtags"] else ""
        file_path = img["path"]

        # Проверяем что файл реально существует и читаем
        if not file_path.exists():
            logger.error(f"❌ Файл не найден на диске: {file_path}")
            return {"ok": False, "reason": "file_missing",
                    "details": f"Файл исчез: {file_path.name}"}

        ok = await self.send_file(bot, ch_cfg["channel_id"], file_path, caption)

        if ok:
            try:
                file_path.unlink()
                logger.info(f"🗑️ Удалён: {file_path.name}")
            except Exception as e:
                logger.error(f"❌ Ошибка удаления: {e}")
            # Очистка пустых папок после удаления файла
            cleanup_empty_dirs()
            self.last_post_time = datetime.now()
            self._save_state()
            return {"ok": True}

        # send_file вернул False — ошибка API
        api_err = getattr(self, '_last_send_error', None) or 'неизвестная ошибка'
        return {"ok": False, "reason": "send_failed",
                "details": f"Файл: {file_path.name} ({file_path.stat().st_size} байт), "
                           f"категория: {img.get('category', '?')}\n"
                           f"API ошибка: {api_err}"}

    # --- Проверка низкого остатка ---

    async def _check_low_content(self, bot):
        """Проверяет остаток контента и шлёт предупреждение админам."""
        threshold = CONFIG.get("settings", {}).get(
            "low_content_threshold", DEFAULT_LOW_CONTENT_THRESHOLD
        )
        low = get_low_content_channels(threshold)

        for ch_key, count in low.items():
            if ch_key in self._low_content_warned:
                continue  # уже предупреждали
            ch_name = CONFIG["channels"][ch_key].get("name", ch_key)
            text = (
                f"🔴 *Мало контента!*\n"
                f"Канал: *{escape_md(ch_name)}*\n"
                f"Осталось: *{count}* файлов (порог: {threshold})"
            )
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id, text=text, parse_mode="Markdown"
                    )
                except Exception:
                    pass
            self._low_content_warned.add(ch_key)
            logger.warning(f"🔴 Мало контента в {ch_key}: {count} файлов")

        # Сбрасываем предупреждение если контент пополнился
        for ch_key in list(self._low_content_warned):
            if ch_key not in low:
                self._low_content_warned.discard(ch_key)

    # --- Управление расписанием ---

    def start_posting(self, job_queue) -> bool:
        if self.is_posting:
            return False

        schedule = CONFIG.get("schedule", {})
        interval_min = schedule.get("post_interval_minutes", 30)

        first_delay = 10
        if self.last_post_time:
            elapsed = (datetime.now() - self.last_post_time).total_seconds()
            remaining = interval_min * 60 - elapsed
            if remaining > 0:
                first_delay = remaining

        self.posting_job = job_queue.run_repeating(
            callback=self._posting_tick,
            interval=timedelta(minutes=interval_min),
            first=timedelta(seconds=first_delay),
            name="posting_job",
        )
        self.is_posting = True
        self._save_state()
        logger.info(
            f"🚀 Автопостинг запущен (интервал {interval_min} мин, "
            f"первый пост через {int(first_delay)} сек)"
        )
        return True

    def stop_posting(self) -> bool:
        if not self.is_posting:
            return False
        if self.posting_job:
            self.posting_job.schedule_removal()
            self.posting_job = None
        self.is_posting = False
        self._save_state()
        logger.info("⏹️ Автопостинг остановлен")
        return True

    async def _posting_tick(self, context):
        """Callback JobQueue — один тик постинга."""
        schedule = CONFIG.get("schedule", {})
        first_h = schedule.get("first_post_hour", 0)
        last_h = schedule.get("last_post_hour", 24)
        now = datetime.now()

        if not (first_h <= now.hour < last_h):
            logger.debug(f"💤 Вне активного времени ({first_h}:00–{last_h}:00)")
            return

        channel_key = self.get_next_channel()
        if not channel_key:
            logger.warning("⚠️ Нет доступных каналов")
            return

        logger.info(f"⏰ Постинг в {channel_key}")
        result = await self.post_and_delete(context.bot, channel_key)

        if not result["ok"]:
            # Собираем диагностику
            reason = result.get("reason", "unknown")
            details = result.get("details", "")
            ch_name = CONFIG["channels"][channel_key].get("name", channel_key)

            # Считаем файлы в папках этого канала
            file_count = 0
            folder_info = []
            for month_dir in self.content_path.iterdir():
                if month_dir.is_dir() and re.match(r"\d{4}-\d{2}", month_dir.name):
                    ch_path = month_dir / channel_key
                    if ch_path.exists():
                        for cat_dir in ch_path.iterdir():
                            if cat_dir.is_dir():
                                cnt = sum(1 for f in cat_dir.iterdir()
                                          if f.suffix.lower() in get_supported_formats())
                                if cnt > 0:
                                    folder_info.append(f"  {month_dir.name}/{cat_dir.name}: {cnt}")
                                file_count += cnt

            # Классифицируем API-ошибки по тексту
            api_hint = ""
            if reason == "send_failed":
                err_lower = details.lower()
                if "chat not found" in err_lower:
                    api_hint = "🔧 Бот не добавлен в канал или неверный channel_id"
                elif "bot was kicked" in err_lower or "bot is not a member" in err_lower:
                    api_hint = "🔧 Бот исключён из канала — добавьте его обратно как администратора"
                elif "forbidden" in err_lower:
                    api_hint = "🔧 Нет прав на публикацию — проверьте права бота в канале"
                elif "wrong file identifier" in err_lower or "invalid" in err_lower:
                    api_hint = "🔧 Файл повреждён или неподдерживаемый формат"
                elif "too large" in err_lower or "file is too big" in err_lower:
                    api_hint = "🔧 Файл слишком большой для Telegram (лимит: фото 10 МБ, видео 50 МБ)"
                elif "flood" in err_lower or "too many requests" in err_lower:
                    api_hint = "🔧 Превышен лимит запросов — бот временно заблокирован Telegram"

            reason_text = {
                "no_content": "📭 Контент не найден (0 файлов)",
                "file_missing": "🗑️ Файл исчез с диска",
                "send_failed": "📡 Ошибка отправки в Telegram API",
            }.get(reason, f"❓ Неизвестная причина: {reason}")

            lines = [
                f"⚠️ *Не удалось опубликовать*",
                f"",
                f"📺 Канал: *{escape_md(ch_name)}* (`{channel_key}`)",
                f"❌ Причина: {reason_text}",
            ]
            if api_hint:
                lines.append(f"💡 {api_hint}")
            if details:
                lines.append(f"📋 Детали: {escape_md(details)}")
            lines.append(f"")
            lines.append(f"📁 Файлов в папках канала: *{file_count}*")
            if folder_info:
                lines.append("*Содержимое:*")
                lines.extend(folder_info[:15])  # не больше 15 строк
            else:
                lines.append("⚠️ Папки канала пусты или не найдены")

            lines.append(f"")
            lines.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            diag_text = "\n".join(lines)
            logger.warning(f"Диагностика постинга {channel_key}: reason={reason}, "
                           f"details={details}, files_found={file_count}")

            # Отправляем диагностику + лог-файл админам
            today_log = PATHS["logs"] / f"telbot_{datetime.now().strftime('%Y%m%d')}.log"
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=diag_text,
                        parse_mode="Markdown",
                    )
                except Exception:
                    # Fallback без Markdown
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=diag_text.replace("*", "").replace("`", ""),
                        )
                    except Exception:
                        pass
                # Отправляем лог
                if today_log.exists():
                    try:
                        with open(today_log, "rb") as lf:
                            await context.bot.send_document(
                                chat_id=admin_id,
                                document=lf,
                                filename=today_log.name,
                                caption="📋 Лог на момент ошибки постинга",
                            )
                    except Exception:
                        pass

        # После каждого поста проверяем остатки
        await self._check_low_content(context.bot)

# ============================================
# КОМАНДЫ БОТА
# ============================================

# --- Доступно ВСЕМ пользователям (user + admin) ---

@user_only
async def cmd_start(update, context):
    uid = update.effective_user.id
    role = "👑 Администратор" if _is_admin(uid) else "👤 Пользователь"
    await update.message.reply_text(
        f"👋 *TelBot 2.0* — бот автопостинга\n\n"
        f"Ваша роль: {role}\n"
        f"Используйте /help для списка команд.",
        parse_mode="Markdown",
    )


@user_only
async def cmd_help(update, context):
    uid = update.effective_user.id
    base = (
        "📖 *Справка TelBot 2.0*\n\n"
        "*Общие команды:*\n"
        "/status — статус бота\n"
        "/stats — статистика контента\n"
        "/channels — список каналов\n"
        "/history — история постинга\n"
        "📥 Отправьте фото/документ с хештегом для загрузки\n"
        "📦 Поддерживаются альбомы (медиагруппы)\n"
    )
    if _is_admin(uid):
        base += (
            "\n*🔧 Админ-команды:*\n"
            "/posting\\_start — запустить автопостинг\n"
            "/posting\\_stop — остановить автопостинг\n"
            "/post\\_now [канал] — пост сейчас\n"
            "/reload — перезагрузить конфиг\n"
            "/test — тест подключения\n"
        )
    await update.message.reply_text(base, parse_mode="Markdown")


@user_only
async def cmd_status(update, context):
    poster: TelegramPoster = context.bot_data["poster"]
    schedule = CONFIG.get("schedule", {})
    interval = schedule.get("post_interval_minutes", 30)

    lines = ["📊 *Статус бота*\n"]

    if poster.is_posting:
        lines.append("🟢 Автопостинг: *активен*")
    else:
        lines.append("🔴 Автопостинг: *остановлен*")

    lines.append(f"⏱ Интервал: *{interval}* мин")

    if poster.is_posting and poster.posting_job:
        next_run = poster.posting_job.next_t
        if next_run:
            now_aware = datetime.now(timezone.utc)
            remaining = (next_run - now_aware).total_seconds()
            if remaining > 0:
                m, s = divmod(int(remaining), 60)
                lines.append(f"⏳ До след. поста: *{m}м {s}с*")
            else:
                lines.append("⏳ След. пост: *скоро...*")

    enabled = get_enabled_channels()
    lines.append(f"📺 Каналов: *{len(enabled)}*")

    if poster.channels_list:
        nxt_ch = poster.channels_list[poster.current_channel_index]
        lines.append(
            f"➡️ Следующий: *{CONFIG['channels'][nxt_ch].get('name', nxt_ch)}*"
        )

    stats = get_content_stats()
    lines.append(f"\n📁 Контента: *{stats['total']}* шт.")

    # Предупреждение о низком остатке (видно всем)
    low = get_low_content_channels()
    if low:
        lines.append("\n⚠️ *Мало контента:*")
        for ch_key, cnt in low.items():
            ch_name = CONFIG["channels"][ch_key].get("name", ch_key)
            lines.append(f"   🔴 {escape_md(ch_name)}: {cnt} шт.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@user_only
async def cmd_stats(update, context):
    args = context.args
    channel_filter = args[0] if args else None
    await update.message.reply_text(
        format_stats_message(channel_filter), parse_mode="Markdown"
    )


@user_only
async def cmd_channels(update, context):
    lines = ["📺 *Список каналов*\n"]
    for key, cfg in CONFIG["channels"].items():
        icon = "🟢" if cfg.get("enabled", True) else "🔴"
        name = cfg.get("name", key)
        cat_count = len(cfg.get("categories", {}))
        lines.append(f"{icon} *{name}*\n   Категорий: {cat_count}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@user_only
async def cmd_history(update, context):
    """Команда /history [дней] — история постинга."""
    args = context.args
    days = 7
    if args:
        try:
            days = max(1, min(int(args[0]), 30))
        except ValueError:
            pass

    history = parse_posting_history(days)
    if not history:
        await update.message.reply_text(f"📭 За последние {days} дней постов не найдено.")
        return

    total = sum(history.values())
    lines = [f"📊 *История постинга ({days} дней)*\n"]
    lines.append(f"Всего: *{total}* постов\n")

    for day_str in sorted(history.keys(), reverse=True):
        count = history[day_str]
        bar = "█" * min(count, 30)
        lines.append(f"`{day_str}` {bar} *{count}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Только для АДМИНОВ ---

@admin_only
async def cmd_posting_start(update, context):
    poster: TelegramPoster = context.bot_data["poster"]
    if poster.is_posting:
        await update.message.reply_text("⚠️ Постинг уже запущен")
        return
    poster.start_posting(context.application.job_queue)
    await update.message.reply_text("✅ Автопостинг запущен!")


@admin_only
async def cmd_posting_stop(update, context):
    poster: TelegramPoster = context.bot_data["poster"]
    if not poster.is_posting:
        await update.message.reply_text("⚠️ Постинг не запущен")
        return
    poster.stop_posting()
    await update.message.reply_text("⏹ Автопостинг остановлен")


@admin_only
async def cmd_post_now(update, context):
    poster: TelegramPoster = context.bot_data["poster"]
    args = context.args

    if args:
        ch = args[0].lower()
        if ch not in CONFIG["channels"]:
            await update.message.reply_text(f"❌ Канал '{ch}' не найден")
            return
    else:
        ch = poster.get_next_channel()
        if not ch:
            await update.message.reply_text("❌ Нет доступных каналов")
            return

    await update.message.reply_text(f"📤 Публикация в {ch}...")
    result = await poster.post_and_delete(context.bot, ch)
    if result["ok"]:
        await update.message.reply_text("✅ Опубликовано!")
    else:
        reason = result.get('reason', 'unknown')
        details = result.get('details', '')
        await update.message.reply_text(
            f"❌ Ошибка публикации\n"
            f"Причина: {reason}\n"
            f"Детали: {details}"
        )


@admin_only
async def cmd_reload(update, context):
    """Перезагрузка конфига без рестарта бота."""
    try:
        reload_config()
        poster: TelegramPoster = context.bot_data["poster"]
        # Обновляем список каналов в poster
        old_channels = poster.channels_list[:]
        poster.channels_list = list(get_enabled_channels().keys())
        if poster.current_channel_index >= len(poster.channels_list):
            poster.current_channel_index = 0

        added = set(poster.channels_list) - set(old_channels)
        removed = set(old_channels) - set(poster.channels_list)

        lines = ["✅ *Конфигурация перезагружена*\n"]
        lines.append(f"📺 Каналов: *{len(poster.channels_list)}*")
        lines.append(f"👑 Админов: *{len(ADMIN_IDS)}*")
        if added:
            lines.append(f"\n➕ Добавлены: {', '.join(added)}")
        if removed:
            lines.append(f"\n➖ Убраны: {', '.join(removed)}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        logger.info(f"🔄 Конфиг перезагружен по команде от {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка перезагрузки конфига: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка перезагрузки:\n`{str(e)[:300]}`", parse_mode="Markdown")


@admin_only
async def cmd_test(update, context):
    lines = ["🧪 *Тест подключения*\n"]
    for key, cfg in get_enabled_channels().items():
        try:
            await context.bot.get_chat(cfg["channel_id"])
            lines.append(f"✅ {cfg.get('name', key)}: OK")
        except Exception as e:
            lines.append(f"❌ {cfg.get('name', key)}: {str(e)[:40]}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ============================================
# GLOBAL ERROR HANDLER
# ============================================

async def error_handler(update, context):
    """Логирует необработанные ошибки с полным traceback и шлёт лог админам."""
    tb_text = "".join(
        traceback.format_exception(
            type(context.error), context.error, context.error.__traceback__
        )
    )
    logger.error(
        f"❌ Необработанная ошибка: {context.error}\n"
        f"Update: {update}\n{tb_text}"
    )

    # Текстовое уведомление + лог-файл
    error_msg = (
        f"❌ *Ошибка бота*\n\n"
        f"`{str(context.error)[:500]}`\n\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    today_log = PATHS["logs"] / f"telbot_{datetime.now().strftime('%Y%m%d')}.log"

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id, text=error_msg, parse_mode="Markdown"
            )
        except Exception:
            # Если Markdown не парсится (спецсимволы в ошибке), шлём plain
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"❌ Ошибка бота:\n{str(context.error)[:500]}",
                )
            except Exception:
                pass
        # Отправляем лог-файл за сегодня
        if today_log.exists():
            try:
                with open(today_log, "rb") as lf:
                    await context.bot.send_document(
                        chat_id=admin_id,
                        document=lf,
                        filename=today_log.name,
                        caption="📋 Лог-файл на момент ошибки",
                    )
            except Exception:
                pass

# ============================================
# ЗАПУСК
# ============================================

def main():
    parser = argparse.ArgumentParser(description="TelBot 2.0")
    parser.add_argument("--status", action="store_true", help="Статус контента")
    args = parser.parse_args()

    if args.status:
        stats = get_content_stats()
        print(f"📊 Контент: {stats['total']} файлов")
        for ch, st in stats["channels"].items():
            print(f"   {ch}: {st['total']}")
        return

    token = load_token()

    try:
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
    except ImportError:
        logger.error("❌ pip install 'python-telegram-bot[job-queue]'")
        sys.exit(1)

    logger.info("🤖 Запуск TelBot 2.0...")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    logger.info(f"👤 Пользователи: {USER_IDS}")

    app = Application.builder().token(token).build()

    # --- Poster и Uploader ---
    poster = TelegramPoster()
    app.bot_data["poster"] = poster

    uploader = ContentUploader()
    app.bot_data["uploader"] = uploader

    # --- Регистрация команд ---
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("posting_start", cmd_posting_start))
    app.add_handler(CommandHandler("posting_stop", cmd_posting_stop))
    app.add_handler(CommandHandler("post_now", cmd_post_now))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("test", cmd_test))

    # --- Обработка медиа (фото, документы, видео) ---

    @user_only
    async def handle_media(update, context):
        """Приём фото, документов, видео — одиночных и альбомов."""
        msg = update.message
        up: ContentUploader = context.bot_data["uploader"]

        # Медиагруппа (альбом) — собираем в буфер
        if msg.media_group_id:
            await up.handle_album_message(update, context)
            return

        # Одиночное сообщение
        file_id, ext = ContentUploader._extract_file_info(msg)
        if not file_id:
            await msg.reply_text("❌ Не удалось распознать файл.")
            return

        caption = msg.caption or ""
        result = await up.save_file(file_id, caption, context.bot, ext)

        if "error" in result:
            await msg.reply_text(f"❌ {result['error']}")
        else:
            ch_name = CONFIG["channels"].get(result["channel"], {}).get(
                "name", result["channel"]
            )
            await msg.reply_text(
                f"✅ Сохранено {result['saved']} файл\n"
                f"📺 Канал: {ch_name}\n"
                f"📁 Категория: {result['category']}"
            )

    # Принимаем: фото, документы, видео, GIF
    media_filter = filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ANIMATION
    app.add_handler(MessageHandler(media_filter, handle_media))

    # --- Global error handler ---
    app.add_error_handler(error_handler)

    # --- Еженедельный отчёт (понедельник) ---
    async def weekly_report_tick(context):
        """Еженедельный отчёт по понедельникам."""
        now = datetime.now()
        if now.weekday() != 0:  # 0 = понедельник
            return

        logger.info("📅 Формирование еженедельного отчёта")
        stats = get_content_stats()
        history = parse_posting_history(days=7, by_channel=True)
        schedule = CONFIG.get("schedule", {})
        interval = schedule.get("post_interval_minutes", 30)
        posts_per_day = (24 * 60) // interval if interval > 0 else 0
        enabled_count = len(get_enabled_channels())

        # Считаем посты за неделю по каналам
        ch_id_to_key = {}
        for ch_key, ch_cfg in CONFIG["channels"].items():
            ch_id_to_key[ch_cfg.get("channel_id", "")] = ch_key

        weekly_by_channel: Dict[str, int] = defaultdict(int)
        total_posts = 0
        for day_str, ch_counts in history.items():
            for ch_id, cnt in ch_counts.items():
                ch_key = ch_id_to_key.get(ch_id, ch_id)
                weekly_by_channel[ch_key] += cnt
                total_posts += cnt

        lines = [
            "📅 *Еженедельный отчёт*",
            f"🕐 {now.strftime('%Y-%m-%d %H:%M')}\n",
            f"📤 Постов за неделю: *{total_posts}*",
            f"📁 Контента осталось: *{stats['total']}* файлов",
        ]

        if stats["total"] > 0 and posts_per_day > 0:
            days_left = stats["total"] / posts_per_day
            lines.append(f"⏱ Хватит на: *{days_left:.1f}* дней\n")

        lines.append("*По каналам:*")
        for ch_key in get_enabled_channels():
            ch_name = escape_md(CONFIG["channels"][ch_key].get("name", ch_key))
            ch_stats = stats["channels"].get(ch_key, {"total": 0})
            posted = weekly_by_channel.get(ch_key, 0)
            remaining = ch_stats["total"]
            posts_per_day_ch = posts_per_day / enabled_count if enabled_count > 0 else 0
            days_ch = remaining / posts_per_day_ch if posts_per_day_ch > 0 else 0
            lines.append(
                f"\n📺 *{ch_name}*"
                f"\n   📤 Постов: {posted} | 📁 Осталось: *{remaining}*"
                f" (~{days_ch:.0f} дней)"
            )

        low = get_low_content_channels()
        if low:
            lines.append("\n⚠️ *Требуется пополнение:*")
            for ch_key, cnt in low.items():
                ch_name = CONFIG["channels"][ch_key].get("name", ch_key)
                lines.append(f"   🔴 {escape_md(ch_name)}: {cnt} шт.")

        report = "\n".join(lines)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id, text=report, parse_mode="Markdown"
                )
            except Exception:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=report.replace("*", "").replace("`", ""),
                    )
                except Exception:
                    pass
        logger.info(f"📅 Еженедельный отчёт отправлен ({total_posts} постов за неделю)")

    # --- Автозапуск постинга ---
    async def post_init(application):
        logger.info("🚀 Инициализация бота...")
        p: TelegramPoster = application.bot_data["poster"]
        p.start_posting(application.job_queue)

        # Еженедельный отчёт — проверяем каждый день в 10:00
        application.job_queue.run_daily(
            callback=weekly_report_tick,
            time=datetime.strptime("10:00", "%H:%M").time(),
            name="weekly_report",
        )
        logger.info("📅 Еженедельный отчёт: каждый понедельник в 10:00")

        logger.info(f"📁 Папка контента: {PATHS['content']}")
        logger.info("✅ Бот готов к работе")

        # Приветственное сообщение админам
        stats = get_content_stats()
        schedule = CONFIG.get("schedule", {})
        interval = schedule.get("post_interval_minutes", 30)
        enabled = len(get_enabled_channels())
        low = get_low_content_channels()

        lines = [
            "🤖 *TelBot 2.0 запущен!*\n",
            f"📁 Контента: *{stats['total']}* файлов",
            f"📺 Каналов: *{enabled}*",
            f"⏱ Интервал: *{interval}* мин",
            f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if low:
            lines.append("\n⚠️ *Мало контента:*")
            for ch_key, cnt in low.items():
                ch_name = CONFIG["channels"][ch_key].get("name", ch_key)
                lines.append(f"   🔴 {escape_md(ch_name)}: {cnt} шт.")

        greeting = "\n".join(lines)
        for admin_id in ADMIN_IDS:
            try:
                await application.bot.send_message(
                    chat_id=admin_id, text=greeting, parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"❌ Не удалось отправить приветствие админу {admin_id}: {e}")

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

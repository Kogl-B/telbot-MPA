#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CONTENT MANAGER - Локальный менеджер контента для TelBot
Версия: 2.0.0

Функции:
- Сортировка изображений из inbox в storage
- Формирование пакетов для загрузки на сервер
- Статистика и управление хранилищем

Использование:
    python content_manager.py          # Интерактивное меню
    python content_manager.py sort     # Только сортировка
    python content_manager.py form     # Формирование пакета
    python content_manager.py stats    # Статистика
    python content_manager.py upload   # Инструкция по загрузке
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BASE_DIR = Path(__file__).parent

# Настройка логирования
log_dir = BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "content_manager.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Загружает конфигурацию из файлов"""
    config_path = BASE_DIR / "config" / "config.json"
    custom_config_path = BASE_DIR / "config_custom.json"
    
    config = {}
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    if custom_config_path.exists():
        with open(custom_config_path, 'r', encoding='utf-8') as f:
            custom = json.load(f)
            for key, value in custom.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
    
    return config

CONFIG = load_config()

# Пути для SORTER (локальная программа)
PATHS = {
    "inbox": BASE_DIR / "inbox",       # Входящие изображения
    "storage": BASE_DIR / "storage",   # Локальное хранилище
    "upload": BASE_DIR / "upload",     # Готовые пакеты для загрузки
    "logs": BASE_DIR / "logs"
}

# Создаём папки
for path in PATHS.values():
    path.mkdir(parents=True, exist_ok=True)

SUPPORTED_FORMATS = (
    CONFIG.get("supported_formats") or 
    CONFIG.get("settings", {}).get("supported_formats") or 
    [".jpg", ".jpeg", ".png", ".gif", ".webp"]
)


# ============================================
# КЛАСС СОРТИРОВЩИКА
# ============================================

class ImageSorter:
    """Сортировка изображений из inbox в storage"""
    
    def __init__(self):
        self.inbox_path = PATHS["inbox"]
        self.storage_path = PATHS["storage"]
    
    def scan_inbox(self) -> List[Path]:
        """Сканирует inbox на наличие папок"""
        folders = [f for f in self.inbox_path.iterdir() if f.is_dir()]
        return folders
    
    def parse_folder_name(self, folder_name: str) -> Dict[str, Optional[str]]:
        """Определяет канал и категорию по имени папки"""
        result = {"channel": None, "category": folder_name}
        
        # Проверяем префикс канала
        for channel_key in CONFIG.get("channels", {}).keys():
            prefix = f"{channel_key}_"
            if folder_name.lower().startswith(prefix):
                result["channel"] = channel_key
                result["category"] = folder_name[len(prefix):]
                return result
        
        # Ищем по имени категории
        folder_normalized = folder_name.lower().replace(" ", "").replace("_", "")
        for channel_key, channel_config in CONFIG.get("channels", {}).items():
            for cat_key, cat_config in channel_config.get("categories", {}).items():
                category_name = cat_config.get("folder_name", "")
                category_normalized = category_name.lower().replace(" ", "").replace("_", "")
                
                if category_name.lower() == folder_name.lower() or category_normalized == folder_normalized:
                    result["channel"] = channel_key
                    result["category"] = category_name
                    return result
        
        return result
    
    def get_images(self, folder: Path) -> List[Path]:
        """Получает все изображения из папки"""
        images = []
        for root, _, files in os.walk(folder):
            for f in files:
                path = Path(root) / f
                if path.suffix.lower() in SUPPORTED_FORMATS:
                    images.append(path)
        return images
    
    def sort_all(self) -> Dict[str, Any]:
        """Сортирует все папки из inbox"""
        stats = {"moved": 0, "skipped": 0, "errors": 0, "skipped_folders": [], "by_channel": {}}
        
        print("\n" + "=" * 70)
        print("🔄 НАЧАЛО СОРТИРОВКИ")
        print("=" * 70)
        
        folders = self.scan_inbox()
        
        if not folders:
            print("📭 Папок для сортировки не найдено")
            print("\n💡 Совет: поместите изображения в inbox/{имя_категории}/")
            return stats
        
        print(f"\n📂 Найдено папок: {len(folders)}")
        for folder in folders:
            img_count = len([f for f in folder.rglob('*') if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS])
            if img_count > 0:
                print(f"   • {folder.name:<30} ({img_count} файлов)")
            else:
                print(f"   • {folder.name:<30} (пусто)")
        
        print("\n" + "-" * 70)
        print("Начинаем обработку...\n")
        
        for idx, folder in enumerate(folders, 1):
            print(f"📦 [{idx}/{len(folders)}] {folder.name}")
            info = self.parse_folder_name(folder.name)
            
            if not info["channel"]:
                print(f"   ⚠️  Не удалось определить канал")
                print(f"   💡 Используйте названия: Sakura, Hermione Grander, Alice и т.д.")
                stats["skipped"] += 1
                stats["skipped_folders"].append(folder.name)
                print()
                continue
            
            channel_config = CONFIG.get("channels", {}).get(info["channel"], {})
            channel_name = channel_config.get("name", info["channel"])
            
            print(f"   ✅ Канал: {channel_name}")
            print(f"   📁 Категория: {info['category']}")
            
            target_dir = self.storage_path / info["channel"] / info["category"]
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"   📍 Целевая папка: storage/{info['channel']}/{info['category']}")
            
            images = self.get_images(folder)
            
            if len(images) == 0:
                print(f"   📭 Изображений не найдено\n")
                continue
            
            print(f"   🖼️  Найдено изображений: {len(images)}")
            
            moved_count = 0
            renamed_count = 0
            for img in images:
                try:
                    new_name = img.name
                    target = target_dir / new_name
                    
                    if target.exists():
                        stem = img.stem
                        suffix = img.suffix
                        ts = datetime.now().strftime("%Y%m%d%H%M%S")
                        new_name = f"{stem}_{ts}{suffix}"
                        target = target_dir / new_name
                        renamed_count += 1
                    
                    shutil.move(str(img), str(target))
                    stats["moved"] += 1
                    moved_count += 1
                except Exception as e:
                    print(f"      ❌ Ошибка: {img.name}: {e}")
                    stats["errors"] += 1
            
            print(f"   ✨ Перемещено: {moved_count}")
            if renamed_count > 0:
                print(f"   🔄 Переименовано (дубликаты): {renamed_count}")
            
            if info["channel"] not in stats["by_channel"]:
                stats["by_channel"][info["channel"]] = 0
            stats["by_channel"][info["channel"]] += moved_count
            
            self._cleanup_folder(folder)
            print()
        
        print("=" * 70)
        print("✅ СОРТИРОВКА ЗАВЕРШЕНА")
        print("=" * 70)
        
        print(f"\n📊 ИТОГО:")
        print(f"   ✅ Перемещено: {stats['moved']}")
        print(f"   ⏭️  Пропущено папок: {stats['skipped']}")
        print(f"   ❌ Ошибок: {stats['errors']}")
        
        if stats["by_channel"]:
            print(f"\n📺 ПО КАНАЛАМ:")
            for ch_key, count in stats["by_channel"].items():
                ch_config = CONFIG.get("channels", {}).get(ch_key, {})
                ch_name = ch_config.get("name", ch_key)
                print(f"   • {ch_name}: +{count} изображений")
        
        print("\n" + "=" * 70)
        
        if stats['skipped_folders']:
            print(f"\n⚠️  Пропущенные папки:")
            for name in stats['skipped_folders']:
                print(f"   • {name}")
            self._show_expected_folders()
        
        return stats
    
    def _cleanup_folder(self, folder: Path):
        """Очищает папку от пустых подпапок"""
        is_character = self._is_character_folder(folder.name)
        
        for subdir in sorted(folder.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if subdir.is_dir() and subdir != folder:
                try:
                    subdir.rmdir()
                except OSError:
                    pass
        
        if not is_character and not any(folder.iterdir()):
            try:
                folder.rmdir()
                print(f"   🗑️ Папка удалена (пуста)")
            except:
                pass
    
    def _is_character_folder(self, folder_name: str) -> bool:
        """Проверяет, является ли папка папкой персонажа"""
        folder_normalized = folder_name.lower().replace(" ", "").replace("_", "")
        for ch_config in CONFIG.get("channels", {}).values():
            for cat_cfg in ch_config.get("categories", {}).values():
                char_name = cat_cfg.get("folder_name", "")
                char_normalized = char_name.lower().replace(" ", "").replace("_", "")
                if char_normalized == folder_normalized:
                    return True
        return False
    
    def _show_expected_folders(self):
        """Показывает ожидаемые названия папок"""
        print(f"\n💡 Ожидаемые названия папок:")
        for channel_key, channel_config in CONFIG.get("channels", {}).items():
            channel_name = channel_config.get("name", channel_key)
            categories = channel_config.get("categories", {})
            if categories:
                print(f"\n{channel_name}:")
                for cat_cfg in list(categories.values())[:5]:
                    folder_name = cat_cfg.get("folder_name", "")
                    if folder_name:
                        print(f"   • {folder_name}")
                if len(categories) > 5:
                    print(f"   • ... и ещё {len(categories) - 5}")


# ============================================
# КЛАСС ФОРМИРОВАНИЯ ПАКЕТОВ
# ============================================

class PackageBuilder:
    """Формирует пакеты для загрузки на сервер"""
    
    def __init__(self):
        self.storage_path = PATHS["storage"]
        self.upload_path = PATHS["upload"]
        
        schedule_config = CONFIG.get("schedule", {})
        # Поддерживаем оба формата: часы и минуты
        if "post_interval_hours" in schedule_config:
            self.interval_minutes = schedule_config["post_interval_hours"] * 60
        else:
            self.interval_minutes = schedule_config.get("post_interval_minutes", 120)
        self.first_post_hour = schedule_config.get("first_post_hour", 8)
        self.last_post_hour = schedule_config.get("last_post_hour", 22)
    
    def get_available_images(self, channel_key: str) -> Dict[str, List[Path]]:
        """Получает доступные изображения для канала"""
        result = {}
        channel_path = self.storage_path / channel_key
        
        if not channel_path.exists():
            return result
        
        for cat_path in channel_path.iterdir():
            if cat_path.is_dir():
                images = [f for f in cat_path.iterdir() 
                         if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS]
                if images:
                    result[cat_path.name] = images
        
        return result
    
    def calculate_posts_for_month(self, year: int, month: int) -> int:
        """Рассчитывает количество постов на месяц для ОДНОГО канала"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        days_in_month = (next_month - datetime(year, month, 1)).days
        posting_minutes_per_day = (self.last_post_hour - self.first_post_hour) * 60
        total_posts_per_day = posting_minutes_per_day // self.interval_minutes
        num_channels = len(CONFIG.get("channels", {}))
        posts_per_channel_per_day = total_posts_per_day // max(num_channels, 1)
        
        return posts_per_channel_per_day * days_in_month
    
    def build_package(self, year: int, month: int) -> Dict[str, Any]:
        """Формирует пакет на указанный месяц"""
        month_str = f"{year}-{month:02d}"
        package_path = self.upload_path / month_str
        
        print("\n" + "=" * 70)
        print(f"📦 ФОРМИРОВАНИЕ ПАКЕТА НА {month_str}")
        print("=" * 70)
        
        if package_path.exists():
            print(f"\n🗑️  Удаляем старый пакет {month_str}...")
            shutil.rmtree(package_path)
        package_path.mkdir(parents=True, exist_ok=True)
        
        stats = {"channels": {}, "total_images": 0, "warnings": []}
        channels = CONFIG.get("channels", {})
        
        print(f"\n📋 Параметры постинга:")
        print(f"   • Интервал: {self.interval_minutes} минут")
        print(f"   • Время работы: {self.first_post_hour:02d}:00 - {self.last_post_hour:02d}:00")
        print(f"   • Каналов активно: {len(channels)}")
        
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        days_in_month = (next_month - datetime(year, month, 1)).days
        
        posting_minutes_per_day = (self.last_post_hour - self.first_post_hour) * 60
        total_posts_per_day = posting_minutes_per_day // self.interval_minutes
        posts_per_channel_per_day = total_posts_per_day // max(len(channels), 1)
        
        print(f"\n📊 Расчёт на месяц:")
        print(f"   • Дней в месяце: {days_in_month}")
        print(f"   • Постов в день на ВСЕ каналы: {total_posts_per_day}")
        print(f"   • Постов на ОДИН канал в день: {posts_per_channel_per_day}")
        
        print(f"\n" + "-" * 70)
        
        for channel_key, channel_config in channels.items():
            channel_name = channel_config.get("name", channel_key)
            print(f"\n📺 {channel_name}")
            print(f"   ID: {channel_key}")
            
            needed = self.calculate_posts_for_month(year, month)
            print(f"   📊 Нужно изображений: {needed}")
            
            available = self.get_available_images(channel_key)
            
            if not available:
                warning = f"❌ {channel_name}: нет изображений в storage"
                stats["warnings"].append(warning)
                print(f"   {warning}")
                continue
            
            print(f"   📂 Доступно по категориям:")
            total_available = 0
            for cat_name, imgs in sorted(available.items()):
                count = len(imgs)
                total_available += count
                print(f"      • {cat_name}: {count}")
            
            print(f"   📦 ВСЕГО доступно: {total_available}")
            
            if total_available < needed:
                shortage = needed - total_available
                warning = f"⚠️  {channel_name}: не хватает {shortage} изображений"
                stats["warnings"].append(warning)
                print(f"   {warning}")
                print(f"   💡 Будет скопировано: {total_available} (на сколько хватит)")
            else:
                print(f"   ✅ Достаточно для полного пакета")
            
            # Папка канала в пакете (структура для бота: content/channel_key/category/)
            channel_package_path = package_path / channel_key
            channel_package_path.mkdir(parents=True, exist_ok=True)
            
            selected_images = []
            categories = channel_config.get("categories", {})
            
            images_per_category = needed // max(len(categories), 1)
            print(f"\n   🔄 Распределение (~{images_per_category} на категорию):")
            
            for cat_key, cat_config in categories.items():
                folder_name = cat_config.get("folder_name", "")
                if folder_name in available:
                    cat_images = available[folder_name]
                    random.shuffle(cat_images)
                    take = min(images_per_category, len(cat_images))
                    selected_images.extend(cat_images[:take])
                    if take > 0:
                        print(f"      • {folder_name}: выбрано {take}")
            
            if len(selected_images) < needed:
                all_available = []
                for imgs in available.values():
                    all_available.extend(imgs)
                
                remaining = [img for img in all_available if img not in selected_images]
                random.shuffle(remaining)
                need_more = min(needed - len(selected_images), len(remaining))
                selected_images.extend(remaining[:need_more])
                if need_more > 0:
                    print(f"      • Дополнительно (случайные): {need_more}")
            
            print(f"\n   📋 Копирование файлов...")
            copied = 0
            copied_by_cat = {}
            
            for idx, img in enumerate(selected_images[:needed]):
                try:
                    category = img.parent.name
                    cat_path = channel_package_path / category
                    cat_path.mkdir(parents=True, exist_ok=True)
                    
                    target = cat_path / img.name
                    if target.exists():
                        stem = img.stem
                        suffix = img.suffix
                        target = cat_path / f"{stem}_{idx}{suffix}"
                    
                    shutil.copy2(str(img), str(target))
                    copied += 1
                    
                    if category not in copied_by_cat:
                        copied_by_cat[category] = 0
                    copied_by_cat[category] += 1
                    
                except Exception as e:
                    print(f"      ❌ Ошибка копирования {img.name}: {e}")
            
            print(f"   ✅ Скопировано всего: {copied}")
            if copied_by_cat:
                print(f"   📊 По категориям:")
                for cat, cnt in sorted(copied_by_cat.items()):
                    print(f"      • {cat}: {cnt}")
            
            stats["channels"][channel_key] = {"needed": needed, "copied": copied}
            stats["total_images"] += copied
        
        # Сохраняем информацию о пакете
        package_info = {
            "month": month_str,
            "created": datetime.now().isoformat(),
            "stats": stats,
            "posting_params": {
                "interval_minutes": self.interval_minutes,
                "hours": f"{self.first_post_hour:02d}:00-{self.last_post_hour:02d}:00",
                "channels": len(channels)
            }
        }
        
        info_path = package_path / "package_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(package_info, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 70)
        print(f"✅ ПАКЕТ СФОРМИРОВАН")
        print("=" * 70)
        
        print(f"\n📦 Расположение: {package_path}")
        print(f"📊 Всего изображений: {stats['total_images']}")
        
        total_size = sum(f.stat().st_size for f in package_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"💾 Размер пакета: {size_mb:.1f} MB")
        
        print(f"\n📊 По каналам:")
        for ch_key, ch_stats in stats["channels"].items():
            ch_config = CONFIG.get("channels", {}).get(ch_key, {})
            ch_name = ch_config.get("name", ch_key)
            needed = ch_stats["needed"]
            copied = ch_stats["copied"]
            percent = (copied / needed * 100) if needed > 0 else 0
            print(f"   • {ch_name}: {copied}/{needed} ({percent:.0f}%)")
        
        if stats["warnings"]:
            print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for w in stats["warnings"]:
                print(f"   {w}")
        
        print(f"\n💡 Следующий шаг:")
        print(f"   Используйте пункт 5 меню для инструкции по загрузке на сервер")
        
        print("\n" + "=" * 70)
        
        return stats


# ============================================
# СТАТИСТИКА
# ============================================

class StorageStats:
    """Статистика хранилища"""
    
    def __init__(self):
        self.storage_path = PATHS["storage"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Собирает статистику по хранилищу"""
        stats = {"channels": {}, "total_images": 0, "inbox_images": 0, "inbox_folders": 0}
        
        # Считаем inbox
        inbox_path = PATHS["inbox"]
        if inbox_path.exists():
            for folder in inbox_path.iterdir():
                if folder.is_dir():
                    stats["inbox_folders"] += 1
                    for f in folder.rglob('*'):
                        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
                            stats["inbox_images"] += 1
        
        for channel_key in CONFIG.get("channels", {}).keys():
            channel_path = self.storage_path / channel_key
            if channel_path.exists():
                channel_stats = {}
                channel_total = 0
                
                for cat_path in sorted(channel_path.iterdir()):
                    if cat_path.is_dir():
                        count = len([f for f in cat_path.iterdir() 
                                    if f.suffix.lower() in SUPPORTED_FORMATS])
                        channel_stats[cat_path.name] = count
                        channel_total += count
                
                stats["channels"][channel_key] = {
                    "categories": channel_stats,
                    "total": channel_total
                }
                stats["total_images"] += channel_total
        
        return stats
    
    def show_stats(self):
        """Выводит статистику"""
        stats = self.get_stats()
        
        print("\n" + "=" * 70)
        print("📊 СТАТИСТИКА ХРАНИЛИЩА (storage)")
        print("=" * 70)
        
        for channel_key, channel_data in stats["channels"].items():
            channel_config = CONFIG.get("channels", {}).get(channel_key, {})
            channel_name = channel_config.get("name", channel_key)
            
            print(f"\n📺 {channel_name}: {channel_data['total']} изображений")
            
            for cat_name, count in sorted(channel_data["categories"].items()):
                bar = "█" * min(count // 10, 30)
                print(f"   {cat_name:20} {count:5} {bar}")
        
        print(f"\n{'=' * 70}")
        print(f"📦 ВСЕГО В ХРАНИЛИЩЕ: {stats['total_images']} изображений")
        print("=" * 70)
        
        builder = PackageBuilder()
        now = datetime.now()
        needed_per_month = {}
        
        for channel_key in CONFIG.get("channels", {}).keys():
            needed = builder.calculate_posts_for_month(now.year, now.month)
            needed_per_month[channel_key] = needed
        
        print(f"\n📅 ПРОГНОЗ:")
        for channel_key, channel_data in stats["channels"].items():
            channel_config = CONFIG.get("channels", {}).get(channel_key, {})
            channel_name = channel_config.get("name", channel_key)
            needed = needed_per_month.get(channel_key, 0)
            available = channel_data['total']
            months = available / needed if needed > 0 else 0
            
            print(f"   {channel_name}: хватит на ~{months:.1f} месяцев ({needed} в месяц)")


# ============================================
# ИНТЕРАКТИВНОЕ МЕНЮ
# ============================================

def show_menu():
    """Показывает главное меню"""
    print("\n" + "=" * 70)
    print("📦 CONTENT MANAGER для TelBot (v2.0)")
    print("=" * 70)
    print()
    print("  1. 🔄 Сортировка (inbox → storage)")
    print("  2. 📦 Сформировать пакет на месяц")
    print("  3. 📊 Статистика хранилища")
    print("  4. 📂 Создать папки персонажей в inbox")
    print("  5. 📤 Инструкция по загрузке на сервер")
    print("  6. 🗑️ Удалить исходники после загрузки")
    print("  7. 🧹 Очистить папку upload")
    print()
    print("  0. ❌ Выход")
    print()
    
    return input("Выберите действие: ").strip()


def create_character_folders():
    """Создаёт папки персонажей в inbox"""
    inbox_path = PATHS["inbox"]
    created = 0
    
    print("\n📁 Создание папок персонажей в inbox...")
    
    for channel_key, channel_config in CONFIG.get("channels", {}).items():
        for cat_config in channel_config.get("categories", {}).values():
            folder_name = cat_config.get("folder_name", "")
            if folder_name:
                folder_path = inbox_path / folder_name
                if not folder_path.exists():
                    folder_path.mkdir(parents=True, exist_ok=True)
                    print(f"   ✅ {folder_name}")
                    created += 1
    
    if created == 0:
        print("   Все папки уже существуют")
    else:
        print(f"\n✅ Создано папок: {created}")


def clear_upload():
    """Очищает папку upload"""
    upload_path = PATHS["upload"]
    
    if not any(upload_path.iterdir()):
        print("📭 Папка upload уже пуста")
        return
    
    confirm = input("⚠️ Удалить все файлы из upload? (да/нет): ").strip().lower()
    if confirm in ["да", "yes", "y", "д"]:
        shutil.rmtree(upload_path)
        upload_path.mkdir(parents=True, exist_ok=True)
        print("✅ Папка upload очищена")
    else:
        print("❌ Отменено")


def show_upload_instructions():
    """Показывает инструкцию по загрузке на сервер"""
    upload_path = PATHS["upload"]
    
    packages = [d for d in upload_path.iterdir() if d.is_dir()]
    
    print("\n" + "=" * 70)
    print("📤 ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ НА СЕРВЕР")
    print("=" * 70)
    
    if not packages:
        print("\n⚠️ Папка upload пуста!")
        print("   Сначала сформируйте пакет (пункт 2 меню)")
        return
    
    print(f"\n📦 Готовые пакеты для загрузки:")
    total_size = 0
    for pkg in packages:
        size = sum(f.stat().st_size for f in pkg.rglob('*') if f.is_file())
        size_mb = size / (1024 * 1024)
        total_size += size_mb
        
        files = len([f for f in pkg.rglob('*') if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS])
        print(f"   📁 {pkg.name}: {files} файлов ({size_mb:.1f} MB)")
    
    print(f"\n   Всего: {total_size:.1f} MB")
    
    print("\n" + "-" * 70)
    print("📋 КОМАНДЫ ДЛЯ ЗАГРУЗКИ:")
    print("-" * 70)
    
    print("\n1️⃣ Загрузка через SCP (с Windows):")
    print(f'   scp -r "sorter\\upload\\*" user@server:~/telbot/content/')
    
    print("\n2️⃣ Загрузка через rsync (Linux/Mac):")
    print(f'   rsync -avz --progress sorter/upload/ user@server:~/telbot/content/')
    
    print("\n3️⃣ Или используйте FileZilla/WinSCP:")
    print(f"   - Подключитесь к серверу")
    print(f"   - Перейдите в ~/telbot/content/")
    print(f"   - Скопируйте содержимое папки sorter/upload/")
    
    print("\n" + "-" * 70)
    print("⚠️ СТРУКТУРА НА СЕРВЕРЕ:")
    print("-" * 70)
    print("   telbot/")
    print("   └── content/")
    print("       ├── naruto/")
    print("       │   ├── Sakura/")
    print("       │   └── Hinata/")
    print("       └── harry_potter/")
    print("           └── Hermione Grander/")
    
    print("\n" + "=" * 70)


def delete_after_upload():
    """Удаляет исходники из storage после успешной загрузки"""
    upload_path = PATHS["upload"]
    storage_path = PATHS["storage"]
    
    packages = [d for d in upload_path.iterdir() if d.is_dir()]
    if not packages:
        print("📭 Нечего удалять - upload пуст")
        return
    
    print("\n⚠️ Эта функция удалит из ЛОКАЛЬНОГО storage те файлы,")
    print("   которые были скопированы в папку upload.")
    print("   Используйте ТОЛЬКО после успешной загрузки на сервер!")
    
    confirm = input("\n❓ Удалить исходники? (да/нет): ").strip().lower()
    if confirm not in ["да", "yes", "y", "д"]:
        print("❌ Отменено")
        return
    
    deleted = 0
    errors = 0
    
    for package in packages:
        for channel_dir in package.iterdir():
            if not channel_dir.is_dir():
                continue
                
            for cat_dir in channel_dir.iterdir():
                if not cat_dir.is_dir():
                    continue
                    
                source_cat = storage_path / channel_dir.name / cat_dir.name
                
                for img in cat_dir.iterdir():
                    if img.is_file() and img.suffix.lower() in SUPPORTED_FORMATS:
                        source_file = source_cat / img.name
                        if source_file.exists():
                            try:
                                source_file.unlink()
                                deleted += 1
                            except Exception as e:
                                print(f"   ❌ Ошибка удаления {source_file}: {e}")
                                errors += 1
    
    print(f"\n✅ Удалено файлов из storage: {deleted}")
    if errors:
        print(f"❌ Ошибок: {errors}")
    
    clear_confirm = input("\n❓ Очистить папку upload? (да/нет): ").strip().lower()
    if clear_confirm in ["да", "yes", "y", "д"]:
        for pkg in packages:
            shutil.rmtree(pkg)
        print("✅ Папка upload очищена")


def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "sort":
            sorter = ImageSorter()
            sorter.sort_all()
            return
        
        elif cmd == "form":
            now = datetime.now()
            year = int(sys.argv[2]) if len(sys.argv) > 2 else now.year
            month = int(sys.argv[3]) if len(sys.argv) > 3 else now.month
            
            builder = PackageBuilder()
            builder.build_package(year, month)
            return
        
        elif cmd == "stats":
            stats = StorageStats()
            stats.show_stats()
            return
        
        elif cmd == "upload":
            show_upload_instructions()
            return
        
        else:
            print(f"❌ Неизвестная команда: {cmd}")
            print("Доступные команды: sort, form, stats, upload")
            return
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            sorter = ImageSorter()
            sorter.sort_all()
        
        elif choice == "2":
            now = datetime.now()
            print(f"\n📅 Текущий месяц: {now.year}-{now.month:02d}")
            
            year_input = input(f"Год [{now.year}]: ").strip()
            year = int(year_input) if year_input else now.year
            
            month_input = input(f"Месяц [{now.month}]: ").strip()
            month = int(month_input) if month_input else now.month
            
            builder = PackageBuilder()
            builder.build_package(year, month)
        
        elif choice == "3":
            stats = StorageStats()
            stats.show_stats()
        
        elif choice == "4":
            create_character_folders()
        
        elif choice == "5":
            show_upload_instructions()
        
        elif choice == "6":
            delete_after_upload()
        
        elif choice == "7":
            clear_upload()
        
        elif choice == "0":
            print("\n👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор")
        
        input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI для Content Manager
Современный графический интерфейс на CustomTkinter
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sys
import io
import threading
import shutil
from pathlib import Path
from datetime import datetime

# Импортируем классы из content_manager
sys.path.insert(0, str(Path(__file__).parent))
from content_manager import (
    ImageSorter, PackageBuilder, StorageStats, CONFIG, PATHS,
    SUPPORTED_FORMATS, create_character_folders
)

# ============================================
# ЦВЕТОВАЯ СХЕМА
# ============================================
COLORS = {
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "success": "#2ed573",
    "warning": "#ffa502",
    "error": "#ff4757",
    "info": "#70a1ff",
    "text_dim": "#a4b0be",
    "progress_fill": "#e94560",
    "btn_primary": "#e94560",
    "btn_primary_hover": "#ff6b81",
    "btn_secondary": "#0f3460",
    "btn_secondary_hover": "#1a4a8a",
    "btn_danger": "#ff4757",
    "btn_danger_hover": "#ff6b81",
}


class StdoutRedirector(io.StringIO):
    """Перехватывает stdout и перенаправляет в GUI лог"""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def write(self, text):
        if text and text.strip():
            self.callback(text)
        return len(text) if text else 0

    def flush(self):
        pass


# ============================================
# ГЛАВНОЕ ОКНО
# ============================================

class ContentManagerGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Content Manager")
        self.root.geometry("1050x860")
        self.root.minsize(900, 700)
        
        self._build_ui()
        self.update_stats()
        self.check_packages_status()
    
    def run(self):
        self.root.mainloop()
    
    # =============================================
    # ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # =============================================
    
    def _build_ui(self):
        self.main = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=16, pady=12)
        
        self._build_header()
        self._build_stats_row()
        self._build_actions()
        self._build_progress()
        self._build_log()
        self._build_footer()
    
    def _build_header(self):
        """Заголовок приложения"""
        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")
        
        ctk.CTkLabel(
            left, text="📦  Content Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left")
        
        ctk.CTkLabel(
            left, text="   v2.0",
            font=ctk.CTkFont(size=13),
            text_color="#747d8c"
        ).pack(side="left", padx=(4, 0))
        
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")
        
        self.theme_switch = ctk.CTkSwitch(
            right, text="☀️  Светлая тема",
            font=ctk.CTkFont(size=12),
            command=self._toggle_theme,
            onvalue=1, offvalue=0, width=40
        )
        self.theme_switch.pack(side="right")
    
    def _build_stats_row(self):
        """Статистика и пакеты — две карточки"""
        row = ctk.CTkFrame(self.main, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        
        # Карточка: статистика
        stats_card = ctk.CTkFrame(row, corner_radius=12)
        stats_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        ctk.CTkLabel(
            stats_card, text="📊  Статистика хранилища",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 6))
        
        self.stats_text = ctk.CTkTextbox(
            stats_card, height=200,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8, activate_scrollbars=True
        )
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Карточка: пакеты
        pkg_card = ctk.CTkFrame(row, corner_radius=12)
        pkg_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        ctk.CTkLabel(
            pkg_card, text="📦  Статус пакетов",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 6))
        
        self.packages_text = ctk.CTkTextbox(
            pkg_card, height=200,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8, activate_scrollbars=True
        )
        self.packages_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _build_actions(self):
        """Панель кнопок"""
        card = ctk.CTkFrame(self.main, corner_radius=12)
        card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            card, text="⚡  Действия",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 8))
        
        # Строка 1: главные
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(0, 6))
        
        self.sort_btn = ctk.CTkButton(
            row1, text="🔄  Сортировка inbox → storage",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38, corner_radius=8,
            fg_color=COLORS["btn_primary"], hover_color=COLORS["btn_primary_hover"],
            command=self.run_sort
        )
        self.sort_btn.pack(side="left", padx=(0, 8))
        
        self.auto_package_btn = ctk.CTkButton(
            row1, text="📦  Авто-формирование пакетов",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38, corner_radius=8,
            fg_color=COLORS["btn_primary"], hover_color=COLORS["btn_primary_hover"],
            command=self.run_auto_package
        )
        self.auto_package_btn.pack(side="left", padx=(0, 8))
        
        self.stats_btn = ctk.CTkButton(
            row1, text="📊  Обновить всё",
            font=ctk.CTkFont(size=13), height=38, corner_radius=8,
            fg_color=COLORS["btn_secondary"], hover_color=COLORS["btn_secondary_hover"],
            command=self.refresh_all
        )
        self.stats_btn.pack(side="left")
        
        # Строка 2: вспомогательные
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 10))
        
        self.create_folders_btn = ctk.CTkButton(
            row2, text="📂  Создать папки персонажей",
            font=ctk.CTkFont(size=12), height=34, corner_radius=8,
            fg_color=COLORS["btn_secondary"], hover_color=COLORS["btn_secondary_hover"],
            command=self.run_create_folders
        )
        self.create_folders_btn.pack(side="left", padx=(0, 6))
        
        self.upload_info_btn = ctk.CTkButton(
            row2, text="📤  Инструкция загрузки",
            font=ctk.CTkFont(size=12), height=34, corner_radius=8,
            fg_color=COLORS["btn_secondary"], hover_color=COLORS["btn_secondary_hover"],
            command=self.show_upload_instructions
        )
        self.upload_info_btn.pack(side="left", padx=(0, 6))
        
        self.delete_sources_btn = ctk.CTkButton(
            row2, text="🗑️  Удалить исходники",
            font=ctk.CTkFont(size=12), height=34, corner_radius=8,
            fg_color=COLORS["btn_danger"], hover_color=COLORS["btn_danger_hover"],
            command=self.run_delete_sources
        )
        self.delete_sources_btn.pack(side="left", padx=(0, 6))
        
        self.clear_upload_btn = ctk.CTkButton(
            row2, text="🧹  Очистить upload",
            font=ctk.CTkFont(size=12), height=34, corner_radius=8,
            fg_color=COLORS["btn_danger"], hover_color=COLORS["btn_danger_hover"],
            command=self.run_clear_upload
        )
        self.clear_upload_btn.pack(side="left")
    
    def _build_progress(self):
        prog = ctk.CTkFrame(self.main, fg_color="transparent")
        prog.pack(fill="x", pady=(0, 6))
        
        self.progress_label = ctk.CTkLabel(
            prog, text="", font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"]
        )
        self.progress_label.pack(side="left", padx=(0, 10))
        
        self.progress = ctk.CTkProgressBar(
            prog, height=10, corner_radius=5,
            progress_color=COLORS["progress_fill"]
        )
        self.progress.pack(fill="x", expand=True)
        self.progress.set(0)
    
    def _build_log(self):
        card = ctk.CTkFrame(self.main, corner_radius=12)
        card.pack(fill="both", expand=True, pady=(0, 10))
        
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        
        ctk.CTkLabel(
            hdr, text="📝  Журнал операций",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(side="left")
        
        ctk.CTkButton(
            hdr, text="📋 Копировать", width=110, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["btn_secondary"], hover_color=COLORS["btn_secondary_hover"],
            command=self.copy_log
        ).pack(side="right", padx=(6, 0))
        
        ctk.CTkButton(
            hdr, text="🗑️ Очистить", width=100, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["btn_secondary"], hover_color=COLORS["btn_secondary_hover"],
            command=self.clear_log
        ).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(
            card, font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8, activate_scrollbars=True, wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _build_footer(self):
        footer = ctk.CTkFrame(self.main, fg_color="transparent")
        footer.pack(fill="x")
        
        self.status_label = ctk.CTkLabel(
            footer, text="✅  Готов к работе",
            font=ctk.CTkFont(size=12), text_color=COLORS["success"]
        )
        self.status_label.pack(side="left")
        
        ctk.CTkButton(
            footer, text="❌  Выход", width=100, height=32, corner_radius=8,
            font=ctk.CTkFont(size=12),
            fg_color="#4a4a5a", hover_color="#5a5a6a",
            command=self.root.quit
        ).pack(side="right")
    
    # =============================================
    # ТЕМА
    # =============================================
    
    def _toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="🌙  Тёмная тема")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="☀️  Светлая тема")
    
    # =============================================
    # ЛОГИРОВАНИЕ
    # =============================================
    
    def log(self, message, tag=None):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()
    
    def log_redirect(self, text):
        self.root.after(0, lambda: self._append_log(text))
    
    def _append_log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()
        
    def clear_log(self):
        self.log_text.delete("1.0", "end")
        self.log("Лог очищен")
    
    def copy_log(self):
        try:
            content = self.log_text.get("1.0", "end")
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.set_status("📋  Лог скопирован", COLORS["info"])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать:\n{e}")
    
    # =============================================
    # СТАТУС И ПРОГРЕСС
    # =============================================
    
    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or COLORS["info"])
    
    def set_progress(self, value, maximum=100, text=""):
        self.root.after(0, lambda: self._update_progress(value, maximum, text))
    
    def _update_progress(self, value, maximum, text):
        frac = value / maximum if maximum > 0 else 0
        self.progress.set(frac)
        if text:
            self.progress_label.configure(text=text)
        self.root.update_idletasks()
    
    # =============================================
    # СТАТИСТИКА
    # =============================================

    def refresh_all(self):
        self.update_stats()
        self.check_packages_status()
        self.set_status("✅  Данные обновлены", COLORS["success"])
        
    def update_stats(self):
        self.stats_text.delete("1.0", "end")
        try:
            stats_obj = StorageStats()
            stats = stats_obj.get_stats()
            
            self.stats_text.insert("end", f"📁  Всего в storage: {stats['total_images']} изображений\n")
            self.stats_text.insert("end", f"📥  В inbox: {stats['inbox_images']} изобр. ({stats['inbox_folders']} папок)\n\n")
            
            for ch_key, ch_stats in stats['channels'].items():
                cfg = CONFIG.get('channels', {}).get(ch_key, {})
                name = cfg.get('name', ch_key)
                parts = name.split()
                short = parts[1] if len(parts) > 1 else name
                
                self.stats_text.insert("end", f"📺  {short}: {ch_stats['total']} изобр.\n")
                for cat, count in sorted(ch_stats.get('categories', {}).items()):
                    bar = "█" * min(count // 5, 20) if count > 0 else "░"
                    self.stats_text.insert("end", f"    {cat:<20} {count:>5}  {bar}\n")
                self.stats_text.insert("end", "\n")
        except Exception as e:
            self.stats_text.insert("end", f"❌ Ошибка: {e}\n")
    
    def get_schedule_params(self):
        s = CONFIG.get("schedule", {})
        if "post_interval_hours" in s:
            interval = s["post_interval_hours"] * 60
        else:
            interval = s.get("post_interval_minutes", 120)
        return interval, s.get("first_post_hour", 8), s.get("last_post_hour", 22)
    
    def get_posts_needed_per_month(self):
        interval, fh, lh = self.get_schedule_params()
        total = ((lh - fh) * 60) // interval
        per_ch = total // max(len(CONFIG.get("channels", {})), 1)
        return per_ch * 31
    
    def check_package_completeness(self, year, month):
        pkg_path = PATHS["upload"] / f"{year}-{month:02d}"
        needed = self.get_posts_needed_per_month()
        result = {"exists": pkg_path.exists(), "complete": True, "channels": {},
                  "total_images": 0, "needed_total": 0}
        if not pkg_path.exists():
            result["complete"] = False
            return result
        for ch_key in CONFIG.get("channels", {}).keys():
            cp = pkg_path / ch_key
            count = 0
            if cp.exists():
                for d in cp.iterdir():
                    if d.is_dir():
                        count += sum(1 for f in d.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS)
            result["channels"][ch_key] = {"count": count, "needed": needed, "complete": count >= needed}
            result["total_images"] += count
            result["needed_total"] += needed
            if count < needed:
                result["complete"] = False
        return result
    
    def check_storage_for_package(self):
        needed = self.get_posts_needed_per_month()
        result = {"can_create": True, "channels": {}, "total_available": 0, "total_needed": 0}
        for ch_key in CONFIG.get("channels", {}).keys():
            cp = PATHS["storage"] / ch_key
            count = 0
            if cp.exists():
                for d in cp.iterdir():
                    if d.is_dir():
                        count += sum(1 for f in d.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS)
            result["channels"][ch_key] = {"available": count, "needed": needed, "enough": count >= needed}
            result["total_available"] += count
            result["total_needed"] += needed
            if count < needed:
                result["can_create"] = False
        return result
    
    def check_packages_status(self):
        self.packages_text.delete("1.0", "end")
        try:
            now = datetime.now()
            cy, cm = now.year, now.month
            ny, nm = (cy + 1, 1) if cm == 12 else (cy, cm + 1)
            
            interval, fh, lh = self.get_schedule_params()
            needed = self.get_posts_needed_per_month()
            
            self.packages_text.insert("end", f"⏱️  Интервал: {interval} мин, {fh:02d}:00–{lh:02d}:00\n")
            self.packages_text.insert("end", f"📅  ~{needed} изобр./канал/месяц\n\n")

            for y, m in [(cy, cm), (ny, nm)]:
                st = self.check_package_completeness(y, m)
                tag = f"{y}-{m:02d}"
                if st["exists"] and st["complete"]:
                    self.packages_text.insert("end", f"✅  {tag}: ГОТОВ ({st['total_images']} изобр.)\n")
                elif st["exists"]:
                    diff = st["needed_total"] - st["total_images"]
                    self.packages_text.insert("end", f"⚠️  {tag}: НЕПОЛНЫЙ (−{diff})\n")
                else:
                    self.packages_text.insert("end", f"❌  {tag}: НЕ СОЗДАН\n")
            
            ss = self.check_storage_for_package()
            self.packages_text.insert("end", f"\n📦  Storage: {ss['total_available']} изобр.\n")
            if ss["can_create"]:
                self.packages_text.insert("end", "✅  Материала достаточно\n")
            else:
                bad = [c for c, i in ss["channels"].items() if not i["enough"]]
                self.packages_text.insert("end", f"⚠️  Не хватает: {', '.join(bad)}\n")
        except Exception as e:
            self.packages_text.insert("end", f"❌ Ошибка: {e}\n")
    
    # =============================================
    # ОПЕРАЦИИ
    # =============================================
    
    def _all_btns(self):
        return [self.sort_btn, self.auto_package_btn, self.stats_btn,
                self.create_folders_btn, self.upload_info_btn,
                self.delete_sources_btn, self.clear_upload_btn]
    
    def disable_buttons(self):
        for b in self._all_btns():
            b.configure(state="disabled")
    
    def enable_buttons(self):
        for b in self._all_btns():
            b.configure(state="normal")
        self.progress.set(0)
        self.progress_label.configure(text="")
    
    def run_in_thread(self, fn, name="Операция"):
        def wrapper():
            redir = StdoutRedirector(self.log_redirect)
            old = sys.stdout
            sys.stdout = redir
            try:
                fn()
            except Exception as e:
                sys.stdout = old
                self.root.after(0, lambda: self.log(f"\n❌ ОШИБКА: {e}"))
                import traceback
                self.root.after(0, lambda: self.log(traceback.format_exc()))
                self.root.after(0, lambda: self.set_status(f"❌ {name}: ошибка", COLORS["error"]))
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"{name}:\n{e}"))
            finally:
                sys.stdout = old
                self.root.after(0, self.enable_buttons)
        self.disable_buttons()
        threading.Thread(target=wrapper, daemon=True).start()
    
    # ----- Сортировка -----
    def run_sort(self):
        def task():
            self.root.after(0, lambda: self.set_status("⏳  Сортировка...", COLORS["warning"]))
            sorter = ImageSorter()
            folders = sorter.scan_inbox()
            n = len(folders)
            if n == 0:
                self.root.after(0, lambda: self.log("📭 Inbox пуст"))
                self.root.after(0, lambda: self.set_status("✅  Inbox пуст", COLORS["success"]))
                return
            self.set_progress(0, n, f"0/{n}")
            result = sorter.sort_all()
            self.set_progress(n, n, f"{n}/{n}")
            self.root.after(0, self.refresh_all)
            self.root.after(0, lambda: self.set_status(
                f"✅  Перемещено {result['moved']} изобр.", COLORS["success"]))
            self.root.after(0, lambda: messagebox.showinfo(
                "Сортировка",
                f"Перемещено: {result['moved']}\nПропущено: {result['skipped']}\nОшибок: {result['errors']}"))
        self.run_in_thread(task, "Сортировка")
    
    # ----- Формирование пакетов -----
    def run_auto_package(self):
        def task():
            self.root.after(0, lambda: self.set_status("⏳  Анализ...", COLORS["warning"]))
            now = datetime.now()
            cy, cm = now.year, now.month
            ny, nm = (cy + 1, 1) if cm == 12 else (cy, cm + 1)
            
            created, skipped = [], []
            storage_st = self.check_storage_for_package()
            
            print(f"\n📊 Storage: {storage_st['total_available']} изобр., нужно: {storage_st['total_needed']}")
            if not storage_st["can_create"]:
                print("⚠️  Недостаточно для полного пакета!")
                for c, i in storage_st["channels"].items():
                    if not i["enough"]:
                        cn = CONFIG['channels'][c].get('name', c)
                        print(f"   • {cn}: −{i['needed'] - i['available']}")
            
            builder = PackageBuilder()
            self.set_progress(0, 2, "0/2")
            
            for idx, (y, m) in enumerate([(cy, cm), (ny, nm)]):
                tag = f"{y}-{m:02d}"
                print(f"\n{'─' * 50}")
                print(f"📅 Пакет {tag}")
                st = self.check_package_completeness(y, m)
                
                if st["exists"] and st["complete"]:
                    print(f"   ✅ Уже готов")
                    skipped.append(tag)
                else:
                    ss = self.check_storage_for_package()
                    if ss["can_create"] or st["exists"]:
                        self.root.after(0, lambda t=tag: self.set_status(f"⏳  Создание {t}...", COLORS["warning"]))
                        builder.build_package(y, m)
                        created.append(tag)
                    else:
                        print(f"   ❌ Недостаточно материала")
                        skipped.append(tag)
                self.set_progress(idx + 1, 2, f"{idx + 1}/2")
            
            print(f"\n{'=' * 50}")
            if created: print(f"✅ Создано: {', '.join(created)}")
            if skipped: print(f"⏭️  Пропущено: {', '.join(skipped)}")
            
            self.root.after(0, self.refresh_all)
            self.root.after(0, lambda: self.set_status("✅  Готово", COLORS["success"]))
            if created:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Готово", f"Создано: {len(created)} ({', '.join(created)})\nПропущено: {len(skipped)}"))
            else:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Внимание", "Новых пакетов не создано."))
        self.run_in_thread(task, "Формирование пакетов")
    
    # ----- Создание папок -----
    def run_create_folders(self):
        def task():
            self.root.after(0, lambda: self.set_status("⏳  Создание папок...", COLORS["warning"]))
            create_character_folders()
            self.root.after(0, self.refresh_all)
            self.root.after(0, lambda: self.set_status("✅  Папки созданы", COLORS["success"]))
        self.run_in_thread(task, "Создание папок")
    
    # ----- Инструкция загрузки -----
    def show_upload_instructions(self):
        pkgs = [d for d in PATHS["upload"].iterdir() if d.is_dir()] if PATHS["upload"].exists() else []
        
        self.log("\n" + "═" * 55)
        self.log("📤  ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ НА СЕРВЕР")
        self.log("═" * 55)
        
        if not pkgs:
            self.log("\n⚠️  Upload пуст! Сначала сформируйте пакет.")
            return
        
        total_mb = 0
        for p in pkgs:
            sz = sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
            mb = sz / (1024 * 1024)
            total_mb += mb
            n = len([f for f in p.rglob('*') if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS])
            self.log(f"   📁 {p.name}: {n} файлов ({mb:.1f} MB)")
        self.log(f"   Итого: {total_mb:.1f} MB\n")
        self.log('   SCP:   scp -r "upload/*" user@server:~/telbot/content/')
        self.log('   rsync: rsync -avz upload/ user@server:~/telbot/content/')
        self.log("═" * 55)
    
    # ----- Удалить исходники -----
    def run_delete_sources(self):
        pkgs = [d for d in PATHS["upload"].iterdir() if d.is_dir()] if PATHS["upload"].exists() else []
        if not pkgs:
            messagebox.showwarning("Внимание", "Upload пуст.")
            return
        if not messagebox.askyesno("Подтверждение",
                "⚠️ Удалить из storage файлы, скопированные в upload?\n\nТолько после загрузки на сервер!"):
            return
        
        def task():
            self.root.after(0, lambda: self.set_status("⏳  Удаление...", COLORS["warning"]))
            deleted = errors = 0
            for pkg in pkgs:
                for ch in pkg.iterdir():
                    if not ch.is_dir(): continue
                    for cat in ch.iterdir():
                        if not cat.is_dir(): continue
                        src_cat = PATHS["storage"] / ch.name / cat.name
                        for img in cat.iterdir():
                            if img.is_file() and img.suffix.lower() in SUPPORTED_FORMATS:
                                src = src_cat / img.name
                                if src.exists():
                                    try:
                                        src.unlink()
                                        deleted += 1
                                    except Exception as e:
                                        print(f"❌ {src}: {e}")
                                        errors += 1
            print(f"\n✅ Удалено: {deleted}, ошибок: {errors}")
            self.root.after(0, self.refresh_all)
            self.root.after(0, lambda: self.set_status(f"✅  Удалено {deleted}", COLORS["success"]))
            self.root.after(0, lambda: messagebox.showinfo("Готово", f"Удалено: {deleted}\nОшибок: {errors}"))
        self.run_in_thread(task, "Удаление")
    
    # ----- Очистить upload -----
    def run_clear_upload(self):
        if not PATHS["upload"].exists() or not any(PATHS["upload"].iterdir()):
            messagebox.showinfo("Информация", "Upload уже пуст.")
            return
        if not messagebox.askyesno("Подтверждение", "⚠️ Удалить ВСЕ файлы из upload?"):
            return
        try:
            shutil.rmtree(PATHS["upload"])
            PATHS["upload"].mkdir(parents=True, exist_ok=True)
            self.log("✅ Upload очищен")
            self.set_status("✅  Upload очищен", COLORS["success"])
            self.refresh_all()
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))


def main():
    app = ContentManagerGUI()
    app.run()

if __name__ == "__main__":
    main()

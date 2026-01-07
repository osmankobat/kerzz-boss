"""
KERZZ BOSS Yönetim Programı - Modern CustomTkinter GUI
============================================================
Geliştirici: Osman Kobat
Lisans: MIT License (c) 2024-2026
Sürüm: 3.0.0
============================================================
Özellikler:
- Loading indicator, tooltips, keyboard shortcuts
- Lisans doğrulama ve güncelleme kontrolü
- Excel tarzı filtreleme
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, List, Dict, Any, Callable
import threading
import webbrowser

# Uygulama sabitleri
APP_NAME = "KERZZ BOSS"
APP_VERSION = "3.0.0"
DEVELOPER = "Osman Kobat"
GITHUB_URL = "https://github.com/osmankobat/kerzz-boss"

# CustomTkinter tema ayarları
ctk.set_appearance_mode("dark")  # "dark", "light", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

# Backend import
try:
    from kerzz_yonetim_programi import KerzzYonetim
except ImportError:
    KerzzYonetim = None

# Lisans ve Güncelleme modülü
try:
    from license_manager import LicenseManager, UpdateManager, BackgroundService
    LICENSE_MODULE_AVAILABLE = True
except ImportError:
    LICENSE_MODULE_AVAILABLE = False
    LicenseManager = None
    UpdateManager = None
    BackgroundService = None


# ============== TOOLTIP SINIFI ==============
class ToolTip:
    """Modern tooltip sınıfı"""
    
    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        
        widget.bind("<Enter>", self._schedule_show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<Button-1>", self._hide)
    
    def _schedule_show(self, event=None):
        self._hide()
        self.after_id = self.widget.after(self.delay, self._show)
    
    def _show(self, event=None):
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        # Tooltip label
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            background="#2c3e50",
            foreground="white",
            relief="flat",
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=8,
            pady=4
        )
        label.pack()
    
    def _hide(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


# ============== LOADING OVERLAY ==============
class LoadingOverlay(ctk.CTkFrame):
    """Şeffaf loading overlay"""
    
    def __init__(self, parent, message: str = "Yükleniyor..."):
        super().__init__(parent, fg_color=("gray90", "gray20"))
        
        self.message = message
        self.dots = 0
        self.animating = False
        
        # Center frame
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        
        # Spinner (basit animasyon)
        self.spinner_label = ctk.CTkLabel(
            center,
            text="⏳",
            font=ctk.CTkFont(size=48)
        )
        self.spinner_label.pack(pady=(0, 10))
        
        self.message_label = ctk.CTkLabel(
            center,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.message_label.pack()
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(center, width=200, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start()
    
    def show(self, message: str = None):
        """Overlay'i göster"""
        if message:
            self.message_label.configure(text=message)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self.animating = True
        self._animate()
    
    def hide(self):
        """Overlay'i gizle"""
        self.animating = False
        self.progress.stop()
        self.place_forget()
    
    def _animate(self):
        """Spinner animasyonu"""
        if not self.animating:
            return
        spinners = ["⏳", "⌛"]
        self.dots = (self.dots + 1) % len(spinners)
        self.spinner_label.configure(text=spinners[self.dots])
        self.after(500, self._animate)
    
    def update_message(self, message: str):
        """Mesajı güncelle"""
        self.message_label.configure(text=message)


# ============== PROGRESS DIALOG ==============
class ProgressDialog(ctk.CTkToplevel):
    """İlerleme dialog'u - toplu işlemler için"""
    
    def __init__(self, parent, title: str, total: int):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 75
        self.geometry(f"+{x}+{y}")
        
        self.total = total
        self.current = 0
        self.cancelled = False
        
        # UI
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=f"İşleniyor... (0/{total})",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(main_frame, width=350)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        self.detail_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.detail_label.pack(pady=5)
        
        self.cancel_btn = ctk.CTkButton(
            main_frame,
            text="İptal",
            width=80,
            fg_color="#e74c3c",
            command=self._cancel
        )
        self.cancel_btn.pack(pady=(10, 0))
        
        self.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def update_progress(self, current: int, detail: str = ""):
        """İlerlemeyi güncelle"""
        self.current = current
        progress = current / self.total if self.total > 0 else 0
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"İşleniyor... ({current}/{self.total})")
        if detail:
            self.detail_label.configure(text=detail)
        self.update()
    
    def _cancel(self):
        """İptal et"""
        self.cancelled = True
        self.destroy()
    
    def is_cancelled(self) -> bool:
        return self.cancelled
    
    def complete(self, message: str = "Tamamlandı!"):
        """Tamamlandı"""
        self.status_label.configure(text=message)
        self.progress_bar.set(1)
        self.cancel_btn.configure(text="Tamam", fg_color="#27ae60")
        self.cancelled = False  # Reset


# ============== FİLTRE POPUP SINIFI ==============
class FilterPopup(ctk.CTkToplevel):
    """Sütun filtresi için modern popup - Excel tarzı"""

    def __init__(self, parent, column_name, values, current_filter, callback):
        super().__init__(parent)

        self.callback = callback
        self.column_name = column_name

        # Window ayarları
        self.title(f"Filtre: {column_name}")
        self.geometry("300x400")
        self.resizable(False, True)

        # Modal
        self.transient(parent)
        self.grab_set()

        # Pozisyon - Mouse'a yakın
        x = parent.winfo_pointerx() + 10
        y = parent.winfo_pointery() + 10
        self.geometry(f"+{x}+{y}")

        # Arama kutusu
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)

        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(search_frame, text="🔍 Ara:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.focus()

        # Değer listesi
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(list_frame)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Tümünü seç/kaldır
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            btn_frame,
            text="✓ Tümü",
            width=80,
            command=self._select_all
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="✗ Temizle",
            width=80,
            command=self._clear_all
        ).pack(side="left", padx=2)

        # Uygula/İptal
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            action_frame,
            text="✓ Uygula",
            fg_color="green",
            hover_color="darkgreen",
            command=self._apply
        ).pack(side="left", expand=True, fill="x", padx=2)

        ctk.CTkButton(
            action_frame,
            text="✗ İptal",
            fg_color="red",
            hover_color="darkred",
            command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=2)

        # Değerleri yükle
        self.all_values = sorted(set(str(v) for v in values if v is not None and str(v).strip()))
        self.checkboxes = {}
        self._load_values(current_filter)

    def _load_values(self, current_filter=None):
        """Checkbox'ları oluştur"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.checkboxes.clear()

        # (Tümü) seçeneği
        var = tk.BooleanVar(value=(current_filter is None))
        cb = ctk.CTkCheckBox(
            self.scrollable_frame,
            text="(Tümü)",
            variable=var,
            command=lambda: self._on_all_toggle(var)
        )
        cb.pack(anchor="w", padx=5, pady=2)
        self.checkboxes["__ALL__"] = var

        # Değerler
        search_text = self.search_var.get().lower()
        for value in self.all_values:
            if search_text and search_text not in value.lower():
                continue

            is_checked = (current_filter is None) or (value in current_filter)
            var = tk.BooleanVar(value=is_checked)
            cb = ctk.CTkCheckBox(
                self.scrollable_frame,
                text=value,
                variable=var
            )
            cb.pack(anchor="w", padx=5, pady=2)
            self.checkboxes[value] = var

    def _on_all_toggle(self, all_var):
        """Tümü seçildiğinde"""
        if all_var.get():
            for val, var in self.checkboxes.items():
                if val != "__ALL__":
                    var.set(True)

    def _on_search(self, *args):
        """Arama değiştiğinde"""
        current = self._get_selected_values()
        self._load_values(current if current else None)

    def _select_all(self):
        """Tümünü seç"""
        for var in self.checkboxes.values():
            var.set(True)

    def _clear_all(self):
        """Tümünü kaldır"""
        for val, var in self.checkboxes.items():
            if val != "__ALL__":
                var.set(False)
        self.checkboxes["__ALL__"].set(False)

    def _get_selected_values(self):
        """Seçili değerleri al"""
        selected = []
        for val, var in self.checkboxes.items():
            if val != "__ALL__" and var.get():
                selected.append(val)
        return selected if selected else None

    def _apply(self):
        """Filtreyi uygula"""
        selected = self._get_selected_values()
        self.callback(self.column_name, selected)
        self.destroy()


# ============== GELİŞMİŞ TREEVIEW SINIFI ==============
class EnhancedTreeview(tk.Frame):
    """Header'da filtre ikonu olan gelişmiş Treeview - Excel tarzı filtreleme"""

    def __init__(self, parent, columns, column_widths=None, show_filters=True, **kwargs):
        super().__init__(parent, bg="#2b2b2b")

        self.columns = columns
        self.column_widths = column_widths or [100] * len(columns)
        self.show_filters = show_filters
        self.all_data = []
        self.filtered_data = []
        self.column_filters = {}  # {col_name: [selected_values] or None}

        # Tema renklerini belirle
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            frame_bg = "#1e1e1e"
            sb_bg = '#3a3a3a'
            sb_trough = '#1e1e1e'
            sb_active = '#4a4a4a'
        else:
            frame_bg = "#ffffff"
            sb_bg = '#c0c0c0'
            sb_trough = '#f0f0f0'
            sb_active = '#a0a0a0'

        self.tree_frame = tk.Frame(self, bg=frame_bg)
        self.tree_frame.pack(fill="both", expand=True)

        # Scrollbar'lar
        self.vsb = tk.Scrollbar(self.tree_frame, orient="vertical",
                               bg=sb_bg, troughcolor=sb_trough,
                               activebackground=sb_active,
                               highlightthickness=0, bd=0)
        self.vsb.pack(side="right", fill="y")

        self.hsb = tk.Scrollbar(self.tree_frame, orient="horizontal",
                               bg=sb_bg, troughcolor=sb_trough,
                               activebackground=sb_active,
                               highlightthickness=0, bd=0)
        self.hsb.pack(side="bottom", fill="x")

        # Treeview stili
        style = ttk.Style()
        style.theme_use("clam")
        
        if current_mode == "Dark":
            style.configure("Enhanced.Treeview",
                           background="#2b2b2b",
                           foreground="white",
                           fieldbackground="#2b2b2b",
                           rowheight=26,
                           font=('Segoe UI', 10))
            style.configure("Enhanced.Treeview.Heading",
                           background="#1f538d",
                           foreground="white",
                           font=('Segoe UI', 10, 'bold'),
                           padding=(5, 5))
            style.map("Enhanced.Treeview",
                     background=[("selected", "#1f538d")],
                     foreground=[("selected", "white")])
        else:
            style.configure("Enhanced.Treeview",
                           background="#ffffff",
                           foreground="#333333",
                           fieldbackground="#ffffff",
                           rowheight=26,
                           font=('Segoe UI', 10))
            style.configure("Enhanced.Treeview.Heading",
                           background="#0078d7",
                           foreground="white",
                           font=('Segoe UI', 10, 'bold'),
                           padding=(5, 5))
            style.map("Enhanced.Treeview",
                     background=[("selected", "#0078d7")],
                     foreground=[("selected", "white")])

        # Treeview
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
            style="Enhanced.Treeview",
            **kwargs
        )
        self.tree.pack(side="left", fill="both", expand=True)

        self.vsb.config(command=self.tree.yview)
        self.hsb.config(command=self.tree.xview)

        # Sütun başlıkları - filtre ikonu ile
        for idx, col in enumerate(columns):
            header_text = f"{col} 🔽" if show_filters else col
            self.tree.heading(
                col,
                text=header_text,
                command=lambda c=col: self._on_header_click(c)
            )
            self.tree.column(col, width=self.column_widths[idx], anchor="w")

        # Sağ tık menüsü için bind
        self.tree.bind("<Button-3>", self._show_context_menu)
        
        # Çift tıklama için bind
        self.tree.bind("<Double-1>", self._on_double_click)

    def _on_header_click(self, column):
        """Header tıklandığında - filtre popup aç"""
        if not self.show_filters:
            return

        # Mevcut veriyi al - benzersiz değerler
        unique_values = set()
        for row in self.all_data:
            col_idx = self.columns.index(column)
            if col_idx < len(row):
                unique_values.add(row[col_idx])

        # Mevcut filtreyi al
        current_filter = self.column_filters.get(column)

        # Popup aç
        FilterPopup(
            self,
            column,
            unique_values,
            current_filter,
            self._apply_column_filter
        )

    def _apply_column_filter(self, column, selected_values):
        """Sütun filtresini uygula"""
        self.column_filters[column] = selected_values
        self.apply_filters()

        # Header'ı güncelle - filtre aktifse işaret ekle
        icon = "🔽" if selected_values is None else "🔽✓"
        self.tree.heading(column, text=f"{column} {icon}")

    def load_data(self, data: List):
        """Veriyi yükle"""
        self.all_data = list(data)
        self.apply_filters()

    def apply_filters(self):
        """Filtreleri uygula"""
        # Treeview'i temizle
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Filtreleri uygula
        self.filtered_data = []
        for row in self.all_data:
            match = True
            for col_name, filter_values in self.column_filters.items():
                if filter_values is None:
                    continue

                col_idx = self.columns.index(col_name)
                if col_idx < len(row):
                    if str(row[col_idx]) not in filter_values:
                        match = False
                        break

            if match:
                self.filtered_data.append(row)
                self.tree.insert("", "end", values=row)

    def clear_filters(self):
        """Tüm filtreleri temizle"""
        self.column_filters.clear()
        for col in self.columns:
            self.tree.heading(col, text=f"{col} 🔽" if self.show_filters else col)
        self.apply_filters()

    def _show_context_menu(self, event):
        """Sağ tık menüsünü göster"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._open_context_menu(event.x_root, event.y_root)

    def _open_context_menu(self, x, y):
        """Context menu popup aç"""
        menu_win = ctk.CTkToplevel(self)
        menu_win.overrideredirect(True)
        menu_win.geometry(f"+{x}+{y}")

        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            menu_bg = "#2b2b2b"
            hover_color = "#3b3b3b"
            text_color = "white"
        else:
            menu_bg = "#f0f0f0"
            hover_color = "#e0e0e0"
            text_color = "black"

        menu_win.configure(fg_color=menu_bg)

        # Menü öğeleri
        options = [
            ("📋 Kopyala", self._on_copy),
            ("🔄 Filtreleri Temizle", self.clear_filters),
        ]

        for text, command in options:
            btn = ctk.CTkButton(
                menu_win,
                text=text,
                width=150,
                height=30,
                anchor="w",
                fg_color="transparent",
                text_color=text_color,
                hover_color=hover_color,
                command=lambda cmd=command: self._execute_menu_action(cmd, menu_win)
            )
            btn.pack(fill="x", padx=2, pady=1)

        menu_win.bind("<FocusOut>", lambda e: menu_win.destroy())
        menu_win.focus_set()

    def _execute_menu_action(self, command, menu_win):
        """Menü aksiyonunu çalıştır"""
        menu_win.destroy()
        command()

    def _on_copy(self):
        """Seçili satırı kopyala"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item["values"]
            text = "\t".join(str(v) for v in values)
            self.clipboard_clear()
            self.clipboard_append(text)

    def _on_double_click(self, event):
        """Çift tıklama olayı"""
        # Alt sınıflar override edebilir
        pass

    def get_selected(self):
        """Seçili satırları döndür"""
        return [self.tree.item(item)["values"] for item in self.tree.selection()]

    def get_all_data(self):
        """Tüm veriyi döndür"""
        return self.all_data

    def get_filtered_data(self):
        """Filtrelenmiş veriyi döndür"""
        return self.filtered_data

    def bind_tree(self, event, handler):
        """Tree event binding"""
        self.tree.bind(event, handler)

    def get_tree(self):
        """Treeview widget'ını döndür"""
        return self.tree


class ModernDatePicker(ctk.CTkFrame):
    """Modern inline tarih seçici"""
    
    def __init__(self, parent, variable: ctk.StringVar, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.variable = variable
        self.picker_visible = False
        self.picker_frame = None
        
        # Entry ve buton container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(side="left")
        
        self.entry = ctk.CTkEntry(container, textvariable=variable, width=110, 
                                  font=ctk.CTkFont(size=13))
        self.entry.pack(side="left", padx=(0, 5))
        
        self.btn = ctk.CTkButton(container, text="📅", width=35, height=28,
                                 command=self.toggle_picker,
                                 font=ctk.CTkFont(size=14))
        self.btn.pack(side="left")
    
    def toggle_picker(self):
        if self.picker_visible:
            self.hide_picker()
        else:
            self.show_picker()
    
    def show_picker(self):
        if self.picker_frame:
            self.picker_frame.destroy()
        
        self.picker_frame = ctk.CTkFrame(self, corner_radius=10)
        self.picker_frame.pack(side="left", padx=10)
        
        try:
            current = datetime.strptime(self.variable.get(), '%Y-%m-%d')
        except:
            current = datetime.now()
        
        # Spinbox'lar için tkinter kullanıyoruz (customtkinter'da yok)
        inner = ctk.CTkFrame(self.picker_frame, fg_color="transparent")
        inner.pack(padx=10, pady=8)
        
        # Yıl
        ctk.CTkLabel(inner, text="Yıl", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=3)
        self.year_var = ctk.StringVar(value=str(current.year))
        year_entry = ctk.CTkEntry(inner, textvariable=self.year_var, width=60, 
                                  font=ctk.CTkFont(size=12))
        year_entry.grid(row=1, column=0, padx=3)
        
        # Ay
        ctk.CTkLabel(inner, text="Ay", font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=3)
        self.month_var = ctk.StringVar(value=str(current.month).zfill(2))
        month_entry = ctk.CTkEntry(inner, textvariable=self.month_var, width=45,
                                   font=ctk.CTkFont(size=12))
        month_entry.grid(row=1, column=1, padx=3)
        
        # Gün
        ctk.CTkLabel(inner, text="Gün", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=3)
        self.day_var = ctk.StringVar(value=str(current.day).zfill(2))
        day_entry = ctk.CTkEntry(inner, textvariable=self.day_var, width=45,
                                 font=ctk.CTkFont(size=12))
        day_entry.grid(row=1, column=2, padx=3)
        
        # Butonlar
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.grid(row=1, column=3, padx=5)
        
        ctk.CTkButton(btn_frame, text="✓", width=30, height=28,
                     fg_color="#27ae60", hover_color="#2ecc71",
                     command=self.apply_date).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="✗", width=30, height=28,
                     fg_color="#e74c3c", hover_color="#c0392b",
                     command=self.hide_picker).pack(side="left", padx=2)
        
        self.picker_visible = True
        self.btn.configure(text="❌")
    
    def hide_picker(self):
        if self.picker_frame:
            self.picker_frame.destroy()
            self.picker_frame = None
        self.picker_visible = False
        self.btn.configure(text="📅")
    
    def apply_date(self):
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            day = min(int(self.day_var.get()), 28 if month == 2 else 30 if month in [4,6,9,11] else 31)
            self.variable.set(f"{year}-{month:02d}-{day:02d}")
        except:
            pass
        self.hide_picker()


class ModernDateRangeSelector(ctk.CTkFrame):
    """Modern tarih aralığı seçici"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        # Başlangıç
        ctk.CTkLabel(self, text="Başlangıç:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 5))
        self.start_var = ctk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        self.start_picker = ModernDatePicker(self, self.start_var)
        self.start_picker.pack(side="left", padx=(0, 15))
        
        # Bitiş
        ctk.CTkLabel(self, text="Bitiş:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 5))
        self.end_var = ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.end_picker = ModernDatePicker(self, self.end_var)
        self.end_picker.pack(side="left", padx=(0, 20))
        
        # Hızlı seçim butonları
        quick_frame = ctk.CTkFrame(self, fg_color="transparent")
        quick_frame.pack(side="left")
        
        buttons = [
            ("Bugün", "#3498db", 0),
            ("7 Gün", "#9b59b6", 7),
            ("30 Gün", "#e67e22", 30),
            ("Bu Ay", "#27ae60", -1)
        ]
        
        for text, color, days in buttons:
            cmd = lambda d=days: self._quick_select(d) if d >= 0 else self._select_this_month()
            ctk.CTkButton(quick_frame, text=text, width=70, height=28,
                         fg_color=color, hover_color=self._lighten(color),
                         font=ctk.CTkFont(size=12, weight="bold"),
                         command=cmd).pack(side="left", padx=3)
    
    def _lighten(self, color):
        try:
            r = min(255, int(int(color[1:3], 16) * 1.2))
            g = min(255, int(int(color[3:5], 16) * 1.2))
            b = min(255, int(int(color[5:7], 16) * 1.2))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color
    
    def _quick_select(self, days):
        end = datetime.now()
        start = end - timedelta(days=days)
        self.start_var.set(start.strftime('%Y-%m-%d'))
        self.end_var.set(end.strftime('%Y-%m-%d'))
    
    def _select_this_month(self):
        now = datetime.now()
        self.start_var.set(now.replace(day=1).strftime('%Y-%m-%d'))
        self.end_var.set(now.strftime('%Y-%m-%d'))
    
    def get_start(self): return self.start_var.get()
    def get_end(self): return self.end_var.get()


class ExcelStyleTable(ctk.CTkFrame):
    """Excel tarzı tablo - Filtreler grid içinde, tarih kolonlarında picker"""
    
    # Class-level style tracking
    _style_initialized = False
    _current_theme = "dark"
    
    def __init__(self, parent, columns: List[tuple], column_types: Dict[str, str] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.columns = columns
        self.column_types = column_types or {}
        self.data = []
        self.filtered_data = []
        self.filter_vars = {}
        self.filter_entries = {}
        self.sort_reverse = {}
        self.style_id = str(id(self))[-6:]
        
        # Ana container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Treeview satırı genişlesin
        
        # Treeview stilini ayarla
        self._setup_style()
        
        # ===== FİLTRE SATIRI =====
        self.filter_frame = ctk.CTkFrame(self, fg_color="#2d5a8a", corner_radius=5, height=40)
        self.filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        
        # ===== TREEVIEW =====
        tree_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        col_ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show="headings",
                                style="Excel.Treeview", selectmode="extended")
        
        for col_id, col_name, width in columns:
            self.tree.heading(col_id, text=f"▼ {col_name}", 
                            command=lambda c=col_id: self._sort_column(c))
            self.tree.column(col_id, width=width, minwidth=40)
        
        # Scrollbars
        v_scroll = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        h_scroll = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        # Filtre satırını oluştur
        self._create_filter_row()
    
    def _setup_style(self):
        """Treeview stilini ayarla"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Tema bazlı renkler
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        if is_dark:
            bg_color = "#2b2b2b"
            fg_color = "white"
            field_bg = "#2b2b2b"
            select_bg = "#1f538d"
            filter_bg = "#3d3d3d"
            entry_bg = "#4a4a4a"
        else:
            bg_color = "#ffffff"
            fg_color = "#333333"
            field_bg = "#ffffff"
            select_bg = "#0078d7"
            filter_bg = "#e0e0e0"
            entry_bg = "#f5f5f5"
        
        style.configure("Excel.Treeview",
                       background=bg_color,
                       foreground=fg_color,
                       fieldbackground=field_bg,
                       rowheight=26,
                       font=('Segoe UI', 10))
        style.configure("Excel.Treeview.Heading",
                       background="#1f538d",
                       foreground="white",
                       font=('Segoe UI', 10, 'bold'),
                       padding=(5, 5))
        style.map("Excel.Treeview",
                 background=[("selected", select_bg)],
                 foreground=[("selected", "white")])
        
        # Filter frame renkleri kaydet
        self._filter_bg = filter_bg
        self._entry_bg = entry_bg
        self._fg_color = fg_color
    
    def update_theme(self, theme: str):
        """Tema değişikliğinde renkleri güncelle"""
        is_dark = theme == 'dark'
        
        if is_dark:
            filter_bg = "#3d3d3d"
            entry_bg = "#4a4a4a"
            fg_color = "white"
        else:
            filter_bg = "#e0e0e0"
            entry_bg = "#f5f5f5"
            fg_color = "#333333"
        
        # Filter frame güncelle
        if hasattr(self, 'filter_frame'):
            self.filter_frame.configure(fg_color=filter_bg)
        
        # Entry'leri güncelle
        for col_id, entry in self.filter_entries.items():
            if entry and entry.winfo_exists():
                entry.configure(bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        
        # Tablo yenile
        self._refresh_tree()
    
    def _create_filter_row(self):
        """Filtre satırı oluştur - CustomTkinter ile"""
        # Başlık etiketi
        ctk.CTkLabel(self.filter_frame, text="🔍 Filtreler:", 
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="white").pack(side="left", padx=(10, 15), pady=5)
        
        # Her kolon için filtre entry
        for col_id, col_name, width in self.columns:
            # Label
            ctk.CTkLabel(self.filter_frame, text=f"{col_name}:", 
                        font=ctk.CTkFont(size=11),
                        text_color="#cccccc").pack(side="left", padx=(5, 2), pady=5)
            
            # Entry
            var = ctk.StringVar()
            var.trace_add("write", lambda *args: self._apply_filters())
            self.filter_vars[col_id] = var
            
            entry = ctk.CTkEntry(self.filter_frame, textvariable=var,
                                width=max(60, width - 40), height=28,
                                placeholder_text="...",
                                font=ctk.CTkFont(size=11))
            entry.pack(side="left", padx=2, pady=5)
            self.filter_entries[col_id] = entry
    
    def _show_date_picker(self, var, entry):
        """Mini inline tarih seçici göster"""
        # Mevcut picker varsa kapat
        if hasattr(self, '_date_popup') and self._date_popup:
            try:
                self._date_popup.destroy()
            except:
                pass
        
        # Popup oluştur
        self._date_popup = tk.Toplevel(self)
        self._date_popup.overrideredirect(True)  # Kenarlıksız
        self._date_popup.attributes('-topmost', True)
        
        # Pozisyon - entry'nin altında
        x = entry.winfo_rootx()
        y = entry.winfo_rooty() + entry.winfo_height()
        self._date_popup.geometry(f"+{x}+{y}")
        
        popup_frame = tk.Frame(self._date_popup, bg="#2d2d2d", bd=2, relief="solid")
        popup_frame.pack(fill="both", expand=True)
        
        # Mevcut tarihi parse et
        try:
            current = datetime.strptime(var.get(), '%Y-%m-%d')
        except:
            current = datetime.now()
        
        # Yıl-Ay-Gün satırı
        row = tk.Frame(popup_frame, bg="#2d2d2d")
        row.pack(padx=5, pady=5)
        
        year_var = tk.StringVar(value=str(current.year))
        month_var = tk.StringVar(value=str(current.month).zfill(2))
        day_var = tk.StringVar(value=str(current.day).zfill(2))
        
        tk.Spinbox(row, from_=2020, to=2030, width=5, textvariable=year_var,
                  font=('Segoe UI', 9), bg="#3d3d3d", fg="white").pack(side="left", padx=2)
        tk.Label(row, text="-", bg="#2d2d2d", fg="white").pack(side="left")
        tk.Spinbox(row, from_=1, to=12, width=3, textvariable=month_var,
                  font=('Segoe UI', 9), bg="#3d3d3d", fg="white", format="%02.0f").pack(side="left", padx=2)
        tk.Label(row, text="-", bg="#2d2d2d", fg="white").pack(side="left")
        tk.Spinbox(row, from_=1, to=31, width=3, textvariable=day_var,
                  font=('Segoe UI', 9), bg="#3d3d3d", fg="white", format="%02.0f").pack(side="left", padx=2)
        
        # Butonlar
        btn_row = tk.Frame(popup_frame, bg="#2d2d2d")
        btn_row.pack(pady=5)
        
        def apply():
            var.set(f"{year_var.get()}-{month_var.get().zfill(2)}-{day_var.get().zfill(2)}")
            self._date_popup.destroy()
        
        def clear():
            var.set("")
            self._date_popup.destroy()
        
        tk.Button(btn_row, text="✓", command=apply, bg="#27ae60", fg="white",
                 font=('Segoe UI', 8), bd=0, padx=8).pack(side="left", padx=2)
        tk.Button(btn_row, text="✗", command=lambda: self._date_popup.destroy(),
                 bg="#e74c3c", fg="white", font=('Segoe UI', 8), bd=0, padx=8).pack(side="left", padx=2)
        tk.Button(btn_row, text="Temizle", command=clear, bg="#7f8c8d", fg="white",
                 font=('Segoe UI', 8), bd=0, padx=5).pack(side="left", padx=2)
        
        # Popup dışına tıklanınca kapat
        def on_click_outside(e):
            if self._date_popup and e.widget not in [self._date_popup] + list(self._date_popup.winfo_children()):
                self._date_popup.destroy()
        
        self._date_popup.bind("<FocusOut>", lambda e: self._date_popup.after(100, self._date_popup.destroy))
    
    def set_data(self, data: List[tuple]):
        """Veriyi tabloya yükle"""
        self.data = list(data)
        self.filtered_data = list(data)
        self._refresh_tree()
    
    def _refresh_tree(self):
        """Treeview'ı yenile"""
        self.tree.delete(*self.tree.get_children())
        for row in self.filtered_data:
            self.tree.insert("", "end", values=row)
    
    def _apply_filters(self):
        """Filtreleri uygula"""
        self.filtered_data = []
        for row in self.data:
            match = True
            for i, (col_id, _, _) in enumerate(self.columns):
                filter_val = self.filter_vars[col_id].get().lower()
                # Placeholder'ı atla
                if filter_val == "🔍" or filter_val == "":
                    continue
                if filter_val not in str(row[i]).lower():
                    match = False
                    break
            if match:
                self.filtered_data.append(row)
        self._refresh_tree()
    
    def _sort_column(self, col_id):
        """Kolona göre sırala"""
        col_idx = [c[0] for c in self.columns].index(col_id)
        reverse = self.sort_reverse.get(col_id, False)
        
        self.filtered_data.sort(key=lambda x: str(x[col_idx]), reverse=reverse)
        self.sort_reverse[col_id] = not reverse
        
        # Başlığı güncelle
        for cid, cname, _ in self.columns:
            arrow = "▲" if cid == col_id and reverse else "▼"
            self.tree.heading(cid, text=f"{arrow} {cname}" if cid == col_id else f"▼ {cname}")
        
        self._refresh_tree()
    
    def get_selected(self) -> List[tuple]:
        return [self.tree.item(item)["values"] for item in self.tree.selection()]
    
    def get_all_data(self) -> List[tuple]:
        return self.data
    
    def get_filtered_data(self) -> List[tuple]:
        return self.filtered_data
    
    def clear(self):
        self.data = []
        self.filtered_data = []
        self.tree.delete(*self.tree.get_children())
    
    def clear_filters(self):
        """Tüm filtreleri temizle"""
        for var in self.filter_vars.values():
            var.set("")
        self.filtered_data = list(self.data)
        self._refresh_tree()
    
    def bind_tree(self, event, handler):
        self.tree.bind(event, handler)
    
    def get_tree(self):
        return self.tree


class ModernDataTable(ctk.CTkFrame):
    """Modern veri tablosu - Treeview tabanlı (eski uyumluluk için)"""
    
    def __init__(self, parent, columns: List[tuple], **kwargs):
        super().__init__(parent, **kwargs)
        
        self.columns = columns
        self.data = []
        
        # Filtre satırı
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.filter_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        self.filter_vars = {}
        for col_id, col_name, width in columns:
            var = ctk.StringVar()
            var.trace_add("write", lambda *args: self._apply_filters())
            self.filter_vars[col_id] = var
            
            entry = ctk.CTkEntry(self.filter_frame, textvariable=var, 
                                placeholder_text=f"🔍 {col_name}",
                                width=width-10, height=28,
                                font=ctk.CTkFont(size=11))
            entry.pack(side="left", padx=2)
        
        # Treeview container
        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Treeview stili
        style = ttk.Style()
        style.theme_use("clam")
        
        # Dark tema için stil
        style.configure("Modern.Treeview",
                       background="#2b2b2b",
                       foreground="white",
                       fieldbackground="#2b2b2b",
                       rowheight=28,
                       font=('Segoe UI', 10))
        style.configure("Modern.Treeview.Heading",
                       background="#1f538d",
                       foreground="white",
                       font=('Segoe UI', 10, 'bold'))
        style.map("Modern.Treeview",
                 background=[("selected", "#1f538d")],
                 foreground=[("selected", "white")])
        
        # Treeview
        col_ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(tree_container, columns=col_ids, show="headings",
                                style="Modern.Treeview", selectmode="extended")
        
        for col_id, col_name, width in columns:
            self.tree.heading(col_id, text=col_name, 
                            command=lambda c=col_id: self._sort_column(c))
            self.tree.column(col_id, width=width, minwidth=50)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_container, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Sıralama durumu
        self.sort_reverse = {}
    
    def set_data(self, data: List[tuple]):
        """Veriyi tabloya yükle"""
        self.data = list(data)
        self._refresh_tree()
    
    def _refresh_tree(self, filtered_data=None):
        """Treeview'ı yenile"""
        self.tree.delete(*self.tree.get_children())
        data = filtered_data if filtered_data is not None else self.data
        for row in data:
            self.tree.insert("", "end", values=row)
    
    def _apply_filters(self):
        """Filtreleri uygula"""
        filtered = []
        for row in self.data:
            match = True
            for i, (col_id, _, _) in enumerate(self.columns):
                filter_val = self.filter_vars[col_id].get().lower()
                if filter_val and filter_val not in str(row[i]).lower():
                    match = False
                    break
            if match:
                filtered.append(row)
        self._refresh_tree(filtered)
    
    def _sort_column(self, col_id):
        """Kolona göre sırala"""
        col_idx = [c[0] for c in self.columns].index(col_id)
        reverse = self.sort_reverse.get(col_id, False)
        
        self.data.sort(key=lambda x: str(x[col_idx]), reverse=reverse)
        self.sort_reverse[col_id] = not reverse
        self._apply_filters()
    
    def get_selected(self) -> List[tuple]:
        """Seçili satırları döndür"""
        return [self.tree.item(item)["values"] for item in self.tree.selection()]
    
    def get_all_data(self) -> List[tuple]:
        """Tüm veriyi döndür"""
        return self.data
    
    def clear(self):
        """Tabloyu temizle"""
        self.data = []
        self.tree.delete(*self.tree.get_children())
    
    def bind_tree(self, event, handler):
        self.tree.bind(event, handler)
    
    def get_tree(self):
        return self.tree


class KerzzGUIModern(ctk.CTk):
    """Modern KERZZ BOSS GUI - CustomTkinter"""
    
    def __init__(self):
        super().__init__()
        
        self.title("🍽️ KERZZ BOSS Yönetim Sistemi PRO v3.0")
        self.geometry("1500x900")
        self.minsize(1200, 700)
        
        # Veritabanı
        self.db = None
        self.bagli = False
        
        # Renkler
        self.colors = {
            'primary': "#1f538d",
            'success': "#27ae60",
            'danger': "#e74c3c",
            'warning': "#f39c12",
            'info': "#3498db",
            'dark': "#2c3e50"
        }
        
        # Tooltips listesi (referansları tutmak için)
        self.tooltips = []
        
        # Ana layout
        self._create_header()
        self._create_sidebar()
        self._create_main_content()
        self._create_statusbar()
        
        # Loading overlay
        self.loading_overlay = LoadingOverlay(self.main_frame)
        
        # Klavye kısayolları
        self._setup_keyboard_shortcuts()
        
        # Hoşgeldin mesajı
        self._show_welcome()
    
    def _create_header(self):
        """Üst başlık paneli"""
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=self.colors['primary'])
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Logo ve başlık
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(title_frame, text="🍽️ KERZZ BOSS", 
                    font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        ctk.CTkLabel(title_frame, text="  Yönetim Sistemi PRO v3.0", 
                    font=ctk.CTkFont(size=16),
                    text_color="#bdc3c7").pack(side="left", pady=(8, 0))
        
        # Sağ taraf butonları
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)
        
        # Tema değiştir
        self.theme_btn = ctk.CTkButton(right_frame, text="🌙", width=40, height=35,
                                       command=self._toggle_theme,
                                       fg_color="#34495e", hover_color="#4a6278")
        self.theme_btn.pack(side="left", padx=5)
        
        # İstatistikler
        ctk.CTkButton(right_frame, text="📊 İstatistikler", width=120, height=35,
                     command=self._show_stats,
                     fg_color=self.colors['success'], hover_color="#2ecc71").pack(side="left", padx=5)
    
    def _create_sidebar(self):
        """Sol kenar çubuğu - Bağlantı paneli"""
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.pack(fill="y", side="left", padx=(0, 0))
        self.sidebar.pack_propagate(False)
        
        # Bağlantı başlığı
        ctk.CTkLabel(self.sidebar, text="🔌 Veritabanı Bağlantısı",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 15))
        
        # Sunucu
        ctk.CTkLabel(self.sidebar, text="Sunucu:", anchor="w").pack(fill="x", padx=20)
        self.server_var = ctk.StringVar(value="ABC01CL099")
        ctk.CTkEntry(self.sidebar, textvariable=self.server_var, width=260).pack(padx=20, pady=(0, 10))
        
        # Veritabanı
        ctk.CTkLabel(self.sidebar, text="Veritabanı:", anchor="w").pack(fill="x", padx=20)
        self.database_var = ctk.StringVar(value="TALAS")
        ctk.CTkOptionMenu(self.sidebar, variable=self.database_var,
                         values=["TALAS", "VERI", "LOG_DB"],
                         width=260).pack(padx=20, pady=(0, 10))
        
        # Auth tipi
        ctk.CTkLabel(self.sidebar, text="Kimlik Doğrulama:", anchor="w").pack(fill="x", padx=20)
        self.auth_var = ctk.StringVar(value="windows")
        
        auth_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        auth_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkRadioButton(auth_frame, text="Windows", variable=self.auth_var, 
                          value="windows", command=self._toggle_auth).pack(side="left")
        ctk.CTkRadioButton(auth_frame, text="SQL Server", variable=self.auth_var,
                          value="sql", command=self._toggle_auth).pack(side="left", padx=10)
        
        # SQL Auth bilgileri
        self.sql_auth_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sql_auth_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(self.sql_auth_frame, text="Kullanıcı:", anchor="w").pack(fill="x")
        self.username_var = ctk.StringVar(value="sa")
        self.username_entry = ctk.CTkEntry(self.sql_auth_frame, textvariable=self.username_var,
                                          width=260, state="disabled")
        self.username_entry.pack(pady=(0, 5))
        
        ctk.CTkLabel(self.sql_auth_frame, text="Şifre:", anchor="w").pack(fill="x")
        self.password_var = ctk.StringVar()
        self.password_entry = ctk.CTkEntry(self.sql_auth_frame, textvariable=self.password_var,
                                          width=260, show="●", state="disabled")
        self.password_entry.pack()
        
        # Bağlan butonu
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        self.connect_btn = ctk.CTkButton(btn_frame, text="🔌 Bağlan", height=40,
                                        fg_color=self.colors['success'],
                                        hover_color="#2ecc71",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=self._connect)
        self.connect_btn.pack(fill="x", pady=(0, 10))
        
        self.disconnect_btn = ctk.CTkButton(btn_frame, text="🔌 Bağlantıyı Kes", height=40,
                                           fg_color=self.colors['danger'],
                                           hover_color="#c0392b",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           command=self._disconnect,
                                           state="disabled")
        self.disconnect_btn.pack(fill="x")
        
        # Durum göstergesi
        self.status_indicator = ctk.CTkLabel(self.sidebar, 
                                            text="⚫ Bağlı Değil",
                                            font=ctk.CTkFont(size=14, weight="bold"),
                                            text_color=self.colors['danger'])
        self.status_indicator.pack(pady=20)
        
        # Sidebar gizle butonu
        self.sidebar_visible = True
        self.toggle_sidebar_btn = ctk.CTkButton(self.sidebar, text="◀ Gizle", width=100,
                                               fg_color="#34495e", hover_color="#4a6278",
                                               command=self._toggle_sidebar)
        self.toggle_sidebar_btn.pack(side="bottom", pady=20)
    
    def _create_main_content(self):
        """Ana içerik alanı"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, side="left")
        
        # Tab görünümü
        self.tabview = ctk.CTkTabview(self.main_frame, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sekmeler
        self.tab_iptal = self.tabview.add("📋 İptal Ürünler")
        self.tab_birlestirme = self.tabview.add("🔀 Masa Birleştirme")
        self.tab_fiyat = self.tabview.add("💰 Fiyat Güncelle")
        self.tab_adisyon = self.tabview.add("🗑️ Adisyon Sil")
        self.tab_arsiv = self.tabview.add("📦 Arşiv")
        self.tab_about = self.tabview.add("ℹ️ Hakkında")
        
        # Her sekme içeriği
        self._create_iptal_tab()
        self._create_birlestirme_tab()
        self._create_fiyat_tab()
        self._create_adisyon_tab()
        self._create_arsiv_tab()
        self._create_about_tab()
    
    def _create_iptal_tab(self):
        """İptal ürünler sekmesi - Excel tarzı"""
        # Üst buton paneli
        top_frame = ctk.CTkFrame(self.tab_iptal, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top_frame, text="📋 İptal Edilen Ürünler",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Tarih aralığı seçimi
        date_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        date_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(date_frame, text="📅 Tarih:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        
        # Başlangıç tarihi
        self.iptal_start_var = ctk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        self.iptal_start_entry = ctk.CTkEntry(date_frame, textvariable=self.iptal_start_var, 
                                               width=100, font=ctk.CTkFont(size=11))
        self.iptal_start_entry.pack(side="left", padx=2)
        
        ctk.CTkLabel(date_frame, text="→", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        
        # Bitiş tarihi
        self.iptal_end_var = ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.iptal_end_entry = ctk.CTkEntry(date_frame, textvariable=self.iptal_end_var,
                                             width=100, font=ctk.CTkFont(size=11))
        self.iptal_end_entry.pack(side="left", padx=2)
        
        # Adisyon arama
        ctk.CTkLabel(date_frame, text="Adisyon:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(15, 5))
        self.iptal_adisyon_var = ctk.StringVar()
        ctk.CTkEntry(date_frame, textvariable=self.iptal_adisyon_var, 
                    width=100, placeholder_text="Adisyon No").pack(side="left", padx=2)
        
        # Masa arama  
        ctk.CTkLabel(date_frame, text="Masa:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(15, 5))
        self.iptal_masa_var = ctk.StringVar()
        ctk.CTkEntry(date_frame, textvariable=self.iptal_masa_var, 
                    width=80, placeholder_text="Masa No").pack(side="left", padx=2)
        
        fetch_btn = ctk.CTkButton(top_frame, text="🔍 Verileri Getir", width=130,
                     fg_color=self.colors['info'], hover_color="#5dade2",
                     command=self._iptal_listele)
        fetch_btn.pack(side="left", padx=10)
        self.tooltips.append(ToolTip(fetch_btn, "Belirlenen tarih aralığındaki iptal kayıtlarını listeler (F5)"))
        
        # Filtreleri temizle butonu iptal_table oluşturulduktan sonra oluşturulacak
        self.iptal_clear_btn_frame = top_frame  # Referans tut
        
        # İpucu
        ctk.CTkLabel(top_frame, text="💡 Sütun başlığına tıklayarak filtreleyin",
                    font=ctk.CTkFont(size=10), text_color="#888888").pack(side="right", padx=10)
        
        # Excel tarzı veri tablosu (filtreler header'da)
        columns = ['Anahtar', 'Tarih', 'Adisyon', 'Masa', 'Ürün', 'Miktar', 'Fiyat', 'Toplam', 'Silen', 'Silme Zamanı']
        widths = [80, 100, 100, 70, 180, 60, 80, 80, 100, 130]
        
        self.iptal_table = EnhancedTreeview(self.tab_iptal, columns, widths, show_filters=True)
        self.iptal_table.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Seçim değiştiğinde sayacı güncelle
        self.iptal_table.tree.bind("<<TreeviewSelect>>", lambda e: self._update_selection_count(self.iptal_table))
        
        # Filtreleri temizle butonunu şimdi ekle (tablo oluşturulduktan sonra)
        clear_btn = ctk.CTkButton(self.iptal_clear_btn_frame, text="🗑️ Filtreleri Temizle", width=130,
                     fg_color="#7f8c8d", hover_color="#95a5a6",
                     command=lambda: self.iptal_table.clear_filters())
        clear_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(clear_btn, "Tüm sütun filtrelerini temizler"))
        
        # Alt buton paneli
        btn_frame = ctk.CTkFrame(self.tab_iptal)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        geri_al_btn = ctk.CTkButton(btn_frame, text="✅ Seçileni Geri Al", width=150,
                     fg_color=self.colors['success'], hover_color="#2ecc71",
                     command=self._iptal_geri_al)
        geri_al_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(geri_al_btn, "Seçili iptal kaydını geri alır"))
        
        toplu_geri_btn = ctk.CTkButton(btn_frame, text="✅ Tümünü Geri Al", width=150,
                     fg_color=self.colors['warning'], hover_color="#f5b041",
                     command=self._iptal_toplu_geri_al)
        toplu_geri_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(toplu_geri_btn, "Listede görünen TÜM iptal kayıtlarını geri alır"))
        
        kalici_sil_btn = ctk.CTkButton(btn_frame, text="🗑️ Kalıcı Sil", width=150,
                     fg_color="#c0392b", hover_color="#e74c3c",
                     command=self._iptal_kalici_sil)
        kalici_sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(kalici_sil_btn, "Seçili kaydı veritabanından kalıcı olarak siler (Delete)"))
        
        derin_sil_btn = ctk.CTkButton(btn_frame, text="☠️ DERİN SİL", width=150,
                     fg_color="#8B0000", hover_color="#a00000",
                     command=self._iptal_derin_sil)
        derin_sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(derin_sil_btn, "⚠️ TÜM veritabanlarından ilişkili kayıtları siler!"))
        
        excel_btn = ctk.CTkButton(btn_frame, text="📤 Excel", width=100,
                     fg_color=self.colors['info'], hover_color="#5dade2",
                     command=lambda: self._export_excel(self.iptal_table))
        excel_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(excel_btn, "Tabloyu Excel dosyası olarak dışa aktar"))
        
        # Sayaç
        self.iptal_count = ctk.CTkLabel(btn_frame, text="Kayıt: 0 | Seçili: 0",
                                       font=ctk.CTkFont(size=12, weight="bold"))
        self.iptal_count.pack(side="right", padx=10)
        
        # Sağ tık menüsü
        self._create_context_menu()
        self.iptal_table.bind_tree("<Button-3>", self._show_context_menu)
        self.iptal_table.bind_tree("<<TreeviewSelect>>", 
                                   lambda e: self._update_count(self.iptal_table, self.iptal_count))
    
    def _create_birlestirme_tab(self):
        """Masa birleştirme sekmesi - Excel tarzı"""
        # Üst panel
        top_frame = ctk.CTkFrame(self.tab_birlestirme, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top_frame, text="🔀 Masa Birleştirme Kayıtları",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Tarih aralığı seçimi
        date_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        date_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(date_frame, text="📅 Tarih:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        
        self.birlestirme_start_var = ctk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        ctk.CTkEntry(date_frame, textvariable=self.birlestirme_start_var, 
                    width=100, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
        
        ctk.CTkLabel(date_frame, text="→", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        
        self.birlestirme_end_var = ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ctk.CTkEntry(date_frame, textvariable=self.birlestirme_end_var,
                    width=100, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
        
        ctk.CTkButton(top_frame, text="🔍 Verileri Getir", width=130,
                     fg_color=self.colors['info'],
                     command=self._birlestirme_listele).pack(side="left", padx=10)
        
        ctk.CTkButton(top_frame, text="🗑️ Filtreleri Temizle", width=130,
                     fg_color="#7f8c8d",
                     command=lambda: self.birlestirme_table.clear_filters()).pack(side="left", padx=5)
        
        # Tablo - Excel tarzı (header'da filtre)
        columns = ['Kimlik', 'İşlem Zamanı', 'Hedef Masa', 'Hedef Adisyon', 'İptal Masa', 'İptal Adisyon', 'Kullanıcı']
        widths = [80, 140, 100, 120, 100, 120, 100]
        
        self.birlestirme_table = EnhancedTreeview(self.tab_birlestirme, columns, widths, show_filters=True)
        self.birlestirme_table.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Butonlar
        btn_frame = ctk.CTkFrame(self.tab_birlestirme)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkButton(btn_frame, text="↩️ Birleştirmeyi Geri Al", width=180,
                     fg_color=self.colors['danger'],
                     command=self._birlestirme_geri_al).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="�️ Seçileni Sil", width=130,
                     fg_color=self.colors['warning'],
                     command=self._birlestirme_sil).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="🗑️ Seçilenleri Sil", width=140,
                     fg_color="#c0392b",
                     command=self._birlestirme_toplu_sil).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="☠️ Derin Sil", width=120,
                     fg_color="#8B0000",
                     command=self._birlestirme_derin_sil).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="☠️ Seçilenleri Derin Sil", width=160,
                     fg_color="#4a0000",
                     command=self._birlestirme_toplu_derin_sil).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="�📤 Excel", width=100,
                     fg_color=self.colors['info'],
                     command=lambda: self._export_excel(self.birlestirme_table)).pack(side="left", padx=5)
    
    def _create_fiyat_tab(self):
        """Fiyat güncelleme sekmesi - Excel tarzı"""
        # Üst panel
        top_frame = ctk.CTkFrame(self.tab_fiyat, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top_frame, text="💰 Ürün Fiyat Güncelleme",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        fetch_btn = ctk.CTkButton(top_frame, text="🔍 Ürünleri Getir", width=130,
                     fg_color=self.colors['info'],
                     command=self._urunleri_listele)
        fetch_btn.pack(side="left", padx=20)
        self.tooltips.append(ToolTip(fetch_btn, "Veritabanındaki ürün listesini getirir (F5)"))
        
        # Fiyat güncelleme alanı
        update_frame = ctk.CTkFrame(self.tab_fiyat)
        update_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(update_frame, text="💰 Yeni Fiyat:", 
                    font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        self.yeni_fiyat_var = ctk.StringVar()
        ctk.CTkEntry(update_frame, textvariable=self.yeni_fiyat_var, width=120,
                    placeholder_text="0.00").pack(side="left")
        
        guncelle_btn = ctk.CTkButton(update_frame, text="💾 Güncelle", width=120,
                     fg_color=self.colors['success'],
                     command=self._fiyat_guncelle)
        guncelle_btn.pack(side="left", padx=10)
        self.tooltips.append(ToolTip(guncelle_btn, "Seçili ürünün fiyatını günceller"))
        
        sil_btn = ctk.CTkButton(update_frame, text="🗑️ Seçili Sil", width=120,
                     fg_color=self.colors['danger'],
                     command=self._urun_sil)
        sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(sil_btn, "Seçili ürünü veritabanından siler (Delete)"))
        
        toplu_sil_btn = ctk.CTkButton(update_frame, text="☠️ Tümünü Sil", width=120,
                     fg_color="#8B0000",
                     command=self._urun_toplu_sil)
        toplu_sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(toplu_sil_btn, "⚠️ Filtrelenmiş TÜM ürünleri siler!"))
        
        clear_btn = ctk.CTkButton(update_frame, text="🗑️ Filtreleri Temizle", width=130,
                     fg_color="#7f8c8d",
                     command=lambda: self.urun_table.clear_filters())
        clear_btn.pack(side="left", padx=20)
        self.tooltips.append(ToolTip(clear_btn, "Tüm sütun filtrelerini temizler"))
        
        # Ürün listesi - Excel tarzı (header'da filtre)
        columns = ['Ürün Adı', 'Birim Fiyat', 'Birim']
        widths = [300, 120, 80]
        
        self.urun_table = EnhancedTreeview(self.tab_fiyat, columns, widths, show_filters=True)
        self.urun_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Seçim değiştiğinde sayacı güncelle
        self.urun_table.tree.bind("<<TreeviewSelect>>", lambda e: self._update_selection_count(self.urun_table))
    
    def _create_adisyon_tab(self):
        """Adisyon silme sekmesi - Excel tarzı"""
        # Üst panel
        top_frame = ctk.CTkFrame(self.tab_adisyon, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top_frame, text="📋 Adisyon Silme İşlemleri",
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Tarih aralığı seçimi
        date_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        date_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(date_frame, text="📅 Tarih:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        
        self.adisyon_start_var = ctk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        ctk.CTkEntry(date_frame, textvariable=self.adisyon_start_var, 
                    width=100, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
        
        ctk.CTkLabel(date_frame, text="→", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        
        self.adisyon_end_var = ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ctk.CTkEntry(date_frame, textvariable=self.adisyon_end_var,
                    width=100, font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
        
        # Masa arama
        ctk.CTkLabel(date_frame, text="Masa:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(15, 5))
        self.adisyon_masa_var = ctk.StringVar()
        ctk.CTkEntry(date_frame, textvariable=self.adisyon_masa_var, 
                    width=80, placeholder_text="Masa No").pack(side="left", padx=2)
        
        # Adisyon No arama
        ctk.CTkLabel(date_frame, text="Adisyon:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(15, 5))
        self.adisyon_no_var = ctk.StringVar()
        ctk.CTkEntry(date_frame, textvariable=self.adisyon_no_var, 
                    width=100, placeholder_text="Adisyon No").pack(side="left", padx=2)
        
        fetch_btn = ctk.CTkButton(top_frame, text="🔍 Verileri Getir", width=130,
                     fg_color=self.colors['info'],
                     command=self._adisyon_listele)
        fetch_btn.pack(side="left", padx=10)
        self.tooltips.append(ToolTip(fetch_btn, "Adisyon kayıtlarını listeler (F5)"))
        
        clear_btn = ctk.CTkButton(top_frame, text="🗑️ Filtreleri Temizle", width=130,
                     fg_color="#7f8c8d",
                     command=lambda: self.adisyon_table.clear_filters())
        clear_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(clear_btn, "Tüm sütun filtrelerini temizler"))
        
        # Tablo - Excel tarzı (header'da filtre)
        columns = ['Adisyon No', 'Tarih', 'Masa', 'Ürün Sayısı', 'Toplam', 'Durum']
        widths = [120, 100, 80, 100, 100, 80]
        
        self.adisyon_table = EnhancedTreeview(self.tab_adisyon, columns, widths, show_filters=True)
        self.adisyon_table.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Seçim değiştiğinde sayacı güncelle
        self.adisyon_table.tree.bind("<<TreeviewSelect>>", lambda e: self._update_selection_count(self.adisyon_table))
        
        # Butonlar
        btn_frame = ctk.CTkFrame(self.tab_adisyon)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        sil_btn = ctk.CTkButton(btn_frame, text="🗑️ Seçileni Sil", width=130,
                     fg_color=self.colors['danger'],
                     command=self._adisyon_sil)
        sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(sil_btn, "Seçili adisyonu siler (Delete)"))
        
        toplu_sil_btn = ctk.CTkButton(btn_frame, text="🗑️ Seçilenleri Sil", width=140,
                     fg_color=self.colors['warning'],
                     command=self._adisyon_toplu_sil)
        toplu_sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(toplu_sil_btn, "Seçilen TÜM adisyonları toplu olarak siler"))
        
        derin_sil_btn = ctk.CTkButton(btn_frame, text="☠️ DERİN SİL", width=130,
                     fg_color="#8B0000",
                     command=self._adisyon_derin_sil)
        derin_sil_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(derin_sil_btn, "⚠️ TÜM veritabanlarından ilişkili kayıtları siler!"))
        
        toplu_derin_btn = ctk.CTkButton(btn_frame, text="☠️ Seçilenleri Derin Sil", width=160,
                     fg_color="#4a0000",
                     command=self._adisyon_toplu_derin_sil)
        toplu_derin_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(toplu_derin_btn, "⚠️ Seçilen TÜM adisyonları derin siler!"))
        
        excel_btn = ctk.CTkButton(btn_frame, text="📤 Excel", width=100,
                     fg_color=self.colors['info'],
                     command=lambda: self._export_excel(self.adisyon_table))
        excel_btn.pack(side="left", padx=5)
        self.tooltips.append(ToolTip(excel_btn, "Tabloyu Excel dosyası olarak dışa aktar"))
    
    def _create_arsiv_tab(self):
        """Arşiv sekmesi"""
        ctk.CTkLabel(self.tab_arsiv, text="📦 Arşiv işlemleri burada olacak...",
                    font=ctk.CTkFont(size=16)).pack(pady=50)
    
    def _create_about_tab(self):
        """Hakkında, Lisans ve Güncelleme sekmesi"""
        # Ana scroll frame
        scroll_frame = ctk.CTkScrollableFrame(self.tab_about)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== HAKKINDA BÖLÜMÜ ==========
        about_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        about_frame.pack(fill="x", pady=(0, 20))
        
        # Logo/Başlık
        header = ctk.CTkFrame(about_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header, text="🍽️", font=ctk.CTkFont(size=64)).pack()
        ctk.CTkLabel(header, text=APP_NAME, 
                    font=ctk.CTkFont(size=32, weight="bold")).pack()
        ctk.CTkLabel(header, text=f"Yönetim Sistemi PRO v{APP_VERSION}",
                    font=ctk.CTkFont(size=16),
                    text_color="gray").pack()
        
        # Geliştirici bilgileri
        dev_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        dev_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(dev_frame, text="👨‍💻 Geliştirici:", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(dev_frame, text=f"   {DEVELOPER}",
                    font=ctk.CTkFont(size=13)).pack(anchor="w")
        
        ctk.CTkLabel(dev_frame, text="📜 Lisans:", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(dev_frame, text="   MIT License (c) 2024-2026",
                    font=ctk.CTkFont(size=13)).pack(anchor="w")
        
        # Butonlar
        btn_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(btn_frame, text="🌐 GitHub", width=120,
                     command=lambda: webbrowser.open(GITHUB_URL)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📧 İletişim", width=120,
                     command=lambda: webbrowser.open("mailto:osmankbt038@gmail.com")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📋 Lisans", width=120,
                     command=self._show_license).pack(side="left", padx=5)
        
        # ========== LİSANS DOĞRULAMA BÖLÜMÜ ==========
        license_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        license_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(license_frame, text="🔐 Lisans Yönetimi",
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))
        
        # Lisans durumu
        self.license_status_label = ctk.CTkLabel(license_frame, 
                                                 text="⏳ Lisans kontrol ediliyor...",
                                                 font=ctk.CTkFont(size=12))
        self.license_status_label.pack(pady=5)
        
        # Lisans aktivasyon
        lic_input_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
        lic_input_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(lic_input_frame, text="E-posta:").pack(side="left", padx=5)
        self.license_email_var = ctk.StringVar()
        ctk.CTkEntry(lic_input_frame, textvariable=self.license_email_var, 
                    width=200, placeholder_text="email@example.com").pack(side="left", padx=5)
        
        ctk.CTkLabel(lic_input_frame, text="Anahtar:").pack(side="left", padx=5)
        self.license_key_var = ctk.StringVar()
        ctk.CTkEntry(lic_input_frame, textvariable=self.license_key_var,
                    width=200, placeholder_text="XXXX-XXXX-XXXX-XXXX").pack(side="left", padx=5)
        
        lic_btn_frame = ctk.CTkFrame(license_frame, fg_color="transparent")
        lic_btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(lic_btn_frame, text="✅ Aktive Et", width=120,
                     fg_color=self.colors['success'],
                     command=self._activate_license).pack(side="left", padx=5)
        ctk.CTkButton(lic_btn_frame, text="🔄 Kontrol Et", width=120,
                     fg_color=self.colors['info'],
                     command=self._check_license).pack(side="left", padx=5)
        ctk.CTkButton(lic_btn_frame, text="🔑 Anahtar Oluştur", width=130,
                     fg_color=self.colors['warning'],
                     command=self._generate_license_key).pack(side="left", padx=5)
        
        # ========== GÜNCELLEME BÖLÜMÜ ==========
        update_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        update_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(update_frame, text="🔄 Güncelleme Yönetimi",
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))
        
        # Sürüm bilgisi
        version_frame = ctk.CTkFrame(update_frame, fg_color="transparent")
        version_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(version_frame, text=f"Mevcut Sürüm: v{APP_VERSION}",
                    font=ctk.CTkFont(size=13)).pack(side="left")
        
        self.update_status_label = ctk.CTkLabel(version_frame, text="",
                                                font=ctk.CTkFont(size=12),
                                                text_color="gray")
        self.update_status_label.pack(side="right")
        
        # Güncelleme butonları
        update_btn_frame = ctk.CTkFrame(update_frame, fg_color="transparent")
        update_btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(update_btn_frame, text="🔍 Güncelleme Kontrol", width=160,
                     fg_color=self.colors['info'],
                     command=self._check_updates).pack(side="left", padx=5)
        ctk.CTkButton(update_btn_frame, text="⬇️ Güncelle", width=120,
                     fg_color=self.colors['success'],
                     command=self._download_update).pack(side="left", padx=5)
        
        # Otomatik güncelleme
        auto_frame = ctk.CTkFrame(update_frame, fg_color="transparent")
        auto_frame.pack(fill="x", padx=20, pady=10)
        
        self.auto_update_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(auto_frame, text="Başlangıçta güncelleme kontrol et",
                       variable=self.auto_update_var).pack(side="left")
        
        ctk.CTkButton(auto_frame, text="🚀 Başlangıca Ekle", width=140,
                     fg_color="#34495e",
                     command=self._add_to_startup).pack(side="right", padx=5)
        
        # ========== SİSTEM BİLGİSİ ==========
        sys_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        sys_frame.pack(fill="x")
        
        ctk.CTkLabel(sys_frame, text="💻 Sistem Bilgisi",
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))
        
        import platform
        sys_info = f"""
        İşletim Sistemi: {platform.system()} {platform.release()}
        Python Sürümü: {platform.python_version()}
        Makine: {platform.machine()}
        """
        
        ctk.CTkLabel(sys_frame, text=sys_info,
                    font=ctk.CTkFont(size=11),
                    justify="left").pack(padx=20, pady=(0, 15))
        
        # İlk lisans kontrolü
        self.after(1000, self._check_license)
    
    def _show_license(self):
        """Lisans metnini göster"""
        license_text = """
MIT License

Copyright (c) 2024-2026 Osman Kobat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""
        messagebox.showinfo("📜 MIT Lisansı", license_text)
    
    def _check_license(self):
        """Lisans durumunu kontrol et"""
        if not LICENSE_MODULE_AVAILABLE:
            self.license_status_label.configure(
                text="⚠️ Lisans modülü yüklü değil (Demo mod)",
                text_color="orange"
            )
            return
        
        try:
            lm = LicenseManager()
            valid, message = lm.check_license()
            
            if valid:
                self.license_status_label.configure(text=message, text_color="green")
            else:
                self.license_status_label.configure(text=message, text_color="red")
        except Exception as e:
            self.license_status_label.configure(
                text=f"❌ Hata: {e}",
                text_color="red"
            )
    
    def _activate_license(self):
        """Lisansı aktive et"""
        if not LICENSE_MODULE_AVAILABLE:
            messagebox.showwarning("Uyarı", "Lisans modülü yüklü değil!")
            return
        
        email = self.license_email_var.get().strip()
        key = self.license_key_var.get().strip()
        
        if not email or not key:
            messagebox.showwarning("Uyarı", "E-posta ve lisans anahtarı gerekli!")
            return
        
        try:
            lm = LicenseManager()
            success, message = lm.activate_license(key, email)
            
            if success:
                messagebox.showinfo("Başarılı", message)
                self._check_license()
            else:
                messagebox.showerror("Hata", message)
        except Exception as e:
            messagebox.showerror("Hata", str(e))
    
    def _generate_license_key(self):
        """Demo için lisans anahtarı oluştur"""
        if not LICENSE_MODULE_AVAILABLE:
            messagebox.showwarning("Uyarı", "Lisans modülü yüklü değil!")
            return
        
        email = self.license_email_var.get().strip()
        if not email:
            messagebox.showwarning("Uyarı", "Önce e-posta adresinizi girin!")
            return
        
        try:
            lm = LicenseManager()
            key = lm._generate_license_key(email)
            self.license_key_var.set(key)
            messagebox.showinfo("Lisans Anahtarı", 
                              f"Bu bilgisayar için oluşturulan anahtar:\n\n{key}\n\n"
                              f"Bu anahtarı kaydedin!")
        except Exception as e:
            messagebox.showerror("Hata", str(e))
    
    def _check_updates(self):
        """Güncelleme kontrol et"""
        if not LICENSE_MODULE_AVAILABLE:
            messagebox.showinfo("Bilgi", "Güncelleme modülü yüklü değil!")
            return
        
        self.update_status_label.configure(text="🔍 Kontrol ediliyor...")
        self.update()
        
        def check():
            try:
                um = UpdateManager()
                has_update, message, info = um.check_for_updates()
                
                self.after(0, lambda: self.update_status_label.configure(text=message))
                
                if has_update and info:
                    self.after(0, lambda: messagebox.showinfo(
                        "Güncelleme Mevcut",
                        f"Yeni sürüm: v{info.get('version')}\n\n"
                        f"{info.get('body', '')[:200]}...\n\n"
                        f"İndirmek için 'Güncelle' butonuna tıklayın."
                    ))
            except Exception as e:
                self.after(0, lambda: self.update_status_label.configure(
                    text=f"❌ Hata: {e}"
                ))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _download_update(self):
        """Güncellemeyi indir"""
        if not LICENSE_MODULE_AVAILABLE:
            messagebox.showinfo("Bilgi", "Güncelleme modülü yüklü değil!")
            return
        
        try:
            um = UpdateManager()
            has_update, message, info = um.check_for_updates()
            
            if not has_update:
                messagebox.showinfo("Bilgi", "Güncel sürümü kullanıyorsunuz!")
                return
            
            if messagebox.askyesno("Güncelleme", 
                                   f"v{info.get('version')} indirilsin mi?"):
                self.update_status_label.configure(text="⬇️ İndiriliyor...")
                
                def download():
                    success, result = um.download_update()
                    if success:
                        self.after(0, lambda: messagebox.showinfo(
                            "İndirme Tamamlandı",
                            f"Dosya: {result}"
                        ))
                    else:
                        self.after(0, lambda: messagebox.showerror("Hata", result))
                    
                    self.after(0, lambda: self.update_status_label.configure(
                        text="İndirme tamamlandı" if success else "İndirme başarısız"
                    ))
                
                threading.Thread(target=download, daemon=True).start()
                
        except Exception as e:
            messagebox.showerror("Hata", str(e))
    
    def _add_to_startup(self):
        """Windows başlangıcına ekle"""
        if not LICENSE_MODULE_AVAILABLE:
            messagebox.showinfo("Bilgi", "Servis modülü yüklü değil!")
            return
        
        try:
            service = BackgroundService()
            success, message = service.create_startup_shortcut()
            
            if success:
                messagebox.showinfo("Başarılı", message)
            else:
                messagebox.showerror("Hata", message)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _create_statusbar(self):
        """Alt durum çubuğu - gelişmiş"""
        self.statusbar = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=self.colors['dark'])
        self.statusbar.pack(fill="x", side="bottom")
        self.statusbar.pack_propagate(False)
        
        # Sol: Durum mesajı
        self.status_label = ctk.CTkLabel(self.statusbar, text="✓ Hazır",
                                        font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=10)
        
        # Orta: Seçim sayacı
        self.selection_label = ctk.CTkLabel(self.statusbar, text="",
                                           font=ctk.CTkFont(size=11),
                                           text_color="#3498db")
        self.selection_label.pack(side="left", padx=20)
        
        # Sağ: Bağlantı durumu ve saat
        right_frame = ctk.CTkFrame(self.statusbar, fg_color="transparent")
        right_frame.pack(side="right", padx=10)
        
        self.connection_label = ctk.CTkLabel(right_frame, text="⚫ Bağlı Değil",
                                            font=ctk.CTkFont(size=10),
                                            text_color="#e74c3c")
        self.connection_label.pack(side="left", padx=10)
        
        # Ayırıcı
        ctk.CTkLabel(right_frame, text="|", text_color="gray").pack(side="left")
        
        self.time_label = ctk.CTkLabel(right_frame, text="",
                                       font=ctk.CTkFont(size=11))
        self.time_label.pack(side="left", padx=10)
        self._update_time()
        
        # Kısayol bilgisi
        self.shortcut_label = ctk.CTkLabel(self.statusbar, 
                                          text="F5: Yenile | Delete: Sil | Ctrl+A: Tümünü Seç",
                                          font=ctk.CTkFont(size=9),
                                          text_color="gray")
        self.shortcut_label.pack(side="left", padx=50)
    
    def _setup_keyboard_shortcuts(self):
        """Klavye kısayollarını ayarla"""
        # F5 - Yenile
        self.bind("<F5>", self._on_refresh_shortcut)
        # Delete - Sil
        self.bind("<Delete>", self._on_delete_shortcut)
        # Ctrl+A - Tümünü seç
        self.bind("<Control-a>", self._on_select_all_shortcut)
        # Escape - Seçimi kaldır
        self.bind("<Escape>", self._on_escape_shortcut)
        # F1 - Yardım
        self.bind("<F1>", self._on_help_shortcut)
    
    def _on_refresh_shortcut(self, event=None):
        """F5 - Aktif sekmeyi yenile"""
        current_tab = self.tabview.get()
        if "İptal" in current_tab:
            self._iptal_listele()
        elif "Birleştirme" in current_tab:
            self._birlestirme_listele()
        elif "Fiyat" in current_tab:
            self._urunleri_getir()
        elif "Adisyon" in current_tab:
            self._adisyon_listele()
        self._update_status("🔄 Liste yenilendi (F5)")
    
    def _on_delete_shortcut(self, event=None):
        """Delete - Seçili kaydı sil"""
        current_tab = self.tabview.get()
        if "İptal" in current_tab:
            self._iptal_kalici_sil()
        elif "Birleştirme" in current_tab:
            self._birlestirme_sil()
        elif "Fiyat" in current_tab:
            self._urun_sil()
        elif "Adisyon" in current_tab:
            self._adisyon_sil()
    
    def _on_select_all_shortcut(self, event=None):
        """Ctrl+A - Tümünü seç"""
        current_tab = self.tabview.get()
        table = None
        if "İptal" in current_tab:
            table = self.iptal_table
        elif "Birleştirme" in current_tab:
            table = self.birlestirme_table
        elif "Fiyat" in current_tab:
            table = self.urun_table
        elif "Adisyon" in current_tab:
            table = self.adisyon_table
        
        if table and hasattr(table, 'tree'):
            table.tree.selection_set(table.tree.get_children())
            self._update_selection_count(table)
    
    def _on_escape_shortcut(self, event=None):
        """Escape - Seçimi kaldır"""
        current_tab = self.tabview.get()
        table = None
        if "İptal" in current_tab:
            table = self.iptal_table
        elif "Birleştirme" in current_tab:
            table = self.birlestirme_table
        elif "Fiyat" in current_tab:
            table = self.urun_table
        elif "Adisyon" in current_tab:
            table = self.adisyon_table
        
        if table and hasattr(table, 'tree'):
            table.tree.selection_remove(table.tree.selection())
            self._update_selection_count(table)
    
    def _on_help_shortcut(self, event=None):
        """F1 - Yardım"""
        help_text = """
🍽️ KERZZ BOSS Yönetim Sistemi - Klavye Kısayolları

📋 GENEL KISAYOLLAR:
  F5          → Listeyi yenile
  Delete      → Seçili kaydı sil
  Ctrl+A      → Tümünü seç
  Escape      → Seçimi kaldır
  F1          → Bu yardım penceresi

📊 TABLO İŞLEMLERİ:
  • Sütun başlığına tıkla → Filtre popup aç
  • Çift tıkla → Detay görüntüle
  • Sağ tık → Bağlam menüsü

💡 İPUÇLARI:
  • Toplu silme için önce birden fazla kayıt seçin
  • Excel'e aktarma için "Excel" butonunu kullanın
  • Derin silme tüm ilişkili verileri temizler
"""
        messagebox.showinfo("📘 Yardım", help_text)
    
    def _update_selection_count(self, table):
        """Seçim sayısını güncelle"""
        if hasattr(table, 'tree'):
            selected = len(table.tree.selection())
            total = len(table.tree.get_children())
            if selected > 0:
                self.selection_label.configure(text=f"📌 Seçili: {selected} / {total}")
            else:
                self.selection_label.configure(text=f"📋 Toplam: {total} kayıt")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Durum çubuğu mesajını güncelle"""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "loading": "⏳"
        }
        colors = {
            "info": "white",
            "success": "#27ae60",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "loading": "#3498db"
        }
        icon = icons.get(status_type, "")
        self.status_label.configure(
            text=f"{icon} {message}",
            text_color=colors.get(status_type, "white")
        )
        self.update()
    
    def _show_loading(self, message: str = "İşlem yapılıyor..."):
        """Loading overlay'i göster"""
        self.loading_overlay.show(message)
        self.update()
    
    def _hide_loading(self):
        """Loading overlay'i gizle"""
        self.loading_overlay.hide()
        self.update()

    def _create_context_menu(self):
        """Sağ tık menüsü"""
        self.context_menu = tk.Menu(self, tearoff=0, font=('Segoe UI', 10))
        self.context_menu.add_command(label="🔍 Listele", command=self._iptal_listele)
        self.context_menu.add_command(label="🔄 Yenile", command=self._iptal_listele)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✅ Seçileni Geri Al", command=self._iptal_geri_al)
        self.context_menu.add_command(label="✅ Tümünü Geri Al", command=self._iptal_toplu_geri_al)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Kalıcı Sil", command=self._iptal_kalici_sil)
        self.context_menu.add_command(label="☠️ DERİN SİL", command=self._iptal_derin_sil)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📤 Excel'e Aktar", 
                                      command=lambda: self._export_excel(self.iptal_table))
    
    def _show_context_menu(self, event):
        """Sağ tık menüsünü göster"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    # ==================== EVENT HANDLERS ====================
    
    def _toggle_theme(self):
        """Tema değiştir"""
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="☀️")
            self._apply_light_theme()
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="🌙")
            self._apply_dark_theme()
    
    def _apply_dark_theme(self):
        """Dark tema stil ayarları"""
        style = ttk.Style()
        style.configure("Excel.Treeview",
                       background="#2b2b2b",
                       foreground="white",
                       fieldbackground="#2b2b2b")
        style.map("Excel.Treeview",
                 background=[("selected", "#1f538d")],
                 foreground=[("selected", "white")])
        # Tabloları yenile
        for table in [self.iptal_table, self.birlestirme_table, self.adisyon_table, self.urun_table]:
            if hasattr(table, 'update_theme'):
                table.update_theme('dark')
    
    def _apply_light_theme(self):
        """Light tema stil ayarları"""
        style = ttk.Style()
        style.configure("Excel.Treeview",
                       background="#ffffff",
                       foreground="#333333",
                       fieldbackground="#ffffff")
        style.map("Excel.Treeview",
                 background=[("selected", "#0078d7")],
                 foreground=[("selected", "white")])
        # Tabloları yenile
        for table in [self.iptal_table, self.birlestirme_table, self.adisyon_table, self.urun_table]:
            if hasattr(table, 'update_theme'):
                table.update_theme('light')
    
    def _toggle_sidebar(self):
        """Sidebar'ı gizle/göster"""
        if self.sidebar_visible:
            self.sidebar.pack_forget()
            self.toggle_sidebar_btn.configure(text="▶ Göster")
            self.sidebar_visible = False
            # Küçük buton oluştur
            self.show_sidebar_btn = ctk.CTkButton(self.main_frame, text="▶", width=30,
                                                  command=self._toggle_sidebar)
            self.show_sidebar_btn.place(x=5, y=5)
        else:
            if hasattr(self, 'show_sidebar_btn'):
                self.show_sidebar_btn.destroy()
            self.sidebar.pack(fill="y", side="left", before=self.main_frame)
            self.toggle_sidebar_btn.configure(text="◀ Gizle")
            self.sidebar_visible = True
    
    def _toggle_auth(self):
        """Auth tipini değiştir"""
        if self.auth_var.get() == "windows":
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
        else:
            self.username_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
    
    def _update_time(self):
        """Saati güncelle"""
        self.time_label.configure(text=datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        self.after(1000, self._update_time)
    
    def _update_count(self, table: ModernDataTable, label: ctk.CTkLabel):
        """Sayacı güncelle"""
        total = len(table.get_all_data())
        selected = len(table.get_selected())
        label.configure(text=f"Kayıt: {total} | Seçili: {selected}")
    
    def _show_welcome(self):
        """Hoşgeldin animasyonu"""
        self.status_label.configure(text="🎉 KERZZ BOSS v3.0'a Hoşgeldiniz!")
    
    def _show_stats(self):
        """İstatistikleri göster"""
        messagebox.showinfo("İstatistikler", "İstatistik modülü yakında...")
    
    # ==================== DATABASE OPERATIONS ====================
    
    def _check_connection(self):
        """Bağlantı kontrolü"""
        if not self.bagli or not self.db:
            messagebox.showwarning("Uyarı", "Önce veritabanına bağlanın!")
            return False
        return True
    
    def _connect(self):
        """Veritabanına bağlan"""
        try:
            self._update_status("Bağlanılıyor...", "loading")
            server = self.server_var.get()
            database = self.database_var.get()
            
            if self.auth_var.get() == "windows":
                self.db = KerzzYonetim(server, database)
            else:
                self.db = KerzzYonetim(server, database, 
                                      self.username_var.get(), 
                                      self.password_var.get())
            
            # Bağlantıyı aç
            if not self.db.baglan():
                raise Exception("Veritabanına bağlanılamadı!")
            
            self.bagli = True
            self.status_indicator.configure(text="🟢 Bağlı", text_color=self.colors['success'])
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.configure(state="normal")
            self._update_status(f"Bağlandı: {database}", "success")
            
            # Statusbar connection label güncelle
            self.connection_label.configure(text=f"🟢 {database}", text_color="#27ae60")
            
            # Ürünleri yükle
            self._load_urunler()
            
            messagebox.showinfo("Başarılı", f"{database} veritabanına bağlanıldı!")
            
        except Exception as e:
            self._update_status("Bağlantı hatası!", "error")
            messagebox.showerror("Bağlantı Hatası", str(e))
    
    def _disconnect(self):
        """Bağlantıyı kes"""
        if self.db:
            self.db.kapat()
        self.db = None
        self.bagli = False
        self.status_indicator.configure(text="⚫ Bağlı Değil", text_color=self.colors['danger'])
        self.connect_btn.configure(state="normal")
        self.disconnect_btn.configure(state="disabled")
        self._update_status("Bağlantı kesildi", "warning")
        self.connection_label.configure(text="⚫ Bağlı Değil", text_color="#e74c3c")
    
    def _load_urunler(self):
        """Ürünleri yükle"""
        try:
            if self.db and hasattr(self.db, 'urun_listesi_getir'):
                df = self.db.urun_listesi_getir()
                if df is not None and not df.empty:
                    # Sütun adları: URUN_ADI, BIRIM_FIYAT, BIRIM
                    data = [(row['URUN_ADI'], f"{row['BIRIM_FIYAT']:.2f}", row.get('BIRIM', 'Adet')) 
                            for _, row in df.iterrows()]
                    self.urun_table.load_data(data)
                    self.status_label.configure(text=f"{len(data)} ürün yüklendi")
        except Exception as e:
            print(f"Ürün yükleme hatası: {e}")
    
    # ==================== İPTAL İŞLEMLERİ ====================
    
    def _iptal_listele(self):
        """İptal ürünlerini tarih aralığına göre listele"""
        if not self._check_connection():
            return
        
        try:
            self._update_status("İptal kayıtları yükleniyor...", "loading")
            
            # Tarih aralığını al
            start = self.iptal_start_var.get()
            end = self.iptal_end_var.get()
            adisyon = self.iptal_adisyon_var.get() or None
            
            df = self.db.iptal_urunleri_listele(start, end, adisyon)
            
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['Anahtar'],
                    str(row['Tarih'])[:10],
                    row['adisyonno'],
                    row['masa'],
                    row['urunadi'],
                    row['miktari'],
                    f"{row['birimfiyati']:.2f}",
                    f"{row['toplam']:.2f}",
                    row['silen'],
                    str(row['SILINME_ZAMAN'])[:19]
                ))
            
            self.iptal_table.load_data(data)
            self._update_count(self.iptal_table, self.iptal_count)
            self._update_selection_count(self.iptal_table)
            self._update_status(f"{len(df)} iptal kaydı listelendi ({start} - {end})", "success")
            
        except Exception as e:
            self._update_status("Hata oluştu!", "error")
            messagebox.showerror("Hata", str(e))
    
    def _urunleri_listele(self):
        """Ürünleri listele"""
        if not self._check_connection():
            return
        self._update_status("Ürünler yükleniyor...", "loading")
        self._load_urunler()
        self._update_selection_count(self.urun_table)
        self._update_status("Ürünler listelendi", "success")
    
    def _iptal_geri_al(self):
        """Seçili iptalleri geri al"""
        if not self._check_connection():
            return
        
        selected = self.iptal_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen kayıt seçin!")
            return
        
        if messagebox.askyesno("Onay", f"{len(selected)} kayıt geri alınacak?"):
            self._update_status(f"Kayıtlar geri alınıyor...", "loading")
            basarili = 0
            for row in selected:
                if self.db.urun_iptalini_geri_al(row[0]):
                    basarili += 1
            
            self._update_status(f"{basarili} kayıt geri alındı", "success")
            messagebox.showinfo("Sonuç", f"✅ {basarili} kayıt geri alındı")
            self._iptal_listele()
    
    def _iptal_toplu_geri_al(self):
        """Tüm iptalleri geri al"""
        if not self._check_connection():
            return
        
        all_data = self.iptal_table.get_all_data()
        if not all_data:
            messagebox.showwarning("Uyarı", "Liste boş!")
            return
        
        if messagebox.askyesno("⚠️ DİKKAT", f"TÜM {len(all_data)} kayıt geri alınacak!"):
            self._update_status(f"TÜM kayıtlar geri alınıyor...", "loading")
            basarili = 0
            for row in all_data:
                if self.db.urun_iptalini_geri_al(row[0]):
                    basarili += 1
            
            self._update_status(f"{basarili} kayıt geri alındı", "success")
            messagebox.showinfo("Sonuç", f"✅ {basarili} kayıt geri alındı")
            self._iptal_listele()
    
    def _iptal_kalici_sil(self):
        """Seçili iptalleri kalıcı sil"""
        if not self._check_connection():
            return
        
        selected = self.iptal_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen kayıt seçin!")
            return
        
        if messagebox.askyesno("⚠️ UYARI", f"{len(selected)} kayıt KALICI silinecek!\n\nDevam?"):
            self._update_status("Silme işlemi yapılıyor...", "loading")
            anahtarlar = [int(row[0]) for row in selected]
            sonuc = self.db.iptal_urunleri_toplu_kalici_sil(anahtarlar)
            self._update_status(f"Silme tamamlandı: {sonuc['basarili']} başarılı", "success")
            messagebox.showinfo("Sonuç", f"✅ Başarılı: {sonuc['basarili']}\n❌ Hatalı: {sonuc['hatali']}")
            self._iptal_listele()
    
    def _iptal_derin_sil(self):
        """Derin silme - tüm veritabanlarından"""
        if not self._check_connection():
            return
        
        selected = self.iptal_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen kayıt seçin!")
            return
        
        msg = f"""!!! SON DERECE TEHLIKELI !!!

{len(selected)} kayit TUM VERITABANLARINDAN silinecek!
- TALAS
- LOG_DB
- VERI

Bu islem GERI ALINAMAZ!"""
        
        if messagebox.askyesno("DERIN SILME", msg):
            if messagebox.askyesno("SON ONAY", "EMIN MISINIZ?"):
                anahtarlar = [str(row[0]) for row in selected]
                sonuc = self.db.coklu_derin_sil(anahtarlar, 'anahtar')
                messagebox.showinfo("Sonuç", f"✅ Toplam {sonuc['toplam_silinen']} kayıt silindi")
                self._iptal_listele()
    
    # ==================== BİRLEŞTİRME ====================
    
    def _birlestirme_listele(self):
        """Birleştirmeleri listele - Tarih aralığına göre"""
        if not self._check_connection():
            return
        
        try:
            self._update_status("Birleştirme kayıtları yükleniyor...", "loading")
            start = self.birlestirme_start_var.get()
            end = self.birlestirme_end_var.get()
            df = self.db.birlestirilen_adisyonlari_listele(start, end)
            
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['Kimlik'],
                    str(row['ISLEM_ZAMANI'])[:19],
                    row['HEDEF_MASA'],
                    row['HEDEF_ADISYONNO'],
                    row['IPTAL_MASA'],
                    row['IPTAL_ADISYONNO'],
                    row['KULLANICI']
                ))
            
            self.birlestirme_table.load_data(data)
            self._update_selection_count(self.birlestirme_table)
            self._update_status(f"{len(df)} birleştirme kaydı listelendi ({start} - {end})", "success")
            
        except Exception as e:
            self._update_status("Hata oluştu!", "error")
            messagebox.showerror("Hata", str(e))
    
    def _birlestirme_geri_al(self):
        """Birleştirmeyi geri al"""
        messagebox.showinfo("Bilgi", "Bu özellik yakında...")
    
    def _birlestirme_sil(self):
        """Seçili birleştirme kaydını sil (Kimlik ile)"""
        if not self._check_connection():
            return
        
        selected = self.birlestirme_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kaydı seçin!")
            return
        
        kimlik = selected[0][0]
        if messagebox.askyesno("Onay", f"Birleştirme kaydı {kimlik} silinecek?"):
            sonuc = self.db.derin_sil(str(kimlik), 'kimlik')
            messagebox.showinfo("Sonuç", f"✅ {sonuc['toplam_silinen']} kayıt silindi")
            self._birlestirme_listele()
    
    def _birlestirme_toplu_sil(self):
        """Seçili tüm birleştirme kayıtlarını sil"""
        if not self._check_connection():
            return
        
        selected = self.birlestirme_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kayıtları seçin!\n\n"
                                   "💡 İpucu: Ctrl+Tık ile birden fazla seçebilirsiniz.")
            return
        
        adet = len(selected)
        kimlik_listesi = [row[0] for row in selected]
        
        if not messagebox.askyesno("⚠️ Toplu Silme", 
                                   f"{adet} adet birleştirme kaydı silinecek!\n\n"
                                   "Devam etmek istiyor musunuz?"):
            return
        
        toplam_silinen = 0
        for kimlik in kimlik_listesi:
            sonuc = self.db.derin_sil(str(kimlik), 'kimlik')
            toplam_silinen += sonuc['toplam_silinen']
        
        messagebox.showinfo("Sonuç", f"✅ {toplam_silinen} kayıt silindi")
        self._birlestirme_listele()
    
    def _birlestirme_derin_sil(self):
        """Seçili birleştirme kaydının adisyonlarını da derin sil"""
        if not self._check_connection():
            return
        
        selected = self.birlestirme_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kaydı seçin!")
            return
        
        # Seçili satırdan bilgileri al
        row = selected[0]
        kimlik = row[0]
        hedef_adisyon = row[3]  # Hedef Adisyon
        iptal_adisyon = row[5]  # İptal Adisyon
        
        if not messagebox.askyesno("☠️ DERİN SİL", 
                                   f"Birleştirme kaydı ve ilişkili adisyonlar silinecek!\n\n"
                                   f"Kimlik: {kimlik}\n"
                                   f"Hedef Adisyon: {hedef_adisyon}\n"
                                   f"İptal Adisyon: {iptal_adisyon}\n\n"
                                   "⚠️ Bu işlem GERİ ALINAMAZ!"):
            return
        
        toplam = 0
        # Birleştirme kaydını sil
        sonuc = self.db.derin_sil(str(kimlik), 'kimlik')
        toplam += sonuc['toplam_silinen']
        
        # Hedef adisyonu sil
        if hedef_adisyon:
            sonuc = self.db.derin_sil(str(hedef_adisyon), 'adisyonno')
            toplam += sonuc['toplam_silinen']
        
        # İptal adisyonu sil
        if iptal_adisyon:
            sonuc = self.db.derin_sil(str(iptal_adisyon), 'adisyonno')
            toplam += sonuc['toplam_silinen']
        
        messagebox.showinfo("Sonuç", f"✅ Toplam {toplam} kayıt silindi")
        self._birlestirme_listele()
    
    def _birlestirme_toplu_derin_sil(self):
        """Seçili tüm birleştirme kayıtlarını ve adisyonlarını derin sil"""
        if not self._check_connection():
            return
        
        selected = self.birlestirme_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kayıtları seçin!\n\n"
                                   "💡 İpucu: Ctrl+Tık ile birden fazla seçebilirsiniz.")
            return
        
        adet = len(selected)
        
        # İlk onay
        if not messagebox.askyesno("☠️ TOPLU DERİN SİLME", 
                                   f"⚠️ {adet} birleştirme kaydı ve TÜM İLİŞKİLİ ADİSYONLAR silinecek!\n\n"
                                   "⚠️ Bu işlem GERİ ALINAMAZ!\n\n"
                                   "Devam etmek istiyor musunuz?"):
            return
        
        # İkinci onay
        if not messagebox.askyesno("☠️ SON ONAY", 
                                   f"{adet} birleştirme ve adisyonları KESİNLİKLE silinecek!\n\n"
                                   "EMİN MİSİNİZ?"):
            return
        
        toplam = 0
        for row in selected:
            kimlik = row[0]
            hedef_adisyon = row[3]
            iptal_adisyon = row[5]
            
            # Birleştirme kaydını sil
            sonuc = self.db.derin_sil(str(kimlik), 'kimlik')
            toplam += sonuc['toplam_silinen']
            
            # Hedef adisyonu sil
            if hedef_adisyon:
                sonuc = self.db.derin_sil(str(hedef_adisyon), 'adisyonno')
                toplam += sonuc['toplam_silinen']
            
            # İptal adisyonu sil
            if iptal_adisyon:
                sonuc = self.db.derin_sil(str(iptal_adisyon), 'adisyonno')
                toplam += sonuc['toplam_silinen']
        
        messagebox.showinfo("Sonuç", f"✅ {adet} birleştirme kaydı\n🗑️ Toplam {toplam} kayıt silindi")
        self._birlestirme_listele()
    
    # ==================== FİYAT =arih aralığına göre"""
        if not self._check_connection():
            return
        
        try:
            start = self.adisyon_start_var.get()
            end = self.adisyon_end_var.get()
            masa = self.adisyon_masa_var.get() or None
            
            df = self.db.adisyonlari_listele(start, end, masa)
            
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['adisyonno'],
                    str(row['Tarih'])[:10],
                    row['masa'],
                    row['urun_sayisi'],
                    f"{row['toplam']:.2f}",
                    "Aktif" if row.get('silinme', 0) == 0 else "İptal"
                ))
            
            self.adisyon_table.load_data(data)
            self.status_label.configure(text=f"{len(df)} adisyon listelendi ({start} - {end})")
            
        except Exception as e:
            messagebox.showerror("Hata", str(e))
    
    def _fiyat_guncelle(self):
        """Fiyat güncelle"""
        if not self._check_connection():
            return
        
        selected = self.urun_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen ürün seçin!")
            return
        
        try:
            yeni_fiyat = float(self.yeni_fiyat_var.get().replace(',', '.'))
        except:
            messagebox.showerror("Hata", "Geçerli bir fiyat girin!")
            return
        
        urun_adi = selected[0][0]
        if messagebox.askyesno("Onay", f"{urun_adi}\nYeni fiyat: {yeni_fiyat:.2f}₺"):
            if self.db.urun_fiyat_guncelle(urun_adi, yeni_fiyat):
                messagebox.showinfo("Başarılı", "✅ Fiyat güncellendi!")
                self._load_urunler()
    
    def _urun_sil(self):
        """Seçili ürünü sil"""
        if not self._check_connection():
            return
        
        selected = self.urun_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz ürünü seçin!")
            return
        
        urun_adi = selected[0][0]
        if messagebox.askyesno("⚠️ Ürün Silme", 
                              f"'{urun_adi}' ürünü silinecek!\n\n"
                              "Bu işlem GERİ ALINAMAZ!\n\n"
                              "Devam etmek istiyor musunuz?"):
            if self.db.urun_sil(urun_adi):
                messagebox.showinfo("Başarılı", f"✅ '{urun_adi}' silindi!")
                self._urunleri_listele()
            else:
                messagebox.showerror("Hata", "Ürün silinemedi!")
    
    def _urun_toplu_sil(self):
        """Filtrelenmiş tüm ürünleri sil"""
        if not self._check_connection():
            return
        
        # Filtrelenmiş veriyi al
        filtered = self.urun_table.get_filtered_data()
        if not filtered:
            messagebox.showwarning("Uyarı", "Silinecek ürün bulunamadı!")
            return
        
        urun_sayisi = len(filtered)
        
        # Çift onay iste
        if not messagebox.askyesno("⚠️ TOPLU SİLME", 
                                   f"{urun_sayisi} ürün silinecek!\n\n"
                                   "⚠️ DİKKAT: Bu işlem GERİ ALINAMAZ!\n\n"
                                   "Devam etmek istiyor musunuz?"):
            return
        
        # İkinci onay
        if not messagebox.askyesno("☠️ SON ONAY", 
                                   f"⚠️ {urun_sayisi} ürün KESİNLİKLE silinecek!\n\n"
                                   "EMIN MİSİNİZ?"):
            return
        
        # Ürün adlarını topla
        urun_adlari = [row[0] for row in filtered]
        
        # Toplu silme
        sonuc = self.db.urun_toplu_sil(urun_adlari)
        
        messagebox.showinfo("Toplu Silme Sonucu", 
                           f"✅ Başarılı: {sonuc['basarili']}\n"
                           f"❌ Başarısız: {sonuc['basarisiz']}")
        
        self._urunleri_listele()

    # ==================== ADİSYON ====================
    
    def _adisyon_listele(self):
        """Adisyonları listele - Tarih aralığına göre"""
        if not self._check_connection():
            return
        
        try:
            self._update_status("Adisyon kayıtları yükleniyor...", "loading")
            start = self.adisyon_start_var.get()
            end = self.adisyon_end_var.get()
            masa = self.adisyon_masa_var.get() or None
            adisyon_no = self.adisyon_no_var.get() or None
            
            df = self.db.adisyonlari_listele(start, end, masa, adisyon_no)
            
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['adisyonno'],
                    str(row['Tarih'])[:10],
                    row['masa'],
                    row['urun_sayisi'],
                    f"{row['toplam']:.2f}",
                    "Aktif" if row.get('silinme', 0) == 0 else "İptal"
                ))
            
            self.adisyon_table.load_data(data)
            self._update_selection_count(self.adisyon_table)
            self._update_status(f"{len(df)} adisyon listelendi ({start} - {end})", "success")
            
        except Exception as e:
            self._update_status("Hata oluştu!", "error")
            messagebox.showerror("Hata", str(e))
    
    def _adisyon_sil(self):
        """Tek adisyon sil"""
        if not self._check_connection():
            return
        
        selected = self.adisyon_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen adisyon seçin!")
            return
        
        adisyonno = selected[0][0]
        if messagebox.askyesno("Onay", f"Adisyon {adisyonno} silinecek?"):
            if self.db.adisyon_sil(adisyonno, "ADMIN"):
                messagebox.showinfo("Başarılı", "✅ Adisyon silindi!")
                self._adisyon_listele()
    
    def _adisyon_toplu_sil(self):
        """Seçili tüm adisyonları sil"""
        if not self._check_connection():
            return
        
        selected = self.adisyon_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz adisyonları seçin!\n\n"
                                   "💡 İpucu: Ctrl+Tık ile birden fazla seçebilirsiniz.")
            return
        
        adet = len(selected)
        adisyon_listesi = [row[0] for row in selected]
        
        # Onay iste
        if not messagebox.askyesno("⚠️ Toplu Silme", 
                                   f"{adet} adet adisyon silinecek!\n\n"
                                   f"Adisyonlar: {', '.join(str(a) for a in adisyon_listesi[:5])}"
                                   f"{'...' if adet > 5 else ''}\n\n"
                                   "Devam etmek istiyor musunuz?"):
            return
        
        # Silme işlemi
        basarili = 0
        basarisiz = 0
        
        for adisyonno in adisyon_listesi:
            try:
                if self.db.adisyon_sil(adisyonno, "ADMIN"):
                    basarili += 1
                else:
                    basarisiz += 1
            except:
                basarisiz += 1
        
        messagebox.showinfo("Toplu Silme Sonucu", 
                           f"✅ Başarılı: {basarili}\n"
                           f"❌ Başarısız: {basarisiz}")
        
        self._adisyon_listele()

    def _adisyon_derin_sil(self):
        """Tek adisyonu derin sil"""
        if not self._check_connection():
            return
        
        selected = self.adisyon_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen adisyon seçin!")
            return
        
        adisyonno = selected[0][0]
        if messagebox.askyesno("☠️ DERİN SİL", f"Adisyon {adisyonno} TÜM DB'lerden silinecek!"):
            sonuc = self.db.derin_sil(adisyonno, 'adisyonno')
            messagebox.showinfo("Sonuç", f"✅ {sonuc['toplam_silinen']} kayıt silindi")
            self._adisyon_listele()
    
    def _adisyon_toplu_derin_sil(self):
        """Seçili tüm adisyonları derin sil"""
        if not self._check_connection():
            return
        
        selected = self.adisyon_table.get_selected()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz adisyonları seçin!\n\n"
                                   "💡 İpucu: Ctrl+Tık ile birden fazla seçebilirsiniz.")
            return
        
        adet = len(selected)
        adisyon_listesi = [row[0] for row in selected]
        
        # İlk onay
        if not messagebox.askyesno("☠️ TOPLU DERİN SİLME", 
                                   f"⚠️ {adet} adet adisyon TÜM VERITABANLARINDAN silinecek!\n\n"
                                   f"Adisyonlar: {', '.join(str(a) for a in adisyon_listesi[:5])}"
                                   f"{'...' if adet > 5 else ''}\n\n"
                                   "⚠️ Bu işlem GERİ ALINAMAZ!\n\n"
                                   "Devam etmek istiyor musunuz?"):
            return
        
        # İkinci onay (ekstra güvenlik)
        if not messagebox.askyesno("☠️ SON ONAY", 
                                   f"⚠️ {adet} adisyon KESİNLİKLE ve TAMAMEN silinecek!\n\n"
                                   "EMİN MİSİNİZ?"):
            return
        
        # Derin silme işlemi
        toplam_silinen = 0
        basarili = 0
        basarisiz = 0
        hatalar = []
        
        for adisyonno in adisyon_listesi:
            try:
                sonuc = self.db.derin_sil(adisyonno, 'adisyonno')
                if sonuc['basarili']:
                    basarili += 1
                    toplam_silinen += sonuc['toplam_silinen']
                else:
                    basarisiz += 1
                    hatalar.extend(sonuc['hatalar'])
            except Exception as e:
                basarisiz += 1
                hatalar.append(str(e))
        
        # Sonuç mesajı
        mesaj = f"✅ Başarılı: {basarili} adisyon\n"
        mesaj += f"🗑️ Toplam Silinen Kayıt: {toplam_silinen}\n"
        if basarisiz > 0:
            mesaj += f"\n❌ Başarısız: {basarisiz}\n"
            if hatalar[:3]:
                mesaj += f"Hatalar: {', '.join(hatalar[:3])}..."
        
        messagebox.showinfo("Toplu Derin Silme Sonucu", mesaj)
        self._adisyon_listele()

    # ==================== EXPORT ====================
    
    def _export_excel(self, table: ExcelStyleTable):
        """Excel'e aktar"""
        data = table.get_all_data()
        if not data:
            messagebox.showwarning("Uyarı", "Aktarılacak veri yok!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Excel Dosyası Kaydet",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if filename:
            try:
                columns = [c[1] for c in table.columns]
                df = pd.DataFrame(data, columns=columns)
                df.to_excel(filename, index=False)
                messagebox.showinfo("Başarılı", f"✅ Dosya kaydedildi:\n{filename}")
            except Exception as e:
                messagebox.showerror("Hata", str(e))


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     🍽️  KERZZ BOSS YÖNETİM PROGRAMI PRO v3.0                  ║
║         Modern CustomTkinter Arayüzü                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ✨ Özellikler:                                               ║
║     • Modern karanlık/aydınlık tema                          ║
║     • Yuvarlak köşeli modern butonlar                        ║
║     • Inline tarih seçici                                    ║
║     • Gelişmiş filtreleme                                    ║
║     • Sağ tık menüsü                                         ║
║     • Excel aktarım                                          ║
║                                                              ║
║  ⌨️  Kısayollar:                                              ║
║     🌙 Tema değiştir butonu sağ üstte                        ║
║     ◀ Sidebar gizle/göster                                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app = KerzzGUIModern()
    app.mainloop()


if __name__ == "__main__":
    main()

import os
import shutil
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from core.backup import (
    CATEGORIES, get_default_backup_root, scan_category,
    perform_backup, list_backups, delete_backup
)

#these are temporary until i can get real icons
STATUS_ICONS = {
    "idle": "",
    "running": "Wait...",
    "done": "Done!",
    "empty": "None.",
    "failed": "Failed!",
}

STATUS_TEXT = {
    "done": "Backed up",
    "empty": "Nothing found",
    "failed": "Failed",
}


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class BackupFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.destination_root = get_default_backup_root()
        self.selected_categories = {c["key"] for c in CATEGORIES}
        self.category_cards = {}
        self.loaded_serial = None
        self.backup_running = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_view_switch()
        self._build_new_backup_view()
        self._build_history_view()

        self._show_view("new")

    def _build_view_switch(self):
        self.view_switch = ctk.CTkFrame(self, fg_color="transparent")
        self.view_switch.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

        self.new_backup_tab_btn = ctk.CTkButton(
            self.view_switch, text="New Backup", width=130,
            border_width=1, border_color=("gray70", "gray40"),
            command=lambda: self._show_view("new")
        )
        self.new_backup_tab_btn.pack(side="left", padx=(0, 10))

        self.history_tab_btn = ctk.CTkButton(
            self.view_switch, text="History", width=130,
            border_width=1, border_color=("gray70", "gray40"),
            fg_color="transparent",
            command=lambda: self._show_view("history")
        )
        self.history_tab_btn.pack(side="left")

    def _show_view(self, view):
        if view == "new":
            self.new_backup_tab_btn.configure(fg_color=("gray75", "gray25"))
            self.history_tab_btn.configure(fg_color="transparent")
            self.history_view.grid_remove()
            self.new_backup_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
        else:
            self.history_tab_btn.configure(fg_color=("gray75", "gray25"))
            self.new_backup_tab_btn.configure(fg_color="transparent")
            self.new_backup_view.grid_remove()
            self.history_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
            self._load_history()

    def _build_new_backup_view(self):
        self.new_backup_view = ctk.CTkFrame(self, fg_color="transparent")
        self.new_backup_view.grid_columnconfigure(0, weight=1)
        self.new_backup_view.grid_columnconfigure(1, weight=1)

        for i, category in enumerate(CATEGORIES):
            self._build_category_card(category, row=i // 2, column=i % 2)

        self.destination_row = ctk.CTkFrame(self.new_backup_view, fg_color="gray17")
        self.destination_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 10))

        self.destination_label = ctk.CTkLabel(
            self.destination_row, text=f"Save to: {self.destination_root}",
            anchor="w", font=ctk.CTkFont(size=12)
        )
        self.destination_label.pack(side="left", padx=15, pady=12, fill="x", expand=True)

        self.change_destination_button = ctk.CTkButton(
            self.destination_row, text="Change", width=90,
            border_width=1, border_color=("gray70", "gray40"),
            command=self._change_destination
        )
        self.change_destination_button.pack(side="right", padx=15, pady=12)

        self.space_label = ctk.CTkLabel(
            self.new_backup_view, text="", text_color="gray60", font=ctk.CTkFont(size=11)
        )
        self.space_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 15))

        self.backup_button = ctk.CTkButton(
            self.new_backup_view, text="Back Up Now", height=40,
            command=self._start_backup
        )
        self.backup_button.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.summary_label = ctk.CTkLabel(
            self.new_backup_view, text="", justify="left", anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.summary_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(15, 0))

        self.open_folder_button = ctk.CTkButton(
            self.new_backup_view, text="Open Backup Folder", width=180,
            border_width=1, border_color=("gray70", "gray40"),
            command=self._open_last_backup_folder
        )
        self.last_backup_folder = None

    def _build_category_card(self, category, row, column):
        card = ctk.CTkFrame(
            self.new_backup_view, border_width=2,
            border_color=("gray75", "gray30"), fg_color="gray17"
        )
        card.grid(row=row, column=column, sticky="ew", padx=(0, 10) if column == 0 else (10, 0), pady=(0, 10))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 4))

        icon_label = ctk.CTkLabel(header, text=category["icon"], font=ctk.CTkFont(size=18))
        icon_label.pack(side="left", padx=(0, 8))

        name_label = ctk.CTkLabel(header, text=category["label"], font=ctk.CTkFont(size=14, weight="bold"))
        name_label.pack(side="left")

        status_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=14))
        status_label.pack(side="right")

        stats_label = ctk.CTkLabel(
            card, text="Scanning...", text_color="gray60",
            font=ctk.CTkFont(size=12), anchor="w"
        )
        stats_label.pack(fill="x", padx=15, pady=(0, 12))

        for widget in (card, header, icon_label, name_label, stats_label):
            widget.bind("<Button-1>", lambda e, k=category["key"]: self._toggle_category(k))

        self.category_cards[category["key"]] = {
            "card": card, "stats_label": stats_label, "status_label": status_label
        }
        self._set_card_selected(category["key"], True)

    def _toggle_category(self, key):
        if self.backup_running:
            return
        if key in self.selected_categories:
            self.selected_categories.remove(key)
            self._set_card_selected(key, False)
        else:
            self.selected_categories.add(key)
            self._set_card_selected(key, True)

    def _set_card_selected(self, key, selected):
        card = self.category_cards[key]["card"]
        if selected:
            card.configure(border_color=("#1f6aa5", "#3b8ed0"))
        else:
            card.configure(border_color=("gray75", "gray30"))

    def _change_destination(self):
        chosen = filedialog.askdirectory(initialdir=self.destination_root)
        if chosen:
            self.destination_root = chosen
            self.destination_label.configure(text=f"Save to: {self.destination_root}")
            self._update_space_label()

    def _update_space_label(self):
        try:
            usage = shutil.disk_usage(os.path.splitdrive(self.destination_root)[0] + os.sep)
            self.space_label.configure(text=f"{format_size(usage.free)} free on this drive")
        except Exception:
            self.space_label.configure(text="")

    def refresh(self):
        if not self.app.connected_serial:
            self.loaded_serial = None
            for key in self.category_cards:
                self.category_cards[key]["stats_label"].configure(text="Connect a device to scan")
            return

        self._update_space_label()

        if self.app.connected_serial != self.loaded_serial:
            self.loaded_serial = self.app.connected_serial
            self._scan_all_categories()

    def _scan_all_categories(self):
        serial = self.app.connected_serial
        for category in CATEGORIES:
            self.category_cards[category["key"]]["stats_label"].configure(text="Scanning...")
            threading.Thread(target=self._scan_one, args=(serial, category), daemon=True).start()

    def _scan_one(self, serial, category):
        stats = scan_category(serial, category)
        self.after(0, self._on_scan_done, serial, category["key"], stats)

    def _on_scan_done(self, serial, key, stats):
        if serial != self.app.connected_serial:
            return
        size_text = format_size(stats["size_kb"] * 1024)
        self.category_cards[key]["stats_label"].configure(
            text=f"{stats['files']} files, {size_text}"
        )

    def _start_backup(self):
        if self.backup_running:
            return
        if not self.app.connected_serial:
            return
        if not self.selected_categories:
            messagebox.showinfo("Android Toolbox", "Select at least one category to back up.")
            return

        self.backup_running = True
        self.backup_button.configure(text="Backing Up...", state="disabled")
        self.summary_label.configure(text="")
        self.open_folder_button.grid_remove()

        for key in self.selected_categories:
            self.category_cards[key]["status_label"].configure(text="")

        serial = self.app.connected_serial
        keys = list(self.selected_categories)
        destination = self.destination_root

        threading.Thread(
            target=self._run_backup_thread, args=(serial, keys, destination), daemon=True
        ).start()

    def _run_backup_thread(self, serial, keys, destination):
        def progress(key, status):
            self.after(0, self._on_category_progress, key, status)

        backup_folder, results = perform_backup(serial, keys, destination, progress_callback=progress)
        self.after(0, self._on_backup_finished, backup_folder, results)

    def _on_category_progress(self, key, status):
        if key in self.category_cards:
            self.category_cards[key]["status_label"].configure(text=STATUS_ICONS.get(status, ""))

    def _on_backup_finished(self, backup_folder, results):
        self.backup_running = False
        self.backup_button.configure(text="Back Up Now", state="normal")
        self.last_backup_folder = backup_folder

        lines = []
        for key, status in results.items():
            label = next(c["label"] for c in CATEGORIES if c["key"] == key)
            lines.append(f"{STATUS_ICONS.get(status, '')} {label} — {STATUS_TEXT.get(status, status)}")
        self.summary_label.configure(text="\n".join(lines))
        self.open_folder_button.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _open_last_backup_folder(self):
        if self.last_backup_folder and os.path.isdir(self.last_backup_folder):
            os.startfile(self.last_backup_folder)

    def _build_history_view(self):
        self.history_view = ctk.CTkFrame(self, fg_color="transparent")
        self.history_view.grid_columnconfigure(0, weight=1)
        self.history_view.grid_rowconfigure(0, weight=1)

        self.history_scroll = ctk.CTkScrollableFrame(self.history_view, fg_color="gray17")
        self.history_scroll.grid(row=0, column=0, sticky="nsew")

        self.history_status_label = ctk.CTkLabel(self.history_scroll, text="Loading...", text_color="gray60")
        self.history_status_label.pack(pady=30)

    def _load_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
        loading_label = ctk.CTkLabel(self.history_scroll, text="Loading...", text_color="gray60")
        loading_label.pack(pady=30)
        threading.Thread(target=self._fetch_history, args=(self.destination_root,), daemon=True).start()

    def _fetch_history(self, destination_root):
        backups = list_backups(destination_root)
        self.after(0, self._render_history, backups)

    def _render_history(self, backups):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not backups:
            empty_label = ctk.CTkLabel(self.history_scroll, text="No backups yet", text_color="gray60")
            empty_label.pack(pady=30)
            return

        for backup in backups:
            self._create_history_row(backup)

    def _create_history_row(self, backup):
        row = ctk.CTkFrame(self.history_scroll, fg_color="transparent", border_width=1, border_color=("gray70", "gray40"))
        row.pack(fill="x", pady=4, padx=4)

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)

        name_label = ctk.CTkLabel(info_frame, text=backup["name"], anchor="w", font=ctk.CTkFont(weight="bold"))
        name_label.pack(anchor="w")

        included = [k for k, v in backup["categories"].items() if v == "done"]
        categories_text = ", ".join(included) if included else "No files backed up"
        detail_label = ctk.CTkLabel(
            info_frame, text=f"{categories_text} — {format_size(backup['size_bytes'])}",
            anchor="w", text_color="gray60", font=ctk.CTkFont(size=12)
        )
        detail_label.pack(anchor="w")

        button_frame = ctk.CTkFrame(row, fg_color="transparent")
        button_frame.pack(side="right", padx=15, pady=10)

        open_button = ctk.CTkButton(
            button_frame, text="Open", width=70,
            border_width=1, border_color=("gray70", "gray40"),
            command=lambda p=backup["path"]: os.startfile(p)
        )
        open_button.pack(side="left", padx=(0, 8))

        delete_button = ctk.CTkButton(
            button_frame, text="Delete", width=70, fg_color="#c0392b", hover_color="#a5301f",
            command=lambda b=backup: self._confirm_delete(b)
        )
        delete_button.pack(side="left")

    def _confirm_delete(self, backup):
        confirmed = messagebox.askyesno(
            "Delete Backup",
            f"Permanently delete the backup from {backup['name']}? This cannot be undone."
        )
        if confirmed:
            delete_backup(backup["path"])
            self._load_history()

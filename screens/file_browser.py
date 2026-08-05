import threading
import customtkinter as ctk
from core.adb import list_directory

ROOT_PATH = "/sdcard"

SHORTCUTS = [
    ("Internal Storage", "/sdcard"),
    ("DCIM", "/sdcard/DCIM"),
    ("Downloads", "/sdcard/Download"),
    ("Pictures", "/sdcard/Pictures"),
    ("Movies", "/sdcard/Movies"),
    ("Music", "/sdcard/Music"),
]

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "webm"}
AUDIO_EXTS = {"mp3", "wav", "ogg", "m4a", "flac"}


def get_icon(entry):
    if entry["is_dir"]:
        return "📁"
    ext = entry["name"].rsplit(".", 1)[-1].lower() if "." in entry["name"] else ""
    if ext in IMAGE_EXTS:
        return "🖼️"
    if ext in VIDEO_EXTS:
        return "🎞️"
    if ext in AUDIO_EXTS:
        return "🎵"
    if ext == "apk":
        return "📦"
    return "📄"


def format_size(size_bytes, is_dir):
    if is_dir:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class FileBrowserFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_path = ROOT_PATH
        self.history = [ROOT_PATH]
        self.history_index = 0
        self.current_entries = []
        self.loaded_serial = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_shortcuts_panel()
        self._build_main_panel()

    def _build_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(15, 5))

        self.back_button = ctk.CTkButton(self.top_bar, text="←", width=35, command=self._go_back)
        self.back_button.pack(side="left", padx=(0, 5))

        self.forward_button = ctk.CTkButton(self.top_bar, text="→", width=35, command=self._go_forward)
        self.forward_button.pack(side="left", padx=(0, 5))

        self.up_button = ctk.CTkButton(self.top_bar, text="↑", width=35, command=self._go_up)
        self.up_button.pack(side="left", padx=(0, 15))

        self.breadcrumb_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.breadcrumb_frame.pack(side="left", fill="x", expand=True)

        self.search_entry = ctk.CTkEntry(self.top_bar, placeholder_text="Search this folder", width=200)
        self.search_entry.pack(side="right", padx=(5, 0))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_entries())

        self.refresh_button = ctk.CTkButton(self.top_bar, text="⟳", width=35, command=self._load_current_path)
        self.refresh_button.pack(side="right", padx=(5, 5))

    def _build_shortcuts_panel(self):
        self.shortcuts_panel = ctk.CTkFrame(self, width=160)
        self.shortcuts_panel.grid(row=1, column=0, sticky="ns", padx=(15, 5), pady=(5, 15))
        self.shortcuts_panel.pack_propagate(False)

        for label, path in SHORTCUTS:
            btn = ctk.CTkButton(
                self.shortcuts_panel, text=label, anchor="w",
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda p=path: self._navigate_to(p)
            )
            btn.pack(fill="x", padx=10, pady=(10, 0))

    def _build_main_panel(self):
        self.main_panel = ctk.CTkFrame(self, fg_color="gray17")
        self.main_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 15), pady=(5, 15))
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.main_panel, text="", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=0, column=0)

        self.scroll_area = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")

    def refresh(self):
        if not self.app.connected_serial:
            self.loaded_serial = None
            self._show_status("Connect a device to browse files")
            return

        if self.app.connected_serial != self.loaded_serial:
            self.loaded_serial = self.app.connected_serial
            self.current_path = ROOT_PATH
            self.history = [ROOT_PATH]
            self.history_index = 0
            self._load_current_path()
        elif not self.current_entries:
            self._load_current_path()

    def _navigate_to(self, path, record_history=True):
        self.current_path = path
        if record_history:
            self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        self._load_current_path()

    def _go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self._load_current_path()

    def _go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self._load_current_path()

    def _go_up(self):
        if self.current_path == ROOT_PATH:
            return
        parent = self.current_path.rsplit("/", 1)[0]
        if not parent or len(parent) < len(ROOT_PATH):
            parent = ROOT_PATH
        self._navigate_to(parent)

    def _load_current_path(self):
        self._build_breadcrumb()
        self._update_nav_buttons()
        self._show_status("Loading...")
        serial = self.app.connected_serial
        if not serial:
            return
        threading.Thread(target=self._fetch_entries, args=(serial, self.current_path), daemon=True).start()

    def _fetch_entries(self, serial, path):
        entries = list_directory(serial, path)
        self.after(0, self._on_entries_loaded, path, entries)

    def _on_entries_loaded(self, path, entries):
        if path != self.current_path:
            return
        if entries is None:
            self._show_status("Could not read this folder")
            self.current_entries = []
            return
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        self.current_entries = entries
        self._render_entries()

    def _render_entries(self):
        query = self.search_entry.get().strip().lower()
        filtered = [e for e in self.current_entries if query in e["name"].lower()]

        self.status_label.grid_remove()
        self.scroll_area.grid(row=0, column=0, sticky="nsew")

        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        if not filtered:
            empty_text = "No matching files" if query else "This folder is empty"
            empty_label = ctk.CTkLabel(self.scroll_area, text=empty_text, text_color="gray60")
            empty_label.pack(pady=30)
            return

        for entry in filtered:
            self._create_row(entry)

    def _create_row(self, entry):
        row = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        row.pack(fill="x", pady=1)

        icon_label = ctk.CTkLabel(row, text=get_icon(entry), width=30)
        icon_label.pack(side="left", padx=(5, 5))

        name_label = ctk.CTkLabel(row, text=entry["name"], anchor="w")
        name_label.pack(side="left", fill="x", expand=True)

        date_label = ctk.CTkLabel(row, text=entry["modified"], text_color="gray60", width=130)
        date_label.pack(side="right", padx=(0, 10))

        size_label = ctk.CTkLabel(row, text=format_size(entry["size"], entry["is_dir"]), text_color="gray60", width=70)
        size_label.pack(side="right")

        for widget in (row, icon_label, name_label, date_label, size_label):
            widget.bind("<Double-Button-1>", lambda e, en=entry: self._on_row_double_click(en))
            widget.bind("<Button-1>", lambda e, w=row: self._select_row(w))

    def _select_row(self, row_widget):
        for widget in self.scroll_area.winfo_children():
            widget.configure(fg_color="transparent")
        row_widget.configure(fg_color=("gray75", "gray25"))

    def _on_row_double_click(self, entry):
        if entry["is_dir"]:
            new_path = f"{self.current_path.rstrip('/')}/{entry['name']}"
            self._navigate_to(new_path)
        else:
            self._show_temporary_message("Preview and download coming soon")

    def _show_temporary_message(self, text):
        popup = ctk.CTkLabel(
            self, text=text, fg_color="gray20", corner_radius=8,
            font=ctk.CTkFont(size=12)
        )
        popup.place(relx=0.5, rely=0.95, anchor="s")
        self.after(1800, popup.destroy)

    def _build_breadcrumb(self):
        for widget in self.breadcrumb_frame.winfo_children():
            widget.destroy()

        relative = self.current_path[len(ROOT_PATH):].strip("/")
        segments = [("Internal Storage", ROOT_PATH)]
        if relative:
            parts = relative.split("/")
            built = ROOT_PATH
            for part in parts:
                built = f"{built}/{part}"
                segments.append((part, built))

        for i, (label, path) in enumerate(segments):
            btn = ctk.CTkButton(
                self.breadcrumb_frame, text=label, fg_color="transparent",
                text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                width=1, command=lambda p=path: self._navigate_to(p)
            )
            btn.pack(side="left")
            if i < len(segments) - 1:
                sep = ctk.CTkLabel(self.breadcrumb_frame, text="/", text_color="gray50")
                sep.pack(side="left")

    def _update_nav_buttons(self):
        self.back_button.configure(state="normal" if self.history_index > 0 else "disabled")
        self.forward_button.configure(state="normal" if self.history_index < len(self.history) - 1 else "disabled")
        self.up_button.configure(state="normal" if self.current_path != ROOT_PATH else "disabled")

    def _show_status(self, text):
        self.scroll_area.grid_remove()
        self.status_label.configure(text=text)
        self.status_label.grid(row=0, column=0)

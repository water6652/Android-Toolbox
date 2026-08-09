import threading
import customtkinter as ctk
from PIL import Image
from core.gallery import SOURCES, list_media, get_thumbnail_path, pull_full_media

SOURCE_LABELS = {key: label for key, label, _paths in SOURCES}
SOURCE_KEYS_BY_LABEL = {label: key for key, label, _paths in SOURCES}

TILE_SIZE = 140
TILE_GAP = 10

class GalleryFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_source = "all"
        self.current_media = []
        self.filtered_media = []
        self.tile_widgets = []
        self.rendered_count = 0
        self.batch_size = 60
        self.generation = 0
        self.loaded_serial = None
        self.columns = 1
        self.preview_window = None
        self.preview_index = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_main_panel()

    def _build_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        self.search_entry = ctk.CTkEntry(
            self.top_bar, placeholder_text="Search filename",
            border_width=1, border_color=("gray70", "gray40")
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_grid())

        self.source_menu = ctk.CTkOptionMenu(
            self.top_bar, values=list(SOURCE_LABELS.values()),
            command=self._on_source_changed, width=170
        )
        self.source_menu.set(SOURCE_LABELS["all"])
        self.source_menu.pack(side="right")

    def _build_main_panel(self):
        self.main_panel = ctk.CTkFrame(self, fg_color="gray17")
        self.main_panel.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.main_panel, text="", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=0, column=0)

        self.scroll_area = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        self.scroll_area._parent_canvas.bind("<MouseWheel>", self._on_scroll, add="+")
        self.scroll_area.bind("<Configure>", self._on_container_resize)

    def _on_source_changed(self, label):
        self.current_source = SOURCE_KEYS_BY_LABEL.get(label, "all")
        self._load_media()

    def refresh(self):
        if not self.app.connected_serial:
            self.loaded_serial = None
            self._show_status("Connect a device to view media")
            return
        if self.app.connected_serial != self.loaded_serial:
            self.loaded_serial = self.app.connected_serial
            self._load_media()

    def _load_media(self):
        serial = self.app.connected_serial
        if not serial:
            return
        self.generation += 1
        generation = self.generation
        self._show_status("Loading media...")
        threading.Thread(
            target=self._fetch_media, args=(serial, self.current_source, generation), daemon=True
        ).start()

    def _fetch_media(self, serial, source_key, generation):
        media = list_media(serial, source_key)
        self.after(0, self._on_media_loaded, generation, media)

    def _on_media_loaded(self, generation, media):
        if generation != self.generation:
            return
        self.current_media = media
        self._render_grid()

    def _compute_columns(self):
        width = self.scroll_area.winfo_width()
        if width < 50:
            width = self.main_panel.winfo_width()
        tile_span = TILE_SIZE + TILE_GAP
        columns = max(1, width // tile_span)
        return columns

    def _render_grid(self):
        query = self.search_entry.get().strip().lower()
        self.filtered_media = [m for m in self.current_media if query in m["name"].lower()]
        self.rendered_count = 0
        self.tile_widgets = []

        self.status_label.grid_remove()
        self.scroll_area.grid(row=0, column=0, sticky="nsew")
        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        if not self.filtered_media:
            empty_text = "No matching files" if query else "No photos or videos found here"
            ctk.CTkLabel(self.scroll_area, text=empty_text, text_color="gray60").grid(row=0, column=0, pady=30)
            return

        self.columns = self._compute_columns()
        self._render_next_batch()

    def _render_next_batch(self):
        serial = self.app.connected_serial
        generation = self.generation
        start = self.rendered_count
        remaining = self.filtered_media[start:start + self.batch_size]

        for offset, entry in enumerate(remaining):
            index = start + offset
            self._create_tile(entry, index, serial, generation)

        self.rendered_count += len(remaining)

    def _on_scroll(self, _event=None):
        self.after(30, self._check_scroll_position)

    def _check_scroll_position(self):
        if self.rendered_count >= len(self.filtered_media):
            return
        try:
            _top, bottom = self.scroll_area._parent_canvas.yview()
        except Exception:
            return
        if bottom > 0.9:
            self._render_next_batch()

    def _on_container_resize(self, _event=None):
        if not self.filtered_media:
            return
        new_columns = self._compute_columns()
        if new_columns == self.columns:
            return
        self.columns = new_columns
        for index, tile in enumerate(self.tile_widgets):
            row, col = divmod(index, self.columns)
            tile.grid_configure(row=row, column=col)

    def _create_tile(self, entry, index, serial, generation):
        row, col = divmod(index, self.columns)
        tile = ctk.CTkFrame(
            self.scroll_area, width=TILE_SIZE, height=TILE_SIZE,
            border_width=1, border_color=("gray70", "gray40")
        )
        tile.grid(row=row, column=col, padx=TILE_GAP // 2, pady=TILE_GAP // 2)
        tile.grid_propagate(False)
        self.tile_widgets.append(tile)

        icon_text = "🎞️" if entry["is_video"] else "🖼️"
        icon_label = ctk.CTkLabel(tile, text=icon_text, font=ctk.CTkFont(size=30))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        tile.bind("<Button-1>", lambda e, en=entry, i=index: self._on_tile_click(en, i))
        icon_label.bind("<Button-1>", lambda e, en=entry, i=index: self._on_tile_click(en, i))

        if not entry["is_video"]:
            threading.Thread(
                target=self._resolve_thumbnail, args=(serial, entry, tile, icon_label, generation), daemon=True
            ).start()

    def _resolve_thumbnail(self, serial, entry, tile, icon_label, generation):
        path = get_thumbnail_path(serial, entry)
        self.after(0, self._on_thumbnail_ready, generation, tile, icon_label, path)

    def _on_thumbnail_ready(self, generation, tile, icon_label, path):
        if generation != self.generation or not tile.winfo_exists():
            return
        if not path:
            return
        try:
            img = Image.open(path)
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(TILE_SIZE - 8, TILE_SIZE - 8))
            icon_label.configure(image=ctk_image, text="")
        except Exception:
            pass

    def _on_tile_click(self, entry, index):
        if entry["is_video"]:
            self._show_temporary_message("Video preview coming soon")
            return
        self._open_preview(index)

    def _show_temporary_message(self, text):
        popup = ctk.CTkLabel(self, text=text, fg_color="gray20", corner_radius=8, font=ctk.CTkFont(size=12))
        popup.place(relx=0.5, rely=0.95, anchor="s")
        self.after(1800, popup.destroy)

    def _show_status(self, text):
        self.scroll_area.grid_remove()
        self.status_label.configure(text=text)
        self.status_label.grid(row=0, column=0)

    def _open_preview(self, index):
        self.preview_index = index

        if self.preview_window is None or not self.preview_window.winfo_exists():
            self.preview_window = ctk.CTkToplevel(self)
            self.preview_window.title("Preview")
            self.preview_window.geometry("900x700")
            self.preview_window.configure(fg_color="gray10")

            self.preview_image_label = ctk.CTkLabel(self.preview_window, text="Loading...")
            self.preview_image_label.pack(expand=True, fill="both", padx=10, pady=(10, 5))

            nav_row = ctk.CTkFrame(self.preview_window, fg_color="transparent")
            nav_row.pack(pady=(0, 10))

            self.prev_button = ctk.CTkButton(nav_row, text="← Prev", width=100, command=self._preview_prev)
            self.prev_button.pack(side="left", padx=10)

            self.close_button = ctk.CTkButton(nav_row, text="Close", width=100, command=self._close_preview)
            self.close_button.pack(side="left", padx=10)

            self.next_button = ctk.CTkButton(nav_row, text="Next →", width=100, command=self._preview_next)
            self.next_button.pack(side="left", padx=10)

            self.preview_window.bind("<Escape>", lambda e: self._close_preview())
            self.preview_window.bind("<Left>", lambda e: self._preview_prev())
            self.preview_window.bind("<Right>", lambda e: self._preview_next())
            self.preview_window.protocol("WM_DELETE_WINDOW", self._close_preview)

        self.preview_window.focus_set()
        self._load_preview_image()

    def _preview_prev(self):
        if self.preview_index is None:
            return
        new_index = self.preview_index - 1
        while new_index >= 0 and self.filtered_media[new_index]["is_video"]:
            new_index -= 1
        if new_index >= 0:
            self.preview_index = new_index
            self._load_preview_image()

    def _preview_next(self):
        if self.preview_index is None:
            return
        new_index = self.preview_index + 1
        while new_index < len(self.filtered_media) and self.filtered_media[new_index]["is_video"]:
            new_index += 1
        if new_index < len(self.filtered_media):
            self.preview_index = new_index
            self._load_preview_image()

    def _load_preview_image(self):
        entry = self.filtered_media[self.preview_index]
        self.preview_image_label.configure(text=f"Loading {entry['name']}...", image=None)
        serial = self.app.connected_serial
        generation = self.generation
        index = self.preview_index
        threading.Thread(
            target=self._fetch_preview_image, args=(serial, entry, generation, index), daemon=True
        ).start()

    def _fetch_preview_image(self, serial, entry, generation, index):
        path = pull_full_media(serial, entry)
        self.after(0, self._on_preview_ready, generation, index, entry, path)

    def _on_preview_ready(self, generation, index, entry, path):
        if generation != self.generation or self.preview_window is None or not self.preview_window.winfo_exists():
            return
        if index != self.preview_index:
            return
        if not path:
            self.preview_image_label.configure(text="Could not load image")
            return
        try:
            img = Image.open(path)
            img.thumbnail((860, 600))
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.preview_image_label.configure(image=ctk_image, text="")
            self.preview_window.title(entry["name"])
        except Exception:
            self.preview_image_label.configure(text="Could not display this file")

    def _close_preview(self):
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_index = None

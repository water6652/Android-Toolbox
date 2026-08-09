import os
import io
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
from core.apps import (
    list_packages, resolve_app_info, disable_app, enable_app,
    uninstall_app, restore_app, save_apk, log_action, list_history, get_history_dir
)

FILTER_LABELS = {
    "all": "All",
    "user": "User Apps",
    "system": "System Apps",
    "disabled": "Disabled",
}

ACTION_LABELS = {
    "disable": "Disabled",
    "enable": "Enabled",
    "uninstall": "Uninstalled",
    "restore": "Restored",
    "save": "Saved APK",
}

ACTION_BADGE_COLOR = {
    "Disabled": "#e0a800",
    "Enabled": "#2ecc71",
    "Uninstalled": "#e74c3c",
    "Restored": "#2ecc71",
    "Saved APK": "#3b8ed0",
}


def bytes_to_ctkimage(icon_bytes, size=(28, 28)):
    if not icon_bytes:
        return None
    try:
        img = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


class AppManagerFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_view = "all"
        self.current_packages = []
        self.filtered_packages = []
        self.rendered_count = 0
        self.batch_size = 80
        self.selected = set()
        self.row_widgets = {}
        self.generation = 0
        self.loaded_serial = None
        self.action_running = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_view_switch()
        self._build_apps_view()
        self._build_history_view()

        self._show_view("apps")

    def _build_view_switch(self):
        self.view_switch = ctk.CTkFrame(self, fg_color="transparent")
        self.view_switch.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

        self.apps_tab_btn = ctk.CTkButton(
            self.view_switch, text="Apps", width=130,
            border_width=1, border_color=("gray70", "gray40"),
            command=lambda: self._show_view("apps")
        )
        self.apps_tab_btn.pack(side="left", padx=(0, 10))

        self.history_tab_btn = ctk.CTkButton(
            self.view_switch, text="History", width=130,
            border_width=1, border_color=("gray70", "gray40"),
            fg_color="transparent",
            command=lambda: self._show_view("history")
        )
        self.history_tab_btn.pack(side="left")

    def _show_view(self, view):
        if view == "apps":
            self.apps_tab_btn.configure(fg_color=("gray75", "gray25"))
            self.history_tab_btn.configure(fg_color="transparent")
            self.history_view.grid_remove()
            self.apps_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
        else:
            self.history_tab_btn.configure(fg_color=("gray75", "gray25"))
            self.apps_tab_btn.configure(fg_color="transparent")
            self.apps_view.grid_remove()
            self.history_view.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
            self._load_history()

    def _build_apps_view(self):
        self.apps_view = ctk.CTkFrame(self, fg_color="transparent")
        self.apps_view.grid_columnconfigure(0, weight=1)
        self.apps_view.grid_rowconfigure(2, weight=1)

        top_row = ctk.CTkFrame(self.apps_view, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            top_row, placeholder_text="Search apps",
            border_width=1, border_color=("gray70", "gray40")
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_list())

        self.filter_menu = ctk.CTkOptionMenu(
            top_row, values=list(FILTER_LABELS.values()),
            command=self._on_filter_changed, width=150
        )
        self.filter_menu.set(FILTER_LABELS["all"])
        self.filter_menu.pack(side="right")

        self.bulk_bar = ctk.CTkFrame(self.apps_view, fg_color="gray17")
        self.bulk_label = ctk.CTkLabel(self.bulk_bar, text="", font=ctk.CTkFont(size=12))
        self.bulk_label.pack(side="left", padx=15, pady=8)

        self.bulk_buttons_frame = ctk.CTkFrame(self.bulk_bar, fg_color="transparent")
        self.bulk_buttons_frame.pack(side="right", padx=10, pady=6)

        self.main_panel = ctk.CTkFrame(self.apps_view, fg_color="gray17")
        self.main_panel.grid(row=2, column=0, sticky="nsew")
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.main_panel, text="", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=0, column=0)

        self.scroll_area = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        self.scroll_area._parent_canvas.bind("<MouseWheel>", self._on_scroll, add="+")

    def _on_filter_changed(self, label):
        for key, val in FILTER_LABELS.items():
            if val == label:
                self.current_view = key
                break
        self._load_packages()

    def refresh(self):
        if not self.app.connected_serial:
            self.loaded_serial = None
            self._show_status("Connect a device to manage apps")
            return
        if self.app.connected_serial != self.loaded_serial:
            self.loaded_serial = self.app.connected_serial
            self.selected.clear()
            self._update_bulk_bar()
            self._load_packages()

    def _load_packages(self):
        serial = self.app.connected_serial
        if not serial:
            return
        self.generation += 1
        generation = self.generation
        self.selected.clear()
        self._update_bulk_bar()
        self._show_status("Loading apps...")
        threading.Thread(
            target=self._fetch_packages, args=(serial, self.current_view, generation), daemon=True
        ).start()

    def _fetch_packages(self, serial, view, generation):
        packages = list_packages(serial, view)
        self.after(0, self._on_packages_loaded, generation, packages)

    def _on_packages_loaded(self, generation, packages):
        if generation != self.generation:
            return
        self.current_packages = packages
        self._render_list()

    def _render_list(self):
        query = self.search_entry.get().strip().lower()
        self.filtered_packages = [p for p in self.current_packages if query in p.lower()]
        self.rendered_count = 0
        self.row_widgets = {}

        self.status_label.grid_remove()
        self.scroll_area.grid(row=0, column=0, sticky="nsew")
        for widget in self.scroll_area.winfo_children():
            widget.destroy()

        if not self.filtered_packages:
            empty_text = "No matching apps" if query else "No apps in this view"
            ctk.CTkLabel(self.scroll_area, text=empty_text, text_color="gray60").pack(pady=30)
            return

        self._render_next_batch()

    def _render_next_batch(self):
        remaining = self.filtered_packages[self.rendered_count:self.rendered_count + self.batch_size]
        serial = self.app.connected_serial
        generation = self.generation
        for package in remaining:
            self._create_row(package, serial, generation)
        self.rendered_count += len(remaining)

    def _on_scroll(self, _event=None):
        self.after(30, self._check_scroll_position)

    def _check_scroll_position(self):
        if self.rendered_count >= len(self.filtered_packages):
            return
        try:
            _top, bottom = self.scroll_area._parent_canvas.yview()
        except Exception:
            return
        if bottom > 0.9:
            self._render_next_batch()

    def _create_row(self, package, serial, generation):
        row = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        row.pack(fill="x", pady=1)

        var = tk.BooleanVar(value=package in self.selected)
        checkbox = ctk.CTkCheckBox(
            row, text="", variable=var, width=20,
            command=lambda p=package, v=var: self._on_check_toggled(p, v)
        )
        checkbox.pack(side="left", padx=(5, 10))

        icon_label = ctk.CTkLabel(row, text="📱", width=32, font=ctk.CTkFont(size=16))
        icon_label.pack(side="left", padx=(0, 10))

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)

        name_label = ctk.CTkLabel(text_frame, text=package, anchor="w", font=ctk.CTkFont(size=13))
        name_label.pack(anchor="w")

        id_label = ctk.CTkLabel(text_frame, text=package, anchor="w", text_color="gray60", font=ctk.CTkFont(size=11))
        id_label.pack(anchor="w")

        status_label = ctk.CTkLabel(row, text="", font=ctk.CTkFont(size=11), width=90)
        status_label.pack(side="right", padx=(0, 10))

        self.row_widgets[package] = {
            "row": row, "icon_label": icon_label, "name_label": name_label, "status_label": status_label
        }

        threading.Thread(
            target=self._resolve_row, args=(serial, package, generation), daemon=True
        ).start()

    def _resolve_row(self, serial, package, generation):
        info = resolve_app_info(serial, package)
        self.after(0, self._on_row_resolved, generation, package, info)

    def _on_row_resolved(self, generation, package, info):
        if generation != self.generation:
            return
        widgets = self.row_widgets.get(package)
        if not widgets or not widgets["row"].winfo_exists():
            return
        widgets["name_label"].configure(text=info["label"])
        image = bytes_to_ctkimage(info["icon_bytes"])
        if image:
            widgets["icon_label"].configure(image=image, text="")

    def _on_check_toggled(self, package, var):
        if var.get():
            self.selected.add(package)
        else:
            self.selected.discard(package)
        self._update_bulk_bar()

    def _update_bulk_bar(self):
        count = len(self.selected)
        if count == 0:
            self.bulk_bar.grid_remove()
            return

        self.bulk_label.configure(text=f"{count} app{'s' if count != 1 else ''} selected")
        for widget in self.bulk_buttons_frame.winfo_children():
            widget.destroy()

        if self.current_view == "disabled":
            actions = [("Enable", "enable"), ("Restore", "restore"), ("Save APK", "save")]
        else:
            actions = [("Disable", "disable"), ("Uninstall", "uninstall"), ("Save APK", "save")]

        for label, action_key in actions:
            btn = ctk.CTkButton(
                self.bulk_buttons_frame, text=label, width=100,
                border_width=1, border_color=("gray70", "gray40"),
                command=lambda a=action_key: self._run_bulk_action(a)
            )
            btn.pack(side="left", padx=(0, 8))

        self.bulk_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

    def _run_bulk_action(self, action_key):
        if self.action_running:
            return
        packages = list(self.selected)
        if not packages:
            return

        if action_key in ("disable", "uninstall"):
            verb = "disable" if action_key == "disable" else "uninstall"
            confirmed = messagebox.askyesno(
                "Android Toolbox",
                f"{verb.capitalize()} {len(packages)} selected app(s)?"
            )
            if not confirmed:
                return

        destination = None
        if action_key == "save":
            destination = filedialog.askdirectory()
            if not destination:
                return

        self.action_running = True
        serial = self.app.connected_serial
        for package in packages:
            widgets = self.row_widgets.get(package)
            if widgets:
                widgets["status_label"].configure(text="⏳")

        threading.Thread(
            target=self._bulk_action_thread, args=(serial, action_key, packages, destination), daemon=True
        ).start()

    def _bulk_action_thread(self, serial, action_key, packages, destination):
        results = []
        for package in packages:
            success = self._perform_single_action(serial, action_key, package, destination)
            info = resolve_app_info(serial, package)
            results.append({
                "package": package, "label": info["label"],
                "status": "success" if success else "failed"
            })
            self.after(0, self._on_bulk_item_done, package, success)

        log_action(ACTION_LABELS.get(action_key, action_key), results)
        self.after(0, self._on_bulk_action_finished)

    def _perform_single_action(self, serial, action_key, package, destination):
        try:
            if action_key == "disable":
                return disable_app(serial, package)
            if action_key == "enable":
                return enable_app(serial, package)
            if action_key == "uninstall":
                return uninstall_app(serial, package)
            if action_key == "restore":
                return restore_app(serial, package)
            if action_key == "save":
                return save_apk(serial, package, destination)
        except Exception:
            return False
        return False

    def _on_bulk_item_done(self, package, success):
        widgets = self.row_widgets.get(package)
        if widgets and widgets["row"].winfo_exists():
            widgets["status_label"].configure(text="✅" if success else "❌")

    def _on_bulk_action_finished(self):
        self.action_running = False
        self.selected.clear()
        self._update_bulk_bar()
        self._load_packages()

    def _show_status(self, text):
        self.scroll_area.grid_remove()
        self.status_label.configure(text=text)
        self.status_label.grid(row=0, column=0)

    def _build_history_view(self):
        self.history_view = ctk.CTkFrame(self, fg_color="transparent")
        self.history_view.grid_columnconfigure(0, weight=1)
        self.history_view.grid_rowconfigure(0, weight=1)

        self.history_scroll = ctk.CTkScrollableFrame(self.history_view, fg_color="gray17")
        self.history_scroll.grid(row=0, column=0, sticky="nsew")

    def _load_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.history_scroll, text="Loading...", text_color="gray60").pack(pady=30)
        threading.Thread(target=self._fetch_history, daemon=True).start()

    def _fetch_history(self):
        entries = list_history()
        self.after(0, self._render_history, entries)

    def _render_history(self, entries):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not entries:
            ctk.CTkLabel(self.history_scroll, text="No app actions yet", text_color="gray60").pack(pady=30)
            return

        for entry in entries:
            self._create_history_entry(entry)

    def _create_history_entry(self, entry):
        container = ctk.CTkFrame(
            self.history_scroll, fg_color="transparent",
            border_width=1, border_color=("gray70", "gray40")
        )
        container.pack(fill="x", pady=4, padx=4)

        timestamp_display = entry["timestamp"].replace("_", " ").replace("-", "/", 2).replace("-", ":")
        count = len(entry.get("apps", []))

        header = ctk.CTkButton(
            container, fg_color="transparent", text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"), anchor="w",
            text=f"{timestamp_display}   —   {entry.get('action', '')}: {count} app{'s' if count != 1 else ''}",
            command=lambda c=container, e=entry: self._toggle_history_entry(c, e)
        )
        header.pack(fill="x")

        sub_list = ctk.CTkFrame(container, fg_color="transparent")
        container.sub_list = sub_list
        container.expanded = False

    def _toggle_history_entry(self, container, entry):
        if container.expanded:
            container.sub_list.pack_forget()
            container.expanded = False
            return

        for widget in container.sub_list.winfo_children():
            widget.destroy()

        for app_entry in entry.get("apps", []):
            row = ctk.CTkFrame(container.sub_list, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)

            ctk.CTkLabel(row, text="📱", width=24).pack(side="left")
            ctk.CTkLabel(row, text=app_entry.get("label", app_entry.get("package", "")), anchor="w").pack(
                side="left", fill="x", expand=True
            )

            status = app_entry.get("status", "")
            badge_text = "OK" if status == "success" else "Failed"
            badge_color = "#2ecc71" if status == "success" else "#e74c3c"
            ctk.CTkLabel(row, text=badge_text, text_color=badge_color, font=ctk.CTkFont(size=11)).pack(side="right")

        container.sub_list.pack(fill="x", pady=(0, 8))
        container.expanded = True
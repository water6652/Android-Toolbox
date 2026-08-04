import tkinter as tk
import customtkinter as ctk
from core import scrcpy
from core.adb import get_screen_resolution

ORIGINAL_COLOR = "#9a9a9a"
MIRRORED_COLOR = "#e03c3c"


class ScreenMirrorFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.process = None
        self.original_res = None
        self.selected_preset = "Balanced"
        self.advanced_visible = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)

        self.preset_row = ctk.CTkFrame(self, fg_color="transparent")
        self.preset_row.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))

        self.preset_buttons = {}
        for name in PRESET_ORDER:
            btn = ctk.CTkButton(
                self.preset_row, text=name, width=110,
                command=lambda n=name: self._select_preset(n)
            )
            btn.pack(side="left", padx=(0, 10))
            self.preset_buttons[name] = btn

        self.advanced_toggle = ctk.CTkButton(
            self.preset_row, text="Advanced Options", fg_color="transparent",
            border_width=1, width=140, command=self._toggle_advanced
        )
        self.advanced_toggle.pack(side="left", padx=(20, 0))

        self.advanced_frame = ctk.CTkFrame(self)
        self.max_size_entry = ctk.CTkEntry(self.advanced_frame, placeholder_text="Max size (e.g. 1080)")
        self.max_size_entry.pack(side="left", padx=10, pady=10)
        self.bit_rate_entry = ctk.CTkEntry(self.advanced_frame, placeholder_text="Bit rate (e.g. 8M)")
        self.bit_rate_entry.pack(side="left", padx=10, pady=10)
        self.apply_custom_button = ctk.CTkButton(
            self.advanced_frame, text="Apply", width=80, command=self._apply_custom
        )
        self.apply_custom_button.pack(side="left", padx=10, pady=10)

        self.canvas = tk.Canvas(self, bg="#242424", highlightthickness=0)
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.canvas.bind("<Configure>", lambda e: self._draw_diagram())

        self.info_panel = ctk.CTkFrame(self, fg_color="gray20")
        self.info_panel.grid(row=2, column=1, sticky="nsew", padx=(0, 20), pady=10)
        self.info_label = ctk.CTkLabel(
            self.info_panel, text=EXPLANATIONS[self.selected_preset],
            font=ctk.CTkFont(size=15), justify="left", wraplength=280
        )
        self.info_label.pack(padx=20, pady=20, anchor="nw")

        self.bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_row.grid(row=3, column=0, columnspan=2, sticky="e", padx=20, pady=(0, 20))

        self.start_button = ctk.CTkButton(
            self.bottom_row, text="Start", width=140,
            command=self._on_start_stop
        )
        self.start_button.pack(side="right")

        self._select_preset(self.selected_preset)

    def refresh(self):
        if self.app.connected_serial:
            self.original_res = get_screen_resolution(self.app.connected_serial)
        else:
            self.original_res = None
        self._draw_diagram()

    def _select_preset(self, name):
        self.selected_preset = name
        for btn_name, btn in self.preset_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color=["#1f6aa5", "#1f6aa5"])
        self.info_label.configure(text=EXPLANATIONS[name])
        self._draw_diagram()

    def _toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 10))
        else:
            self.advanced_frame.grid_forget()

    def _apply_custom(self):
        self._draw_diagram()

    def _get_target_max_size_and_bitrate(self):
        max_size_text = self.max_size_entry.get().strip()
        bit_rate_text = self.bit_rate_entry.get().strip()

        preset = scrcpy.PRESETS[self.selected_preset]
        max_size = preset["max_size"]
        bit_rate = preset["bit_rate"]

        if max_size_text.isdigit():
            max_size = int(max_size_text)
        if bit_rate_text:
            bit_rate = bit_rate_text

        return max_size, bit_rate

    def _compute_mirrored_res(self, max_size):
        if not self.original_res:
            return None
        width, height = self.original_res
        if not max_size or max_size <= 0:
            return width, height

        longest = max(width, height)
        if longest <= max_size:
            return width, height

        scale = max_size / longest
        return int(width * scale), int(height * scale)

    def _draw_diagram(self):
        self.canvas.delete("all")
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50 or canvas_h < 50:
            return

        if not self.original_res:
            self.canvas.create_text(
                canvas_w / 2, canvas_h / 2,
                text="Connect a device to preview resolution",
                fill="gray60", font=("Segoe UI", 13)
            )
            return

        max_size, _ = self._get_target_max_size_and_bitrate()
        mirrored_res = self._compute_mirrored_res(max_size)

        orig_w, orig_h = self.original_res
        mir_w, mir_h = mirrored_res

        phone_area_w = canvas_w * 0.45
        phone_area_h = canvas_h * 0.75
        aspect = orig_w / orig_h
        if phone_area_w / phone_area_h > aspect:
            phone_h = phone_area_h
            phone_w = phone_h * aspect
        else:
            phone_w = phone_area_w
            phone_h = phone_w / aspect

        phone_x = canvas_w * 0.08
        phone_y = (canvas_h - phone_h) / 2 - 20

        self._draw_phone_outline(phone_x, phone_y, phone_w, phone_h)

        bar_x = phone_x + phone_w + 60
        bar_top = phone_y
        bar_height = phone_h
        max_height_value = max(orig_h, mir_h)

        orig_bar_h = (orig_h / max_height_value) * bar_height
        mir_bar_h = (mir_h / max_height_value) * bar_height

        self._draw_vertical_bar(bar_x, bar_top, bar_height, orig_bar_h, ORIGINAL_COLOR, f"Original:\n{orig_h}")
        self._draw_vertical_bar(bar_x + 45, bar_top, bar_height, mir_bar_h, MIRRORED_COLOR, f"Mirrored:\n{mir_h}")

        hbar_y = phone_y + phone_h + 60
        hbar_width = phone_w
        max_width_value = max(orig_w, mir_w)
        orig_bar_w = (orig_w / max_width_value) * hbar_width
        mir_bar_w = (mir_w / max_width_value) * hbar_width

        self._draw_horizontal_bar(phone_x, hbar_y, hbar_width, orig_bar_w, mir_bar_w, orig_w, mir_w)

    def _draw_phone_outline(self, x, y, w, h):
        radius = 18
        self.canvas.create_rectangle(
            x, y, x + w, y + h,
            outline="white", width=2
        )
        notch_x = x + w / 2
        self.canvas.create_oval(notch_x - 5, y + 10, notch_x + 5, y + 20, outline="white", width=1)

    def _draw_vertical_bar(self, x, top, max_h, bar_h, color, label):
        bottom = top + max_h
        bar_top = bottom - bar_h
        self.canvas.create_line(x, top, x, bottom, fill="gray40", width=1)
        self.canvas.create_line(x, bar_top, x, bottom, fill=color, width=3)
        self.canvas.create_text(
            x + 45, bar_top, text=label, fill=color,
            font=("Segoe UI", 10), anchor="w"
        )

    def _draw_horizontal_bar(self, x, y, max_w, orig_w, mir_w, orig_value, mir_value):
        self.canvas.create_line(x, y, x + max_w, y, fill="gray40", width=1)
        self.canvas.create_line(x, y, x + orig_w, y, fill=ORIGINAL_COLOR, width=3)
        self.canvas.create_line(x, y + 10, x + mir_w, y + 10, fill=MIRRORED_COLOR, width=3)
        self.canvas.create_text(
            x, y + 25, text=f"Original: {orig_value}", fill=ORIGINAL_COLOR,
            font=("Segoe UI", 10), anchor="w"
        )
        self.canvas.create_text(
            x + orig_w + 20, y + 25, text=f"Mirrored: {mir_value}", fill=MIRRORED_COLOR,
            font=("Segoe UI", 10), anchor="w"
        )

    def _on_start_stop(self):
        if scrcpy.is_running(self.process):
            scrcpy.stop(self.process)
            self.process = None
            self.start_button.configure(text="Start", fg_color=["#1f6aa5", "#1f6aa5"])
            return

        if not self.app.connected_serial:
            return

        max_size, bit_rate = self._get_target_max_size_and_bitrate()
        self.process = scrcpy.launch(self.app.connected_serial, max_size, bit_rate)
        if self.process:
            self.start_button.configure(text="Stop Mirroring", fg_color="#c0392b")
            self._watch_process()

    def _watch_process(self):
        if self.process is None:
            return
        if not scrcpy.is_running(self.process):
            self.process = None
            self.start_button.configure(text="Start", fg_color=["#1f6aa5", "#1f6aa5"])
            return
        self.after(1000, self._watch_process)


PRESET_ORDER = ["Performance", "Balanced", "Quality"]

EXPLANATIONS = {
    "Performance": "Lower resolution and bit rate. Best for slower PCs or laggy connections, at the cost of visual sharpness.",
    "Balanced": "A middle ground between smoothness and quality. Good default for most devices and computers.",
    "Quality": "Full resolution and higher bit rate. Best visual quality, but requires a stronger PC and USB connection.",
}

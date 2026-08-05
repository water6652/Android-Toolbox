import threading
import time
import customtkinter as ctk
from core.adb import check_devices, get_device_model
from core.device_info import resolve_marketing_name
from core.paths import check_engine_files
from screens.home import HomeFrame
from screens.screen_mirror import ScreenMirrorFrame
from screens.file_browser import FileBrowserFrame

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    "Home",
    "File Browser",
    "Gallery",
    "App Manager",
    "Screen Mirror",
    "Backup",
    "Settings",
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Android Toolbox")
        self.geometry("1100x650")

        self.connected_serial = None
        self.device_name = None
        self.device_status = "searching"
        self.polling = True
        self.tabs = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False)

        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="Android Toolbox",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.pack(padx=20, pady=(20, 15))

        self.appearance_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Light", "Dark", "System"],
            command=self.change_appearance
        )
        self.appearance_menu.set("Dark")
        self.appearance_menu.pack(side="bottom", padx=15, pady=20)

        self.nav_buttons = {}
        self.device_sub_frame = None

        for name in NAV_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                border_width=1,
                border_color=("gray70", "gray40"),
                command=lambda n=name: self.select_tab(n)
            )
            btn.pack(padx=15, pady=(5, 0), fill="x")
            self.nav_buttons[name] = btn

            if name == "Home":
                self.device_sub_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", width=170)

                self.device_name_label = ctk.CTkLabel(
                    self.device_sub_frame, text="", font=ctk.CTkFont(size=11),
                    text_color="gray60", anchor="w", justify="left"
                )
                self.device_name_label.pack(anchor="w")

                self.device_status_row = ctk.CTkFrame(self.device_sub_frame, fg_color="transparent")
                self.device_status_row.pack(anchor="w", fill="x")

                self.device_status_dot = ctk.CTkLabel(
                    self.device_status_row, text="●", font=ctk.CTkFont(size=11),
                    text_color="gray40", width=15
                )
                self.device_status_dot.pack(side="left")

                self.device_status_label = ctk.CTkLabel(
                    self.device_status_row, text="", font=ctk.CTkFont(size=11),
                    text_color="gray60", anchor="w"
                )
                self.device_status_label.pack(side="left")

                self.device_usb_icon = ctk.CTkLabel(
                    self.device_status_row, text="USB", font=ctk.CTkFont(size=10),
                    text_color="gray50"
                )
                self.device_usb_icon.pack(side="right", padx=(0, 5))

        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.home_frame = HomeFrame(self.content, self)
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.tabs["Home"] = self.home_frame

        self.screen_mirror_frame = ScreenMirrorFrame(self.content, self)
        self.screen_mirror_frame.grid(row=0, column=0, sticky="nsew")
        self.tabs["Screen Mirror"] = self.screen_mirror_frame

        self.file_browser_frame = FileBrowserFrame(self.content, self)
        self.file_browser_frame.grid(row=0, column=0, sticky="nsew")
        self.tabs["File Browser"] = self.file_browser_frame

        self.select_tab("Home")

        missing = check_engine_files()
        if missing:
            self.home_frame.show_engine_warning(missing)
        else:
            threading.Thread(target=self._poll_for_device, daemon=True).start()

    def select_tab(self, name):
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        if name in self.tabs:
            self.tabs[name].tkraise()
            if hasattr(self.tabs[name], "refresh"):
                self.tabs[name].refresh()

    def _poll_for_device(self):
        while self.polling:
            result = check_devices()
            if result["authorized"]:
                serial = result["authorized"][0]
                if serial != self.connected_serial or self.device_status != "connected":
                    self.after(0, self._on_device_found, serial)
            elif result["unauthorized"]:
                self.after(0, self._on_device_unauthorized)
            else:
                self.after(0, self._on_searching)
            time.sleep(1.5)

    def _on_searching(self):
        if self.device_status == "searching":
            return
        self.device_status = "searching"
        self.connected_serial = None
        self.device_sub_frame.pack_forget()
        self._refresh_active_tab()

    def _on_device_unauthorized(self):
        self.device_status = "unauthorized"
        self.connected_serial = None
        self.device_sub_frame.pack(after=self.nav_buttons["Home"], pady=(6, 5))
        self.device_name_label.configure(text="Unknown device")
        self.device_status_dot.configure(text_color="#e0a800")
        self.device_status_label.configure(text="Not authorized")
        self._refresh_active_tab()

    def _on_device_found(self, serial):
        self.connected_serial = serial
        self.device_status = "connected"
        raw_model = get_device_model(serial)
        self.device_name = resolve_marketing_name(raw_model)

        self.device_sub_frame.pack(after=self.nav_buttons["Home"], pady=(6, 5))
        self.device_name_label.configure(text=self.device_name)
        self.device_status_dot.configure(text_color="#2ecc71")
        self.device_status_label.configure(text="Connected")
        self._refresh_active_tab()

    def _refresh_active_tab(self):
        for name, frame in self.tabs.items():
            if self.nav_buttons[name].cget("fg_color") != "transparent":
                if hasattr(frame, "refresh"):
                    frame.refresh()

    def change_appearance(self, mode):
        ctk.set_appearance_mode(mode)


if __name__ == "__main__":
    app = App()
    app.mainloop()
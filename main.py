import subprocess
import threading
import time
import customtkinter as ctk

ADB_PATH = "adb"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def check_devices() -> list[str]:
    result = subprocess.run(
        [ADB_PATH, "devices"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        return []
    lines = result.stdout.strip().splitlines()[1:]
    devices = []
    for line in lines:
        if not line.strip():
            continue
        serial, status = line.split("\t")
        if status == "device":
            devices.append(serial)
    return devices


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Android Toolbox")
        self.geometry("1100x650")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="Android Toolbox",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 15))

        self.nav_buttons = {}
        nav_items = [
            "Home",
            "File Browser",
            "Gallery",
            "App Manager",
            "Screen Mirror",
            "Backup",
            "Settings",
        ]

        for i, name in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda n=name: self.select_tab(n)
            )
            btn.grid(row=i + 1, column=0, padx=15, pady=5, sticky="ew")
            self.nav_buttons[name] = btn

        self.appearance_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Light", "Dark", "System"],
            command=self.change_appearance
        )
        self.appearance_menu.set("Dark")
        self.appearance_menu.grid(row=10, column=0, padx=15, pady=20, sticky="s")

        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.connected_serial = None
        self.tabs = {}

        self.home_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.tabs["Home"] = self.home_frame

        self.status_label = ctk.CTkLabel(
            self.home_frame, text="Searching for device...",
            font=ctk.CTkFont(size=16)
        )
        self.status_label.pack(pady=(40, 10))

        self.spinner = ctk.CTkProgressBar(self.home_frame, mode="indeterminate", width=200)
        self.spinner.pack(pady=10)
        self.spinner.start()

        self.select_tab("Home")

        self.polling = True
        threading.Thread(target=self._poll_for_device, daemon=True).start()

    def select_tab(self, name):
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        if name in self.tabs:
            self.tabs[name].tkraise()

    def _poll_for_device(self):
        while self.polling:
            devices = check_devices()
            if devices:
                self.after(0, self._on_device_found, devices[0])
                return
            time.sleep(1.5)

    def _on_device_found(self, serial):
        self.connected_serial = serial
        self.spinner.stop()
        self.spinner.pack_forget()
        self.status_label.configure(text=f"Connected: {serial}")

    def change_appearance(self, mode):
        ctk.set_appearance_mode(mode)


if __name__ == "__main__":
    app = App()
    app.mainloop()

import subprocess
import threading
import customtkinter as ctk

ADB_PATH = "adb"
SCRCPY_PATH = "scrcpy"

def run_adb_command(args: list[str]) -> str:
    result = subprocess.run(
        [ADB_PATH] + args,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def check_devices() -> list[str]:
    output = run_adb_command(["devices"])
    lines = output.splitlines()[1:] if output else []
    devices = []
    for line in lines:
        if not line.strip():
            continue
        serial, status = line.split("\t")
        if status == "device":
            devices.append(serial)
    return devices

def launch_scrcpy(serial: str):
    try:
        subprocess.Popen(
            [SCRCPY_PATH, "-s", serial],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except FileNotFoundError:
        print(f"[ERROR] Could not find '{SCRCPY_PATH}'.")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Android Toolbox")
        self.geometry("500x350")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.connected_serial = None

        self.status_label = ctk.CTkLabel(
            self, text="No device connected", font=("Segoe UI", 16)
        )
        self.status_label.pack(pady=(30, 10))

        self.connect_button = ctk.CTkButton(
            self, text="Connect Device", command=self.on_connect_clicked
        )
        self.connect_button.pack(pady=10)

        self.scrcpy_button = ctk.CTkButton(
            self, text="Mirror Screen (scrcpy)",
            command=self.on_scrcpy_clicked, state="disabled"
        )
        self.scrcpy_button.pack(pady=10)

    def on_connect_clicked(self):
        self.status_label.configure(text="Checking for devices...")
        threading.Thread(target=self._check_devices_thread, daemon=True).start()

    def _check_devices_thread(self):
        devices = check_devices()
        self.after(0, self._update_after_check, devices)

    def _update_after_check(self, devices):
        if devices:
            self.connected_serial = devices[0]
            self.status_label.configure(text=f"Connected: {self.connected_serial}")
            self.scrcpy_button.configure(state="normal")
        else:
            self.status_label.configure(text="No authorized device found")
            self.scrcpy_button.configure(state="disabled")

    def on_scrcpy_clicked(self):
        if self.connected_serial:
            launch_scrcpy(self.connected_serial)


if __name__ == "__main__":
    app = App()
    app.mainloop()
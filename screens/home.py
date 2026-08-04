import customtkinter as ctk


class HomeFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        self.title_label = ctk.CTkLabel(
            self, text="Android Toolbox",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=(60, 10))

        self.subtitle_label = ctk.CTkLabel(
            self, text="Connect your phone via USB to get started",
            font=ctk.CTkFont(size=15),
            text_color="gray60"
        )
        self.subtitle_label.pack(pady=(0, 20))

        self.warning_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=14),
            text_color="#e74c3c", justify="left"
        )
        self.warning_label.pack(pady=(10, 0))

    def show_engine_warning(self, missing_files):
        files_text = "\n".join(missing_files)
        self.warning_label.configure(
            text=f"Missing required files:\n{files_text}\n\nPlace adb.exe and scrcpy.exe (with their DLLs) inside the 'engine' folder next to main.py."
        )

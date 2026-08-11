import webbrowser
import customtkinter as ctk

APP_VERSION = "Alpha 0.1.LARP"
REPO_URL = "https://github.com/water6652/Android-Toolbox"
ISSUES_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeBEb_PMxInyWC1BC04w15enZRXAGP3_3mDXvWn16ploSf_hg/viewform?usp=publish-editor"

ATTRIBUTIONS = [
    ("CustomTkinter", "https://github.com/tomschimansky/customtkinter"),
    ("ADB", "https://developer.android.com/tools/adb"),
    ("scrcpy", "https://github.com/genymobile/scrcpy"),
    ("pyaxmlparser", "https://github.com/appknox/pyaxmlparser"),
    ("Pillow", "https://github.com/python-pillow/Pillow"),
]

class AboutSettingsFrame(ctk.CTkFrame):
    def __init__(self ,master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        title = ctk.CTkLabel(self, text="About", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(20,15))

        info_section = ctk.CTkFrame(self, fg_color="gray17")
        info_section.pack(fill="x", padx=20, pady=(0,10))

        ctk.CTkLabel(
            info_section, text="Android Toolbox", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15,0))
        ctk.CTkLabel(
            info_section, text=f"Version {APP_VERSION}", text_color="gray60"
        ).pack(anchor="w", padx=15, pady=(0,15))

        links_section = ctk.CTkFrame(self, fg_color="gray17")
        links_section.pack(fill="x", padx=20, pady=(0, 10))

        self._build_link_row(links_section, "View the source code on GitHub!", REPO_URL)
        self._build_link_row(links_section, "If you encounter any bugs lemme know!", ISSUES_URL)

        attributions_section = ctk.CTkFrame(self, fg_color="gray17")
        attributions_section.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(attributions_section, text="This wouldn't exist of it weren't for these goats:", anchor="w").pack(
            anchor="w", padx=15, pady=(12,6)
        )
        for name, url in ATTRIBUTIONS:
            self._build_link_row(attributions_section, name, url, small=True)

        ctk.CTkLabel(attributions_section, text="", height=1).pack(pady=4)

    def _build_link_row(self, parent, label_text, url, small=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0,10) if not small else (0, 4))

        font = ctk.CTkFont(size=12) if small else ctk.CTkFont(size=13)
        link_label = ctk.CTkLabel(row, text=label_text, text_color="#3f91d4", font=font, cursor="hand2")
        link_label.pack(anchor="w")
        link_label.bind("<Button-1>", lambda e, u=url: webbrowser)
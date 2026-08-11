import customtkinter as ctk
from screens.about import AboutSettingsFrame

CATEGORY_ORDER = [
    "General",
    "File Browser",
    "Gallery",
    "App Manager",
    "Screen Mirror",
    "Backup",
    "About",
]

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.tabs = {}
        self.category_buttons = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_category_panel()
        self._build_content_area()

        self.tabs["About"] = AboutSettingsFrame(self.content, self.app)

        for tab in self.tabs.values():
            tab.grid(row=0, column=0, sticky="nsew")

        self._show_category(CATEGORY_ORDER[0])

    def _build_category_panel(self):
        self.category_panel = ctk.CTkFrame(self, width=180)
        self.category_panel.grid(row=0, column=0, sticky="ns", padx=(20, 10), pady=20)
        self.category_panel.pack_propagate(False)

        for name in CATEGORY_ORDER:
            btn = ctk.CTkButton(
                self.category_panel, text=name, anchor="w",
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                border_width=1, border_color=("gray70", "gray40"),
                command=lambda n=name: self._show_category(n)
            )
            btn.pack(fill="x", padx=10, pady=(10,0))
            self.category_buttons[name] = btn

    def _build_content_area(self):
        self.content = ctk.CTkFrame(self, fg_color="gray17")
        self.content.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.placeholder = ctk.CTkLabel(self.content, text="", text_color="gray67", font=ctk.CTkFont(size=21))
        self.placeholder.grid(row=0, column=0)

    def _show_category(self, name):
        for category_name, btn in self.category_buttons.items():
            if category_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        for tab in self.tabs.values():
            tab.grid_remove()

        if name in self.tabs:
            self.placeholder.grid_remove()
            self.tabs[name].grid(row=0, column=0, sticky="nsew")
        else:
            self.placeholder.configure(text=f"{name} coming soon trust #fairs✌")
            self.placeholder.grid(row=0, column=0)
                              

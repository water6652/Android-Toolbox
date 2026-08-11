import os
import json
import copy

DEFAULTS = {
    "general": {
        "launch_on_startup": False,
        "appearance_mode": "Dark",
    },
    "file_browser": {
        "default_path": "/sdcard",
        "show_hidden": False,
        "confirm_delete": True,
    },
    "gallery": {
        "default_source": "all",
        "thumbnail_max_size": 220,
    },
    "app_manager": {
        "confirm_disable": True,
        "confirm_uninstall": True,
        "keep_data_default": True,
        "save_apk_destination": "",
    },
    "screen_mirror": {
        "default_preset": "Balanced",
        "lock_screen_while_mirroring": False,
    },
    "backup": {
        "default_destination": "",
        "default_categories": ["photos", "music", "downloads", "whatsapp"],
        "auto_backup_on_connect": False,
    },
}

def get_settings_path() -> str:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    settings_dir = os.path.join(base, "Android Toolbox")
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, "settings.json")

def _deep_merge_defaults(data: dict) -> dict:
    merged = copy.deepcopy(DEFAULTS)
    for category, values in data.items():
        if category not in merged:
            continue
        if isinstance(values, dict):
            merged[category].update(values)
    return merged


def load_settings() -> dict:
    path = get_settings_path()
    if not os.path.isfile(path):
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _deep_merge_defaults(data)
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULTS)


def save_settings(data: dict) -> None:
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass

_settings = load_settings()

def get(category: str, key: str):
    return _settings.get(category, {}).get(key, DEFAULTS.get(category, {}).get(key))

def set(category: str, key: str, value) -> None:
    if category not in _settings:
        _settings[category] = {}
    _settings[category][key] = value
    save_settings(_settings)

def get_category(category: str) -> dict:
    return _settings.get(category, copy.deepcopy(DEFAULTS.get(category, {})))
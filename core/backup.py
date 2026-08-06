import os
import json
import shutil
import subprocess
from datetime import datetime
from core.paths import ADB_PATH

CATEGORIES = [
    {"key": "photos", "label": "Photos & Videos", "icon": "🖼️",
     "paths": ["/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Movies"]},
    {"key": "music", "label": "Music", "icon": "🎵",
     "paths": ["/sdcard/Music"]},
    {"key": "downloads", "label": "Downloads", "icon": "📥",
     "paths": ["/sdcard/Download"]},
    {"key": "whatsapp", "label": "WhatsApp Media", "icon": "💬",
     "paths": ["/sdcard/Android/media/com.whatsapp/WhatsApp/Media", "/sdcard/WhatsApp/Media"]},
]

CATEGORIES_BY_KEY = {c["key"]: c for c in CATEGORIES}


def get_default_backup_root() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "Android Toolbox", "Backups")


def _shell(serial, command) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            [ADB_PATH, "-s", serial, "shell", command],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        return None


def scan_category(serial: str, category: dict) -> dict:
    total_files = 0
    total_kb = 0
    for path in category["paths"]:
        quoted = f'"{path}"'
        count_result = _shell(serial, f"find {quoted} -type f 2>/dev/null | wc -l")
        if count_result and count_result.returncode == 0 and count_result.stdout:
            try:
                total_files += int(count_result.stdout.strip())
            except ValueError:
                pass

        size_result = _shell(serial, f"du -sk {quoted} 2>/dev/null")
        if size_result and size_result.returncode == 0 and size_result.stdout.strip():
            try:
                total_kb += int(size_result.stdout.strip().split()[0])
            except (ValueError, IndexError):
                pass
    return {"files": total_files, "size_kb": total_kb}


def perform_backup(serial: str, category_keys: list[str], destination_root: str, progress_callback=None):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = os.path.join(destination_root, timestamp)
    os.makedirs(backup_folder, exist_ok=True)

    results = {}

    for key in category_keys:
        category = CATEGORIES_BY_KEY[key]
        if progress_callback:
            progress_callback(key, "running")

        category_folder = os.path.join(backup_folder, key)
        os.makedirs(category_folder, exist_ok=True)

        pulled_any = False
        had_error = False

        for path in category["paths"]:
            try:
                result = subprocess.run(
                    [ADB_PATH, "-s", serial, "pull", path, category_folder],
                    capture_output=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result is None:
                    had_error = True
                    continue
                if result.returncode == 0:
                    pulled_any = True
                elif "does not exist" not in (result.stderr or ""):
                    had_error = True
            except Exception:
                had_error = True

        if pulled_any:
            status = "done"
        elif had_error:
            status = "failed"
        else:
            status = "empty"

        results[key] = status
        if progress_callback:
            progress_callback(key, status)

    manifest = {"timestamp": timestamp, "categories": results}
    manifest_path = os.path.join(backup_folder, "manifest.json")
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except OSError:
        pass

    return backup_folder, results


def get_folder_size(folder: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def list_backups(destination_root: str) -> list[dict]:
    if not os.path.isdir(destination_root):
        return []

    backups = []
    for name in sorted(os.listdir(destination_root), reverse=True):
        folder = os.path.join(destination_root, name)
        manifest_path = os.path.join(folder, "manifest.json")
        if not os.path.isdir(folder) or not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        backups.append({
            "name": name,
            "path": folder,
            "categories": manifest.get("categories", {}),
            "size_bytes": get_folder_size(folder),
        })
    return backups


def delete_backup(path: str) -> bool:
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        return False
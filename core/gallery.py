import os
import hashlib
import tempfile
import subprocess
from PIL import Image
from core.paths import ADB_PATH
from core.adb import list_directory

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "webm", "3gp"}

SOURCES = [
    ("all", "All Photos & Videos", ["/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Movies"]),
    ("camera", "Camera", ["/sdcard/DCIM/Camera"]),
    ("screenshots", "Screenshots", ["/sdcard/Pictures/Screenshots"]),
    ("downloads", "Downloads", ["/sdcard/Download"]),
]
SOURCES_BY_KEY = {key: (label, paths) for key, label, paths in SOURCES}


def get_extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def list_media(serial: str, source_key: str) -> list[dict]:
    _, paths = SOURCES_BY_KEY.get(source_key, (None, []))
    media = []

    for path in paths:
        entries = list_directory(serial, path)
        if not entries:
            continue
        for entry in entries:
            if entry["is_dir"]:
                continue
            ext = get_extension(entry["name"])
            is_image = ext in IMAGE_EXTS
            is_video = ext in VIDEO_EXTS
            if not is_image and not is_video:
                continue
            media.append({
                "name": entry["name"],
                "remote_path": f"{path.rstrip('/')}/{entry['name']}",
                "size": entry["size"],
                "modified": entry["modified"],
                "is_video": is_video,
            })

    media.sort(key=lambda e: e["modified"], reverse=True)
    return media


def get_cache_dir() -> str:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    cache_dir = os.path.join(base, "Android Toolbox", "thumbnail_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _cache_key(entry: dict) -> str:
    raw = f"{entry['remote_path']}|{entry['size']}|{entry['modified']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_thumbnail_path(serial: str, entry: dict, max_size=(220, 220)) -> str | None:
    if entry["is_video"]:
        return None

    cache_dir = get_cache_dir()
    key = _cache_key(entry)
    cache_path = os.path.join(cache_dir, f"{key}.jpg")

    if os.path.isfile(cache_path):
        return cache_path

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, "original")
        try:
            result = subprocess.run(
                [ADB_PATH, "-s", serial, "pull", entry["remote_path"], local_path],
                capture_output=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            return None

        if result.returncode != 0 or not os.path.isfile(local_path):
            return None

        try:
            img = Image.open(local_path)
            img = img.convert("RGB")
            img.thumbnail(max_size)
            img.save(cache_path, "JPEG", quality=85)
            return cache_path
        except Exception:
            return None


def pull_full_media(serial: str, entry: dict) -> str | None:
    cache_dir = get_cache_dir()
    key = _cache_key(entry) + "_full"
    ext = get_extension(entry["name"]) or "bin"
    cache_path = os.path.join(cache_dir, f"{key}.{ext}")

    if os.path.isfile(cache_path):
        return cache_path

    try:
        result = subprocess.run(
            [ADB_PATH, "-s", serial, "pull", entry["remote_path"], cache_path],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        return None

    if result.returncode == 0 and os.path.isfile(cache_path):
        return cache_path
    return None
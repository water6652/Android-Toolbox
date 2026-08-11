import subprocess
import shlex
from core.paths import ADB_PATH


def _run(args: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            [ADB_PATH] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        return None


def check_devices() -> dict:
    result = _run(["devices"])
    if result is None or result.returncode != 0:
        return {"authorized": [], "unauthorized": []}

    lines = result.stdout.strip().splitlines()[1:]
    authorized = []
    unauthorized = []
    for line in lines:
        if not line.strip():
            continue
        serial, status = line.split("\t")
        if status == "device":
            authorized.append(serial)
        elif status == "unauthorized":
            unauthorized.append(serial)
    return {"authorized": authorized, "unauthorized": unauthorized}


def get_device_model(serial: str) -> str:
    result = _run(["-s", serial, "shell", "getprop", "ro.product.model"])
    if result is None or result.returncode != 0:
        return "Unknown Device"
    return result.stdout.strip()


def get_screen_resolution(serial: str) -> tuple[int, int] | None:
    result = _run(["-s", serial, "shell", "wm", "size"])
    if result is None or result.returncode != 0:
        return None

    output = result.stdout.strip()
    if "Override size" in output:
        line = [l for l in output.splitlines() if "Override size" in l][0]
    elif "Physical size" in output:
        line = [l for l in output.splitlines() if "Physical size" in l][0]
    else:
        return None

    try:
        resolution_part = line.split(":")[1].strip()
        width_str, height_str = resolution_part.split("x")
        return int(width_str), int(height_str)
    except (IndexError, ValueError):
        return None


def list_directory(serial: str, path: str) -> list[dict] | None:
    result = _run(["-s", serial, "shell", "ls", "-la", path])
    if result is None or result.returncode != 0 or result.stdout is None:
        return None 


    entries = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("total"):
            continue

        parts = line.split(None, 7)
        if len(parts) < 8:
            continue

        perms, _links, _owner, _group, size, date, time, name = parts

        if name in (".", ".."):
            continue

        is_dir = perms.startswith("d")
        is_link = perms.startswith("l")
        if is_link and " -> " in name:
            name = name.split(" -> ")[0]

        try:
            size_value = int(size)
        except ValueError:
            size_value = 0

        entries.append({
            "name": name,
            "is_dir": is_dir,
            "size": size_value,
            "modified": f"{date} {time}",
        })

    return entries
import os
import json
import tempfile
import subprocess
from datetime import datetime
from core.paths import ADB_PATH

try:
    from pyaxmlparser import APK as AxmlAPK
    PYAXMLPARSER_AVAILABLE = True
except ImportError:
    PYAXMLPARSER_AVAILABLE = False

_info_cache = {}


def _run(args) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            [ADB_PATH] + args,
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        return None


def _parse_package_list(output: str) -> set[str]:
    names = set()
    if not output:
        return names
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            names.add(line[len("package:"):].strip())
    return names


def list_packages(serial: str, view: str) -> list[str]:
    if view == "all":
        result = _run(["-s", serial, "shell", "pm", "list", "packages", "-e"])
        return sorted(_parse_package_list(result.stdout if result else ""))

    if view == "user":
        result = _run(["-s", serial, "shell", "pm", "list", "packages", "-3", "-e"])
        return sorted(_parse_package_list(result.stdout if result else ""))

    if view == "system":
        result = _run(["-s", serial, "shell", "pm", "list", "packages", "-s", "-e"])
        return sorted(_parse_package_list(result.stdout if result else ""))

    if view == "disabled":
        disabled_result = _run(["-s", serial, "shell", "pm", "list", "packages", "-d"])
        uninstalled_result = _run(["-s", serial, "shell", "pm", "list", "packages", "-u"])
        active_result = _run(["-s", serial, "shell", "pm", "list", "packages"])

        disabled = _parse_package_list(disabled_result.stdout if disabled_result else "")
        uninstalled = _parse_package_list(uninstalled_result.stdout if uninstalled_result else "")
        active = _parse_package_list(active_result.stdout if active_result else "")

        removed_for_user = uninstalled - active
        return sorted(disabled | removed_for_user)

    return []


def resolve_app_info(serial: str, package: str) -> dict:
    if package in _info_cache:
        return _info_cache[package]

    info = {"label": package, "icon_bytes": None}

    if not PYAXMLPARSER_AVAILABLE:
        _info_cache[package] = info
        return info

    path_result = _run(["-s", serial, "shell", "pm", "path", package])
    if not path_result or path_result.returncode != 0 or not path_result.stdout:
        _info_cache[package] = info
        return info

    lines = [l for l in path_result.stdout.splitlines() if l.startswith("package:")]
    if not lines:
        _info_cache[package] = info
        return info

    remote_apk_path = lines[0][len("package:"):].strip()

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_apk_path = os.path.join(tmp_dir, "app.apk")
        pull_result = subprocess.run(
            [ADB_PATH, "-s", serial, "pull", remote_apk_path, local_apk_path],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if pull_result.returncode != 0 or not os.path.isfile(local_apk_path):
            _info_cache[package] = info
            return info

        try:
            apk = AxmlAPK(local_apk_path)
            label = apk.application
            if label:
                info["label"] = label
            info["icon_bytes"] = apk.icon_data
        except Exception:
            pass

    _info_cache[package] = info
    return info


def disable_app(serial: str, package: str) -> bool:
    result = _run(["-s", serial, "shell", "pm", "disable-user", "--user", "0", package])
    return result is not None and result.returncode == 0


def enable_app(serial: str, package: str) -> bool:
    result = _run(["-s", serial, "shell", "pm", "enable", package])
    return result is not None and result.returncode == 0


def uninstall_app(serial: str, package: str, keep_data: bool = True) -> bool:
    args = ["-s", serial, "shell", "pm", "uninstall"]
    if keep_data:
        args.append("-k")
    args += ["--user", "0", package]
    result = _run(args)
    return result is not None and result.returncode == 0


def restore_app(serial: str, package: str) -> bool:
    result = _run(["-s", serial, "shell", "cmd", "package", "install-existing", "--user", "0", package])
    return result is not None and result.returncode == 0


def save_apk(serial: str, package: str, destination_folder: str) -> bool:
    path_result = _run(["-s", serial, "shell", "pm", "path", package])
    if not path_result or path_result.returncode != 0 or not path_result.stdout:
        return False
    lines = [l for l in path_result.stdout.splitlines() if l.startswith("package:")]
    if not lines:
        return False
    remote_apk_path = lines[0][len("package:"):].strip()

    os.makedirs(destination_folder, exist_ok=True)
    local_path = os.path.join(destination_folder, f"{package}.apk")
    result = subprocess.run(
        [ADB_PATH, "-s", serial, "pull", remote_apk_path, local_path],
        capture_output=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return result.returncode == 0


def get_history_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "Android Toolbox", "AppManagerHistory")


def log_action(action_type: str, apps: list[dict]) -> None:
    history_dir = get_history_dir()
    os.makedirs(history_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    entry = {"timestamp": timestamp, "action": action_type, "apps": apps}
    path = os.path.join(history_dir, f"{timestamp}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
    except OSError:
        pass


def list_history() -> list[dict]:
    history_dir = get_history_dir()
    if not os.path.isdir(history_dir):
        return []

    entries = []
    for name in sorted(os.listdir(history_dir), reverse=True):
        if not name.endswith(".json"):
            continue
        path = os.path.join(history_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return entries
import subprocess
from core.paths import ADB_PATH


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [ADB_PATH] + args,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )


def check_devices() -> dict:
    result = _run(["devices"])
    if result.returncode != 0:
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
    if result.returncode != 0:
        return "Unknown Device"
    return result.stdout.strip()


def get_screen_resolution(serial: str) -> tuple[int, int] | None:
    result = _run(["-s", serial, "shell", "wm", "size"])
    if result.returncode != 0:
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

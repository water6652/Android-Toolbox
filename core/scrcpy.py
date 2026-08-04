import subprocess
from core.paths import SCRCPY_PATH

PRESETS = {
    "Performance": {"max_size": 720, "bit_rate": "2M"},
    "Balanced": {"max_size": 1080, "bit_rate": "8M"},
    "Quality": {"max_size": 0, "bit_rate": "16M"},
}


def build_args(serial: str, max_size: int, bit_rate: str) -> list[str]:
    args = [SCRCPY_PATH, "-s", serial, "--video-bit-rate", bit_rate]
    if max_size and max_size > 0:
        args += ["--max-size", str(max_size)]
    return args


def launch(serial: str, max_size: int, bit_rate: str) -> subprocess.Popen | None:
    try:
        process = subprocess.Popen(
            build_args(serial, max_size, bit_rate),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return process
    except FileNotFoundError:
        return None


def is_running(process: subprocess.Popen | None) -> bool:
    if process is None:
        return False
    return process.poll() is None


def stop(process: subprocess.Popen | None):
    if process is not None and is_running(process):
        process.terminate()


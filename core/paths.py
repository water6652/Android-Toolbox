import sys
import os

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENGINE_DIR = os.path.join(BASE_DIR, "engine")
ADB_PATH = os.path.join(ENGINE_DIR, "adb.exe")
SCRCPY_PATH = os.path.join(ENGINE_DIR, "scrcpy.exe")


def check_engine_files() -> list[str]:
    missing = []
    if not os.path.isfile(ADB_PATH):
        missing.append("engine/adb.exe")
    if not os.path.isfile(SCRCPY_PATH):
        missing.append("engine/scrcpy.exe")
    return missing

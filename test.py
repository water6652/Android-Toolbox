import subprocess
import os

ADB_PATH = "adb"
SCRCPY_PATH = "scrcpy"

def run_adb_command(args: ist[str]) -> str:
    result = subprocess.run(
        [ADB_PATH] + args,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW 
    )
    if result.returncode != 0:
        print(f"[ERROR] adb {' '.join(args)} failed:\n{result.stderr}")
        return ""
    return result.stdout.strip()

def check_devices() -> list[str]:
    output = run_adb_command(["devices"])
    print("Raw output:\n", output, "\n")

    lines = output.splitlines()[1:] 
    devices = []
    for line in lines:
        if not line.strip():
            continue
        serial, status = line.split("\t")
        if status == "device":
            devices.append(serial)
        elif status == "unauthorized":
            print(f"[!] Device {serial} detected but UNAUTHORIZED — "
                  f"check the phone screen and tap 'Allow USB debugging'.")
    return devices


def list_sdcard_root(serial: str):
    """Lists files in /sdcard to confirm shell commands work."""
    output = run_adb_command(["-s", serial, "shell", "ls", "/sdcard"])
    print(f"Contents of /sdcard on {serial}:\n{output}\n")


def launch_scrcpy(serial: str):
    """Launches scrcpy as a separate detached window."""
    print(f"Launching scrcpy for {serial} ...")
    subprocess.Popen(
        [SCRCPY_PATH, "-s", serial],
        creationflags=subprocess.CREATE_NEW_CONSOLE 
    )

def main():
    print("=== Android Toolbox - Core Test ===\n")

    devices = check_devices()

    if not devices:
        print("No authorized devices found.")
        print("Checklist:")
        print(" 1. USB debugging enabled in Developer Options")
        print(" 2. Cable is a data cable, not charge-only")
        print(" 3. 'Allow USB debugging' prompt accepted on the phone")
        return

    print(f"Found {len(devices)} device(s): {devices}\n")

    serial = devices[0]
    list_sdcard_root(serial)

    launch = input("Launch scrcpy for this device? (y/n): ").strip().lower()
    if launch == "y":
        launch_scrcpy(serial)


if __name__ == "__main__":
    main()

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load the juicebox.env located in the same directory as this script
env_path = Path(__file__).parent / "juicebox.env"
load_dotenv(env_path)

NAS_LIST = os.getenv("MOUNT_NAS_FILE")

def remount_missing_nas(mount_file_path: str = NAS_LIST):
    if not mount_file_path:
        print("[ERROR] MOUNT_NAS_FILE not set in juicebox.env")
        return

    if not os.path.exists(mount_file_path):
        print(f"[ERROR] Mount file not found: {mount_file_path}")
        return

    with open(mount_file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Example line:
        # sudo mount -t nfs 10.10.10.5:/volume1/NAS /mnt/nas1
        parts = line.split()
        if len(parts) < 2:
            print(f"[WARN] Skipping malformed line: {line}")
            continue

        mount_point = parts[-1]

        if not mount_point.startswith("/mnt/"):
            print(f"[WARN] Skipping unknown mount point: {mount_point}")
            continue

        # Check if currently mounted
        if subprocess.call(["mountpoint", "-q", mount_point]) == 0:
            continue  # already mounted

        print(f"[WARNING] {mount_point} is unmounted. Attempting remount...")

        # Remove sudo so the script can run as root or via cron
        cmd = line.replace("sudo ", "").split()

        try:
            subprocess.run(cmd, check=True)
            print(f"[OK] Remounted {mount_point}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to remount {mount_point}: {e}")


if __name__ == "__main__":
    remount_missing_nas()

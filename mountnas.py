import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load the juicebox.env located in the same directory as this script
env_path = Path(__file__).parent / "juicebox.env"
load_dotenv(env_path)

NAS_LIST = os.getenv("NAS_LIST")

def is_host_online(host):
    try:
        subprocess.run(["ping", "-c", "1", "-W", "2", host],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def remount_missing_nas(mount_file_path: str = NAS_LIST):
    if not mount_file_path:
        print("[ERROR] NAS_LIST not set in juicebox.env")
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

        parts = line.replace("sudo ", "").split()
        mount_point = parts[-1]

        # Extract host
        host = None
        for p in parts[2:-1]:
            if p.startswith("//"):
                host = p.split('/')[2]
                break
            elif ":" in p:
                host = p.split(':')[0]
                break

        # Check if host is reachable
        if host and not is_host_online(host):
            print(f"[WARNING] Host {host} unreachable. Skipping {mount_point}.")
            continue

        # Check if already mounted
        if subprocess.call(["mountpoint", "-q", mount_point]) == 0:
            print(f"[OK] {mount_point} is already mounted. Skipping.")
            continue

        print(f"[WARNING] {mount_point} is unmounted. Attempting remount...")

        try:
            subprocess.run(parts, check=True, timeout=15)
            print(f"[OK] Remounted {mount_point}")
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Timeout. Skipping {mount_point}.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to remount {mount_point}: {e}")

if __name__ == "__main__":
    remount_missing_nas()
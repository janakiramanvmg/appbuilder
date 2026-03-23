import sys
import time

print("[1] Starting imports...")
start = time.time()

# Test each blocking operation individually
print("[2] Testing psutil cpu_percent...")
import psutil
t = time.time()
psutil.cpu_percent(interval=1)  # THIS BLOCKS 1 SECOND
print(f"    cpu_percent(interval=1) took {time.time()-t:.2f}s  <-- BLOCKING")

t = time.time()
psutil.cpu_percent(interval=None)
print(f"    cpu_percent(interval=None) took {time.time()-t:.2f}s  <-- OK")

print("[3] Testing platform/subprocess calls...")
import platform
import subprocess

t = time.time()
if platform.system().lower() == "windows":
    try:
        serial = subprocess.check_output(
            ["wmic", "bios", "get", "serialnumber"], 
            text=True,
            timeout=5
        )
        print(f"    wmic took {time.time()-t:.2f}s")
    except Exception as e:
        print(f"    wmic failed: {e} in {time.time()-t:.2f}s")

print("[4] Testing socket operations...")
import socket
t = time.time()
try:
    socket.setdefaulttimeout(5)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    print(f"    socket connect took {time.time()-t:.2f}s, ip={ip}")
except Exception as e:
    print(f"    socket failed: {e} in {time.time()-t:.2f}s  <-- BLOCKING?")

print("[5] Testing Qt import...")
t = time.time()
from PySide6.QtWidgets import QApplication
print(f"    Qt import took {time.time()-t:.2f}s")

print("[6] Testing cache file access...")
t = time.time()
import json, os, tempfile
from pathlib import Path

if platform.system() == "Windows":
    d_drive = Path("D:/")
    if d_drive.exists():
        BASE_TARGET_DIR = d_drive / "PremediaApp" / "Nas"
    else:
        BASE_TARGET_DIR = Path("C:/PremediaApp/Nas")
else:
    BASE_TARGET_DIR = Path.home() / "PremediaApp" / "Nas"

cache_dir = BASE_TARGET_DIR / "PremediaApp"
cache_file = cache_dir / "cache.json"
print(f"    Cache path: {cache_file}")
print(f"    Cache exists: {cache_file.exists()}")
print(f"    Cache check took {time.time()-t:.2f}s")

print("[7] Testing keyring...")
t = time.time()
try:
    import keyring
    # just import — don't call get_password yet
    print(f"    keyring import took {time.time()-t:.2f}s")
except Exception as e:
    print(f"    keyring failed: {e}")

print("[8] Testing validate_user network call...")
import urllib3
urllib3.disable_warnings()
import requests
BASE_DOMAIN = "https://app-uat.vmgpremedia.com"
USER_VALIDATE_URL = f"{BASE_DOMAIN}/api/user/validate"
t = time.time()
try:
    resp = requests.get(
        USER_VALIDATE_URL,
        params={"key": "test", "machine_id": "test"},
        verify=False,
        timeout=5   # SHORT timeout for debug only
    )
    print(f"    validate_user took {time.time()-t:.2f}s, status={resp.status_code}")
except Exception as e:
    print(f"    validate_user failed/timeout: {e} in {time.time()-t:.2f}s  <-- BLOCKING?")

print(f"\n[DONE] Total time: {time.time()-start:.2f}s")
print("The step that took the longest is your startup bottleneck.")
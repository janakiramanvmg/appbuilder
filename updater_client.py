import os
import sys
import time
import tempfile
import subprocess
import hashlib
import platform
import requests
import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk

# 🔹 Hosted version file
VERSION_URL = "https://vmg-premedia-22112023.s3.ap-southeast-2.amazonaws.com/application/drn/latest_version.json"


# =========================
# Utility helpers
# =========================

def sha256(path):
    """Compute lowercase SHA256 checksum."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def show_error(title, msg):
    """Safe Tk error dialog."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, msg)
    root.destroy()


def ask_user_to_update(latest):
    """Ask user if they want to update."""
    root = tk.Tk()
    root.withdraw()
    res = messagebox.askyesno(
        "Update Available",
        f"A new version {latest} is available.\nDo you want to update now?"
    )
    root.destroy()
    return res


# =========================
# Main update logic
# =========================

def check_for_update(current_version, exe_path):
    """Check S3 JSON for update and apply if needed."""
    try:
        r = requests.get(
            f"{VERSION_URL}?t={int(time.time())}",
            timeout=8,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        r.raise_for_status()

        try:
            data = r.json()
        except Exception as e:
            show_error("Update Error", f"Invalid update metadata:\n{e}")
            return

        latest_version = str(data.get("version", "")).strip()
        if not latest_version:
            show_error("Update Error", "Version information missing from server.")
            return

        print(f"[Updater] Current: {current_version} | Latest: {latest_version}")

        if latest_version == current_version:
            print("[Updater] ✅ Already up to date.")
            return

        mandatory = bool(data.get("mandatory"))
        if not mandatory and not ask_user_to_update(latest_version):
            print("[Updater] Skipped by user.")
            return

        os_type = platform.system()

        if os_type == "Windows":
            platform_data = data.get("windows", {})
        elif os_type == "Darwin":
            platform_data = data.get("mac", {})
        else:
            show_error("Update Error", f"Unsupported OS: {os_type}")
            return

        download_url = platform_data.get("url", "").strip()
        expected_sha = platform_data.get("sha256", "").strip().lower()

        if not download_url or not expected_sha:
            show_error(
                "Update Error",
                "Invalid update metadata for this platform.\nPlease contact support."
            )
            return

        print("[Updater] Download URL:", download_url)

        tmp_file = os.path.join(
            tempfile.gettempdir(),
            "PremediaApp_update.exe"  # unchanged (safe)
        )

        print(f"[Updater] Downloading update...")

        # =========================
        # 🔹 UI START (SAFE ADDITION)
        # =========================
        root = tk.Tk()
        root.title("Downloading Update")
        root.geometry("400x120")
        root.resizable(False, False)

        label = tk.Label(root, text="Downloading update...", anchor="center")
        label.pack(pady=10)

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
        progress_bar.pack(fill="x", padx=20, pady=10)

        percent_label = tk.Label(root, text="0%")
        percent_label.pack()

        root.update()
        # =========================

        with requests.get(download_url, stream=True, timeout=30) as resp:
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(tmp_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

                        # =========================
                        # 🔹 PROGRESS UPDATE (SAFE)
                        # =========================
                        downloaded += len(chunk)

                        if total > 0:
                            percent = (downloaded / total) * 100
                            progress_var.set(percent)
                            percent_label.config(text=f"{percent:.1f}%")

                        root.update_idletasks()
                        # =========================

        # =========================
        # 🔹 UI END (SAFE)
        # =========================
        root.destroy()
        # =========================

        print(f"[Updater] Downloaded to: {tmp_file}")

        # 🔹 Verify checksum
        actual_sha = sha256(tmp_file)
        print(f"[Updater] Expected SHA: {expected_sha}")
        print(f"[Updater] Actual SHA:   {actual_sha}")

        if actual_sha != expected_sha:
            try:
                os.remove(tmp_file)
            except Exception:
                pass
            show_error("Checksum Error", "Downloaded file failed verification.")
            return

        if os_type == "Darwin":
            os.chmod(tmp_file, 0o755)

        # 🔹 Launch updater
        if os_type == "Windows":
            updater_path = os.path.join(os.path.dirname(exe_path), "updater.exe")

            if not os.path.exists(updater_path):
                show_error("Update Error", f"Missing updater.exe at:\n{updater_path}")
                return

            print(f"[Updater] Launching updater.exe")

            subprocess.Popen(
                [updater_path, tmp_file, exe_path],
                close_fds=True,
                shell=False
            )

            time.sleep(2)
            sys.exit(0)

        elif os_type == "Darwin":
            updater_path = os.path.join(os.path.dirname(exe_path), "updater.sh")

            if not os.path.exists(updater_path):
                show_error("Update Error", "Missing updater.sh")
                return

            subprocess.Popen(["bash", updater_path, tmp_file, exe_path])
            sys.exit(0)

    except Exception as e:
        show_error("Update Failed", str(e))
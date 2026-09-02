import os
import sys
import time
import tempfile
import subprocess
import hashlib
import platform
import requests

from packaging.version import Version, InvalidVersion

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import Qt

VERSION_URL = (
    "https://vmg-premedia-22112023.s3.ap-southeast-2.amazonaws.com/"
    "application_uat/drn/latest_version.json"
)


def sha256(path):
    """Compute lowercase SHA256 checksum."""
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest().lower()


def normalize_version(version):
    """
    Convert versions such as:
        1.2.9(UAT) -> 1.2.9
        1.2.9      -> 1.2.9
    """
    value = str(version or "").strip()

    if "(" in value:
        value = value.split("(", 1)[0].strip()

    return value


def show_error(title, msg):
    """Display update error using PySide6."""
    QMessageBox.critical(
        None,
        title,
        str(msg),
        QMessageBox.StandardButton.Ok,
    )


def ask_user_to_update(latest):
    """Ask whether the user wants to install the update."""
    response = QMessageBox.question(
        None,
        "Update Available",
        (f"A new version {latest} is available.\n\n" "Do you want to update now?"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )

    return response == QMessageBox.StandardButton.Yes


def check_for_update(current_version, exe_path):
    """Check S3 JSON for update and apply if needed."""

    try:
        # ----------------------------------------------------------
        # Download version metadata
        # ----------------------------------------------------------
        r = requests.get(
            f"{VERSION_URL}?t={int(time.time())}",
            timeout=8,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )

        r.raise_for_status()

        try:
            data = r.json()
        except Exception as e:
            show_error(
                "Update Error",
                f"Invalid update metadata:\n{e}",
            )
            return

        latest_version = str(data.get("version", "")).strip()

        if not latest_version:
            show_error(
                "Update Error",
                "Version information missing from server.",
            )
            return

        print(f"[Updater] Current: {current_version} | " f"Latest: {latest_version}")

        # ----------------------------------------------------------
        # Proper version comparison
        # ----------------------------------------------------------
        try:
            current_clean = normalize_version(current_version)
            latest_clean = normalize_version(latest_version)

            current_ver = Version(current_clean)
            latest_ver = Version(latest_clean)

            print(f"[Updater] Comparing: " f"{current_ver} -> {latest_ver}")

            if latest_ver <= current_ver:
                print("[Updater] ✅ Already up to date.")
                return

        except InvalidVersion as e:
            print(f"[Updater] Invalid version value: {e}")
            return

        # ----------------------------------------------------------
        # Ask user
        # ----------------------------------------------------------
        mandatory = bool(data.get("mandatory", False))

        if not mandatory and not ask_user_to_update(latest_version):
            print("[Updater] Skipped by user.")
            return

        # ----------------------------------------------------------
        # Select platform
        # ----------------------------------------------------------
        os_type = platform.system()

        if os_type == "Windows":
            platform_data = data.get(
                "windows",
                {},
            )

            tmp_filename = "PremediaApp_update.exe"

        elif os_type == "Darwin":
            platform_data = data.get(
                "mac",
                {},
            )

            tmp_filename = "PremediaApp_update.dmg"

        else:
            show_error(
                "Update Error",
                f"Unsupported OS: {os_type}",
            )
            return

        download_url = str(platform_data.get("url", "")).strip()

        expected_sha = str(platform_data.get("sha256", "")).strip().lower()

        if not download_url or not expected_sha:
            show_error(
                "Update Error",
                (
                    "Invalid update metadata "
                    "for this platform.\n\n"
                    "Please contact support."
                ),
            )
            return

        print(
            "[Updater] Download URL:",
            download_url,
        )

        tmp_file = os.path.join(
            tempfile.gettempdir(),
            tmp_filename,
        )

        print("[Updater] Downloading update...")

        # ----------------------------------------------------------
        # PySide6 progress window
        # ----------------------------------------------------------
        progress_dialog = QProgressDialog(
            "Downloading update...",
            None,
            0,
            100,
        )

        progress_dialog.setWindowTitle("PremediaApp Update")

        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        progress_dialog.setCancelButton(None)

        progress_dialog.setMinimumDuration(0)

        progress_dialog.setAutoClose(False)

        progress_dialog.setValue(0)

        progress_dialog.show()

        QApplication.processEvents()

        # ----------------------------------------------------------
        # Download
        # ----------------------------------------------------------
        try:
            with requests.get(
                download_url,
                stream=True,
                timeout=30,
            ) as resp:

                resp.raise_for_status()

                total = int(
                    resp.headers.get(
                        "content-length",
                        0,
                    )
                )

                downloaded = 0

                with open(
                    tmp_file,
                    "wb",
                ) as f:

                    for chunk in resp.iter_content(chunk_size=8192):
                        if not chunk:
                            continue

                        f.write(chunk)

                        downloaded += len(chunk)

                        if total > 0:
                            percent = (downloaded / total) * 100

                            progress_dialog.setValue(int(percent))

                            progress_dialog.setLabelText(
                                ("Downloading update... " f"{percent:.1f}%")
                            )

                            QApplication.processEvents()

        finally:
            progress_dialog.close()

        print(f"[Updater] Downloaded to: " f"{tmp_file}")

        # ----------------------------------------------------------
        # SHA256 verification
        # ----------------------------------------------------------
        actual_sha = sha256(tmp_file)

        print(f"[Updater] Expected SHA: " f"{expected_sha}")

        print(f"[Updater] Actual SHA:   " f"{actual_sha}")

        if actual_sha != expected_sha:
            try:
                os.remove(tmp_file)
            except Exception:
                pass

            show_error(
                "Checksum Error",
                ("Downloaded file failed " "verification."),
            )
            return

        # ----------------------------------------------------------
        # Windows updater
        # ----------------------------------------------------------
        if os_type == "Windows":

            updater_path = os.path.join(
                os.path.dirname(exe_path),
                "updater.exe",
            )

            if not os.path.exists(updater_path):
                show_error(
                    "Update Error",
                    ("Missing updater.exe at:\n" f"{updater_path}"),
                )
                return

            print("[Updater] Launching updater.exe")

            subprocess.Popen(
                [
                    updater_path,
                    tmp_file,
                    exe_path,
                ],
                close_fds=True,
                shell=False,
            )

            time.sleep(2)

            sys.exit(0)

        # ----------------------------------------------------------
        # macOS updater
        # ----------------------------------------------------------
        elif os_type == "Darwin":

            updater_path = os.path.join(
                os.path.dirname(exe_path),
                "updater.sh",
            )

            if not os.path.exists(updater_path):
                show_error(
                    "Update Error",
                    ("Missing updater.sh at:\n" f"{updater_path}"),
                )
                return

            print("[Updater] Launching updater.sh")

            subprocess.Popen(
                [
                    "bash",
                    updater_path,
                    tmp_file,
                    exe_path,
                ]
            )

            sys.exit(0)

    except Exception as e:
        print(f"[Updater] Update failed: {e}")

        show_error(
            "Update Failed",
            str(e),
        )

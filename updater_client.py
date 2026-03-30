# updater_client.py
import os
import sys
import time
import tempfile
import subprocess
import hashlib
import platform
import threading
import requests

VERSION_URL = "https://vmg-premedia-22112023.s3.ap-southeast-2.amazonaws.com/application/drn/latest_version.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def check_for_update(current_version, exe_path):
    """
    Check for update and show a PySide6 progress window during download.
    Must be called BEFORE QApplication is created (top of main block).
    """
    try:
        r = requests.get(
            f"{VERSION_URL}?t={int(time.time())}",
            timeout=8,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            verify=False
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[Updater] Version check failed: {e}")
        return

    latest_version = str(data.get("version", "")).strip()
    if not latest_version or latest_version == current_version:
        print(f"[Updater] Up to date: {current_version}")
        return

    mandatory = bool(data.get("mandatory"))

    # ── Ask user (PySide6 dialog) ─────────────────────────────────────────
    from PySide6.QtWidgets import QApplication, QMessageBox
    _app = QApplication.instance() or QApplication(sys.argv)

    if not mandatory:
        reply = QMessageBox.question(
            None,
            "Update Available",
            f"Version {latest_version} is available.\n\nDo you want to update now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            print("[Updater] Skipped by user.")
            return

    os_type = platform.system()
    platform_data = data.get("windows" if os_type == "Windows" else "mac", {})
    download_url = platform_data.get("url", "").strip()
    expected_sha = platform_data.get("sha256", "").strip().lower()

    if not download_url or not expected_sha:
        QMessageBox.critical(None, "Update Error", "Invalid update metadata for this platform.")
        return

    # ── Download with progress UI ─────────────────────────────────────────
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
    )
    from PySide6.QtCore import Qt, QThread, Signal
    from PySide6.QtGui import QFont

    class DownloadThread(QThread):
        progress = Signal(int, str)   # percent, status_text
        finished = Signal(bool, str)  # success, message

        def __init__(self, url, dest):
            super().__init__()
            self.url = url
            self.dest = dest
            self.cancelled = False

        def run(self):
            try:
                self.progress.emit(0, "Connecting to server...")
                with requests.get(self.url, stream=True, timeout=60, verify=False) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    start = time.time()

                    with open(self.dest, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if self.cancelled:
                                self.finished.emit(False, "Cancelled")
                                return
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                elapsed = time.time() - start

                                if total > 0:
                                    pct = int((downloaded / total) * 90)
                                    speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                                    remaining_bytes = total - downloaded
                                    eta = remaining_bytes / (downloaded / elapsed) if downloaded > 0 else 0
                                    eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta/60)}m {int(eta%60)}s"
                                    mb_done = downloaded / 1024 / 1024
                                    mb_total = total / 1024 / 1024
                                    status = f"Downloading... {mb_done:.1f} / {mb_total:.1f} MB  •  {speed:.1f} MB/s  •  ETA {eta_str}"
                                else:
                                    mb_done = downloaded / 1024 / 1024
                                    status = f"Downloading... {mb_done:.1f} MB"
                                    pct = -1

                                self.progress.emit(pct, status)

                self.progress.emit(92, "Verifying download...")
                actual = sha256(self.dest)

                if actual != expected_sha:
                    os.remove(self.dest)
                    self.finished.emit(False, "Checksum verification failed. Please try again.")
                    return

                self.progress.emit(100, "Download complete!")
                self.finished.emit(True, "")

            except Exception as e:
                self.finished.emit(False, str(e))

    class UpdateDialog(QDialog):
        def __init__(self, version):
            super().__init__()
            self.setWindowTitle("Updating PremediaApp")
            self.setFixedSize(480, 200)
            self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.result_success = False
            self.result_message = ""

            self.setStyleSheet("""
                QDialog {
                    background: #1a1a2e;
                    border: 1px solid #16213e;
                }
                QLabel#title {
                    color: #e94560;
                    font-size: 15px;
                    font-weight: bold;
                }
                QLabel#status {
                    color: #a8b2d8;
                    font-size: 11px;
                }
                QProgressBar {
                    border: none;
                    border-radius: 4px;
                    background: #16213e;
                    height: 10px;
                    text-align: center;
                    color: transparent;
                }
                QProgressBar::chunk {
                    border-radius: 4px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e94560, stop:1 #0f3460);
                }
                QPushButton {
                    background: #16213e;
                    color: #a8b2d8;
                    border: 1px solid #0f3460;
                    border-radius: 4px;
                    padding: 4px 16px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #0f3460; }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(24, 20, 24, 20)
            layout.setSpacing(12)

            title = QLabel(f"Updating to version {version}")
            title.setObjectName("title")
            layout.addWidget(title)

            self.status_lbl = QLabel("Preparing download...")
            self.status_lbl.setObjectName("status")
            layout.addWidget(self.status_lbl)

            self.bar = QProgressBar()
            self.bar.setRange(0, 100)
            self.bar.setValue(0)
            layout.addWidget(self.bar)

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self._cancel)
            btn_row.addWidget(self.cancel_btn)
            layout.addLayout(btn_row)

            self._cancelled = False

        def set_thread(self, thread):
            self._thread = thread
            thread.progress.connect(self._on_progress)
            thread.finished.connect(self._on_finished)
            thread.start()

        def _on_progress(self, pct, text):
            self.status_lbl.setText(text)
            if pct >= 0:
                self.bar.setValue(pct)
            else:
                self.bar.setRange(0, 0)  # indeterminate

        def _on_finished(self, success, message):
            self.result_success = success
            self.result_message = message
            self.bar.setRange(0, 100)
            if success:
                self.bar.setValue(100)
                self.status_lbl.setText("Verified! Launching installer...")
            else:
                self.status_lbl.setText(f"Failed: {message}")
            self.cancel_btn.setText("Close")
            QApplication.processEvents()
            time.sleep(1)
            self.accept()

        def _cancel(self):
            if hasattr(self, '_thread') and self._thread.isRunning():
                self._thread.cancelled = True
                self.status_lbl.setText("Cancelling...")
                self.cancel_btn.setEnabled(False)
            else:
                self.reject()

    # ── Determine install path ────────────────────────────────────────────
    # Install next to the current exe so PyInstaller can find its _internal folder
    exe_dir = os.path.dirname(os.path.abspath(exe_path))

    if os_type == "Windows":
        # Download to a temp location first, then launch from there
        # The updater.exe will copy it to the install dir and relaunch
        tmp_dest = os.path.join(tempfile.gettempdir(), f"PremediaApp_v{latest_version}.exe")
    elif os_type == "Darwin":
        tmp_dest = os.path.join(tempfile.gettempdir(), f"PremediaApp_v{latest_version}.dmg")
    else:
        QMessageBox.critical(None, "Update Error", f"Unsupported OS: {os_type}")
        return

    dialog = UpdateDialog(latest_version)
    thread = DownloadThread(download_url, tmp_dest)
    dialog.set_thread(thread)
    dialog.exec()

    if not dialog.result_success:
        if dialog.result_message and dialog.result_message != "Cancelled":
            QMessageBox.critical(None, "Update Failed", dialog.result_message)
        return

    # ── Launch platform updater ───────────────────────────────────────────
    if os_type == "Windows":
        updater_path = os.path.join(exe_dir, "updater.exe")
        if not os.path.exists(updater_path):
            QMessageBox.critical(None, "Update Error", f"Missing updater.exe at:\n{updater_path}")
            return

        print(f"[Updater] Launching updater.exe: {updater_path}")
        subprocess.Popen(
            [updater_path, tmp_dest, exe_path],
            close_fds=True,
            shell=False
        )
        time.sleep(1)
        sys.exit(0)

    elif os_type == "Darwin":
        updater_path = os.path.join(exe_dir, "updater.sh")
        if not os.path.exists(updater_path):
            QMessageBox.critical(None, "Update Error", "Missing updater.sh")
            return

        subprocess.Popen(["bash", updater_path, tmp_dest, exe_path])
        sys.exit(0)
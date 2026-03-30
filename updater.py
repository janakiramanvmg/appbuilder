import os
import sys
import time
import tempfile
import subprocess
import logging
import psutil
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QProgressBar,
    QFrame, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont


# =========================
# Setup Robust Logging (for support/debug)
# =========================
log_file = os.path.join(tempfile.gettempdir(), "PremediaApp_Updater.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("Updater")


# =========================
# Update Worker (Background - Extremely Safe)
# =========================
class UpdateWorker(QThread):
    status = Signal(str)
    step_complete = Signal(int)      # 1 = kill done, 2 = launch done
    error = Signal(str)
    success = Signal()

    def __init__(self, new_exe: str, old_exe: str):
        super().__init__()
        self.new_exe = Path(new_exe).resolve()
        self.old_exe = Path(old_exe).resolve()

    def run(self):
        try:
            log.info(f"Updater started | New: {self.new_exe} | Old: {self.old_exe}")

            # Step 1: Kill old process (with retries + fallback)
            self.status.emit("Closing previous version...")
            self._kill_old_process()

            # Step 2: Small safety delay + verification
            time.sleep(1.5)
            if self.old_exe.exists():
                self._force_kill_fallback()

            self.step_complete.emit(1)
            self.status.emit("Launching new version...")

            # Step 3: Launch new executable
            time.sleep(0.8)
            self._launch_new_version()

            self.step_complete.emit(2)
            self.status.emit("✅ Update completed successfully!")
            time.sleep(1.2)
            self.success.emit()

        except Exception as e:
            log.error(f"Critical error: {e}", exc_info=True)
            self.error.emit(str(e))

    def _kill_old_process(self):
        """Primary kill using psutil + 3 retries"""
        exe_name = self.old_exe.name.lower()
        killed = False

        for attempt in range(3):
            for proc in psutil.process_iter(["name", "pid", "exe"]):
                try:
                    p_name = (proc.info.get("name") or "").lower()
                    p_exe = (proc.info.get("exe") or "").lower()

                    if exe_name in p_name or str(self.old_exe).lower() in p_exe:
                        if proc.pid == os.getpid():
                            continue
                        log.info(f"Terminating PID {proc.pid}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed:
                break
            time.sleep(0.8)

    def _force_kill_fallback(self):
        """Windows fallback using taskkill"""
        log.warning("psutil kill insufficient → using taskkill fallback")
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", self.old_exe.name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(1)
        except Exception as e:
            log.error(f"taskkill fallback failed: {e}")

    def _launch_new_version(self):
        """Launch with full error checking"""
        if not self.new_exe.exists():
            raise FileNotFoundError(f"New executable not found: {self.new_exe}")

        log.info(f"Launching new version: {self.new_exe}")
        try:
            subprocess.Popen(
                [str(self.new_exe)],
                shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        except Exception as e:
            log.error(f"Failed to launch new version: {e}")
            raise


# =========================
# Main UI Window (Modern & Clean)
# =========================
class UpdaterWindow(QWidget):
    def __init__(self, new_exe: str, old_exe: str):
        super().__init__()
        self.setWindowTitle("PremediaApp — Updating")
        self.setFixedSize(480, 260)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Modern styling
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; font-family: "Segoe UI", Arial; }
            QLabel { color: #222; }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;
                background: #f0f0f0;
                height: 14px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:1 #2a7ac0);
                border-radius: 7px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(35, 35, 35, 35)

        title = QLabel("Updating PremediaApp")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("Preparing update...")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # indeterminate
        layout.addWidget(self.progress)

        # Step indicator
        self.step_label = QLabel("Step 1 of 3")
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.step_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        # Footer
        footer = QLabel("Please keep this window open.\nThe app will restart automatically.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #555; font-size: 9px;")
        layout.addWidget(footer)

        # Worker
        self.worker = UpdateWorker(new_exe, old_exe)
        self.worker.status.connect(self.update_status)
        self.worker.step_complete.connect(self.update_step)
        self.worker.success.connect(self.on_success)
        self.worker.error.connect(self.on_error)

        # Start after window appears
        QTimer.singleShot(250, self.worker.start)

    def update_status(self, text: str):
        self.status_label.setText(text)
        log.info(f"UI Status: {text}")

    def update_step(self, step: int):
        self.step_label.setText(f"Step {step} of 3")

    def on_success(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        QTimer.singleShot(1200, self.close)

    def on_error(self, msg: str):
        log.error(f"User-visible error: {msg}")
        QMessageBox.critical(
            self,
            "Update Error",
            f"The update could not be completed.\n\nError: {msg}\n\n"
            f"A log file was saved to:\n{log_file}\n\n"
            "Please send this log to support if the problem continues."
        )
        self.close()


# =========================
# Entry Point (Exactly same as before)
# =========================
def main():
    if len(sys.argv) < 3:
        QMessageBox.critical(None, "Error", "Updater was launched with incorrect parameters.")
        sys.exit(1)

    new_exe = sys.argv[1]
    old_exe = sys.argv[2]

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = UpdaterWindow(new_exe, old_exe)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
# updater.py
import os
import sys
import time
import shutil
import psutil
import subprocess

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal


class UpdateWorker(QThread):
    status = Signal(str)
    progress = Signal(int)
    done = Signal(bool, str)   # success, message

    def __init__(self, new_exe, old_exe):
        super().__init__()
        self.new_exe = new_exe   # downloaded temp exe
        self.old_exe = old_exe   # currently running exe (install location)

    def kill_old_process(self):
        exe_name = os.path.basename(self.old_exe)
        self.status.emit(f"Closing {exe_name}...")
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if proc.info["name"] and exe_name.lower() in proc.info["name"].lower():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass

    def run(self):
        try:
            # ── 1. Kill old process ───────────────────────────────────────
            self.kill_old_process()
            self.progress.emit(20)
            time.sleep(1)

            # ── 2. Determine install destination ─────────────────────────
            # The new exe must be placed exactly where the old one was
            # so PyInstaller can find its _internal folder sibling
            install_dir = os.path.dirname(os.path.abspath(self.old_exe))
            exe_name = os.path.basename(self.old_exe)
            dest_exe = os.path.join(install_dir, exe_name)

            self.status.emit("Installing update...")
            self.progress.emit(40)

            # ── 3. Back up old exe ────────────────────────────────────────
            backup = dest_exe + ".bak"
            if os.path.exists(dest_exe):
                try:
                    shutil.copy2(dest_exe, backup)
                except Exception:
                    pass  # non-fatal

            # ── 4. Copy new exe into install location ─────────────────────
            # This is the critical fix — new exe must run from its own dir,
            # not from the temp folder where it was downloaded
            shutil.copy2(self.new_exe, dest_exe)
            self.progress.emit(70)

            # ── 5. Clean up downloaded temp file ─────────────────────────
            try:
                os.remove(self.new_exe)
            except Exception:
                pass

            # ── 6. Remove backup if copy succeeded ───────────────────────
            try:
                if os.path.exists(backup):
                    os.remove(backup)
            except Exception:
                pass

            self.status.emit("Launching new version...")
            self.progress.emit(90)
            time.sleep(0.5)

            # ── 7. Launch from install dir (NOT from temp) ────────────────
            # cwd must be the install directory so PyInstaller bootloader
            # finds the _internal folder — this is what fixes the
            # "Cannot respawn self, not named.exe" error
            subprocess.Popen(
                [dest_exe],
                cwd=install_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.progress.emit(100)
            self.status.emit("Update complete!")
            time.sleep(1)
            self.done.emit(True, "")

        except Exception as e:
            # ── Rollback on failure ───────────────────────────────────────
            backup = os.path.join(
                os.path.dirname(os.path.abspath(self.old_exe)),
                os.path.basename(self.old_exe) + ".bak"
            )
            if os.path.exists(backup):
                try:
                    shutil.copy2(backup, self.old_exe)
                except Exception:
                    pass

            self.done.emit(False, str(e))


class UpdaterWindow(QWidget):
    def __init__(self, new_exe, old_exe):
        super().__init__()
        self.setWindowTitle("Updating PremediaApp")
        self.setFixedSize(460, 160)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        self.setStyleSheet("""
            QWidget {
                background: #1a1a2e;
            }
            QLabel#title {
                color: #e2e8f0;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#status {
                color: #94a3b8;
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("Installing Update")
        title.setObjectName("title")
        layout.addWidget(title)

        self.status_lbl = QLabel("Preparing...")
        self.status_lbl.setObjectName("status")
        layout.addWidget(self.status_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        self.worker = UpdateWorker(new_exe, old_exe)
        self.worker.status.connect(self.status_lbl.setText)
        self.worker.progress.connect(self.bar.setValue)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_done(self, success, message):
        if not success:
            self.status_lbl.setText(f"Update failed: {message}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Update Failed", message)
        self.close()


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    new_exe = sys.argv[1]   # downloaded temp exe path
    old_exe = sys.argv[2]   # current install path

    app = QApplication(sys.argv)
    window = UpdaterWindow(new_exe, old_exe)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
import os
import sys
import time
import shutil
import subprocess
import psutil

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal


# ==================================================
# Utility: Kill running app safely
# ==================================================
def kill_process_by_path(exe_path: str, timeout=5):
    exe_name = os.path.basename(exe_path).lower()

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if not proc.info["name"]:
                continue

            # match by name OR full path
            if (
                proc.info["name"].lower() == exe_name
                or (proc.info["exe"] and proc.info["exe"].lower() == exe_path.lower())
            ):
                proc.terminate()
        except Exception:
            pass

    # wait for termination
    start = time.time()
    while time.time() - start < timeout:
        still_running = False
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == exe_name:
                    still_running = True
                    break
            except Exception:
                pass

        if not still_running:
            return

        time.sleep(0.5)

    # force kill if still alive
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == exe_name:
                proc.kill()
        except Exception:
            pass


# ==================================================
# Worker Thread
# ==================================================
class UpdateWorker(QThread):
    status = Signal(str)
    finished_signal = Signal()

    def __init__(self, new_exe, old_exe):
        super().__init__()
        self.new_exe = os.path.abspath(new_exe)
        self.old_exe = os.path.abspath(old_exe)

    def validate(self):
        if not os.path.exists(self.new_exe):
            raise RuntimeError(f"New EXE not found: {self.new_exe}")

        if not self.old_exe.lower().endswith(".exe"):
            raise RuntimeError(f"Invalid target EXE: {self.old_exe}")

    def atomic_replace(self):
        target_dir = os.path.dirname(self.old_exe)
        backup_path = self.old_exe + ".bak"

        # backup old exe
        if os.path.exists(self.old_exe):
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(self.old_exe, backup_path)

        # move new exe into place
        shutil.move(self.new_exe, self.old_exe)

        # cleanup backup (optional)
        if os.path.exists(backup_path):
            os.remove(backup_path)

    def launch(self):
        subprocess.Popen(
            [self.old_exe],
            cwd=os.path.dirname(self.old_exe),
            close_fds=True
        )

    def run(self):
        try:
            self.status.emit("Validating update...")
            self.validate()

            self.status.emit("Closing running application...")
            kill_process_by_path(self.old_exe)

            time.sleep(1)

            self.status.emit("Replacing application files...")

            # retry logic for file lock
            for attempt in range(3):
                try:
                    self.atomic_replace()
                    break
                except PermissionError:
                    time.sleep(1)
                    if attempt == 2:
                        raise

            self.status.emit("Launching updated version...")
            time.sleep(1)

            self.launch()

            self.status.emit("Update completed successfully")
            time.sleep(1)

        except Exception as e:
            self.status.emit(f"Update failed: {str(e)}")

        finally:
            self.finished_signal.emit()


# ==================================================
# UI
# ==================================================
class UpdaterWindow(QWidget):
    def __init__(self, new_exe, old_exe):
        super().__init__()

        self.setWindowTitle("Updating PremediaApp")
        self.setFixedSize(420, 140)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint)

        self.label = QLabel("Preparing update...")
        self.label.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)

        self.worker = UpdateWorker(new_exe, old_exe)
        self.worker.status.connect(self.update_status)
        self.worker.finished_signal.connect(self.close)

        self.worker.start()

    def update_status(self, text):
        self.label.setText(text)


# ==================================================
# Entry
# ==================================================
def main():
    if len(sys.argv) < 3:
        print("Usage: updater.exe <new_exe_path> <installed_exe_path>")
        sys.exit(1)

    new_exe = sys.argv[1]
    old_exe = sys.argv[2]

    app = QApplication(sys.argv)
    window = UpdaterWindow(new_exe, old_exe)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
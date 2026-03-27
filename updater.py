import os
import sys
import time
import shutil
import subprocess
import psutil
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal


# ==================================================
# Logger (persistent file logging)
# ==================================================
LOG_FILE = os.path.join(os.getcwd(), "updater.log")


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ==================================================
# Kill process safely
# ==================================================
def kill_process_by_path(exe_path: str, timeout=5):
    exe_name = os.path.basename(exe_path).lower()
    log(f"Killing process: {exe_name}")

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if not proc.info["name"]:
                continue

            if (
                proc.info["name"].lower() == exe_name
                or (proc.info["exe"] and proc.info["exe"].lower() == exe_path.lower())
            ):
                log(f"Terminating PID {proc.pid}")
                proc.terminate()
        except Exception as e:
            log(f"Process terminate error: {e}")

    start = time.time()
    while time.time() - start < timeout:
        still_running = False
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == exe_name:
                    still_running = True
                    break
            except:
                pass

        if not still_running:
            log("Process terminated successfully")
            return

        time.sleep(0.5)

    log("Force killing remaining processes")
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == exe_name:
                proc.kill()
        except:
            pass


# ==================================================
# Worker
# ==================================================
class UpdateWorker(QThread):
    status = Signal(str)
    finished_signal = Signal()

    def __init__(self, new_exe, old_exe):
        super().__init__()
        self.new_exe = os.path.abspath(new_exe)
        self.old_exe = os.path.abspath(old_exe)

    def validate(self):
        log(f"NEW EXE: {self.new_exe}")
        log(f"OLD EXE: {self.old_exe}")

        if not os.path.exists(self.new_exe):
            raise RuntimeError(f"New EXE not found: {self.new_exe}")

        if not self.old_exe.lower().endswith(".exe"):
            raise RuntimeError(f"Invalid target EXE: {self.old_exe}")

    def atomic_replace(self):
        backup = self.old_exe + ".bak"

        log("Starting atomic replace")

        if os.path.exists(self.old_exe):
            log("Creating backup")
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(self.old_exe, backup)

        log("Moving new EXE into place")
        shutil.move(self.new_exe, self.old_exe)

        log("Replace completed")

        if os.path.exists(backup):
            os.remove(backup)
            log("Backup removed")

    def launch(self):
        log(f"Launching: {self.old_exe}")

        subprocess.Popen(
            [self.old_exe],
            cwd=os.path.dirname(self.old_exe),
            close_fds=True
        )

    def run(self):
        try:
            self.status.emit("Validating update...")
            self.validate()

            self.status.emit("Closing application...")
            kill_process_by_path(self.old_exe)

            time.sleep(1)

            self.status.emit("Replacing files...")

            for i in range(3):
                try:
                    self.atomic_replace()
                    break
                except PermissionError as e:
                    log(f"Retry {i+1} due to lock: {e}")
                    time.sleep(1)
                    if i == 2:
                        raise

            self.status.emit("Launching new version...")
            time.sleep(1)

            self.launch()

            self.status.emit("Update completed")
            log("Update completed successfully")

        except Exception as e:
            log(f"UPDATE FAILED: {str(e)}")
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
    log("=== UPDATER STARTED ===")

    if len(sys.argv) < 3:
        log("Invalid arguments")
        sys.exit(1)

    new_exe = sys.argv[1]
    old_exe = sys.argv[2]

    app = QApplication(sys.argv)
    window = UpdaterWindow(new_exe, old_exe)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
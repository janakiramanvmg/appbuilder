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
# Logger
# ==================================================
def get_log_path():
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(exe_dir, "updater.log")


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ==================================================
# Admin check (debug only)
# ==================================================
def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# ==================================================
# Kill process
# ==================================================
def kill_process(exe_path):
    exe_name = os.path.basename(exe_path).lower()
    log(f"Killing process: {exe_name}")

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == exe_name:
                log(f"Terminate PID {proc.pid}")
                proc.terminate()
        except Exception as e:
            log(f"Terminate error: {e}")

    time.sleep(3)

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == exe_name:
                log(f"Force kill PID {proc.pid}")
                proc.kill()
        except:
            pass

    log("Process cleanup done")


# ==================================================
# Worker
# ==================================================
class UpdateWorker(QThread):
    status = Signal(str)
    done = Signal()

    def __init__(self, new_exe, old_exe):
        super().__init__()
        self.new_exe = os.path.abspath(new_exe)
        self.old_exe = os.path.abspath(old_exe)

    def run(self):
        try:
            log("=== UPDATE START ===")
            log(f"ADMIN: {is_admin()}")
            log(f"NEW EXE: {self.new_exe}")
            log(f"OLD EXE: {self.old_exe}")

            if not os.path.exists(self.new_exe):
                raise RuntimeError("New EXE missing")

            if not self.old_exe.endswith(".exe"):
                raise RuntimeError("Invalid target EXE")

            self.status.emit("Closing application...")
            kill_process(self.old_exe)

            time.sleep(2)

            backup = self.old_exe + ".bak"

            self.status.emit("Replacing application...")

            for attempt in range(5):
                try:
                    log(f"Replace attempt {attempt+1}")

                    if os.path.exists(self.old_exe):
                        if os.path.exists(backup):
                            os.remove(backup)

                        os.rename(self.old_exe, backup)
                        log("Backup created")

                    shutil.move(self.new_exe, self.old_exe)
                    log("New EXE moved")

                    if os.path.exists(backup):
                        os.remove(backup)
                        log("Backup removed")

                    break

                except PermissionError as e:
                    log(f"Permission error: {e}")
                    time.sleep(2)

                    if attempt == 4:
                        raise

            self.status.emit("Launching updated app...")
            time.sleep(1)

            log(f"Launching: {self.old_exe}")

            subprocess.Popen(
                [self.old_exe],
                cwd=os.path.dirname(self.old_exe),
                close_fds=True
            )

            log("Update SUCCESS")

        except Exception as e:
            log(f"UPDATE FAILED: {e}")
            self.status.emit(f"Failed: {e}")

        finally:
            self.done.emit()


# ==================================================
# UI
# ==================================================
class UpdaterWindow(QWidget):
    def __init__(self, new_exe, old_exe):
        super().__init__()

        self.setWindowTitle("Updating PremediaApp")
        self.setFixedSize(420, 140)

        self.label = QLabel("Starting update...")
        self.label.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)

        self.worker = UpdateWorker(new_exe, old_exe)
        self.worker.status.connect(self.update_status)
        self.worker.done.connect(self.close)

        self.worker.start()

    def update_status(self, text):
        self.label.setText(text)


# ==================================================
# MAIN
# ==================================================
def main():
    log("=== UPDATER LAUNCHED ===")

    if len(sys.argv) < 3:
        log("Invalid arguments")
        sys.exit(1)

    new_exe = sys.argv[1]
    old_exe = sys.argv[2]

    app = QApplication(sys.argv)
    win = UpdaterWindow(new_exe, old_exe)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
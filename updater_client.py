import os
import sys
import time
import tempfile
import subprocess
import hashlib
import platform
import requests

from packaging.version import Version, InvalidVersion

VERSION_URL = (
    "https://vmg-premedia-22112023.s3.ap-southeast-2.amazonaws.com/application/drn/latest_version.json"
)


class DownloadProgress:
    """Small Tk progress window that does not create a Qt QApplication."""

    def __init__(self):
        self.root = None
        self.label = None
        self.progress = None

        try:
            import tkinter as tk
            from tkinter import ttk

            self.root = tk.Tk()
            self.root.title("PremediaApp Update")
            self.root.resizable(False, False)
            self.root.protocol("WM_DELETE_WINDOW", lambda: None)

            frame = ttk.Frame(self.root, padding=18)
            frame.pack(fill="both", expand=True)

            self.label = ttk.Label(frame, text="Downloading update...")
            self.label.pack(anchor="w", pady=(0, 10))

            self.progress = ttk.Progressbar(
                frame, orient="horizontal", length=380, mode="determinate"
            )
            self.progress.pack(fill="x")

            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = max(0, (self.root.winfo_screenwidth() - width) // 2)
            y = max(0, (self.root.winfo_screenheight() - height) // 2)
            self.root.geometry(f"+{x}+{y}")
            self.root.attributes("-topmost", True)
            self.root.update()
        except Exception as exc:
            print(f"[Updater] Progress window unavailable: {exc}")
            self.close()

    def update(self, downloaded, total):
        if self.root is None:
            return

        try:
            if total > 0:
                percent = min((downloaded / total) * 100, 100)
                self.progress.configure(mode="determinate", value=percent)
                self.label.configure(text=f"Downloading update... {percent:.1f}%")
            else:
                self.progress.configure(mode="indeterminate")
                self.progress.start(10)
                self.label.configure(text="Downloading update...")
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            self.close()

    def close(self):
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
        self.root = None


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
    """Display an updater error without creating a Qt application."""

    message = str(msg)
    try:
        if platform.system() == "Windows":
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10 | 0x0)
            return

        if platform.system() == "Darwin":
            script = (
                'display alert "' + title.replace('"', '\\"') + '" '
                'message "' + message.replace('"', '\\"') + '" as critical'
            )
            subprocess.run(["osascript", "-e", script], check=False)
            return

        from tkinter import messagebox

        messagebox.showerror(title, message)
    except Exception:
        print(f"[Updater] {title}: {message}")


def ask_user_to_update(latest):
    """Ask whether to update without creating the main app's Qt singleton."""

    title = "Update Available"
    message = f"A new version {latest} is available.\n\nDo you want to update now?"

    try:
        if platform.system() == "Windows":
            import ctypes

            # MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON1; IDYES == 6
            return ctypes.windll.user32.MessageBoxW(
                None, message, title, 0x04 | 0x20 | 0x0
            ) == 6

        if platform.system() == "Darwin":
            script = (
                'display dialog "' + message.replace('"', '\\"') + '" '
                'with title "Update Available" buttons {"No", "Yes"} '
                'default button "Yes" cancel button "No"'
            )
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            return result.returncode == 0 and "Yes" in result.stdout

        from tkinter import messagebox

        return bool(messagebox.askyesno(title, message))
    except Exception as exc:
        print(f"[Updater] Could not display update prompt: {exc}")
        return False


def check_for_update(current_version, exe_path):
    """
    Check S3 JSON for update and apply if needed.

    Returns:
        True  -> Continue opening the current application.
        False -> Current process is exiting for update.
    """

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
            return True

        latest_version = str(
            data.get("version", "")
        ).strip()

        if not latest_version:
            show_error(
                "Update Error",
                "Version information missing from server.",
            )
            return True

        print(
            f"[Updater] Current: {current_version} | "
            f"Latest: {latest_version}"
        )

        # ----------------------------------------------------------
        # Proper version comparison
        # ----------------------------------------------------------
        try:

            current_clean = normalize_version(
                current_version
            )

            latest_clean = normalize_version(
                latest_version
            )

            current_ver = Version(
                current_clean
            )

            latest_ver = Version(
                latest_clean
            )

            print(
                f"[Updater] Comparing: "
                f"{current_ver} -> {latest_ver}"
            )

            if latest_ver <= current_ver:

                print(
                    "[Updater] ✅ Already up to date."
                )

                return True

        except InvalidVersion as e:

            print(
                f"[Updater] Invalid version value: {e}"
            )

            show_error(
                "Update Error",
                f"Invalid version value:\n{e}",
            )

            return True

        # ----------------------------------------------------------
        # Ask user
        # ----------------------------------------------------------
        mandatory = bool(
            data.get("mandatory", False)
        )

        if not mandatory:

            user_wants_update = ask_user_to_update(
                latest_version
            )

            if not user_wants_update:

                print(
                    "[Updater] Update declined by user. "
                    "Continuing with current application."
                )

                # IMPORTANT:
                # Only exit the update check.
                # Main application should continue loading.
                return True

        # ----------------------------------------------------------
        # Select platform
        # ----------------------------------------------------------
        os_type = platform.system()

        if os_type == "Windows":

            platform_data = data.get(
                "windows",
                {},
            )

            tmp_filename = (
                "PremediaApp_update.exe"
            )

        elif os_type == "Darwin":

            platform_data = data.get(
                "mac",
                {},
            )

            tmp_filename = (
                "PremediaApp_update.dmg"
            )

        else:

            show_error(
                "Update Error",
                f"Unsupported OS: {os_type}",
            )

            return True

        download_url = str(
            platform_data.get(
                "url",
                "",
            )
        ).strip()

        expected_sha = str(
            platform_data.get(
                "sha256",
                "",
            )
        ).strip().lower()

        if not download_url or not expected_sha:

            show_error(
                "Update Error",
                (
                    "Invalid update metadata "
                    "for this platform.\n\n"
                    "Please contact support."
                ),
            )

            return True

        print(
            "[Updater] Download URL:",
            download_url,
        )

        tmp_file = os.path.join(
            tempfile.gettempdir(),
            tmp_filename,
        )

        print(
            "[Updater] Downloading update..."
        )

        # This progress window uses Tk, not Qt. Therefore clicking No (or an
        # update failure) can safely continue into PremediaApp(QApplication).
        progress_dialog = DownloadProgress()

        # ----------------------------------------------------------
        # Download update
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

                progress_dialog.update(0, total)

                with open(
                    tmp_file,
                    "wb",
                ) as f:

                    for chunk in resp.iter_content(
                        chunk_size=8192
                    ):

                        if not chunk:
                            continue

                        f.write(
                            chunk
                        )

                        downloaded += len(
                            chunk
                        )

                        progress_dialog.update(downloaded, total)

        finally:
            progress_dialog.close()

        print(
            f"[Updater] Downloaded to: "
            f"{tmp_file}"
        )

        # ----------------------------------------------------------
        # SHA256 verification
        # ----------------------------------------------------------
        actual_sha = sha256(
            tmp_file
        )

        print(
            f"[Updater] Expected SHA: "
            f"{expected_sha}"
        )

        print(
            f"[Updater] Actual SHA:   "
            f"{actual_sha}"
        )

        if actual_sha != expected_sha:

            try:
                os.remove(
                    tmp_file
                )

            except Exception:
                pass

            show_error(
                "Checksum Error",
                (
                    "Downloaded file failed "
                    "verification."
                ),
            )

            # Update failed, allow current app to continue.
            return True

        print(
            "[Updater] ✅ Checksum verified."
        )

        # ----------------------------------------------------------
        # Windows updater
        # ----------------------------------------------------------
        if os_type == "Windows":

            updater_path = os.path.join(
                os.path.dirname(
                    exe_path
                ),
                "updater.exe",
            )

            if not os.path.exists(
                updater_path
            ):

                show_error(
                    "Update Error",
                    (
                        "Missing updater.exe at:\n"
                        f"{updater_path}"
                    ),
                )

                return True

            print(
                "[Updater] Launching updater.exe"
            )

            subprocess.Popen(
                [
                    updater_path,
                    tmp_file,
                    exe_path,
                ],
                close_fds=True,
                shell=False,
            )

            time.sleep(
                2
            )

            # Updater has launched successfully.
            # Close old/current app so updater can replace it.
            sys.exit(0)

        # ----------------------------------------------------------
        # macOS updater
        # ----------------------------------------------------------
        elif os_type == "Darwin":

            updater_path = os.path.join(
                os.path.dirname(
                    exe_path
                ),
                "updater.sh",
            )

            if not os.path.exists(
                updater_path
            ):

                show_error(
                    "Update Error",
                    (
                        "Missing updater.sh at:\n"
                        f"{updater_path}"
                    ),
                )

                return True

            print(
                "[Updater] Launching updater.sh"
            )

            subprocess.Popen(
                [
                    "bash",
                    updater_path,
                    tmp_file,
                    exe_path,
                ]
            )

            # Updater has launched successfully.
            # Close old/current app.
            sys.exit(0)

    except SystemExit:
        # Intentional exit after updater launch.
        raise

    except Exception as e:

        print(
            f"[Updater] Update failed: {e}"
        )

        show_error(
            "Update Failed",
            str(e),
        )

        # If update check fails, do not block normal application startup.
        return True


# ==============================================================
# MAIN APPLICATION STARTUP EXAMPLE
# ==============================================================
#
# IMPORTANT:
#
# The updater deliberately does not create QApplication. This allows the
# existing PremediaApp(QApplication) class to start normally after No is
# selected or when the update check fails.
#
#
# --------------------------------------------------------------
# RESULTING UPDATE FLOW
# --------------------------------------------------------------
#
# No update:
#     continue and open current application
#
# Update available + NO:
#     skip update
#     continue and open current application
#
# Update available + YES:
#     download
#     verify SHA256
#     launch updater
#     exit current application
#
# Update-check error:
#     show error
#     continue and open current application
#
# ==============================================================

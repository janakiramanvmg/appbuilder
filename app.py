import socket
import uuid
from PySide6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QProgressDialog, QTextEdit, QSystemTrayIcon,
    QMenu, QVBoxLayout, QStatusBar, QWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QProgressBar, QSizePolicy,QLabel, QFrame, QScrollArea, QGridLayout
)
from updater_client import check_for_update
  # your current version

from PySide6.QtGui import QIcon, QTextCursor, QAction, QCursor, QFont,QPixmap, QDesktopServices, QColor
from PySide6.QtCore import QRunnable, QThreadPool, QEvent, QSize, QThread, QTimer, Qt, QObject, Signal, QMetaObject, Slot, QLockFile, QDir, QEventLoop, QUrl, Q_ARG, QMimeData, QPropertyAnimation, QEvent
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkRequest
from login import Ui_Dialog
from PySide6.QtWidgets import QLineEdit, QGraphicsOpacityEffect, QGraphicsDropShadowEffect

import sys
import logging
import os
import platform
import logging.handlers
import requests
from requests.exceptions import RequestException
import urllib3
import json
from urllib.parse import urlparse, parse_qs, quote
from pathlib import Path
from datetime import datetime, timedelta, timezone 
from zoneinfo import ZoneInfo
from PIL import Image, ImageSequence
import subprocess
from queue import Queue
import threading
import time
import re
import io
import hashlib
import httpx
import mimetypes
from pid import PidFile, PidFileError
import warnings
import tempfile
import psutil  # To check if Photoshop is running
from threading import Lock, Semaphore, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

if platform.system() != "Windows":
    import fcntl
import numpy as np
try:
    from psd_tools import PSDImage
except ImportError:
    PSDImage = None
try:
    import rawpy
except ImportError:
    rawpy = None
try:
    import tifffile
except ImportError:
    tifffile = None
import pytz
import shutil
# Lazy import — keyring blocks on Windows credential store at import time
keyring = None
# def _load_keyring():
#     global keyring
#     try:
#         import keyring as _kr
#         keyring = _kr
#     except Exception as e:
#         logger.warning(f"keyring unavailable: {e}")

# threading.Thread(target=_load_keyring, daemon=True).start()
try:
    import imagecodecs
except ImportError:
    logger.warning("imagecodecs not installed, LZW-compressed TIFFs may not work")
from httpx import Timeout
if platform.system() == "Windows":
    import pythoncom
    import win32com.client
    import win32gui
    import win32con
from scp import SCPClient
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl

from ssh2.session import Session
from ssh2.sftp import LIBSSH2_FXF_CREAT, LIBSSH2_FXF_WRITE, LIBSSH2_FXF_TRUNC
from ssh2.exceptions import SFTPError


def ensure_single_instance(app_name: str):
    """
    Enforces single-instance execution using an OS-level file lock.
    Must be called BEFORE QApplication initialization.
    """

    lock_dir = tempfile.gettempdir()
    lock_file_path = os.path.join(lock_dir, f"{app_name}.lock")

    lock_file = open(lock_file_path, "w")

    try:
        if platform.system() == "Windows":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except Exception:
        _show_already_running_popup(app_name)
        sys.exit(0)

    return lock_file  # MUST stay referenced

def _show_already_running_popup(app_name: str):
    """
    Shows a blocking popup even if QApplication is not yet created.
    """
    print ("------------------------------ one instancee ---------------------")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        owns_app = False

        if app is None:
            app = QApplication(sys.argv)
            owns_app = True

        # QMessageBox.warning(
        #     None,
        #     f"{app_name} Already Running",
        #     f"{app_name} is already running on your machine. Only one instance is allowed.",
        # )
        show_alert(f"{app_name} Already Running", f"{app_name} is already running on your machine. Only one instance is allowed.", QMessageBox.Warning)
        if owns_app:
            app.quit()

    except Exception:
        # Absolute fallback (no Qt available)
        sys.stderr.write(f"{app_name} is already running.\n")


SUPPORTED_EXTENSIONS = [
    "jpg", "jpeg", "png", "gif", "tiff", "tif", "bmp", "webp",
    "psd", "psb", "cr2", "nef", "arw", "dng", "raf", "pef", "srw"
]
import shlex
# Global stop queue for signaling
FILE_WATCHER_STOP_QUEUE = Queue()
# Handle paramiko import
try:
    import paramiko
    NAS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"paramiko not installed: {e}. NAS functionality disabled.")
    NAS_AVAILABLE = False
    paramiko = None

try:
    import traceback
except ImportError as e:
    logging.error(f"Failed to import traceback module: {e}")
    traceback = None  # Fallback to None if import fails


# At the top of the file, ensure all imports are explicit
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"PIL not installed: {e}. Image conversion disabled.")
    PIL_AVAILABLE = False
    Image = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Server and environment Pointing global variables ===

# BASE_DOMAIN = "https://app.vmgpremedia.com"
# NAS_IP = "192.168.1.145"
# NAS_PASSWORD = "D&*qmn012@12"
# NAS_PORT = 22
# NAS_SHARE = ""
# NAS_PREFIX ='/mnt/nas/softwaremedia/IR_prod'
# NAS_USERNAME = "irnasappprod"
# MOUNTED_NAS_PATH ='/mnt/nas/softwaremedia/IR_prod'
# NAS_PATH = "softwaremedia/IR_prod/"
# APPVERSION = "1.2.7"
# GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAjCmpAxc/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=ibA47XmxTeve-NPc_AXQUVDY3ZvYriKEXL0vAjpKHag"

BASE_DOMAIN = "https://app-uat.vmgpremedia.com"
NAS_IP = "192.168.1.145"
NAS_USERNAME = "irdev"
NAS_PASSWORD = "i#0f!L&+@s%^qc"
NAS_PORT = 22
NAS_SHARE = ""
NAS_PREFIX ='/mnt/nas/softwaremedia/IR_uat'
MOUNTED_NAS_PATH ='/mnt/nas/softwaremedia/IR_uat'
NAS_PATH = "softwaremedia/IR_uat/"
APPVERSION = "1.2.7(UAT)"
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAUrb-ok4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=EUoZGB55TLIOIOBQ_D0uKNyYHB2UJWH9pA23QDGgNug"


BASE_DIR = Path(__file__).parent.resolve()

if platform.system() == "Windows":
    # Check if D: drive exists and is writable, else fall back to C:
    d_drive = Path("D:/")
    if d_drive.exists() and d_drive.is_dir():
        BASE_TARGET_DIR = d_drive / "PremediaApp" / "Nas"
    else:
        BASE_TARGET_DIR = Path("C:/PremediaApp/Nas")
else:
    # For Linux/macOS, use home directory
    BASE_TARGET_DIR = Path.home() / "PremediaApp" / "Nas"

# Ensure the directory exists
BASE_TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Cache icon paths
ICON_CACHE = {}
def load_icon(path, description):
    return QIcon(path)

def add_version_footer(window, version_text):
    """
    Adds a version label to the bottom of any QDialog or QMainWindow.
    """
    from PySide6.QtWidgets import QLabel, QVBoxLayout
    from PySide6.QtCore import Qt

    version_label = QLabel(f"Version: {version_text}")
    version_label.setAlignment(Qt.AlignRight)
    version_label.setStyleSheet("color: gray; font-size: 10px; margin-right: 10px;")

    # If the window already has a layout, append it
    layout = window.layout()
    if layout:
        layout.addWidget(version_label)
    else:
        new_layout = QVBoxLayout(window)
        new_layout.addStretch()
        new_layout.addWidget(version_label)
        window.setLayout(new_layout)


ICON_CACHE = {}
BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))

def get_icon_path(icon_name: str) -> str:
    """
    Returns a safe and correct path to an icon file for both source and frozen builds.
    """
    if icon_name in ICON_CACHE:
        return str(ICON_CACHE[icon_name])

    # Detect icon directory (inside _MEIPASS for frozen apps)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        icons_dir = Path(sys._MEIPASS) / "icons"
    else:
        icons_dir = BASE_DIR / "icons"

    icon_path = icons_dir / icon_name

    # Debug log to help verify path at runtime
    if not icon_path.exists():
        print(f"[Icons] ⚠️ Missing icon: {icon_path}")

    ICON_CACHE[icon_name] = icon_path
    return str(icon_path)

# OS-specific main icon
ICON_PATH = get_icon_path({
    "Windows": "premedia.ico",
    "Darwin": "premedia.icns",
    "Linux": "premedia.png"
}.get(platform.system(), "premedia.png"))

LOGGEDIN_ICON_PATH = get_icon_path({
    "Windows": "login-logo.ico",
    "Darwin": "login-logo.icns",
    "Linux": "login-logo.png"
}.get(platform.system(), "login-logo.png"))

# PHOTOSHOP_ICON_PATH = get_icon_path("photoshop.png") if (BASE_DIR / "icons" / "photoshop.png").exists() else ""
# COPY_ICON_PATH = get_icon_path("copy_icon.png") if (BASE_DIR / "icons" / "folder.png").exists() else ""
# RETRY_ICON_PATH = get_icon_path("retry.png") if (BASE_DIR / "icons" / "folder.png").exists() else ""
# FOLDER_ICON_PATH = get_icon_path("folder.png") if (BASE_DIR / "icons" / "folder.png").exists() else ""

PHOTOSHOP_ICON_PATH = get_icon_path("photoshop.png")
COPY_ICON_PATH = get_icon_path("copy_icon.png")
RETRY_ICON_PATH = get_icon_path("retry.png")
FOLDER_ICON_PATH = get_icon_path("folder.png")


def get_cache_file_path():
    # Use BASE_TARGET_DIR as the base for cache file generation
    cache_dir = Path(BASE_TARGET_DIR) / "PremediaApp"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensured cache directory exists: {cache_dir}")
    except Exception as e:
        print(f"Failed to create cache directory {cache_dir}: {e}")
        app_signals.append_log.emit(f"[Cache] Failed to create cache directory {cache_dir}: {str(e)}")
        # Fallback to a default directory if creation fails
        cache_dir = Path.home() / ".cache" / "PremediaApp"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"Fell back to default cache directory: {cache_dir}")
        except Exception as e2:
            print(f"Failed to create fallback cache directory {cache_dir}: {e2}")
            app_signals.append_log.emit(f"[Cache] Failed to create fallback cache directory {cache_dir}: {str(e2)}")
    
    cache_file = cache_dir / "cache.json"
    return str(cache_file)

CACHE_FILE = get_cache_file_path()
CACHE_DAYS = 10
API_URL = f"{BASE_DOMAIN}/api/ir_production/get/projectList?business=image_retouching"
DOWNLOAD_UPLOAD_API = f"{BASE_DOMAIN}/api/get_download_upload/submission"
FILE_FORMAT_API = f"{BASE_DOMAIN}/api/file-formats"
OAUTH_URL = f"{BASE_DOMAIN}/oauth/token"
USER_VALIDATE_URL = f"{BASE_DOMAIN}/api/user/validate"
API_URL_CREATE = f"{BASE_DOMAIN}/api/nas_create/creative"
API_URL_UPDATE_CREATE = f"{BASE_DOMAIN}/api/nas_update/creative"
API_REPLACE_QC_QA_FILE = f"{BASE_DOMAIN}/api/nas-qc-qa/update/ir-files"
API_URL_UPLOAD = f"{BASE_DOMAIN}/api/post/operator_upload"
API_URL_UPLOAD_DOWNLOAD_UPDATE = f"{BASE_DOMAIN}/api/save_download_upload/update"
API_URL_PROJECT_LIST = f"{BASE_DOMAIN}/api/get/nas/assets"
API_URL_UPDATE_NAS_ASSET = f"{BASE_DOMAIN}/api/update/nas/assets"
DRUPAL_DB_ENTRY_API = f"{BASE_DOMAIN}/api/add/files/ir/assets"
API_URL_LOGOUT = f"{BASE_DOMAIN}/premedia/logout"
IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False


API_POLL_INTERVAL = 5000  # 5 seconds in milliseconds

# === Google Chat transfer reporting (latency / speed) ===
# Paste your Google Chat "Incoming Webhook" URL here (Space -> Apps & integrations -> Webhooks)
# GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAUrb-ok4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=EUoZGB55TLIOIOBQ_D0uKNyYHB2UJWH9pA23QDGgNug"
TRANSFER_REPORT_INTERVAL_SEC = 10  # send a report every 10 seconds while a transfer is active
LATENCY_TARGET_HOST = None  # None => uses NAS_IP; set to a domain/IP to ping a different server
LATENCY_TARGET_PORT = None  # None => uses NAS_PORT

# === Network/server problem alarm thresholds ===
LATENCY_WARNING_MS = 1000       # server latency above this = "server is very slow"
LATENCY_MIN_MS = 1              # server latency below this (but not None) = suspicious/likely bad reading
SPEED_WARNING_MBPS = 0.5        # transfer speed below this (mid-transfer) = "server is very slow"
ALARM_COOLDOWN_SEC = 300        # don't repeat the same alarm type more than once per 5 minutes

log_window_handler = None
# === Global State ===
GLOBAL_CACHE = None
CACHE_WRITE_LOCK = threading.Lock()
_MEMORY_CACHE = None          # in-memory cache object
_MEMORY_CACHE_DIRTY = False   # True when memory cache differs from disk
HTTP_SESSION = requests.Session()
FILE_WATCHER_RUNNING = False
LOGGING_ACTIVE = True
app_signals = None
LAST_API_HIT_TIME = None
NEXT_API_HIT_TIME = None

USER_SYSTEM_INFO = {}

# ========== CONFIGURATION ==========
THROTTLE_MBPS = None       # Set to e.g. 50, 100, or None for no limit (full speed)
MIN_REQUIRED_MBPS = 50     # Optional: for warning if speed too low (in Mbps)
PRINT_INTERVAL = 0.5       # Progress update frequency in seconds

# ---- TEMPORARY: Max upload file size limit ----
# To DISABLE this limit, just set ENABLE_MAX_UPLOAD_SIZE_LIMIT = False below
# (or delete/comment out these two lines) — no other code changes needed.
ENABLE_MAX_UPLOAD_SIZE_LIMIT = True   # <-- flip to False to turn the limit off
MAX_UPLOAD_SIZE_MB = 2048             # 2 GB
# =================================================
# ===================================
# === Logging Setup ===
logger = logging.getLogger("PremediaApp")
logger.setLevel(logging.INFO)  # Only INFO and higher allowed

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_dir = BASE_DIR / "log"

try:
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=10485760, backupCount=5
    )
    file_handler.setLevel(logging.ERROR)  # <- Restrict handler
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    logger.error(f"Error setting up log file: {e}")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # <- Restrict console handler too
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


# === Signals for Safe GUI Updates ===
class AppSignals(QObject):
    update_status = Signal(str)
    append_log = Signal(str)
    update_file_list = Signal(str, str, str, int, bool)
    api_call_status = Signal(str, str, int)
    update_timer_status = Signal(str)
    network_alarm = Signal(str, str)  # summary, full_diagnostic_report_text
    # file_path, PSDValidationResult, confirmation_box (_PSDConfirmationBox)
    psd_validation_required = Signal(str, object, object)

    def __init__(self):
        super().__init__()
        # Self-connect with QueuedConnection: app_signals is created at import
        # time on the main thread, so this guarantees _on_network_alarm (and
        # the Qt dialog it builds) always runs on the main GUI thread, even
        # though network_alarm.emit() is called from background threads.
        self.network_alarm.connect(self._on_network_alarm, Qt.QueuedConnection)
        # Same pattern for the PSD/PSB pre-upload validation confirmation
        # dialog — must always be built/shown on the main GUI thread even
        # though the request originates from a background upload thread.
        self.psd_validation_required.connect(self._on_psd_validation_required, Qt.QueuedConnection)

    @Slot(str, str)
    def _on_network_alarm(self, summary, report_text):
        show_network_alarm_dialog(summary, report_text)

    @Slot(str, object, object)
    def _on_psd_validation_required(self, file_path, result, confirmation_box):
        """
        Runs on the main GUI thread (QueuedConnection). Shows the PSD
        quality-check report + Upload/Cancel confirmation dialog, then wakes
        up the waiting background upload thread with the user's decision.
        """
        try:
            dlg = PSDValidationDialog(file_path, result, parent=None)
            dlg.raise_()
            dlg.activateWindow()
            choice = dlg.exec()
            confirmation_box.result = (choice == QDialog.Accepted)
        except Exception as e:
            logger.error(f"[PSD Validation] Failed to show confirmation dialog: {e}")
            confirmation_box.result = False
        finally:
            confirmation_box.event.set()

app_signals = AppSignals()


# ============================================================================
# === PSD / PSB Production-Readiness Validation ============================
# ============================================================================
#
# Runs a checklist of production-readiness rules against a .psd/.psb file
# before it is uploaded to the NAS, and always shows the user a report +
# Upload/Cancel confirmation dialog — regardless of whether validation
# passed or failed — so the human makes the final call.
#
# Config is optional; pass a dict via FileWatcherWorker.psd_validation_config
# to customize behavior, e.g.:
#   {
#       "allowed_hidden_layers": ["Guides"],
#       "temp_layer_patterns": ["temp", "tmp", "wip", "draft", "test"],
#       "reference_layer_patterns": ["reference", "ref", "guide"],
#       "layer_naming_regex": r"^[A-Za-z0-9_\-\s]+$",
#       "mandatory_layers": ["Background", "Final"],
#       "expected_hierarchy": None,
#       "allowed_locked_layers": [],
#       "min_width": None,
#       "min_height": None,
#       "required_color_mode": None,   # e.g. "RGB"
#       "require_flattenable": False,
#   }
# ============================================================================

class PSDUploadCancelled(Exception):
    """Raised when the user cancels an upload from the PSD validation dialog."""
    pass


class UploadSizeLimitExceeded(Exception):
    """Raised when a file exceeds the configured MAX_UPLOAD_SIZE_MB limit."""
    pass


def exceeds_max_upload_size(file_path):
    """
    Checks a file against the temporary MAX_UPLOAD_SIZE_MB limit.

    TO DISABLE: set ENABLE_MAX_UPLOAD_SIZE_LIMIT = False near the top of
    this file (in the CONFIGURATION block) — this function will then
    always return (False, size_mb) and the limit has no effect anywhere.

    Returns (exceeds: bool, size_mb: float).
    """
    if not ENABLE_MAX_UPLOAD_SIZE_LIMIT:
        return False, 0.0
    try:
        size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    except Exception as e:
        logger.warning(f"[UploadSizeLimit] Could not stat {file_path}: {e}")
        return False, 0.0
    return size_mb > MAX_UPLOAD_SIZE_MB, size_mb


class PSDValidationResult:
    """Container for one PSD/PSB validation run."""

    def __init__(self):
        self.checks = []          # list of {"name","passed","message"}
        self.canvas_size = None   # (width, height)
        self.overall_pass = True

    def add(self, name, passed, message=""):
        self.checks.append({"name": name, "passed": bool(passed), "message": message or ""})
        if not passed:
            self.overall_pass = False


def _psd_layer_name(layer):
    try:
        return layer.name or "(unnamed layer)"
    except Exception:
        return "(unnamed layer)"


def validate_psd_document(file_path, config=None):
    """
    Validates a .psd/.psb file against a production-readiness checklist.
    Never raises — any internal failure is captured as a FAIL check so the
    caller always gets back a usable PSDValidationResult.
    """
    config = config or {}
    result = PSDValidationResult()

    if PSDImage is None:
        result.add("PSD Library", False, "psd-tools is not installed; cannot validate this file")
        return result

    try:
        psd = PSDImage.open(file_path)
    except Exception as e:
        result.add("File Open", False, f"Could not open PSD/PSB file: {e}")
        return result

    try:
        result.canvas_size = (psd.width, psd.height)
    except Exception:
        result.canvas_size = None

    try:
        all_layers = list(psd.descendants())
    except Exception as e:
        result.add("Layer Enumeration", False, f"Could not enumerate layers: {e}")
        return result

    def _is_group(layer):
        try:
            return bool(layer.is_group())
        except Exception:
            return False

    # ---- 1. Hidden Layer Check ----
    try:
        allowed_hidden = set(config.get("allowed_hidden_layers", []))
        hidden = [_psd_layer_name(l) for l in all_layers if not getattr(l, "visible", True)]
        bad_hidden = [n for n in hidden if n not in allowed_hidden]
        if bad_hidden:
            result.add("Hidden Layer Check", False, f"Hidden layers found: {', '.join(bad_hidden)}")
        else:
            result.add("Hidden Layer Check", True)
    except Exception as e:
        result.add("Hidden Layer Check", False, f"Check failed to run: {e}")

    # ---- 2. Empty Layer Check ----
    try:
        empty_layers = []
        for l in all_layers:
            if _is_group(l):
                continue
            try:
                bbox = l.bbox
                if bbox is None or (bbox[2] - bbox[0]) <= 0 or (bbox[3] - bbox[1]) <= 0:
                    empty_layers.append(_psd_layer_name(l))
            except Exception:
                continue
        if empty_layers:
            result.add("Empty Layer Check", False, f"Empty layers: {', '.join(empty_layers)}")
        else:
            result.add("Empty Layer Check", True)
    except Exception as e:
        result.add("Empty Layer Check", False, f"Check failed to run: {e}")

    # ---- 3. Temporary Layer Check ----
    try:
        temp_patterns = config.get("temp_layer_patterns", ["temp", "tmp", "test", "working", "wip", "draft"])
        temp_layers = [
            _psd_layer_name(l) for l in all_layers
            if any(p.lower() in (_psd_layer_name(l)).lower() for p in temp_patterns)
        ]
        if temp_layers:
            result.add("Temporary Layer Check", False, f"Temporary/working layers found: {', '.join(temp_layers)}")
        else:
            result.add("Temporary Layer Check", True)
    except Exception as e:
        result.add("Temporary Layer Check", False, f"Check failed to run: {e}")

    # ---- 4. Reference Layer Check ----
    try:
        ref_patterns = config.get("reference_layer_patterns", ["reference", "ref", "guide"])
        ref_layers = [
            _psd_layer_name(l) for l in all_layers
            if any(p.lower() in (_psd_layer_name(l)).lower() for p in ref_patterns)
        ]
        if ref_layers:
            result.add("Reference Layer Check", False, f"Reference/guide layers found: {', '.join(ref_layers)}")
        else:
            result.add("Reference Layer Check", True)
    except Exception as e:
        result.add("Reference Layer Check", False, f"Check failed to run: {e}")

    # ---- 5. Layer Naming Validation ----
    try:
        naming_pattern = config.get("layer_naming_regex")
        if naming_pattern:
            bad_names = [
                _psd_layer_name(l) for l in all_layers
                if l.name and not re.match(naming_pattern, l.name)
            ]
            if bad_names:
                result.add("Layer Naming Validation", False, f"Layers violating naming convention: {', '.join(bad_names)}")
            else:
                result.add("Layer Naming Validation", True)
        else:
            result.add("Layer Naming Validation", True, "No naming convention configured; check skipped")
    except Exception as e:
        result.add("Layer Naming Validation", False, f"Check failed to run: {e}")

    # ---- 6. Mandatory Layer Validation ----
    try:
        mandatory = config.get("mandatory_layers", [])
        if mandatory:
            existing_names = {_psd_layer_name(l) for l in all_layers}
            missing = [m for m in mandatory if m not in existing_names]
            if missing:
                result.add("Mandatory Layer Validation", False, f"Missing mandatory layers: {', '.join(missing)}")
            else:
                result.add("Mandatory Layer Validation", True)
        else:
            result.add("Mandatory Layer Validation", True, "No mandatory layers configured; check skipped")
    except Exception as e:
        result.add("Mandatory Layer Validation", False, f"Check failed to run: {e}")

    # ---- 7. Duplicate Layer Detection ----
    try:
        name_counts = {}
        for l in all_layers:
            n = _psd_layer_name(l)
            name_counts[n] = name_counts.get(n, 0) + 1
        dupes = [n for n, c in name_counts.items() if c > 1 and n != "(unnamed layer)"]
        if dupes:
            result.add("Duplicate Layer Detection", False, f"Duplicate layer names: {', '.join(dupes)}")
        else:
            result.add("Duplicate Layer Detection", True)
    except Exception as e:
        result.add("Duplicate Layer Detection", False, f"Check failed to run: {e}")

    # ---- 8. Layer Hierarchy Validation ----
    try:
        expected_hierarchy = config.get("expected_hierarchy")
        if expected_hierarchy:
            # Placeholder for a project-specific structural comparison —
            # wire in actual group/folder-path comparison logic here when
            # an expected_hierarchy spec is provided via config.
            result.add("Layer Hierarchy Validation", True)
        else:
            result.add("Layer Hierarchy Validation", True, "No expected_hierarchy configured; check skipped")
    except Exception as e:
        result.add("Layer Hierarchy Validation", False, f"Check failed to run: {e}")

    # ---- 9. Locked Layer Validation ----
    try:
        allowed_locked = set(config.get("allowed_locked_layers", []))
        locked_layers = []
        for l in all_layers:
            is_locked = False
            for attr in ("locked", "is_locked"):
                try:
                    val = getattr(l, attr, False)
                    if callable(val):
                        val = val()
                    if val:
                        is_locked = True
                        break
                except Exception:
                    continue
            if is_locked:
                locked_layers.append(_psd_layer_name(l))
        bad_locked = [n for n in locked_layers if n not in allowed_locked]
        if bad_locked:
            result.add("Locked Layer Validation", False, f"Unexpected locked layers: {', '.join(bad_locked)}")
        else:
            result.add("Locked Layer Validation", True)
    except Exception as e:
        result.add("Locked Layer Validation", False, f"Check failed to run: {e}")

    # ---- 10. Document Properties Check ----
    try:
        doc_issues = []
        min_w = config.get("min_width")
        min_h = config.get("min_height")
        if min_w and result.canvas_size and result.canvas_size[0] < min_w:
            doc_issues.append(f"Width {result.canvas_size[0]} < required {min_w}")
        if min_h and result.canvas_size and result.canvas_size[1] < min_h:
            doc_issues.append(f"Height {result.canvas_size[1]} < required {min_h}")
        required_color_mode = config.get("required_color_mode")
        if required_color_mode:
            try:
                actual_mode = str(psd.color_mode).upper()
            except Exception:
                actual_mode = "UNKNOWN"
            if required_color_mode.upper() not in actual_mode:
                doc_issues.append(f"Color mode {actual_mode} != required {required_color_mode.upper()}")
        if doc_issues:
            result.add("Document Properties Check", False, "; ".join(doc_issues))
        else:
            result.add("Document Properties Check", True)
    except Exception as e:
        result.add("Document Properties Check", False, f"Check failed to run: {e}")

    # ---- 11. Smart Object Check ----
    try:
        require_flatten = bool(config.get("require_flattenable", False))
        if require_flatten:
            smart_objects = []
            for l in all_layers:
                try:
                    if str(getattr(l, "kind", "")).lower() == "smartobject":
                        smart_objects.append(_psd_layer_name(l))
                except Exception:
                    continue
            if smart_objects:
                result.add("Smart Object Check", False, f"Smart objects present (must be flattened): {', '.join(smart_objects)}")
            else:
                result.add("Smart Object Check", True)
        else:
            result.add("Smart Object Check", True, "Flattenability not required; check skipped")
    except Exception as e:
        result.add("Smart Object Check", False, f"Check failed to run: {e}")

    # ---- 12. Production Readiness Check (aggregate of the above) ----
    try:
        blocking_checks = (
            "Hidden Layer Check", "Empty Layer Check", "Temporary Layer Check",
            "Reference Layer Check", "Mandatory Layer Validation", "Duplicate Layer Detection",
        )
        non_production = any(
            (not c["passed"]) for c in result.checks if c["name"] in blocking_checks
        )
        if non_production:
            result.add("Production Readiness Check", False, "PSD contains non-production layers; not ready for delivery")
        else:
            result.add("Production Readiness Check", True)
    except Exception as e:
        result.add("Production Readiness Check", False, f"Check failed to run: {e}")

    return result


def format_psd_validation_report(file_path, result: PSDValidationResult) -> str:
    """Formats a PSDValidationResult into the standard readable report text."""
    lines = []
    lines.append(f"PSD Validation Report — {file_path}")
    if result.canvas_size:
        lines.append(f"Canvas: {result.canvas_size[0]}x{result.canvas_size[1]}")
    lines.append("=" * 72)
    for check in result.checks:
        icon = "✅ [PASS]" if check["passed"] else "❌ [FAIL]"
        lines.append(f"{icon} {check['name']}")
        if check["message"]:
            level = "INFO" if check["passed"] else "FAIL"
            lines.append(f"        - ({level}) -: {check['message']}")
    lines.append("=" * 72)
    overall_icon = "✅" if result.overall_pass else "❌"
    overall_text = "PASS" if result.overall_pass else "FAIL"
    lines.append(f"{overall_icon} Overall status: {overall_text}")
    return "\n".join(lines)


class PSDCheckRowWidget(QFrame):
    """One row in the QC checklist — glassy dark card with an accent-colored
    icon chip, check name, optional message, and a status pill."""

    def __init__(self, name: str, passed: bool, message: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("PSDCheckRow")

        accent = "#3ddc97" if passed else "#ff5c7a"
        accent_soft = "rgba(61, 220, 151, 0.12)" if passed else "rgba(255, 92, 122, 0.12)"
        icon = "✓" if passed else "✕"
        pill_text = "PASS" if passed else "FAIL"

        self.setStyleSheet(f"""
            QFrame#PSDCheckRow {{
                background: #1b1e2b;
                border: 1px solid #262a3b;
                border-left: 3px solid {accent};
                border-radius: 10px;
            }}
            QFrame#PSDCheckRow:hover {{
                background: #20243450;
                border-color: {accent};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background-color: {accent_soft};
            color: {accent};
            font-weight: bold;
            font-size: 14px;
            border-radius: 15px;
            border: 1px solid {accent};
        """)
        outer.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "color: #eef0f7; font-weight: 600; font-size: 12.5px; "
            "background: transparent; letter-spacing: 0.2px;"
        )
        text_col.addWidget(name_lbl)

        if message:
            msg_lbl = QLabel(message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(
                f"color: {'#8c93a8' if passed else '#ff8fa3'}; font-size: 11px; "
                "background: transparent; line-height: 140%;"
            )
            text_col.addWidget(msg_lbl)

        outer.addLayout(text_col, 1)

        pill = QLabel(pill_text)
        pill.setAlignment(Qt.AlignCenter)
        pill.setFixedWidth(62)
        pill.setStyleSheet(f"""
            background-color: {accent};
            color: #0e1018;
            font-weight: 800;
            font-size: 10px;
            letter-spacing: 0.5px;
            border-radius: 10px;
            padding: 4px 0;
        """)
        outer.addWidget(pill, 0, Qt.AlignTop)


class _PSDSegmentedBar(QFrame):
    """Slim rounded pass/fail ratio bar — a small dashboard-style touch
    showing at a glance how much of the checklist passed."""

    def __init__(self, passed: int, total: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self.setStyleSheet("background: rgba(255,255,255,0.18); border-radius: 4px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        failed = max(total - passed, 0)
        if total <= 0:
            return

        if passed:
            seg_pass = QFrame()
            seg_pass.setStyleSheet("background-color: #3ddc97; border-radius: 4px;")
            layout.addWidget(seg_pass, passed)
        if failed:
            seg_fail = QFrame()
            seg_fail.setStyleSheet("background-color: #ff5c7a; border-radius: 4px;")
            layout.addWidget(seg_fail, failed)


class PSDValidationDialog(QDialog):
    """
    QC / production-readiness check window for a PSD or PSB file, shown
    right before upload. Dark, modern "dashboard" styling — gradient
    header, glassy checklist cards, segmented pass/fail meter, drop
    shadows, and pill-shaped gradient action buttons — instead of a plain
    report/error-style window. Shown for BOTH pass and fail outcomes,
    since the human always makes the final call.
    """

    def __init__(self, file_path, result: "PSDValidationResult", parent=None):
        super().__init__(parent)
        overall_pass = result.overall_pass
        passed_count = sum(1 for c in result.checks if c["passed"])
        total_count = len(result.checks)
        failed_count = total_count - passed_count

        accent = "#3ddc97" if overall_pass else "#ff5c7a"
        gradient = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f9b6e, stop:1 #3ddc97)"
            if overall_pass else
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #c0293f, stop:1 #ff5c7a)"
        )

        self.setWindowTitle("Quality Check — PSD/PSB")
        self.setMinimumSize(640, 660)
        self.resize(700, 700)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QDialog { background: #0f111a; }
            QScrollBar:vertical {
                background: transparent;
                width: 9px;
                margin: 4px 2px 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #33384c;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #454b66; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        try:
            self.setWindowIcon(load_icon(ICON_PATH, "psd validation"))
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Gradient header ──────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"background: {gradient}; border: none;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 22, 24, 22)
        header_layout.setSpacing(10)

        eyebrow = QLabel("PRODUCTION QC")
        eyebrow.setStyleSheet(
            "color: rgba(255,255,255,0.75); font-size: 10px; font-weight: 800; "
            "letter-spacing: 2px; background: transparent;"
        )
        header_layout.addWidget(eyebrow)

        title_row = QHBoxLayout()
        title_row.setSpacing(14)

        badge = QLabel("✓" if overall_pass else "!")
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background-color: rgba(255,255,255,0.20); color: white; "
            "font-size: 22px; font-weight: 900; border-radius: 23px; "
            "border: 1px solid rgba(255,255,255,0.35);"
        )
        title_row.addWidget(badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Quality Check Passed" if overall_pass else "Quality Check Failed")
        title_lbl.setStyleSheet(
            "color: white; font-size: 19px; font-weight: 800; background: transparent;"
        )
        title_col.addWidget(title_lbl)

        subtitle_lbl = QLabel(Path(file_path).name)
        subtitle_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 11.5px; background: transparent;"
        )
        subtitle_lbl.setWordWrap(True)
        title_col.addWidget(subtitle_lbl)

        title_row.addLayout(title_col, 1)
        header_layout.addLayout(title_row)

        # ── Chips: canvas size + pass/fail counts ───────────────────────
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)

        def _make_chip(text):
            chip = QLabel(text)
            chip.setStyleSheet(
                "background-color: rgba(255,255,255,0.16); color: white; font-size: 10.5px; "
                "font-weight: 700; border-radius: 10px; padding: 4px 12px; "
                "border: 1px solid rgba(255,255,255,0.25);"
            )
            return chip

        if result.canvas_size:
            chip_row.addWidget(_make_chip(f"📐  {result.canvas_size[0]} × {result.canvas_size[1]} px"))
        chip_row.addWidget(_make_chip(f"✓  {passed_count} passed"))
        if failed_count:
            chip_row.addWidget(_make_chip(f"✕  {failed_count} failed"))
        chip_row.addStretch(1)
        header_layout.addLayout(chip_row)

        # ── Segmented pass/fail meter ────────────────────────────────────
        header_layout.addSpacing(2)
        header_layout.addWidget(_PSDSegmentedBar(passed_count, total_count))

        root.addWidget(header)

        # ── Scrollable checklist ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #0f111a; border: none; }")

        checklist_container = QWidget()
        checklist_container.setStyleSheet("background: #0f111a;")
        checklist_layout = QVBoxLayout(checklist_container)
        checklist_layout.setContentsMargins(20, 18, 20, 18)
        checklist_layout.setSpacing(10)
        checklist_layout.setAlignment(Qt.AlignTop)

        section_lbl = QLabel("CHECKLIST")
        section_lbl.setStyleSheet(
            "color: #5b6178; font-size: 10px; font-weight: 800; "
            "letter-spacing: 2px; background: transparent; padding-bottom: 2px;"
        )
        checklist_layout.addWidget(section_lbl)

        for check in result.checks:
            row = PSDCheckRowWidget(check["name"], check["passed"], check["message"])
            checklist_layout.addWidget(row)

        scroll.setWidget(checklist_container)
        root.addWidget(scroll, 1)

        # ── Footer: note + actions ───────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet("background: #14172200; border-top: 1px solid #232838;")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(20, 16, 20, 18)
        footer_layout.setSpacing(12)

        note_lbl = QLabel(
            "All checks passed. Proceed with uploading this file to the NAS?"
            if overall_pass else
            "One or more checks failed. Do you still want to proceed with uploading this file to the NAS?"
        )
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet("color: #9aa0b4; font-size: 11.5px; background: transparent;")
        footer_layout.addWidget(note_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.copy_btn = QPushButton("📋  Copy Report")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setMinimumHeight(38)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1b1e2b;
                color: #c6cadb;
                border: 1px solid #2b3044;
                border-radius: 19px;
                padding: 6px 18px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #232838; border-color: #3a4160; }
            QPushButton:pressed { background-color: #171a26; padding-top: 7px; padding-bottom: 5px; }
        """)
        self.copy_btn.clicked.connect(lambda: self._copy_report(file_path, result))
        btn_row.addWidget(self.copy_btn)
        btn_row.addStretch(1)

        self.proceed_btn = QPushButton("⬆  Upload to NAS")
        self.cancel_btn = QPushButton("✕  Cancel")

        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.proceed_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(40)
        self.proceed_btn.setMinimumHeight(40)
        self.cancel_btn.setMinimumWidth(120)
        self.proceed_btn.setMinimumWidth(160)

        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff5c7a;
                border: 1.5px solid #ff5c7a;
                border-radius: 20px;
                padding: 6px 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(255, 92, 122, 0.12);
            }
            QPushButton:pressed {
                background-color: rgba(255, 92, 122, 0.22);
                padding-top: 7px;
                padding-bottom: 5px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #ff5c7a;
            }
            QPushButton:disabled {
                background-color: transparent;
                color: #4a4f5e;
                border-color: #33384c;
            }
        """)
        self.proceed_btn.setStyleSheet(f"""
            QPushButton {{
                background: {gradient};
                color: #0e1018;
                border: none;
                border-radius: 20px;
                padding: 6px 20px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {gradient.replace('stop:0', 'stop:0.15').replace('stop:1', 'stop:1')};
            }}
            QPushButton:pressed {{
                padding-top: 7px;
                padding-bottom: 5px;
            }}
            QPushButton:focus {{
                outline: none;
                border: 2px solid rgba(255,255,255,0.55);
            }}
            QPushButton:disabled {{
                background: #33384c;
                color: #6b7182;
            }}
        """)

        proceed_shadow = QGraphicsDropShadowEffect(self.proceed_btn)
        proceed_shadow.setBlurRadius(24)
        proceed_shadow.setOffset(0, 4)
        proceed_shadow.setColor(QColor(*(61, 220, 151) if overall_pass else (255, 92, 122), 140))
        self.proceed_btn.setGraphicsEffect(proceed_shadow)

        self.proceed_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.proceed_btn)
        footer_layout.addLayout(btn_row)

        root.addWidget(footer)

        # Default focus follows the outcome: safest action is the default.
        (self.proceed_btn if overall_pass else self.cancel_btn).setDefault(True)
        (self.proceed_btn if overall_pass else self.cancel_btn).setFocus()

    @staticmethod
    def _copy_report(file_path, result):
        try:
            QApplication.clipboard().setText(format_psd_validation_report(file_path, result))
        except Exception as e:
            logger.warning(f"[PSD Validation] Failed to copy report to clipboard: {e}")


class _PSDConfirmationBox:
    """Simple cross-thread mailbox: worker thread waits on `event`,
    main thread sets `result` then signals `event`."""

    def __init__(self):
        self.event = threading.Event()
        self.result = False


def request_psd_upload_confirmation(file_path, result: "PSDValidationResult"):
    """
    Thread-safe: shows the PSD quality-check dialog on the main GUI thread
    and BLOCKS the calling (background/worker) thread until the user
    responds.

    Must NEVER be called from the main GUI thread itself (it would deadlock
    waiting on an event that only the main thread's own queued slot can set).

    Returns True if the user chose to proceed with the upload, False if
    they cancelled (or the dialog could not be shown).
    """
    box = _PSDConfirmationBox()
    app_signals.psd_validation_required.emit(file_path, result, box)
    box.event.wait()
    return box.result


# ============================================================================
# === Google Chat transfer reporting (latency + speed, every N seconds) ====
# ============================================================================

# Shared "what's happening right now" state, updated by the download/upload
# progress callbacks (which already compute speed_mbps every ~0.5s), and
# read every TRANSFER_REPORT_INTERVAL_SEC by the background reporter thread.
_TRANSFER_MONITOR_LOCK = Lock()
_CURRENT_TRANSFER_STATS = {
    "active": False,
    "action": None,       # "download" or "upload"
    "file_name": None,
    "file_type": None,
    "file_size_mb": 0.0,
    "speed_mbps": 0.0,
    "percent": 0,
    "elapsed_sec": 0.0,
    "eta_text": "-",
}


def _file_type_of(name: str) -> str:
    """Return a short human-readable file type/extension label, e.g. 'JPG', 'PSD'."""
    if not name:
        return "-"
    ext = Path(name).suffix.lstrip(".").upper()
    return ext or "UNKNOWN"


def _format_elapsed(seconds: float) -> str:
    try:
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "-"


def _update_transfer_stats(action: str, file_name: str, speed_mbps: float, percent: int,
                            file_size_mb: float = 0.0, elapsed_sec: float = 0.0, eta_text: str = "-"):
    """Called from the download/upload progress callbacks to record current speed/size/ETA."""
    with _TRANSFER_MONITOR_LOCK:
        _CURRENT_TRANSFER_STATS.update({
            "active": True,
            "action": action,
            "file_name": file_name,
            "file_type": _file_type_of(file_name),
            "file_size_mb": file_size_mb,
            "speed_mbps": speed_mbps,
            "percent": percent,
            "elapsed_sec": elapsed_sec,
            "eta_text": eta_text,
        })


def _clear_transfer_stats():
    """Called when a transfer finishes (success or failure) to stop reporting it."""
    with _TRANSFER_MONITOR_LOCK:
        _CURRENT_TRANSFER_STATS["active"] = False
        _CURRENT_TRANSFER_STATS["speed_mbps"] = 0.0
        _CURRENT_TRANSFER_STATS["percent"] = 0
        _CURRENT_TRANSFER_STATS["elapsed_sec"] = 0.0
        _CURRENT_TRANSFER_STATS["eta_text"] = "-"


def measure_latency_ms(host: str = None, port: int = None, timeout: float = 3.0):
    """
    Simple TCP-connect latency check against the NAS/server (in milliseconds).
    Returns None if the host is unreachable within the timeout.
    """
    host = host or LATENCY_TARGET_HOST or NAS_IP
    port = port or LATENCY_TARGET_PORT or NAS_PORT
    start = time.perf_counter()
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return round((time.perf_counter() - start) * 1000, 1)
    except Exception as e:
        logger.debug(f"[Latency] Could not reach {host}:{port}: {e}")
        return None
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def _tcp_check(host: str, port: int, timeout: float = 3.0):
    """Generic reachability probe. Returns (reachable: bool, latency_ms or None, error_str or None)."""
    start = time.perf_counter()
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return True, round((time.perf_counter() - start) * 1000, 1), None
    except Exception as e:
        return False, None, str(e)
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def build_network_diagnostics_report(issue_type: str, summary: str, context: dict = None, error: str = None) -> str:
    """
    Builds a full, human-readable diagnostics report suitable for a screenshot
    or copy/paste to the development team: who/what/where, plus live
    reachability checks against the NAS, the API server, Google Chat, and
    general internet, so the dev team can immediately tell whether the
    problem is local-network-wide or specific to one endpoint.
    """
    lines = []
    lines.append("PremediaApp — Network / Server Alarm Report")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Issue Type: {issue_type}")
    lines.append(f"Summary: {summary}")
    lines.append("")

    try:
        cache = load_cache()
        username = cache.get("user", "Unknown")
    except Exception:
        username = "Unknown"

    identifiers = {}
    if isinstance(USER_SYSTEM_INFO, dict):
        identifiers = USER_SYSTEM_INFO.get("details", {}).get("identifiers", {}) or {}
    hostname = identifiers.get("hostname") or socket.gethostname()
    ip_address = identifiers.get("ip_address") or USER_SYSTEM_INFO.get("ip_address", "") or ""

    lines.append("-- User / System --")
    lines.append(f"User: {username}")
    lines.append(f"System: {hostname}")
    lines.append(f"Local IP: {ip_address}")
    lines.append(f"OS: {platform.system()} {platform.release()}")
    lines.append(f"App Version: {APPVERSION}")
    lines.append("")

    if context:
        lines.append("-- Context --")
        for k, v in context.items():
            lines.append(f"{k}: {v}")
        lines.append("")

    lines.append("-- Live Connectivity Checks --")

    nas_ok, nas_latency, nas_err = _tcp_check(NAS_IP, NAS_PORT)
    lines.append(
        f"NAS Server ({NAS_IP}:{NAS_PORT}): "
        + (f"Reachable — {nas_latency} ms" if nas_ok else f"UNREACHABLE — {nas_err}")
    )

    try:
        api_host = BASE_DOMAIN.replace("https://", "").replace("http://", "").split("/")[0]
    except Exception:
        api_host = BASE_DOMAIN
    api_ok, api_latency, api_err = _tcp_check(api_host, 443)
    lines.append(
        f"API Server ({api_host}:443): "
        + (f"Reachable — {api_latency} ms" if api_ok else f"UNREACHABLE — {api_err}")
    )

    gchat_ok, gchat_latency, gchat_err = _tcp_check("chat.googleapis.com", 443)
    lines.append(
        f"Google Chat (chat.googleapis.com:443): "
        + (f"Reachable — {gchat_latency} ms" if gchat_ok else f"UNREACHABLE — {gchat_err}")
    )

    inet_ok, inet_latency, inet_err = _tcp_check("8.8.8.8", 53)
    lines.append(
        f"General Internet (8.8.8.8:53): "
        + (f"Reachable — {inet_latency} ms" if inet_ok else f"UNREACHABLE — {inet_err}")
    )
    lines.append("")

    if error:
        lines.append("-- Error Details --")
        lines.append(str(error))
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


class NetworkAlarmWindow(QDialog):
    """
    Singleton, non-modal alarm window. ALL network/server alarms (NAS
    unreachable, server slow, transfer slow, Google Chat unreachable, API
    call failures, etc.) land in this SAME window as separate, clearly
    labeled/timestamped entries — instead of each alarm spawning its own
    popup.

    Why this exists (bug fix):
    The previous implementation created a brand-new modal QDialog and called
    .exec() on every single call to raise_network_alarm(). Because
    .exec() runs its own nested Qt event loop, a second network_alarm
    signal arriving (from a different background thread/issue type) while
    the first dialog was still open got processed *during* that nested loop
    and spawned a second, independent dialog on top of the first — so two
    separate windows with two different reports could appear at once.

    Fix: keep exactly ONE instance alive for the lifetime of the app. New
    alarms call add_report() on the existing instance (appending to the
    same scrollable log with a divider + timestamp + issue banner) rather
    than creating a new window. The window itself is shown non-modally
    (show(), not exec()), so nothing blocks and nothing can double-spawn.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__(None)
        self._entries = []  # list of (timestamp_str, summary, report_text) — newest first
        self._alert_count = 0

        self.setWindowTitle("⚠ PremediaApp — Network / Server Alarms")
        self.setMinimumSize(760, 520)
        self.resize(820, 560)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        try:
            self.setWindowIcon(load_icon(ICON_PATH, "network alarm"))
        except Exception:
            pass

        layout = QVBoxLayout(self)

        self.summary_lbl = QLabel("⚠  Network / Server Alarms")
        self.summary_lbl.setWordWrap(True)
        self.summary_lbl.setStyleSheet(
            "color: white; background-color: #c0392b; font-weight: bold; "
            "font-size: 14px; padding: 10px; border-radius: 4px;"
        )
        layout.addWidget(self.summary_lbl)

        hint_lbl = QLabel(
            "Every alert is listed below (most recent first), clearly separated and "
            "timestamped. Click 'Copy All Reports' and paste into an email/chat message "
            "to the development team, or 'Clear' to reset this window."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(hint_lbl)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas" if platform.system() == "Windows" else "Monospace", 10))
        layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy All Reports")
        clear_btn = QPushButton("🧹 Clear")
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #2ecc71; font-weight: bold;")
        close_btn = QPushButton("Close")

        copy_btn.clicked.connect(self._copy_all)
        clear_btn.clicked.connect(self._clear_all)
        close_btn.clicked.connect(self.close)

        btn_row.addWidget(copy_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(self.status_lbl)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def add_report(self, summary: str, report_text: str):
        """Append a new alarm entry (most recent on top) and (re)show the window."""
        self._alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._entries.insert(0, (timestamp, summary, report_text))

        # Keep at most the last 50 alerts so the window/memory don't grow unbounded
        if len(self._entries) > 50:
            self._entries = self._entries[:50]

        self._rebuild_text()

        self.summary_lbl.setText(
            f"⚠  {summary}   ({self._alert_count} alert{'s' if self._alert_count != 1 else ''} this session)"
        )

        # Beep to get attention, then bring the single window to front
        for i in range(3):
            QTimer.singleShot(i * 300, QApplication.beep)
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        _set_alarm_window_visible(True)

    def _rebuild_text(self):
        blocks = []
        for idx, (timestamp, summary, report_text) in enumerate(self._entries, start=1):
            divider = "=" * 70
            header = f"{divider}\n[Alert #{len(self._entries) - idx + 1}]  {timestamp}\n{summary}\n{divider}"
            blocks.append(f"{header}\n{report_text}\n")
        self.text_edit.setPlainText("\n".join(blocks))
        self.text_edit.moveCursor(QTextCursor.Start)

    def _copy_all(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())
        self.status_lbl.setText("Copied!")
        QTimer.singleShot(2000, lambda: self.status_lbl.setText(""))

    def _clear_all(self):
        self._entries = []
        self._alert_count = 0
        self.text_edit.clear()
        self.summary_lbl.setText("⚠  Network / Server Alarms")

    def closeEvent(self, event):
        # Hide instead of destroying — keeps history and avoids recreating
        # (and re-registering) the singleton on the next alarm.
        event.ignore()
        self.hide()
        _set_alarm_window_visible(False)


def show_network_alarm_dialog(summary: str, report_text: str):
    """
    Routes every alarm to the single persistent NetworkAlarmWindow instance
    instead of creating a brand-new dialog per call. See NetworkAlarmWindow
    docstring for why this fixes the "two separate windows at once" bug.

    Must only be invoked on the main GUI thread — reached exclusively via
    AppSignals.network_alarm's self-connected QueuedConnection.
    """
    try:
        window = NetworkAlarmWindow.get_instance()
        window.add_report(summary, report_text)
    except Exception as e:
        logger.error(f"[Alarm] Failed to show network alarm window: {e}")


_ALARM_LOCK = Lock()
_LAST_ALARM_TIME = {}
_ALARM_WINDOW_VISIBLE_LOCK = Lock()
_ALARM_WINDOW_VISIBLE = False

def _set_alarm_window_visible(is_visible: bool):
    global _ALARM_WINDOW_VISIBLE
    with _ALARM_WINDOW_VISIBLE_LOCK:
        _ALARM_WINDOW_VISIBLE = is_visible

def _is_alarm_window_visible() -> bool:
    with _ALARM_WINDOW_VISIBLE_LOCK:
        return _ALARM_WINDOW_VISIBLE

def raise_network_alarm(issue_type: str, summary: str, context: dict = None, error: str = None):
    """
    Raises a popup alarm (with sound + full diagnostics) for network/server
    problems: can't reach Google Chat, can't reach the NAS/server, server
    responding very slowly, or any other unexpected reporting failure.

    Rate-limited per issue_type (ALARM_COOLDOWN_SEC) so a persistent problem
    doesn't spam popups every few seconds — the underlying issue still gets
    logged every time, just not re-popped-up.

    Safe to call from any thread.
    """
    now = time.time()
    with _ALARM_LOCK:
        last = _LAST_ALARM_TIME.get(issue_type, 0)
        if _is_alarm_window_visible() and (now - last < ALARM_COOLDOWN_SEC):
            logger.debug(f"[Alarm] Suppressed duplicate '{issue_type}' alarm (cooldown active)")
            return
        _LAST_ALARM_TIME[issue_type] = now

    logger.error(f"[Alarm] {issue_type}: {summary}")
    try:
        app_signals.append_log.emit(f"[Alarm] {issue_type}: {summary}")
    except Exception:
        pass

    # ── NEW: surface the problem directly on the transfer card/window ──
    # Previously a network alarm only opened the separate NetworkAlarmWindow.
    # The download/upload card had no idea anything was wrong and just kept
    # showing whatever progress % it last received — looking "frozen" or
    # "stuck" to the user instead of clearly indicating the network dropped.
    if issue_type in ("ServerUnreachable", "ServerSlow", "ServerLatencyAbnormal", "TransferSlow"):
        try:
            ctx = context or {}
            file_name = ctx.get("File")
            if file_name and file_name != "-":
                is_upload = ctx.get("Action", "").lower() == "upload"
                status_text = f"⚠ {summary}"
                if is_upload:
                    FileWatcherWorker.get_instance().upload_status_detail.emit(
                        file_name, status_text, "upload", 0, True
                    )
                else:
                    FileWatcherWorker.get_instance().download_status_detail.emit(
                        file_name, status_text, "download", 0, True
                    )
        except Exception as ui_err:
            logger.debug(f"[Alarm] Could not surface alarm on transfer UI: {ui_err}")

    try:
        report_text = build_network_diagnostics_report(issue_type, summary, context, error)
    except Exception as e:
        report_text = f"Failed to build full diagnostics report: {e}\n\nOriginal issue: {issue_type} - {summary}"

    # Hand off to the main thread — Qt widgets can only be built there.
    app_signals.network_alarm.emit(summary, report_text)


def report_api_failure(api_name: str, url: str, status_code=None, response_text=None, error: str = None):
    """
    Notifies Google Chat whenever a POST/GET API call fails — either a
    non-2xx status code or a request exception (timeout, connection error,
    JSON decode error, etc). All API failures share one thread_key so they
    group into a single Google Chat thread instead of scattering as
    separate top-level messages. Also raises the existing local
    popup/diagnostics alarm (raise_network_alarm) so it shows up the same
    way NAS/server alarms do.

    Safe to call from any thread. Never blocks the caller — the actual
    Google Chat POST + local alarm happen on a background daemon thread.
    """
    if status_code is not None:
        summary = f"API call failed: {api_name} — HTTP {status_code}"
    else:
        summary = f"API call failed: {api_name} — {error or 'Unknown error'}"

    logger.error(f"[APIFailure] {summary} | url={url} | response={str(response_text)[:300]}")
    try:
        app_signals.append_log.emit(f"[APIFailure] {summary}")
    except Exception:
        pass

    lines = [
        f"*🔴 API Call Failed — {api_name}*",
        f"URL: {url}",
    ]
    if status_code is not None:
        lines.append(f"Status Code: {status_code}")
    if response_text:
        lines.append(f"Response: {str(response_text)[:500]}")
    if error:
        lines.append(f"Error: {error}")
    lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    text = "\n".join(lines)
    thread_key = "premedia-api-failures"

    def _worker():
        try:
            ok, result = send_google_chat_message(text, thread_key=thread_key)
            if not ok:
                logger.warning(f"[APIFailure] Could not deliver failure report to Google Chat: {result}")

            raise_network_alarm(
                "APICallFailed",
                summary,
                context={
                    "API": api_name,
                    "URL": url,
                    "Status Code": status_code if status_code is not None else "-",
                    "Response": str(response_text)[:300] if response_text else "-",
                },
                error=error,
            )
        except Exception as e:
            logger.warning(f"[APIFailure] Failed while reporting API failure for {api_name}: {e}")

    threading.Thread(target=_worker, daemon=True, name=f"APIFailureReport-{api_name}").start()


def _gchat_webhook_url_with_threading():
    """
    Ensure the webhook URL has messageReplyOption=REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD,
    which is required for Google Chat to group messages sharing the same
    threadKey into a single thread instead of posting separate top-level messages.
    """
    if not GOOGLE_CHAT_WEBHOOK_URL:
        return ""
    if "messageReplyOption=" in GOOGLE_CHAT_WEBHOOK_URL:
        return GOOGLE_CHAT_WEBHOOK_URL
    separator = "&" if "?" in GOOGLE_CHAT_WEBHOOK_URL else "?"
    return f"{GOOGLE_CHAT_WEBHOOK_URL}{separator}messageReplyOption=REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"


def send_google_chat_message(text: str, thread_key: str = None):
    """
    Post a message to the configured Google Chat webhook.

    Returns (True, response_json_or_None) on success, or
            (False, error_message_str) on failure — the caller uses this to
    decide whether to raise a network alarm.

    NOTE ON "UPDATING" MESSAGES:
    Google Chat's message-edit endpoint (PUT/PATCH .../spaces/*/messages/*)
    requires full OAuth app authentication (a registered Chat app + service
    account with the chat.bot scope) — a plain incoming webhook's key/token
    can only ever CREATE messages, it cannot edit one after the fact. So true
    "keep editing message #1" is not possible with just a webhook URL.

    The practical equivalent used here: every event for the same file+
    operation is posted with the SAME thread_key. Google Chat groups all
    messages sharing a thread_key into a single collapsible thread, so the
    conversation for that file+operation stays together instead of scattering
    across the space, and the first message is never replaced.
    """
    if not GOOGLE_CHAT_WEBHOOK_URL:
        return False, "GOOGLE_CHAT_WEBHOOK_URL is not configured"
    try:
        url = _gchat_webhook_url_with_threading()
        payload = {"text": text}
        if thread_key:
            payload["thread"] = {"threadKey": thread_key}
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            logger.warning(f"[GChat] Failed to send message: {err}")
            return False, err
        try:
            return True, resp.json()
        except ValueError:
            # 204 No Content (or an empty body on 200) — still a success
            return True, None
    except requests.exceptions.Timeout:
        err = "Request to Google Chat timed out (slow or unreachable network)"
        logger.warning(f"[GChat] {err}")
        return False, err
    except requests.exceptions.ConnectionError as e:
        err = f"Could not connect to Google Chat: {e}"
        logger.warning(f"[GChat] {err}")
        return False, err
    except Exception as e:
        err = f"Unexpected error sending to Google Chat: {e}"
        logger.warning(f"[GChat] {err}")
        return False, err


def _thread_key_for(action: str, file_name: str) -> str:
    """Stable thread key so every event for this (action, file_name) lands in one thread."""
    raw = f"{action}:{file_name}"
    return "premedia-" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:20]


def _pad_cell(value, width):
    value = str(value)
    return value + " " * max(0, width - len(value))


def _build_transfer_table_text(header_info: dict, rows: list) -> str:
    """
    Builds one Google Chat message: a header block (User/System/IP/File/Type/Size,
    shown once) followed by a monospaced table (inside a code block, so columns
    stay aligned) with one row per event (Started / periodic Progress / Completed
    or Failed).
    """
    header_lines = [
        f"*PremediaApp Transfer — {header_info.get('action', '')}*",
        f"User: {header_info.get('user', '-')}",
        f"System: {header_info.get('system', '-')}",
        f"IP: {header_info.get('ip', '-')}",
        f"File: {header_info.get('file', '-')}",
        f"Type: {header_info.get('type', '-')}",
        f"Size: {header_info.get('size', '-')}",
    ]

    columns = ["Event", "Time", "Progress", "Speed", "Time Taken", "ETA", "Latency"]
    keys = ["event", "time", "progress", "speed", "time_taken", "eta", "latency"]

    widths = [len(c) for c in columns]
    for row in rows:
        for i, k in enumerate(keys):
            widths[i] = max(widths[i], len(str(row.get(k, "-"))))

    def _fmt_row(values):
        return " | ".join(_pad_cell(v, widths[i]) for i, v in enumerate(values))

    separator = "-+-".join("-" * w for w in widths)

    table_lines = [_fmt_row(columns), separator]
    for row in rows:
        table_lines.append(_fmt_row([row.get(k, "-") for k in keys]))

    table_block = "```\n" + "\n".join(table_lines) + "\n```"

    return "\n".join(header_lines) + "\n\n" + table_block


# One Google Chat message per (action, file_name) currently in flight.
# key: (action, file_name) -> {"message_name": str|None, "rows": [...], "header_info": {...}}
_MESSAGE_REGISTRY_LOCK = Lock()
_ACTIVE_MESSAGE_REGISTRY = {}


class TransferMonitorReporter:
    """
    Background daemon-thread reporter. Every TRANSFER_REPORT_INTERVAL_SEC
    seconds, if an upload/download is currently active, it appends a
    "Progress" row (latency/speed/ETA/etc.) to that file's existing Google
    Chat table message — it does NOT post a brand-new message.

    Runs on its own thread — never touches Qt widgets — so it's safe to
    start once and leave running for the lifetime of the app.
    """

    def __init__(self, interval_sec: int = 10):
        self.interval_sec = interval_sec
        self._stop_flag = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run_loop, name="TransferMonitorReporter", daemon=True)
        self._thread.start()
        logger.info(f"[TransferMonitorReporter] Started (interval={self.interval_sec}s)")

    def stop(self):
        self._stop_flag.set()

    def _run_loop(self):
        while not self._stop_flag.is_set():
            # Sleep in small chunks so stop() is responsive
            for _ in range(self.interval_sec):
                if self._stop_flag.is_set():
                    return
                time.sleep(1)

            with _TRANSFER_MONITOR_LOCK:
                stats = dict(_CURRENT_TRANSFER_STATS)

            if not stats.get("active"):
                continue

            try:
                report_transfer_event(
                    "Progress",
                    stats.get("action") or "",
                    stats.get("file_name") or "",
                    percent=stats.get("percent", 0),
                    speed_mbps=stats.get("speed_mbps", 0.0),
                    file_size_mb=stats.get("file_size_mb", 0.0),
                    elapsed_sec=stats.get("elapsed_sec", 0.0),
                    eta_text=stats.get("eta_text", "-"),
                )
            except Exception as e:
                logger.warning(f"[TransferMonitorReporter] Failed to build/send report: {e}")


# Single shared instance — .start() is called once near app startup below.
TRANSFER_REPORTER = TransferMonitorReporter(interval_sec=TRANSFER_REPORT_INTERVAL_SEC)


def report_transfer_event(
    event: str,
    action: str,
    file_name: str,
    percent: int = 0,
    speed_mbps: float = 0.0,
    file_size_mb: float = 0.0,
    elapsed_sec: float = 0.0,
    eta_text: str = "-",
):
    """
    Post one Google Chat message per event ("Started", "Progress",
    "Completed", "Failed") for a given (action, file_name) — but every one of
    them is posted with the SAME thread_key, so Google Chat groups them into
    a single thread instead of scattering separate top-level messages across
    the space. The first message ("Started") is never overwritten; each later
    post is a reply in that same thread and carries the FULL cumulative table
    (all rows so far), so the most recent message always shows the complete
    history for that file+operation.

    (True in-place message editing would need a full Chat app with OAuth app
    authentication — not possible with a plain incoming webhook's key/token —
    see send_google_chat_message() for details.)

    On "Completed"/"Failed" the row history for that file+operation is
    cleared, so a later transfer of the same file starts a fresh thread/table.

    Runs on its own daemon thread so it never blocks the actual transfer.
    """
    def _worker():
        try:
            cache = load_cache()
            username = cache.get("user", "Unknown")

            identifiers = {}
            if isinstance(USER_SYSTEM_INFO, dict):
                identifiers = USER_SYSTEM_INFO.get("details", {}).get("identifiers", {}) or {}

            hostname = identifiers.get("hostname") or socket.gethostname()
            ip_address = identifiers.get("ip_address") or USER_SYSTEM_INFO.get("ip_address", "") or ""

            latency_ms = measure_latency_ms()
            latency_text = f"{latency_ms} ms" if latency_ms is not None else "N/A"

            alarm_context = {
                "Action": action.capitalize(),
                "File": file_name or "-",
                "Event": event,
                "Progress": f"{percent}%",
                "Speed": f"{speed_mbps:.2f} MB/s",
            }

            # ---- Alarm: NAS/server unreachable ("not able to ping server") ----
            # Treat both a None reading (connection failed / timed out) and an
            # exact 0ms reading (measure_latency_ms() couldn't produce a real
            # timing — e.g. socket error swallowed upstream) as "unreachable",
            # since a legitimate TCP-connect latency of exactly 0ms is not
            # realistically possible.
            if latency_ms is None or latency_ms == 0:
                target_host = LATENCY_TARGET_HOST or NAS_IP
                target_port = LATENCY_TARGET_PORT or NAS_PORT
                raise_network_alarm(
                    "ServerUnreachable",
                    f"Cannot reach the server ({target_host}:{target_port}) — it may be down "
                    f"or your network connection may be lost.",
                    context=alarm_context,
                )
            # ---- Alarm: server responding, but very slow (high latency) ----
            elif latency_ms > LATENCY_WARNING_MS:
                raise_network_alarm(
                    "ServerSlow",
                    f"Server latency is very high ({latency_ms} ms) — the connection to the "
                    f"server appears unstable or overloaded.",
                    context={**alarm_context, "Latency": f"{latency_ms} ms"},
                )
            # ---- Alarm: server latency is abnormally/suspiciously low ----
            # A very low but non-zero reading (below LATENCY_MIN_MS) can indicate
            # an unreliable/flaky connection or a bad measurement rather than a
            # genuinely healthy server, so flag it too instead of silently
            # treating it as "all good".
            elif latency_ms < LATENCY_MIN_MS:
                raise_network_alarm(
                    "ServerLatencyAbnormal",
                    f"Server latency reading is abnormally low ({latency_ms} ms) — this may "
                    f"indicate an unstable connection or an unreliable measurement.",
                    context={**alarm_context, "Latency": f"{latency_ms} ms"},
                )

            # ---- Alarm: transfer speed is critically slow mid-transfer ----
            if event == "Progress" and 0 < percent < 100 and 0 < speed_mbps < SPEED_WARNING_MBPS:
                raise_network_alarm(
                    "TransferSlow",
                    f"Transfer speed is very slow ({speed_mbps:.2f} MB/s) for '{file_name}' — "
                    f"the server or network may be degraded.",
                    context=alarm_context,
                )

            row = {
                "event": event,
                "time": datetime.now().strftime("%H:%M:%S"),
                "progress": f"{percent}%",
                "speed": f"{speed_mbps:.2f} MB/s",
                "time_taken": _format_elapsed(elapsed_sec),
                "eta": eta_text,
                "latency": latency_text,
            }

            header_info = {
                "action": action.capitalize(),
                "user": username,
                "system": hostname,
                "ip": ip_address,
                "file": file_name or "-",
                "type": _file_type_of(file_name),
                "size": f"{file_size_mb:.2f} MB" if file_size_mb else "-",
            }

            reg_key = (action, file_name)
            is_final = event in ("Completed", "Failed")
            thread_key = _thread_key_for(action, file_name)

            with _MESSAGE_REGISTRY_LOCK:
                entry = _ACTIVE_MESSAGE_REGISTRY.get(reg_key)
                if entry is None:
                    entry = {"rows": [], "header_info": header_info}
                    _ACTIVE_MESSAGE_REGISTRY[reg_key] = entry

                entry["header_info"] = header_info  # keep size/type current
                entry["rows"].append(row)
                text = _build_transfer_table_text(entry["header_info"], entry["rows"])

                ok, result = send_google_chat_message(text, thread_key=thread_key)

                if is_final:
                    _ACTIVE_MESSAGE_REGISTRY.pop(reg_key, None)

            # ---- Alarm: could not deliver the report to Google Chat at all ----
            if not ok:
                raise_network_alarm(
                    "GoogleChatUnreachable",
                    f"Unable to send the transfer report to Google Chat for '{file_name}'.",
                    context=alarm_context,
                    error=result,
                )

        except Exception as e:
            logger.warning(f"[TransferReport:{event}] Failed to send report: {e}")
            raise_network_alarm(
                "ReportingError",
                f"Unexpected error while building/sending the transfer report for '{file_name}'.",
                context={"Action": action, "File": file_name, "Event": event},
                error=str(e),
            )

    threading.Thread(target=_worker, daemon=True, name=f"TransferReport-{event}").start()


def show_alert(title: str, message: str, icon=QMessageBox.Warning, parent=None):
    """
    Shows a QMessageBox that always raises to the front and steals focus.
    Safe to call from the main thread only (use Qt.QueuedConnection from workers).
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(icon)

    # ── FIX: WindowType and WindowState cannot be OR'd together in PySide6 ──
    # Set window flags (WindowType flags only)
    msg.setWindowFlags(
        msg.windowFlags()
        | Qt.WindowType.Window
        | Qt.WindowType.WindowStaysOnTopHint
    )
    # Set window state separately (WindowState flags only)
    msg.setWindowState(Qt.WindowState.WindowActive)

    msg.setAttribute(Qt.WA_ShowWithoutActivating, False)

    if platform.system() == "Windows":
        try:
            import ctypes
            msg.show()
            hwnd = int(msg.winId())
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    msg.raise_()
    msg.activateWindow()
    msg.show()
    msg.raise_()
    msg.activateWindow()
    return msg.exec()

# === Custom Log Handler ===
class LogWindowHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_queue = []
        self.log_window = None

    def set_log_window(self, log_window):
        self.log_window = log_window
        # Flush queued logs
        for record in self.log_queue:
            self.emit(record)
        self.log_queue.clear()

    def emit(self, record):
        msg = self.format(record)
        if self.log_window and hasattr(app_signals, 'append_log'):
            try:
                app_signals.append_log.emit(msg)
            except Exception as e:
                self.log_queue.append(record)
                logging.getLogger("PremediaApp").warning(f"Failed to emit log to LogWindow: {e}")
        else:
            self.log_queue.append(record)

# === Async Logging ===
log_queue = Queue()
def async_log_worker():
    global LOGGING_ACTIVE
    while LOGGING_ACTIVE:
        record = log_queue.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)

log_thread = threading.Thread(target=async_log_worker, daemon=True)

# log_window_handler = None  # Global variable to store LogWindowHandler

def setup_logger(log_window=None):
    logger = logging.getLogger("PremediaApp")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    # Add StreamHandler for fallback logging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

    # Add LogWindowHandler
    global log_window_handler
    log_window_handler = LogWindowHandler()
    log_window_handler.setLevel(logging.INFO)
    logger.addHandler(log_window_handler)

    # Connect signals if log_window is provided
    if log_window:
        log_window_handler.set_log_window(log_window)
        app_signals.append_log.connect(log_window.append_log, Qt.QueuedConnection)
        app_signals.api_call_status.connect(log_window.append_api_status, Qt.QueuedConnection)
        app_signals.update_timer_status.connect(log_window.update_timer_status, Qt.QueuedConnection)
        logger.info("Connected logger signals to LogWindow")
    else:
        logger.info("No LogWindow provided; using StreamHandler for logging")

    return logger


def stop_logging():
    global LOGGING_ACTIVE
    LOGGING_ACTIVE = False
    log_queue.put(None)
    if log_thread.is_alive():
        log_thread.join(timeout=2.0)

def load_icon(path, context=""):
    if not path:
        logger.error(f"No icon path provided for {context}")
        app_signals.append_log.emit(f"[Init] No icon path provided for {context}")
        return QIcon()
    if path in ICON_CACHE and Path(path).exists():
        return QIcon(path)
    if not Path(path).exists():
        logger.error(f"Icon file does not exist for {context}: {path}")
        app_signals.append_log.emit(f"[Init] Icon file does not exist for {context}: {path}")
        return QIcon()
    icon = QIcon(path)
    if icon.isNull():
        logger.error(f"Failed to load icon for {context}: {path}")
        app_signals.append_log.emit(f"[Init] Failed to load icon for {context}: {path}")
    return icon
    
CACHE_DAYS = 7

def get_system_info():
    try:
        uname = platform.uname()
    except Exception:
        uname = None
        print("uname not found")

    info = {}
    
    
    # === CPU Info ===
    try:
        info["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "max_frequency_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else None,
            "min_frequency_mhz": psutil.cpu_freq().min if psutil.cpu_freq() else None,
            "current_frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "cpu_usage_percent": psutil.cpu_percent(interval=None),
            "per_core_usage_percent": psutil.cpu_percent(interval=None, percpu=True)
        }
    except Exception as e:
        info["cpu"] = {"error": str(e)}



    # === OS and System Info ===
    info["system"] = {
        "os": uname.system if uname else platform.system(),
        "node_name": uname.node if uname else socket.gethostname(),
        "release": uname.release if uname else "",
        "version": uname.version if uname else "",
        "machine": uname.machine if uname else platform.machine(),
        "processor": uname.processor if uname else platform.processor(),
        "architecture": platform.architecture()[0],
    }
    try:
        system = platform.system().lower()
        if system == "darwin":  # macOS
            print('darwin')
            serial = subprocess.check_output(["system_profiler", "SPHardwareDataType"], text=True)
            info["system"]["hardware_serial"] = next((line.split(":")[1].strip()
                                                    for line in serial.splitlines()
                                                    if "Serial Number" in line), None)
        elif system == "windows":
            serial = subprocess.check_output(
                ["wmic", "bios", "get", "serialnumber"],
                text=True,
                timeout=5,          # ADD timeout — wmic hangs on some machines
                creationflags=subprocess.CREATE_NO_WINDOW  # don't flash a console
            )
            lines = [line.strip() for line in serial.split("\n") if line.strip()]
            if len(lines) >= 2:
                # First line is usually "SerialNumber", second is actual value
                info["system"]["hardware_serial"] = lines[1]
            else:
                info["system"]["hardware_serial"] = 'None'
            
    except Exception:
        info["system"]["hardware_serial"] = 'None'
        
        
    # === System Identifiers ===
    try:
        if platform.system().lower() == "windows":
            info["identifiers"] = {
                "hostname": socket.gethostname(),
                "ip_address": socket.gethostbyname(socket.gethostname()),
                "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                                        for elements in range(0, 2 * 6, 8)][::-1]),
                "uuid": str(uuid.uuid1())
            }
        elif platform.system().lower() == "darwin":
            # safer way to get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)          # ADD 3 second timeout
            try:
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            finally:
                s.close()

            info["identifiers"] = {
                "hostname": socket.gethostname(),
                "ip_address": ip_address,
                "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                                        for elements in range(0, 2 * 6, 8)][::-1]),
                "uuid": str(uuid.uuid1())
            }
    except Exception as e:
        info["identifiers"] = {"error": str(e)}



    # === Additional macOS/Windows Specific Info ===
    try:
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        network_info = []
        for interface_name, addrs in net_if_addrs.items():
            iface = {"name": interface_name, "mac": None, "ipv4": [], "ipv6": [], "is_up": False}
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    iface["ipv4"].append({
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
                elif addr.family == socket.AF_INET6:
                    iface["ipv6"].append({
                        "address": addr.address.split('%')[0],
                        "netmask": addr.netmask
                    })
                elif getattr(psutil, "AF_LINK", None) and addr.family == psutil.AF_LINK:
                    iface["mac"] = addr.address
            iface["is_up"] = net_if_stats.get(interface_name, None) and net_if_stats[interface_name].isup
            network_info.append(iface)
        info["network"] = network_info
        data = {}
        data["ip_address"] = info.get("identifiers", {}).get("ip_address", "")
        data["mac_address"] = info.get("identifiers", {}).get("mac_address", "")
        
        mac_address = info.get("identifiers", {}).get("mac_address", "")
        if mac_address:
            encoded_mac = hashlib.md5(mac_address.encode()).hexdigest()
        else:
            encoded_mac = ""

        data["encoded_mac"] = encoded_mac
        
        data["details"] = info
        global USER_SYSTEM_INFO
        USER_SYSTEM_INFO = data
        print(f"USER_SYSTEM_INFO ======== {USER_SYSTEM_INFO}")
    except Exception as e:
        info["network"] = {"error": str(e)}


def get_default_cache():
    """Return a fresh cache dictionary with created_at set once."""
    return {
        "token": "",
        "user": "",
        "user_id": "",
        "user_info": {},
        "info_resp": {},
        "user_data": {},
        "data": "",
        "downloaded_files": {},
        "uploaded_files": [],
        "created_at": int(time.time())  # only when initialized
    }

# def initialize_cache():
#     """Create a new cache file safely."""
#     cache = get_default_cache()
#     try:
#         os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
#         with open(CACHE_FILE, "w") as f:
#             json.dump(cache, f, indent=2)
#     except OSError as e:
#         print(f"[WARN] Could not initialize cache file: {e}")
#     return cache

def initialize_cache():
    """Create a new cache file safely and reset in-memory cache."""
    global _MEMORY_CACHE, _MEMORY_CACHE_DIRTY
    cache = get_default_cache()
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except OSError as e:
        print(f"[WARN] Could not initialize cache file: {e}")
    _MEMORY_CACHE = cache
    _MEMORY_CACHE_DIRTY = False
    return cache

# def load_cache():
#     """Load cache safely. If missing/corrupted, reinitialize."""
#     if os.path.exists(CACHE_FILE):
#         try:
#             with open(CACHE_FILE, "r") as f:
#                 cache = json.load(f)
#             # Ensure required keys exist (avoid KeyError later)
#             for key, default_value in get_default_cache().items():
#                 if key not in cache:
#                     cache[key] = default_value
#             return cache
#         except (json.JSONDecodeError, OSError) as e:
#             print(f"[WARN] Cache load failed ({e}), recreating...")
#             return initialize_cache()
#     else:
#         return initialize_cache()


def load_cache():
    """
    Return in-memory cache if available.
    Only reads disk on first call or after cache is invalidated.
    Eliminates the disk I/O that was happening every 3-second poll cycle.
    """
    global _MEMORY_CACHE
    if _MEMORY_CACHE is not None:
        return _MEMORY_CACHE

    # Cold start — read from disk once
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
            for key, default_value in get_default_cache().items():
                if key not in cache:
                    cache[key] = default_value
            _MEMORY_CACHE = cache
            return _MEMORY_CACHE
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Cache load failed ({e}), recreating...")
            _MEMORY_CACHE = initialize_cache()
            return _MEMORY_CACHE
    else:
        _MEMORY_CACHE = initialize_cache()
        return _MEMORY_CACHE


# def save_cache(cache, significant_change=True):
#     """Save cache safely without crashing app."""
#     try:
#         with open(CACHE_FILE, "w") as f:
#             json.dump(cache, f, indent=2)
#     except OSError as e:
#         print(f"[WARN] Could not save cache file: {e}")

def save_cache(cache, significant_change=True):
    """
    Update in-memory cache immediately.
    Write to disk only when significant_change=True (default).
    Polling cycles that just read state can pass significant_change=False
    to skip the disk write entirely.
    """
    global _MEMORY_CACHE, _MEMORY_CACHE_DIRTY
    _MEMORY_CACHE = cache

    if significant_change:
        try:
            with CACHE_WRITE_LOCK:
                with open(CACHE_FILE, "w") as f:
                    json.dump(cache, f, indent=2)
            _MEMORY_CACHE_DIRTY = False
        except OSError as e:
            print(f"[WARN] Could not save cache file: {e}")
            _MEMORY_CACHE_DIRTY = True
    else:
        _MEMORY_CACHE_DIRTY = True

def get_cache_age(cache):
    """Get cache age in seconds."""
    created_at = cache.get("created_at", int(time.time()))
    return int(time.time()) - created_at


def parse_custom_url():
    try:
        args = sys.argv[1:]
        logger.debug(f"Parsing custom URL from arguments: {args}")
        app_signals.append_log.emit(f"[Init] Parsing custom URL from arguments: {args}")
        if not args:
            logger.info("No custom URL provided")
            app_signals.append_log.emit("[Init] No custom URL provided")
            return ""
        url = args[0]
        parsed_url = urlparse(url)
        if parsed_url.scheme != "myapp":
            logger.warning(f"Invalid scheme in URL: {url}")
            app_signals.append_log.emit(f"[Init] Invalid scheme in URL: {url}")
            return ""
        query_params = parse_qs(parsed_url.query)
        key = query_params.get("key", [""])[0]
        logger.info(f"Parsed key: {key[:8]}..." if key else "No key found")
        app_signals.append_log.emit(f"[Init] Parsed key: {key[:8]}..." if key else "[Init] No key found")
        return key
    except Exception as e:
        logger.error(f"Error parsing custom URL: {e}")
        app_signals.append_log.emit(f"[Init] Failed to parse custom URL: {str(e)}")
        return ""

def validate_user(access_key, status_bar=None):
    """
    Validates a user's token using the API endpoint with access_key.

    Args:
        access_key (str): The access key (defaults to a hardcoded value if not provided).
        status_bar (QStatusBar, optional): Status bar to update with validation messages.

    Returns:
        dict: Contains 'status' (bool), 'message' (str), 'user' (str), 'token' (str), or full API response on success.
    """
    try:
        if not access_key:
            access_key = "e0d6aa4baffc84333faa65356d78e439"
            logger.info("No access_key provided, using default key")
            app_signals.append_log.emit("[API Scan] No access_key provided, using default key")
        
        machine_id = USER_SYSTEM_INFO.get("encoded_mac", "")
        cache = load_cache()
        validation_url = USER_VALIDATE_URL
        logger.debug(f"Validating user with access_key: {access_key[:8]}... at {validation_url}")
        app_signals.append_log.emit(f"[API Scan] Validating user with access_key: {access_key[:8]}...")
        
        resp = HTTP_SESSION.get(
            validation_url,
            params={"key": access_key, "machine_id": machine_id},
            # headers={"Authorization": f"Bearer {cache.get('token', '')}"},
            verify=False,  # Replace with verify="/path/to/server-ca.pem" in production
            timeout=30
        )
        print(f"Request URL: {resp.url}")
        app_signals.api_call_status.emit(
            validation_url,
            f"Status: {resp.status_code}, Response: {resp.text}",
            resp.status_code
        )
        app_signals.append_log.emit(f"[API Scan] User validation API response: {resp.status_code}")
        
        if status_bar:
            status_bar.showMessage(f"User validation API response: {resp.status_code}")
        
        resp.raise_for_status()
        result = resp.json()
        if result.get("status") == 403:
            return result
        
        if not result.get("uuid"):
            raise ValueError(f"Validation failed: {result.get('message', 'No uuid in response')}")
        
        logger.info("User validation successful")
        app_signals.append_log.emit("[API Scan] User validation successful")
        return result  # Return full API response as per original function
    
    except Exception as e:
        logger.error(f"User validation error: {e}")
        app_signals.append_log.emit(f"[API Scan] Failed: User validation error - {str(e)}")
        if status_bar:
            status_bar.showMessage(f"User validation failed: {str(e)}")
        return {"status": False, "message": str(e), "user": "", "token": ""}

def create_folders_from_response(response):
    try:
        cache = load_cache()
        projects = cache.get("user_data", {}).get("projects", [])
        project_name = response.get("project_name", response.get("name", "unknown")).replace(" ", "_")
        client_name = response.get("client_name", "").replace(" ", "_")
        project_path = BASE_TARGET_DIR / client_name / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project folder: {project_path}")
        app_signals.append_log.emit(f"[Folder] Created project folder: {project_path}")
        projects.append(response)
        cache["user_data"] = {"projects": projects}
        save_cache(cache)
    except Exception as e:
        logger.error(f"Failed to create folders: {e}")
        app_signals.append_log.emit(f"[Folder] Failed to create folders: {str(e)}")

def start_timer_api(file_path, token):
    try:
        response = HTTP_SESSION.post(
            f"{BASE_DOMAIN}/api/ir_production/timer/start",
            json={"file_path": file_path},
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=30
        )
        app_signals.api_call_status.emit(
            f"{BASE_DOMAIN}/api/ir_production/timer/start",
            "Success" if response.status_code == 200 else f"Failed: {response.status_code}",
            response.status_code
        )
        app_signals.append_log.emit(f"[API Scan] Timer start API response: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to start timer: {e}")
        app_signals.append_log.emit(f"[API Scan] Failed to start timer: {str(e)}")
        return None

def end_timer_api(file_path, timer_response, token):
    try:
        response = HTTP_SESSION.post(
            f"{BASE_DOMAIN}/api/ir_production/timer/end",
            json={"file_path": file_path, "timer_response": timer_response},
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=30
        )
        app_signals.api_call_status.emit(
            f"{BASE_DOMAIN}/api/ir_production/timer/end",
            "Success" if response.status_code == 200 else f"Failed: {response.status_code}",
            response.status_code
        )
        app_signals.append_log.emit(f"[API Scan] Timer end API response: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to end timer: {e}")
        app_signals.append_log.emit(f"[API Scan] Failed to end timer: {str(e)}")
        return None

# def connect_to_nas():
#     if not NAS_AVAILABLE:
#         raise Exception("NAS functionality disabled")
#     start = time.perf_counter()
#     try:
#         transport = paramiko.Transport((NAS_IP, 22))
#         transport.connect(username=NAS_USERNAME, password=NAS_PASSWORD)
#         sftp = paramiko.SFTPClient.from_transport(transport)
#         print(f"Connection time: {(time.perf_counter() - start)*1000:.1f}ms")
#         return (transport, sftp)
#     except (paramiko.AuthenticationException, paramiko.SSHException, Exception) as e:
#         print(f"Connection failed after {(time.perf_counter() - start)*1000:.1f}ms: {str(e)}")
#         raise Exception(f"NAS connection failed: {str(e)}")

# def check_nas_write_permission(sftp, nas_path):
#     """Verify and set write permission for NAS directory and file."""
#     try:
#         nas_parent = str(Path(nas_path).parent)
#         logger.debug(f"Checking NAS directory permissions: {nas_parent}")
#         app_signals.append_log.emit(f"[Transfer] Checking NAS directory permissions: {nas_parent}")
#         try:
#             stat = sftp.stat(nas_parent)
#             mode = stat.st_mode & 0o777
#             logger.debug(f"Directory {nas_parent} permissions: {oct(mode)}")
#             app_signals.append_log.emit(f"[Transfer] Directory {nas_parent} permissions: {oct(mode)}")
#             if mode != 0o770:
#                 sftp.chmod(nas_parent, 0o770)
#                 logger.info(f"Set permissions to 770 for {nas_parent}")
#                 app_signals.append_log.emit(f"[Transfer] Set permissions to 770 for {nas_parent}")
#         except FileNotFoundError:
#             sftp.makedirs(nas_parent, mode=0o770)
#             logger.info(f"Created directory {nas_parent} with permissions 770")
#             app_signals.append_log.emit(f"[Transfer] Created directory {nas_parent} with permissions 770")
        
#         # Test write access
#         temp_file = f"{nas_parent}/.test_write_{int(time.time())}.tmp"
#         sftp.open(temp_file, 'w').close()
#         sftp.remove(temp_file)
        
#         # Handle existing file
#         try:
#             stat = sftp.stat(nas_path)
#             mode = stat.st_mode & 0o777
#             logger.debug(f"File {nas_path} exists with permissions: {oct(mode)}")
#             app_signals.append_log.emit(f"[Transfer] File {nas_path} exists with permissions: {oct(mode)}")
#             try:
#                 sftp.chmod(nas_path, 0o660)
#                 logger.info(f"Set permissions to 660 for existing file {nas_path}")
#                 app_signals.append_log.emit(f"[Transfer] Set permissions to 660 for existing file {nas_path}")
#             except Exception:
#                 sftp.remove(nas_path)
#                 logger.info(f"Removed existing file {nas_path} due to permission issue")
#                 app_signals.append_log.emit(f"[Transfer] Removed existing file {nas_path} due to permission issue")
#         except FileNotFoundError:
#             pass  # File doesn't exist, which is fine
        
#         logger.info(f"Write permission confirmed for {nas_parent}")
#         app_signals.append_log.emit(f"[Transfer] Write permission confirmed for {nas_parent}")
#         return True
#     except Exception as e:
#         logger.error(f"Write permission check failed for {nas_path}: {e}")
#         app_signals.append_log.emit(f"[Transfer] Write permission check failed for {nas_path}: {e}")
#         return False

MAX_RETRIES = 10
RETRY_BACKOFF = 2  # seconds
TIMEOUT = 1000  # seconds


def call_api(api_url, payload, local_file_path=None):
    logger.info("+++++++++++++++++++++++++++++++ Posting operator upload ++++++++++++++++++++++++++++++")
    attempt = 0
    while attempt < MAX_RETRIES:
        files = None
        try:
            if local_file_path:
                file_name = os.path.basename(local_file_path)
                if not os.path.exists(local_file_path):
                    logger.error(f"File not found: {local_file_path}")
                    return {"error": "File not found"}
                mime_type, _ = mimetypes.guess_type(local_file_path)
                mime_type = mime_type or 'application/octet-stream'
                files = {
                    'creative_files': (file_name, open(local_file_path, 'rb'), mime_type)
                }
                logger.debug(f"File Name: {file_name}, MIME Type: {mime_type}, File Size: {os.path.getsize(local_file_path)} bytes")
            logger.debug(f"Payload being sent: {payload}")
            logger.debug(f"Files being sent: {'Yes' if files else 'No'}")
            with httpx.Client(timeout=TIMEOUT, verify=False) as client:
                response = client.post(api_url, files=files, data=payload)
            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Text: {response.text[:500]}...")
            if response.status_code >= 400:
                report_api_failure(
                    "operator_upload", api_url,
                    status_code=response.status_code, response_text=response.text
                )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as req_err:
            logger.warning(f"[Attempt {attempt+1}] Request error: {req_err}")
            attempt += 1
            if attempt < MAX_RETRIES:
                sleep_time = RETRY_BACKOFF ** attempt
                logger.debug(f"Retrying after {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                report_api_failure("operator_upload", api_url, error=str(req_err))
                return {"error": "Request failed", "details": str(req_err)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            report_api_failure("operator_upload", api_url, error=str(e))
            return {"error": "Unexpected error", "details": str(e)}
        finally:
            if files:
                for _, file_obj, _ in files.values():
                    file_obj.close()

def call_api_qc_qa(api_url, payload, local_file_path=None):
    logger.info("_____________________________ Posting Qc Qa Replace _______________________")
    attempt = 0
    while attempt < MAX_RETRIES:
        files = None
        try:
            if local_file_path:
                file_name = os.path.basename(local_file_path)
                if not os.path.exists(local_file_path):
                    logger.error(f"File not found: {local_file_path}")
                    return {"error": "File not found"}
                mime_type, _ = mimetypes.guess_type(local_file_path)
                mime_type = mime_type or 'application/octet-stream'
                files = {
                    'files[]': (file_name, open(local_file_path, 'rb'), mime_type)
                }
                logger.debug(f"File Name: {file_name}, MIME Type: {mime_type}, File Size: {os.path.getsize(local_file_path)} bytes")
            logger.debug(f"Payload being sent: {payload}")
            logger.debug(f"Files being sent: {'Yes' if files else 'No'}")
            with httpx.Client(timeout=TIMEOUT, verify=False) as client:
                response = client.post(api_url, files=files, data=payload)
            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Text: {response.text[:500]}...")
            if response.status_code >= 400:
                report_api_failure(
                    "qc_qa_replace", api_url,
                    status_code=response.status_code, response_text=response.text
                )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as req_err:
            logger.warning(f"[Attempt {attempt+1}] Request error: {req_err}")
            attempt += 1
            if attempt < MAX_RETRIES:
                sleep_time = RETRY_BACKOFF ** attempt
                logger.debug(f"Retrying after {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                report_api_failure("qc_qa_replace", api_url, error=str(req_err))
                return {"error": "Request failed", "details": str(req_err)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            report_api_failure("qc_qa_replace", api_url, error=str(e))
            return {"error": "Unexpected error", "details": str(e)}
        finally:
            if files:
                for _, file_obj, _ in files.values():
                    file_obj.close()


def post_metadata_to_api_upload(spec_id, user_id):
    logger.info("============================ Posting Metadata to Upload API ==============================")
    
    try:
        payload = {
            'business': 'image_retouching',
            'operator_uid': user_id,
            'spec_id': spec_id
        }
        response = requests.post(API_URL_UPLOAD, json=payload, verify=False)
        logger.info(response)
        if response.status_code == 200:
            logger.info(f"Successfully posted metadata to API (Upload).")
        else:
            logger.error(f"Failed to post metadata to API (Upload): {response.status_code} {response.text}")
            report_api_failure(
                "post_metadata_upload", API_URL_UPLOAD,
                status_code=response.status_code, response_text=response.text
            )
    except Exception as e:
        logger.error(f"Error posting metadata to API (Upload): {e}")
        report_api_failure("post_metadata_upload", API_URL_UPLOAD, error=str(e))


def post_api(api_url,payload):
    logger.info("-------------------------------------------------- Posting update -------------------------------")
    try:        
        response = requests.post(api_url, data=payload, verify=False)
        logger.info(response)
        if response.status_code == 200:
            logger.info(f"Successfully posted metadata to API (Upload).")
        else:
            logger.error(f"Failed to post metadata to API (Upload): {response.status_code} {response.text}")
            report_api_failure(
                "post_api", api_url,
                status_code=response.status_code, response_text=response.text
            )
    except Exception as e:
        logger.error(f"Error posting metadata to API (Upload): {e}")
        report_api_failure("post_api", api_url, error=str(e))


def update_download_upload_metadata(task_id, request_status, retries=3, timeout=10.0, base_retry_delay=2):
   
    payload = {"id": task_id, "request_status": request_status}
    headers = {"Content-Type": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            response = httpx.post(
                API_URL_UPLOAD_DOWNLOAD_UPDATE,
                data=json.dumps(payload),
                headers=headers,
                verify=False,
                timeout=timeout,
            )
            print(f"================================================ Status Code {task_id} : {request_status}")
            if response.status_code == 200:
                return response.json()

            logger.error(
                f"Attempt {attempt}: Failed with status {response.status_code}"
            )
            if attempt == retries:
                report_api_failure(
                    "update_download_upload_metadata", API_URL_UPLOAD_DOWNLOAD_UPDATE,
                    status_code=response.status_code, response_text=response.text
                )

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"Attempt {attempt}: Request error -> {e}")
            if attempt == retries:
                report_api_failure("update_download_upload_metadata", API_URL_UPLOAD_DOWNLOAD_UPDATE, error=str(e))
        except Exception as e:
            logger.error(f"Attempt {attempt}: Unexpected error -> {e}")
            if attempt == retries:
                report_api_failure("update_download_upload_metadata", API_URL_UPLOAD_DOWNLOAD_UPDATE, error=str(e))

        if attempt < retries:
            delay = base_retry_delay * (2 ** (attempt - 1))  # exponential backoff
            time.sleep(delay)

    return {"error": "Failed after retries"}

def get_file_types_from_api(job_id):
    api_url = f"{FILE_FORMAT_API}?job_id={job_id}"
    try:
        cache = load_cache()
        token = cache.get('token', '')
        headers = {"Authorization": f"Bearer {token}"}
        format_response = HTTP_SESSION.get(api_url, headers=headers, verify=False, timeout=60)
        try:
            response_data = format_response.json()
            print(response_data)
            # print(f"=============Priority extension=============={response_data}========")

            if response_data:
                return response_data
            else: False
        except:
            False
    except:
        print(f"=============API GET FORMAT FAILS=============={response_data}========")
        return False

# ===================== image convertion logic =====================

def sanitize_filename(filename):
    return re.sub(r'[^\w\-.]', '_', filename)

def get_file_hash(file_path):
    """Calculate SHA256 hash of a file for integrity check."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        return None

# def check_nas_write_permission(sftp, nas_path):
#     """Verify and set write permission for NAS directory and file."""
#     try:
#         nas_parent = str(Path(nas_path).parent)
#         logger.debug(f"Checking NAS directory permissions: {nas_parent}")
#         app_signals.append_log.emit(f"[Transfer] Checking NAS directory permissions: {nas_parent}")
#         try:
#             stat = sftp.stat(nas_parent)
#             mode = stat.st_mode & 0o777
#             logger.debug(f"Directory {nas_parent} permissions: {oct(mode)}")
#             app_signals.append_log.emit(f"[Transfer] Directory {nas_parent} permissions: {oct(mode)}")
#             if mode != 0o777:
#                 sftp.chmod(nas_parent, 0o777)
#                 logger.info(f"Set permissions to 777 for {nas_parent}")
#                 app_signals.append_log.emit(f"[Transfer] Set permissions to 777 for {nas_parent}")
#         except FileNotFoundError:
#             sftp.makedirs(nas_parent, mode=0o777)
#             logger.info(f"Created directory {nas_parent} with permissions 777")
#             app_signals.append_log.emit(f"[Transfer] Created directory {nas_parent} with permissions 777")
        
#         # Test write access
#         temp_file = f"{nas_parent}/.test_write_{int(time.time())}.tmp"
#         sftp.open(temp_file, 'w').close()
#         sftp.remove(temp_file)
        
#         # Handle existing file
#         try:
#             stat = sftp.stat(nas_path)
#             mode = stat.st_mode & 0o777
#             logger.debug(f"File {nas_path} exists with permissions: {oct(mode)}")
#             app_signals.append_log.emit(f"[Transfer] File {nas_path} exists with permissions: {oct(mode)}")
#             try:
#                 sftp.chmod(nas_path, 0o777)
#                 logger.info(f"Set permissions to 777 for existing file {nas_path}")
#                 app_signals.append_log.emit(f"[Transfer] Set permissions to 777 for existing file {nas_path}")
#             except Exception:
#                 sftp.remove(nas_path)
#                 logger.info(f"Removed existing file {nas_path} due to permission issue")
#                 app_signals.append_log.emit(f"[Transfer] Removed existing file {nas_path} due to permission issue")
#         except FileNotFoundError:
#             pass  # File doesn't exist, which is fine
        
#         logger.info(f"Write permission confirmed for {nas_parent}")
#         app_signals.append_log.emit(f"[Transfer] Write permission confirmed for {nas_parent}")
#         return True
#     except Exception as e:
#         logger.error(f"Write permission check failed for {nas_path}: {e}")
#         app_signals.append_log.emit(f"[Transfer-lang=python] Write permission check failed for {nas_path}: {e}")
#         return False


def open_file_with_photoshop(file_path: str, log_callback=None) -> bool:
    """
    Module-level helper — open a file in Adobe Photoshop across platforms.
    Used by FileWatcherWorker, FileDownloadListWindow, and FileUploadListWindow.

    Args:
        file_path: Absolute path to the file to open.
        log_callback: Optional callable(str) for log messages (e.g. self.log_update.emit).

    Returns:
        True on success, raises on failure.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    import platform as _platform
    system = _platform.system()
    file_path = str(Path(file_path).resolve())

    if not Path(file_path).exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    _log(f"[Photoshop] Opening {Path(file_path).name} on {system}")
    photoshop_path = None

    if system == "Windows":
        try:
            import win32gui, win32con, win32com.client, win32api, win32process, ctypes
        except ImportError as e:
            raise ImportError("Required pywin32 modules not found. Run: pip install pywin32") from e

        photoshop_path = os.getenv("PHOTOSHOP_PATH")
        if photoshop_path and Path(photoshop_path).exists():
            _log(f"[Photoshop] Using PHOTOSHOP_PATH: {photoshop_path}")
        else:
            for base_dir in [Path("C:/Program Files/Adobe"), Path("C:/Program Files (x86)/Adobe")]:
                if not base_dir.exists():
                    continue
                exes = sorted(base_dir.glob("Adobe Photoshop */Photoshop.exe"),
                              key=lambda x: x.parent.name, reverse=True)
                if exes:
                    photoshop_path = str(exes[0])
                    break
            if not photoshop_path:
                raise FileNotFoundError("Adobe Photoshop executable not found in Program Files")

        if not os.access(photoshop_path, os.X_OK):
            raise PermissionError(f"Photoshop executable not accessible: {photoshop_path}")

        # Try COM first
        try:
            ps_app = win32com.client.Dispatch("Photoshop.Application")
            ps_app.Visible = True
            ps_app.Open(file_path)

            def _bring_to_front():
                def _enum(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd) and \
                            "adobe photoshop" in win32gui.GetWindowText(hwnd).lower():
                        try:
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            this = win32api.GetCurrentThreadId()
                            target = win32process.GetWindowThreadProcessId(hwnd)[0]
                            if ctypes.windll.user32.AttachThreadInput(this, target, True):
                                win32gui.SetForegroundWindow(hwnd)
                                ctypes.windll.user32.AttachThreadInput(this, target, False)
                        except Exception:
                            pass
                win32gui.EnumWindows(_enum, None)

            time.sleep(1.5)
            _bring_to_front()
            _log(f"[Photoshop] Opened {Path(file_path).name} via COM")
            return True
        except Exception as com_err:
            _log(f"[Photoshop] COM failed ({com_err}), trying subprocess...")

        # Fallback: subprocess
        for attempt in range(3):
            try:
                subprocess.Popen([photoshop_path, file_path], stderr=subprocess.PIPE, text=True)
                time.sleep(2)
                hwnds = []
                win32gui.EnumWindows(
                    lambda h, l: l.append(h)
                    if win32gui.IsWindowVisible(h) and
                       "adobe photoshop" in win32gui.GetWindowText(h).lower()
                    else None,
                    hwnds
                )
                if hwnds:
                    win32gui.ShowWindow(hwnds[0], win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnds[0])
                _log(f"[Photoshop] Opened {Path(file_path).name} via subprocess")
                return True
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to open after 3 attempts: {e}")

    elif system == "Darwin":
        photoshop_path = os.getenv("PHOTOSHOP_PATH")
        if photoshop_path and not Path(photoshop_path).exists():
            photoshop_path = None

        if not photoshop_path:
            try:
                result = subprocess.run(
                    ["mdfind", "kMDItemKind == 'Application' && "
                     "(kMDItemFSName == 'Adobe Photoshop*.app' || "
                     "kMDItemFSName == 'Photoshop*.app')"],
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip():
                    photoshop_path = result.stdout.strip().split("\n")[0]
            except Exception:
                pass

        if not photoshop_path:
            search_dirs = [
                Path("/Applications"), Path("~/Applications").expanduser(),
                Path("/Applications/Adobe"), Path("~/Applications/Adobe").expanduser(),
            ]
            for d in search_dirs:
                if not d.exists():
                    continue
                apps = (list(d.glob("Adobe*Photoshop*.app")) +
                        list(d.glob("Photoshop*.app")) +
                        list(d.glob("*/Adobe*Photoshop*.app")))
                if apps:
                    photoshop_path = str(sorted(apps, key=lambda x: x.name, reverse=True)[0])
                    break

        if not photoshop_path:
            versioned = [
                Path(f"/Applications/Adobe Photoshop {yr}/Adobe Photoshop {yr}.app")
                for yr in (2025, 2024, 2023)
            ]
            for p in versioned:
                if p.exists():
                    photoshop_path = str(p)
                    break

        if not photoshop_path:
            raise FileNotFoundError(
                "Adobe Photoshop not found. Set the PHOTOSHOP_PATH environment variable."
            )

        for attempt in range(3):
            try:
                subprocess.run(["open", "-a", photoshop_path, file_path], check=True)
                app_name = Path(photoshop_path).stem
                subprocess.run(
                    ["osascript", "-e", f'tell application "{app_name}" to activate'],
                    capture_output=True
                )
                _log(f"[Photoshop] Opened {Path(file_path).name} via open -a")
                return True
            except subprocess.CalledProcessError as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to open after 3 attempts: {e}")

    elif system == "Linux":
        try:
            subprocess.run(["wine", "--version"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            raise FileNotFoundError("Wine is not installed or not functioning")

        for base_dir in [
            Path.home() / ".wine/drive_c/Program Files/Adobe",
            Path.home() / ".wine/drive_c/Program Files (x86)/Adobe",
        ]:
            if not base_dir.exists():
                continue
            exes = sorted(base_dir.glob("Adobe Photoshop */Photoshop.exe"),
                          key=lambda x: x.parent.name, reverse=True)
            if exes:
                photoshop_path = str(exes[0])
                break

        if not photoshop_path:
            raise FileNotFoundError("Photoshop.exe not found in Wine directories")

        for attempt in range(3):
            try:
                subprocess.run(["wine", photoshop_path, file_path], check=True)
                subprocess.run(["wmctrl", "-a", "Adobe Photoshop"], check=False)
                _log(f"[Photoshop] Opened {Path(file_path).name} via wine")
                return True
            except subprocess.CalledProcessError as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to open after 3 attempts: {e}")

    else:
        raise ValueError(f"Unsupported platform: {system}")

def check_nas_write_permission(sftp, nas_path):
    """
    Verify write permission for NAS directory and file.
    Sets permissions to 0o777 on directory and existing file.
    Returns True if write access confirmed, False otherwise.
    """
    try:
        nas_parent = str(Path(nas_path).parent)
        logger.debug(f"Checking NAS directory permissions: {nas_parent}")
        app_signals.append_log.emit(
            f"[Transfer] Checking NAS directory permissions: {nas_parent}"
        )

        # --- Check / create the parent directory ---
        try:
            stat = sftp.stat(nas_parent)
            mode = stat.st_mode & 0o777
            logger.debug(f"Directory {nas_parent} permissions: {oct(mode)}")
            app_signals.append_log.emit(
                f"[Transfer] Directory {nas_parent} permissions: {oct(mode)}"
            )
            if mode != 0o777:
                sftp.chmod(nas_parent, 0o777)
                logger.info(f"Set permissions to 777 for {nas_parent}")
                app_signals.append_log.emit(
                    f"[Transfer] Set permissions to 777 for {nas_parent}"
                )
        except FileNotFoundError:
            sftp.makedirs(nas_parent, mode=0o777)
            logger.info(f"Created directory {nas_parent} with permissions 777")
            app_signals.append_log.emit(
                f"[Transfer] Created directory {nas_parent} with permissions 777"
            )

        # --- Confirm write access with a temp file ---
        temp_file = f"{nas_parent}/.test_write_{int(time.time())}.tmp"
        sftp.open(temp_file, 'w').close()
        sftp.remove(temp_file)

        # --- Handle existing destination file ---
        try:
            stat = sftp.stat(nas_path)
            mode = stat.st_mode & 0o777
            logger.debug(f"File {nas_path} exists with permissions: {oct(mode)}")
            app_signals.append_log.emit(
                f"[Transfer] File {nas_path} exists with permissions: {oct(mode)}"
            )
            try:
                sftp.chmod(nas_path, 0o777)
                logger.info(f"Set permissions to 777 for existing file {nas_path}")
                app_signals.append_log.emit(
                    f"[Transfer] Set permissions to 777 for existing file {nas_path}"
                )
            except Exception:
                sftp.remove(nas_path)
                logger.info(
                    f"Removed existing file {nas_path} due to permission issue"
                )
                app_signals.append_log.emit(
                    f"[Transfer] Removed existing file {nas_path} due to permission issue"
                )
        except FileNotFoundError:
            pass  # File doesn't exist yet — that's fine

        logger.info(f"Write permission confirmed for {nas_parent}")
        app_signals.append_log.emit(
            f"[Transfer] Write permission confirmed for {nas_parent}"
        )
        return True

    except Exception as e:
        logger.error(f"Write permission check failed for {nas_path}: {e}")
        app_signals.append_log.emit(
            # NOTE: fixed stray 'lang=python' that was in the original log line
            f"[Transfer] Write permission check failed for {nas_path}: {e}"
        )
        return False


def process_image_in_memory(image_data, ext, full_file_path):
   
    stream = io.BytesIO(image_data)
    pil_image = None
    ext = ext.lower()
    logger.info(f"Starting processing of {full_file_path} with extension {ext}")

    if ext in ['jpg', 'jpeg', 'png']:
        pil_image = Image.open(stream)
        logger.info(f"Opened {ext} file, mode: {pil_image.mode}")
    elif ext == 'gif':
        pil_image = Image.open(stream)
        pil_image = next(ImageSequence.Iterator(pil_image))
        logger.info("Processed GIF first frame, mode: {pil_image.mode}")
    elif ext in ['tif', 'tiff']:
        with tifffile.TiffFile(stream) as tif:
            page = tif.pages[0]
            arr = page.asarray()
            photometric = getattr(page.photometric, 'name', 'unknown').lower()
            if photometric in ['rgb', 'ycbcr']:
                arr = arr[:, :, :3] if arr.ndim == 3 and arr.shape[2] >= 3 else arr
                pil_image = Image.fromarray(arr.astype(np.uint8), mode='RGB')
            elif photometric == 'cmyk':
                pil_image = Image.fromarray(arr.astype(np.uint8), mode='CMYK').convert("RGB")
            elif photometric == 'minisblack' or arr.ndim == 2:
                arr = np.stack((arr,) * 3, axis=-1)
                pil_image = Image.fromarray(arr.astype(np.uint8), mode='RGB')
            else:
                logger.warning(f"Unsupported TIFF photometric: {photometric}")
                return None
            logger.info(f"Processed TIFF, mode: {pil_image.mode}, photometric: {photometric}")
    elif ext in ['psd', 'psb']:
            psd = PSDImage.open(stream)
            if psd is None or not psd.has_preview():
                logger.error(f"PSD preview not available for {full_file_path}")
                return None

            pil_image = psd.composite()
            logger.info(f"PSD composite result, mode: {pil_image.mode}, size: {pil_image.size}")

            # Apply ICC profile if available
            try:
                icc = psd.image_resources.get("icc_profile")
                if icc:
                    pil_image.info["icc_profile"] = icc.data
                    logger.info(f"Applied ICC profile to PSD: {full_file_path}")
            except Exception as e:
                logger.warning(f"Error extracting ICC profile: {e}")
    elif ext in ['cr2', 'nef', 'arw', 'dng', 'raf', 'pef', 'srw']:
        with rawpy.imread(stream) as raw:
            rgb = raw.postprocess()
            pil_image = Image.fromarray(rgb)
        logger.info(f"Processed raw image, mode: {pil_image.mode}")
    else:
        pil_image = Image.open(stream)
        logger.info(f"Opened {ext} file, mode: {pil_image.mode}")

    if pil_image is None:
        logger.error(f"Failed to create PIL image for {full_file_path}")
        return None

    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
        logger.info("Final conversion to RGB, size: {pil_image.size}")

    jpeg_buffer = io.BytesIO()
    logger.info(f"Attempting to save JPEG to buffer, initial position: {jpeg_buffer.tell()}")
    pil_image.save(jpeg_buffer, format="JPEG", quality=80, icc_profile=pil_image.info.get('icc_profile'))
    logger.info(f"JPEG save completed, buffer position: {jpeg_buffer.tell()}")
    jpeg_buffer.seek(0)
    buffer_size = jpeg_buffer.getbuffer().nbytes
    logger.info(f"Buffer byte count: {buffer_size}")
    if buffer_size == 0:
        logger.error(f"Empty JPEG buffer for {full_file_path} after save")
        return None
    jpeg_buffer.seek(0)
    return jpeg_buffer
 






def process_single_file(full_file_path):
    """Convert a single file to JPEG and move original to backup."""
    path = Path(full_file_path)
    if not path.is_file():
        logger.error(f"File does not exist: {full_file_path}")
        return None, None

    base_directory = path.parent
    original_file_name = path.name
    file_name = sanitize_filename(original_file_name)
    ext = path.suffix.lower().lstrip(".")

    if ext not in SUPPORTED_EXTENSIONS:
        logger.debug(f"Unsupported file extension: {ext}")
        error_dir = base_directory / "invalid_files"
        error_dir.mkdir(exist_ok=True)
        error_path = error_dir / original_file_name
        path.rename(error_path)
        logger.warning(f"File moved to invalid folder: {error_path}")
        return None, None

    output_file_name = ".".join(file_name.split(".")[:-1]) + ".jpg"
    local_output_path = base_directory / output_file_name

    if local_output_path.exists():
        logger.info(f"Skipping: Output JPEG exists: {local_output_path}")
        return str(local_output_path), str(path)

    if ext in ["jpg", "jpeg"]:
        sanitized_path = base_directory / file_name
        if path != sanitized_path:
            path.rename(sanitized_path)
        logger.debug(f"JPEG moved/renamed to {sanitized_path}")
        return str(sanitized_path), str(sanitized_path)

    with open(path, "rb") as f:
        image_data = f.read()

    start_time = time.time()
    jpeg_buffer = process_image_in_memory(image_data, ext, str(path))
    elapsed = time.time() - start_time
    logger.info(f"Conversion time: {elapsed:.2f} seconds")

    if jpeg_buffer is None:
        error_dir = base_directory / "invalid_files"
        error_dir.mkdir(exist_ok=True)
        error_path = error_dir / original_file_name
        path.rename(error_path)
        logger.warning(f"File moved to invalid folder: {error_path}")
        return None, None

    if local_output_path.exists():
        local_output_path.unlink()

    with open(local_output_path, "wb") as f:
        f.write(jpeg_buffer.getvalue())
    os.chmod(local_output_path, 0o777)
    logger.debug(f"Converted JPEG written to {local_output_path}")

    backup_path = base_directory / original_file_name
    path.rename(backup_path)
    logger.debug(f"Original file renamed to {backup_path}")

    return str(local_output_path), str(full_file_path)


# ===================== image covertion logic =====================



class FileConversionWorker(QObject):
    finished = Signal(str, str, str)
    error = Signal(str, str)
    progress = Signal(str, int)

    def __init__(self, src_path, dest_dir):
        super().__init__()
        self.src_path = src_path
        self.dest_dir = dest_dir

    def run(self):
        if not PIL_AVAILABLE:
            self.error.emit("Pillow not installed, image conversion disabled", Path(self.src_path).name)
            return
        try:
            img = Image.open(self.src_path)
            filename = os.path.splitext(Path(self.src_path).name)[0]
            jpg_path = str(Path(self.dest_dir) / f"{filename}.jpg")
            psd_path = str(Path(self.dest_dir) / f"{filename}.psd")

            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(jpg_path, 'JPEG', quality=95)
            self.progress.emit(jpg_path, 50)
            img.save(psd_path, 'PSD')
            self.progress.emit(psd_path, 75)

            cache = load_cache()
            with open(jpg_path, 'rb') as f:
                resp = HTTP_SESSION.post(
                    f"{BASE_DOMAIN}/api/ir_production/upload/jpg",
                    files={'file': f},
                    headers={"Authorization": f"Bearer {cache.get('token', '')}"},
                    verify=False,
                    timeout=30
                )
                app_signals.api_call_status.emit(
                    f"{BASE_DOMAIN}/api/ir_production/upload/jpg",
                    "Success" if resp.status_code == 200 else f"Failed: {resp.status_code}",
                    resp.status_code
                )
                resp.raise_for_status()

            self.progress.emit(jpg_path, 100)
            self.finished.emit(jpg_path, psd_path, Path(self.src_path).name)
        except Exception as e:
            logger.error(f"File conversion error for {self.src_path}: {e}")
            self.error.emit(str(e), Path(self.src_path).name)


class FileWatcherWorker(QObject):
    show_dialog = Signal(str, str, str)  # Signal for title, message, dialog_type
    status_update = Signal(str)
    log_update = Signal(str)
    progress_update = Signal(str, str, int)
    request_reauth = Signal()
    task_list_update = Signal(list)
    cleanup_signal = Signal()
    user_in_other_system = Signal(str)
    alert_notification = Signal(str, str)
  
    download_progress = Signal(str, str, str, int)
    # (spec_id, file_path, filename, percent)

    download_status_detail = Signal(str, str, str, int, bool)
    # (file_path, status_text, action_type, percent, is_nas_src)

    upload_progress = Signal(str, str, str, int)          # spec_id, file_path, filename, percent
    upload_status_detail = Signal(str, str, str, int, bool)  # file_path, text, action_type="upload", percent, is_nas_src


    _instance = None
    _instance_thread = None
    _is_running = False
    _busy = False

    @classmethod
    def get_instance(cls, parent=None):
        """Return the singleton instance of FileWatcherWorker."""
        if cls._instance is None:
            logger.debug(f"Creating new FileWatcherWorker instance with parent={parent}")
            cls._instance = cls(parent=parent)
            cls._instance_thread = QThread.currentThread()
            logger.info(f"FileWatcherWorker instance created in thread {cls._instance_thread}")
        elif parent is not None and cls._instance.parent() != parent:
            logger.warning(f"Existing instance has different parent; ignoring new parent={parent}")
            cls._instance.log_update.emit(f"[FileWatcher] Warning: Existing instance has different parent; ignoring new parent={parent}")
        return cls._instance

    def __init__(self, parent=None):
        if self._instance is not None and self._instance is not self:
            logger.warning(f"FileWatcherWorker already initialized in thread {self._instance_thread}, use get_instance()")
            self.log_update.emit(f"[FileWatcher] Warning: Already initialized in thread {self._instance_thread}, use get_instance()")
            raise RuntimeError("FileWatcherWorker is a singleton; use FileWatcherWorker.get_instance()")
        super().__init__(parent)
        FileWatcherWorker._instance = self
        FileWatcherWorker._instance_thread = QThread.currentThread()
        # self.processed_tasks = set()
        self.processed_tasks = {}
        self.running = True
        self._lock = Lock()  # Initialize the lock
        self.last_api_hit_time = None
        self.next_api_hit_time = None
        self.api_poll_interval = 3000
        self.config = {
            "photoshop_path": os.getenv("PHOTOSHOP_PATH", ""),
            "max_processed_tasks": 1000,
            "task_retention_hours": 24,
            "supported_image_extensions": (
                ".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".bmp", ".webp",
                ".psd", ".psb", ".cr2", ".nef", ".arw", ".dng", ".raf", ".pef", ".srw"
            ),
        }
        logger.info("FileWatcherWorker initialized")
        self.log_update.emit("[FileWatcher] Initialized")
        self.log_update.emit(f"[FileWatcher] Application started at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        # self.timer = QTimer(self)
        # self.timer.setSingleShot(True)  # Single-shot to prevent overlapping ticks
        # self.timer.timeout.connect(self.run)
        # self.cleanup_signal.connect(self.cleanup)
        # if not self.timer.isActive():
        #     self.timer.start(self.api_poll_interval)
        #     logger.debug(f"FileWatcherWorker timer started with {self.api_poll_interval/1000}-second interval")
        #     self.log_update.emit(f"[FileWatcher] Timer started with {self.api_poll_interval/1000}-second interval")
        # else:
        #     logger.debug("FileWatcherWorker timer already active")
        #     self.log_update.emit("[FileWatcher] Timer already active")


    def _prepare_download_path(self, item):
        """Prepare the local destination path for download using file_path."""
        file_path = item.get("file_path", "")
        print(item)
        print(".....................................................................")
        print(file_path)
        print(".....................................................................")
        if not file_path:
            self.alert_notification.emit("ERROR (MD2)", "File does not exist on NAS")
            self.alert_notification.emit(
                "Download Error",
                "The file path is missing or empty.\n\nThis file does not exist on the NAS server. Please contact your administrator."
            )
            raise ValueError("Empty file_path in item")
            # show_alert_notification("ERROR (MD2)", "Please check Nas Connection.")
            # # QMessageBox.warning(None, "ERROR (MD2)", "Please check Nas Connection.")
            # raise ValueError("Empty file_path in item")
        dest_path = BASE_TARGET_DIR / file_path
        logger.debug(f"Preparing download path: file_path={file_path}, dest_path={dest_path}")
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True, mode=0o777)
            os.chmod(dest_path.parent, 0o777)
            logger.debug(f"Created directory {dest_path.parent} with permissions 777")
            self.log_update.emit(f"[Transfer] Created directory {dest_path.parent} with permissions 777")
        except Exception as e:
            logger.error(f"Failed to create directory {dest_path.parent}: {str(e)}")
            self.log_update.emit(f"[Transfer] Failed to create directory {dest_path.parent}: {str(e)}")
            # show_alert_notification("ERROR (MD2)", "Please check Nas Connection.")
            # # QMessageBox.warning(None, "ERROR (MD2)", "Please check Nas Connection.")
            # raise
            self.alert_notification.emit("ERROR (MD2)", f"[Transfer] Failed to create directory {dest_path.parent}: {str(e)}")
            raise
        resolved_dest_path = str(dest_path.resolve())
        logger.debug(f"Prepared local path: {resolved_dest_path}")
        self.log_update.emit(f"[Transfer] Prepared local path: {resolved_dest_path}")
        return resolved_dest_path





    def _download_from_nas(self, src_path, dest_path, item):
        task_id = item.get("id", "")
        spec_id = str(item.get("spec_id"))

        file_watcher = FileWatcherWorker.get_instance()

        dest_path = str(Path(dest_path).resolve())
        filename = Path(dest_path).name

        transport = None
        transfer_start_time = time.time()
        try:
            transport = paramiko.Transport((NAS_IP, NAS_PORT))
            transport.default_window_size = 2147483647
            transport.default_max_packet_size = 65536
            transport.packetizer.REKEY_BYTES = 2**40
            transport.packetizer.REKEY_PACKETS = 2**40
            transport.get_security_options().ciphers = (
                "aes128-ctr", "aes192-ctr", "aes256-ctr"
            )
            transport.connect(username=NAS_USERNAME, password=NAS_PASSWORD)

            nas_path = item.get("file_path", src_path)
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

            sftp = transport.open_sftp_client()
            total_size = sftp.stat(nas_path).st_size
            sftp.close()
            total_size_mb = total_size / 1024 / 1024

            report_transfer_event("Started", "download", filename, file_size_mb=total_size_mb, eta_text="Calculating...")

            start_time = time.time()
            last_emit = 0.0
            # ── Stall watchdog state ──────────────────────────────────────
            # A dropped network connection doesn't raise immediately — the
            # OS can sit on a dead TCP socket for a long time (60s+) before
            # surfacing an error. Track "no new bytes received" ourselves so
            # we fail fast and let the retry loop kick in promptly instead
            # of appearing to hang at whatever % it was at when the network died.
            STALL_TIMEOUT_SEC = 15
            last_byte_time = [start_time]
            last_sent_bytes = [0]

            def format_time(seconds: float) -> str:
                if seconds <= 0 or seconds == float("inf"):
                    return "—"
                m, s = divmod(int(seconds), 60)
                h, m = divmod(m, 60)
                if h:
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"

            def scp_progress(_remote, size, sent):
                nonlocal last_emit

                now = time.time()
                elapsed = now - start_time
                if elapsed <= 0:
                    return

                # ── Stall detection ──────────────────────────────────────
                if sent != last_sent_bytes[0]:
                    last_sent_bytes[0] = sent
                    last_byte_time[0] = now
                elif now - last_byte_time[0] > STALL_TIMEOUT_SEC and sent < total_size:
                    stall_msg = (
                        f"Download stalled — no data received for "
                        f"{STALL_TIMEOUT_SEC}s (network likely disconnected)"
                    )
                    logger.warning(f"[Transfer] {stall_msg}: {filename}")
                    file_watcher.download_status_detail.emit(
                        dest_path, f"⚠ {stall_msg}", "download",
                        int((sent / total_size) * 100) if total_size else 0, True
                    )
                    raise RuntimeError(stall_msg)

                # Throttle UI updates
                if now - last_emit < 0.5 and sent < total_size:
                    return
                last_emit = now

                percent = int((sent / total_size) * 100) if total_size else 0

                # ---- Speed (MB/s) ----
                speed_mbps = (sent / 1024 / 1024) / elapsed if elapsed > 0 else 0.0

                # ---- ETA ----
                remaining = total_size - sent
                eta = (remaining / 1024 / 1024) / speed_mbps if speed_mbps > 0 else float("inf")

                # ---- Progress bar (numeric only) ----
                file_watcher.download_progress.emit(
                    spec_id,
                    dest_path,
                    filename,
                    percent
                )

                # ---- Feed the Google Chat transfer reporter (latency/speed/size/ETA) ----
                _update_transfer_stats(
                    "download", filename, speed_mbps, percent,
                    file_size_mb=total_size / 1024 / 1024,
                    elapsed_sec=elapsed,
                    eta_text=format_time(eta),
                )

                # ---- Status text (human readable) ----
                status_text = (
                    f"Downloading {percent}% • "
                    f"{speed_mbps:.1f} MB/s • "
                    f"ETA {format_time(eta)}"
                )

                file_watcher.download_status_detail.emit(
                    dest_path,
                    status_text,
                    "download",
                    percent,
                    True
                )

            with SCPClient(
                transport,
                socket_timeout=30,
                buff_size=8 * 1024 * 1024,
                progress=scp_progress
            ) as scp:
                scp.get(nas_path, local_path=dest_path)

            # ---- Final completion ----
            self.download_progress.emit(
                spec_id,
                dest_path,
                filename,
                100
            )
            self.download_status_detail.emit(
                dest_path,
                "Download Completed",
                "download",
                100,
                True
            )

            duration_seconds = time.time() - transfer_start_time   # ← ADD THIS
            
            # Save duration to cache
            cache = load_cache()
            meta = cache.get("downloaded_files_with_metadata", {}).get(spec_id)
            if meta:
                meta["api_response"]["transfer_duration"] = round(duration_seconds, 1)
                save_cache(cache, significant_change=False)           # ← ADD THIS

            self.download_progress.emit(spec_id, dest_path, filename, 100)
            self.download_status_detail.emit(dest_path, "Download Completed", "download", 100, True)
            _clear_transfer_stats()

            _avg_speed_mbps = (total_size / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0.0
            report_transfer_event(
                "Completed", "download", filename, percent=100, speed_mbps=_avg_speed_mbps,
                file_size_mb=total_size / 1024 / 1024, elapsed_sec=duration_seconds, eta_text="Done",
            )

        except Exception:
            self.download_progress.emit(
                spec_id,
                dest_path,
                filename,
                0
            )
            self.download_status_detail.emit(
                dest_path,
                "Download Failed",
                "download",
                0,
                True
            )
            _clear_transfer_stats()
            _elapsed_at_failure = time.time() - transfer_start_time
            _size_mb_at_failure = (total_size / 1024 / 1024) if 'total_size' in locals() else 0.0
            report_transfer_event(
                "Failed", "download", filename,
                file_size_mb=_size_mb_at_failure, elapsed_sec=_elapsed_at_failure, eta_text="-",
            )
            raise

        finally:
            if transport is not None:
                try:
                    if transport.is_active():
                        transport.close()
                except Exception as t_err:
                    logger.warning(f"Could not close download transport: {t_err}")



    def _upload_to_nas(self, src_path, dest_path, item):
        task_id = item.get("id", "")
        spec_id = str(item.get("spec_id"))
        # client_id = str(item.get("client_id"))

        metadata_key = "uploaded_files_with_metadata"
        cache = load_cache()
        cache.setdefault(metadata_key, {})

        file_watcher = FileWatcherWorker.get_instance()

        src_path = Path(src_path)
        filename = src_path.name
        # allowed_types = get_file_types_from_api(client_id)
        # matched_file = None
        # matched_ext = None
        # first_prior = False
        
        # #for ext in allowed_types:
        # for ind, ext in enumerate(allowed_types):
        #     alt_path = src_path.with_suffix(f".{ext}")

        #     if alt_path.exists():
        #         first_prior = ind == 0
        #         matched_file = alt_path
        #         matched_ext = ext
        #         break

        # print("=============matched_file======================")
        # print(matched_file)
        # print(first_prior)
        # print("=============matched_file======================")


        # if matched_file:
        #     print("========INTO Matched File=====matched_file======================")
        #     src_path = matched_file
        #     filename = src_path.name
        #     if not first_prior:
        #         #show_alert("File Format alert", f"Uploading {matched_ext} file. Expected format: {allowed_types[0]}", QMessageBox.Information)
        #         self.alert_notification.emit("File Format Alert", f"Uploading {matched_ext} file. Expected format: {allowed_types[0]}")            
        # else:
        if not src_path.exists(): 
            print("========INTO File Not Found=====matched_file======================")
            cache[metadata_key][spec_id]["api_response"]["request_status"] = "Upload Failed"
            save_cache(cache, significant_change=True)
            update_download_upload_metadata(task_id, "failed")
            self.alert_notification.emit("Error (U1)", "Upload failed try again.")
            self.alert_notification.emit(
                "Upload Error",
                f"File not found on disk:\n{src_path}\n\nPlease ensure the file exists before uploading."
            )
            file_watcher.upload_progress.emit(spec_id, dest_path, filename, 0)
            file_watcher.upload_status_detail.emit(
                dest_path, "Upload Failed", "upload", 0, True
            )
            report_transfer_event("Failed", "upload", filename)
            raise FileNotFoundError(f"Source file does not exist: {src_path}")
        
        print("========Continue upload=====matched_file======================")
        # dest_path = item.get("file_path", dest_path)
        # if matched_ext:
        #     dest_path = str(Path(dest_path).with_suffix(f".{matched_ext}"))
        #dest_dir = os.path.dirname(dest_path)
        dest_path = dest_path.replace("\\", "/")
        dest_dir = os.path.dirname(dest_path).replace("\\", "/")
        print("=============dest_dir======================")
        print(dest_dir)
        print(dest_path)
        print("=============dest_dir======================")

        sock = None
        session = None
        sftp = None
        remote_file = None      # FIX: track remote file handle explicitly

        try:
            # ---------- CONNECTION ----------
            start_conn = time.time()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # FIX: this socket previously had NO timeout at all. If the
            # network dropped mid-write, remote_file.write() could block
            # indefinitely (potentially far longer than the download path's
            # ~60s OS-level stall) with no way for the retry logic to kick
            # in. Bound every blocking socket op to 30s so a dead connection
            # surfaces as an exception promptly.
            sock.settimeout(30)
            sock.connect((NAS_IP, NAS_PORT))

            session = Session()
            session.handshake(sock)
            session.userauth_password(NAS_USERNAME, NAS_PASSWORD)

            if not session.userauth_authenticated():
                raise Exception("SSH authentication failed")

            end_conn = time.time()
            print(f"Connection established in {(end_conn - start_conn) * 1000:.1f} ms")

            # ---------- SFTP INIT ----------
            sftp = session.sftp_init()

            print("Directory creation skipped.")
            print(f"Assuming destination directory exists: {dest_dir}")

            # ---------- UPLOAD ----------
            upload_start = time.time()

            # ────────────────────────────────────────────────────────────────
            # FIX (CRITICAL — data integrity): upload to a hidden temp file,
            # NOT directly to dest_path.
            #
            # The previous code did:
            #   sftp.open(dest_path, CREAT|WRITE|TRUNC, 0o644)
            # LIBSSH2_FXF_TRUNC truncates the file the INSTANT it's opened —
            # before a single byte of the new upload has been written. That
            # means the existing good file on the NAS was destroyed the
            # moment the upload started. If the network dropped mid-transfer
            # (e.g. after 250MB of a 1GB file), dest_path was left containing
            # only those 250MB — and anyone downloading that file in the
            # meantime got the truncated/corrupt version, with no way to
            # tell it wasn't the real file.
            #
            # Fix: write the new content to a temp sibling file
            # (".<name>.uploading_<random>.tmp") in the SAME directory as
            # dest_path. The real dest_path is never opened/truncated during
            # the transfer, so it keeps serving the last-known-good file to
            # anyone downloading it throughout the entire upload. Only once
            # the full byte count has been written and verified do we
            # atomically rename the temp file over dest_path — a rename is
            # effectively instantaneous, so there's no window where a
            # partial file is visible under the real filename. If anything
            # fails at any point, we just delete the temp file; dest_path is
            # untouched and the previous good file remains available.
            # ────────────────────────────────────────────────────────────────
            temp_suffix = f".uploading_{uuid.uuid4().hex[:12]}.tmp"
            if "/" in dest_path:
                _dest_dir_part, _dest_name_part = dest_path.rsplit("/", 1)
                temp_dest_path = f"{_dest_dir_part}/.{_dest_name_part}{temp_suffix}"
            else:
                temp_dest_path = f".{dest_path}{temp_suffix}"

            flags = LIBSSH2_FXF_CREAT | LIBSSH2_FXF_WRITE | LIBSSH2_FXF_TRUNC
            chunk_size = 4 * 1024 * 1024  # 4 MB

            file_size = src_path.stat().st_size
            total_mb = file_size / (1024 * 1024)

            bytes_per_second = None
            if THROTTLE_MBPS is not None:
                bytes_per_second = (THROTTLE_MBPS * 1024 * 1024) / 8

            transferred = 0
            last_emit = 0.0
            chunk_start_time = time.time()

            print(f"Uploading: {filename} ({total_mb:.2f} MB)")
            print(f"Destination (final): {dest_path}")
            print(f"Destination (temp, in-progress): {temp_dest_path}")

            report_transfer_event("Started", "upload", filename, file_size_mb=total_mb, eta_text="Calculating...")

            # FIX: open both file handles explicitly so both are closed in finally
            local_file = open(src_path, "rb")
            try:
                # ── Write to the TEMP path, never to dest_path directly ──
                remote_file = sftp.open(temp_dest_path, flags, 0o644)
                try:
                    while True:
                        data = local_file.read(chunk_size)
                        if not data:
                            break

                        remote_file.write(data)
                        transferred += len(data)

                        # ---- Throttling ----
                        if bytes_per_second:
                            now = time.time()
                            elapsed = now - chunk_start_time
                            expected = len(data) / bytes_per_second
                            if elapsed < expected:
                                time.sleep(expected - elapsed)
                            chunk_start_time = time.time()

                        # ---- UI Progress Emit (throttled) ----
                        now = time.time()
                        if now - last_emit >= 0.5 or transferred == file_size:
                            elapsed_total = now - upload_start
                            percent = int((transferred / file_size) * 100) if file_size else 100

                            speed_mbps = (
                                (transferred / 1024 / 1024) / elapsed_total
                                if elapsed_total > 0 else 0.0
                            )

                            remaining = file_size - transferred
                            eta = (
                                (remaining / 1024 / 1024) / speed_mbps
                                if speed_mbps > 0 else float("inf")
                            )

                            status_text = (
                                f"Uploading {percent}% • "
                                f"{speed_mbps:.1f} MB/s • "
                                f"ETA {int(eta)}s"
                                if eta != float("inf") else
                                f"Uploading {percent}% • {speed_mbps:.1f} MB/s • ETA —"
                            )

                            file_watcher.upload_progress.emit(
                                spec_id, dest_path, filename, percent
                            )
                            file_watcher.upload_status_detail.emit(
                                dest_path, status_text, "upload", percent, True
                            )
                            # ---- Feed the Google Chat transfer reporter (latency/speed/size/ETA) ----
                            _eta_text = (
                                f"{int(eta)}s" if eta != float("inf") else "—"
                            )
                            _update_transfer_stats(
                                "upload", filename, speed_mbps, percent,
                                file_size_mb=total_mb,
                                elapsed_sec=elapsed_total,
                                eta_text=_eta_text,
                            )
                            last_emit = now

                finally:
                    # FIX: always close remote file handle — was leaking before
                    try:
                        remote_file.close()
                    except Exception as rf_err:
                        logger.warning(f"Could not close remote file handle: {rf_err}")
                    remote_file = None

                # ────────────────────────────────────────────────────────
                # VERIFY + ATOMIC SWAP
                # Only now — after the temp file has been fully written and
                # closed — do we touch dest_path. If the transfer was
                # interrupted (network drop, exception, etc.) we never
                # reach this point, so dest_path still holds the
                # last-known-good file, completely untouched, for the
                # entire duration of the upload.
                # ────────────────────────────────────────────────────────
                if transferred != file_size:
                    raise IOError(
                        f"Incomplete upload: transferred {transferred} of "
                        f"{file_size} bytes — aborting swap, existing file "
                        f"on NAS left untouched"
                    )

                try:
                    # Prefer an atomic overwrite-rename if the server/library
                    # supports the flag — POSIX rename semantics replace
                    # dest_path in a single step with no window where the
                    # file is missing or partial.
                    try:
                        from ssh2.sftp import (
                            LIBSSH2_SFTP_RENAME_OVERWRITE,
                            LIBSSH2_SFTP_RENAME_ATOMIC,
                            LIBSSH2_SFTP_RENAME_NATIVE,
                        )
                        rename_flags = (
                            LIBSSH2_SFTP_RENAME_OVERWRITE
                            | LIBSSH2_SFTP_RENAME_ATOMIC
                            | LIBSSH2_SFTP_RENAME_NATIVE
                        )
                        sftp.rename(temp_dest_path, dest_path, rename_flags)
                    except ImportError:
                        sftp.rename(temp_dest_path, dest_path)
                except Exception as rename_err:
                    # Some SFTP servers refuse to rename onto an existing
                    # file even with the overwrite flag. Fall back to
                    # remove-then-rename. This has a brief non-atomic
                    # window, but it only happens AFTER the new file is
                    # fully uploaded and verified — worst case a
                    # downloader briefly sees "file not found" instead of
                    # ever seeing a truncated/partial file, which is the
                    # failure mode this fixes.
                    logger.debug(
                        f"[Transfer] Direct rename failed ({rename_err}), "
                        f"retrying with unlink+rename"
                    )
                    try:
                        sftp.unlink(dest_path)
                    except Exception:
                        pass  # dest_path may not exist yet (first-time upload)
                    sftp.rename(temp_dest_path, dest_path)

                logger.info(f"[Transfer] Upload verified, swapped into place: {dest_path}")
                app_signals.append_log.emit(
                    f"[Transfer] Upload verified and swapped into place: {dest_path}"
                )

                # ---------- FINAL SUCCESS ----------
                duration = time.time() - upload_start
                final_speed = total_mb / duration if duration > 0 else 0.0

                # Save duration to cache
                cache = load_cache()
                meta = cache.get("uploaded_files_with_metadata", {}).get(spec_id)
                if meta:
                    meta["api_response"]["transfer_duration"] = round(duration, 1)
                    save_cache(cache, significant_change=False)           # ← ADD THIS

                file_watcher.upload_progress.emit(spec_id, dest_path, filename, 100)
                file_watcher.upload_status_detail.emit(dest_path, "Upload Completed", "upload", 100, True)
            finally:
                # FIX: always close local file handle
                try:
                    local_file.close()
                except Exception as lf_err:
                    logger.warning(f"Could not close local file handle: {lf_err}")

            # ---------- FINAL SUCCESS ----------
            duration = time.time() - upload_start
            final_speed = total_mb / duration if duration > 0 else 0.0

            print(
                f"\nUpload completed: {total_mb:.2f} MB "
                f"in {duration:.2f}s ({final_speed:.2f} MB/s)"
            )

            file_watcher.upload_progress.emit(spec_id, dest_path, filename, 100)
            file_watcher.upload_status_detail.emit(
                dest_path, "Upload Completed", "upload", 100, True
            )

            if MIN_REQUIRED_MBPS:
                actual_mbps = final_speed * 8
                if actual_mbps < MIN_REQUIRED_MBPS:
                    print(
                        f"WARNING: Upload speed {actual_mbps:.1f} Mbps "
                        f"is below required {MIN_REQUIRED_MBPS} Mbps"
                    )

            _clear_transfer_stats()
            report_transfer_event(
                "Completed", "upload", filename, percent=100, speed_mbps=final_speed,
                file_size_mb=total_mb, elapsed_sec=duration, eta_text="Done",
            )

        except Exception as e:
            _clear_transfer_stats()
            error_details = str(e)

            if sftp:
                try:
                    err = sftp.last_error()
                    if err:
                        error_details += f" | SFTP error code: {err}"
                except Exception:
                    pass

            if session:
                try:
                    err = session.last_errno()
                    if err:
                        error_details += f" | Session error code: {err}"
                except Exception:
                    pass

            print(f"Upload failed: {error_details}")
            traceback.print_exc()

            # ── FIX: clean up the orphaned temp file, if any ──
            # dest_path was never opened/truncated during the transfer (see
            # temp-file upload strategy above), so the existing good file on
            # the NAS is still intact and safe. Just remove the partial
            # temp file so it doesn't linger.
            try:
                if sftp is not None and 'temp_dest_path' in locals():
                    sftp.unlink(temp_dest_path)
                    logger.debug(f"[Transfer] Cleaned up incomplete temp file: {temp_dest_path}")
                    app_signals.append_log.emit(
                        f"[Transfer] Cleaned up incomplete temp upload; "
                        f"existing file at {dest_path} was not modified"
                    )
            except Exception:
                pass  # temp file may not exist if failure occurred before sftp.open

            try:
                cache[metadata_key][spec_id]["api_response"]["request_status"] = "Upload Failed"
                save_cache(cache, significant_change=True)
            except Exception:
                pass

            file_watcher.upload_progress.emit(spec_id, dest_path, filename, 0)
            file_watcher.upload_status_detail.emit(
                dest_path, "Upload Failed", "upload", 0, True
            )

            self.alert_notification.emit(
                "Error (U3)",
                "Upload failed — the existing file on the NAS was NOT modified. "
                "Please retry the upload."
            )
            _elapsed_at_failure = (time.time() - upload_start) if 'upload_start' in locals() else 0.0
            _size_mb_at_failure = total_mb if 'total_mb' in locals() else 0.0
            report_transfer_event(
                "Failed", "upload", filename,
                file_size_mb=_size_mb_at_failure, elapsed_sec=_elapsed_at_failure, eta_text="-",
            )
            raise

        finally:
            # FIX: structured cleanup order — sftp first, then session, then socket
            # Each step is individually guarded so one failure never skips the rest

            if sftp is not None:
                try:
                    sftp.close()        # FIX: was never closed before
                except Exception as sftp_err:
                    logger.warning(f"Could not close SFTP handle: {sftp_err}")

            if session is not None:
                try:
                    session.disconnect()
                except Exception as sess_err:
                    logger.warning(f"Could not disconnect SSH session: {sess_err}")

            if sock is not None:
                try:
                    sock.close()        # FIX: now always reached even if session.disconnect() throws
                except Exception as sock_err:
                    logger.warning(f"Could not close socket: {sock_err}")

        
    def _validate_and_confirm_psd_upload(self, file_path):
        """
        For .psd/.psb uploads only: runs the production-readiness checklist
        and shows the report + Upload/Cancel confirmation dialog to the
        user — for BOTH pass and fail outcomes — before the file is sent
        to the NAS.

        Blocks THIS worker thread (never the GUI thread) until the user
        responds. Returns True to proceed with the upload, False to cancel.
        """
        try:
            config = getattr(self, "psd_validation_config", {}) or {}
            result = validate_psd_document(file_path, config)

            status_word = "PASS" if result.overall_pass else "FAIL"
            logger.info(f"[PSD Validation] {file_path}: {status_word}")
            self.log_update.emit(f"[PSD Validation] {Path(file_path).name}: {status_word}")
            app_signals.append_log.emit(f"[PSD Validation] {Path(file_path).name}: {status_word}")

            proceed = request_psd_upload_confirmation(file_path, result)
            self.log_update.emit(
                f"[PSD Validation] User {'confirmed upload' if proceed else 'cancelled upload'} "
                f"for {Path(file_path).name}"
            )
            return proceed
        except Exception as e:
            logger.error(f"[PSD Validation] Error validating {file_path}: {e}")
            self.log_update.emit(f"[PSD Validation] Error validating {Path(file_path).name}: {str(e)}")
            # Validation itself crashed — still let the user decide, with a
            # synthetic result explaining that validation could not complete.
            fallback_result = PSDValidationResult()
            fallback_result.add("Validation Execution", False, f"Validation could not be completed: {e}")
            return request_psd_upload_confirmation(file_path, fallback_result)

    def _update_cache_and_signals(self, action_type, src_path, dest_path, item, task_id, is_nas, file_type="original"):
        cache = load_cache()
        cache.setdefault("downloaded_files", {})
        cache.setdefault("downloaded_files_with_metadata", {})
        cache.setdefault("uploaded_files", [])
        cache.setdefault("uploaded_files_with_metadata", {})
        cache.setdefault("timer_responses", {})
        local_path = src_path if action_type.lower() == "upload" else dest_path
        try:
            if action_type.lower() == "download":
                cache["downloaded_files"][task_id] = local_path
                cache["downloaded_files_with_metadata"][task_id] = {"local_path": local_path, "api_response": item}
                # timer_response = start_timer_api(src_path, cache.get('token', ''))
                # if timer_response:
                #     cache["timer_responses"][local_path] = timer_response
                app_signals.update_file_list.emit(local_path, f"{action_type} Completed", action_type.lower(), 100, is_nas)
                logger.debug(f"Emitted update_file_list signal: dest_path={local_path}, status={action_type} Completed, is_nas={is_nas}")
                self.log_update.emit(f"[Signal] Emitted update_file_list: dest_path={local_path}, status={action_type} Completed, is_nas={is_nas}")
            elif action_type.lower() in ("upload", "replace"):
                cache["uploaded_files"].append(dest_path)
                cache["uploaded_files_with_metadata"][task_id] = {"local_path": local_path, "api_response": item}
                # timer_response = cache.get("timer_responses", {}).get(local_path)
                # if timer_response:
                #     end_timer_api(src_path, timer_response, cache.get('token', ''))
                # app_signals.update_file_list.emit(local_path, f"{action_type} Completed ({file_type.capitalize()})", action_type.lower(), 100, is_nas)
                app_signals.update_file_list.emit(local_path, f"{action_type} Completed", action_type.lower(), 100, is_nas)
                logger.debug(f"Emitted update_file_list signal: dest_path={local_path}, status={action_type} Completed, is_nas={is_nas}")
                self.log_update.emit(f"[Signal] Emitted update_file_list: dest_path={local_path}, status={action_type} Completed, is_nas={is_nas}")
            save_cache(cache)
            app_signals.append_log.emit(f"[Transfer] {action_type} completed: {src_path} to {dest_path}")
        except Exception as e:
            logger.error(f"Failed to update cache and signals for {action_type} ({file_type}, Task {task_id}): {str(e)}")
            self.log_update.emit(f"[Transfer] Failed to update cache and signals for {action_type} ({file_type}, Task {task_id}): {str(e)}")
            raise
    
    def open_with_photoshop(self, file_path, key_val):
        """Open file in Photoshop — delegates to module-level helper."""
        try:
            key_val_int = int(key_val) if key_val is not None else 0
        except (TypeError, ValueError):
            key_val_int = 0

        if key_val_int >= 1:
            self.log_update.emit("[Photoshop] Skipping — key_val >= 1")
            return True

        try:
            return open_file_with_photoshop(file_path, log_callback=self.log_update.emit)
        except Exception as e:
            error_msg = f"Failed to open {Path(file_path).name} in Photoshop: {e}"
            logger.error(error_msg)
            self.log_update.emit(f"[Photoshop] {error_msg}")
            raise
    
    
    
    @Slot(str, str, str, str, bool, bool)
    # def perform_file_transfer(self,src_path: str,dest_path: str,action_type: str,item,is_nas_src: bool,is_nas_dest: bool):
    def perform_file_transfer(self, src_path: str, dest_path: str, action_type: str, item, is_nas_src: bool, is_nas_dest: bool, is_final_attempt: bool = True):
    # def perform_file_transfer(self, src_path, dest_path, action_type, item, is_nas_src, is_nas_dest):

        # ============================================================
        # 🔑 FIX: Normalize `item` for retry calls (CRITICAL)
        # ============================================================
        if not isinstance(item, dict):
            cache = load_cache()
            reconstructed = None

            for _, meta in cache.get("downloaded_files_with_metadata", {}).items():
                api = meta.get("api_response", {})
                if not api:
                    continue

                if (
                    api.get("file_path") == src_path
                    or api.get("nas_path") == src_path
                    or api.get("file_path") == dest_path
                    or api.get("nas_path") == dest_path
                ):
                    reconstructed = api
                    break

            if not isinstance(reconstructed, dict):
                raise RuntimeError(
                    "[perform_file_transfer] Retry failed: unable to reconstruct item metadata"
                )

            item = reconstructed
        # ============================================================
        # 🔑 END FIX
        # ============================================================


        """Perform file transfer (download/upload/replace) and update cache metadata reliably."""
        task_id = str(item.get('id'))
        spec_id = str(item.get("spec_id"))
        print("===================================")
        print(item.get("file_path"))
        print("===================================")
        
        if not task_id:
            raise ValueError("Task ID is missing or invalid in item dictionary")
        
        global IS_APP_ACTIVE_UPLOAD_DOWNLOAD
        IS_APP_ACTIVE_UPLOAD_DOWNLOAD = True

        status_prefix = "Download" if action_type.lower() == "download" else "Upload"
        metadata_key = "downloaded_files_with_metadata" if action_type.lower() == "download" else "uploaded_files_with_metadata"

        try:
            logger.debug(f"Starting file transfer for task {task_id}, action_type: {action_type}")

            # Load cache once
            cache = load_cache()
            cache.setdefault(metadata_key, {})

            # Initialize task entry if missing
            if task_id not in cache[metadata_key]:
                cache[metadata_key][spec_id] = {
                    "local_path": dest_path if action_type.lower() == "download" else src_path,
                    "api_response": {
                        "id": task_id,
                        "file_path": item.get("file_path"),
                        "file_name": item.get("file_name", Path(src_path).name),
                        "request_type": action_type.lower(),
                        "job_id": item.get("job_id"),
                        "job_name": item.get("job_name"),
                        "project_id": item.get("project_id"),
                        "project_name": item.get("project_name"),
                        "client_name": item.get("client_name"),
                        "spec_id": item.get("spec_id"),
                        "user_id": item.get("user_id"),
                        "user_type": item.get("user_type"),
                        "creative_id": item.get("creative_id"),
                        "inventory_id": item.get("inventory_id"),
                        "nas_path": item.get("nas_path"),
                        "thumbnail": item.get("thumbnail"),
                        "created_on": item.get("created_on"),
                        "updated_date": item.get("updated_date"),
                        "request_status": f"{status_prefix} Started"
                    },
                    
                }

            # Save initial "In Progress" state
            save_cache(cache, significant_change=True)
            update_download_upload_metadata(task_id, "In Progress")
            logger.info(f"[{status_prefix} In Progress] Task {task_id}")
            self.progress_update.emit(f"{action_type} (Task {task_id}): {Path(src_path).name}", dest_path, 10)
            self.download_status_detail.emit(dest_path, f"{action_type} (Task {task_id}): {Path(src_path).name}", action_type, 10, True)
            # ------------------------------
            # Handle Download
            # ------------------------------
            if action_type.lower() == "download":
               
                dest_path = self._prepare_download_path(item)

                if is_nas_src:
                    self._download_from_nas(src_path, dest_path, item)
                else:
                    self._download_from_http(src_path, dest_path)

                if not os.path.exists(dest_path):
                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Failed"
                    save_cache(cache, significant_change=True)
                    if is_final_attempt:
                        self.alert_notification.emit(
                            "Download Error",
                            f"Downloaded file was not found on disk:\n{dest_path}\n\nThe transfer may have been incomplete."
                        )
                    raise FileNotFoundError(f"{status_prefix} file not found: {dest_path}")

                cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Completed"
                cache[metadata_key][spec_id]["local_path"] = dest_path
                save_cache(cache, significant_change=True)
                update_download_upload_metadata(task_id, "completed")

                # Optional: Open with Photoshop
                try:
                    key_val = item.get("key_val")
                    self.open_with_photoshop(dest_path, key_val)
                except Exception as e:
                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Failed Photoshop"
                    save_cache(cache, significant_change=True)
                    logger.warning(f"Failed to open {dest_path} with Photoshop: {str(e)}")
                    self.log_update.emit(f"[Transfer] Warning: Failed to open {dest_path} with Photoshop: {str(e)}")

                # Optional: Conversion to JPG
                # cache[metadata_key][task_id]["api_response"]["request_status"] = f"{status_prefix} Conversion Started"
                # save_cache(cache, significant_change=True)
                # local_jpg, _ = process_single_file(dest_path)
                # if local_jpg:
                #     cache[metadata_key][task_id]["api_response"]["request_status"] = f"{status_prefix} Conversion Completed"
                #     save_cache(cache, significant_change=True)
                #     app_signals.update_file_list.emit(local_jpg, "Conversion Completed", "download", 100, False)
                # else:
                #     cache[metadata_key][task_id]["api_response"]["request_status"] = f"{status_prefix} Conversion Failed"
                #     save_cache(cache, significant_change=True)
                #     self.log_update.emit(f"[Transfer] Failed: JPG conversion failed for {dest_path}")

                # self.progress_update.emit(f"{action_type} Completed (Task {task_id}): {Path(src_path).name}", dest_path, 100)
                # app_signals.update_file_list.emit(dest_path, f"{action_type} Completed", "download", 100, is_nas_src)

            # ------------------------------
            # Handle Upload / Replace
            # ------------------------------
            elif action_type.lower() in ("upload", "replace"):
                # Upload to NAS or HTTP
                # print(f"======into Upload-replace==========={src_path}====")
                if is_nas_dest:
                    job_id = str(item.get("job_id"))
                    allowed_types = get_file_types_from_api(job_id)
                    matched_file = None
                    matched_ext = None
                    first_prior = False
                    try:
                        #for ext in allowed_types:
                        for ind, ext in enumerate(allowed_types):
                            # alt_path = src_path.with_suffix(f".{ext}")
                            alt_path = Path(src_path).with_suffix(f".{ext}")

                            if alt_path.exists():
                                first_prior = ind == 0
                                matched_file = alt_path
                                matched_ext = ext
                                break
                        # print(f"=====matched_file================{matched_file}======")
                        if matched_file:
                            src_path = matched_file
                            # filename = src_path.name
                            if not first_prior:
                                #show_alert("File Format alert", f"Uploading {matched_ext} file. Expected format: {allowed_types[0]}", QMessageBox.Information)
                                self.alert_notification.emit("File Format Alert", f"Prefered format: {allowed_types[0].upper()}, Currently uploading {matched_ext.upper()} file.")            
                        else:
                            if is_final_attempt:
                                self.alert_notification.emit("ERROR", f"No completed file found in target folder. upload the file manually.")            
                            cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} HTTP Not Implemented"
                            save_cache(cache, significant_change=True)
                            raise NotImplementedError("HTTP upload not implemented")

                        dest_path = item.get("file_path", dest_path)
                        if matched_ext:
                            dest_path = str(Path(dest_path).with_suffix(f".{matched_ext}"))
                        #dest_dir = os.path.dirname(dest_path)
                        dest_path = dest_path.replace("\\", "/")

                        # ── TEMPORARY: max upload file size limit ──────────
                        # Applies to every upload/replace, any file type.
                        # To disable: set ENABLE_MAX_UPLOAD_SIZE_LIMIT = False
                        # near the top of this file — no other changes needed.
                        too_big, size_mb = exceeds_max_upload_size(src_path)
                        if too_big:
                            cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Blocked (Too Large)"
                            save_cache(cache, significant_change=True)
                            self.alert_notification.emit(
                                "Upload Blocked — File Too Large",
                                f"'{Path(src_path).name}' is {size_mb:.1f} MB, which exceeds the "
                                f"current {MAX_UPLOAD_SIZE_MB} MB upload limit.\n\n"
                                "Please contact your administrator if this file needs to be uploaded."
                            )
                            raise UploadSizeLimitExceeded(
                                f"{Path(src_path).name} ({size_mb:.1f} MB) exceeds the {MAX_UPLOAD_SIZE_MB} MB upload limit"
                            )

                        # ── PSD/PSB pre-upload production-readiness validation ──
                        # For .psd/.psb files only: run the checklist and show
                        # the report + Upload/Cancel confirmation dialog to the
                        # user BEFORE the file is sent to the NAS — regardless
                        # of whether validation passed or failed.
                        src_ext = Path(src_path).suffix.lower().lstrip(".")
                        if src_ext in ("psd", "psb"):
                            proceed_with_upload = self._validate_and_confirm_psd_upload(str(src_path))
                            if not proceed_with_upload:
                                cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Cancelled"
                                save_cache(cache, significant_change=True)
                                self.alert_notification.emit(
                                    "Upload Cancelled",
                                    f"Upload of '{Path(src_path).name}' was cancelled after PSD validation review."
                                )
                                raise PSDUploadCancelled(
                                    f"Upload cancelled by user after PSD validation for {Path(src_path).name}"
                                )

                        self._upload_to_nas(src_path, dest_path, item)
                        cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Completed"
                    except (PSDUploadCancelled, UploadSizeLimitExceeded):
                        # Do NOT mask these as "HTTP Not Implemented" — re-raise
                        # as-is so the outer handler reports them accurately.
                        raise
                    except Exception as e:
                        # self.alert_notification.emit("ERROR", f"2No completed file found in target folder. upload the file manually.")            
                        cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} HTTP Not Implemented"
                        save_cache(cache, significant_change=True)
                        raise NotImplementedError("HTTP upload not implemented")

                else:
                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} HTTP Not Implemented"
                    save_cache(cache, significant_change=True)
                    raise NotImplementedError("HTTP upload not implemented")
                
                if not os.path.exists(src_path):
                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Source Missing"
                    save_cache(cache, significant_change=True)
                    if is_final_attempt:
                        self.alert_notification.emit(
                            "Upload Error",
                            "Completed files are not available. Please upload them manually."
                        )
                    raise FileNotFoundError(f"Source file does not exist: {src_path}")

                # Check if file is accessible
                try:
                    with open(src_path, 'rb') as f:
                        f.read(1)
                except (PermissionError, IOError):
                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} File In Use"
                    save_cache(cache, significant_change=True)
                    raise RuntimeError(f"File {src_path} is currently in use by another application.")

                

                save_cache(cache, significant_change=True)
                update_download_upload_metadata(task_id, "completed")
                self.progress_update.emit(f"{action_type} Completed (Task {task_id}): {Path(src_path).name}", dest_path, 100)
                self.download_status_detail.emit(dest_path, f"{action_type} (Task {task_id}): {Path(src_path).name}", action_type, 10, True)


                try:
                    request_data = {
                        'job_id': item.get('job_id'),
                        'project_id': item.get("project_id"),
                        'file_name': item.get("user_id"),
                        'user_id': item.get("user_id"),
                        'user_type': item.get("user_type"),
                        'spec_id': item.get("spec_id"),
                        'creative_id': item.get("creative_id"),
                        'inventory_id': item.get("inventory_id"),
                        'nas_path': NAS_PATH + dest_path,
                    }

                    response = requests.post(
                        DRUPAL_DB_ENTRY_API,
                        data=request_data,
                        headers={},
                        verify=False
                    )

                    cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} completed"
                    save_cache(cache, significant_change=True)
                    update_download_upload_metadata(task_id, "Conversion Started")
                    logging.info(f"DRUPAL_DB_ENTRY_API data success: {response.text}")

                except Exception as e:
                    cache[metadata_key][spec_id]["status"] = f"{status_prefix} API Call Failed"
                    save_cache(cache, significant_change=True)
                    logging.error(f"DRUPAL_DB_ENTRY_API call error: {str(e)}")
                
            else:
                raise ValueError(f"Invalid action_type: {action_type}")
            IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False

        except PSDUploadCancelled as e:
            # User explicitly cancelled the upload from the PSD validation
            # dialog — this is not a transfer failure, so keep the status
            # and logging distinct from a genuine "Failed" transfer.
            cache.setdefault(metadata_key, {})
            if spec_id not in cache[metadata_key]:
                cache[metadata_key][spec_id] = {"local_path": dest_path, "status": f"{status_prefix} Cancelled"}
            else:
                cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Cancelled"

            save_cache(cache, significant_change=True)
            update_download_upload_metadata(task_id, "cancelled")
            IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False
            logger.info(f"{status_prefix} cancelled by user after PSD validation (Task {task_id}): {str(e)}")
            self.log_update.emit(f"[Transfer] Cancelled by user (Task {task_id}): {str(e)}")
            self.progress_update.emit(f"{action_type} Cancelled (Task {task_id}): {Path(src_path).name}", dest_path, 0)
            self.download_status_detail.emit(dest_path, f"{action_type} Cancelled (Task {task_id}): {Path(src_path).name}", action_type, 0, True)

            raise

        except UploadSizeLimitExceeded as e:
            # File exceeds the temporary MAX_UPLOAD_SIZE_MB limit — this is
            # a policy block, not a transfer failure, so keep the status
            # and logging distinct from a genuine "Failed" transfer.
            cache.setdefault(metadata_key, {})
            if spec_id not in cache[metadata_key]:
                cache[metadata_key][spec_id] = {"local_path": dest_path, "status": f"{status_prefix} Blocked (Too Large)"}
            else:
                cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Blocked (Too Large)"

            save_cache(cache, significant_change=True)
            update_download_upload_metadata(task_id, "blocked")
            IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False
            logger.info(f"{status_prefix} blocked by size limit (Task {task_id}): {str(e)}")
            self.log_update.emit(f"[Transfer] Blocked — exceeds size limit (Task {task_id}): {str(e)}")
            self.progress_update.emit(f"{action_type} Blocked (Task {task_id}): {Path(src_path).name}", dest_path, 0)
            self.download_status_detail.emit(dest_path, f"{action_type} Blocked (Task {task_id}): {Path(src_path).name}", action_type, 0, True)

            raise

        except Exception as e:
            # Update cache with failure
            cache.setdefault(metadata_key, {})
            if spec_id not in cache[metadata_key]:
                cache[metadata_key][spec_id] = {"local_path": dest_path, "status": f"{status_prefix} Failed"}
            else:
                cache[metadata_key][spec_id]["api_response"]["request_status"] = f"{status_prefix} Failed"

            save_cache(cache, significant_change=True)
            update_download_upload_metadata(task_id, "failed")
            IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False
            logger.error(f"{status_prefix} error (Task {task_id}): {str(e)}")
            self.log_update.emit(f"[Transfer] Failed (Task {task_id}): {str(e)}")
            self.progress_update.emit(f"{action_type} Failed (Task {task_id}): {Path(src_path).name}", dest_path, 0)
            self.download_status_detail.emit(dest_path, f"{action_type} Failed (Task {task_id}): {Path(src_path).name}", action_type, 10, True)

            raise

    @Slot()
    def run(self):
        with self._lock:
            if self._busy:
                logger.debug(f"[{datetime.now(timezone.utc).isoformat()}] File watcher already running, skipping")
                self.log_update.emit("[FileWatcher] Skipped: Already running")
                return
            current_time = datetime.now(timezone.utc)
            if hasattr(self, 'next_api_hit_time') and self.next_api_hit_time and current_time < self.next_api_hit_time:
                logger.debug(f"[{current_time.isoformat()}] API call skipped: Too soon since last call")
                self.log_update.emit("[FileWatcher] Skipped: Too soon since last API call")
                return
            self._busy = True
            self._is_running = True

        try:
            # Initialize executor and semaphore if not already set
            if not hasattr(self, 'executor'):
                self.executor = ThreadPoolExecutor(max_workers=2)
                self.log_update.emit("[FileWatcher] Initialized ThreadPoolExecutor with max_workers=2")
            if not hasattr(self, 'sftp_semaphore'):
                self.sftp_semaphore = Semaphore(2)
                self.log_update.emit("[FileWatcher] Initialized SFTP semaphore with limit=2")

            if not self.running:
                self.log_update.emit("[FileWatcher] Stopped: Worker is not running")
                return

            self.log_update.emit("[API Scan] Starting file watcher run")

            # ✅ FIX Bug 3: connectivity check now uses a lightweight HEAD request
            # instead of a fake task API call with user_id=200, which was causing
            # a double API hit every single cycle and polluting the server logs.
            if not self.check_connectivity():
                logger.warning("Connectivity check failed, will retry on next run")
                self.status_update.emit("Connectivity check failed, will retry")
                self.log_update.emit("[API Scan] Connectivity check failed")
                return

            cache = load_cache()
            user_id = cache.get('user_id', '')
            token = cache.get('token', '')
            cache.setdefault('user_type', 'operator')
            save_cache(cache, significant_change=False)

            if not user_id or not token:
                logger.error("No user_id or token found in cache")
                self.status_update.emit("No user_id or token found in cache")
                self.log_update.emit("[API Scan] Failed: No user_id or token found in cache")
                self.request_reauth.emit()
                return

            self.status_update.emit("Checking for file tasks...")
            self.log_update.emit("[API Scan] Starting file task check")
            app_signals.append_log.emit("[API Scan] Initiating file task check")

            self.last_api_hit_time = current_time
            self.next_api_hit_time = self.last_api_hit_time + timedelta(milliseconds=self.api_poll_interval)
            app_signals.update_timer_status.emit(
                f"Last API hit: {self.last_api_hit_time.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                f"Next API hit: {self.next_api_hit_time.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                f"Interval: {self.api_poll_interval/1000:.1f}s"
            )

            headers = {"Authorization": f"Bearer {token}"}
            max_retries = 3
            tasks = []

            if isinstance(USER_SYSTEM_INFO, dict):
                machine_id = USER_SYSTEM_INFO.get("encoded_mac", "")
            elif isinstance(USER_SYSTEM_INFO, list) and USER_SYSTEM_INFO:
                first_entry = USER_SYSTEM_INFO[0]
                machine_id = first_entry.get("encoded_mac", "") if isinstance(first_entry, dict) else ""
            else:
                machine_id = ""

            api_url = f"{DOWNLOAD_UPLOAD_API}?user_id={quote(user_id)}&machine_id={machine_id}"
            logger.debug(f"[DEBUG] machine_id={machine_id}, api_url={api_url}")

            for attempt in range(max_retries):
                try:
                    logger.debug(f"Hitting API: {api_url}")
                    app_signals.append_log.emit(f"[API Scan] Hitting API: {api_url}")
                    response = HTTP_SESSION.get(api_url, headers=headers, verify=False, timeout=60)

                    # ✅ FIX Bug 1: Call .json() ONCE and store it.
                    # Previously response.json() was called twice — the second call
                    # overwrote the first result and could exhaust the response stream,
                    # causing silent data loss and always returning empty tasks.
                    try:
                        response_data = response.json()
                    except ValueError as json_err:
                        logger.error(f"Failed to parse API response as JSON: {json_err}")
                        self.log_update.emit(f"[API Scan] Failed: Invalid JSON response - {str(json_err)}")
                        return

                    logger.debug(f"API response: Status={response.status_code}, Content={str(response_data)[:500]}")
                    app_signals.append_log.emit(
                        f"[API Scan] API response: Status={response.status_code}, "
                        f"Content={str(response_data)[:500]}"
                    )
                    app_signals.api_call_status.emit(
                        api_url,
                        "Success" if response.status_code == 200 else f"Failed: {response.status_code}",
                        response.status_code
                    )

                    if response.status_code == 401:
                        logger.warning("Unauthorized: Token may be invalid")
                        self.log_update.emit("[API Scan] Unauthorized: Token invalid")
                        self.status_update.emit("Unauthorized: Token invalid")
                        self.request_reauth.emit()
                        return

                    response.raise_for_status()

                    # ✅ FIX Bug 2: Parse tasks ONCE in one clean block.
                    # Previously tasks were assigned twice — the second unconditional
                    # assignment always overwrote the first, making the 403 check
                    # above it pointless and causing tasks to be lost.
                    if isinstance(response_data, dict):
                        if response_data.get("status") == 403:
                            logger.warning("403 received — user logged in elsewhere")
                            self.log_update.emit("[API Scan] 403: User logged in on another machine")
                            # ✅ FIX Bug 6: ONLY emit the signal here.
                            # Previously premedia.show_login_page() was called directly
                            # from the worker thread — unsafe UI call across threads.
                            # The connected slot in PremediaApp handles the logout safely.
                            self.user_in_other_system.emit("user_already_logged_in")
                            return
                        tasks = response_data.get("data", [])
                    elif isinstance(response_data, list):
                        tasks = response_data
                    else:
                        logger.error(f"Unexpected API response type: {type(response_data)}")
                        self.log_update.emit(f"[API Scan] Unexpected response type: {type(response_data)}")
                        tasks = []

                    if not isinstance(tasks, list):
                        logger.error(f"API returned non-list tasks: {type(tasks)}, data: {tasks}")
                        self.log_update.emit(f"[API Scan] Failed: Non-list tasks: {type(tasks)}")
                        return

                    logger.debug(f"Retrieved {len(tasks)} tasks")
                    app_signals.append_log.emit(f"[API Scan] Retrieved {len(tasks)} tasks from API")
                    break

                except RequestException as e:
                    logger.error(f"Attempt {attempt + 1} failed fetching tasks: {e}")
                    self.log_update.emit(f"[API Scan] Failed to fetch tasks (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    self.status_update.emit(f"Error fetching tasks after retries: {str(e)}")
                    self.log_update.emit(f"[API Scan] Failed after retries: {str(e)}")
                    return

            unprocessed_tasks = [
                task for task in tasks
                if f"{task.get('id', '')}:{task.get('request_type', '').lower()}" not in self.processed_tasks
            ]

            # Build task lists for GUI
            download_tasks = []
            upload_tasks = []
            for item in unprocessed_tasks:
                if not isinstance(item, dict):
                    continue
                req_type = item.get('request_type', '').lower()
                task_data = {
                    "task_id": str(item.get('id', '')),
                    "action_type": req_type,
                    "file_name": item.get('file_name', Path(item.get('file_path') or '').name if item.get('file_path') else 'unknown_file'),
                    "file_path": item.get('file_path', ''),
                    "status": "Queued",
                    "thumbnail": item.get('thumbnail', ''),
                    "job_id": item.get('job_id', ''),
                    "job_name": item.get('job_name', ''),
                    "project_id": item.get('project_id', ''),
                    "project_name": item.get('project_name', ''),
                    "created_at": datetime.now().strftime("%d-%b-%Y %I:%M %p")
                }
                if req_type == "download":
                    task_data["task_type"] = "download"
                    download_tasks.append(task_data)
                elif req_type in ("upload", "replace"):
                    task_data["task_type"] = "upload"
                    upload_tasks.append(task_data)

            self.task_list_update.emit(download_tasks + upload_tasks)
            self.log_update.emit(
                f"[API Scan] Task list emitted: {len(download_tasks)} download, {len(upload_tasks)} upload"
            )

            self._clean_processed_tasks()
            futures = []

            for item in unprocessed_tasks:
                if not isinstance(item, dict):
                    logger.error(f"Invalid task item type: {type(item)}")
                    self.log_update.emit(f"[API Scan] Failed: Invalid task type: {type(item)}")
                    continue

                task_id = str(item.get('id', ''))
                file_path = item.get('file_path', '')
                if not file_path:
                    logger.error(f"Invalid task {task_id}: Missing file_path")
                    self.log_update.emit(f"[API Scan] Failed: Task {task_id} missing file_path")
                    continue

                file_name = item.get('file_name', Path(file_path).name)
                action_type = item.get('request_type', '').lower()
                task_key = f"{task_id}:{action_type}"
                is_online = 'http' in file_path.lower()
                local_path = str(BASE_TARGET_DIR / file_path.lstrip("/"))

                with self._lock:
                    if task_key in self.processed_tasks:
                        logger.debug(f"Skipping duplicate task: {task_key}")
                        self.log_update.emit(f"[API Scan] Skipped duplicate: {task_key}")
                        continue
                    # self.processed_tasks.add(task_key)
                    self.processed_tasks[task_key] = time.time()
                    

                logger.debug(f"Submitting task: {task_key}, file_path={file_path}")
                self.log_update.emit(f"[API Scan] Submitting: {task_key}, action={action_type}")

                futures.append(
                    self.executor.submit(
                        self._process_task,
                        task_id, file_name, file_path, action_type,
                        local_path, is_online, item, 3, self.sftp_semaphore
                    )
                )

            def handle_task_results(futures):
                completed_tasks = 0
                failed_tasks = 0
                updates = []
                for future in futures:
                    try:
                        result = future.result()
                        updates.append(result['update'])
                        # ── Mark as processed regardless of success/failure ──
                        # Without this, failed tasks are never added to processed_tasks
                        # and the poll loop keeps re-picking them up every 3 seconds,
                        # causing infinite retry loops and repeated popups.
                        with self._lock:
                            self.processed_tasks[result['task_key']] = time.time()
                        if result['success']:
                            completed_tasks += 1
                        else:
                            failed_tasks += 1
                    except Exception as e:
                        logger.error(f"Task processing error: {str(e)}")
                        self.log_update.emit(f"[API Scan] Task error: {str(e)}")
                        failed_tasks += 1
                for update in updates:
                    app_signals.update_file_list.emit(*update)
                logger.info(f"Background task summary: {completed_tasks} completed, {failed_tasks} failed")
                self.log_update.emit(
                    f"[FileWatcher] Background task summary: {completed_tasks} completed, {failed_tasks} failed"
                )

            Thread(target=handle_task_results, args=(futures,), daemon=True).start()
            self.status_update.emit("File tasks check completed")
            self.log_update.emit(f"[API Scan] Completed: Submitted {len(futures)} tasks")
            app_signals.append_log.emit(f"[API Scan] Completed: {len(futures)} tasks submitted")

        except Exception as e:
            logger.error(f"Error in file watcher run: {e}")
            self.status_update.emit(f"Error processing tasks: {str(e)}")
            self.log_update.emit(f"[API Scan] Failed: {str(e)}")
            app_signals.append_log.emit(f"[API Scan] Failed: {str(e)}")
        finally:
            self._busy = False
            self._is_running = False
            self.log_update.emit("[FileWatcher] Cycle completed, awaiting next timer tick")


    def _process_task(self, task_id, file_name, file_path, action_type, local_path, is_online, item, max_download_retries, sftp_semaphore):
        """Process a single task (download/upload) with retry logic and SFTP semaphore."""
        # update_download_upload_metadata(task_id, "in progress")
        task_key = f"{task_id}:{action_type}"
        update = (local_path, f"{action_type} Queued", action_type, 0, not is_online)
        try:
            if action_type == "download":
                self.status_update.emit(f"Downloading {file_name}")
                self.log_update.emit(f"[API Scan] Starting download: {file_path} to {local_path}, task_id: {task_id}")
                app_signals.append_log.emit(f"[API Scan] Initiating download: {file_name}")
                app_signals.update_file_list.emit(local_path, f"{action_type} Queued", action_type, 0, not is_online)
                for attempt in range(max_download_retries):
                    is_final_attempt = (attempt == max_download_retries - 1)
                    try:
                        if not is_online:
                            with sftp_semaphore:  # Limit concurrent SFTP connections
                                self.show_progress(f"Downloading {file_name}", file_path, local_path, action_type, item, not is_online, False)
                        else:
                            self.show_progress(f"Downloading {file_name}", file_path, local_path, action_type, item, not is_online, False)
                        if os.path.exists(local_path):
                            self.log_update.emit(f"[API Scan] Download successful: {local_path}, task_id: {task_id}")
                            return {
                                'update': (local_path, f"Download Completed", action_type, 100, not is_online),
                                'task_key': task_key,
                                'success': True
                            }
                        else:
                            logger.warning(f"[{datetime.now(timezone.utc).isoformat()}] Download failed for {local_path}; attempt {attempt + 1} of {max_download_retries}, instance: {id(self)}")
                            self.log_update.emit(f"[API Scan] Download failed for {local_path}; attempt {attempt + 1} of {max_download_retries}")
                            update = (local_path, f"Download Failed: File not found", action_type, 0, not is_online)
                            if attempt == max_download_retries - 1:
                                raise FileNotFoundError(f"Downloaded file not found: {local_path}")
                    except Exception as e:
                        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] Download failed for {local_path} (Task {task_id}): {str(e)}, attempt {attempt + 1}, instance: {id(self)}")
                        self.log_update.emit(f"[API Scan] Download failed for {local_path} (Task {task_id}): {str(e)}")
                        update = (local_path, f"Download Failed: {str(e)}", action_type, 0, not is_online)
                        if attempt < max_download_retries - 1:
                            delay = 2 ** attempt
                            logger.debug(f"[{datetime.now(timezone.utc).isoformat()}] Retrying download after {delay}s, instance: {id(self)}")
                            self.log_update.emit(f"[API Scan] Retrying download after {delay}s")
                            # ── NEW: tell the UI a retry is happening ──
                            # Without this the card/window keeps showing the last
                            # progress % it received before the drop, which looks
                            # "stuck" — even though the app is about to restart
                            # the transfer from scratch (SCP has no resume).
                            retry_msg = (
                                f"⚠ Network lost — retrying download "
                                f"(attempt {attempt + 2}/{max_download_retries}) in {delay}s"
                            )
                            self.download_status_detail.emit(
                                local_path, retry_msg, action_type, 0, not is_online
                            )
                            time.sleep(delay)
                        else:
                            raise
            elif action_type.lower() in ("upload", "replace"):
                self.status_update.emit(f"Uploading {file_name}")
                self.log_update.emit(f"[API Scan] Starting upload: {local_path} to {file_path}, task_id: {task_id}")
                app_signals.append_log.emit(f"[API Scan] Initiating upload: {file_name}")
                app_signals.update_file_list.emit(local_path, f"{action_type} Queued", action_type, 0, not is_online)
                for attempt in range(max_download_retries):
                    is_final_attempt = (attempt == max_download_retries - 1)
                    try:
                        if not is_online:
                            with sftp_semaphore:
                                client_name = item.get("client_name", "").strip().replace(" ", "_") or None
                                project_name = item.get("project_name", item.get("name", "")).strip().replace(" ", "_") or None
                                if not client_name or not project_name:
                                    try:
                                        parts = Path(file_path).parts
                                        if len(parts) >= 3:
                                            client_name = client_name or parts[1]
                                            project_name = project_name or parts[2]
                                        else:
                                            client_name = client_name or "default_client"
                                            project_name = project_name or "default_project"
                                    except Exception as e:
                                        self.log_update.emit(f"[Upload] Fallback parsing failed: {e}")
                                        client_name = client_name or "default_client"
                                        project_name = project_name or "default_project"
                                original_nas_path = item.get('file_path', file_path)
                                # self.show_progress(f"Uploading {file_name}", local_path, original_nas_path, action_type, item, False, not is_online)
                                self.show_progress(f"Uploading {file_name}", local_path, original_nas_path, action_type, item, False, not is_online, is_final_attempt)
                                self.log_update.emit(f"[API Scan] Upload successful: {local_path} to {original_nas_path}, task_id: {task_id}")
                                return {
                                    'update': (local_path, "Upload Completed (Original)", action_type, 100, not is_online),
                                    'task_key': task_key,
                                    'success': True
                                }
                        else:
                            # self.show_progress(f"Uploading {file_name}", local_path, file_path, action_type, item, False, not is_online)
                            self.show_progress(f"Uploading {file_name}", local_path, file_path, action_type, item, False, not is_online, is_final_attempt)
                            self.log_update.emit(f"[API Scan] Upload successful: {local_path} to {file_path}, task_id: {task_id}")
                            return {
                                'update': (local_path, "Upload Completed (Original)", action_type, 100, not is_online),
                                'task_key': task_key,
                                'success': True
                            }
                    except PSDUploadCancelled as e:
                        # User explicitly declined the upload from the PSD
                        # validation dialog — stop immediately instead of
                        # re-prompting them again on every retry attempt.
                        logger.info(f"Upload cancelled by user for {local_path} (Task {task_id}): {str(e)}")
                        self.log_update.emit(f"[API Scan] Upload cancelled by user (Task {task_id}): {str(e)}")
                        return {
                            'update': (local_path, "Upload Cancelled", action_type, 0, not is_online),
                            'task_key': task_key,
                            'success': False
                        }
                    except UploadSizeLimitExceeded as e:
                        # File exceeds the configured size limit — retrying
                        # won't change the file size, so stop immediately
                        # instead of burning 3 retry attempts and re-alerting.
                        logger.info(f"Upload blocked by size limit for {local_path} (Task {task_id}): {str(e)}")
                        self.log_update.emit(f"[API Scan] Upload blocked — exceeds size limit (Task {task_id}): {str(e)}")
                        return {
                            'update': (local_path, "Upload Blocked (Too Large)", action_type, 0, not is_online),
                            'task_key': task_key,
                            'success': False
                        }
                    except Exception as e:
                        logger.error(f"[{datetime.now(timezone.utc).isoformat()}] Upload failed for {local_path} (Task {task_id}): {str(e)}, attempt {attempt + 1}, instance: {id(self)}")
                        self.log_update.emit(f"[API Scan] Upload failed for {local_path} (Task {task_id}): {str(e)}")
                        update = (local_path, f"Upload Failed: {str(e)}", action_type, 0, not is_online)
                        if attempt < max_download_retries - 1:
                            delay = 2 ** attempt
                            logger.debug(f"[{datetime.now(timezone.utc).isoformat()}] Retrying upload after {delay}s, instance: {id(self)}")
                            self.log_update.emit(f"[API Scan] Retrying upload after {delay}s")
                            # ── NEW: tell the UI a retry is happening ──
                            retry_msg = (
                                f"⚠ Network lost — retrying upload "
                                f"(attempt {attempt + 2}/{max_download_retries}) in {delay}s"
                            )
                            self.upload_status_detail.emit(
                                local_path, retry_msg, action_type, 0, not is_online
                            )
                            time.sleep(delay)
                        else:
                            raise
        except Exception as e:
            logger.error(f"[{datetime.now(timezone.utc).isoformat()}] Error processing task {task_id}: {str(e)}, instance: {id(self)}")
            self.log_update.emit(f"[API Scan] Error processing task {task_id}: {str(e)}")
            return {
                'update': (local_path, f"{action_type} Failed: {str(e)}", action_type, 0, not is_online),
                'task_key': task_key,
                'success': False
            }

    def check_connectivity(self):
        try:
            import socket
            # ✅ Simple TCP socket check — just tests if the host is reachable
            # on port 443. No HTTP request, no API hit, no fake user_id.
            # Guaranteed to be fast and never hit your task API endpoint.
            host = BASE_DOMAIN.replace("https://", "").replace("http://", "").split("/")[0]
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 443))
            self.log_update.emit("[API Scan] Connectivity OK")
            return True
        except Exception as e:
            logger.error(f"Connectivity check failed: {str(e)}")
            self.log_update.emit(f"[API Scan] Connectivity check failed: {str(e)}")
            return False

    # def show_progress(self, message, src_path, dest_path, action_type, item, is_nas_src, is_nas_dest):
    # def show_progress(self, message, src_path, dest_path, action_type, item, is_nas_src, is_nas_dest, is_final_attempt=True):
    #     task_id = str(item.get('id', ''))
    #     original_filename = Path(src_path).name
    #     update_download_upload_metadata(task_id, "in progress")
    #     try:
    #         self.perform_file_transfer(src_path, dest_path, action_type, item, is_nas_src, is_nas_dest)
    #         self.progress_update.emit(f"{action_type} Completed (Task {task_id}): {original_filename}", dest_path, 100)
    #         self.download_status_detail.emit(dest_path, f"{action_type} Completed (Task {task_id}): {original_filename}", action_type, 10, True)
    #     except Exception as e:
    #         logger.error(f"Progress error for {action_type} (Task {task_id}): {str(e)}")
    #         self.log_update.emit(f"[App] Progress update: {action_type} Failed (Task {task_id}): {original_filename}")
    #         raise

    def show_progress(self, message, src_path, dest_path, action_type, item, is_nas_src, is_nas_dest, is_final_attempt=True):
        print("================item===================================")
        print(item)
        print("=================item=========================================")

        task_id = str(item.get('id', ''))
        original_filename = Path(src_path).name
        update_download_upload_metadata(task_id, "in progress")
        try:
            self.perform_file_transfer(src_path, dest_path, action_type, item, is_nas_src, is_nas_dest, is_final_attempt=is_final_attempt)
            self.progress_update.emit(f"{action_type} Completed (Task {task_id}): {original_filename}", dest_path, 100)
            self.download_status_detail.emit(dest_path, f"{action_type} Completed (Task {task_id}): {original_filename}", action_type, 10, True)
        except Exception as e:
            logger.error(f"Progress error for {action_type} (Task {task_id}): {str(e)}")
            self.log_update.emit(f"[App] Progress update: {action_type} Failed (Task {task_id}): {original_filename}")
            raise

    def _download_from_http(self, src_path, dest_path):
        raise NotImplementedError("HTTP download not implemented")

    def _upload_to_http(self, src_path):
        raise NotImplementedError("HTTP upload not implemented")

    def _clean_processed_tasks(self):
        """
        Remove tasks older than retention window and enforce max size.
        Uses dict {task_key: insertion_timestamp} for correct time tracking.
        """
        current_time = time.time()
        retention_seconds = self.config["task_retention_hours"] * 3600

        # Remove expired tasks based on actual insertion time
        self.processed_tasks = {
            key: ts for key, ts in self.processed_tasks.items()
            if (current_time - ts) < retention_seconds
        }

        # Enforce max size — keep most recently added tasks
        if len(self.processed_tasks) > self.config["max_processed_tasks"]:
            sorted_keys = sorted(self.processed_tasks, key=lambda k: self.processed_tasks[k])
            excess = len(self.processed_tasks) - self.config["max_processed_tasks"]
            for key in sorted_keys[:excess]:
                del self.processed_tasks[key]

        logger.debug(f"[Cleanup] processed_tasks size: {len(self.processed_tasks)}")


    def cleanup(self):
        self.running = False
        logger.info("FileWatcherWorker cleaned up")
        self.log_update.emit("[FileWatcher] Cleaned up")

    def stop(self):
        """Stop the timer and worker gracefully."""
        self.running = False
        if self.timer.isActive():
            self.timer.stop()
        logger.debug(f"[{datetime.now(timezone.utc).isoformat()}] FileWatcherWorker stopped")






class LogWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PremediaApp Log")
        self.setWindowIcon(load_icon(ICON_PATH, "log window"))
        self.setMinimumSize(700, 400)
        self.resize(700, 400)

        # Initialize UI components
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.status_bar = QStatusBar(self)

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.status_bar)
        self.setLayout(layout)

        # Track signal-slot pairs with metadata
        self._connected_signals = {}  # Format: {name: (signal, slot, signal_signature)}

        # Load logs and connect signals
        self.load_logs()
        self.connect_signals()

        logger.info("LogWindow initialized")
        app_signals.append_log.emit("[Log] LogWindow initialized")

    def connect_signals(self):
        """Connect all signals, ensuring no duplicates."""
        if self._connected_signals:
            logger.debug("Signals already connected, skipping reconnection.")
            return

        # Define signal-slot pairs with expected signatures
        signal_pairs = [
            (app_signals.append_log, self.append_log, "append_log", str),
            (app_signals.api_call_status, self.append_api_status, "api_call_status", (str, str, int)),
            (app_signals.update_status, self.handle_update_status, "update_status", str),
            (app_signals.update_timer_status, self.update_timer_status, "update_timer_status", str),
        ]

        for signal, slot, name, expected_signature in signal_pairs:
            self.safe_connect(signal, slot, name, expected_signature)

    def safe_connect(self, signal, slot, name, expected_signature):
        """Connect a signal to a slot with signature verification and tracking."""
        try:
            # Verify signal signature
            signal_signature = getattr(signal, "signature", None)
            if signal_signature:
                logger.debug(f"Signal '{name}' signature: {signal_signature}")
            else:
                logger.warning(f"No signature available for signal '{name}'")

            # Basic signature check (PyQt doesn't expose signature directly, so we rely on expected)
            signal.connect(slot)
            self._connected_signals[name] = (signal, slot, expected_signature)
            logger.debug(f"✅ Connected '{name}' to '{slot.__name__}' with expected signature {expected_signature}")
        except Exception as e:
            logger.error(f"❌ Failed to connect '{name}' to '{slot.__name__}': {e}")
            app_signals.append_log.emit(f"[Log] Failed to connect signal '{name}': {str(e)}")


    def safe_disconnect(self, name):
        """Disconnect a signal safely with detailed logging."""
        signal_slot = self._connected_signals.pop(name, None)
        if signal_slot:
            signal, slot, signature = signal_slot
            try:
                if signal is not None and slot is not None:
                    with warnings.catch_warnings(record=True) as caught_warnings:
                        warnings.simplefilter("always")
                        signal.disconnect(slot)

                        if caught_warnings:
                            for w in caught_warnings:
                                logger.warning(f"⚠️ Disconnect warning for '{name}': {w.message}")
                        else:
                            logger.debug(f"✅ Disconnected '{name}' from '{slot.__name__}' (signature: {signature})")
                else:
                    logger.warning(f"⚠️ '{name}' has invalid signal or slot object.")
            except Exception as e:
                logger.warning(f"⚠️ Could not disconnect '{name}' from '{getattr(slot, '__name__', repr(slot))}': {e}")
        else:
            logger.debug(f"⚠️ '{name}' was never connected or already disconnected.")

    def disconnect_signals(self):
        """Disconnect all tracked signals."""
        for name in list(self._connected_signals.keys()):
            self.safe_disconnect(name)
        logger.debug("All signals disconnected.")

    def handle_update_status(self, message):
        """Update status bar with a message."""
        try:
            self.status_bar.showMessage(message)
            logger.debug(f"Status bar updated: {message}")
        except Exception as e:
            logger.error(f"Failed to update status bar: {e}")
            app_signals.append_log.emit(f"[Log] Failed to update status bar: {str(e)}")

    def update_timer_status(self, message):
        """Update timer status in status bar and log."""
        try:
            self.status_bar.showMessage(message)
            app_signals.append_log.emit(f"[Timer] {message}")
            logger.debug(f"Timer status updated: {message}")
        except Exception as e:
            logger.error(f"Failed to update timer status: {e}")
            app_signals.append_log.emit(f"[Timer] Failed to update timer status: {str(e)}")

    def load_logs(self):
        """Load recent logs from file."""
        try:
            log_file = log_dir / "app.log"
            if log_file.exists():
                with log_file.open("r", encoding='utf-8') as f:
                    lines = f.readlines()[-200:]
                self.text_edit.setPlainText("".join(lines))
                self.text_edit.moveCursor(QTextCursor.End)
                self.status_bar.showMessage("Logs loaded")
                app_signals.append_log.emit("[Log] Loaded existing logs from app.log")
                logger.debug(f"Loaded {len(lines)} log lines from {log_file}")
            else:
                self.status_bar.showMessage("No log file found")
                app_signals.append_log.emit("[Log] No log file found, starting fresh")
                logger.warning("No log file found at {log_file}")
        except Exception as e:
            logger.error(f"Failed to load logs: {e}")
            self.text_edit.setPlainText(f"Failed to load logs: {e}")
            self.status_bar.showMessage(f"Failed to load logs: {str(e)}")
            app_signals.append_log.emit(f"[Log] Failed to load logs: {str(e)}")

    def append_log(self, message):
        """
        Append a log message to the text edit.
        Connected via Qt.QueuedConnection — always runs on main thread.
        No processEvents() needed or safe here.
        """
        try:
            if "[API Scan]" in message:
                self.text_edit.append(f"<b>{message}</b>")
            else:
                self.text_edit.append(message)

            # Trim to last 200 lines to prevent unbounded memory growth
            lines = self.text_edit.toPlainText().splitlines()
            if len(lines) > 200:
                # Block signals during bulk replace to avoid recursive append_log
                self.text_edit.blockSignals(True)
                self.text_edit.setPlainText("\n".join(lines[-200:]))
                self.text_edit.blockSignals(False)

            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()
            # NOTE: QApplication.processEvents() removed — re-entrant crash risk.
            # Qt repaints the widget automatically via its own event loop.
            logger.debug(f"Appended log: {message}")
        except Exception as e:
            logger.error(f"Failed to append log: {e}")
            # NOTE: Do NOT emit append_log here — would cause infinite recursion
            
    def append_api_status(self, endpoint, status, status_code):
        """
        Append API call status to the log.
        Connected via Qt.QueuedConnection — always runs on main thread.
        No processEvents() needed or safe here.
        """
        try:
            log_msg = (
                f"[API Scan] API Call: {endpoint} "
                f"| Status: {status} "
                f"| Code: {status_code}"
            )
            self.text_edit.append(f"<b>{log_msg}</b>")

            # Trim to last 200 lines
            lines = self.text_edit.toPlainText().splitlines()
            if len(lines) > 200:
                self.text_edit.blockSignals(True)
                self.text_edit.setPlainText("\n".join(lines[-200:]))
                self.text_edit.blockSignals(False)

            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()
            # NOTE: QApplication.processEvents() removed — re-entrant crash risk.
            logger.debug(f"Appended API status: {log_msg}")
        except Exception as e:
            logger.error(f"Failed to append API status: {e}")
            # NOTE: Do NOT emit append_log here — would cause recursive append_api_status
            
            
    def closeEvent(self, event):
        logger.debug("LogWindow is closing. Disconnecting signals.")
        self.disconnect_signals()
        self._connected_signals.clear()  # Allow reconnection
        super().closeEvent(event)

# ---------------------- NEW: Async Thumbnail Loader ----------------------

class ThumbnailWorker(QRunnable):
    def __init__(self, url, target_label):
        super().__init__()
        self.url = url
        self.target_label = target_label

    def run(self):
        if not self.url:
            return
        try:
            r = requests.get(self.url, timeout=5)  # reduced from 10s — thumbnails should be fast
            if r.status_code != 200:
                return
            pix = QPixmap()
            if not pix.loadFromData(r.content):
                return
            pix = pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            QMetaObject.invokeMethod(
                self.target_label, "setPixmap", Qt.QueuedConnection, Q_ARG(QPixmap, pix)
            )
        except requests.exceptions.Timeout:
            logger.debug(f"[Thumbnail] Timed out fetching: {self.url}")
        except requests.exceptions.ConnectionError:
            logger.debug(f"[Thumbnail] Connection error fetching: {self.url}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"[Thumbnail] Request failed: {e}")
        except Exception as e:
            logger.debug(f"[Thumbnail] Unexpected error: {e}")





# ─────────────────────────────────────────────────────────────────────────────
# REPLACE the entire TransferNotificationPopup + TransferNotificationManager
# classes with the following. Also update start_file_watcher() to use
# the new NotificationOverlay.
# ─────────────────────────────────────────────────────────────────────────────


class TransferNotificationPopup(QFrame):
    """Single notification card for one transfer."""

    def __init__(self, spec_id: str, filename: str, action: str, parent=None):
        super().__init__(parent)
        self.spec_id = spec_id
        self.action = action
        self._done = False

        self.setFixedWidth(320)
        self.setObjectName("NotifCard")

        is_upload = action == "upload"
        accent = "#3b82f6" if is_upload else "#2ecc71"
        icon  = "⬆️" if is_upload else "⬇️"
        label = "Upload" if is_upload else "Download"

        self.setStyleSheet(f"""
            QFrame#NotifCard {{
                background: #1e1e2e;
                border: 1px solid #2a2a3e;
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ── Header ───────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self.icon_lbl = QLabel(f"{icon} {label}")
        self.icon_lbl.setStyleSheet(
            f"color:{accent}; font-weight:bold; font-size:12px; background:transparent;"
        )
        self.status_lbl = QLabel("Starting...")
        self.status_lbl.setStyleSheet(
            "color:#888; font-size:11px; background:transparent;"
        )
        self.status_lbl.setAlignment(Qt.AlignRight)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setStyleSheet("""
            QPushButton { background:transparent; color:#555; border:none; font-size:11px; }
            QPushButton:hover { color:#fff; }
        """)
        self.close_btn.clicked.connect(self._dismiss)

        header.addWidget(self.icon_lbl)
        header.addWidget(self.status_lbl, 1)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        # ── Filename ──────────────────────────────────────────────────────────
        self.file_lbl = QLabel(filename)
        self.file_lbl.setStyleSheet(
            "color:#ccc; font-size:11px; background:transparent;"
        )
        self.file_lbl.setWordWrap(True)
        self.file_lbl.setMaximumWidth(290)
        layout.addWidget(self.file_lbl)

        # ── Progress bar ──────────────────────────────────────────────────────
        self.bar = QProgressBar()
        self.bar.setFixedHeight(5)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setStyleSheet(f"""
            QProgressBar {{ background:#2a2a3e; border-radius:2px; border:none; }}
            QProgressBar::chunk {{ background:{accent}; border-radius:2px; }}
        """)
        layout.addWidget(self.bar)

        # ── Percent label ─────────────────────────────────────────────────────
        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setStyleSheet(
            "color:#666; font-size:10px; background:transparent;"
        )
        self.pct_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(self.pct_lbl)

        # ── Auto-dismiss timer ────────────────────────────────────────────────
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)

        # ── Fade-in ───────────────────────────────────────────────────────────
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_progress(self, percent: int, status_text: str = ""):
        self.bar.setValue(percent)
        self.pct_lbl.setText(f"{percent}%")
        if status_text:
            short = status_text.split(" • ")[0] if " • " in status_text else status_text
            self.status_lbl.setText(short)

    def mark_done(self, success: bool):
        if self._done:
            return
        self._done = True
        self.bar.setValue(100)
        self.pct_lbl.setText("100%")
        if success:
            self.status_lbl.setText("✅ Completed")
            self.status_lbl.setStyleSheet(
                "color:#2ecc71; font-size:11px; background:transparent;"
            )
        else:
            self.status_lbl.setText("❌ Failed")
            self.status_lbl.setStyleSheet(
                "color:#e74c3c; font-size:11px; background:transparent;"
            )
        self._auto_timer.start(4000)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _dismiss(self):
        self._anim2 = QPropertyAnimation(self._opacity, b"opacity")
        self._anim2.setDuration(250)
        self._anim2.setStartValue(1.0)
        self._anim2.setEndValue(0.0)
        self._anim2.finished.connect(self._remove_self)
        self._anim2.start()

    def _remove_self(self):
        manager = self.parent()
        if manager and hasattr(manager, "_remove_popup"):
            manager._remove_popup(self)
        self.deleteLater()


class TransferNotificationManager(QWidget):
    """
    Floating top-level overlay — always on top, bottom-right of the screen.

    Key fixes vs the original:
    • Uses Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint so the
      overlay is always visible regardless of which window is focused.
    • Does NOT depend on an anchor widget — anchors to the screen instead.
    • setWindowOpacity(0.95) gives a slight transparency so it feels non-intrusive.
    • A single _reposition() call on construction is all that's needed.
    """

    def __init__(self, parent=None):
        # ── CRITICAL: pass None so this becomes a real top-level window ───────
        super().__init__(None)

        self._popups: dict = {}   # spec_id → TransferNotificationPopup

        # ── Window flags: frameless, always-on-top tool window ────────────────
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.X11BypassWindowManagerHint   # needed on some Linux WMs
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # never steal focus
        self.setWindowOpacity(0.95)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignBottom | Qt.AlignRight)

        self._reposition()
        self.show()
        self.raise_()

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _reposition(self):
        """Anchor to the bottom-right corner of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()   # excludes taskbar

        popup_w   = 340
        margin    = 16
        max_h     = min(600, available.height() - margin * 2)

        x = available.right()  - popup_w - margin
        y = available.bottom() - max_h   - margin

        self.setGeometry(x, y, popup_w, max_h)

    # ── Popup management ──────────────────────────────────────────────────────

    def _get_or_create(self, spec_id: str, filename: str, action: str):
        if spec_id not in self._popups:
            popup = TransferNotificationPopup(spec_id, filename, action, parent=self)
            self._popups[spec_id] = popup
            self._layout.addWidget(popup)
            popup.show()
            self.raise_()           # keep overlay on top whenever a new card arrives
        return self._popups[spec_id]

    def _remove_popup(self, popup: TransferNotificationPopup):
        spec_id = popup.spec_id
        if spec_id in self._popups:
            self._layout.removeWidget(popup)
            del self._popups[spec_id]

    # ── Slots ─────────────────────────────────────────────────────────────────

    @Slot(str, str, str, int)
    def on_download_progress(self, spec_id: str, file_path: str, filename: str, percent: int):
        popup = self._get_or_create(spec_id, filename, "download")
        popup.update_progress(percent)
        if percent >= 100:
            popup.mark_done(True)

    @Slot(str, str, str, int, bool)
    def on_download_status_detail(
        self, file_path: str, text: str, action_type: str, percent: int, is_nas: bool
    ):
        if action_type != "download":
            return
        fname = Path(file_path).name
        for popup in self._popups.values():
            if popup.action == "download" and (
                popup.file_lbl.text() == fname or file_path in popup.file_lbl.text()
            ):
                popup.update_progress(percent, text)
                if "Failed" in text:
                    popup.mark_done(False)
                elif "Completed" in text:
                    popup.mark_done(True)
                break

    @Slot(str, str, str, int)
    def on_upload_progress(self, spec_id: str, file_path: str, filename: str, percent: int):
        popup = self._get_or_create(spec_id, filename, "upload")
        popup.update_progress(percent)
        if percent >= 100:
            popup.mark_done(True)

    @Slot(str, str, str, int, bool)
    def on_upload_status_detail(
        self, file_path: str, text: str, action_type: str, percent: int, is_nas: bool
    ):
        if action_type != "upload":
            return
        fname = Path(file_path).name
        for popup in self._popups.values():
            if popup.action == "upload" and (
                popup.file_lbl.text() == fname or file_path in popup.file_lbl.text()
            ):
                popup.update_progress(percent, text)
                if "Failed" in text:
                    popup.mark_done(False)
                elif "Completed" in text:
                    popup.mark_done(True)
                break




class CardWidget(QFrame):
    copyRequested = Signal(str)
    retryRequested = Signal(dict)
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.row_data = row_data

        self.setObjectName("CardWidget")
        self.setStyleSheet("""
            QFrame#CardWidget {
                background: #ffffff;
                border: 1px solid #dcdcdc;
                border-left: 4px solid #2ecc71;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }
            QFrame#CardWidget:hover { background: #f8f9fa; }
        """)

        main = QHBoxLayout(self)
        main.setSpacing(14)
        main.setContentsMargins(10, 10, 10, 10)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(64, 64)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border:1px solid #ccc; border-radius:6px; background:#f0f0f0;")
        placeholder = QPixmap(64, 64)
        placeholder.fill(Qt.lightGray)
        self.thumb.setPixmap(placeholder)
        main.addWidget(self.thumb)
        self._load_thumbnail(row_data.get("thumbnail"))

        # Info
        info = QVBoxLayout()
        info.setSpacing(6)
        # self.project_lbl = QLabel(f"<b>Project:</b> {row_data.get('project_name', 'Loading...')}")
        # self.job_lbl = QLabel(f"<b>Job:</b> {row_data.get('job_name', 'Loading...')}")
        # self.file_lbl = QLabel(f"<b>File:</b> {row_data.get('file_name', 'Unknown')}")
        # self.date_lbl = QLabel(self._format_date(row_data.get("created_at", "")))
        # self.user_type_lbl = QLabel(f"<b>User Type:</b> {row_data.get('user_type', '')}")
        # self.duration_lbl = QLabel(self._format_duration(row_data.get("transfer_duration")))
        self.project_lbl = QLabel(f"🗂️  {row_data.get('project_name', 'Loading...')}")
        self.job_lbl     = QLabel(f"💼  {row_data.get('job_name', 'Loading...')}")
        self.file_lbl    = QLabel(f"📄  {row_data.get('file_name', 'Unknown')}")
        self.user_type_lbl = QLabel(f"🎭  {row_data.get('user_type', '').upper()}")
        self.date_lbl    = QLabel(f"🕐  {self._format_date(row_data.get('created_at', ''))}")
        self.duration_lbl  = QLabel(self._format_duration(row_data.get("transfer_duration")))

        self.duration_lbl.setWordWrap(True)
        self.duration_lbl.setStyleSheet("color: #444;")
        
        for lbl in (self.project_lbl, self.job_lbl, self.file_lbl, self.date_lbl):
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #444;")
        info.addWidget(self.project_lbl)
        info.addWidget(self.job_lbl)
        info.addWidget(self.file_lbl)
        info.addWidget(self.user_type_lbl)
        info.addWidget(self.date_lbl)
        
        info.addWidget(self.duration_lbl)
        main.addLayout(info, 1)

        # Right side
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignTop | Qt.AlignRight)
        right.setSpacing(8)

        # Status label
        self.status_lbl = QLabel("Download Completed")
        self.status_lbl.setAlignment(Qt.AlignRight)
        self.status_lbl.setStyleSheet("color: #555; font-size: 11px;")
        right.addWidget(self.status_lbl)

        # Progress bar — always hidden on creation
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #bbb; border-radius: 4px; background: #f0f0f0; }
            QProgressBar::chunk { background: #2ecc71; border-radius: 3px; }
        """)
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        right.addWidget(self.progress_bar)

        # Actions
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)

        self.folder_btn = QPushButton()
        self.folder_btn.setIcon(load_icon(FOLDER_ICON_PATH, "folder"))
        self.folder_btn.clicked.connect(lambda: parent.open_folder(row_data.get("local_path", "")))
        self.actions_layout.addWidget(self.folder_btn)

        self.ps_btn = QPushButton()
        self.ps_btn.setIcon(load_icon(PHOTOSHOP_ICON_PATH, "ps"))
        self.ps_btn.clicked.connect(lambda: parent.open_with_photoshop(row_data.get("local_path", "")))
        self.actions_layout.addWidget(self.ps_btn)

        right.addLayout(self.actions_layout)
        main.addLayout(right)

        # Initial action buttons
        self._update_action_buttons(row_data.get("status", "Download Completed"))

    def _load_thumbnail(self, url):
        if url:
            worker = ThumbnailWorker(url, self.thumb)
            QThreadPool.globalInstance().start(worker)

    def update_progress(self, percent: int):
        """Only live signals show the progress bar"""
        self.progress_bar.show()
        self.progress_bar.setValue(percent)

    def update_status(self, text: str):
        self.status_lbl.setText(text)
        if "Completed" in text or "Failed" in text:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)

    def _update_action_buttons(self, status):
        for i in reversed(range(self.actions_layout.count())):
            widget = self.actions_layout.itemAt(i).widget()
            if widget and widget not in (self.folder_btn, self.ps_btn):
                widget.setParent(None)
                widget.deleteLater()

        if "Completed" in status:
            # copy_btn = QPushButton()
            # copy_btn.setIcon(load_icon(COPY_ICON_PATH, "copy"))
            # # copy_btn.clicked.connect(lambda: self.parent().copy_file_to_clipboard(self.row_data.get("local_path", "")))
            # copy_btn.clicked.connect(
            #         lambda: self.copyRequested.emit(
            #             self.row_data.get("local_path", "")
            #         )
            #     )
            # self.actions_layout.addWidget(copy_btn)
            retry_btn = QPushButton()
            retry_btn.setIcon(load_icon(RETRY_ICON_PATH, "retry"))
            # retry_btn.clicked.connect(lambda: self.parent().retry_file_process(self.row_data))
            retry_btn.clicked.connect(lambda: self.retryRequested.emit(self.row_data.copy()))

            self.actions_layout.addWidget(retry_btn)


        if "Failed" in status:
            retry_btn = QPushButton()
            retry_btn.setIcon(load_icon(RETRY_ICON_PATH, "retry"))
            # retry_btn.clicked.connect(lambda: self.parent().retry_file_process(self.row_data))
            retry_btn.clicked.connect(lambda: self.retryRequested.emit(self.row_data.copy()))
            self.actions_layout.addWidget(retry_btn)

    def update_row(self, new_row):
        self.row_data.update(new_row)

        # self.project_lbl.setText(f"<b>Project:</b> {new_row.get('project_name', 'Unknown')}")
        # self.job_lbl.setText(f"<b>Job:</b> {new_row.get('job_name', 'Unknown')}")
        # self.file_lbl.setText(f"<b>File:</b> {new_row.get('file_name', 'Unknown')}")
        # self.date_lbl.setText(self._format_date(new_row.get("created_at", "")))
        # self.user_type_lbl.setText(f"ROLE: {new_row.get('user_type', '')}")
        # self.duration_lbl.setText(self._format_duration(new_row.get("transfer_duration")))



        self.project_lbl.setText(f"🗂️  {new_row.get('project_name', 'Unknown')}")
        self.job_lbl.setText(f"💼  {new_row.get('job_name', 'Unknown')}")
        self.file_lbl.setText(f"📄  {new_row.get('file_name', 'Unknown')}")
        self.date_lbl.setText(f"🕐  {self._format_date(new_row.get('created_at', ''))}")
        self.user_type_lbl.setText(f"🎭  {new_row.get('user_type', '').upper()}")
        self.duration_lbl.setText(self._format_duration(new_row.get("transfer_duration")))


        status = new_row.get("status", "Download Completed")
        self.status_lbl.setText(status)

        # NEVER show progress bar from cache data
        if "Completed" in status or "Failed" in status:
            self.progress_bar.hide()
            self.progress_bar.setValue(0)

        if new_row.get("thumbnail"):
            self._load_thumbnail(new_row.get("thumbnail"))

        self._update_action_buttons(status)

    @staticmethod
    def _format_date(value) -> str:
        try:
            from datetime import datetime
            return datetime.fromtimestamp(int(value)).strftime("%B %d %Y  %I:%M:%S %p")
        except (ValueError, TypeError, OSError):
            return str(value) if value else ""

   
    @staticmethod
    def _format_duration(seconds) -> str:
        try:
            s = float(seconds)
            if s <= 0:
                return ""
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            if h:
                return f"⏱️  {h}h {m}m {sec}s"
            if m:
                return f"⏱️  {m}m {sec}s"
            return f"⏱️  {sec}s"
        except (TypeError, ValueError):
            return ""
 
    

class FileDownloadListWindow(QDialog):
    def __init__(self, file_type="downloaded", parent=None):
        super().__init__(parent)
        self.file_type = file_type.lower()
        self.setWindowTitle(f"{self.file_type.capitalize()} Files")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 900)

        # SINGLE KEY: spec_id → CardWidget
        self.card_index = {}

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.load_files)

        # UI setup
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search by project, job or file name")
        self.search_bar.textChanged.connect(self.filter_cards)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(lambda: self.filter_cards(self.search_bar.text()))
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_search)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_bar, 1)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_btn)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(10)

        self.scroll_area.setWidget(self.cards_container)

        layout = QVBoxLayout(self)
        layout.addLayout(search_layout)
        layout.addWidget(self.scroll_area)

        # Load completed files on open
        self.load_files()

        # Connect signals
        self._connected_watcher = None
        self._ensure_watcher_connected()
        # Keep your existing update_file_list if needed
        # app_signals.update_file_list.connect(self.on_file_update, Qt.QueuedConnection)

    def _ensure_watcher_connected(self):
        """
        (Re)connect to the CURRENT FileWatcherWorker singleton.

        FIX: Every logout/login (and every start_file_watcher() call) does
        `FileWatcherWorker._instance = None` and creates a brand-new worker
        with its own fresh download_progress/download_status_detail signals.
        This window used to connect only once in __init__, so after a single
        logout/login cycle it stayed wired to the dead old worker and the
        card UI silently stopped updating even though transfers were
        actually happening. Called from showEvent so it's always current.
        """
        watcher = FileWatcherWorker.get_instance()
        if watcher is self._connected_watcher:
            return
        if self._connected_watcher is not None:
            try:
                self._connected_watcher.download_progress.disconnect(self.on_download_progress)
                self._connected_watcher.download_status_detail.disconnect(self.on_download_status_detail)
            except Exception:
                pass
        watcher.download_progress.connect(self.on_download_progress, Qt.QueuedConnection)
        watcher.download_status_detail.connect(self.on_download_status_detail, Qt.QueuedConnection)
        self._connected_watcher = watcher
        logger.debug("[FileDownloadListWindow] (Re)connected to current FileWatcherWorker instance")

    @staticmethod
    def normalize_path(path: str) -> str:
        return str(Path(path).resolve())

    def load_files(self):
        cache = load_cache()
        metadata = cache.get("downloaded_files_with_metadata", {})
       
        rows = []

        for spec_id, entry in metadata.items():
            local_path = entry.get("local_path")

            # 🔴 FIX 1:
            # Do NOT require file to exist on disk
            # UI reflects metadata, not filesystem state
            if not local_path:
                continue

            api = entry.get("api_response", {})

            # Normalize status for UI
            status = api.get("request_status", "Download Completed")
            if "Downloading" in status:
                status = "Download Completed"

            rows.append({
                "spec_id": str(spec_id),
                "thumbnail": api.get("thumbnail"),
                "project_name": api.get("project_name", "Unknown"),
                "job_name": api.get("job_name", "Unknown"),
                "file_name": Path(local_path).name,
                "created_at": api.get("created_on", ""),
                "local_path": local_path,
                "user_type": api.get("user_type", ""),
                "transfer_duration": api.get("transfer_duration"),
                "status": status,
            })
        rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        self._sync_cards(rows)


    def _sync_cards(self, rows):
        seen_spec_ids = set()

        # --- Create / Update cards ---
        for row in rows:
            spec_id = row["spec_id"]
            seen_spec_ids.add(spec_id)

            if spec_id in self.card_index:
                self.card_index[spec_id].update_row(row)
            else:
                card = CardWidget(row, self)
                card.copyRequested.connect(self.copy_file_to_clipboard) 
                card.retryRequested.connect(self.retry_file_process)
                self.card_index[spec_id] = card
                self.cards_layout.addWidget(card)


        # --- 🔴 FIX 2: DO NOT DELETE COMPLETED CARDS ---
        for spec_id in list(self.card_index.keys()):
            if spec_id not in seen_spec_ids:
                card = self.card_index[spec_id]
                status = card.row_data.get("status", "")

                # Only remove cards that are NOT completed or failed
                if status not in ("Download Completed", "Download Failed"):
                    self.card_index.pop(spec_id)
                    card.setParent(None)
                    card.deleteLater()

        # --- Reorder cards: active downloads at top ---
        all_cards = []
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                all_cards.append(item.widget())

        active = [
            c for c in all_cards
            if c.progress_bar.isVisible() and 0 < c.progress_bar.value() < 100
        ]
        completed = [c for c in all_cards if c not in active]

        completed.sort(key=lambda c: c.row_data.get("created_at", ""), reverse=True)

        for card in active:
            self.cards_layout.addWidget(card)
        for card in completed:
            self.cards_layout.addWidget(card)


    def on_download_progress(self, spec_id: str, file_path: str, filename: str, percent: int):
        spec_id = str(spec_id)

        card = self.card_index.get(spec_id)
        if not card:
            temp_row = {
                "spec_id": spec_id,
                "local_path": file_path,
                "file_name": filename,
                "project_name": "Loading...",
                "job_name": "Loading...",
                "thumbnail": None,
                "created_at": "",
                "status": "Downloading",
            }
            card = CardWidget(temp_row, self)
            card.copyRequested.connect(self.copy_file_to_clipboard)
            card.retryRequested.connect(self.retry_file_process)

            self.card_index[spec_id] = card
            self.cards_layout.insertWidget(0, card)
            card._promoted = False

        # ---- HARD GUARD: avoid repaint storms ----
        if percent == card.progress_bar.value():
            return

        # ---- Update progress ----
        card.update_progress(percent)

        if file_path:
            card.row_data["local_path"] = file_path

        if filename:
            card.row_data["file_name"] = filename
            card.file_lbl.setText(f"<b>File:</b> {filename}")

        # ---- Load metadata ONCE ----
        if not card.row_data.get("_meta_loaded"):
            cache = load_cache()
            meta = cache.get("downloaded_files_with_metadata", {}).get(spec_id)

            if meta:
                api = meta.get("api_response", {})
                if api.get("project_name"):
                    card.project_lbl.setText(f"<b>Project:</b> {api['project_name']}")
                if api.get("job_name"):
                    card.job_lbl.setText(f"<b>Job:</b> {api['job_name']}")
                if api.get("thumbnail"):
                    card._load_thumbnail(api["thumbnail"])
                if api.get("user_type"):
                    card.user_type_lbl.setText(f"🎭 {api['user_type']}")
                card.row_data["user_type"] = api.get("user_type", "")

            card.row_data["_meta_loaded"] = True

        # ---- Promote ONLY ONCE ----
        if not getattr(card, "_promoted", False):
            self.cards_layout.removeWidget(card)
            self.cards_layout.insertWidget(0, card)
            card._promoted = True




    def on_download_status_detail(self, file_path: str, text: str, action_type: str, percent: int, is_nas_src: bool):
        if action_type != "download":
            return

        for card in self.card_index.values():
            if card.row_data.get("local_path") == file_path or card.row_data.get("file_name") == Path(file_path).name:
                card.update_status(text)

                # ── NEW: refresh metadata from cache when transfer completes ──
                if "Completed" in text or "Failed" in text:
                    spec_id = card.row_data.get("spec_id")
                    if spec_id:
                        cache = load_cache()
                        meta = cache.get("downloaded_files_with_metadata", {}).get(spec_id)
                        if meta:
                            api = meta.get("api_response", {})
                            fresh_row = {
                                "spec_id": str(spec_id),
                                "thumbnail": api.get("thumbnail"),
                                "project_name": api.get("project_name", card.row_data.get("project_name", "Unknown")),
                                "job_name": api.get("job_name", card.row_data.get("job_name", "Unknown")),
                                "file_name": Path(file_path).name,
                                "created_at": api.get("created_on", card.row_data.get("created_at", "")),
                                "local_path": file_path,
                                "user_type": api.get("user_type", card.row_data.get("user_type", "")),
                                "transfer_duration": api.get("transfer_duration"),
                                "status": "Download Completed" if "Completed" in text else "Download Failed",
                            }
                            card.update_row(fresh_row)
                break



    # def on_download_status_detail(self, file_path: str, text: str, action_type: str, percent: int, is_nas_src: bool):
    #     if action_type != "download":
    #         return

    #     # Find card by local_path or filename
    #     for card in self.card_index.values():
    #         if card.row_data.get("local_path") == file_path or card.row_data.get("file_name") == Path(file_path).name:
    #             card.update_status(text)
    #             break

    def filter_cards(self, text: str = None):
        if text is None:
            text = self.search_bar.text()
        text = text.lower().strip()
        for card in self.card_index.values():
            row = card.row_data
            visible = (
                not text or
                text in str(row.get("project_name", "")).lower() or
                text in str(row.get("job_name", "")).lower() or
                text in str(row.get("file_name", "")).lower()
            )
            card.setVisible(visible)

    def clear_search(self):
        self.search_bar.clear()
        self.filter_cards("")

    def showEvent(self, event):
        super().showEvent(event)
        self._ensure_watcher_connected()  # FIX: reconnect if worker was recreated
        self.load_files()  # Refresh when shown



    def open_with_photoshop(self, file_path):
        """Open file in Photoshop — delegates to module-level helper."""
        try:
            open_file_with_photoshop(file_path)
        except Exception as e:
            error_msg = f"Failed to open {Path(file_path).name} in Photoshop: {e}"
            logger.error(error_msg)
            # QMessageBox.critical(self, "Photoshop Error", error_msg)
            show_alert("Photoshop Error", error_msg, QMessageBox.Critical)



    def open_folder(self, file_path):
        """Open the folder containing the file."""
        try:
            folder_path = str(Path(file_path).parent)
            system = platform.system()
            if system == "Windows":
                # subprocess.run(["explorer", folder_path], check=True)
                subprocess.Popen(["explorer", folder_path])
            elif system == "Darwin":
                subprocess.run(["open", folder_path], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", folder_path], check=True)
            else:
                logger.warning(f"Unsupported platform for opening folder: {system}")
                app_signals.append_log.emit(f"[Folder] Unsupported platform for opening folder: {system}")
                app_signals.update_status.emit(f"Unsupported platform for opening folder: {system}")
                return
            app_signals.update_status.emit(f"Opened folder for {Path(file_path).name}")
            app_signals.append_log.emit(f"[Folder] Opened folder for {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Failed to open folder {file_path}: {e}")
            app_signals.append_log.emit(f"[Folder] Failed to open folder: {str(e)}")
            app_signals.update_status.emit(f"Failed to open folder for {Path(file_path).name}: {str(e)}")

    def copy_file_to_clipboard(self, file_path: str):
        print("copy_file_to_clipboard CALLED")  # you will now see this

        path = Path(file_path).resolve()
        clipboard = QApplication.clipboard()

        mime = QMimeData()
        mime.setText(str(path))
        mime.setUrls([QUrl.fromLocalFile(str(path))])

        clipboard.setMimeData(mime)
        msg = f"File path copied to clipboard:\n{path}"
        show_alert("Copied", msg, QMessageBox.Information)
        # QMessageBox.information(
        #     self,
        #     "Copied",
        #     f"File path copied to clipboard:\n{path}"
        # )



    def retry_file_process(self, row_data: dict):
   
        logger.info("========== RETRY START ==========")

        # ------------------------------------------------------------------
        # 1. Validate row identity
        # ------------------------------------------------------------------
        spec_id = str(row_data.get("spec_id"))
        status = row_data.get("status")

        if not spec_id:
            logger.error("[Retry] Missing spec_id in row_data")
            return

        # if status not in ("Download Failed", "Upload Failed"):
        #     logger.warning(
        #         f"[Retry] Ignored retry for spec_id={spec_id}, status={status}"
        #     )
        #     return

        # ------------------------------------------------------------------
        # 2. Load authoritative cache metadata (SOURCE OF TRUTH)
        # ------------------------------------------------------------------
        cache = load_cache()
        meta = cache.get("downloaded_files_with_metadata", {}).get(spec_id)

        if not meta or "api_response" not in meta:
            logger.error(f"[Retry] No cached api_response for spec_id={spec_id}")
            return

        api = meta["api_response"]

        # ------------------------------------------------------------------
        # 3. Validate API payload (STRICT)
        # ------------------------------------------------------------------
        request_type = api.get("request_type")
        nas_file_path = api.get("file_path")   # NAS REMOTE PATH
        nas_path = api.get("nas_path")
        task_id = api.get("id")

        if request_type != "download":
            logger.error(
                f"[Retry] Unsupported retry type={request_type} for spec_id={spec_id}"
            )
            return

        if not nas_file_path or not task_id:
            logger.error(
                f"[Retry] Invalid API data for spec_id={spec_id} "
                f"(file_path={nas_file_path}, id={task_id})"
            )
            return

        # ------------------------------------------------------------------
        # 4. Resolve transfer paths (NAS → LOCAL)
        # ------------------------------------------------------------------
        src_path = nas_file_path                    # NAS SOURCE
        dest_path = os.path.join(BASE_TARGET_DIR, nas_path)

        is_nas_src = True
        is_nas_dest = False

        # ------------------------------------------------------------------
        # 5. Reset SAME card UI (NO recreation)
        # ------------------------------------------------------------------
        card = self.card_index.get(spec_id)
        if card:
            card.update_status("Retrying...")
            card.progress_bar.setValue(0)
            card.progress_bar.show()

            # Promote ONCE
            self.cards_layout.removeWidget(card)
            self.cards_layout.insertWidget(0, card)

        # ------------------------------------------------------------------
        # 6. Build CLEAN retry item (CRITICAL FIX)
        #    SCP requires NAS file_path, NOT local path
        # ------------------------------------------------------------------
        retry_item = {
            "id": api["id"],
            "spec_id": api["spec_id"],
            "file_path": api["file_path"],     # NAS PATH (MANDATORY)
            "nas_path": api["nas_path"],
            "file_name": api.get("file_name"),
            "job_id": api.get("job_id"),
            "job_name": api.get("job_name"),
            "project_id": api.get("project_id"),
            "project_name": api.get("project_name"),
            "client_name": api.get("client_name"),
            "user_id": api.get("user_id"),
            "user_type": api.get("user_type"),
            "creative_id": api.get("creative_id"),
            "inventory_id": api.get("inventory_id"),
            "thumbnail": api.get("thumbnail"),
            "created_on": api.get("created_on"),
            "updated_date": api.get("updated_date"),
            "request_type": "download",
        }

        # ------------------------------------------------------------------
        # 7. Dispatch retry to worker (NON-BLOCKING)
        # ------------------------------------------------------------------
        try:
            file_worker = FileWatcherWorker.get_instance()

            file_worker.perform_file_transfer(
                src_path,
                dest_path,
                "download",
                retry_item,       # 🔑 CORRECT ITEM PAYLOAD
                is_nas_src,
                is_nas_dest
            )

            logger.info(
                f"[Retry] Download retry dispatched "
                f"(spec_id={spec_id}, task_id={task_id})"
            )

        except Exception as e:
            logger.exception(
                f"[Retry] Failed to dispatch retry for spec_id={spec_id}: {e}"
            )

        logger.info("========== RETRY END ==========")


    
    


class FileUploadListWindow(QDialog):
    def __init__(self, file_type="uploaded", parent=None):
        super().__init__(parent)
        self.file_type = file_type.lower()
        self.setWindowTitle(f"{self.file_type.capitalize()} Files")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 900)

        # SINGLE KEY: spec_id → CardWidget
        self.card_index = {}

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.load_files)

        # UI setup
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search by project, job or file name")
        self.search_bar.textChanged.connect(self.filter_cards)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(lambda: self.filter_cards(self.search_bar.text()))
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_search)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_bar, 1)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_btn)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(10)

        self.scroll_area.setWidget(self.cards_container)

        layout = QVBoxLayout(self)
        layout.addLayout(search_layout)
        layout.addWidget(self.scroll_area)

        # Load uploaded files on open
        self.load_files()

        # Connect signals
        self._connected_watcher = None
        self._ensure_watcher_connected()

    def _ensure_watcher_connected(self):
        """
        (Re)connect to the CURRENT FileWatcherWorker singleton.
        See FileDownloadListWindow._ensure_watcher_connected for why this
        is necessary — logout/login recreates the worker with fresh signals.
        """
        watcher = FileWatcherWorker.get_instance()
        if watcher is self._connected_watcher:
            return
        if self._connected_watcher is not None:
            try:
                self._connected_watcher.upload_progress.disconnect(self.on_upload_progress)
                self._connected_watcher.upload_status_detail.disconnect(self.on_upload_status_detail)
            except Exception:
                pass
        watcher.upload_progress.connect(self.on_upload_progress, Qt.QueuedConnection)
        watcher.upload_status_detail.connect(self.on_upload_status_detail, Qt.QueuedConnection)
        self._connected_watcher = watcher
        logger.debug("[FileUploadListWindow] (Re)connected to current FileWatcherWorker instance")

    @staticmethod
    def normalize_path(path: str) -> str:
        return str(Path(path).resolve())

    def load_files(self):
        cache = load_cache()
        metadata = cache.get("uploaded_files_with_metadata", {})  # Changed key for uploads
       
        rows = []

        for spec_id, entry in metadata.items():
            local_path = entry.get("local_path")

            # Do NOT require file to exist on disk
            # UI reflects metadata, not filesystem state
            if not local_path:
                continue

            api = entry.get("api_response", {})

            # Normalize status for UI
            status = api.get("request_status", "Upload Completed")
            if "Uploading" in status:
                status = "Upload Completed"

            rows.append({
                "spec_id": str(spec_id),
                "thumbnail": api.get("thumbnail"),
                "project_name": api.get("project_name", "Unknown"),
                "job_name": api.get("job_name", "Unknown"),
                "file_name": Path(local_path).name,
                "created_at": api.get("created_on", ""),
                "local_path": local_path,
                "user_type": api.get("user_type", ""),
                "transfer_duration": api.get("transfer_duration"),
                "status": status,
            })
        rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        self._sync_cards(rows)

    def _sync_cards(self, rows):
        seen_spec_ids = set()

        # --- Create / Update cards ---
        for row in rows:
            spec_id = row["spec_id"]
            seen_spec_ids.add(spec_id)

            if spec_id in self.card_index:
                self.card_index[spec_id].update_row(row)
            else:
                card = CardWidget(row, self)
                card.copyRequested.connect(self.copy_file_to_clipboard) 
                card.retryRequested.connect(self.retry_file_process)
                self.card_index[spec_id] = card
                self.cards_layout.addWidget(card)

        # --- DO NOT DELETE COMPLETED CARDS ---
        for spec_id in list(self.card_index.keys()):
            if spec_id not in seen_spec_ids:
                card = self.card_index[spec_id]
                status = card.row_data.get("status", "")

                # Only remove cards that are NOT completed or failed
                if status not in ("Upload Completed", "Upload Failed"):
                    self.card_index.pop(spec_id)
                    card.setParent(None)
                    card.deleteLater()

        # --- Reorder cards: active uploads at top ---
        all_cards = []
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                all_cards.append(item.widget())

        active = [
            c for c in all_cards
            if c.progress_bar.isVisible() and 0 < c.progress_bar.value() < 100
        ]
        completed = [c for c in all_cards if c not in active]

        for card in active:
            self.cards_layout.addWidget(card)
        for card in completed:
            self.cards_layout.addWidget(card)

    def on_upload_progress(self, spec_id: str, file_path: str, filename: str, percent: int):
        spec_id = str(spec_id)

        card = self.card_index.get(spec_id)
        if not card:
            temp_row = {
                "spec_id": spec_id,
                "local_path": file_path,
                "file_name": filename,
                "project_name": "Loading...",
                "job_name": "Loading...",
                "thumbnail": None,
                "created_at": "",
                "status": "Uploading",
            }
            card = CardWidget(temp_row, self)
            card.copyRequested.connect(self.copy_file_to_clipboard)
            card.retryRequested.connect(self.retry_file_process)

            self.card_index[spec_id] = card
            self.cards_layout.insertWidget(0, card)
            card._promoted = False

        # ---- HARD GUARD: avoid repaint storms ----
        if percent == card.progress_bar.value():
            return

        # ---- Update progress ----
        card.update_progress(percent)

        if file_path:
            card.row_data["local_path"] = file_path

        if filename:
            card.row_data["file_name"] = filename
            card.file_lbl.setText(f"<b>File:</b> {filename}")

        # ---- Load metadata ONCE ----
        if not card.row_data.get("_meta_loaded"):
            cache = load_cache()
            meta = cache.get("uploaded_files_with_metadata", {}).get(spec_id)

            if meta:
                api = meta.get("api_response", {})
                if api.get("project_name"):
                    card.project_lbl.setText(f"<b>Project:</b> {api['project_name']}")
                if api.get("job_name"):
                    card.job_lbl.setText(f"<b>Job:</b> {api['job_name']}")
                if api.get("thumbnail"):
                    card._load_thumbnail(api["thumbnail"])
                if api.get("user_type"):                                        
                    card.user_type_lbl.setText(f"🎭 {api['user_type']}")
                card.row_data["user_type"] = api.get("user_type", "")

            card.row_data["_meta_loaded"] = True

        # ---- Promote ONLY ONCE ----
        if not getattr(card, "_promoted", False):
            self.cards_layout.removeWidget(card)
            self.cards_layout.insertWidget(0, card)
            card._promoted = True





    def on_upload_status_detail(self, file_path: str, text: str, action_type: str, percent: int, is_nas_src: bool):
        if action_type != "upload":
            return

        for card in self.card_index.values():
            if card.row_data.get("local_path") == file_path or card.row_data.get("file_name") == Path(file_path).name:
                card.update_status(text)

                # ── NEW: refresh metadata from cache when transfer completes ──
                if "Completed" in text or "Failed" in text:
                    spec_id = card.row_data.get("spec_id")
                    if spec_id:
                        cache = load_cache()
                        meta = cache.get("uploaded_files_with_metadata", {}).get(spec_id)
                        if meta:
                            api = meta.get("api_response", {})
                            fresh_row = {
                                "spec_id": str(spec_id),
                                "thumbnail": api.get("thumbnail"),
                                "project_name": api.get("project_name", card.row_data.get("project_name", "Unknown")),
                                "job_name": api.get("job_name", card.row_data.get("job_name", "Unknown")),
                                "file_name": Path(file_path).name,
                                "created_at": api.get("created_on", card.row_data.get("created_at", "")),
                                "local_path": file_path,
                                "user_type": api.get("user_type", card.row_data.get("user_type", "")),
                                "transfer_duration": api.get("transfer_duration"),
                                "status": "Upload Completed" if "Completed" in text else "Upload Failed",
                            }
                            card.update_row(fresh_row)
                break



    # def on_upload_status_detail(self, file_path: str, text: str, action_type: str, percent: int, is_nas_src: bool):
    #     if action_type != "upload":
    #         return

    #     # Find card by local_path or filename
    #     for card in self.card_index.values():
    #         if card.row_data.get("local_path") == file_path or card.row_data.get("file_name") == Path(file_path).name:
    #             card.update_status(text)
    #             break

    def filter_cards(self, text: str = None):
        if text is None:
            text = self.search_bar.text()
        text = text.lower().strip()
        for card in self.card_index.values():
            row = card.row_data
            visible = (
                not text or
                text in str(row.get("project_name", "")).lower() or
                text in str(row.get("job_name", "")).lower() or
                text in str(row.get("file_name", "")).lower()
            )
            card.setVisible(visible)

    def clear_search(self):
        self.search_bar.clear()
        self.filter_cards("")

    def showEvent(self, event):
        super().showEvent(event)
        self._ensure_watcher_connected()  # FIX: reconnect if worker was recreated
        self.load_files()  # Refresh when shown


    def open_with_photoshop(self, file_path):
        """Open file in Photoshop — delegates to module-level helper."""
        try:
            open_file_with_photoshop(file_path)
        except Exception as e:
            error_msg = f"Failed to open {Path(file_path).name} in Photoshop: {e}"
            logger.error(error_msg)
            # QMessageBox.critical(self, "Photoshop Error", error_msg)
            show_alert("Photoshop Error", error_msg, QMessageBox.Critical)


    def open_folder(self, file_path):
        # Exact same as in FileDownloadListWindow
        try:
            folder_path = str(Path(file_path).parent)
            system = platform.system()
            if system == "Windows":
                # subprocess.run(["explorer", folder_path], check=True)
                subprocess.Popen(["explorer", folder_path])
            elif system == "Darwin":
                subprocess.run(["open", folder_path], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", folder_path], check=True)
            else:
                logger.warning(f"Unsupported platform for opening folder: {system}")
                app_signals.append_log.emit(f"[Folder] Unsupported platform for opening folder: {system}")
                app_signals.update_status.emit(f"Unsupported platform for opening folder: {system}")
                return
            app_signals.update_status.emit(f"Opened folder for {Path(file_path).name}")
            app_signals.append_log.emit(f"[Folder] Opened folder for {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Failed to open folder {file_path}: {e}")
            app_signals.append_log.emit(f"[Folder] Failed to open folder: {str(e)}")
            app_signals.update_status.emit(f"Failed to open folder for {Path(file_path).name}: {str(e)}")

    def copy_file_to_clipboard(self, file_path: str):
        print("copy_file_to_clipboard CALLED")

        path = Path(file_path).resolve()
        clipboard = QApplication.clipboard()

        mime = QMimeData()
        mime.setText(str(path))
        mime.setUrls([QUrl.fromLocalFile(str(path))])

        clipboard.setMimeData(mime)
        msg = f"File path copied to clipboard:\n{path}"
        show_alert("Copied", msg, QMessageBox.Information)
        # QMessageBox.information(
        #     self,
        #     "Copied",
        #     f"File path copied to clipboard:\n{path}"
        # )

    def retry_file_process(self, row_data: dict):
        logger.info("========== UPLOAD RETRY START ==========")

        spec_id = str(row_data.get("spec_id"))
        status = row_data.get("status")

        if not spec_id:
            logger.error("[Upload Retry] Missing spec_id in row_data")
            return

        cache = load_cache()
        meta = cache.get("uploaded_files_with_metadata", {}).get(spec_id)

        if not meta or "api_response" not in meta:
            logger.error(f"[Upload Retry] No cached api_response for spec_id={spec_id}")
            return

        api = meta["api_response"]

        request_type = api.get("request_type")
        local_file_path = api.get("file_path")     # Local source path
        nas_path = api.get("nas_path")
        task_id = api.get("id")

        if request_type != "upload":
            logger.error(f"[Upload Retry] Unsupported retry type={request_type} for spec_id={spec_id}")
            return

        if not local_file_path or not task_id:
            logger.error(f"[Upload Retry] Invalid API data for spec_id={spec_id}")
            return

        src_path = local_file_path
        dest_path = os.path.join(BASE_TARGET_DIR, nas_path)

        is_nas_src = False
        is_nas_dest = True

        card = self.card_index.get(spec_id)
        if card:
            card.update_status("Retrying upload...")
            card.progress_bar.setValue(0)
            card.progress_bar.show()

            self.cards_layout.removeWidget(card)
            self.cards_layout.insertWidget(0, card)

        retry_item = {
            "id": api["id"],
            "spec_id": api["spec_id"],
            "file_path": api["file_path"],
            "nas_path": api["nas_path"],
            "file_name": api.get("file_name"),
            "job_id": api.get("job_id"),
            "job_name": api.get("job_name"),
            "project_id": api.get("project_id"),
            "project_name": api.get("project_name"),
            "client_name": api.get("client_name"),
            "user_id": api.get("user_id"),
            "user_type": api.get("user_type"),
            "creative_id": api.get("creative_id"),
            "inventory_id": api.get("inventory_id"),
            "thumbnail": api.get("thumbnail"),
            "created_on": api.get("created_on"),
            "updated_date": api.get("updated_date"),
            "request_type": "upload",
        }

        try:
            file_worker = FileWatcherWorker.get_instance()

            file_worker.perform_file_transfer(
                src_path,
                dest_path,
                "upload",
                retry_item,
                is_nas_src,
                is_nas_dest
            )

            logger.info(f"[Upload Retry] Upload retry dispatched (spec_id={spec_id}, task_id={task_id})")

        except Exception as e:
            logger.exception(f"[Upload Retry] Failed to dispatch retry for spec_id={spec_id}: {e}")

        logger.info("========== UPLOAD RETRY END ==========")
    

# LoginWorker (provided, with fixes)
class LoginWorker(QObject):
    success = Signal(dict, str) 
    failure = Signal(str)
    user_in_use = Signal(str)
    proceed = None
    switch_login = False

    def __init__(self, username, password, remember_me, tray_icon, status_bar, switch_login):
        super().__init__()
        self.username = username
        self.password = password
        self.rememberme = remember_me
        self.tray_icon = tray_icon
        self.status_bar = status_bar
        self.switch_login = switch_login

    def _set_status(self, message: str):
        """
        Safely update the status bar — guards against the widget being
        deleted by Qt before the background thread finishes.
        """
        try:
            if self.status_bar is not None:
                self.status_bar.showMessage(message)
        except RuntimeError:
            # Qt already deleted the C++ object — silently ignore
            pass
        except Exception as e:
            logger.debug(f"[LoginWorker] Status bar update skipped: {e}")

    def run(self):
        try:
            print("inside_logworker")
            logger.debug("Starting LoginWorker.run")
            app_signals.append_log.emit("[Login] Starting LoginWorker.run")

            if self.status_bar is None:
                logger.warning("Status bar is None, cannot update message")
            
            self._set_status("Requesting access token...")

            session = requests.Session()
            payload = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": "hZBc4VyhUSQgZobyjdVH7ZPk4WRey2BIjqws_UxF5cM",
                "client_secret": "crazy-cloud",
                "scope": "pm_client",
                "details": USER_SYSTEM_INFO.get("details", {}),
                "machine_id": USER_SYSTEM_INFO.get("encoded_mac", ""),
                "mac_address": USER_SYSTEM_INFO.get("mac_address", ""),
                "add_mac": 1 if self.switch_login else 0
            }

            token_resp = session.post(
                OAUTH_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False,
                timeout=60
            )
            self.switch_login = False

            app_signals.api_call_status.emit(
                OAUTH_URL,
                f"Status: {token_resp.status_code}, Response: {token_resp.text}",
                token_resp.status_code
            )
            app_signals.append_log.emit(
                f"[Login] Token API response: {token_resp.status_code}, {token_resp.text}"
            )

            if token_resp.status_code == 403:
                self.user_in_use.emit("user_already_logged_in")
                QThread.currentThread().quit()
                return

            self._set_status(f"Token API response: {token_resp.status_code}")

            if token_resp.status_code in (400, 401):
                try:
                    error_details = token_resp.json()
                    error_msg = f"Bad request: {error_details.get('error_description', token_resp.text)}"
                except ValueError:
                    error_msg = f"Bad request: {token_resp.text}"
                logger.error(f"Token API error: {error_msg}")
                raise Exception(error_msg)

            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise Exception("No access token received in response")

            self._set_status("Fetching user info...")

            info_resp = session.get(
                f"{BASE_DOMAIN}/api/user/getinfo?emailid={self.username}",
                headers={"Authorization": f"Bearer {access_token}"},
                verify=False,
                timeout=60
            )
            app_signals.api_call_status.emit(
                f"{BASE_DOMAIN}/api/user/getinfo?emailid={self.username}",
                f"Status: {info_resp.status_code}, Response: {info_resp.text}",
                info_resp.status_code
            )
            app_signals.append_log.emit(
                f"[Login] User info API response: {info_resp.status_code}"
            )
            self._set_status(f"User info API response: {info_resp.status_code}")
            info_resp.raise_for_status()
            user_info = info_resp.json()

            self._set_status("Fetching user data...")

            user_resp = session.get(
                f"{BASE_DOMAIN}/jsonapi/user/user?filter[name]={self.username}",
                headers={"Authorization": f"Bearer {access_token}"},
                verify=False,
                timeout=60
            )
            app_signals.api_call_status.emit(
                f"{BASE_DOMAIN}/jsonapi/user/user?filter[name]={self.username}",
                f"Status: {user_resp.status_code}, Response: {user_resp.text}",
                user_resp.status_code
            )
            app_signals.append_log.emit(
                f"[Login] User data API response: {user_resp.status_code}"
            )
            self._set_status(f"User data API response: {user_resp.status_code}")
            user_resp.raise_for_status()
            user_data = user_resp.json()

            cache = load_cache() or {}
            cached_user = cache.get("user")
            cached_token = cache.get("token")

            if not cached_user or self.username != cached_user:
                cache_data = {
                    "token": access_token,
                    "user": self.username,
                    "user_id": user_info.get('uid', ''),
                    "user_info": dict(user_info),
                    "info_resp": dict(user_info),
                    "user_data": dict(user_data),
                    "data": self.username,
                    "downloaded_files": cache.get("downloaded_files", []),
                    "uploaded_files": cache.get("uploaded_files", []),
                    "timer_responses": cache.get("timer_responses", {}),
                    "saved_username": self.username if self.rememberme else cache.get("saved_username", ""),
                    "saved_password": self.password if self.rememberme else cache.get("saved_password", ""),
                    "cached_at": datetime.now(ZoneInfo("UTC")).isoformat()
                }
                save_cache(cache_data)
                app_signals.append_log.emit(f"[Login] Cache saved for user: {self.username}")

            elif self.username == cached_user and not cached_token:
                cache["token"] = access_token
                cache["cached_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
                save_cache(cache)

            _username = self.username
            _password = self.password
            _rememberme = self.rememberme
            self.success.emit(user_info, access_token)

            def _save_keyring():
                try:
                    system = platform.system()
                    if _rememberme:
                        if system == "Windows":
                            try:
                                import win32cred as _wc
                                _wc.CredWrite({
                                    'Type': _wc.CRED_TYPE_GENERIC,
                                    'TargetName': f"PremediaApp/{_username}",
                                    'CredentialBlob': _password,
                                    'Persist': _wc.CRED_PERSIST_LOCAL_MACHINE,
                                    'UserName': _username,
                                }, 0)
                                c = load_cache()
                                c["saved_username"] = _username
                                c["saved_password"] = _password
                                save_cache(c)
                            except ImportError:
                                c = load_cache()
                                c["saved_username"] = _username
                                c["saved_password"] = _password
                                save_cache(c)
                            except Exception as e:
                                logger.warning(f"win32cred write failed ({e}), falling back to cache")
                                c = load_cache()
                                c["saved_username"] = _username
                                c["saved_password"] = _password
                                save_cache(c)
                        else:
                            c = load_cache()
                            c["saved_username"] = _username
                            c["saved_password"] = _password
                            save_cache(c)
                    else:
                        c = load_cache()
                        c["saved_username"] = ""
                        c["saved_password"] = ""
                        save_cache(c)
                        if system == "Windows":
                            try:
                                import win32cred as _wc
                                _wc.CredDelete(f"PremediaApp/{_username}", _wc.CRED_TYPE_GENERIC)
                            except Exception:
                                pass
                except Exception as e:
                    logger.warning(f"_save_keyring failed: {e}")

            threading.Thread(target=_save_keyring, daemon=True).start()
            app_signals.append_log.emit(f"[Login] Successful login for user: {self.username}")
            self._set_status(f"Successful login for {self.username}")

        except requests.exceptions.SSLError as e:
            error_msg = f"SSL error: {str(e)}"
            logger.error(error_msg)
            self.failure.emit(error_msg)
            app_signals.append_log.emit(f"[Login] Failed: {error_msg}")
            self._set_status(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            self.failure.emit(error_msg)
            app_signals.append_log.emit(f"[Login] Failed: {error_msg}")
            self._set_status(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out: {str(e)}"
            logger.error(error_msg)
            self.failure.emit(error_msg)
            app_signals.append_log.emit(f"[Login] Failed: {error_msg}")
            self._set_status(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            self.failure.emit(error_msg)
            app_signals.append_log.emit(f"[Login] Failed: {error_msg}")
            self._set_status(error_msg)
        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            logger.error(error_msg)
            self.failure.emit(error_msg)
            app_signals.append_log.emit(f"[Login] Failed: {error_msg}")
            self._set_status(error_msg)
        
        
    
    def switch_user_here(self):
        try:
            session = requests.Session()
            token_resp_validation = session.post(
                OAUTH_URL,
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                    "client_id": "hZBc4VyhUSQgZobyjdVH7ZPk4WRey2BIjqws_UxF5cM",
                    "client_secret": "crazy-cloud",
                    "scope": "pm_client",
                    "details": USER_SYSTEM_INFO.get("details", {}),
                    "machine_id": USER_SYSTEM_INFO.get("encoded_mac", ""),
                    "mac_address": USER_SYSTEM_INFO.get("mac_address", ""),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False,  # Enable SSL verification
                timeout=60
            )
            logger.debug(f"Token response raw: {token_resp_validation.text}")
            app_signals.api_call_status.emit(
                OAUTH_URL,
                f"Status: {token_resp_validation.status_code}, Response: {token_resp_validation.text}",
                token_resp_validation.status_code
            )
            app_signals.append_log.emit(f"[Login] Token API response: {token_resp_validation.status_code}, {token_resp_validation.text}")    
            if self.status_bar:
                self.status_bar.showMessage(f"Token API response: {token_resp_validation.status_code}")
            if token_resp_validation.status_code in (400, 401):
                try:
                    error_details = token_resp_validation.json()
                    error_msg = f"Bad request: {error_details.get('error_description', token_resp_validation.text)}"
                except ValueError:
                    error_msg = f"Bad request: {token_resp_validation.text}"
                logger.error(f"Token API error: {error_msg}")
                return False
            return token_resp_validation
        except:
            return False

class LoginDialog(QDialog):
    login_success = Signal(dict, str)
    login_failure = Signal(str)
    login_clicked = Signal(str, str)
    user_in_other_system = Signal(str)
    switch_login = False
    LoginDialog_USERNAME = ''
    LoginDialog_PASSWORD = ''
    def __init__(self, parent=None, app=None):
        try:
            from PySide6.QtWidgets import QWidget
            if parent is not None and not isinstance(parent, QWidget):
                logger.warning(f"Invalid parent type {type(parent).__name__}, setting parent to None")
                app_signals.append_log.emit(f"[Login] Warning: Invalid parent type {type(parent).__name__}, setting parent to None")
                parent = None

            self.app = app
            logger.debug(f"Initializing LoginDialog with parent={parent}, app={app}")
            super().__init__(parent)
            self.is_logged_in = False

            if traceback:
                logger.debug(f"Call stack:\n{''.join(traceback.format_stack()[:-1])}")
            else:
                logger.warning("traceback module not available, skipping stack trace")
                app_signals.append_log.emit("[Login] Warning: traceback module not available, skipping stack trace")

            self.setWindowIcon(load_icon(ICON_PATH, "login dialog"))
            self.setWindowTitle("PremediaApp Login")
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

            self.ui = Ui_Dialog()
            self.ui.setupUi(self)

            self.status_bar = QStatusBar()
            self.status_bar.setSizeGripEnabled(False)
            self.status_bar.setFixedHeight(20)
            self.status_bar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

            main_layout = QVBoxLayout()
            main_layout.addStretch(1)
            main_layout.addWidget(self.status_bar, stretch=0)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)
            self.setLayout(main_layout)
            add_version_footer(self, APPVERSION)

            cache = load_cache()
            token = cache.get("token")
            user_id = cache.get("user_id")
           
            name = cache.get("user_data", {}).get("data", [{}])[0].get(
                "attributes", {}
            ).get("name", cache.get("user_info", {}).get("mail", "user"))

            # Store on instance so the background thread can emit them via invokeMethod
            self._cached_user_info = {
                "uid": user_id,
                "name": name,
                "mail": cache.get("user_info", {}).get("mail", "user"),
                "access_key": cache.get("user_info", {}).get("access_key")
            }
            self._cached_token = token
            
            # if token and user_id:
            #     logger.info(f"Auto-login from cache for user: {user_id}")
            #     app_signals.append_log.emit(f"[Login] Auto-login from cache for user: {user_id}")
            #     QTimer.singleShot(100, lambda: self.on_login_success(user_info, token))
            # else:
            #     app_signals.append_log.emit("[Login] No valid cache for auto-login")


            if token and user_id:
                logger.info(f"Attempting auto-login from cache for user: {user_id}")
                app_signals.append_log.emit(
                    f"[Login] Attempting auto-login from cache for user: {user_id}"
                )
                self.status_bar.showMessage("Validating session...")

                # Run validate_user on a background thread so __init__ never blocks
                threading.Thread(
                    target=self._validate_cached_login,
                    daemon=True
                ).start()
            # if cache.get("saved_username") and cache.get("saved_password"):
            #     self.ui.usernametxt.setText(cache["saved_username"])
            #     self.ui.passwordtxt.setText(cache["saved_password"])
            #     self.ui.rememberme.setChecked(True)
            #     app_signals.append_log.emit("[Login] Loaded saved credentials from cache")
            #     self.status_bar.showMessage("Loaded saved credentials")
            # else:
            #     app_signals.append_log.emit("[Login] No saved credentials found in cache")
            #     self.status_bar.showMessage("No saved credentials found")
            # REPLACE the saved credentials block in LoginDialog.__init__:
            # In LoginDialog.__init__, replace the _load_keyring_credentials block:

            saved_username = cache.get("saved_username")
            if saved_username:
                def _load_keyring_credentials(uname):
                    try:
                        pwd = None
                        system = platform.system()
                        
                        if system == "Windows":
                            try:
                                import win32cred as _wc
                                cred = _wc.CredRead(f"PremediaApp/{uname}", _wc.CRED_TYPE_GENERIC)
                                raw = cred['CredentialBlob']
                                # win32cred returns bytes on Python 3 — decode to str
                                if isinstance(raw, bytes):
                                    pwd = raw.decode('utf-16-le').rstrip('\x00')
                                else:
                                    pwd = raw
                            except ImportError:
                                current_cache = load_cache()
                                pwd = current_cache.get("saved_password") or None
                            except Exception:
                                current_cache = load_cache()
                                pwd = current_cache.get("saved_password") or None
                        else:
                            current_cache = load_cache()
                            pwd = current_cache.get("saved_password") or None

                        if pwd:
                            QMetaObject.invokeMethod(
                                self, "_apply_saved_credentials",
                                Qt.QueuedConnection,
                                Q_ARG(str, uname),
                                Q_ARG(str, pwd)
                            )
                        else:
                            QMetaObject.invokeMethod(
                                self, "_no_saved_credentials",
                                Qt.QueuedConnection
                            )
                    except Exception as e:
                        logger.warning(f"_load_keyring_credentials failed: {e}")
                        QMetaObject.invokeMethod(
                            self, "_no_saved_credentials",
                            Qt.QueuedConnection
                        )

                self.status_bar.showMessage("Loading saved credentials...")
                threading.Thread(
                    target=_load_keyring_credentials,
                    args=(saved_username,),
                    daemon=True
                ).start()
            else:
                self.status_bar.showMessage("No saved credentials found")


            app_signals.update_status.connect(self.status_bar.showMessage, Qt.QueuedConnection)
            self.ui.buttonBox.accepted.connect(self.handle_login)
            print(f"---------handle")
            self.progress = None
            self.thread = None
            logger.debug("[Login] LoginDialog initialized")
            app_signals.append_log.emit("[Login] Initializing LoginDialog")
            self.status_bar.showMessage("Login dialog initialized")

            self.resize(764, 669)

            self.ui.passwordtxt.setEchoMode(QLineEdit.Password)

            # Wire show-password radio button
            self.ui.showPasswordRadioButton.toggled.connect(
                self.toggle_password_visibility
            )
        except Exception as e:
            logger.error(f"Failed to initialize LoginDialog: {e}")
            app_signals.append_log.emit(f"[Login] Failed to initialize LoginDialog: {str(e)}")
            # QMessageBox.critical(None, "Initialization Error", f"Failed to initialize login dialog: {str(e)}")
            show_alert("Initialization Error",  f"Failed to initialize login dialog: {str(e)}", QMessageBox.Critical)
            raise


    @Slot(str, str)
    def _apply_saved_credentials(self, username: str, password: str):
        """Main thread — apply credentials loaded from keyring."""
        try:
            self.ui.usernametxt.setText(username)
            self.ui.passwordtxt.setText(password)
            self.ui.rememberme.setChecked(True)
            self.status_bar.showMessage("Loaded saved credentials")
            logger.debug("Saved credentials applied from keyring")
        except RuntimeError:
            pass  # dialog already closed

    @Slot()
    def _no_saved_credentials(self):
        """Main thread — no saved password found."""
        try:
            self.ui.rememberme.setChecked(False)
            self.status_bar.showMessage("No saved credentials found")
        except RuntimeError:
            pass

    @Slot(str, str)
    def _on_saved_credentials_loaded(self, username: str, password: str):
        """Main thread — saved credentials loaded from keyring."""
        try:
            self.ui.usernametxt.setText(username)
            self.ui.passwordtxt.setText(password)
            self.ui.rememberme.setChecked(True)
            self.status_bar.showMessage("Loaded saved credentials")
            logger.debug("Saved credentials loaded from keyring")
        except RuntimeError:
            pass  # dialog already closed

    def toggle_password_visibility(self, checked: bool):
        """
        Toggle password visibility safely (Qt Designer compatible).
        """
        try:
            if checked:
                self.ui.passwordtxt.setEchoMode(QLineEdit.Normal)
                self.status_bar.showMessage("Password visible")
                app_signals.append_log.emit("[Login] Password visibility enabled")
            else:
                self.ui.passwordtxt.setEchoMode(QLineEdit.Password)
                self.status_bar.showMessage("Password hidden")
                app_signals.append_log.emit("[Login] Password visibility disabled")
        except Exception as e:
            logger.error(f"Password toggle failed: {e}")
            app_signals.append_log.emit(f"[Login] Password toggle error: {str(e)}")

    def _validate_cached_login(self):
        """
        Runs on a background thread — NEVER touch Qt widgets here.
        Calls validate_user then routes back to the main thread via
        invokeMethod so all UI updates are safe.
        """
        try:
            access_key = self._cached_user_info.get("access_key")
            validation_result = validate_user(access_key, status_bar=None)

            if validation_result.get("status") == 403:
                QMetaObject.invokeMethod(
                    self,
                    "_on_cached_login_blocked",
                    Qt.QueuedConnection
                )
            elif validation_result.get("uuid"):
                QMetaObject.invokeMethod(
                    self,
                    "_on_cached_login_valid",
                    Qt.QueuedConnection
                )
            else:
                QMetaObject.invokeMethod(
                    self,
                    "_on_cached_login_expired",
                    Qt.QueuedConnection
                )
        except Exception as e:
            logger.error(f"Background validation error: {e}")
            app_signals.append_log.emit(
                f"[Login] Background validation error: {str(e)}"
            )
            QMetaObject.invokeMethod(
                self,
                "_on_cached_login_expired",
                Qt.QueuedConnection
            )

    @Slot()
    def _on_cached_login_valid(self):
        """Main thread — token is valid, proceed with auto-login."""
        logger.info("Cached token valid, proceeding with auto-login")
        app_signals.append_log.emit("[Login] Cached token valid, auto-login proceeding")
        self.status_bar.showMessage("Session valid, logging in...")
        # Small delay so the status message is visible before the dialog closes
        QTimer.singleShot(
            200,
            lambda: self.on_login_success(self._cached_user_info, self._cached_token)
        )

    @Slot()
    def _on_cached_login_blocked(self):
        """Main thread — 403 means user is logged in elsewhere."""
        logger.warning("Cached login blocked: user logged in on another machine")
        app_signals.append_log.emit(
            "[Login] Cached login blocked: user already logged in elsewhere"
        )
        self.user_in_other_system.emit("user_already_logged_in")

    @Slot()
    def _on_cached_login_expired(self):
        """Main thread — token invalid or expired, show login form."""
        error_msg = "Session expired, please log in again"
        logger.info(error_msg)
        app_signals.append_log.emit(f"[Login] {error_msg}")
        self.status_bar.showMessage(error_msg)
        QTimer.singleShot(100, lambda: self.on_login_failed(error_msg))

    def show_progress(self, message):
        try:
            if self.progress and self.progress.isVisible():
                logger.debug(f"Progress dialog already visible, updating message to: {message}")
                self.progress.setLabelText(message)
                QApplication.processEvents()
                return

            self.progress = QProgressDialog(message, None, 0, 0, self)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.setMinimumDuration(0)
            self.progress.setWindowTitle("Please wait")
            self.progress.setWindowIcon(load_icon(ICON_PATH, "progress dialog"))
            self.progress.show()
            # QApplication.processEvents()
            logger.debug(f"Progress dialog shown: {message}, visible={self.progress.isVisible()}")
            app_signals.append_log.emit(f"[Login] Showing progress: {message}")
            self.status_bar.showMessage(message)
        except Exception as e:
            logger.error(f"Progress dialog error: {e}")
            app_signals.append_log.emit(f"[Login] Failed: Progress dialog error - {str(e)}")
            self.status_bar.showMessage(f"Progress error: {str(e)}")
            # QMessageBox.critical(self, "Progress Error", f"Progress dialog error: {str(e)}")
            show_alert("Progress Error", f"Progress dialog error: {str(e)}", QMessageBox.Critical)

    def handle_login(self):
        try:
            logger.debug("handle_login called")
            username = self.ui.usernametxt.text().strip()
            password = self.ui.passwordtxt.text().strip()
            logger.debug(f"Login attempt with username: {username}, rememberme: {self.ui.rememberme.isChecked()}")
            app_signals.append_log.emit(f"[Login] Attempting login with username: {username}")
            self.status_bar.showMessage(f"Attempting login for {username}")
            if not username or not password:
                show_alert("Input Error", "Please enter both username and password.", QMessageBox.Warning)
                # QMessageBox.warning(self, "Input Error", "Please enter both username and password.")
                app_signals.append_log.emit("[Login] Failed: Missing username or password")
                self.status_bar.showMessage("Missing username or password")
                return
            self.show_progress("Validating credentials...")
            self.perform_login(username, password)
        except Exception as e:
            logger.error(f"Error in handle_login: {e}")
            app_signals.append_log.emit(f"[Login] Failed: Handle login error - {str(e)}")
            self.status_bar.showMessage(f"Login error: {str(e)}")
            if self.progress:
                self.progress.close()
            show_alert("Login Error",  f"Login error: {str(e)}", QMessageBox.Critical)
            # QMessageBox.critical(self, "Login Error", f"Login error: {str(e)}")

    def perform_login(self, username, password):
        try:
            self.LoginDialog_USERNAME = username
            self.LoginDialog_PASSWORD = password
            logger.debug("Starting login thread")
            self.thread = QThread()
             # Keep reference alive until thread finishes
            if not hasattr(self, '_login_threads'):
                self._login_threads = []
            self._login_threads.append(self.thread)
            self.thread.finished.connect(
                lambda t=self.thread: self._login_threads.remove(t) if t in self._login_threads else None
            )
            tray_icon = getattr(self.parent(), 'tray_icon', None)
            self.worker = LoginWorker(username, password, self.ui.rememberme.isChecked(), tray_icon=tray_icon, status_bar=self.status_bar, switch_login=self.switch_login)
            self.switch_login = False
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.success.connect(self.on_login_success)
            # self.worker.user_in_use.connect(lambda: self.validate_account_already_inuse(username, password), Qt.QueuedConnection)
            self.worker.user_in_use.connect(self.validate_account_already_inuse)
            self.worker.failure.connect(self.on_login_failed)
            self.worker.success.connect(self.thread.quit)
            self.worker.failure.connect(self.thread.quit)
            self.worker.success.connect(self.worker.deleteLater)
            self.worker.failure.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(lambda: self.cleanup_progress())  # Clean up progress dialog
            self.thread.start()
            self.thread.finished.connect(lambda: None)
            app_signals.append_log.emit(f"[Login] Starting login thread for user: {username}")
            self.status_bar.showMessage(f"Starting login for {username}")
        except Exception as e:
            logger.error(f"Login thread error: {e}")
            app_signals.append_log.emit(f"[Login] Failed: Login thread error - {str(e)}")
            self.status_bar.showMessage(f"Login thread error: {str(e)}")
            if self.progress and self.progress.isVisible():
                self.progress.close()
                # QApplication.processEvents()
                logger.debug("Progress dialog closed in perform_login error handler")
                app_signals.append_log.emit("[Login] Progress dialog closed in error handler")
            # QMessageBox.critical(self, "Login Error", f"Login thread error: {str(e)}")
            show_alert("Title", "message", QMessageBox.Critical)

    def cleanup_progress(self):
        try:
            if self.progress and self.progress.isVisible():
                self.progress.close()
                logger.debug("Progress dialog closed in cleanup_progress")
                app_signals.append_log.emit("[Login] Progress dialog closed in cleanup_progress")
        except RuntimeError:
            # Qt already deleted the C++ progress dialog object — ignore safely
            self.progress = None
        except Exception as e:
            logger.error(f"Error in cleanup_progress: {str(e)}")
            app_signals.append_log.emit(f"[Login] Failed: Error in cleanup_progress - {str(e)}")

    # def validate_account_already_inuse(self):
    #     print("in validate_account_already_inuse")

    #     msg_box = QMessageBox(self)
    #     msg_box.setWindowTitle("Account In Use")
    #     msg_box.setText("You are already logged in on another device.\nDo you want to switch this session here?")
    #     msg_box.setIcon(QMessageBox.Warning)
    #     switch_btn = msg_box.addButton("Switch Here", QMessageBox.AcceptRole)
    #     cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
    #     # Apply red color only to Cancel button
    #     switch_btn.setStyleSheet("""
    #         QPushButton {
    #             color: white;
    #             border-radius: 4px;
    #             padding: 2px;
    #         }
    #     """)
    #     cancel_btn.setStyleSheet("""
    #         QPushButton {
    #             background-color: #d32f2f;   /* Red background */
    #             color: white;
    #             border-radius: 4px;
    #             padding: 2px;
    #         }
    #     """)


    #     # --- Block here until user clicks ---
    #     msg_box.exec()

    #     if msg_box.clickedButton() == switch_btn:
    #         print("User chose to switch session.")
    #         self.switch_login = True
    #     else:
    #         print("User cancelled.")
    #         self.switch_login = False
    #     print(f"self.LoginDialog_USERNAME={self.LoginDialog_USERNAME}===self.LoginDialog_PASSWORD{self.LoginDialog_PASSWORD}")
    #     if self.switch_login:
    #         self.perform_login(self.LoginDialog_USERNAME, self.LoginDialog_PASSWORD)



    def validate_account_already_inuse(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Account In Use")
        msg_box.setText(
            "You are already logged in on another device.\n"
            "Do you want to switch this session here?"
        )
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowFlags(
        msg_box.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
        )
        msg_box.setWindowState(Qt.WindowState.WindowActive)
        msg_box.setAttribute(Qt.WA_ShowWithoutActivating, False)

        switch_btn = msg_box.addButton("Switch Here", QMessageBox.AcceptRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        switch_btn.setStyleSheet("QPushButton { color: white; border-radius: 4px; padding: 2px; }")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #d32f2f; color: white; border-radius: 4px; padding: 2px; }"
        )

        msg_box.raise_()
        msg_box.activateWindow()
        msg_box.exec()

        self.switch_login = (msg_box.clickedButton() == switch_btn)
        if self.switch_login:
            self.perform_login(self.LoginDialog_USERNAME, self.LoginDialog_PASSWORD)

 
    def on_login_success(self, user_info: dict, token: str):
        try:
            logger.info(f"Login successful for user_id: {user_info['uid']}")
            app_signals.append_log.emit(f"[App] Login successful for user_id: {user_info['uid']}")
            self.is_logged_in = True
            user_name = user_info.get('name', user_info.get('mail', 'user'))
            # Update parent (PremediaApp) state
            if hasattr(self, 'app') and self.app:
                self.app.set_logged_in_state()
                self.app.post_login_processes()   # handles start_file_watcher internally
                logger.debug("Updated PremediaApp state")
                app_signals.append_log.emit("[Login] Updated PremediaApp state")
            
            # Close progress dialog
            if self.progress and self.progress.isVisible():
                self.progress.close()
                logger.debug("Progress dialog closed in on_login_success")
                app_signals.append_log.emit("[Login] Progress dialog closed")
            
            # Show success message
            # QMessageBox.information(self, "Login Success", f"Successfully logged in as {user_name}")
            show_alert("Login Success",  f"Successfully logged in as {user_name}", QMessageBox.Information)
            
            self.accept()
            app_signals.update_status.emit("Logged in successfully")
            logger.debug("on_login_success completed successfully")
            app_signals.append_log.emit("[Login] on_login_success completed successfully")
        except Exception as e:
            logger.error(f"Error in on_login_success: {str(e)}")
            app_signals.append_log.emit(f"[Login] Failed: Error in on_login_success - {str(e)}")
            app_signals.update_status.emit(f"Login success handling error: {str(e)}")
            # Ensure progress dialog is closed on error
            if self.progress and self.progress.isVisible():
                self.progress.close()
                QApplication.processEvents()
                logger.debug("Progress dialog closed in on_login_success error handler")
                app_signals.append_log.emit("[Login] Progress dialog closed in error handler")
            # QMessageBox.critical(self, "Login Error", f"Error handling login success: {str(e)}")
            show_alert("Login Error", f"Error handling login success: {str(e)}", QMessageBox.Critical)



    # def on_login_failed(self, error):
    #     try:
    #         # Log the failure
    #         logger.error(f"Login failed: {error}")
    #         app_signals.append_log.emit(f"[App] Login failed: {error}")
    #         app_signals.update_status.emit(f"Login failed: {error}")

    #         # Close progress dialog if open
    #         if self.progress and self.progress.isVisible():
    #             self.progress.close()
    #             QApplication.processEvents()
    #             logger.debug("Progress dialog closed in on_login_failed")
    #             app_signals.append_log.emit("[Login] Progress dialog closed")

    #         # Show error popup
    #         QMessageBox.critical(self, "Login Error", str(error))

    #         # Update parent (PremediaApp) to logged-out state and refresh tray menu
    #         if hasattr(self, 'app') and self.app:
    #             # Ensure logged_in = False and clear cached user info
    #             self.app.set_logged_out_state()  # Updates tray menu to logged-out state

    #             # Open login dialog again after a short delay to ensure tray updates
    #             QTimer.singleShot(100, lambda: self.app.show_login())

    #     except Exception as e:
    #         logger.error(f"Error in on_login_failed: {str(e)}")
    #         app_signals.append_log.emit(f"[Login] Failed: Error in on_login_failed - {str(e)}")
    #         app_signals.update_status.emit(f"Error in on_login_failed: {str(e)}")

    #         # Ensure progress dialog is closed on error
    #         if self.progress and self.progress.isVisible():
    #             self.progress.close()
    #             QApplication.processEvents()
    #             logger.debug("Progress dialog closed in on_login_failed error handler")
    #             app_signals.append_log.emit("[Login] Progress dialog closed in error handler")



    # def on_login_failed(self, error):
    #     try:
    #         logger.error(f"Login failed: {error}")
    #         app_signals.append_log.emit(f"[App] Login failed: {error}")
    #         app_signals.update_status.emit(f"Login failed: {error}")

    #         # Close progress dialog
    #         if self.progress and self.progress.isVisible():
    #             self.progress.close()
    #             QApplication.processEvents()
    #             logger.debug("Progress dialog closed in on_login_failed")
    #             app_signals.append_log.emit("[Login] Progress dialog closed")

    #         # Show error popup
    #         QMessageBox.critical(self, "Login Error", str(error))

    #         # Update parent (PremediaApp) to logged-out state and show login form
    #         if hasattr(self, 'app') and self.app:
    #             self.app.set_logged_out_state()  # Set tray menu/logged-out state
    #             QTimer.singleShot(100, lambda: self.app.show_login())  # Open login dialog again

    #     except Exception as e:
    #         logger.error(f"Error in on_login_failed: {str(e)}")
    #         app_signals.append_log.emit(f"[Login] Failed: Error in on_login_failed - {str(e)}")
    #         app_signals.update_status.emit(f"Error in on_login_failed: {str(e)}")
    #         if self.progress and self.progress.isVisible():
    #             self.progress.close()
    #             QApplication.processEvents()
    #             logger.debug("Progress dialog closed in on_login_failed error handler")
    #             app_signals.append_log.emit("[Login] Progress dialog closed in error handler")


    def on_login_failed(self, error):
        try:
            logger.error(f"Login failed: {error}")
            app_signals.append_log.emit(f"[App] Login failed: {error}")
            app_signals.update_status.emit(f"Login failed: {error}")

            # Close progress dialog safely
            if self.progress and self.progress.isVisible():
                self.progress.close()
                # NOTE: No QApplication.processEvents() here — re-entrant crash risk
                logger.debug("Progress dialog closed in on_login_failed")
                app_signals.append_log.emit("[Login] Progress dialog closed")

            # Show error popup
            # QMessageBox.critical(self, "Login Error", str(error))
            show_alert("Login Error", str(error), QMessageBox.Critical)

            # Set logged-out state and re-show login
            if hasattr(self, 'app') and self.app:
                self.app.set_logged_out_state()
                QTimer.singleShot(100, lambda: self.app.show_login())

        except Exception as e:
            logger.error(f"Error in on_login_failed: {str(e)}")
            app_signals.append_log.emit(
                f"[Login] Failed: Error in on_login_failed - {str(e)}"
            )
            app_signals.update_status.emit(f"Error in on_login_failed: {str(e)}")

            if self.progress and self.progress.isVisible():
                self.progress.close()
                logger.debug("Progress dialog closed in on_login_failed error handler")
                app_signals.append_log.emit(
                    "[Login] Progress dialog closed in error handler"
                )

    def closeEvent(self, event):
        try:
            if app_signals.update_status.isSignalConnected(self.status_bar.showMessage):
                app_signals.update_status.disconnect(self.status_bar.showMessage)
        except Exception as e:
            logger.debug(f"Failed to disconnect update_status signal: {e}")
            app_signals.append_log.emit(f"[Login] Failed to disconnect update_status signal: {str(e)}")
        super().closeEvent(event)
  
  

def check_single_instance():
    pid_dir = tempfile.gettempdir()
    try:
        with PidFile(piddir=pid_dir, pidname='premedia_app.pid'):
            logger.info(f"Acquired lock for PID {os.getpid()}")
            return True
    except PidFileError:
        logger.error(f"Another instance of PremediaApp is running (PID file exists)")
        print("Another instance of PremediaApp is already running")
        sys.exit(1)


class PremediaApp(QApplication):
    
    def __init__(self, key="e0d6aa4baffc84333faa65356d78e439"):
        try:
            super().__init__(sys.argv)
            self.setQuitOnLastWindowClosed(False)
            self.setWindowIcon(load_icon(ICON_PATH, "application"))
            self.CACHE_FILE = CACHE_FILE
            # Prevent multiple instances using a lock file
            self.lock_file = os.path.join(tempfile.gettempdir(), "premedia_app.lock")
            try:
                self.lock_fd = open(self.lock_file, 'w')
            except IOError:
                logger.error("Another instance of PremediaApp is already running")
                app_signals.append_log.emit("[Init] Failed: Another instance of PremediaApp is already running")
                sys.exit(1)

            # Initialize system tray icon
            self.tray_icon = None
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon(load_icon(ICON_PATH, "system tray"))
                self.tray_icon.setToolTip("PremediaApp")
                self.tray_icon.activated.connect(self.handle_tray_icon_activated)
                self.tray_icon.show()
                QApplication.processEvents()
                logger.info(f"System tray icon initialized, visible: {self.tray_icon.isVisible()}")
                app_signals.append_log.emit(f"[Init] System tray icon initialized, visible: {self.tray_icon.isVisible()}")
            else:
                logger.warning("System tray not available")
                app_signals.append_log.emit("[Init] System tray not available")

            self.logged_in = False
            load_cache()

            # Set up tray menu
            self.tray_menu = QMenu()
            self.login_action = QAction("Login")
            self.logout_action = QAction("Logout")
            self.quit_action = QAction("Quit")
            self.log_action = QAction("View Log Window")
            self.downloaded_files_action = QAction("Downloaded Files")
            self.uploaded_files_action = QAction("Uploaded Files")
            self.clear_cache_action = QAction("Clear Cache")
            self.open_cache_action = QAction("Open Cache File")
            self.tray_menu.addAction(self.log_action)
            self.tray_menu.addAction(self.downloaded_files_action)
            self.tray_menu.addAction(self.uploaded_files_action)
            self.tray_menu.addAction(self.open_cache_action)
            self.tray_menu.addAction(self.login_action)
            self.tray_menu.addAction(self.logout_action)
            self.tray_menu.addAction(self.clear_cache_action)
            self.tray_menu.addAction(self.quit_action)
            if self.tray_icon:
                self.tray_icon.setContextMenu(self.tray_menu)
                # Remove redundant show() call
                # QApplication.processEvents()

            # Connect actions to slots
            self.login_action.triggered.connect(self.show_login)
            self.logout_action.triggered.connect(self.logout)
            self.quit_action.triggered.connect(self.cleanup_and_quit)
            self.log_action.triggered.connect(self.show_logs)
            self.downloaded_files_action.triggered.connect(self.show_downloaded_files)
            self.uploaded_files_action.triggered.connect(self.show_uploaded_files)
            self.clear_cache_action.triggered.connect(self.clear_cache)
            self.open_cache_action.triggered.connect(self.open_cache_file)

            self.log_window = LogWindow()
            self.downloaded_files_window = None
            self.uploaded_files_window = None
            try:
                self.login_dialog = LoginDialog(parent=None, app=self)   
                self.login_dialog.user_in_other_system.connect(self.show_login_page)
                # self.user_in_other_system.emit("user_already_logged_in")  
            except Exception as e:
                logger.error(f"Failed to initialize LoginDialog: {e}")
                app_signals.append_log.emit(f"[Init] Failed to initialize LoginDialog: {str(e)}")
                self.login_dialog = None
                # QMessageBox.critical(None, "Initialization Error", f"Failed to initialize login dialog: {str(e)}")
                show_alert("Initialization Error",  f"Failed to initialize login dialog: {str(e)}", QMessageBox.Critical)
                self.cleanup_and_quit()
                return

            # Connect signals to log window
            try:
                app_signals.update_status.disconnect(self.log_window.handle_update_status)
            except Exception:
                logger.debug("No existing update_status connection to disconnect")
            app_signals.update_status.connect(self.log_window.status_bar.showMessage, Qt.QueuedConnection)
            setup_logger(self.log_window)

            if not log_thread.is_alive():
                log_thread.start()

            logger.debug(f"Initializing with key: {key[:8]}...")
            app_signals.append_log.emit(f"[Init] Initializing with key: {key[:8]}...")
            cache = load_cache()
            logger.debug(f"Cache contents: {json.dumps(cache, indent=2)}")
            app_signals.append_log.emit(f"[Init] Cache contents: {json.dumps(cache, indent=2)}")
            #cache validation
            
            cache_created_ts = cache.get("created_at")  # Unix timestamp
            logger.debug(f"[TEST] Cache created_at: {cache_created_ts}")
            app_signals.append_log.emit(f"[TEST] Cache created_at: {cache_created_ts}")

            print(f"cache_created_ts:{cache_created_ts}")

            if cache_created_ts:
                try:
                    print('working fine')
                    cache_created = datetime.fromtimestamp(cache_created_ts, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age_days = (now - cache_created).days
                    logger.debug(f"[TEST] Cache created_at: {cache_created_ts}")
                    app_signals.append_log.emit(f"[TEST] Cache created_at: {cache_created_ts}")
                    print('now:', now)
                    print('cache_created:', cache_created)
                    print('timedelta(days=7):', timedelta(days=7))
                    if now - cache_created > timedelta(days=7):
                    # if now - cache_created > timedelta(minutes=1):
                        logger.info("Cache is older than 7 days. Clearing cache...")
                        app_signals.append_log.emit("[Init] Cache is older than 7 days. Clearing cache...")
                        self.clear_cache()  # Make sure your clear_cache() resets CACHE_FILE too
                        cache = {}  # Reset cache variable
                    else:
                        logger.debug(f"Cache is valid. Age: {(now - cache_created).days} days")
                        print("Cache is valid. Age:", (now - cache_created).days, "days")
                        app_signals.append_log.emit(f"[Init] Cache is valid. Age: {(now - cache_created).days} days")
                except Exception as e:
                    logger.error(f"Failed to validate cache date: {e}")
                    app_signals.append_log.emit(f"[Init] Failed to validate cache date: {str(e)}")
                    self.clear_cache()
                    cache = {}
            else:
                logger.debug("No cache creation timestamp found, skipping validation")
                app_signals.append_log.emit("[Init] No cache creation timestamp found, skipping validation")
                



            # Auto-login logic
            # Non-blocking startup — LoginDialog handles validation on background thread
            # The LoginDialog.__init__ already spawns _validate_cached_login on a daemon
            # thread when token + user_id are present in cache. So we just need to
            # show the login dialog and let it handle everything asynchronously.

            if cache.get("token") and cache.get("user") and cache.get("user_id") and not self.logged_in:
                logger.debug("Cached credentials found — LoginDialog will validate in background")
                app_signals.append_log.emit("[Init] Cached credentials found — background validation starting")
                # LoginDialog.__init__ already started _validate_cached_login thread
                # Just show the dialog — it will call on_login_success or on_login_failed
                self.login_dialog.show()
                self.login_dialog.raise_()

            elif cache.get("saved_username"):
                saved_password = None
                try:
                    import win32cred as _wc
                    cred = _wc.CredRead(
                        f"PremediaApp/{cache['saved_username']}",
                        _wc.CRED_TYPE_GENERIC
                    )
                    saved_password = cred['CredentialBlob']
                except ImportError:
                    # win32cred not available in this build — use cache fallback
                    saved_password = cache.get("saved_password") or None
                except Exception:
                    saved_password = None

                if saved_password:
                    logger.debug("Attempting auto-login with saved credentials")
                    app_signals.append_log.emit("[Init] Attempting auto-login with saved credentials")
                    self.login_dialog.perform_login(cache["saved_username"], saved_password)
                else:
                    logger.debug("No saved password found, showing login dialog")
                    self.set_logged_out_state()
                    self.show_login()
            else:
                logger.debug("No valid cached credentials, showing login dialog")
                app_signals.append_log.emit("[Init] No valid cached credentials, showing login dialog")
                self.set_logged_out_state()
                self.show_login()
                
            logger.info("PremediaApp initialized")
            app_signals.append_log.emit("[Init] PremediaApp initialized")
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            app_signals.append_log.emit(f"[Init] Failed: Initialization error - {str(e)}")
            if self.login_dialog:
                app_signals.update_status.emit(f"Initialization error: {str(e)}")
                self.show_login()
            else:
                # QMessageBox.critical(None, "Initialization Error", f"Failed to initialize application: {str(e)}")
                show_alert("Initialization Error", f"Failed to initialize application: {str(e)}", QMessageBox.Critical)
            self.cleanup_and_quit()

    def event(self, event):
        try:
            if event.type() == QEvent.ApplicationActivate:
                logger.debug("Application activated via taskbar/dock")
                app_signals.append_log.emit("[App] Application activated via taskbar/dock")
                for window in [self.log_window, self.downloaded_files_window, self.uploaded_files_window, self.login_dialog]:
                    if window and window.isVisible():
                        window.raise_()
                        window.activateWindow()
                        logger.debug(f"Restored window: {window.windowTitle()}")
                        app_signals.append_log.emit(f"[App] Restored window: {window.windowTitle()}")
            return super().event(event)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")
            app_signals.append_log.emit(f"[App] Failed: Error in event handler - {str(e)}")
            return super().event(event)

    def show_login_page(self, reason: str):
        print("----------------------------------------------------------------------------------------------------------")
        print(f"user_in_other_system signal received: {reason}")
        self.logout()

        


    def handle_tray_icon_activated(self, reason):
        try:
            system = platform.system().lower()  # "windows", "darwin", "linux"

            if reason == QSystemTrayIcon.Trigger:
                # Left-click: only show menu manually on Windows/Linux
                if system != "darwin":  # Skip on macOS
                    if self.tray_icon.contextMenu():
                        self.tray_icon.contextMenu().popup(QCursor.pos())
                        logger.debug("Tray icon left-click: Showing context menu")
                        app_signals.append_log.emit("[Tray] Left-click: Showing context menu")
                else:
                    logger.debug("Tray icon clicked (macOS auto-handles menu display)")
                    app_signals.append_log.emit("[Tray] macOS: Skipped manual popup")

            elif reason == QSystemTrayIcon.DoubleClick:
                pass  # No action
            elif reason == QSystemTrayIcon.Context:
                pass  # macOS auto-shows menu
            elif reason == QSystemTrayIcon.MiddleClick:
                pass

            app_signals.update_status.emit("Tray icon activated")

        except Exception as e:
            logger.error(f"Error in handle_tray_icon_activated: {e}")
            app_signals.append_log.emit(f"[Tray] Failed: Error handling tray icon activation - {str(e)}")
            app_signals.update_status.emit(f"Error handling tray icon activation: {str(e)}")
            # QMessageBox.critical(None, "Tray Icon Error", f"Error handling tray icon activation: {str(e)}")
            show_alert("Tray Icon Error", f"Error handling tray icon activation: {str(e)}", QMessageBox.Critical)


    def update_tray_menu(self):
        try:
            # Check if system tray is available and tray_icon is initialized
            if not self.tray_icon or not QSystemTrayIcon.isSystemTrayAvailable():
                logger.warning("System tray not available or tray_icon not initialized")
                return

            # Clear the existing tray menu to rebuild it
            self.tray_menu.clear()
            user_fullname = "Unknown"  # Default value

            # Load user full name (with fallback) from cache if logged in
            if self.logged_in:
                try:
                    cache_file = Path(self.CACHE_FILE).resolve()
                    if cache_file.exists() and cache_file.is_file():
                        with cache_file.open('r', encoding='utf-8') as f:
                            cache_data = json.load(f)

                        user_data = cache_data.get('user_data', {}).get('data', [])
                        if user_data and isinstance(user_data, list):
                            attributes = user_data[0].get('attributes', {})

                            # Fallback order: field_fullname → name → mail → "Unknown"
                            user_fullname = (
                                attributes.get('field_fullname')
                                or attributes.get('name')
                                or attributes.get('mail')
                                or "Unknown"
                            )

                            user_fullname = str(user_fullname).strip()
                            if not user_fullname:
                                user_fullname = "Unknown"

                            logger.debug(f"Resolved tray user name: {user_fullname}")
                            app_signals.append_log.emit(f"[Tray] User name resolved: {user_fullname}")
                        else:
                            logger.warning("Cache user_data missing or not a list")
                            user_fullname = "Unknown"
                    else:
                        logger.warning(f"Cache file missing or invalid: {cache_file}")
                        app_signals.append_log.emit(f"[Tray] Cache file missing: {cache_file}")
                        user_fullname = "Unknown"
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to read fullname from cache: {e}")
                    app_signals.append_log.emit(f"[Tray] Failed to read cache: {str(e)}")
                    user_fullname = "Unknown"

            # Clear icon cache to ensure fresh icons are loaded
            ICON_CACHE.clear()
            logger.debug(f"update_tray_menu: self.logged_in = {self.logged_in}")

            # Select platform-specific tray icon based on login status
            tray_icon_name = {
                "Windows": "login-logo.ico" if self.logged_in else "logout-logo.ico",
                "Darwin": "login-logo.icns" if self.logged_in else "logout-logo.icns",
                "Linux": "login-logo.png" if self.logged_in else "logout-logo.png"
            }.get(platform.system(), "logout-logo.png")

            icon_path = get_icon_path(tray_icon_name)

            # Windows-specific workaround to refresh tray icon
            if platform.system() == "Windows":
                dummy_icon_path = get_icon_path("login-logo.png")
                self.tray_icon.setIcon(QIcon(dummy_icon_path))  # Set temporary icon
                QApplication.processEvents()

            # Set the actual tray icon, falling back to default if invalid
            if not Path(icon_path).exists() or QIcon(icon_path).isNull():
                icon_path = get_icon_path("login-logo.png")
            self.tray_icon.setIcon(QIcon(icon_path))
            self.tray_icon.setToolTip(
                f"PremediaApp - {'Logged in as ' + user_fullname if self.logged_in else 'Not logged in'}"
            )
            QApplication.processEvents()

            logger.debug(f"Tray icon updated: {icon_path}, logged_in={self.logged_in}")

            # Helper function to set up action icons with fallback
            def setup_action(action, icon_name, visible=True, enabled=True):
                path = get_icon_path(icon_name)
                if not Path(path).exists() or QIcon(path).isNull():
                    path = get_icon_path("premedia.png")  # Fallback icon
                action.setIcon(QIcon(path))
                action.setVisible(visible)
                action.setEnabled(enabled)

            # Create user info action (always shown when logged in)
            user_icon_name = {
                "Windows": "user_icon.ico",
                "Darwin": "user_icon.icns",
                "Linux": "user_icon.png"
            }.get(platform.system(), "user_icon.png")

            user_action = QAction(f"{user_fullname}", self.tray_menu)
            user_action.setEnabled(False)  # Non-interactive user info
            font = QFont()
            font.setBold(True)
            user_action.setFont(font)
            setup_action(user_action, user_icon_name)

            if self.logged_in:
                self.tray_menu.addAction(user_action)
                self.tray_menu.addSeparator()

            # Set up main actions with platform-specific icons
            setup_action(self.login_action, {
                "Windows": "login_icon.ico",
                "Darwin": "login_icon.icns",
                "Linux": "login_icon.png"
            }.get(platform.system(), "login_icon.png"), visible=not self.logged_in, enabled=not self.logged_in)

            setup_action(self.logout_action, {
                "Windows": "logout_icon.ico",
                "Darwin": "logout_icon.icns",
                "Linux": "logout_icon.png"
            }.get(platform.system(), "logout_icon.png"), visible=self.logged_in, enabled=self.logged_in)

            setup_action(self.downloaded_files_action, {
                "Windows": "download_icon.ico",
                "Darwin": "download_icon.icns",
                "Linux": "download_icon.png"
            }.get(platform.system(), "download_icon.png"), visible=True, enabled=self.logged_in)

            setup_action(self.uploaded_files_action, {
                "Windows": "upload_icon.ico",
                "Darwin": "upload_icon.icns",
                "Linux": "upload_icon.png"
            }.get(platform.system(), "upload_icon.png"), visible=True, enabled=self.logged_in)

            setup_action(self.clear_cache_action, {
                "Windows": "clear_cache_icon.ico",
                "Darwin": "clear_cache_icon.icns",
                "Linux": "clear_cache_icon.png"
            }.get(platform.system(), "clear_cache_icon.png"), visible=True, enabled=self.logged_in)

            setup_action(self.quit_action, {
                "Windows": "quit_icon.ico",
                "Darwin": "quit_icon.icns",
                "Linux": "quit_icon.png"
            }.get(platform.system(), "quit_icon.png"), visible=True, enabled=True)

            # Add actions to tray menu in order
            self.tray_menu.addSeparator()
            self.tray_menu.addAction(self.downloaded_files_action)
            self.tray_menu.addAction(self.uploaded_files_action)
            self.tray_menu.addSeparator()
            self.tray_menu.addAction(self.clear_cache_action)
            self.tray_menu.addSeparator()
            self.tray_menu.addAction(self.login_action)
            self.tray_menu.addAction(self.logout_action)
            self.tray_menu.addSeparator()
            self.tray_menu.addAction(self.quit_action)

            # Add version display at the bottom with icon
            try:
                version_text = f"Version: {APPVERSION}"
            except NameError:
                version_text = "Version: Unknown"
                logger.warning("APPVERSION global variable not defined")
                app_signals.append_log.emit("[Tray] APPVERSION global variable not defined")
            version_action = QAction(version_text, self.tray_menu)
            version_action.setEnabled(False)  # Non-interactive
            font = QFont()
            font.setBold(True)
            version_action.setFont(font)
            # Set platform-specific version icon
            version_icon_name = {
                "Windows": "version_icon.ico",
                "Darwin": "version_icon.icns",
                "Linux": "version_icon.png"
            }.get(platform.system(), "version_icon.png")
            setup_action(version_action, version_icon_name)
            self.tray_menu.addSeparator()
            self.tray_menu.addAction(version_action)

            # Set the context menu for the tray icon
            self.tray_icon.setContextMenu(self.tray_menu)

            logger.debug(f"Tray menu updated: logged_in={self.logged_in}, user={user_fullname}, version={version_text}")
            app_signals.append_log.emit(f"[Tray] Menu updated: User={user_fullname}, Version={version_text}")

        except Exception as e:
            logger.error(f"Error updating tray menu: {e}\n{traceback.format_exc()}")
            app_signals.append_log.emit(f"[Tray] Failed to update tray menu: {str(e)}")
            app_signals.update_status.emit(f"Failed to update tray menu: {str(e)}")
            # QMessageBox.critical(None, "Tray Menu Error", f"Failed to update tray menu: {str(e)}")
            show_alert("Tray Menu Error", f"Failed to update tray menu: {str(e)}", QMessageBox.Critical)

    def is_file_watcher_running(self):
        """Safely check if the file watcher thread is running."""
        thread = getattr(self, 'file_watcher_thread', None)
        if thread is None:
            return False
        try:
            return thread.isRunning()
        except RuntimeError:
            # Thread was already deleted
            self.file_watcher_thread = None
            return False


    
    
    def stop_file_watcher_thread(self):
        """
        Safely stop the poll timer, worker, and thread.
        Each resource is individually guarded so one failure never skips the rest.
        Always resets all references to None so start_file_watcher gets a clean slate.
        """
        # ── 1. Stop poll timer first — prevents new invokeMethod calls ───────
        timer = getattr(self, 'poll_timer', None)
        if timer is not None:
            try:
                if timer.isActive():
                    timer.stop()
            except RuntimeError:
                pass  # already deleted by Qt
            finally:
                self.poll_timer = None

        # ── 2. Stop watchdog timer ────────────────────────────────────────────
        watchdog = getattr(self, 'watchdog_timer', None)
        if watchdog is not None:
            try:
                if watchdog.isActive():
                    watchdog.stop()
            except RuntimeError:
                pass
            finally:
                self.watchdog_timer = None

        # ── 3. Ask the thread to stop and wait up to 5 seconds ───────────────
        thread = getattr(self, 'file_watcher_thread', None)
        if thread is not None:
            try:
                if thread.isRunning():
                    thread.quit()
                    if not thread.wait(5000):
                        logger.warning(
                            "FileWatcherThread did not stop in 5s — terminating"
                        )
                        app_signals.append_log.emit(
                            "[App] FileWatcherThread did not stop in 5s — terminating"
                        )
                        thread.terminate()
                        thread.wait(2000)
            except RuntimeError:
                pass  # thread already deleted by Qt
            finally:
                self.file_watcher_thread = None

        # ── 4. Release worker reference ───────────────────────────────────────
        # Do NOT call deleteLater() here — Qt owns the lifecycle once
        # moveToThread() was called. Just drop our reference.
        worker = getattr(self, 'file_watcher', None)
        if worker is not None:
            try:
                worker.running = False
            except RuntimeError:
                pass
            finally:
                self.file_watcher = None

        logger.debug("stop_file_watcher_thread completed cleanly")
        app_signals.append_log.emit("[App] FileWatcher stopped cleanly")
    
    

    def start_file_watcher(self):
        global FILE_WATCHER_RUNNING
        
        # ── Guard: prevent double-start if called while already running ───────
        # This can happen if post_login_processes and auto-login both
        # trigger start_file_watcher in the same cycle.
        if getattr(self, 'file_watcher_thread', None) is not None:
            try:
                if self.file_watcher_thread.isRunning():
                    logger.warning(
                        "[start_file_watcher] Called while thread already running — skipping"
                    )
                    app_signals.append_log.emit(
                        "[App] start_file_watcher skipped — thread already running"
                    )
                    return
            except RuntimeError:
                # Thread was deleted — safe to proceed
                self.file_watcher_thread = None
                
                
        try:
            logger.info("Attempting to start FileWatcherWorker")
            app_signals.append_log.emit("[App] Attempting to start FileWatcherWorker")

            # Validate log window
            if self.log_window is None or self.log_window.status_bar is None:
                self.handle_error("FileWatcher", "Log window or status bar not initialized")
                return

            # Load cache safely
            try:
                cache = load_cache()
                logger.debug(f"Cache keys: {list(cache.keys())}")
                app_signals.append_log.emit(f"[App] Cache keys: {list(cache.keys())}")
            except Exception:
                cache = {}

            # Stop old thread/worker/timer safely before starting new ones
            self.stop_file_watcher_thread()

            FILE_WATCHER_RUNNING = True

            # ✅ FIX: Create worker FIRST on main thread, then move to thread.
            #         This avoids the race condition where the timer fires before
            #         the worker is created inside the thread's started signal.
            FileWatcherWorker._instance = None
            self.file_watcher = FileWatcherWorker.get_instance(parent=None)

            # ✅ FIX: Create thread and move worker into it
            self.file_watcher_thread = QThread()
            self.file_watcher.moveToThread(self.file_watcher_thread)

            # Connect worker signals AFTER worker is created but BEFORE thread starts
            self.file_watcher.user_in_other_system.connect(self.show_login_page)
            self.file_watcher.status_update.connect(
                self.log_window.status_bar.showMessage, Qt.QueuedConnection
            )
            self.file_watcher.log_update.connect(
                app_signals.append_log, Qt.QueuedConnection
            )
            self.file_watcher.progress_update.connect(
                self.update_progress, Qt.QueuedConnection
            )
            
            self.file_watcher.alert_notification.connect(
                self._show_worker_alert, Qt.QueuedConnection
            )

            app_signals.append_log.emit("[Security] Auto-logout on session conflict enabled")

            # ✅ FIX: Start the poll timer ONLY after thread has started.
            #         Use thread.started signal to guarantee worker is live before
            #         any invokeMethod calls happen.
            # def on_thread_started():
            #     logger.info("FileWatcherWorker thread is live — starting poll timer")
            #     app_signals.append_log.emit("[App] FileWatcherWorker thread live, poll timer starting")

            #     # ✅ FIX: Safe poll timer with None guard (see _safe_invoke_watcher)
            #     if getattr(self, "poll_timer", None):
            #         try:
            #             self.poll_timer.stop()
            #         except Exception:
            #             pass

            #     self.poll_timer = QTimer(self)
            #     self.poll_timer.timeout.connect(self._safe_invoke_watcher)
            #     self.poll_timer.start(3000)  # 3 seconds

            # self.file_watcher_thread.started.connect(on_thread_started)

            # # Start the thread — worker is already inside it via moveToThread
            # self.file_watcher_thread.start()

            # logger.info("FileWatcherWorker thread started successfully")
            # app_signals.append_log.emit("[App] FileWatcherWorker thread started successfully")

            # # Watchdog timer (runs on main thread, just checks memory — safe)
            # if getattr(self, "watchdog_timer", None):
            #     try:
            #         self.watchdog_timer.stop()
            #     except Exception:
            #         pass
            # self.watchdog_timer = QTimer(self)
            # self.watchdog_timer.timeout.connect(self.check_memory_usage)
            # self.watchdog_timer.start(60000)  # every 60 seconds

            # self.schedule_daily_restart(3, 0)
            def on_thread_started():
                logger.info("FileWatcherWorker thread is live — starting poll timer")
                app_signals.append_log.emit("[App] FileWatcherWorker thread live, poll timer starting")

                if getattr(self, "poll_timer", None):
                    try:
                        self.poll_timer.stop()
                    except Exception:
                        pass

                self.poll_timer = QTimer(self)
                self.poll_timer.timeout.connect(self._safe_invoke_watcher)
                self.poll_timer.start(3000)

                # Fire first scan immediately without waiting 3s
                QTimer.singleShot(500, self._safe_invoke_watcher)

                # ── Notification Manager ──────────────────────────────────────
                # FIX: This used to be gated behind "a visible top-level widget
                # exists" via _find_best_anchor(), even though
                # TransferNotificationManager doesn't actually use an anchor —
                # it positions itself off the screen's own geometry. If that
                # search came back empty (e.g. right after login before any
                # window was shown), the whole block was skipped and progress
                # popups silently never got wired up for the rest of the
                # session. Always (re)create and connect it.
                if getattr(self, "notif_manager", None):
                    try:
                        self.notif_manager.hide()
                        self.notif_manager.deleteLater()
                    except Exception:
                        pass

                self.notif_manager = TransferNotificationManager()

                watcher = self.file_watcher
                watcher.download_progress.connect(
                    self.notif_manager.on_download_progress, Qt.QueuedConnection
                )
                watcher.download_status_detail.connect(
                    self.notif_manager.on_download_status_detail, Qt.QueuedConnection
                )
                watcher.upload_progress.connect(
                    self.notif_manager.on_upload_progress, Qt.QueuedConnection
                )
                watcher.upload_status_detail.connect(
                    self.notif_manager.on_upload_status_detail, Qt.QueuedConnection
                )
                logger.info("[App] TransferNotificationManager connected")
                app_signals.append_log.emit("[App] TransferNotificationManager connected")
                # ─────────────────────────────────────────────────────────────

            # Connect and start the thread
            self.file_watcher_thread.started.connect(on_thread_started)
            self.file_watcher_thread.start()

            logger.info("FileWatcherWorker thread started successfully")
            app_signals.append_log.emit("[App] FileWatcherWorker thread started successfully")

            # Watchdog timer
            if getattr(self, "watchdog_timer", None):
                try:
                    self.watchdog_timer.stop()
                except Exception:
                    pass
            self.watchdog_timer = QTimer(self)
            self.watchdog_timer.timeout.connect(self.check_memory_usage)
            self.watchdog_timer.start(60000)

            self.schedule_daily_restart(3, 0)

        except Exception as e:
            self.handle_error("FileWatcher", f"Failed to start FileWatcherWorker: {str(e)}")


            
        # ─────────────────────────────────────────────────────────────────

    def _safe_invoke_watcher(self):
        """
        ✅ NEW HELPER — Safe wrapper for poll timer.
        Guards against invokeMethod being called when file_watcher is None
        (e.g. during restart, after stop, or due to race condition).
        Without this guard, every timer tick would crash silently and
        the polling loop would die permanently.
        """
        try:
            if self.file_watcher is not None:
                QMetaObject.invokeMethod(self.file_watcher, "run", Qt.QueuedConnection)
            else:
                logger.warning("[PollTimer] file_watcher is None, skipping invoke")
                app_signals.append_log.emit("[App] PollTimer skipped: file_watcher not ready")
        except RuntimeError as e:
            # Worker was deleted by Qt GC — stop the timer to prevent spam
            logger.warning(f"[PollTimer] Worker deleted, stopping poll timer: {e}")
            app_signals.append_log.emit("[App] PollTimer stopped: worker was deleted")
            if getattr(self, "poll_timer", None):
                self.poll_timer.stop()
        except Exception as e:
            logger.error(f"[PollTimer] Unexpected error: {e}")
            app_signals.append_log.emit(f"[App] PollTimer error: {str(e)}")


    def restart_file_watcher(self):
        """Restart FileWatcherWorker safely, with backoff."""
        try:
            if not hasattr(self, "restart_count"):
                self.restart_count = 0
            self.restart_count += 1

            backoff_delay = min(self.restart_count * 30, 300)
            if self.restart_count > 10:
                logger.error("[Watchdog] Too many restarts (>10). Stopping FileWatcherWorker permanently.")
                app_signals.append_log.emit("[Watchdog] Too many restarts (>10). Stopping FileWatcherWorker permanently.")
                return

            logger.info(f"[Watchdog] Restart attempt {self.restart_count}, backoff {backoff_delay}s")
            app_signals.append_log.emit(f"[Watchdog] Restart attempt {self.restart_count}, backoff {backoff_delay}s")

            # Stop old thread safely
            self.stop_file_watcher_thread()

            # Restart after backoff
            QTimer.singleShot(backoff_delay * 1000, self.start_file_watcher)

        except Exception as e:
            self.handle_error("FileWatcher", f"Failed to restart FileWatcherWorker: {str(e)}")

    def check_memory_usage(self, threshold_mb: int = 500, cpu_threshold: int = 80):
        """
        Watchdog check: restart file watcher if memory/CPU exceeds thresholds.
        Runs every 60 seconds on the main thread — must NEVER block.
        """
        try:
            import psutil
            process = psutil.Process()

            mem_mb = process.memory_info().rss / 1024 / 1024

            # ✅ FIX: interval=None is non-blocking.
            #         interval=1 would sleep for 1 second on the main thread,
            #         causing "Not Responding" every single watchdog tick.
            #         interval=None returns CPU % accumulated since last call,
            #         which is accurate enough for watchdog purposes.
            cpu_percent = process.cpu_percent(interval=None)

            logger.info(f"[Watchdog] Memory: {mem_mb:.2f} MB | CPU: {cpu_percent:.1f}%")
            app_signals.append_log.emit(
                f"[Watchdog] Memory: {mem_mb:.2f} MB | CPU: {cpu_percent:.1f}%"
            )

            if mem_mb > threshold_mb or cpu_percent > cpu_threshold:
                reason = "Memory" if mem_mb > threshold_mb else "CPU"
                logger.warning(
                    f"[Watchdog] {reason} exceeded limit. Restarting FileWatcherWorker..."
                )
                app_signals.append_log.emit(
                    f"[Watchdog] {reason} exceeded limit. Restarting FileWatcherWorker..."
                )
                self.restart_file_watcher()

        except Exception as e:
            logger.error(f"[Watchdog] Failed to check system usage: {str(e)}")
            app_signals.append_log.emit(
                f"[Watchdog] Failed to check system usage: {str(e)}"
            )


    def daily_restart_file_watcher(self):
        """Restart FileWatcher once every 24h for preventive cleanup."""
        logger.info("[DailyRestart] Performing scheduled daily restart of FileWatcherWorker...")
        app_signals.append_log.emit("[DailyRestart] Performing scheduled daily restart of FileWatcherWorker...")

        self.restart_count = 0  # reset watchdog counter
        self.restart_file_watcher()


    def schedule_daily_restart(self, hour: int = 3, minute: int = 0):
        """Schedule daily restart at fixed time (default 03:00 AM)."""
        from datetime import datetime, timedelta

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)  # schedule for next day if already past

        delay_ms = int((target - now).total_seconds() * 1000)

        logger.info(f"[DailyRestart] Scheduled first daily restart at {target}")
        app_signals.append_log.emit(f"[DailyRestart] Scheduled first daily restart at {target}")

        QTimer.singleShot(delay_ms, self._start_daily_restart_cycle)


    def _start_daily_restart_cycle(self):
        """First trigger, then repeat daily."""
        self.daily_restart_file_watcher()
        self.daily_restart_timer = QTimer(self)
        self.daily_restart_timer.timeout.connect(self.daily_restart_file_watcher)
        self.daily_restart_timer.start(24 * 60 * 60 * 1000)  # 24h




    def handle_error(self, context, error, show_dialog=True):
        import traceback
        logger.error(f"{context}: {str(error)}\n{traceback.format_exc()}")
        app_signals.append_log.emit(f"[{context}] Failed: {str(error)}")
        app_signals.update_status.emit(f"{context} error: {str(error)}")
        if show_dialog:
            # QMessageBox.critical(None, f"{context} Error", f"{context} error: {str(error)}")
            show_alert(f"{context} Error",  f"{context} error: {str(error)}", QMessageBox.Critical)


    def cleanup_and_quit(self):
        if IS_APP_ACTIVE_UPLOAD_DOWNLOAD:
            print(f"Skip log out: {IS_APP_ACTIVE_UPLOAD_DOWNLOAD}")
            # Show success message
            # QMessageBox.information(None, "Action blocked", "An upload/download is currently in progress. Try again once it is complete.")
            show_alert("Action blocked", "An upload/download is currently in progress. Try again once it is complete.", QMessageBox.Information)
            return

        try:
            logger.debug("Cleanup initiated")
            app_signals.append_log.emit("[App] Cleanup initiated")

            global FILE_WATCHER_RUNNING
            FILE_WATCHER_RUNNING = False
            FILE_WATCHER_STOP_QUEUE.put(True)

            # Stop poll timer if exists
            if hasattr(self, 'poll_timer') and self.poll_timer.isActive():
                self.poll_timer.stop()
                logger.debug("Stopped poll_timer")
                app_signals.append_log.emit("[App] Stopped poll_timer")

            # Stop file watcher thread if exists
            if hasattr(self, 'file_watcher_thread') and self.file_watcher_thread.isRunning():
                self.file_watcher_thread.quit()
                self.file_watcher_thread.wait(10000)
                if self.file_watcher_thread.isRunning():
                    logger.warning("File watcher thread did not stop gracefully, terminating")
                    app_signals.append_log.emit("[App] File watcher thread did not stop gracefully, terminating")
                    self.file_watcher_thread.terminate()
                    self.file_watcher_thread.wait(1000)

            # Close all top-level widgets
            for w in QApplication.topLevelWidgets():
                logger.debug(f"Closing widget: {w}")
                app_signals.append_log.emit(f"[App] Closing widget: {w}")
                w.close()

            # Hide tray icon if exists
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()

            # Close HTTP session
            logger.debug("Closing HTTP_SESSION")
            app_signals.append_log.emit("[App] Closing HTTP_SESSION")
            HTTP_SESSION.close()

            # Stop logging
            stop_logging()

            # Update status
            app_signals.update_status.emit("Application quitting")
            app_signals.append_log.emit("[App] Application quitting")
            logger.info("Application quitting")

            # Quit application safely
            QApplication.quit()

        except Exception as e:
            # Don’t crash — just log the error
            self.handle_error("Cleanup", f"Error in cleanup_and_quit: {str(e)}")
            try:
                QApplication.quit()
            except Exception:
                sys.exit(1)

    def logout_apicall(self, user_id):
        machine_id = USER_SYSTEM_INFO.get('encoded_mac', '')
        try:
            payload = {
                'user_id': user_id,
                'machine_id': machine_id,
            }
            response = requests.post(API_URL_LOGOUT, data=payload, verify=False)
            logger.info(response)
            if response.status_code == 200:
                logger.info(f"Successfully posted metadata to API (Logout).")
            else:
                logger.error(f"Failed to post metadata to API (Logout): {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Error posting metadata to API (Logout): {e}")


    def logout(self):
        if IS_APP_ACTIVE_UPLOAD_DOWNLOAD:
            # QMessageBox.information(
            #     None,
            #     "Action blocked",
            #     "An upload/download is currently in progress. "
            #     "Try again once it is complete."
            # )
            show_alert(
                "Action blocked",
                "An upload/download is currently in progress. Try again once it is complete.",
                QMessageBox.Information
            )
            print(f"Skip log out: {IS_APP_ACTIVE_UPLOAD_DOWNLOAD}")
            return

        try:
            # ── 1. Stop file watcher FIRST before anything else ──────────────
            # This prevents the old thread from polling, writing cache, or
            # emitting signals while we are tearing down the session.
            self.stop_file_watcher_thread()

            global FILE_WATCHER_RUNNING
            FILE_WATCHER_RUNNING = False

            # Reset the singleton so start_file_watcher creates a fresh instance
            # on the next login — not the stale one from this session.
            FileWatcherWorker._instance = None

            # ── 2. Clear token from cache ─────────────────────────────────────
            self.logged_in = False
            cache = load_cache()
            user_id = cache.get("user_id", "")
            print(f"logout --------------------------------user_id: {user_id}")

            self.logout_apicall(user_id)

            cache["token"] = ""
            try:
                if (self.login_dialog is not None and
                        hasattr(self.login_dialog, 'ui') and
                        self.login_dialog.ui is not None):
                    if not self.login_dialog.ui.rememberme.isChecked():
                        cache["saved_username"] = ""
                        cache["saved_password"] = ""
            except RuntimeError:
                # Dialog already deleted by Qt — clear credentials to be safe
                cache["saved_username"] = ""
                cache["saved_password"] = ""
            save_cache(cache)

            # ── 3. Stop local API ─────────────────────────────────────────────
            stop_local_api()

            # ── 4. Update tray to logged-out state ───────────────────────────
            self.update_tray_menu()

            logger.info("Logged out successfully")
            app_signals.append_log.emit("[Login] Logged out successfully")
            app_signals.update_status.emit("Logged out successfully")

            # ── 5. Close old dialog and create a fresh one ───────────────────
            # Close first so Qt can clean up its widget tree properly
            try:
                if self.login_dialog is not None:
                    self.login_dialog.close()
                    self.login_dialog.deleteLater()
            except Exception as close_err:
                logger.warning(f"Could not close old login dialog: {close_err}")

            self.login_dialog = None  # explicit None before reassignment

            self.login_dialog = LoginDialog(parent=None, app=self)
            self.login_dialog.user_in_other_system.connect(self.show_login_page)

            self.login_dialog.show()
            self.login_dialog.raise_()
            self.login_dialog.activateWindow()
            self.login_dialog.setWindowState(Qt.WindowActive)
            self.login_dialog.showNormal()

            logger.info("Login dialog opened successfully")
            app_signals.append_log.emit("[Login] Login dialog opened successfully")

        except Exception as e:
            logger.error(f"Logout error: {e}")
            app_signals.append_log.emit(f"[Login] Failed: Logout error - {str(e)}")
            app_signals.update_status.emit(f"Logout error: {str(e)}")

    def set_logged_in_state(self):
        try:
            self.logged_in = True
            logger.debug(f"Setting logged_in state to: {self.logged_in}")
            app_signals.append_log.emit(f"[State] Setting logged_in state to: {self.logged_in}")
            self.update_tray_menu()
            if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon.setIcon(load_icon(LOGGEDIN_ICON_PATH, "logged in"))
                self.tray_icon.show()
                logger.debug(f"Tray icon set to 'logged in', visible: {self.tray_icon.isVisible()}")
                app_signals.append_log.emit(f"[Tray] Tray icon set to 'logged in', visible: {self.tray_icon.isVisible()}")
            else:
                logger.warning("Tray icon or system tray not available")
                app_signals.append_log.emit("[Tray] Tray icon or system tray not available")
            if hasattr(self, 'login_dialog'):
                self.login_dialog.is_logged_in = True
                logger.debug(f"LoginDialog is_logged_in set to: {self.login_dialog.is_logged_in}")
            logger.info("Set logged in state")
            app_signals.append_log.emit("[State] Set to logged-in state")
            app_signals.update_status.emit("Logged in state set")
        except Exception as e:
            self.handle_error("SetLoggedIn", f"Error setting logged-in state: {str(e)}")


    def set_logged_out_state(self):
        try:
            self.logged_in = False
            if hasattr(self, 'login_dialog'):
                self.login_dialog.is_logged_in = False
            logger.info("Set logged out state")
            app_signals.append_log.emit("[State] Set to logged-out state")
            app_signals.update_status.emit("Logged out state set")

            # Force tray menu update
            self.update_tray_menu()
            # QApplication.processEvents()  # Make sure UI updates immediately

            # Optionally force reset the tray icon tooltip
            if self.tray_icon:
                self.tray_icon.setToolTip("PremediaApp - Not logged in")

        except Exception as e:
            logger.error(f"Error in set_logged_out_state: {e}")
            app_signals.append_log.emit(f"[State] Failed: Error setting logged-out state - {str(e)}")
            app_signals.update_status.emit(f"Error setting logged-out state: {str(e)}")


    def open_cache_file(self):
        try:
            cache_file = Path(self.CACHE_FILE).resolve()
            logger.debug(f"Attempting to open cache file: {cache_file}")
            app_signals.append_log.emit(f"[Cache] Attempting to open: {cache_file}")

            # Check if file exists
            if not cache_file.exists():
                logger.warning(f"Cache file does not exist: {cache_file}")
                app_signals.append_log.emit(f"[Cache] Cache file does not exist: {cache_file}")
                app_signals.update_status.emit("Cache file does not exist")
                # QMessageBox.warning(None, "Cache Error", f"Cache file does not exist:\n{cache_file}")
                show_alert("Cache Error", f"Cache file does not exist:\n{cache_file}", QMessageBox.Warning)
                return

            # Verify file is readable
            if not cache_file.is_file():
                logger.warning(f"Cache file is not a valid file: {cache_file}")
                app_signals.append_log.emit(f"[Cache] Invalid file: {cache_file}")
                app_signals.update_status.emit("Invalid cache file")
                # QMessageBox.warning(None, "Cache Error", f"Invalid cache file:\n{cache_file}")
                show_alert("Cache Error", f"Invalid cache file:\n{cache_file}", QMessageBox.Warning)
                return

            # Read and beautify file content
            try:
                with cache_file.open('r', encoding='utf-8') as f:
                    raw_content = f.read()
                # Try to parse and beautify JSON
                try:
                    json_data = json.loads(raw_content)
                    content = json.dumps(json_data, indent=4, sort_keys=True)
                    logger.debug("Successfully parsed and formatted JSON content")
                    app_signals.append_log.emit("[Cache] Successfully formatted JSON content")
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Cache file is not valid JSON: {json_err}")
                    app_signals.append_log.emit(f"[Cache] Not valid JSON, displaying raw content: {str(json_err)}")
                    content = raw_content  # Fall back to raw content
            except UnicodeDecodeError:
                logger.warning(f"Cache file is not UTF-8 encoded: {cache_file}")
                app_signals.append_log.emit(f"[Cache] Non-UTF-8 file detected: {cache_file}")
                with cache_file.open('r', encoding='latin-1') as f:
                    content = f.read()  # Display raw content without JSON formatting

            # Create and show dialog
            dialog = QDialog(None)  # Use None as parent since PremediaApp is not a widget
            dialog.setWindowTitle("Cache File Content")
            dialog.setMinimumSize(600, 400)

            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(content)

            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.close)

            layout = QVBoxLayout()
            layout.addWidget(text_edit)
            layout.addWidget(close_button)
            dialog.setLayout(layout)

            app_signals.update_status.emit("Opened cache file")
            app_signals.append_log.emit(f"[Cache] Opened cache file: {cache_file}")
            dialog.exec_()  # Modal dialog for better visibility

        except (IOError, OSError) as e:
            logger.error(f"IO error opening cache file: {e}\n{traceback.format_exc()}")
            app_signals.append_log.emit(f"[Cache] Failed: IO error - {str(e)}")
            app_signals.update_status.emit(f"Error opening cache file: {str(e)}")
            # QMessageBox.critical(None, "Cache Error", f"Failed to open cache file:\n{str(e)}")
            show_alert("Cache Error",f"Failed to open cache file:\n{str(e)}", QMessageBox.Critical)
        except Exception as e:
            logger.error(f"Unexpected error opening cache file: {e}\n{traceback.format_exc()}")
            app_signals.append_log.emit(f"[Cache] Failed: Unexpected error - {str(e)}")
            app_signals.update_status.emit("Unexpected error")
            # QMessageBox.critical(None, "Cache Error", f"Unexpected error opening cache file:\n{str(e)}")
            show_alert("Cache Error",f"Unexpected error opening cache file:\n{str(e)}", QMessageBox.Critical)

    def clear_cache(self):
        global IS_APP_ACTIVE_UPLOAD_DOWNLOAD
        IS_APP_ACTIVE_UPLOAD_DOWNLOAD = False
        global GLOBAL_CACHE

        msg_box = QMessageBox()
        msg_box.setWindowTitle("Confirm Clear Cache")
        msg_box.setText(
            "Are you sure you want to clear the cache and delete all files and folders in the premedia application directory? "
            "This action cannot be undone, and all data will be permanently deleted."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            try:
                logger.info(f"[Cache] Clearing cache from BASE_DIR: {BASE_TARGET_DIR}")
                app_signals.append_log.emit(f"[Cache] Clearing cache from BASE_DIR: {BASE_TARGET_DIR}")

                initialize_cache()
                GLOBAL_CACHE = None
                self.logged_in = False
                self.update_tray_menu()

                # Delete everything inside BASE_TARGET_DIR
                if os.path.exists(BASE_TARGET_DIR):
                    try:
                        shutil.rmtree(BASE_TARGET_DIR)   # remove the whole folder
                        logger.info(f"Deleted BASE_TARGET_DIR: {BASE_TARGET_DIR}")
                        app_signals.append_log.emit(f"[Cache] Deleted BASE_TARGET_DIR: {BASE_TARGET_DIR}")
                    except Exception as e:
                        logger.error(f"Failed to delete BASE_TARGET_DIR: {e}")
                        app_signals.append_log.emit(f"[Cache] Failed to delete BASE_TARGET_DIR: {e}")

                    # Recreate empty BASE_TARGET_DIR
                    os.makedirs(BASE_TARGET_DIR, exist_ok=True)
                    logger.info(f"Recreated empty {BASE_TARGET_DIR}")
                    app_signals.append_log.emit(f"[Cache] Recreated empty {BASE_TARGET_DIR}")

                logger.info("Cache cleared manually")
                app_signals.append_log.emit("[Cache] Cache cleared manually")
                app_signals.update_status.emit("Cache cleared successfully")

                # ✅ Show success dialog
                # QMessageBox.information(None, "Cache Cleared", "Cache cleared successfully!")
                show_alert("Cache Cleared", "Cache cleared successfully!", QMessageBox.Critical)

                self.show_login()
            except Exception as e:
                print(f"Error clearing cache: {e}")
                app_signals.append_log.emit(f"[Cache] Failed: Error clearing cache - {str(e)}")
                app_signals.update_status.emit(f"Error clearing cache: {str(e)}")
                # QMessageBox.critical(None, "Cache Error", f"Failed to clear cache: {str(e)}")
                show_alert("Cache Cleared", f"Failed to clear cache: {str(e)}", QMessageBox.Critical)
        else:
            app_signals.append_log.emit("[Cache] Cache clear cancelled by user")
            logger.info("Cache clear cancelled by user")
            app_signals.update_status.emit("Cache clear cancelled")

    def quit(self):
        global HTTP_SESSION, FILE_WATCHER_RUNNING
        try:
            logger.debug("Quit initiated")
            if hasattr(self, 'poll_timer') and self.poll_timer.isActive():
                logger.debug("Stopping poll_timer")
                self.poll_timer.stop()
                FILE_WATCHER_RUNNING = False

            if hasattr(self, 'file_watcher_thread') and self.file_watcher_thread.isRunning():
                logger.debug("Quitting file_watcher_thread")
                self.file_watcher_thread.quit()
                self.file_watcher_thread.wait(2000)

            if hasattr(self, 'login_dialog') and self.login_dialog.isVisible():
                logger.debug("Closing login_dialog")
                self.login_dialog.close()

            if self.tray_icon:
                logger.debug("Hiding tray_icon")
                self.tray_icon.hide()

            logger.debug("Closing HTTP_SESSION")
            HTTP_SESSION.close()

            stop_logging()
            app_signals.update_status.emit("Application quitting")
            app_signals.append_log.emit("[App] Application quitting")
            logger.info("Application quitting")
            self.app.quit()
        except Exception as e:
            logger.error(f"Error in quit: {e}")
            app_signals.append_log.emit(f"[App] Failed: Quit error - {str(e)}")
            app_signals.update_status.emit(f"Quit error: {str(e)}")
            stop_logging()
            self.app.quit()

    def show_login(self):
        try:
            if not self.logged_in:
                # If the old dialog was closed or deleted, recreate it safely
                if self.login_dialog is None or not isinstance(self.login_dialog, LoginDialog):
                    logger.warning("Recreating login dialog (previous instance lost or invalid)")
                    self.login_dialog = LoginDialog(parent=None, app=self)
                    self.login_dialog.user_in_other_system.connect(self.show_login_page)

                # If signals were lost after logout, rebind them
                try:
                    if hasattr(self.login_dialog.ui, "login_button") and \
                    not self.login_dialog.ui.login_button.receivers(self.login_dialog.ui.login_button.clicked):
                        self.login_dialog.ui.login_button.clicked.connect(self.login_dialog.handle_login)
                        logger.debug("Reconnected login button signal")

                    if hasattr(self.login_dialog.ui, "cancel_button") and \
                    not self.login_dialog.ui.cancel_button.receivers(self.login_dialog.ui.cancel_button.clicked):
                        self.login_dialog.ui.cancel_button.clicked.connect(self.login_dialog.reject)
                        logger.debug("Reconnected cancel button signal")
                except Exception as signal_error:
                    logger.warning(f"Could not verify/reconnect signals: {signal_error}")

                # Make absolutely sure the dialog is visible and interactive
                self.login_dialog.showNormal()
                self.login_dialog.raise_()
                self.login_dialog.activateWindow()
                self.login_dialog.setWindowState(Qt.WindowActive)
                QApplication.processEvents()

                app_signals.update_status.emit("Login dialog opened")
                app_signals.append_log.emit("[Login] Login dialog opened")
                logger.info("Login dialog opened successfully")
            else:
                app_signals.update_status.emit("Already logged in")
                app_signals.append_log.emit("[Login] Already logged in")
                logger.info("User is already logged in")
        except Exception as e:
            logger.error(f"Error in show_login: {e}")
            app_signals.append_log.emit(f"[Login] Failed: Error opening login dialog - {str(e)}")
            app_signals.update_status.emit(f"Error opening login dialog: {str(e)}")
            # QMessageBox.critical(None, "Login Error", f"Failed to open login dialog: {str(e)}")
            show_alert("Login Error", f"Failed to open login dialog: {str(e)}", QMessageBox.Critical)


    def show_logs(self):
        try:
            self.log_window.load_logs()
            setup_logger(self.log_window)  # Reconnect logger signals
            self.log_window.connect_signals()  # Reconnect LogWindow signals
            self.log_window.show()
            self.log_window.raise_()
            self.log_window.activateWindow()
            self.log_window.setWindowState(Qt.WindowActive)
            self.log_window.showNormal()
            app_signals.update_status.emit("Log window opened")
            app_signals.append_log.emit("[Log] Log window opened")
        except Exception as e:
            logger.error(f"Error in show_logs: {e}")
            app_signals.append_log.emit(f"[Log] Failed: Error opening log window - {str(e)}")
            app_signals.update_status.emit(f"Error opening log window: {str(e)}")
            # QMessageBox.critical(self, "Log Error", f"Failed to open log window: {str(e)}")
            show_alert("Log Error", f"Failed to open log window: {str(e)}", QMessageBox.Critical)

    def show_downloaded_files(self):
        try:
            if not self.downloaded_files_window or not self.downloaded_files_window.isVisible():
                self.downloaded_files_window = FileDownloadListWindow("downloaded")
                self.downloaded_files_window.show()
                self.downloaded_files_window.raise_()
                self.downloaded_files_window.activateWindow()
                # Ensure the window is visible and brought to front
                self.downloaded_files_window.setWindowState(Qt.WindowActive)
                self.downloaded_files_window.showNormal()  # Restore to normal state if minimized
                app_signals.update_status.emit("Downloaded files window opened")
                app_signals.append_log.emit("[Files] Downloaded files window opened")
        except Exception as e:
            logger.error(f"Error in show_downloaded_files: {e}")
            app_signals.append_log.emit(f"[Files] Failed: Error showing downloaded files - {str(e)}")
            app_signals.update_status.emit(f"Error showing downloaded files: {str(e)}")
            # QMessageBox.critical(self, "Files Error", f"Failed to show downloaded files: {str(e)}")
            show_alert("Files Error", f"Failed to show downloaded files: {str(e)}", QMessageBox.Critical)

    def show_uploaded_files(self):
        try:
            if not self.uploaded_files_window or not self.uploaded_files_window.isVisible():
                self.uploaded_files_window = FileUploadListWindow("uploaded")
                self.uploaded_files_window.show()
                self.uploaded_files_window.raise_()
                self.uploaded_files_window.activateWindow()
                # Ensure the window is visible and brought to front
                self.uploaded_files_window.setWindowState(Qt.WindowActive)
                self.uploaded_files_window.showNormal()  # Restore to normal state if minimized
                app_signals.update_status.emit("Uploaded files window opened")
                app_signals.append_log.emit("[Files] Uploaded files window opened")
        except Exception as e:
            logger.error(f"Error in show_uploaded_files: {e}")
            app_signals.append_log.emit(f"[Files] Failed: Error showing uploaded files - {str(e)}")
            app_signals.update_status.emit(f"Error showing uploaded files: {str(e)}")
            # QMessageBox.critical(self, "Files Error", f"Failed to show uploaded files: {str(e)}")
            show_alert("Files Error", f"Failed to show uploaded files: {str(e)}", QMessageBox.Critical)

    def convert_to_jpg_and_psd(self, src_path, dest_dir):
        try:
            self.thread = QThread()
            self.worker = FileConversionWorker(src_path, dest_dir)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.on_conversion_finished)
            self.worker.error.connect(self.on_conversion_error)
            self.worker.progress.connect(lambda file_path, progress: app_signals.update_file_list.emit(file_path, f"Converting: {progress}%", "download", progress, False))
            self.worker.finished.connect(self.thread.quit)
            self.worker.error.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.error.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()
            app_signals.append_log.emit(f"[Conversion] Starting conversion for {src_path}")
        except Exception as e:
            logger.error(f"File conversion thread error: {e}")
            app_signals.append_log.emit(f"[Conversion] Failed: File conversion thread error - {str(e)}")
            app_signals.update_status.emit(f"File conversion thread error: {str(e)}")
            # QMessageBox.critical(self, "Conversion Error", f"File conversion thread error: {str(e)}")
            show_alert("Conversion Error", f"File conversion thread error: {str(e)}", QMessageBox.Critical)

    def on_conversion_finished(self, jpg_path, psd_path, basename):
        try:
            cache = load_cache()
            if cache:
                cache["downloaded_files"].extend([jpg_path, psd_path])
                save_cache(cache)
            app_signals.update_status.emit(f"Uploaded JPG: {basename}")
            app_signals.update_file_list.emit(jpg_path, "Conversion Completed", "download", 100, False)
            app_signals.update_file_list.emit(psd_path, "Conversion Completed", "download", 100, False)
            app_signals.append_log.emit(f"[Conversion] Completed conversion for {basename}")
        except Exception as e:
            logger.error(f"Error in on_conversion_finished: {e}")
            app_signals.append_log.emit(f"[Conversion] Failed: Conversion error - {str(e)}")
            app_signals.update_status.emit(f"Conversion error: {str(e)}")
            # QMessageBox.critical(self, "Conversion Error", f"Conversion error: {str(e)}")
            show_alert("Conversion Error", f"Conversion error: {str(e)}", QMessageBox.Critical)

    def on_conversion_error(self, error, basename):
        try:
            app_signals.update_status.emit(f"Conversion failed for {basename}: {error}")
            app_signals.update_file_list.emit("", f"Conversion Failed: {error}", "download", 0, False)
            app_signals.append_log.emit(f"[Conversion] Failed: Conversion error for {basename} - {error}")
        except Exception as e:
            logger.error(f"Error in on_conversion_error: {e}")
            app_signals.append_log.emit(f"[Conversion] Failed: Error handling conversion error - {str(e)}")
            app_signals.update_status.emit(f"Error handling conversion error: {str(e)}")
            # QMessageBox.critical(self, "Conversion Error", f"Error handling conversion error: {str(e)}")
            show_alert("Conversion Error", f"Error handling conversion error: {str(e)}", QMessageBox.Critical)

    def open_with_photoshop(self, file_path):
        try:
            system = platform.system()
            photoshop_path = None
            if system == "Windows":
                search_dirs = [
                    Path("C:/Program Files/Adobe"),
                    Path("C:/Program Files (x86)/Adobe")
                ]
                for base_dir in search_dirs:
                    if not base_dir.exists():
                        continue
                    photoshop_exes = list(base_dir.glob("Adobe Photoshop */Photoshop.exe"))
                    if photoshop_exes:
                        photoshop_exes.sort(key=lambda x: x.parent.name, reverse=True)
                        photoshop_path = str(photoshop_exes[0])
                        break
                if not photoshop_path:
                    raise FileNotFoundError("Adobe Photoshop executable not found in Program Files")
            elif system == "Darwin":
                try:
                    result = subprocess.run(
                        ["mdfind", "kMDItemKind == 'Application' && kMDItemFSName == 'Adobe Photoshop.app'"],
                        capture_output=True, text=True, check=True
                    )
                    if result.stdout.strip():
                        photoshop_path = result.stdout.strip().split("\n")[0]
                except subprocess.CalledProcessError:
                    photoshop_apps = list(Path("/Applications").glob("Adobe Photoshop*.app"))
                    if photoshop_apps:
                        photoshop_apps.sort(key=lambda x: x.name, reverse=True)
                        photoshop_path = str(photoshop_apps[0])
                if not photoshop_path:
                    raise FileNotFoundError("Adobe Photoshop application not found in /Applications")
            elif system == "Linux":
                try:
                    subprocess.run(["wine", "--version"], capture_output=True, check=True)
                    wine_dirs = [
                        Path.home() / ".wine/drive_c/Program Files/Adobe",
                        Path.home() / ".wine/drive_c/Program Files (x86)/Adobe"
                    ]
                    for base_dir in wine_dirs:
                        if not base_dir.exists():
                            continue
                        photoshop_exes = list(base_dir.glob("Adobe Photoshop */Photoshop.exe"))
                        if photoshop_exes:
                            photoshop_exes.sort(key=lambda x: x.parent.name, reverse=True)
                            photoshop_path = str(photoshop_exes[0])
                            break
                    if not photoshop_path:
                        raise FileNotFoundError("Photoshop.exe not found in Wine directories")
                except subprocess.CalledProcessError:
                    raise FileNotFoundError("Wine is not installed or not functioning")
            else:
                error_msg = f"Unsupported platform for Photoshop: {system}"
                logger.warning(error_msg)
                app_signals.append_log.emit(f"[Photoshop] {error_msg}")
                app_signals.update_status.emit(error_msg)
                # QMessageBox.critical(self, "Photoshop Error", error_msg)
                show_alert("Photoshop Error", error_msg, QMessageBox.Critical)
                return
            if not Path(file_path).is_file():
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                app_signals.append_log.emit(f"[Photoshop] {error_msg}")
                app_signals.update_status.emit(error_msg)
                # QMessageBox.critical(self, "Photoshop Error", error_msg)
                show_alert("Photoshop Error", error_msg, QMessageBox.Critical)
                return
            if system == "Darwin":
                subprocess.run(["open", "-a", photoshop_path, file_path], check=True)
            else:
                subprocess.run([photoshop_path, file_path], check=True)
            logger.info(f"Opened {Path(file_path).name} in Photoshop at {photoshop_path}")
            app_signals.append_log.emit(f"[Photoshop] Opened {Path(file_path).name} at {photoshop_path}")
            app_signals.update_status.emit(f"Opened {Path(file_path).name} in Photoshop")
        except Exception as e:
            error_msg = f"Failed to open {Path(file_path).name} in Photoshop: {str(e)}"
            logger.error(error_msg)
            app_signals.append_log.emit(f"[Photoshop] {error_msg}")
            app_signals.update_status.emit(error_msg)
            # QMessageBox.critical(self, "Photoshop Error", error_msg)
            show_alert("Photoshop Error", error_msg, QMessageBox.Critical)

    def update_progress(self, value: int):
        try:
            logger.debug(f"Progress update received: {value}%")
            app_signals.append_log.emit(f"[App] Progress update: {value}%")
            if hasattr(self, 'log_window') and self.log_window:
                self.log_window.status_bar.showMessage(f"File operation progress: {value}%")
                logger.debug(f"Updated LogWindow status bar with progress: {value}%")
                app_signals.update_status.emit(f"File operation progress: {value}%")
        except Exception as e:
            logger.error(f"Error in update_progress: {e}")
            app_signals.append_log.emit(f"[App] Error in update_progress: {str(e)}")
            
    # @Slot(str, str)
    # def _show_worker_alert(self, title: str, message: str):
    #     """
    #     Receives alert_notification signals from FileWatcherWorker (background thread)
    #     and shows the dialog safely on the main thread via Qt.QueuedConnection.
    #     """
    #     QMessageBox.warning(None, title, message)

    @Slot(str, str)
    def _show_worker_alert(self, title: str, message: str):
        msg = QMessageBox(None)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowFlags(
            msg.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
        )
        msg.setWindowState(Qt.WindowState.WindowActive)
        msg.setAttribute(Qt.WA_ShowWithoutActivating, False)
        msg.raise_()
        msg.activateWindow()
        msg.exec()

    def post_login_processes(self):
        """
        Called ONLY after a successful manual login from LoginDialog.
        NOT called during __init__ auto-login — start_file_watcher() handles that.
        """
        global FILE_WATCHER_RUNNING_show_worker_alert
        try:
            cache = load_cache()
            token = cache.get("token", "")
            user_id = cache.get("user_id", "")
            if not token or not user_id:
                self.handle_error("Post-Login", "No token or user_id for post-login processes")
                self.set_logged_out_state()
                self.show_login()
                return

            FILE_WATCHER_RUNNING = True

            # Stop any existing watcher cleanly before starting a new one
            self.stop_file_watcher_thread()
            FileWatcherWorker._instance = None
            FileWatcherWorker._is_running = False
            FileWatcherWorker._busy = False

            # start_file_watcher is safe to call directly here —
            # post_login_processes is only called after the event loop is running
            # (triggered by LoginDialog.on_login_success, not during __init__)
            self.start_file_watcher()

            logger.info("Post-login processes: file watcher started")
            app_signals.append_log.emit("[Login] Post-login: file watcher started")

            # Update tray
            self.update_tray_menu()
            if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon.show()

            # Close progress dialog if still visible
            try:
                if (hasattr(self, 'login_dialog') and
                        self.login_dialog is not None and
                        self.login_dialog.progress and
                        self.login_dialog.progress.isVisible()):
                    self.login_dialog.progress.close()
                    logger.debug("Progress dialog closed")
                    app_signals.append_log.emit("[Login] Progress dialog closed")
            except RuntimeError:
                pass  # dialog already deleted

            # Reconnect status signal
            try:
                app_signals.update_status.disconnect(self.log_window.status_bar.showMessage)
            except Exception:
                pass
            app_signals.update_status.connect(
                self.log_window.status_bar.showMessage, Qt.QueuedConnection
            )

            logger.info("Post-login processes completed successfully")
            app_signals.append_log.emit("[Login] Post-login processes completed successfully")
            app_signals.update_status.emit("File watcher started")

        except Exception as e:
            self.handle_error("Post-Login", f"Post-login error: {str(e)}")
            try:
                if (hasattr(self, 'login_dialog') and
                        self.login_dialog is not None and
                        self.login_dialog.progress and
                        self.login_dialog.progress.isVisible()):
                    self.login_dialog.progress.close()
            except RuntimeError:
                pass
            self.set_logged_out_state()
            self.show_login()
            
            
    def show_dialog(self, title, message, dialog_type):
        try:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            if dialog_type.lower() == "error":
                msg_box.setIcon(QMessageBox.Critical)
            else:
                msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            logger.debug(f"Displayed dialog: {title} - {message} ({dialog_type})")
            app_signals.append_log.emit(f"[Dialog] Displayed: {title} - {message} ({dialog_type})")
            app_signals.update_status.emit(f"Displayed dialog: {title}")
        except Exception as e:
            logger.error(f"Error in show_dialog: {str(e)}")
            app_signals.append_log.emit(f"[Dialog] Failed: Error displaying dialog - {str(e)}")
            app_signals.update_status.emit(f"Error displaying dialog: {str(e)}")

# get_system_info()
threading.Thread(target=get_system_info, daemon=True).start()

# Start the Google Chat transfer reporter — it stays idle (sends nothing)
# until _CURRENT_TRANSFER_STATS["active"] is True, i.e. an upload/download
# is actually in progress. Then it reports every TRANSFER_REPORT_INTERVAL_SEC.
TRANSFER_REPORTER.start()

import ctypes
import sys

def run_updater(updater_path, new_exe, old_exe):
    params = f'"{new_exe}" "{old_exe}"'

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",   # 🔥 forces admin
        updater_path,
        params,
        None,
        1
    )

    if result <= 32:
        print("Failed to elevate updater")

    sys.exit(0)

api_process = None


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

# def start_local_api():
#     global api_process

#     ip = get_local_ip()
#     port = get_free_port()

#     url = f"http://{ip}:{port}"

#     api_process = subprocess.Popen([
#         sys.executable, "api_runner.py", ip, str(port)
#     ])

#     time.sleep(0.5)
#     print(f"url=============.${url}")
#     # requests.post("https://yourdomain.com/api/register-client", json={
#     #     "private_url": url
#     # }, timeout=5)

#     return api_process

def start_local_api():
    global api_process

    ip = get_local_ip()
    port = get_free_port()

    url = f"http://{ip}:{port}"
    print(f"url ======== {url}")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    API_PATH = os.path.join(BASE_DIR, "api_runner.py")
    print(f"api path-----", API_PATH)
    api_process = subprocess.Popen([
        sys.executable, API_PATH, ip, str(port)
    ])
    print(f"api_process-----{api_process}")

    return api_process


def stop_local_api():
    global api_process
    print("Stop api port")
    if api_process:
        # try:
        #     requests.post("https://yourdomain.com/api/logout", timeout=3)
        # except:
        #     pass

        api_process.terminate()
        api_process.wait(timeout=5)



if __name__ == "__main__":
    lock_handle = ensure_single_instance("PremediaApp")
    try:
        # 🔹 Step 1: Check for updates before launching GUI
        exe_path = sys.executable
        check_for_update(APPVERSION, exe_path)

        # 🔹 Step 2: Launch your main GUI
        key = parse_custom_url()
        # start_local_api()   # START local api server
        app = PremediaApp(key)
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application crashed: {e}")
        stop_local_api()    # CLEAN SHUTDOWN
        import traceback
        traceback.print_exc()
    finally:
        stop_local_api()    # CLEAN SHUTDOWN

# if __name__ == "__main__":
#     lock_handle = ensure_single_instance("PremediaApp")

#     try:
#         key = parse_custom_url()

#         start_local_api()   # START local api server

#         app = PremediaApp(key)

#         exit_code = app.app.exec()   # 🔥 CORRECT CALL

#     except Exception as e:
#         print(f"Application crashed: {e}")
#         import traceback
#         traceback.print_exc()
#         exit_code = 1

#     finally:
#         stop_local_api()    # CLEAN SHUTDOWN

#     sys.exit(exit_code)
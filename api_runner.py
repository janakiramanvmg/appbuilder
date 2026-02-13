import uvicorn
from fastapi import FastAPI
import sys
from fastapi.middleware.cors import CORSMiddleware

from PySide6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QProgressDialog, QTextEdit, QSystemTrayIcon,
    QMenu, QVBoxLayout, QStatusBar, QWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QProgressBar, QSizePolicy,QLabel, QFrame, QScrollArea, QGridLayout
)

from PySide6.QtGui import QIcon, QTextCursor, QAction, QCursor, QFont,QPixmap, QDesktopServices
from PySide6.QtCore import QRunnable, QThreadPool, QEvent, QSize, QThread, QTimer, Qt, QObject, Signal, QMetaObject, Slot, QLockFile, QDir, QEventLoop, QUrl, Q_ARG, QMimeData
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import QLineEdit
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/msg")
def health():
    return {"status": "running"}

def run_server(host, port):
    print(f"host====${host}--- prot===${port}")
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance()
    owns_app = False

    if app is None:
        app = QApplication(sys.argv)
        owns_app = True

    QMessageBox.warning(
        None,
        '',
        f"host= {host}:{port}",
    )
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    # host = sys.argv[1]
    host = "127.0.0.1"
    port = 5600

    print(f"[API] Starting on {host}:{port}", flush=True)
    run_server(host, port)

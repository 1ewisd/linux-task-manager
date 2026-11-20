"""Application entry point."""
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import __version__
from .ui.mainwindow import Main


def _single_instance():
    """Return a QLocalServer if we are the first instance, else poke the first one and exit."""
    sock = QLocalSocket()
    sock.connectToServer("taskmgr-single")
    if sock.waitForConnected(300):
        sock.write(b"raise")
        sock.waitForBytesWritten(300)
        sys.exit(0)
    QLocalServer.removeServer("taskmgr-single")
    server = QLocalServer()
    server.listen("taskmgr-single")
    return server


def _screenshots(app, win, out_dir, seconds):
    """Developer helper: let the graphs fill for `seconds`, then save a PNG of every tab."""
    def shot():
        apps = win.procs.cats["app"]                      # expand the biggest app group
        groups = [apps.child(i) for i in range(apps.childCount())]
        if groups:
            max(groups, key=lambda g: g.childCount()).setExpanded(True)
        for i, name in enumerate(("processes", "performance", "users", "details", "services")):
            win.tabs.setCurrentIndex(i)
            win.tick(force=True)
            QApplication.processEvents()
            win.grab().save(f"{out_dir}/{name}.png")
        app.quit()
    QTimer.singleShot(int(seconds * 1000), shot)


def main():
    if "--version" in sys.argv:
        print(f"taskmgr {__version__}")
        return
    app = QApplication(sys.argv)
    app.setApplicationName("Task Manager")
    app.setDesktopFileName("taskmgr")
    shots = sys.argv[sys.argv.index("--screenshots") + 1] if "--screenshots" in sys.argv else None
    server = None if shots else _single_instance()
    win = Main()
    if server:
        def bring_up():
            server.nextPendingConnection()
            win.setWindowState(win.windowState() & ~Qt.WindowMinimized)
            win.show()
            win.raise_()
            win.activateWindow()
        server.newConnection.connect(bring_up)
    win.show()
    if shots:
        _screenshots(app, win, shots, 45)
    sys.exit(app.exec())

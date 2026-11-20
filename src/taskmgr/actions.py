"""Process actions: signals, running tasks, context menus."""
import os
import shlex
import signal
import subprocess

from PySide6.QtWidgets import QApplication, QMenu, QMessageBox


def send_signal(parent, pids, sig):
    denied = []
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            denied.append(pid)
    if denied and QMessageBox.question(
            parent, "Access denied",
            f"You don't have permission to do that to {len(denied)} process(es).\n"
            "Try again with administrator privileges?") == QMessageBox.Yes:
        subprocess.Popen(["pkexec", "kill", f"-{int(sig)}", *map(str, denied)])


def run_task(parent, text):
    text = text.strip()
    if not text:
        return
    try:
        path = os.path.expanduser(text)
        argv = ["xdg-open", path] if os.path.exists(path) else shlex.split(text)
        subprocess.Popen(argv, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        QMessageBox.warning(parent, "Run new task", f"Cannot run '{text}':\n{e}")


def build_menu(parent, pids, row_info, goto=None):
    m = QMenu(parent)
    m.addAction("End task", lambda: send_signal(parent, pids, signal.SIGTERM))
    m.addAction("Force kill (SIGKILL)", lambda: send_signal(parent, pids, signal.SIGKILL))
    m.addSeparator()
    m.addAction("Suspend", lambda: send_signal(parent, pids, signal.SIGSTOP))
    m.addAction("Resume", lambda: send_signal(parent, pids, signal.SIGCONT))
    m.addSeparator()
    exe, cmd = row_info
    if exe:
        m.addAction("Open file location", lambda: subprocess.Popen(["xdg-open", os.path.dirname(exe)]))
    if cmd:
        m.addAction("Copy command line", lambda: QApplication.clipboard().setText(cmd))
    if goto:
        m.addAction("Go to details", goto)
    return m

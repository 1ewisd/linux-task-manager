"""The Task Manager main window."""
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import QInputDialog, QLabel, QMainWindow, QMessageBox, QTabWidget

from ..actions import run_task
from ..sampling import Sampler, SysSampler
from .details import DetailsTab
from .performance import PerfTab
from .processes import ProcessesTab
from .services import ServicesTab
from .users import UsersTab

ASSETS = Path(__file__).resolve().parent.parent / "assets"


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Manager")
        self.setWindowIcon(QIcon(str(ASSETS / "taskmgr.svg")))
        self.settings = QSettings("taskmgr", "taskmgr")
        self.show_kernel = self.settings.value("show_kernel", False, bool)
        self.sampler, self.syssampler = Sampler(), SysSampler()
        self.last_rows, self.last_sys, self.ticks = [], None, 0

        self.tabs = QTabWidget()
        self.procs = ProcessesTab(self)
        self.perf = PerfTab(bool(self.syssampler.gpu))
        self.users = UsersTab()
        self.details = DetailsTab(self)
        self.services = ServicesTab()
        for w, n in ((self.procs, "Processes"), (self.perf, "Performance"), (self.users, "Users"),
                     (self.details, "Details"), (self.services, "Services")):
            self.tabs.addTab(w, n)
        self.setCentralWidget(self.tabs)
        self.status = QLabel()
        self.statusBar().addWidget(self.status)
        self._menus()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.set_speed(int(self.settings.value("speed", 1000)))
        self.tabs.currentChanged.connect(lambda _: self.refresh_visible(force=True))
        self.resize(self.settings.value("size", None) or QSize(1000, 700))
        self.tabs.setCurrentIndex(int(self.settings.value("tab", 0)))
        self.tick()

    def _menus(self):
        mb = self.menuBar()
        f = mb.addMenu("&File")
        a = f.addAction("Run new task", self.run_new_task)
        a.setShortcut(QKeySequence("Ctrl+N"))
        f.addSeparator()
        f.addAction("Exit", self.close).setShortcut(QKeySequence("Ctrl+Q"))
        o = mb.addMenu("&Options")
        self.on_top = o.addAction("Always on top")
        self.on_top.setCheckable(True)
        self.on_top.toggled.connect(self.set_on_top)
        k = o.addAction("Show kernel threads")
        k.setCheckable(True)
        k.setChecked(self.show_kernel)
        k.toggled.connect(self._kernel)
        v = mb.addMenu("&View")
        v.addAction("Refresh now", lambda: self.tick(force=True)).setShortcut(QKeySequence("F5"))
        sp = v.addMenu("Update speed")
        grp = QActionGroup(self)
        self.speed_actions = {}
        for label, ms in (("High", 500), ("Normal", 1000), ("Low", 4000), ("Paused", 0)):
            act = sp.addAction(label)
            act.setCheckable(True)
            grp.addAction(act)
            act.triggered.connect(lambda _=False, ms=ms: self.set_speed(ms))
            self.speed_actions[ms] = act
        h = mb.addMenu("&Help")
        h.addAction("About", lambda: QMessageBox.about(
            self, "Task Manager", "Task Manager for Linux\nA Windows-style process and performance monitor."))

    def _kernel(self, on):
        self.show_kernel = on
        self.refresh_visible(force=True)

    def set_on_top(self, on):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    def set_speed(self, ms):
        self.speed = ms
        self.speed_actions.get(ms, self.speed_actions[1000]).setChecked(True)
        if ms:
            self.timer.start(ms)
        else:
            self.timer.stop()

    def run_new_task(self):
        text, ok = QInputDialog.getText(self, "Create new task",
                                        "Type the name of a program, folder or file to open:")
        if ok:
            run_task(self, text)

    def goto_details(self, pid):
        self.tabs.setCurrentWidget(self.details)
        self.details.select_pid(pid)

    def tick(self, force=False):
        self.last_rows = self.sampler.sample()
        self.last_sys = self.syssampler.sample()
        self.ticks += 1
        nthreads = sum(r["threads"] for r in self.last_rows)
        self.perf.update(self.last_sys, len(self.last_rows), nthreads, self.ticks)
        m = self.last_sys["mem"]
        self.status.setText(f'Processes: {len(self.last_rows)}      CPU usage: {self.last_sys["cpu"]:.0f}%'
                            f'      Memory: {m.percent:.0f}%')
        self.refresh_visible(force)

    def refresh_visible(self, force=False):
        if self.last_sys is None:
            return
        w = self.tabs.currentWidget()
        if w is self.services:
            if force or self.ticks % 5 == 1:
                self.services.refresh()
        elif w is not self.perf:
            w.update(self.last_rows, self.last_sys)

    def closeEvent(self, e):
        self.settings.setValue("size", self.size())
        self.settings.setValue("tab", self.tabs.currentIndex())
        self.settings.setValue("speed", self.speed)
        self.settings.setValue("show_kernel", self.show_kernel)
        super().closeEvent(e)

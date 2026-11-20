"""Services tab: systemd services with start / stop / restart."""
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QMenu, QTableWidget, QVBoxLayout, QWidget

from .common import SORT, NumItem


class ServicesTab(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 6, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "PID", "Status", "Description"])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        for c, w in enumerate((280, 70, 90)):
            self.table.setColumnWidth(c, w)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context)
        v.addWidget(self.table)

    def refresh(self):
        try:
            out = subprocess.run(["systemctl", "list-units", "--type=service", "--all", "--plain",
                                  "--no-legend", "--no-pager"], capture_output=True, text=True, timeout=5).stdout
            pids = {}
            show = subprocess.run(["systemctl", "show", "*.service", "-p", "Id", "-p", "MainPID"],
                                  capture_output=True, text=True, timeout=5).stdout
            cur = None
            for line in show.splitlines():
                if line.startswith("Id="):
                    cur = line[3:]
                elif line.startswith("MainPID=") and cur:
                    pids[cur] = int(line[8:] or 0)
        except Exception:
            return
        sel = {i.text() for i in self.table.selectedItems() if i.column() == 0}
        t = self.table
        t.setSortingEnabled(False)
        entries = []
        for line in out.splitlines():
            p = line.split(None, 4)
            if len(p) >= 4 and p[1] != "not-found":
                entries.append(p)
        t.setRowCount(len(entries))
        for i, p in enumerate(entries):
            unit, _load, active, sub = p[:4]
            desc = p[4] if len(p) > 4 else ""
            status = "Failed" if active == "failed" else ("Running" if sub == "running" else "Stopped")
            pid = pids.get(unit, 0)
            for c, (txt, key) in enumerate(((unit[:-8], unit.lower()), (str(pid) if pid else "", pid),
                                            (status, status), (desc, desc.lower()))):
                it = NumItem(txt)
                it.setData(SORT, key)
                if c == 1:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 2 and status == "Failed":
                    it.setForeground(QColor("#c42b1c"))
                t.setItem(i, c, it)
            if unit[:-8] in sel:
                t.selectRow(i)
        t.setSortingEnabled(True)

    def context(self, pos):
        row = self.table.itemAt(pos)
        if not row:
            return
        unit = self.table.item(row.row(), 0).text() + ".service"
        m = QMenu(self)
        for verb in ("start", "stop", "restart"):
            m.addAction(verb.title(), lambda v=verb: subprocess.Popen(["pkexec", "systemctl", v, unit]))
        m.exec(self.table.viewport().mapToGlobal(pos))

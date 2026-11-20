"""Users tab: per-user process totals."""
import collections
import os
import pwd

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QVBoxLayout, QWidget

from ..formatting import fmt_mem, fmt_pct
from .common import SORT, NumItem


class UsersTab(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 6, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setHorizontalHeaderLabels(["User", "Processes", "CPU", "Memory"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2, 3):
            hh.setSectionResizeMode(c, QHeaderView.Fixed)
            hh.resizeSection(c, 110)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(3, Qt.DescendingOrder)
        v.addWidget(self.table)
        self.me = pwd.getpwuid(os.getuid()).pw_name

    def update(self, rows, sysd):
        agg = collections.defaultdict(lambda: [0, 0.0, 0])
        for r in rows:
            a = agg[r["user"]]
            a[0] += 1
            a[1] += r["cpu"]
            a[2] += r["mem"]
        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(len(agg))
        for i, (u, (n, cpu, mem)) in enumerate(sorted(agg.items(), key=lambda kv: -kv[1][2])):
            cells = ((u + (" (me)" if u == self.me else ""), u.lower()), (str(n), n),
                     (fmt_pct(cpu), cpu), (fmt_mem(mem), mem))
            for c, (txt, key) in enumerate(cells):
                it = NumItem(txt)
                it.setData(SORT, key)
                if c:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setItem(i, c, it)
        t.setSortingEnabled(True)

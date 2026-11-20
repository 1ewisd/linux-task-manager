"""Processes tab: grouped Apps / Background tree with heat-mapped columns."""
import os
import shlex
import signal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit,
                               QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..actions import build_menu, send_signal
from ..apps import lookup_app
from ..formatting import fmt_mem, fmt_pct, fmt_rate
from .common import RANK, SORT


HEAT = [None, QColor("#fff4c4"), QColor("#ffe29a"), QColor("#ffc178"), QColor("#ff9a5c")]
CPU_STEPS, MEM_STEPS, DISK_STEPS = (0.5, 5, 15, 40), (150e6, 500e6, 1e9, 2e9), (0.05e6, 1e6, 10e6, 50e6)


def heat_level(v, steps):
    return sum(1 for s in steps if v >= s)


def app_icon(name):
    """Theme icon by name, a file path, or a generic gear for background processes."""
    if name and os.path.isabs(name):
        return QIcon(name)
    return QIcon.fromTheme(name or "applications-system", QIcon.fromTheme("application-x-executable"))


class TItem(QTreeWidgetItem):
    def __lt__(self, other):
        tree = self.treeWidget()
        asc = tree.header().sortIndicatorOrder() == Qt.AscendingOrder
        ra, rb = self.data(0, RANK), other.data(0, RANK)
        if ra is not None and rb is not None:     # category rows never swap places
            return ra < rb if asc else ra > rb
        col = tree.sortColumn()
        a, b = self.data(col, SORT), other.data(col, SORT)
        if a is None or b is None:
            a, b = self.text(col).lower(), other.text(col).lower()
        return a < b


class ProcessesTab(QWidget):
    HEADS = ["Name", "Status", "CPU", "Memory", "Disk"]

    def __init__(self, main):
        super().__init__()
        self.main = main
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit(placeholderText="Type a name or PID to search", clearButtonEnabled=True)
        self.search.setMaximumWidth(380)
        self.search.textChanged.connect(lambda _: main.refresh_visible())
        top.addWidget(self.search)
        top.addStretch()
        b1 = QPushButton("Run new task")
        b1.clicked.connect(main.run_new_task)
        self.end_btn = QPushButton("End task")
        self.end_btn.clicked.connect(self.end_task)
        top.addWidget(b1)
        top.addWidget(self.end_btn)
        v.addLayout(top)

        t = self.tree = QTreeWidget()
        t.setColumnCount(5)
        t.setHeaderLabels(self.HEADS)
        t.setRootIsDecorated(True)
        t.setUniformRowHeights(True)
        t.setSelectionMode(QAbstractItemView.ExtendedSelection)
        t.setContextMenuPolicy(Qt.CustomContextMenu)
        t.customContextMenuRequested.connect(self.context)
        t.itemSelectionChanged.connect(self._sel)
        h = t.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 5):
            h.setSectionResizeMode(c, QHeaderView.Fixed)
            h.resizeSection(c, 95)
            h.setDefaultAlignment(Qt.AlignRight | Qt.AlignBottom)
        h.setDefaultAlignment(Qt.AlignRight | Qt.AlignBottom)
        t.headerItem().setTextAlignment(0, Qt.AlignLeft | Qt.AlignBottom)
        t.headerItem().setTextAlignment(1, Qt.AlignLeft | Qt.AlignBottom)
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.AscendingOrder)
        v.addWidget(t)
        self.cats = {}
        for rank, label in enumerate(("Apps", "Background processes")):
            it = TItem(t, [label])
            it.setData(0, RANK, rank)
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
            it.setFlags(Qt.ItemIsEnabled)
            it.setExpanded(True)
            it.label = label
            self.cats["app" if rank == 0 else "bg"] = it
        self.items = {}
        self._sel()

    def _sel(self):
        self.end_btn.setEnabled(bool(self.selected_pids()))

    def selected_pids(self):
        pids = []
        for it in self.tree.selectedItems():
            pids += getattr(it, "pids", [])
        return pids

    def end_task(self):
        send_signal(self, self.selected_pids(), signal.SIGTERM)

    def context(self, pos):
        it = self.tree.itemAt(pos)
        if not it or not getattr(it, "pids", None):
            return
        if not it.isSelected():
            self.tree.clearSelection()
            it.setSelected(True)
        pids = self.selected_pids()
        r = it.rows[0]
        goto = (lambda: self.main.goto_details(pids[0])) if pids else None
        build_menu(self, pids, (r["exe"], " ".join(shlex.quote(a) for a in r["cmd"])), goto).exec(
            self.tree.viewport().mapToGlobal(pos))

    @staticmethod
    def fill(it, rows, label, icon=None):
        cpu = sum(r["cpu"] for r in rows)
        mem = sum(r["mem"] for r in rows)
        disk = sum(r["disk"] for r in rows)
        stopped = all(r["status"] == "stopped" for r in rows)
        status = "Suspended" if stopped else ("Zombie" if all(r["status"] == "zombie" for r in rows) else "")
        it.rows = rows
        it.pids = [r["pid"] for r in rows]
        it.setText(0, label)
        it.setData(0, SORT, label.lower())
        if icon:
            it.setIcon(0, icon)
        it.setText(1, status)
        for c, val, txt, steps in ((2, cpu, fmt_pct(cpu), CPU_STEPS), (3, mem, fmt_mem(mem), MEM_STEPS),
                                   (4, disk, fmt_rate(disk), DISK_STEPS)):
            it.setText(c, txt)
            it.setData(c, SORT, float(val))
            it.setTextAlignment(c, Qt.AlignRight | Qt.AlignVCenter)
            lvl = heat_level(val, steps)
            it.setData(c, Qt.BackgroundRole, HEAT[lvl])
            it.setData(c, Qt.ForegroundRole, QColor("black") if lvl else None)

    def update(self, rows, sysd):
        q = self.search.text().strip().lower()
        show_k = self.main.show_kernel
        groups = {}
        for r in rows:
            if r["kernel"] and not show_k:
                continue
            app = lookup_app(r)
            if q and q not in r["name"].lower() and q not in str(r["pid"]) and q not in " ".join(r["cmd"]).lower() \
                    and not (app and q in app[0].lower()):
                continue
            key = ("app", app[0]) if app else ("bg", r["name"])
            g = groups.setdefault(key, dict(label=key[1], icon=app[1] if app else "", rows=[]))
            g["rows"].append(r)

        t = self.tree
        t.setUpdatesEnabled(False)
        t.setSortingEnabled(False)
        for key, g in groups.items():
            cat = self.cats[key[0]]
            multi = len(g["rows"]) > 1
            it = self.items.get(key)
            if it is not None and it.multi != multi:
                cat.removeChild(it)
                it = None
            if it is None:
                it = self.items[key] = TItem()
                cat.addChild(it)
                it.multi, it.kids = multi, {}
                it.setIcon(0, app_icon(g["icon"]))
            self.fill(it, g["rows"], g["label"])
            if multi:
                live = set()
                for r in g["rows"]:
                    k = it.kids.get(r["pid"])
                    if k is None:
                        k = it.kids[r["pid"]] = TItem()
                        it.addChild(k)
                    self.fill(k, [r], f'{r["name"]} ({r["pid"]})')
                    live.add(r["pid"])
                for pid in [p for p in it.kids if p not in live]:
                    it.removeChild(it.kids.pop(pid))
        for key in [k for k in self.items if k not in groups]:
            it = self.items.pop(key)
            (it.parent() or t.invisibleRootItem()).removeChild(it)
        for kind, cat in self.cats.items():
            n = sum(1 for k in groups if k[0] == kind)
            cat.setText(0, f"{cat.label} ({n})")
        hi = t.headerItem()
        hi.setText(2, f'{sysd["cpu"]:.0f}%\nCPU')
        hi.setText(3, f'{sysd["mem"].percent:.0f}%\nMemory')
        hi.setText(4, f'{sysd["disk"]["active"]:.0f}%\nDisk')
        for c in (2, 3, 4):
            hi.setTextAlignment(c, Qt.AlignRight | Qt.AlignBottom)
        t.setSortingEnabled(True)
        t.setUpdatesEnabled(True)

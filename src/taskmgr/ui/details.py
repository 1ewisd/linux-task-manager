"""Details tab: flat sortable table of every process."""
import shlex

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QTableView, QVBoxLayout, QWidget

from ..actions import build_menu
from ..formatting import fmt_mem
from .common import SORT


class DetailsModel(QAbstractTableModel):
    COLS = ["Name", "PID", "Status", "User name", "CPU", "Memory", "Threads", "Command line"]

    def __init__(self):
        super().__init__()
        self.rows, self.pids = [], []

    def set_rows(self, rows):
        pids = [r["pid"] for r in rows]
        if pids == self.pids:
            self.rows = rows
            if rows:
                self.dataChanged.emit(self.index(0, 0), self.index(len(rows) - 1, len(self.COLS) - 1))
        else:
            self.beginResetModel()
            self.rows, self.pids = rows, pids
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLS)

    def headerData(self, s, o, role=Qt.DisplayRole):
        if o == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLS[s]

    def data(self, idx, role=Qt.DisplayRole):
        r, c = self.rows[idx.row()], idx.column()
        vals = [(r["name"], r["name"].lower()), (str(r["pid"]), r["pid"]),
                ("Suspended" if r["status"] == "stopped" else "Running" if r["status"] in ("running", "sleeping", "disk-sleep", "idle") else r["status"].title(), r["status"]),
                (r["user"], r["user"]), (f'{r["cpu"]:.1f}', r["cpu"]),
                (fmt_mem(r["mem"]), r["mem"]), (str(r["threads"]), r["threads"]),
                (" ".join(r["cmd"]), " ".join(r["cmd"]).lower())]
        if role == Qt.DisplayRole:
            return vals[c][0]
        if role == SORT:
            return vals[c][1]
        if role == Qt.TextAlignmentRole and c in (1, 4, 5, 6):
            return int(Qt.AlignRight | Qt.AlignVCenter)


class DetailsTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 6, 0, 0)
        self.model = DetailsModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(SORT)
        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(1, Qt.AscendingOrder)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(True)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.context)
        h = self.view.horizontalHeader()
        h.setStretchLastSection(True)
        for c, w in enumerate((200, 70, 90, 110, 70, 100, 70)):
            self.view.setColumnWidth(c, w)
        v.addWidget(self.view)

    def pids(self):
        return [self.proxy.data(i.sibling(i.row(), 1), SORT) for i in self.view.selectionModel().selectedRows()]

    def update(self, rows, sysd):
        rows = [r for r in rows if not r["kernel"] or self.main.show_kernel]
        keep = self.pids()
        self.model.set_rows(rows)
        if keep and self.model.pids and not self.view.selectionModel().hasSelection():
            for pid in keep:
                self.select_pid(pid, add=True)

    def select_pid(self, pid, add=False):
        if pid in self.model.pids:
            src = self.model.index(self.model.pids.index(pid), 0)
            idx = self.proxy.mapFromSource(src)
            sel = QAbstractItemView.SelectionFlag
            self.view.selectionModel().select(idx, sel.Select | sel.Rows if add else sel.ClearAndSelect | sel.Rows)
            if not add:
                self.view.scrollTo(idx)

    def context(self, pos):
        pids = self.pids()
        if not pids:
            return
        r = next((x for x in self.model.rows if x["pid"] == pids[0]), None)
        info = (r["exe"], " ".join(shlex.quote(a) for a in r["cmd"])) if r else ("", "")
        build_menu(self, pids, info).exec(self.view.viewport().mapToGlobal(pos))

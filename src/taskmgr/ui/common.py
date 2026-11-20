"""Shared Qt bits for the tabs."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

SORT = Qt.UserRole          # numeric / lowercase sort key stored per cell
RANK = Qt.UserRole + 1      # category rows (Apps / Background) keep a fixed order


class NumItem(QTableWidgetItem):
    def __lt__(self, other):
        a, b = self.data(SORT), other.data(SORT)
        return a < b if a is not None and b is not None else self.text() < other.text()

from PySide6.QtWidgets import QApplication

from taskmgr.ui.mainwindow import Main


def test_every_tab_renders():
    app = QApplication.instance() or QApplication([])
    win = Main()
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        win.tick(force=True)
        app.processEvents()
    assert win.procs.tree.topLevelItemCount() == 2   # Apps + Background
    assert win.details.model.rowCount() > 0

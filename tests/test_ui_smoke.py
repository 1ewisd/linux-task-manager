def test_every_tab_renders(window, qapp):
    for i in range(window.tabs.count()):
        window.tabs.setCurrentIndex(i)
        window.tick(force=True)
        qapp.processEvents()
    assert window.procs.tree.topLevelItemCount() == 2   # Apps + Background
    assert window.details.model.rowCount() > 0

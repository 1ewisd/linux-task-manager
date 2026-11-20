pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    Plasmoid.icon: "taskmgr"
    Plasmoid.status: PlasmaCore.Types.ActiveStatus
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: "Task Manager"
    toolTipSubText: "Processes, performance, users and services"
    toolTipTextFormat: Text.PlainText

    preferredRepresentation: compactRepresentation

    function openTaskmgr(): void {
        runner.connectSource("setsid -f \"$HOME/.local/bin/taskmgr\" >/dev/null 2>&1");
    }

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) { disconnectSource(source); }
    }

    // Never shown (clicking connects instead of expanding), but Plasma only
    // keeps a widget in a panel when it has a full representation.
    fullRepresentation: Item {
        implicitWidth: 1
        implicitHeight: 1
    }

    compactRepresentation: PlasmaComponents.ToolButton {
        implicitWidth: 22
        implicitHeight: 28
        Layout.minimumWidth: 22
        Layout.preferredWidth: 22
        Layout.maximumWidth: 22
        Layout.minimumHeight: 22
        padding: 0
        leftPadding: 0
        rightPadding: 0
        icon.name: "taskmgr"
        icon.width: 22
        icon.height: 22
        text: "Task Manager"
        display: PlasmaComponents.AbstractButton.IconOnly
        onClicked: root.openTaskmgr()
        Accessible.name: "Open Task Manager"
    }
}

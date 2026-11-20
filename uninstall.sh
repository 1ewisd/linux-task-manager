#!/usr/bin/env bash
# Remove Task Manager. Add --purge to also delete saved settings.
set -euo pipefail
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$DATA_HOME/taskmgr" \
       "$DATA_HOME/plasma/plasmoids/dev.taskmgr.panelicon"
rm -f  "$HOME/.local/bin/taskmgr" \
       "$DATA_HOME/applications/taskmgr.desktop" \
       "$DATA_HOME/icons/hicolor/scalable/apps/taskmgr.svg"
[ "${1:-}" = "--purge" ] && rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/taskmgr"
command -v update-desktop-database >/dev/null && update-desktop-database "$DATA_HOME/applications" 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
echo "Task Manager removed."

#!/usr/bin/env bash
# Save or restore GNOME / Pop Shell settings (they live in dconf, not files).
#   ./dconf.sh save     dump current settings into dconf/
#   ./dconf.sh load     apply dconf/ to this machine
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dconf"

# Format: <file name>:<dconf path>
paths=(
    "pop-shell:/org/gnome/shell/extensions/pop-shell/"
    "wm-keybindings:/org/gnome/desktop/wm/keybindings/"
    "wm-preferences:/org/gnome/desktop/wm/preferences/"
    "shell-keybindings:/org/gnome/shell/keybindings/"
    "mutter:/org/gnome/mutter/"
    "media-keys:/org/gnome/settings-daemon/plugins/media-keys/"
)

case "${1:-}" in
    save)
        mkdir -p "$DIR"
        for pair in "${paths[@]}"; do
            dconf dump "${pair#*:}" > "$DIR/${pair%%:*}.ini"
            echo "saved  ${pair#*:} -> dconf/${pair%%:*}.ini"
        done
        ;;
    load)
        for pair in "${paths[@]}"; do
            f="$DIR/${pair%%:*}.ini"
            [ -f "$f" ] || { echo "skip   $f (missing)"; continue; }
            dconf load "${pair#*:}" < "$f"
            echo "loaded dconf/${pair%%:*}.ini -> ${pair#*:}"
        done
        ;;
    *)
        echo "usage: $0 save|load" >&2
        exit 1
        ;;
esac

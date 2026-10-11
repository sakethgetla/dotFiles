#!/usr/bin/env bash
# Build and install Pop Shell (GNOME tiling extension), then restore settings.
# Run ../../link.sh afterwards to link config.json and the autostart override.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HOME/src/pop-shell"
BRANCH="master_noble"   # GNOME 46+

sudo apt install -y git make node-typescript

if [ -d "$SRC/.git" ]; then
    git -C "$SRC" pull --ff-only
else
    git clone -b "$BRANCH" https://github.com/pop-os/shell.git "$SRC"
fi

make -C "$SRC" local-install

"$DIR/dconf.sh" load

gnome-extensions enable pop-shell@system76.com 2>/dev/null \
    || echo "Log out and back in, then run: gnome-extensions enable pop-shell@system76.com"

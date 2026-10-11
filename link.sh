#!/usr/bin/env bash
# Symlink dotfiles into their target locations.
# Safe: skips real files, replaces existing symlinks.
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Format: <source relative to DOTFILES>:<absolute target>
links=(
    "windowManagers/i3:$HOME/.config/i3"
    "terminalEmulators/kitty:$HOME/.config/kitty"
    "editors/nvim:$HOME/.config/nvim"
    "rofi:$HOME/.config/rofi"
    "windowManagers/popShell/pop-shell:$HOME/.config/pop-shell"
    "windowManagers/popShell/autostart/org.kde.xwaylandvideobridge.desktop:$HOME/.config/autostart/org.kde.xwaylandvideobridge.desktop"
    # add more: "shell/zsh:$HOME/.zshrc"
)

for pair in "${links[@]}"; do
    src="$DOTFILES/${pair%%:*}"
    dst="${pair##*:}"

    if [ ! -e "$src" ]; then
        echo "skip   $dst  (source missing: $src)"
        continue
    fi

    mkdir -p "$(dirname "$dst")"

    if [ -L "$dst" ]; then
        ln -sfn "$src" "$dst"
        echo "relink $dst -> $src"
    elif [ -e "$dst" ]; then
        echo "skip   $dst  (exists, not a symlink)"
    else
        ln -s "$src" "$dst"
        echo "link   $dst -> $src"
    fi
done

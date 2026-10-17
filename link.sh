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

# System files owned by root; linked with sudo. Skipped if the target's directory doesn't exist.
# Format: <source relative to DOTFILES>:<absolute target>
system_links=(
    "keyboardLayouts/keyd/default.conf:/etc/keyd/default.conf"
)

# link <src> <dst> [sudo]
link() {
    local src="$1" dst="$2" run="${3:-}"

    if [ ! -e "$src" ]; then
        echo "skip   $dst  (source missing: $src)"
        return
    fi

    $run mkdir -p "$(dirname "$dst")"

    if [ -L "$dst" ]; then
        $run ln -sfn "$src" "$dst"
        echo "relink $dst -> $src"
    elif [ -e "$dst" ]; then
        echo "skip   $dst  (exists, not a symlink)"
    else
        $run ln -s "$src" "$dst"
        echo "link   $dst -> $src"
    fi
}

for pair in "${links[@]}"; do
    link "$DOTFILES/${pair%%:*}" "${pair##*:}"
done

for pair in "${system_links[@]}"; do
    dst="${pair##*:}"
    if [ ! -d "$(dirname "$dst")" ]; then
        echo "skip   $dst  (not installed)"
        continue
    fi
    link "$DOTFILES/${pair%%:*}" "$dst" sudo
done

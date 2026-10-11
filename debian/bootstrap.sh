#!/usr/bin/env bash
# Install all packages listed in packages.txt
set -euo pipefail

cd "$(dirname "$0")"

packages=$(grep -vE '^\s*(#|$)' packages.txt | tr '\n' ' ')

echo "Installing: $packages"
sudo apt update
sudo apt install -y $packages

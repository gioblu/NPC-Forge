#!/bin/bash

# TERMy Installer
#
# NOTE: source files (scripts/, dataset/, config.json, the `termy` client)
# are already installed by the top-level ../../setup.sh, which copies or
# symlinks the whole npcs/ tree in one shot. This script only wires up the
# `termy` CLI entry point on top of that:
#   1. a termy.py symlink (Python needs the .py extension to import it)
#   2. a ~/.local/bin/termy executable wrapper

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RESET='\033[0m'

FORGE_DIR="$HOME/.local/share/npc-forge"
BIN_DIR="$HOME/.local/bin"
TERMY_DIR="$FORGE_DIR/npcs/termy"
INSTALL_MAIN_BIN="$BIN_DIR/termy"

TERMY_USER_DATA_DIR="$HOME/.local/share/termy"
TERMY_USER_CONFIG="$TERMY_USER_DATA_DIR/config.json"

if [ "$EUID" -eq 0 ]; then
  echo -e "${YELLOW}[TERMy]${RESET} ⛔ Error: Do not run as root."
  exit 1
fi

if [ "${1:-}" == "--uninstall" ]; then
    echo -e "${RED}[TERMy] Removing TERMy CLI entry point...${RESET}"
    rm -f "$INSTALL_MAIN_BIN"
    # Only ever unlink this one file we created. Never rm -rf a directory
    # here: $TERMY_DIR may be reached through a symlinked npcs/ (dev mode),
    # and the main ./setup.sh --uninstall already owns removing $FORGE_DIR.
    rm -f "$TERMY_DIR/termy.py"
    hash -r
    echo -e "${GREEN}[TERMy] Done.${RESET} (Run ../../setup.sh --uninstall to remove all NPC-Forge data.)"
    exit 0
fi

if [ ! -d "$TERMY_DIR" ]; then
    echo -e "${RED}[TERMy] ⛔ $TERMY_DIR not found — run the top-level ./setup.sh first.${RESET}"
    exit 1
fi

echo -e "${YELLOW}[TERMy]${RESET} Checking for espeak-ng dependency..."
if ! command -v espeak-ng >/dev/null 2>&1; then
    echo -e "${YELLOW}[TERMy] ${GREEN}espeak-ng${RESET} not found. Attempting to install..."
    
    if command -v apt-get >/dev/null 2>&1; then
        echo -e "${YELLOW}[TERMy] ${RESET}Debian/Ubuntu detected. Running: sudo apt update && sudo apt install -y espeak-ng${RESET}\n"
        sudo apt-get update && sudo apt-get install -y espeak-ng
        echo -e ""
    elif command -v dnf >/dev/null 2>&1; then
        echo -e "${YELLOW}[TERMy] ${RESET}Fedora/RHEL detected. Running: sudo dnf install -y espeak-ng${RESET}\n"
        sudo dnf install -y espeak-ng
        echo -e ""
    elif command -v pacman >/dev/null 2>&1; then
        echo -e "${YELLOW}[TERMy] ${RESET}Arch Linux detected. Running: sudo pacman -S --noconfirm espeak-ng${RESET}\n"
        sudo pacman -S --noconfirm espeak-ng
        echo -e ""
    elif command -v brew >/dev/null 2>&1; then
        echo -e "${YELLOW}[TERMy] ${RESET}macOS (Homebrew) detected. Running: brew install espeak-ng${RESET}\n"
        brew install espeak-ng
        echo -e ""
    else
        echo -e "${RED}⛔ Could not detect package manager. Please install espeak-ng manually.${RESET}\n"
    fi
else
    echo -e "${YELLOW}[TERMy] ${GREEN}espeak-ng ${RESET}is already installed."
fi

echo -e "${YELLOW}[TERMy]${RESET} Linking termy.py entry point..."
ln -sfn "$TERMY_DIR/termy" "$TERMY_DIR/termy.py"

echo -e "${YELLOW}[TERMy]${RESET} Generating termy CLI wrapper..."
mkdir -p "$BIN_DIR"
cat << EOF > "$INSTALL_MAIN_BIN"
#!$FORGE_DIR/venv/bin/python3
import sys
sys.path.insert(0, "$FORGE_DIR")
sys.path.insert(0, "$TERMY_DIR")
import termy
if __name__ == "__main__":
    sys.exit(termy.run_cli())
EOF
chmod +x "$INSTALL_MAIN_BIN"

echo -e "${YELLOW}[TERMy]${RESET} Checking local configuration..."
mkdir -p "$TERMY_USER_DATA_DIR"

if [ ! -f "$TERMY_USER_CONFIG" ]; then
    echo -e "${YELLOW}[TERMy]${RESET} Initializing missing config.json..."
    cat << EOF > "$TERMY_USER_CONFIG"
{
  "termy_voice_mode": "off"
}
EOF
fi

hash -r
echo -e "${GREEN}[TERMy]${RESET} ${GREEN}termy${RESET} command successfully configured!"
echo -e "${GREEN}"
cat << 'BANNER'
 _____ ____  _____ __  __      
|_   _|  __|| ___ \  ||  |      
  | | | |__ | |_/ /      |_   _ 
  | | |  __||    /| |\/| | | | |
  | | | |__ | |\ \| |  | | |_| |
  |_| |____||_| \_\_|  |_|___  |
                           __| |
 Giovanni Blu Mitolo 2026 |____| 

A cynic, deterministic terminal assistant.
BANNER
echo -e "${RESET}"

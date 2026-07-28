#!/bin/bash
cd "$(dirname "$0")/.."

echo "========================================"
echo "  FM Save Copilot - First Time Setup"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed."
    echo
    echo "Please install Python from python.org/downloads"
    echo
    read -p "Press Enter to exit."
    exit 1
fi

echo "Setting up... this takes a minute."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo
echo "Setup complete!"
echo

read -p "Configure your club now? [Y/n]: " RUNWIZARD
if [[ ! "$RUNWIZARD" =~ ^[Nn]$ ]]; then
    python scripts/setup_wizard.py
fi

echo
echo "You're ready. Double-click run.command to generate a report."
read -p "Press Enter to close."

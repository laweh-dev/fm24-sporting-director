#!/bin/bash
cd "$(dirname "$0")/.."

# Check venv exists
if [ ! -f venv/bin/activate ]; then
    echo
    echo "ERROR: Setup has not been run yet."
    echo "Please double-click setup.command first."
    echo
    read -p "Press Enter to close."
    exit 1
fi

source venv/bin/activate

# Check config exists
if [ ! -f config/config.yaml ]; then
    echo
    echo "No config found. Have you run setup.command?"
    echo
    echo "1. Run setup.command first (installs dependencies + wizard)"
    echo "2. Or copy config/config.example.yaml → config/config.yaml"
    echo "   and fill in your settings."
    echo
    read -p "Press Enter to close."
    exit 1
fi

echo "Generating your Director of Football report..."
echo

python -m fm_copilot --open
if [ $? -ne 0 ]; then
    echo
    echo "Something went wrong. See the message above."
    echo
    echo "If you see 'squad file not found': export squad.html from FM24"
    echo "and save it to the data_uploads folder. See VIEW-SETUP.md."
    echo
    read -p "Press Enter to close."
    exit 1
fi

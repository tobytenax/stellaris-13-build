#!/bin/bash
cd "$(dirname "$0")"
echo "  Starting Stellaris-13..."
if command -v python3 &>/dev/null; then PYTHON=python3
elif command -v python &>/dev/null; then PYTHON=python
else
    echo "  Python not found. Install from https://python.org/downloads/"
    open "https://www.python.org/downloads/"
    read -p "  Press Enter to close..."
    exit 1
fi
if [ ! -f ".deps_installed" ]; then
    echo "  Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt --quiet 2>/dev/null || \
    $PYTHON -m pip install -r requirements.txt --quiet --break-system-packages 2>/dev/null
    touch .deps_installed
fi
(sleep 3 && open "http://localhost:13013") &
$PYTHON app.py

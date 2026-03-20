#!/usr/bin/env bash
# ════════════════════════════════════════════
#  Stellaris-13 — Launch Script
# ════════════════════════════════════════════

cd "$(dirname "$0")"

# Check dependencies
python3 -c "import flask" 2>/dev/null || {
    echo "  Installing dependencies..."
    pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt
}

python3 -c "import swisseph" 2>/dev/null || {
    echo "  Installing Swiss Ephemeris..."
    pip install pyswisseph --break-system-packages 2>/dev/null || pip install pyswisseph
}

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       ✦  S T E L L A R I S - 1 3  ✦      ║"
echo "  ║                                          ║"
echo "  ║  13-Sign Astronomical Ephemeris           ║"
echo "  ║  Dual-Method Chart Calculator             ║"
echo "  ║                                          ║"
echo "  ║  Open: http://localhost:13013             ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

python3 app.py

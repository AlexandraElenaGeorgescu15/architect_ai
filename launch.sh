#!/bin/bash
# Architect.AI Universal Launcher for Linux/Mac
# This script launches the Python launcher which handles the rest

echo ""
echo "============================================================"
echo "   🏗️ Architect.AI v2.0 - Production Dual-Mode System"
echo "============================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 not found"
    echo "   Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

# Launch the Python launcher
python3 launch.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application exited with an error"
    read -p "Press Enter to continue..."
fi


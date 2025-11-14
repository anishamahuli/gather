#!/bin/bash
# Script to activate the gather-1 virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

echo "Virtual environment activated!"
echo "Python: $(which python)"
echo ""
echo "To run the app: python -m src.main"
echo "To deactivate: deactivate"


#!/bin/bash
# Script to activate venv and run the gather-1 app

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the app
python -m src.main "$@"


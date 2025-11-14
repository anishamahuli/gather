#!/bin/bash
# Script to run the Streamlit UI

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Change to project root directory (important for imports)
cd "$SCRIPT_DIR"

# Run Streamlit
streamlit run src/ui.py


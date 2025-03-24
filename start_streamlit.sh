#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Streamlit
streamlit run src/app.py 
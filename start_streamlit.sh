#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")"

cd src/web/fullstreamlit

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Streamlit
python3 -m streamlit run app.py 
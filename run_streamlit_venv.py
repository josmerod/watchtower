#!/usr/bin/env python
"""
Simple script to run Streamlit from the virtual environment.
"""
import sys
import subprocess

if __name__ == "__main__":
    # Run streamlit with the app
    cmd = [sys.executable, "-m", "streamlit", "run", "src/web/fullstreamlit/app.py"]
    subprocess.run(cmd) 
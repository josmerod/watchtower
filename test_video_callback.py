#!/usr/bin/env python3
"""Test the video callback directly to see what's happening"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import dash
import dash_bootstrap_components as dbc

from src.web.dashboard.components.videos_tab import (
    register_video_callbacks,
    render_videos_tab,
)

# Create a simple test app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Simple layout with just the videos tab
app.layout = dbc.Container([render_videos_tab()], fluid=True)

# Register the callbacks
register_video_callbacks(app)

if __name__ == "__main__":
    print("Starting test app for video callbacks...")
    print("Go to http://localhost:8055 and test the filters")
    app.run_server(debug=True, port=8055)

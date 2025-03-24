#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")"

# Make all shell scripts executable
chmod +x *.sh

# Create LaunchAgents directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Load the services
launchctl load ~/Library/LaunchAgents/com.watchtower.streamlit.plist
launchctl load ~/Library/LaunchAgents/com.watchtower.etl.plist

echo "Services have been added to startup"
echo "You can check their status using:"
echo "  launchctl list | grep watchtower" 
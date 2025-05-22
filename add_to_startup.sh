#!/bin/bash

# Ensure script runs from project root
cd "$(dirname "$0")" || exit 1

# Set up permissions and directories
chmod +x *.sh
mkdir -p ~/Library/LaunchAgents

# Load Watchtower services
for service in com.watchtower.{streamlit,etl}.plist; do
    launchctl load ~/Library/LaunchAgents/"$service" 2>/dev/null || echo "Failed to load $service"
done

# Provide status feedback
echo "✅ Watchtower services added to startup"
echo "📊 Check status: launchctl list | grep watchtower"
#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")"

# Create the launchd plist file for ETL scheduler
cat > ~/Library/LaunchAgents/com.watchtower.etl.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.watchtower.etl</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(pwd)/run_all_etl.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardErrorPath</key>
    <string>$(pwd)/logs/etl.err</string>
    <key>StandardOutPath</key>
    <string>$(pwd)/logs/etl.out</string>
</dict>
</plist>
EOL

# Load the launchd service
launchctl load ~/Library/LaunchAgents/com.watchtower.etl.plist

echo "ETL scheduler has been set up to run daily at midnight"
echo "You can check the logs in the logs directory" 
#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")"

# Function to create the launchd plist file
create_plist() {
    cat > ~/Library/LaunchAgents/com.watchtower.streamlit.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.watchtower.streamlit</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which streamlit)</string>
        <string>run</string>
        <string>src/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$(echo $PATH)</string>
        <key>PYTHONPATH</key>
        <string>$(pwd)</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>$(pwd)/logs/streamlit.err</string>
    <key>StandardOutPath</key>
    <string>$(pwd)/logs/streamlit.out</string>
</dict>
</plist>
EOL
}

# Function to start the service
start_service() {
    launchctl load ~/Library/LaunchAgents/com.watchtower.streamlit.plist
    echo "Streamlit service started"
}

# Function to stop the service
stop_service() {
    launchctl unload ~/Library/LaunchAgents/com.watchtower.streamlit.plist
    echo "Streamlit service stopped"
}

# Function to restart the service
restart_service() {
    stop_service
    sleep 2
    start_service
}

# Function to check service status
check_status() {
    if launchctl list | grep -q "com.watchtower.streamlit"; then
        echo "Streamlit service is running"
    else
        echo "Streamlit service is not running"
    fi
}

# Main script logic
case "$1" in
    "install")
        create_plist
        echo "Service configuration created"
        ;;
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        check_status
        ;;
    *)
        echo "Usage: $0 {install|start|stop|restart|status}"
        exit 1
        ;;
esac 
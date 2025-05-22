#!/bin/bash

# Ensure script runs from project root and has proper permissions
cd "$(dirname "$0")" || exit 1
chmod +x "$0"

# Constants
PLIST_PATH="$HOME/Library/LaunchAgents/com.watchtower.streamlit.plist"
SERVICE_NAME="com.watchtower.streamlit"
LOG_DIR="logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to create the launchd plist file
create_plist() {
    local streamlit_path
    streamlit_path=$(which streamlit)
    
    if [[ -z "$streamlit_path" ]]; then
        echo "Error: streamlit not found in PATH"
        exit 1
    }

    cat > "$PLIST_PATH" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$streamlit_path</string>
        <string>run</string>
        <string>src/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$PATH</string>
        <key>PYTHONPATH</key>
        <string>$(pwd)</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>$(pwd)/$LOG_DIR/streamlit.err</string>
    <key>StandardOutPath</key>
    <string>$(pwd)/$LOG_DIR/streamlit.out</string>
</dict>
</plist>
EOL
}

# Function to manage service state
manage_service() {
    local action=$1
    local message=$2
    
    if launchctl "$action" "$PLIST_PATH" 2>/dev/null; then
        echo "✅ Streamlit service $message"
    else
        echo "❌ Failed to $message Streamlit service"
        return 1
    fi
}

# Function to start the service
start_service() {
    manage_service "load" "started"
}

# Function to stop the service
stop_service() {
    manage_service "unload" "stopped"
}

# Function to restart the service
restart_service() {
    stop_service && sleep 2 && start_service
}

# Function to check service status
check_status() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo "✅ Streamlit service is running"
        echo "📊 App available at: http://localhost:8501"
    else
        echo "❌ Streamlit service is not running"
    fi
}

# Main script logic
case "${1:-}" in
    "install")
        create_plist
        echo "✅ Service configuration created"
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
#!/bin/bash

#==============================================================================
# WATCHTOWER AUTOMATED DEPLOYMENT SCRIPT
#==============================================================================
# 
# Description: One-command deployment script for Watchtower ETL and Dashboard
# Platform: Ubuntu 24.04+ (tested)
# Usage: ./deploy.sh
# 
# This script performs complete automated setup:
# - Environment detection and validation
# - System dependencies installation
# - Python virtual environment setup
# - Application dependencies installation
# - Configuration file generation
# - ETL pipeline deployment
# - Streamlit dashboard deployment
# - Post-deployment validation
#
#==============================================================================

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Script Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"
readonly VENV_DIR="$PROJECT_ROOT/.venv"
readonly LOGS_DIR="$PROJECT_ROOT/logs"
readonly DATA_DIR="$PROJECT_ROOT/data"
readonly CONFIG_DIR="$PROJECT_ROOT/config"

# Logging Configuration
readonly LOG_FILE="$LOGS_DIR/deployment.log"
readonly TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# System Requirements
readonly MIN_PYTHON_VERSION="3.10"
readonly REQUIRED_SYSTEM_PACKAGES=(
    "python3"
    "python3-pip" 
    "python3-venv"
    "python3-dev"
    "git"
    "curl"
    "wget"
    "build-essential"
    "libssl-dev"
    "libffi-dev"
    "libbz2-dev"
    "libreadline-dev"
    "libsqlite3-dev"
    "libncurses5-dev"
    "libncursesw5-dev"
    "xz-utils"
    "tk-dev"
    "libxml2-dev"
    "libxmlsec1-dev"
    "libffi-dev"
    "liblzma-dev"
)

# Deployment State Tracking
DEPLOYMENT_STATE="starting"
ROLLBACK_COMMANDS=()

#==============================================================================
# UTILITY FUNCTIONS
#==============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    echo "[$TIMESTAMP] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

add_rollback_command() {
    ROLLBACK_COMMANDS+=("$1")
}

execute_rollback() {
    if [[ ${#ROLLBACK_COMMANDS[@]} -gt 0 ]]; then
        log_warning "Executing rollback commands..."
        for cmd in "${ROLLBACK_COMMANDS[@]}"; do
            log_info "Rolling back: $cmd"
            eval "$cmd" || log_error "Rollback command failed: $cmd"
        done
    fi
}

cleanup_on_exit() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed with exit code $exit_code"
        execute_rollback
    fi
    exit $exit_code
}

#==============================================================================
# SYSTEM VALIDATION FUNCTIONS
#==============================================================================

check_operating_system() {
    log_info "Checking operating system compatibility..."
    
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine operating system"
        return 1
    fi
    
    local os_name
    os_name=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
    local os_version
    os_version=$(grep '^VERSION_ID=' /etc/os-release | cut -d'"' -f2)
    
    log_info "Detected OS: $os_name $os_version"
    
    if [[ "$os_name" == "Ubuntu" ]]; then
        local version_major
        version_major=$(echo "$os_version" | cut -d'.' -f1)
        if [[ "$version_major" -ge 20 ]]; then
            log_success "Operating system is compatible: $os_name $os_version"
            return 0
        else
            log_warning "Ubuntu version $os_version detected. Recommended: 20.04+ (tested on 24.04)"
        fi
    else
        log_warning "Non-Ubuntu system detected. This script is optimized for Ubuntu 24.04"
    fi
    
    return 0
}

check_sudo_access() {
    log_info "Checking sudo access for system package installation..."
    
    if sudo -n true 2>/dev/null; then
        log_success "Sudo access confirmed"
        return 0
    else
        log_info "Sudo access required for system package installation"
        if sudo -v; then
            log_success "Sudo access granted"
            return 0
        else
            log_error "Sudo access denied or not available"
            return 1
        fi
    fi
}

check_internet_connectivity() {
    log_info "Checking internet connectivity..."
    
    if ping -c 1 google.com >/dev/null 2>&1; then
        log_success "Internet connectivity confirmed"
        return 0
    elif ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "Internet connectivity confirmed (DNS may have issues)"
        return 0
    else
        log_error "No internet connectivity detected"
        return 1
    fi
}

check_disk_space() {
    log_info "Checking available disk space..."
    
    local required_space_gb=2
    local available_space_gb
    available_space_gb=$(df "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1024/1024)}')
    
    if [[ "$available_space_gb" -ge "$required_space_gb" ]]; then
        log_success "Sufficient disk space: ${available_space_gb}GB available"
        return 0
    else
        log_error "Insufficient disk space: ${available_space_gb}GB available, ${required_space_gb}GB required"
        return 1
    fi
}

#==============================================================================
# PYTHON ENVIRONMENT FUNCTIONS
#==============================================================================

check_python_version() {
    log_info "Checking Python version..."
    
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 not found"
        return 1
    fi
    
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    
    log_info "Detected Python version: $python_version"
    
    # Compare version using sort -V (version sort)
    if printf '%s\n%s' "$MIN_PYTHON_VERSION" "$python_version" | sort -V -C; then
        log_success "Python version $python_version meets requirements (>= $MIN_PYTHON_VERSION)"
        return 0
    else
        log_error "Python version $python_version is below minimum required version $MIN_PYTHON_VERSION"
        return 1
    fi
}

install_system_packages() {
    log_info "Installing required system packages..."
    
    # Update package lists
    log_info "Updating package lists..."
    if ! sudo apt update; then
        log_error "Failed to update package lists"
        return 1
    fi
    
    # Check which packages are missing
    local missing_packages=()
    for package in "${REQUIRED_SYSTEM_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$package "; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -eq 0 ]]; then
        log_success "All required system packages are already installed"
        return 0
    fi
    
    log_info "Installing missing packages: ${missing_packages[*]}"
    if sudo apt install -y "${missing_packages[@]}"; then
        log_success "System packages installed successfully"
        return 0
    else
        log_error "Failed to install system packages"
        return 1
    fi
}

create_virtual_environment() {
    log_info "Setting up Python virtual environment..."
    
    if [[ -d "$VENV_DIR" ]]; then
        log_info "Virtual environment already exists at $VENV_DIR"
        if [[ -f "$VENV_DIR/bin/activate" ]]; then
            log_success "Using existing virtual environment"
            return 0
        else
            log_warning "Invalid virtual environment detected, recreating..."
            rm -rf "$VENV_DIR"
            add_rollback_command "rm -rf '$VENV_DIR'"
        fi
    fi
    
    if python3 -m venv "$VENV_DIR"; then
        log_success "Virtual environment created at $VENV_DIR"
        add_rollback_command "rm -rf '$VENV_DIR'"
        return 0
    else
        log_error "Failed to create virtual environment"
        return 1
    fi
}

activate_virtual_environment() {
    log_info "Activating virtual environment..."
    
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        log_error "Virtual environment activation script not found"
        return 1
    fi
    
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" == "$VENV_DIR" ]]; then
        log_success "Virtual environment activated"
        return 0
    else
        log_error "Failed to activate virtual environment"
        return 1
    fi
}

install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Upgrade pip first
    log_info "Upgrading pip..."
    if ! python -m pip install --upgrade pip; then
        log_error "Failed to upgrade pip"
        return 1
    fi
    
    # Install from requirements.txt
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_info "Installing dependencies from requirements.txt..."
        if python -m pip install -r "$PROJECT_ROOT/requirements.txt"; then
            log_success "Python dependencies installed successfully"
        else
            log_error "Failed to install Python dependencies"
            return 1
        fi
    else
        log_error "requirements.txt not found"
        return 1
    fi
    
    # Install Playwright browsers
    log_info "Installing Playwright browsers..."
    if python -m playwright install; then
        log_success "Playwright browsers installed successfully"
    else
        log_warning "Failed to install Playwright browsers (continuing anyway)"
    fi
    
    return 0
}

#==============================================================================
# CONFIGURATION FUNCTIONS
#==============================================================================

create_directory_structure() {
    log_info "Creating directory structure..."
    
    local directories=("$LOGS_DIR" "$DATA_DIR" "$CONFIG_DIR")
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            if mkdir -p "$dir"; then
                log_info "Created directory: $dir"
                add_rollback_command "rm -rf '$dir'"
            else
                log_error "Failed to create directory: $dir"
                return 1
            fi
        else
            log_info "Directory already exists: $dir"
        fi
    done
    
    log_success "Directory structure created successfully"
    return 0
}

generate_environment_file() {
    log_info "Generating environment configuration file..."
    
    local env_file="$PROJECT_ROOT/.env"
    
    if [[ -f "$env_file" ]]; then
        log_info "Environment file already exists, backing up..."
        cp "$env_file" "${env_file}.backup.$(date +%s)"
    fi
    
    # Generate basic .env file
    cat > "$env_file" << EOF
# Watchtower Environment Configuration
# Generated by deployment script at $(date)

# Environment
WATCHTOWER_ENVIRONMENT=production
DEBUG=false

# Logging Configuration
LOGGING__LEVEL=INFO
LOGGING__FILE_PATH=$LOGS_DIR/watchtower.log

# Streamlit Configuration
STREAMLIT__HOST=0.0.0.0
STREAMLIT__PORT=8501
STREAMLIT__DEBUG=false

# ETL Configuration
ETL__BATCH_SIZE=1000
ETL__PARALLEL_JOBS=4
ETL__DATA_PATH=$DATA_DIR

# Data Paths
DATA_DIR=$DATA_DIR
LOGS_DIR=$LOGS_DIR

# MyAnimeList API (optional - add your client ID if needed)
# MAL_CLIENT_ID=YOUR_MAL_CLIENT_ID_HERE

# Google Drive Backup Configuration (optional)
# WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE=client_secrets.json
# WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID=your_google_drive_folder_id_here

# News API Configuration (optional)
# API_NEWS_API_KEY=YOUR_KEY_HERE
EOF
    
    add_rollback_command "rm -f '$env_file'"
    log_success "Environment file generated at $env_file"
    return 0
}

#==============================================================================
# DEPLOYMENT FUNCTIONS
#==============================================================================

deploy_etl_pipelines() {
    log_info "Deploying ETL pipelines..."
    
    # Verify ETL scripts exist
    if [[ ! -f "$PROJECT_ROOT/run_all_etl.sh" ]]; then
        log_error "ETL runner script not found: run_all_etl.sh"
        return 1
    fi
    
    # Make ETL scripts executable
    chmod +x "$PROJECT_ROOT/run_all_etl.sh"
    
    # Test ETL pipeline (run a quick validation)
    log_info "Testing ETL pipeline configuration..."
    if [[ -d "$PROJECT_ROOT/src/etl" ]]; then
        local etl_count
        etl_count=$(find "$PROJECT_ROOT/src/etl" -name "*.py" -type f | wc -l)
        log_info "Found $etl_count ETL modules"
        log_success "ETL pipelines deployed successfully"
    else
        log_error "ETL source directory not found"
        return 1
    fi
    
    return 0
}

deploy_streamlit_dashboard() {
    log_info "Deploying Streamlit dashboard..."
    
    # Verify Streamlit app exists
    local streamlit_app="$PROJECT_ROOT/src/web/fullstreamlit/app.py"
    if [[ ! -f "$streamlit_app" ]]; then
        log_error "Streamlit app not found: $streamlit_app"
        return 1
    fi
    
    # Test Streamlit installation
    if ! python -c "import streamlit; print(f'Streamlit version: {streamlit.__version__}')"; then
        log_error "Streamlit not properly installed"
        return 1
    fi
    
    log_success "Streamlit dashboard deployed successfully"
    return 0
}

create_systemd_service() {
    log_info "Creating systemd service for Streamlit dashboard..."
    
    local service_file="/etc/systemd/system/watchtower-streamlit.service"
    local current_user
    current_user=$(whoami)
    
    # Create systemd service file
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Watchtower Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$VENV_DIR/bin:$PATH
Environment=PYTHONPATH=$PROJECT_ROOT/src
ExecStart=$VENV_DIR/bin/streamlit run src/web/fullstreamlit/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    add_rollback_command "sudo systemctl stop watchtower-streamlit; sudo systemctl disable watchtower-streamlit; sudo rm -f '$service_file'"
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable watchtower-streamlit
    
    log_success "Systemd service created and enabled"
    return 0
}

start_services() {
    log_info "Starting Watchtower services..."
    
    # Start Streamlit service
    if sudo systemctl start watchtower-streamlit; then
        log_success "Streamlit service started successfully"
    else
        log_error "Failed to start Streamlit service"
        return 1
    fi
    
    # Wait a moment for service to start
    sleep 5
    
    # Check service status
    if sudo systemctl is-active --quiet watchtower-streamlit; then
        log_success "Streamlit service is running"
    else
        log_error "Streamlit service failed to start properly"
        sudo systemctl status watchtower-streamlit
        return 1
    fi
    
    return 0
}

#==============================================================================
# VALIDATION FUNCTIONS
#==============================================================================

validate_installation() {
    log_info "Validating installation..."
    
    local validation_failed=false
    
    # Check virtual environment
    if [[ ! -d "$VENV_DIR" ]] || [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        log_error "Virtual environment validation failed"
        validation_failed=true
    fi
    
    # Check Python dependencies
    if ! python -c "import streamlit, pandas, requests, beautifulsoup4" 2>/dev/null; then
        log_error "Python dependencies validation failed"
        validation_failed=true
    fi
    
    # Check directory structure
    for dir in "$LOGS_DIR" "$DATA_DIR"; do
        if [[ ! -d "$dir" ]]; then
            log_error "Directory validation failed: $dir"
            validation_failed=true
        fi
    done
    
    # Check configuration files
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        log_error "Configuration file validation failed"
        validation_failed=true
    fi
    
    # Check service status
    if ! sudo systemctl is-active --quiet watchtower-streamlit; then
        log_error "Service validation failed: Streamlit service not running"
        validation_failed=true
    fi
    
    # Check service accessibility
    if ! curl -s http://localhost:8501 >/dev/null; then
        log_error "Service accessibility validation failed: Dashboard not accessible"
        validation_failed=true
    fi
    
    if [[ "$validation_failed" == "true" ]]; then
        log_error "Installation validation failed"
        return 1
    else
        log_success "Installation validation passed"
        return 0
    fi
}

#==============================================================================
# MAIN DEPLOYMENT FUNCTION
#==============================================================================

main() {
    echo "=============================================================================="
    echo "                   WATCHTOWER AUTOMATED DEPLOYMENT"
    echo "=============================================================================="
    echo ""
    echo "This script will automatically set up and deploy the complete Watchtower"
    echo "environment including ETL pipelines and Streamlit dashboard."
    echo ""
    echo "Platform: Ubuntu 24.04+ (tested)"
    echo "Requirements: sudo access, internet connection"
    echo ""
    echo "=============================================================================="
    echo ""
    
    # Set up signal handlers for cleanup
    trap cleanup_on_exit EXIT INT TERM
    
    # Create logs directory early
    mkdir -p "$LOGS_DIR"
    
    # Initialize log file
    echo "Watchtower Deployment Log - Started at $TIMESTAMP" > "$LOG_FILE"
    
    log_info "Starting Watchtower automated deployment..."
    log_info "Working directory: $PROJECT_ROOT"
    
    # Phase 1: System Validation
    log_info "Phase 1: System Validation"
    DEPLOYMENT_STATE="system_validation"
    
    check_operating_system || exit 1
    check_sudo_access || exit 1
    check_internet_connectivity || exit 1
    check_disk_space || exit 1
    check_python_version || exit 1
    
    # Phase 2: System Setup
    log_info "Phase 2: System Setup"
    DEPLOYMENT_STATE="system_setup"
    
    install_system_packages || exit 1
    create_virtual_environment || exit 1
    activate_virtual_environment || exit 1
    install_python_dependencies || exit 1
    
    # Phase 3: Configuration
    log_info "Phase 3: Configuration"
    DEPLOYMENT_STATE="configuration"
    
    create_directory_structure || exit 1
    generate_environment_file || exit 1
    
    # Phase 4: Application Deployment
    log_info "Phase 4: Application Deployment"
    DEPLOYMENT_STATE="deployment"
    
    deploy_etl_pipelines || exit 1
    deploy_streamlit_dashboard || exit 1
    create_systemd_service || exit 1
    start_services || exit 1
    
    # Phase 5: Validation
    log_info "Phase 5: Validation"
    DEPLOYMENT_STATE="validation"
    
    validate_installation || exit 1
    
    # Deployment Complete
    DEPLOYMENT_STATE="complete"
    
    echo ""
    echo "=============================================================================="
    log_success "WATCHTOWER DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=============================================================================="
    echo ""
    echo "🎉 Your Watchtower environment is now ready!"
    echo ""
    echo "📊 Dashboard Access:"
    echo "   • URL: http://localhost:8501"
    echo "   • Status: $(sudo systemctl is-active watchtower-streamlit)"
    echo ""
    echo "🔧 Service Management:"
    echo "   • Start:   sudo systemctl start watchtower-streamlit"
    echo "   • Stop:    sudo systemctl stop watchtower-streamlit"
    echo "   • Restart: sudo systemctl restart watchtower-streamlit"
    echo "   • Status:  sudo systemctl status watchtower-streamlit"
    echo ""
    echo "📈 ETL Pipelines:"
    echo "   • Run all: ./run_all_etl.sh"
    echo "   • Logs:    $LOGS_DIR/"
    echo ""
    echo "📁 Important Directories:"
    echo "   • Data:    $DATA_DIR/"
    echo "   • Logs:    $LOGS_DIR/"
    echo "   • Config:  .env"
    echo ""
    echo "📖 For more information, see the README.md file."
    echo ""
    echo "=============================================================================="
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
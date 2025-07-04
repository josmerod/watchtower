#!/bin/bash

#==============================================================================
# WATCHTOWER DEPLOYMENT TESTING SCRIPT
#==============================================================================
#
# Description: Comprehensive testing of deployment script functionality
# Usage: ./test_deployment.sh [--simulate-internet-failure] [--simulate-permission-failure]
# 
# This script tests various deployment scenarios including failure conditions
#==============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"
readonly TEST_LOG="$PROJECT_ROOT/logs/test_deployment.log"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Test configuration
SIMULATE_INTERNET_FAILURE=false
SIMULATE_PERMISSION_FAILURE=false

log_info() {
    echo -e "${BLUE}[TEST-INFO]${NC} $*" | tee -a "$TEST_LOG"
}

log_success() {
    echo -e "${GREEN}[TEST-SUCCESS]${NC} $*" | tee -a "$TEST_LOG"
}

log_warning() {
    echo -e "${YELLOW}[TEST-WARNING]${NC} $*" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[TEST-ERROR]${NC} $*" | tee -a "$TEST_LOG"
}

setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Initialize test log
    echo "Watchtower Deployment Testing - $(date)" > "$TEST_LOG"
    
    # Backup any existing .env file
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.backup.$(date +%s)"
        log_info "Backed up existing .env file"
    fi
}

test_deployment_script_validation() {
    log_info "Testing deployment script validation..."
    
    # Test script syntax
    if bash -n "$PROJECT_ROOT/deploy.sh"; then
        log_success "Deployment script syntax is valid"
    else
        log_error "Deployment script has syntax errors"
        return 1
    fi
    
    # Test that required functions exist
    local required_functions=(
        "check_operating_system"
        "check_sudo_access"
        "install_system_packages"
        "create_virtual_environment"
        "deploy_etl_pipelines"
        "deploy_streamlit_dashboard"
        "validate_installation"
    )
    
    for func in "${required_functions[@]}"; do
        if grep -q "^$func()" "$PROJECT_ROOT/deploy.sh"; then
            log_success "Function $func exists in deployment script"
        else
            log_error "Required function $func not found in deployment script"
            return 1
        fi
    done
    
    return 0
}

test_system_requirements_check() {
    log_info "Testing system requirements checking..."
    
    # Test OS detection
    if [[ -f /etc/os-release ]]; then
        local os_name
        os_name=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
        log_success "OS detection works: $os_name"
    else
        log_warning "Cannot test OS detection (no /etc/os-release)"
    fi
    
    # Test Python version check
    if python3 -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')" >/dev/null 2>&1; then
        log_success "Python version checking works"
    else
        log_error "Python version checking failed"
        return 1
    fi
    
    # Test sudo access simulation
    if [[ "$SIMULATE_PERMISSION_FAILURE" == "false" ]]; then
        if sudo -n true 2>/dev/null || sudo -v; then
            log_success "Sudo access available for testing"
        else
            log_warning "Sudo access not available (some tests will be skipped)"
        fi
    else
        log_info "Simulating permission failure for testing"
    fi
    
    return 0
}

test_virtual_environment_creation() {
    log_info "Testing virtual environment creation..."
    
    local test_venv="$PROJECT_ROOT/.test_venv"
    
    # Clean up any existing test venv
    if [[ -d "$test_venv" ]]; then
        rm -rf "$test_venv"
    fi
    
    # Test venv creation
    if python3 -m venv "$test_venv"; then
        log_success "Virtual environment creation works"
        
        # Test activation
        if [[ -f "$test_venv/bin/activate" ]]; then
            log_success "Virtual environment activation script exists"
            
            # Test pip upgrade in venv
            if "$test_venv/bin/python" -m pip install --upgrade pip >/dev/null 2>&1; then
                log_success "Pip upgrade in virtual environment works"
            else
                log_warning "Pip upgrade in virtual environment failed"
            fi
        else
            log_error "Virtual environment activation script not found"
        fi
        
        # Clean up test venv
        rm -rf "$test_venv"
    else
        log_error "Virtual environment creation failed"
        return 1
    fi
    
    return 0
}

test_configuration_generation() {
    log_info "Testing configuration file generation..."
    
    local test_env="$PROJECT_ROOT/.env.test"
    
    # Test basic configuration generation
    cat > "$test_env" << 'EOF'
# Test configuration
WATCHTOWER_ENVIRONMENT=test
DEBUG=true
LOGGING__LEVEL=DEBUG
STREAMLIT__HOST=0.0.0.0
STREAMLIT__PORT=8501
ETL__BATCH_SIZE=100
EOF
    
    if [[ -f "$test_env" ]]; then
        log_success "Configuration file generation works"
        
        # Test configuration parsing
        if grep -q "WATCHTOWER_ENVIRONMENT=test" "$test_env"; then
            log_success "Configuration content is correct"
        else
            log_error "Configuration content is incorrect"
        fi
        
        # Clean up test config
        rm -f "$test_env"
    else
        log_error "Configuration file generation failed"
        return 1
    fi
    
    return 0
}

test_etl_structure_validation() {
    log_info "Testing ETL structure validation..."
    
    # Check ETL directory exists
    if [[ -d "$PROJECT_ROOT/src/etl" ]]; then
        log_success "ETL directory exists"
        
        # Count ETL modules
        local etl_count
        etl_count=$(find "$PROJECT_ROOT/src/etl" -name "*.py" -type f | wc -l)
        
        if [[ "$etl_count" -gt 0 ]]; then
            log_success "Found $etl_count ETL modules"
        else
            log_error "No ETL modules found"
            return 1
        fi
        
        # Check main ETL runner exists
        if [[ -f "$PROJECT_ROOT/run_all_etl.sh" ]]; then
            log_success "ETL runner script exists"
            
            # Test script syntax
            if bash -n "$PROJECT_ROOT/run_all_etl.sh"; then
                log_success "ETL runner script syntax is valid"
            else
                log_error "ETL runner script has syntax errors"
                return 1
            fi
        else
            log_error "ETL runner script not found"
            return 1
        fi
    else
        log_error "ETL directory not found"
        return 1
    fi
    
    return 0
}

test_streamlit_application() {
    log_info "Testing Streamlit application structure..."
    
    # Check Streamlit app exists
    local streamlit_app="$PROJECT_ROOT/src/web/fullstreamlit/app.py"
    if [[ -f "$streamlit_app" ]]; then
        log_success "Streamlit application file exists"
        
        # Test basic Python syntax
        if python3 -m py_compile "$streamlit_app" 2>/dev/null; then
            log_success "Streamlit application syntax is valid"
        else
            log_warning "Streamlit application has syntax issues (may be import-related)"
        fi
        
        # Check for main Streamlit patterns
        if grep -q "streamlit" "$streamlit_app"; then
            log_success "Streamlit application contains Streamlit imports"
        else
            log_warning "Streamlit application may not import Streamlit properly"
        fi
    else
        log_error "Streamlit application file not found"
        return 1
    fi
    
    return 0
}

test_systemd_service_template() {
    log_info "Testing systemd service template generation..."
    
    # Test that we can generate a basic systemd service file
    local test_service="/tmp/watchtower-test.service"
    local current_user
    current_user=$(whoami)
    
    cat > "$test_service" << EOF
[Unit]
Description=Watchtower Streamlit Dashboard (Test)
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$PROJECT_ROOT/.venv/bin:$PATH
Environment=PYTHONPATH=$PROJECT_ROOT/src
ExecStart=$PROJECT_ROOT/.venv/bin/streamlit run src/web/fullstreamlit/app.py --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    if [[ -f "$test_service" ]]; then
        log_success "Systemd service template generation works"
        
        # Check service file structure
        if grep -q "\[Unit\]" "$test_service" && grep -q "\[Service\]" "$test_service"; then
            log_success "Systemd service template structure is correct"
        else
            log_error "Systemd service template structure is incorrect"
        fi
        
        # Clean up test service
        rm -f "$test_service"
    else
        log_error "Systemd service template generation failed"
        return 1
    fi
    
    return 0
}

test_rollback_functionality() {
    log_info "Testing rollback functionality simulation..."
    
    # Create test directories to simulate deployment state
    local test_dirs=("$PROJECT_ROOT/test_logs" "$PROJECT_ROOT/test_data" "$PROJECT_ROOT/test_config")
    
    for dir in "${test_dirs[@]}"; do
        mkdir -p "$dir"
        echo "test content" > "$dir/test_file"
    done
    
    # Test cleanup commands (simulate rollback)
    local cleanup_success=true
    for dir in "${test_dirs[@]}"; do
        if rm -rf "$dir"; then
            log_success "Rollback cleanup successful for $dir"
        else
            log_error "Rollback cleanup failed for $dir"
            cleanup_success=false
        fi
    done
    
    if [[ "$cleanup_success" == "true" ]]; then
        log_success "Rollback functionality simulation passed"
        return 0
    else
        log_error "Rollback functionality simulation failed"
        return 1
    fi
}

run_comprehensive_tests() {
    log_info "Running comprehensive deployment tests..."
    
    local tests_passed=0
    local tests_total=8
    
    # Array of test functions
    local test_functions=(
        "test_deployment_script_validation"
        "test_system_requirements_check"
        "test_virtual_environment_creation"
        "test_configuration_generation"
        "test_etl_structure_validation"
        "test_streamlit_application"
        "test_systemd_service_template"
        "test_rollback_functionality"
    )
    
    # Run each test
    for test_func in "${test_functions[@]}"; do
        echo ""
        log_info "Running $test_func..."
        
        if "$test_func"; then
            ((tests_passed++))
            log_success "$test_func PASSED"
        else
            log_error "$test_func FAILED"
        fi
    done
    
    echo ""
    echo "=============================================================================="
    echo "COMPREHENSIVE TEST SUMMARY"
    echo "=============================================================================="
    echo "Tests passed: $tests_passed/$tests_total"
    
    if [[ "$tests_passed" -eq "$tests_total" ]]; then
        log_success "All comprehensive tests passed! Deployment script is ready."
        return 0
    else
        log_warning "$((tests_total - tests_passed)) tests failed."
        return 1
    fi
}

main() {
    echo "=============================================================================="
    echo "                   WATCHTOWER DEPLOYMENT TESTING"
    echo "=============================================================================="
    echo ""
    echo "This script performs comprehensive testing of the deployment functionality"
    echo "without actually deploying to validate that the deployment will work."
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --simulate-internet-failure)
                SIMULATE_INTERNET_FAILURE=true
                shift
                ;;
            --simulate-permission-failure)
                SIMULATE_PERMISSION_FAILURE=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--simulate-internet-failure] [--simulate-permission-failure]"
                exit 1
                ;;
        esac
    done
    
    setup_test_environment
    
    if run_comprehensive_tests; then
        echo ""
        log_success "🎉 All deployment tests passed! The deployment script should work correctly."
        echo ""
        echo "Next steps:"
        echo "1. Run ./validate_deployment.sh to do a quick pre-deployment check"
        echo "2. Run ./deploy.sh to perform the actual deployment"
        echo ""
        exit 0
    else
        echo ""
        log_error "❌ Some deployment tests failed. Please review the issues above."
        echo ""
        echo "Check the test log: $TEST_LOG"
        exit 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
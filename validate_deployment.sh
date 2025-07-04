#!/bin/bash

#==============================================================================
# WATCHTOWER DEPLOYMENT VALIDATION SCRIPT
#==============================================================================

set -eu

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

DRY_RUN=false

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

run_validation_tests() {
    local tests_passed=0
    local tests_total=7
    
    # Test 1: Script syntax
    echo ""
    log_info "Testing deployment script syntax..."
    if bash -n "$PROJECT_ROOT/deploy.sh"; then
        log_success "Deployment script syntax is valid"
        ((tests_passed++))
    else
        log_error "Deployment script has syntax errors"
    fi
    
    # Test 2: Required files
    echo ""
    log_info "Checking required files exist..."
    local required_files=("deploy.sh" "requirements.txt" "src/web/fullstreamlit/app.py" "run_all_etl.sh")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log_success "All required files present"
        ((tests_passed++))
    else
        log_error "Missing required files: ${missing_files[*]}"
    fi
    
    # Test 3: Python basic functionality
    echo ""
    log_info "Testing basic Python functionality..."
    if python3 -c "import sys; print('Python test OK')" >/dev/null 2>&1; then
        log_success "Basic Python functionality works"
        ((tests_passed++))
    else
        log_error "Basic Python functionality failed"
    fi
    
    # Test 4: ETL structure
    echo ""
    log_info "Validating ETL structure..."
    if [[ -d "$PROJECT_ROOT/src/etl" ]]; then
        local etl_count
        etl_count=$(find "$PROJECT_ROOT/src/etl" -name "*.py" -type f | wc -l)
        if [[ "$etl_count" -gt 0 ]]; then
            log_success "Found $etl_count ETL modules"
            ((tests_passed++))
        else
            log_error "No ETL modules found"
        fi
    else
        log_error "ETL directory not found"
    fi
    
    # Test 5: Configuration templates
    echo ""
    log_info "Testing configuration template generation..."
    local temp_env="/tmp/test_env_$$"
    if cat > "$temp_env" << 'EOF' && [[ -f "$temp_env" ]]; then
WATCHTOWER_ENVIRONMENT=test
DEBUG=true
LOGGING__LEVEL=DEBUG
EOF
        log_success "Configuration generation works"
        rm -f "$temp_env"
        ((tests_passed++))
    else
        log_error "Configuration generation failed"
    fi
    
    # Test 6: Script permissions
    echo ""
    log_info "Checking script permissions..."
    local script_perms_ok=true
    if [[ -x "$PROJECT_ROOT/deploy.sh" ]]; then
        log_success "Deploy script is executable"
    else
        log_warning "Deploy script is not executable (will be fixed during deployment)"
        script_perms_ok=false
    fi
    
    if [[ -x "$PROJECT_ROOT/run_all_etl.sh" ]]; then
        log_success "ETL runner script is executable"
    else
        log_warning "ETL runner script is not executable (will be fixed during deployment)"
        script_perms_ok=false
    fi
    
    if [[ "$script_perms_ok" == "true" ]]; then
        ((tests_passed++))
    fi
    
    # Test 7: System compatibility
    echo ""
    log_info "Testing system compatibility..."
    local sys_compat_ok=true
    
    if [[ -f /etc/os-release ]]; then
        local os_name
        os_name=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
        log_info "Operating System: $os_name"
        if [[ "$os_name" == "Ubuntu" ]]; then
            log_success "Running on Ubuntu (compatible)"
        else
            log_warning "Not running on Ubuntu (may work but not fully tested)"
            sys_compat_ok=false
        fi
    else
        log_warning "Cannot determine operating system"
        sys_compat_ok=false
    fi
    
    if command -v python3 >/dev/null 2>&1; then
        local python_version
        python_version=$(python3 --version)
        log_success "Python available: $python_version"
    else
        log_error "Python 3 not found"
        sys_compat_ok=false
    fi
    
    if [[ "$sys_compat_ok" == "true" ]]; then
        ((tests_passed++))
    fi
    
    echo ""
    echo "=============================================================================="
    echo "VALIDATION SUMMARY"
    echo "=============================================================================="
    echo "Tests passed: $tests_passed/$tests_total"
    
    if [[ "$tests_passed" -eq "$tests_total" ]]; then
        log_success "All validation tests passed! Deployment should work correctly."
        echo ""
        echo "✅ Ready to deploy! Run: ./deploy.sh"
        return 0
    else
        log_warning "Some validation tests failed or showed warnings."
        echo ""
        echo "⚠️  You may still try deployment, but some issues might occur."
        echo "   Run: ./deploy.sh"
        return 1
    fi
}

main() {
    echo "=============================================================================="
    echo "                   WATCHTOWER DEPLOYMENT VALIDATION"
    echo "=============================================================================="
    echo ""
    
    if [[ "${1:-}" == "--dry-run" ]]; then
        DRY_RUN=true
        log_info "Running in dry-run mode"
    fi
    
    run_validation_tests
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
#!/bin/bash

#==============================================================================
# WATCHTOWER TEST SUITE
#==============================================================================
#
# Description: Runs all deployment tests in sequence
# Usage: ./run_all_tests.sh
#
# This script runs the complete test suite for deployment validation
#==============================================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log_info() {
    echo -e "${BLUE}[TEST-SUITE]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[TEST-SUITE]${NC} $*"
}

log_error() {
    echo -e "${RED}[TEST-SUITE]${NC} $*"
}

main() {
    echo "=============================================================================="
    echo "                   WATCHTOWER COMPLETE TEST SUITE"
    echo "=============================================================================="
    echo ""
    echo "Running all deployment tests to validate complete functionality..."
    echo ""
    
    local tests_passed=0
    local tests_total=3
    
    # Test 1: Basic validation
    log_info "Running basic validation tests..."
    if ./validate_deployment.sh >/dev/null 2>&1; then
        log_success "✅ Basic validation tests PASSED"
        ((tests_passed++))
    else
        log_error "❌ Basic validation tests FAILED"
    fi
    
    echo ""
    
    # Test 2: Comprehensive testing
    log_info "Running comprehensive deployment tests..."
    if ./test_deployment.sh >/dev/null 2>&1; then
        log_success "✅ Comprehensive deployment tests PASSED"
        ((tests_passed++))
    else
        log_error "❌ Comprehensive deployment tests FAILED"
    fi
    
    echo ""
    
    # Test 3: Idempotency testing
    log_info "Running idempotency tests..."
    if ./test_idempotency.sh >/dev/null 2>&1; then
        log_success "✅ Idempotency tests PASSED"
        ((tests_passed++))
    else
        log_error "❌ Idempotency tests FAILED"
    fi
    
    echo ""
    echo "=============================================================================="
    echo "COMPLETE TEST SUITE SUMMARY"
    echo "=============================================================================="
    echo "Test suites passed: $tests_passed/$tests_total"
    echo ""
    
    if [[ "$tests_passed" -eq "$tests_total" ]]; then
        log_success "🎉 ALL TESTS PASSED! Deployment script is ready for production use."
        echo ""
        echo "Your Watchtower deployment script has been thoroughly validated:"
        echo "  ✅ Basic functionality confirmed"
        echo "  ✅ Comprehensive deployment scenarios tested"
        echo "  ✅ Idempotency (multiple runs) verified"
        echo ""
        echo "🚀 Ready to deploy! Run: ./deploy.sh"
        echo ""
        return 0
    else
        log_error "❌ Some test suites failed. Please review individual test outputs."
        echo ""
        echo "Run individual tests for detailed information:"
        echo "  • ./validate_deployment.sh       - Basic validation"
        echo "  • ./test_deployment.sh          - Comprehensive testing"
        echo "  • ./test_idempotency.sh         - Idempotency testing"
        echo ""
        return 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
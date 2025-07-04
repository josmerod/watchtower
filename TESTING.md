# Watchtower Deployment Testing

This document describes the testing approach for the automated deployment script.

## Testing Scripts

### 1. `test_deployment.sh` - Comprehensive Testing
Tests all deployment components without actually deploying:
- Deployment script validation
- System requirements checking  
- Virtual environment creation
- Configuration generation
- ETL structure validation
- Streamlit application testing
- Systemd service template generation
- Rollback functionality

**Usage:**
```bash
./test_deployment.sh
```

**Advanced usage:**
```bash
./test_deployment.sh --simulate-internet-failure
./test_deployment.sh --simulate-permission-failure
```

### 2. `validate_deployment.sh` - Quick Validation
Performs basic pre-deployment checks:
- Script syntax validation
- Required files check
- Basic Python functionality
- System compatibility

**Usage:**
```bash
./validate_deployment.sh
```

### 3. `simple_test.sh` - Basic Sanity Check
Quick verification of core components:
- Script syntax
- File presence
- Python availability

**Usage:**
```bash
./simple_test.sh
```

## Test Coverage

The testing suite validates:

✅ **Script Integrity**
- Syntax validation for all shell scripts
- Function existence verification
- Error handling validation

✅ **System Compatibility**  
- Ubuntu version detection
- Python version compatibility
- Package manager availability
- Sudo access verification

✅ **Environment Setup**
- Virtual environment creation
- Dependency installation simulation
- Configuration file generation
- Directory structure creation

✅ **Application Components**
- ETL pipeline structure validation
- Streamlit application testing
- Service configuration templates
- Logging mechanism verification

✅ **Error Recovery**
- Rollback functionality testing
- Cleanup mechanism validation
- Error state simulation

## Testing Results

When all tests pass, you should see:

```
==============================================================================
COMPREHENSIVE TEST SUMMARY
==============================================================================
Tests passed: 8/8
[TEST-SUCCESS] All comprehensive tests passed! Deployment script is ready.
```

## Failure Scenarios

The tests cover common failure scenarios:

1. **Missing Dependencies**: Validates that all required system packages and Python modules are properly handled
2. **Permission Issues**: Tests sudo access and file permission handling
3. **Configuration Errors**: Validates configuration file generation and parsing
4. **Service Setup Failures**: Tests systemd service template generation
5. **Rollback Requirements**: Ensures proper cleanup on deployment failure

## Integration with CI/CD

These tests can be integrated into continuous integration pipelines:

```bash
# In your CI pipeline
./test_deployment.sh
if [ $? -eq 0 ]; then
    echo "Deployment tests passed - ready for deployment"
else
    echo "Deployment tests failed - fixing required"
    exit 1
fi
```

## Manual Testing Checklist

Before deployment, verify:

- [ ] Run `./test_deployment.sh` - all tests pass
- [ ] Run `./validate_deployment.sh` - validation successful
- [ ] Check target system has Ubuntu 20.04+ 
- [ ] Verify sudo access available
- [ ] Confirm internet connectivity
- [ ] Ensure 2GB+ disk space available

## Post-Deployment Testing

After running `./deploy.sh`, verify:

- [ ] Streamlit dashboard accessible at http://localhost:8501
- [ ] Service status: `sudo systemctl status watchtower-streamlit`
- [ ] ETL pipelines executable: `./run_all_etl.sh --help`
- [ ] Log files created in `logs/` directory
- [ ] Configuration file `.env` properly generated
- [ ] Virtual environment created at `.venv/`

## Troubleshooting Tests

If tests fail:

1. **Check test logs**: `tail -f logs/test_deployment.log`
2. **Run individual tests**: Source the test script and run specific functions
3. **Verify permissions**: Ensure execute permissions on all scripts
4. **Check dependencies**: Ensure basic system tools (bash, python3, etc.) are available

## Test Environment

Tests are designed to run on:
- Ubuntu 20.04+
- Python 3.8+
- Bash 4.0+
- Standard GNU coreutils

No additional dependencies required for testing.
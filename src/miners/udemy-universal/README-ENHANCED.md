# Enhanced Udemy Universal Miner

This is an enhanced version of the Udemy Universal Miner with significant improvements based on features from the [techtanic/Discounted-Udemy-Course-Enroller](https://github.com/techtanic/Discounted-Udemy-Course-Enroller) repository.

## 🆕 New Features

### 1. **Unified CLI Interface** (`unified_cli.py`)
- Single command-line interface for all operations
- Comprehensive argument parsing with help system
- Support for extract, enroll, and combined run modes
- Enhanced error handling and user feedback

```bash
# Extract courses from all sites
python unified_cli.py extract

# Enroll in previously extracted courses
python unified_cli.py enroll

# Extract and enroll in one step
python unified_cli.py run

# Use custom configuration
python unified_cli.py --config settings.json extract

# Show statistics for last 7 days
python unified_cli.py --stats --days 7
```

### 2. **Advanced Update Checking** (`update_checker.py`)
- Automatic checking for updates from the original repository
- Changelog parsing and display
- Configurable update intervals
- Detailed version comparison with semantic versioning

```python
from update_checker import check_for_updates, display_update_notification

# Check for updates
login_title, main_title = check_for_updates()
display_update_notification()
```

### 3. **Comprehensive Statistics** (`statistics_reporter.py`)
- Detailed enrollment session tracking
- Performance metrics and success rates
- Daily, weekly, and monthly statistics
- Export capabilities (JSON, CSV)
- Visual progress reporting

```python
from statistics_reporter import start_session, end_session, record_enrollment

# Track enrollment session
session_id = start_session()
record_enrollment("enrolled", amount_saved=50.0, category="development")
end_session()
```

### 4. **Enhanced Filtering System** (`enhanced_filtering.py`)
- Advanced course filtering with multiple criteria
- Category and language normalization
- Rating, review count, and update date filters
- Keyword-based exclusions
- Flexible rule-based filtering engine

```python
from enhanced_filtering import EnhancedFilter

# Create filter with settings
filter_settings = {
    "languages": {"en": True, "es": False},
    "categories": {"development": True, "business": True},
    "filters": {"min_rating": 4.0, "min_reviews": 10}
}

enhanced_filter = EnhancedFilter(filter_settings)
passes, reasons = enhanced_filter.filter_course(course_data)
```

### 5. **Advanced Cookie Management** (`cookie_manager.py`)
- Multi-browser cookie extraction support
- Chrome, Firefox, Edge, Safari, Opera, Brave compatibility
- Fallback mechanisms for robust cookie retrieval
- Cross-platform support (Windows, macOS, Linux)
- Cookie validation and testing tools

```python
from cookie_manager import get_cookies, detect_browsers

# Detect available browsers
browsers = detect_browsers()

# Extract cookies with fallback
cookies = get_cookies("chrome")
```

### 6. **Configuration Validation** (`config_validator.py`)
- Comprehensive configuration validation
- Detailed error messages with suggestions
- Schema-based validation with type checking
- Default configuration generation
- Cross-field validation

```python
from config_validator import validate_config, generate_default_config

# Validate configuration
is_valid, results = validate_config(config_dict)

# Generate default configuration
default_config = generate_default_config()
```

### 7. **Enhanced Logging** (`logger.py` - enhanced)
- Structured JSON logging support
- Metrics collection and tracking
- Performance timing utilities
- TQDM-compatible progress bar logging
- Configurable log levels and formatting

```python
from logger import setup_structured_logging, create_metrics_logger

# Setup structured logging
logger = setup_structured_logging("udemy-miner")

# Create metrics logger
metrics = create_metrics_logger()
metrics.start_timer("extraction")
metrics.end_timer("extraction")
```

### 8. **Default Configuration Files**
- `default-duce-cli-settings.json` - CLI configuration template
- `default-duce-gui-settings.json` - GUI configuration template
- Comprehensive settings with detailed documentation
- Environment-specific configurations

## 🔧 Enhanced Features

### Improved Base Functionality
- **Enhanced Update Checking**: Integrated with the new update checker for better version management
- **Advanced Cookie Support**: Fallback mechanisms for cookie extraction with multiple browser support
- **Better Error Handling**: Comprehensive error reporting with suggestions
- **Performance Optimization**: Metrics tracking and performance monitoring

### Enhanced CLI Experience
- **Unified Interface**: Single entry point for all operations
- **Rich Help System**: Comprehensive help and usage examples
- **Progress Tracking**: Visual progress indicators with detailed status
- **Flexible Configuration**: Support for multiple configuration formats

### Statistics and Reporting
- **Session Tracking**: Detailed tracking of enrollment sessions
- **Performance Metrics**: Success rates, processing times, and efficiency metrics
- **Historical Analysis**: Trends and patterns over time
- **Export Capabilities**: Multiple export formats for further analysis

### Advanced Filtering
- **Multi-Criteria Filtering**: Complex filtering with multiple conditions
- **Smart Categorization**: Automatic category and language normalization
- **Exclusion Rules**: Flexible exclusion based on keywords, instructors, etc.
- **Performance Optimization**: Efficient filtering with minimal impact

## 📁 File Structure

```
src/miners/udemy-universal/
├── unified_cli.py              # Main unified CLI interface
├── update_checker.py           # Update checking functionality
├── statistics_reporter.py      # Statistics and reporting
├── enhanced_filtering.py       # Advanced filtering system
├── cookie_manager.py           # Multi-browser cookie management
├── config_validator.py         # Configuration validation
├── logger.py                   # Enhanced logging (updated)
├── base.py                     # Core functionality (updated)
├── cli.py                      # Original CLI (updated)
├── enroll.py                   # Enrollment functionality (updated)
├── default-duce-cli-settings.json    # CLI configuration template
├── default-duce-gui-settings.json    # GUI configuration template
├── requirements-enhanced.txt          # Additional dependencies
└── README-ENHANCED.md                # This file
```

## 🚀 Installation

1. **Install Enhanced Dependencies**:
```bash
pip install -r requirements-enhanced.txt
```

2. **Install Playwright Browsers** (if using Playwright features):
```bash
playwright install
```

3. **Create Configuration** (optional):
```bash
python unified_cli.py --create-default-config my-settings.json
```

## 📖 Usage Examples

### Basic Usage
```bash
# Extract courses with metrics
python unified_cli.py extract --metrics

# Enroll with custom configuration
python unified_cli.py --config my-settings.json enroll

# Combined extract and enroll
python unified_cli.py run --sites "Tutorial Bar" "Discudemy"
```

### Advanced Usage
```bash
# Test cookie extraction
python unified_cli.py --test-cookies --browser chrome

# Validate configuration
python unified_cli.py --validate-config settings.json

# Show statistics
python unified_cli.py --stats --days 14

# Check for updates
python unified_cli.py --update-check

# Enable structured logging
python unified_cli.py --structured-logging extract
```

### Configuration Examples
```bash
# Create default configuration
python unified_cli.py --create-default-config settings.json

# Use specific browser for cookies
python unified_cli.py --browser firefox run

# Dry run (show what would be enrolled)
python unified_cli.py enroll --dry-run
```

## 🔧 Configuration

### Default Configuration Structure
```json
{
  "email": "",
  "password": "",
  "use_browser_cookies": true,
  "browser_type": "chrome",
  "sites": { "Tutorial Bar": true, "Discudemy": true },
  "categories": { "development": true, "business": true },
  "languages": { "en": true, "es": false },
  "filters": {
    "min_rating": 4.0,
    "min_reviews": 10,
    "course_update_threshold_months": 24
  },
  "exclusions": {
    "title_exclude": ["test", "demo"],
    "instructor_exclude": ["bad-instructor"]
  }
}
```

### Environment Variables
- `UDEMY_EMAIL`: Default email for authentication
- `UDEMY_PASSWORD`: Default password for authentication
- `UDEMY_BROWSER`: Preferred browser for cookie extraction
- `UDEMY_DEBUG`: Enable debug mode (true/false)

## 🏗️ Integration

### With Existing Watchtower Architecture
The enhanced Udemy Universal Miner integrates seamlessly with the existing Watchtower platform:

1. **ETL Pipeline Integration**: Can be used as an ETL component
2. **Data Model Compatibility**: Follows Watchtower's data model patterns
3. **Logging Integration**: Uses Watchtower's logging system
4. **Configuration Management**: Compatible with Watchtower's configuration system

### Batch Script Integration
The enhanced version is integrated into the main batch script:
```bash
# In run_all_etl.bat
start /B %PYTHON_CMD% src/miners/udemy-universal/unified_cli.py run --metrics
```

## 🔍 Key Improvements

### Performance Enhancements
- **Concurrent Processing**: Multi-threaded scraping with better error handling
- **Efficient Filtering**: Optimized filtering algorithms
- **Caching**: Intelligent caching for repeated operations
- **Resource Management**: Better memory and CPU usage

### Reliability Improvements
- **Robust Error Handling**: Comprehensive error recovery mechanisms
- **Fallback Systems**: Multiple fallback options for critical operations
- **Validation**: Extensive input validation and sanity checks
- **Monitoring**: Built-in monitoring and alerting capabilities

### User Experience
- **Intuitive CLI**: Easy-to-use command-line interface
- **Rich Feedback**: Detailed progress and status information
- **Comprehensive Help**: Built-in help and documentation
- **Flexible Configuration**: Multiple configuration options

## 🧪 Testing

### Test Cookie Extraction
```bash
python unified_cli.py --test-cookies
```

### Validate Configuration
```bash
python unified_cli.py --validate-config settings.json
```

### Dry Run
```bash
python unified_cli.py enroll --dry-run
```

## 🐛 Troubleshooting

### Common Issues

1. **Cookie Extraction Failed**:
   - Ensure browser is installed and has visited Udemy
   - Try different browsers: `--browser firefox`
   - Check browser permissions

2. **Configuration Validation Errors**:
   - Use `--validate-config` to check configuration
   - Generate default: `--create-default-config`

3. **Update Check Failed**:
   - Check internet connection
   - Verify GitHub API access

4. **Dependencies Missing**:
   - Install enhanced requirements: `pip install -r requirements-enhanced.txt`
   - Install Playwright browsers: `playwright install`

## 📊 Monitoring

The enhanced version includes comprehensive monitoring:
- **Session Tracking**: All operations are tracked
- **Performance Metrics**: Timing and success rates
- **Error Reporting**: Detailed error logs with context
- **Statistics**: Historical data and trends

## 🔐 Security

- **Cookie Security**: Secure handling of authentication cookies
- **Configuration Safety**: Validation prevents malicious configurations
- **Input Sanitization**: All inputs are properly sanitized
- **Error Privacy**: Sensitive information is not logged

## 📈 Future Enhancements

- **GUI Integration**: Web-based interface for easier management
- **Database Support**: Persistent storage for statistics and configuration
- **API Integration**: REST API for external integrations
- **Machine Learning**: AI-powered course recommendations
- **Multi-Account Support**: Support for multiple Udemy accounts
- **Cloud Integration**: Cloud-based storage and processing

## 🤝 Contributing

This enhanced version maintains compatibility with the original while adding significant improvements. Contributions are welcome for:
- Additional browser support
- New filtering criteria
- Performance optimizations
- Documentation improvements
- Bug fixes and testing

## 📝 License

This enhanced version maintains the same license as the original Watchtower project and incorporates improvements inspired by the MIT-licensed techtanic/Discounted-Udemy-Course-Enroller project.

---

**Note**: This enhanced version is designed to be backward compatible with existing configurations while providing significant improvements in functionality, reliability, and user experience.

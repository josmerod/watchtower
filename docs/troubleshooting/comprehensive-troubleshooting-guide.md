# Comprehensive Troubleshooting Guide

This guide provides detailed solutions for common issues you might encounter while using Watchtower. It's organized by component and includes diagnostic steps, root cause analysis, and step-by-step solutions.

## 📋 Quick Issue Index

**Critical Issues (System Won't Start)**
- [Installation and Setup Problems](#installation-and-setup-problems)
- [Permission and Access Issues](#permission-and-access-issues)
- [Configuration Errors](#configuration-errors)

**Runtime Issues (System Runs But Has Problems)**
- [ETL Pipeline Failures](#etl-pipeline-failures)
- [Watcher System Issues](#watcher-system-issues)
- [Dashboard and UI Problems](#dashboard-and-ui-problems)

**Performance Issues**
- [Slow Performance and Timeouts](#slow-performance-and-timeouts)
- [Memory and Resource Problems](#memory-and-resource-problems)
- [Network and Connectivity Issues](#network-and-connectivity-issues)

**Data Issues**
- [Data Quality and Validation Problems](#data-quality-and-validation-problems)
- [File System and Storage Issues](#file-system-and-storage-issues)

---

## 🚨 Installation and Setup Problems

### Problem: "ModuleNotFoundError: No module named 'src'"

**Symptoms:**
```
Traceback (most recent call last):
  File "my_etl.py", line 1, in <module>
    from src.etl.base import SimpleETL
ModuleNotFoundError: No module named 'src'
```

**Root Cause:** Python can't find the Watchtower source modules.

**Diagnostic Steps:**
```bash
# 1. Check current directory
pwd
ls -la

# 2. Check if you're in the right location
ls -la src/

# 3. Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Solutions:**

**Solution 1: Navigate to Project Root**
```bash
cd /path/to/watchtower
python my_etl.py
```

**Solution 2: Install in Development Mode**
```bash
# From project root
pip install -e .

# Or with Poetry
poetry install
```

**Solution 3: Add to PYTHONPATH**
```bash
# Linux/macOS
export PYTHONPATH="${PYTHONPATH}:/path/to/watchtower"

# Windows
set PYTHONPATH=%PYTHONPATH%;C:\path\to\watchtower
```

**Solution 4: Use Absolute Imports**
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.etl.base import SimpleETL
```

### Problem: Poetry Virtual Environment Issues

**Symptoms:**
```bash
$ poetry shell
The virtual environment was not found!
```

**Diagnostic Steps:**
```bash
# Check Poetry configuration
poetry config --list

# Check if environment exists
poetry env list

# Check project configuration
cat pyproject.toml
```

**Solutions:**

**Solution 1: Recreate Environment**
```bash
# Remove existing environment
poetry env remove python

# Create new environment
poetry install

# Activate environment
poetry shell
```

**Solution 2: Specify Python Version**
```bash
# Use specific Python version
poetry env use python3.10
poetry install
```

**Solution 3: Clear Poetry Cache**
```bash
poetry cache clear pypi --all
poetry install --no-cache
```

### Problem: Playwright Browser Installation Fails

**Symptoms:**
```
Error: Failed to download browser
Permission denied: /home/user/.cache/ms-playwright
```

**Diagnostic Steps:**
```bash
# Check Playwright installation
playwright --version

# Check permissions
ls -la ~/.cache/
ls -la ~/.cache/ms-playwright/

# Check disk space
df -h
```

**Solutions:**

**Solution 1: Fix Permissions**
```bash
# Fix cache directory permissions
sudo chown -R $USER:$USER ~/.cache/ms-playwright/

# Reinstall browsers
playwright install
```

**Solution 2: Use Different Installation Location**
```bash
# Set custom browser directory
export PLAYWRIGHT_BROWSERS_PATH=/path/to/custom/browsers
playwright install
```

**Solution 3: Manual Browser Installation**
```bash
# Install specific browsers only
playwright install chromium
playwright install firefox

# Verify installation
playwright install --dry-run
```

---

## ⚙️ Configuration Errors

### Problem: "Configuration file not found" or Invalid Settings

**Symptoms:**
```
FileNotFoundError: Configuration file '.env' not found
ValidationError: Invalid configuration for 'database.url'
```

**Diagnostic Steps:**
```bash
# Check for configuration files
ls -la .env*
ls -la config/

# Check environment variables
env | grep -i watchtower
env | grep -i database

# Validate configuration
python -c "from src.config.settings import get_settings; print(get_settings())"
```

**Solutions:**

**Solution 1: Create Configuration File**
```bash
# Copy template
cp .env.template .env

# Edit configuration
nano .env  # or your preferred editor
```

**Solution 2: Set Required Environment Variables**
```bash
# Set essential variables
export DATABASE_URL="sqlite:///data/watchtower.db"
export LOG_LEVEL="INFO"
export DEBUG="false"

# For persistent settings, add to ~/.bashrc or ~/.zshrc
echo 'export DATABASE_URL="sqlite:///data/watchtower.db"' >> ~/.bashrc
```

**Solution 3: Use Default Configuration**
```python
# In your Python script, use defaults
from src.config.settings import get_settings

try:
    settings = get_settings()
except Exception as e:
    print(f"Configuration error: {e}")
    # Use fallback configuration
    settings = get_settings_for_testing()
```

### Problem: Database Connection Issues

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
Connection refused: Could not connect to PostgreSQL server
```

**Diagnostic Steps:**
```bash
# Check database configuration
python -c "from src.config.settings import get_settings; print(get_settings().database.url)"

# Test database connectivity
python -c "
import sqlalchemy as sa
engine = sa.create_engine('your_database_url')
print(engine.execute('SELECT 1').scalar())
"

# Check database file permissions (SQLite)
ls -la data/watchtower.db

# Check database server status (PostgreSQL/MySQL)
systemctl status postgresql
# or
brew services list | grep postgres
```

**Solutions:**

**Solution 1: Fix SQLite Database Issues**
```bash
# Create data directory
mkdir -p data/

# Fix permissions
chmod 755 data/
touch data/watchtower.db
chmod 664 data/watchtower.db

# Use absolute path in configuration
export DATABASE_URL="sqlite:////absolute/path/to/watchtower/data/watchtower.db"
```

**Solution 2: Fix PostgreSQL Connection**
```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE watchtower;"
sudo -u postgres psql -c "CREATE USER watchtower_user WITH PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE watchtower TO watchtower_user;"

# Update connection string
export DATABASE_URL="postgresql://watchtower_user:password@localhost/watchtower"
```

**Solution 3: Use In-Memory Database for Testing**
```python
# Temporary solution for development
from src.config.settings import get_settings

settings = get_settings()
settings.database.url = "sqlite:///:memory:"
```

---

## 🔄 ETL Pipeline Failures

### Problem: ETL Pipeline Crashes During Execution

**Symptoms:**
```
[ERROR] ETL pipeline failed: HTTPError: 404 Client Error
[ERROR] Transformation failed: KeyError: 'expected_field'
[ERROR] Memory allocation failed
```

**Diagnostic Steps:**
```bash
# Check ETL logs
ls -la logs/
tail -50 logs/etl.log

# Check recent ETL runs
ls -la data/*/checkpoints/

# Check system resources
top
free -h
df -h

# Test individual ETL components
python -c "
from your_etl import YourETL
etl = YourETL()
data = etl.extract()
print(f'Extracted {len(data)} records')
"
```

**Solutions:**

**Solution 1: Fix HTTP/API Issues**
```python
# Add robust error handling to your ETL
def extract(self) -> List[Dict[str, Any]]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

**Solution 2: Fix Data Transformation Issues**
```python
# Add defensive programming
def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    transformed = []
    for item in data:
        try:
            # Validate required fields
            required_fields = ['id', 'title', 'url']
            if not all(field in item for field in required_fields):
                self.logger.warning(f"Skipping item with missing fields: {item}")
                continue
            
            # Transform with defaults
            transformed_item = {
                'id': item.get('id', ''),
                'title': item.get('title', 'No Title'),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                # Add timestamp
                'processed_at': datetime.now().isoformat()
            }
            transformed.append(transformed_item)
            
        except Exception as e:
            self.logger.error(f"Failed to transform item: {e}")
            continue  # Skip problematic items
    
    return transformed
```

**Solution 3: Fix Memory Issues**
```python
# Process data in smaller batches
class MemoryEfficientETL(SimpleETL):
    def __init__(self):
        super().__init__(
            batch_size=100,  # Smaller batches
            enable_checkpointing=True  # Enable recovery
        )
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Process in sub-batches
        return self.process_in_batches(data, self._transform_batch, batch_size=25)
    
    def _transform_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Process smaller batch
        return [self._transform_item(item) for item in batch]
```

### Problem: ETL Gets Stuck or Runs Forever

**Symptoms:**
- ETL process appears to hang
- No log output for extended periods
- CPU usage is high but no progress

**Diagnostic Steps:**
```bash
# Check running processes
ps aux | grep python
htop

# Check network connections
netstat -an | grep python

# Check file descriptors
lsof -p <pid_of_etl_process>

# Monitor ETL progress
tail -f logs/etl.log
```

**Solutions:**

**Solution 1: Add Timeouts**
```python
import signal

class TimeoutETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.timeout = 300  # 5 minutes
    
    def extract(self) -> List[Dict[str, Any]]:
        # Set alarm for timeout
        signal.alarm(self.timeout)
        try:
            data = self._extract_data()
            signal.alarm(0)  # Cancel alarm
            return data
        except Exception as e:
            signal.alarm(0)  # Cancel alarm
            raise
```

**Solution 2: Add Progress Monitoring**
```python
def extract(self) -> List[Dict[str, Any]]:
    sources = self.get_sources()
    all_data = []
    
    for i, source in enumerate(sources):
        self.logger.info(f"Processing source {i+1}/{len(sources)}: {source}")
        
        start_time = time.time()
        source_data = self._extract_from_source(source)
        duration = time.time() - start_time
        
        self.logger.info(f"Extracted {len(source_data)} records in {duration:.2f}s")
        all_data.extend(source_data)
        
        # Heartbeat to show progress
        if i % 10 == 0:
            self.logger.info(f"Progress: {i}/{len(sources)} sources processed")
    
    return all_data
```

**Solution 3: Implement Circuit Breaker**
```python
class CircuitBreakerETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.failure_count = 0
        self.failure_threshold = 5
        self.circuit_open = False
    
    def extract(self) -> List[Dict[str, Any]]:
        if self.circuit_open:
            raise Exception("Circuit breaker is open - too many failures")
        
        try:
            data = self._extract_data()
            self.failure_count = 0  # Reset on success
            return data
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
                self.logger.error("Circuit breaker opened due to repeated failures")
            raise
```

---

## 👁️ Watcher System Issues

### Problem: Watchers Not Detecting Changes

**Symptoms:**
- Watcher runs without errors but doesn't trigger alerts
- Changes are visible manually but not detected by watcher
- State file shows old timestamps

**Diagnostic Steps:**
```bash
# Check watcher state
cat data/watchers/your_watcher/state.json

# Check watcher events
ls -la data/watchers/your_watcher/events/

# Check watcher logs
grep "your_watcher" logs/watchers.log

# Test watcher manually
python -c "
from your_watcher import YourWatcher
watcher = YourWatcher()
current_value = watcher.extract_value(watcher.fetch_page())
print(f'Current value: {current_value}')
"
```

**Solutions:**

**Solution 1: Fix Value Extraction**
```python
def extract_value(self, html_content: str) -> Any:
    from bs4 import BeautifulSoup
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Add debugging
        self.logger.debug(f"HTML content length: {len(html_content)}")
        
        # More robust element finding
        element = soup.find('div', class_='target-class')
        if not element:
            # Try alternative selectors
            element = soup.find('span', class_='alternative-class')
        
        if not element:
            self.logger.warning("Target element not found in HTML")
            return None
        
        value = element.get_text().strip()
        self.logger.debug(f"Extracted value: {value}")
        
        return value
        
    except Exception as e:
        self.logger.error(f"Failed to extract value: {e}")
        return None
```

**Solution 2: Improve Change Detection**
```python
def has_changed(self, old_value: Any, new_value: Any) -> bool:
    # Handle None values
    if old_value is None and new_value is None:
        return False
    if old_value is None or new_value is None:
        return new_value is not None  # Only trigger if we have new data
    
    # Normalize values before comparison
    old_normalized = self._normalize_value(old_value)
    new_normalized = self._normalize_value(new_value)
    
    # Log comparison for debugging
    self.logger.debug(f"Comparing: '{old_normalized}' vs '{new_normalized}'")
    
    return old_normalized != new_normalized

def _normalize_value(self, value: Any) -> str:
    """Normalize value for comparison"""
    if value is None:
        return ""
    
    # Convert to string and clean
    str_value = str(value).strip().lower()
    
    # Remove extra whitespace
    import re
    str_value = re.sub(r'\s+', ' ', str_value)
    
    return str_value
```

**Solution 3: Add More Detailed Logging**
```python
def check(self) -> None:
    """Enhanced check with detailed logging"""
    self.logger.info(f"Starting check for {self.name}")
    
    try:
        # Fetch page
        html_content = self.fetch_page()
        self.logger.info(f"Fetched {len(html_content)} bytes from {self.url}")
        
        # Extract value
        new_value = self.extract_value(html_content)
        self.logger.info(f"Extracted value: {new_value}")
        
        # Load previous state
        old_value = self._load_state().get('last_value')
        self.logger.info(f"Previous value: {old_value}")
        
        # Check for changes
        changed = self.has_changed(old_value, new_value)
        self.logger.info(f"Change detected: {changed}")
        
        if changed:
            self.trigger_alarm(old_value, new_value)
        
        # Save new state
        self._save_state({
            'last_check': datetime.now().isoformat(),
            'last_value': new_value,
            'check_count': self._load_state().get('check_count', 0) + 1
        })
        
    except Exception as e:
        self.logger.error(f"Check failed: {e}", exc_info=True)
```

### Problem: Watcher Timeout or Connection Issues

**Symptoms:**
```
[ERROR] Timeout: The read operation timed out
[ERROR] Connection failed: [Errno 111] Connection refused
[ERROR] SSL verification failed
```

**Solutions:**

**Solution 1: Adjust Request Settings**
```python
def fetch_page(self) -> str:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    # Create session with retries
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Request with longer timeout
    response = session.get(
        self.url,
        timeout=(10, 30),  # (connect_timeout, read_timeout)
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; Watchtower/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    
    response.raise_for_status()
    return response.text
```

**Solution 2: Handle SSL Issues**
```python
def fetch_page(self) -> str:
    import requests
    import ssl
    
    try:
        # Try with normal SSL verification
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return response.text
        
    except requests.exceptions.SSLError as e:
        self.logger.warning(f"SSL verification failed, trying without verification: {e}")
        
        # Fallback to no SSL verification (not recommended for production)
        response = requests.get(self.url, timeout=30, verify=False)
        response.raise_for_status()
        return response.text
```

---

## 📊 Dashboard and UI Problems

### Problem: Streamlit Dashboard Won't Start

**Symptoms:**
```
ModuleNotFoundError: No module named 'streamlit'
Error: Port 8501 is already in use
```

**Diagnostic Steps:**
```bash
# Check if Streamlit is installed
pip list | grep streamlit

# Check if port is in use
lsof -i :8501
netstat -an | grep 8501

# Try starting with different port
streamlit run src/web/fullstreamlit/app.py --server.port 8502
```

**Solutions:**

**Solution 1: Install Missing Dependencies**
```bash
# Install Streamlit
pip install streamlit

# Or with Poetry
poetry add streamlit

# Install all dashboard dependencies
pip install streamlit plotly pandas altair
```

**Solution 2: Fix Port Conflicts**
```bash
# Find process using port 8501
lsof -ti:8501

# Kill the process (replace PID with actual process ID)
kill -9 <PID>

# Or use different port
streamlit run src/web/fullstreamlit/app.py --server.port 8502
```

**Solution 3: Fix Dashboard Code Issues**
```python
# Add error handling to dashboard
import streamlit as st
import traceback

def main():
    try:
        st.title("Watchtower Dashboard")
        
        # Your dashboard code here
        display_etl_metrics()
        display_watcher_status()
        
    except Exception as e:
        st.error(f"Dashboard error: {e}")
        st.text("Traceback:")
        st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
```

### Problem: Dashboard Shows No Data

**Symptoms:**
- Dashboard loads but shows empty charts
- "No data available" messages
- Outdated information displayed

**Solutions:**

**Solution 1: Check Data File Paths**
```python
# In your dashboard code, add debugging
import os
import streamlit as st

def load_etl_data():
    data_path = "data/your_etl_name/output.json"
    
    st.write(f"Looking for data at: {os.path.abspath(data_path)}")
    st.write(f"File exists: {os.path.exists(data_path)}")
    
    if os.path.exists(data_path):
        st.write(f"File size: {os.path.getsize(data_path)} bytes")
        with open(data_path) as f:
            data = json.load(f)
        st.write(f"Records loaded: {len(data)}")
        return data
    else:
        st.error("Data file not found")
        return []
```

**Solution 2: Add Data Refresh**
```python
# Add refresh button to dashboard
if st.button("Refresh Data"):
    st.cache_data.clear()  # Clear Streamlit cache
    st.experimental_rerun()  # Reload the app

# Or auto-refresh
import time
time.sleep(60)  # Wait 60 seconds
st.experimental_rerun()
```

---

## 🐌 Slow Performance and Timeouts

### Problem: ETL Pipelines Take Too Long

**Symptoms:**
- ETL runs for hours without completing
- High CPU/memory usage
- Frequent timeout errors

**Diagnostic Steps:**
```bash
# Profile ETL performance
python -m cProfile -o etl_profile.prof your_etl.py

# Analyze profile
python -c "
import pstats
p = pstats.Stats('etl_profile.prof')
p.sort_stats('cumulative').print_stats(20)
"

# Monitor system resources
htop
iotop  # If available
```

**Solutions:**

**Solution 1: Implement Parallel Processing**
```python
import concurrent.futures
from typing import List, Dict, Any

class ParallelETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.max_workers = 4
    
    def extract(self) -> List[Dict[str, Any]]:
        sources = self.get_sources()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all extraction tasks
            future_to_source = {
                executor.submit(self._extract_from_source, source): source
                for source in sources
            }
            
            all_data = []
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    data = future.result(timeout=60)
                    all_data.extend(data)
                    self.logger.info(f"Completed extraction from {source}")
                except Exception as e:
                    self.logger.error(f"Failed to extract from {source}: {e}")
        
        return all_data
```

**Solution 2: Optimize Database Operations**
```python
def load(self, data: List[Dict[str, Any]]) -> None:
    # Batch database operations
    batch_size = 1000
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        self._load_batch(batch)
        
        # Log progress
        if i % (batch_size * 10) == 0:
            self.logger.info(f"Loaded {i + len(batch)}/{len(data)} records")

def _load_batch(self, batch: List[Dict[str, Any]]) -> None:
    # Use bulk operations instead of individual inserts
    # This is database-specific
    pass
```

**Solution 3: Add Caching**
```python
from functools import lru_cache
import pickle
import os

class CachedETL(SimpleETL):
    @lru_cache(maxsize=100)
    def _fetch_url(self, url: str) -> str:
        """Cache URL responses"""
        return requests.get(url).text
    
    def extract(self) -> List[Dict[str, Any]]:
        cache_file = "cache/extract_cache.pkl"
        
        # Check if cached data is recent
        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < 3600:  # 1 hour cache
                self.logger.info("Using cached data")
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        # Extract fresh data
        data = self._extract_fresh_data()
        
        # Cache the results
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        
        return data
```

---

## 💾 Memory and Resource Problems

### Problem: Out of Memory Errors

**Symptoms:**
```
MemoryError: Unable to allocate array
Process killed (signal 9)
Python process consuming too much RAM
```

**Solutions:**

**Solution 1: Stream Processing**
```python
def transform_stream(self, data_source) -> Generator[Dict[str, Any], None, None]:
    """Process data as a stream instead of loading all into memory"""
    for item in data_source:
        try:
            transformed_item = self._transform_item(item)
            yield transformed_item
        except Exception as e:
            self.logger.warning(f"Failed to transform item: {e}")
            continue

def load_stream(self, data_stream) -> None:
    """Load data from stream in batches"""
    batch = []
    batch_size = 100
    
    for item in data_stream:
        batch.append(item)
        
        if len(batch) >= batch_size:
            self._load_batch(batch)
            batch = []  # Clear batch to free memory
    
    # Load remaining items
    if batch:
        self._load_batch(batch)
```

**Solution 2: Memory Monitoring**
```python
import psutil
import gc

class MemoryAwareETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.memory_threshold = 80  # Percent
    
    def _check_memory(self):
        """Check memory usage and clean up if needed"""
        memory_percent = psutil.virtual_memory().percent
        
        if memory_percent > self.memory_threshold:
            self.logger.warning(f"Memory usage high: {memory_percent}%")
            gc.collect()  # Force garbage collection
            
            # Check again
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                raise MemoryError(f"Memory usage critical: {memory_percent}%")
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self._check_memory()
        
        # Process in smaller chunks
        chunk_size = 1000
        result = []
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            transformed_chunk = self._transform_chunk(chunk)
            result.extend(transformed_chunk)
            
            # Clean up after each chunk
            del chunk, transformed_chunk
            gc.collect()
            self._check_memory()
        
        return result
```

---

## 🌐 Network and Connectivity Issues

### Problem: Frequent Connection Timeouts

**Symptoms:**
```
requests.exceptions.Timeout: HTTPSConnectionPool
requests.exceptions.ConnectionError: Max retries exceeded
```

**Solutions:**

**Solution 1: Implement Exponential Backoff**
```python
import time
import random

def fetch_with_backoff(self, url: str, max_retries: int = 5) -> str:
    """Fetch URL with exponential backoff retry logic"""
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=(10, 30))
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise  # Last attempt, re-raise the exception
            
            # Calculate backoff delay
            base_delay = 2 ** attempt
            jitter = random.uniform(0, 1)
            delay = base_delay + jitter
            
            self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
            time.sleep(delay)
```

**Solution 2: Connection Pooling**
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedHTTPETL(SimpleETL):
    def __init__(self):
        super().__init__()
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session"""
        session = requests.Session()
        
        # Retry configuration
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        # Connection adapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Default headers
        session.headers.update({
            'User-Agent': 'Watchtower/1.0 (automated data collection)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def fetch_page(self, url: str) -> str:
        """Fetch page using optimized session"""
        response = self.session.get(url, timeout=(10, 30))
        response.raise_for_status()
        return response.text
```

---

## 📁 Data Quality and Validation Problems

### Problem: Invalid or Corrupt Data

**Symptoms:**
- JSON parsing errors
- Schema validation failures
- Inconsistent data formats

**Solutions:**

**Solution 1: Robust Data Validation**
```python
from pydantic import BaseModel, ValidationError, Field
from typing import Optional, List
from datetime import datetime

class ArticleModel(BaseModel):
    """Data model for article validation"""
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., regex=r'^https?://.+')
    content: Optional[str] = Field(None, max_length=10000)
    published_date: Optional[datetime] = None
    source: str = Field(..., min_length=1)

class ValidatedETL(SimpleETL):
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated_data = []
        validation_errors = 0
        
        for item in data:
            try:
                # Validate using Pydantic model
                validated_item = ArticleModel(**item)
                validated_data.append(validated_item.dict())
                
            except ValidationError as e:
                validation_errors += 1
                self.logger.warning(f"Validation failed for item: {e}")
                
                # Try to fix common issues
                fixed_item = self._fix_common_issues(item)
                if fixed_item:
                    try:
                        validated_item = ArticleModel(**fixed_item)
                        validated_data.append(validated_item.dict())
                    except ValidationError:
                        self.logger.error(f"Could not fix item: {item}")
        
        self.logger.info(f"Validation complete: {len(validated_data)} valid, {validation_errors} errors")
        return validated_data
    
    def _fix_common_issues(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to fix common data issues"""
        fixed = item.copy()
        
        # Fix missing required fields
        if not fixed.get('id'):
            fixed['id'] = self._generate_id(fixed)
        
        if not fixed.get('title'):
            fixed['title'] = fixed.get('url', 'Untitled')[:100]
        
        # Clean URLs
        url = fixed.get('url', '')
        if url and not url.startswith(('http://', 'https://')):
            fixed['url'] = 'https://' + url
        
        # Truncate long fields
        if fixed.get('title') and len(fixed['title']) > 500:
            fixed['title'] = fixed['title'][:497] + '...'
        
        return fixed
```

**Solution 2: Data Quality Metrics**
```python
def analyze_data_quality(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze data quality and generate report"""
    
    total_records = len(data)
    quality_report = {
        'total_records': total_records,
        'missing_fields': {},
        'data_types': {},
        'duplicates': 0,
        'quality_score': 0.0
    }
    
    if total_records == 0:
        return quality_report
    
    # Check for missing fields
    required_fields = ['id', 'title', 'url']
    for field in required_fields:
        missing_count = sum(1 for item in data if not item.get(field))
        quality_report['missing_fields'][field] = {
            'count': missing_count,
            'percentage': (missing_count / total_records) * 100
        }
    
    # Check for duplicates
    urls = [item.get('url') for item in data if item.get('url')]
    quality_report['duplicates'] = len(urls) - len(set(urls))
    
    # Calculate quality score
    missing_percentage = sum(
        report['percentage'] for report in quality_report['missing_fields'].values()
    ) / len(required_fields)
    
    duplicate_percentage = (quality_report['duplicates'] / total_records) * 100
    quality_report['quality_score'] = max(0, 100 - missing_percentage - duplicate_percentage)
    
    return quality_report
```

---

## 🚨 Emergency Recovery Procedures

### Complete System Reset

If Watchtower is completely broken, follow these steps:

```bash
# 1. Stop all running processes
pkill -f "python.*watchtower"
pkill -f "streamlit"

# 2. Backup important data
cp -r data/ data_backup_$(date +%Y%m%d_%H%M%S)/

# 3. Reset virtual environment
poetry env remove python
poetry install

# 4. Clear all caches
poetry cache clear pypi --all
rm -rf ~/.cache/ms-playwright
rm -rf __pycache__/
rm -rf src/**/__pycache__/

# 5. Reinstall browsers
playwright install

# 6. Test basic functionality
python -c "from src.config.settings import get_settings; print('Configuration OK')"
python src/etl/news/news_get_ycombinator.py

# 7. Restart dashboard
streamlit run src/web/fullstreamlit/app.py
```

### Data Recovery

If data is corrupted or missing:

```bash
# 1. Check for checkpoints
ls -la data/*/checkpoints/

# 2. Restore from latest checkpoint
python -c "
from src.etl.your_etl import YourETL
etl = YourETL()
etl.restore_from_checkpoint('latest')
"

# 3. Verify data integrity
python -c "
import json
with open('data/your_etl/output.json') as f:
    data = json.load(f)
    print(f'Records: {len(data)}')
    print(f'Sample: {data[0] if data else None}')
"
```

---

## 📞 Getting Additional Help

### Before Asking for Help

1. **Check logs**: Look in `logs/` directory for error messages
2. **Try diagnostics**: Run the diagnostic commands provided above
3. **Search issues**: Check [GitHub Issues](https://github.com/josmerod/watchtower/issues)
4. **Review documentation**: Check relevant tutorial sections

### Creating Effective Bug Reports

When reporting issues, include:

```
**Environment:**
- OS: [e.g., Ubuntu 20.04, Windows 10, macOS 12.6]
- Python version: [output of `python --version`]
- Watchtower version: [git commit hash]
- Installation method: [Poetry, pip, etc.]

**Issue Description:**
- What you were trying to do
- What you expected to happen
- What actually happened
- Error messages (full traceback)

**Steps to Reproduce:**
1. Step one
2. Step two
3. Error occurs

**Diagnostic Information:**
- Relevant log files
- Output of diagnostic commands
- Configuration files (remove sensitive data)

**Attempted Solutions:**
- What you tried from this guide
- Other troubleshooting steps
```

### Community Resources

- **GitHub Issues**: [Report bugs and request features](https://github.com/josmerod/watchtower/issues)
- **Documentation**: [Complete documentation](../../README.md)
- **Tutorials**: [Step-by-step guides](../tutorials/)
- **API Reference**: [Technical documentation](../development/api-reference.md)

---

## ✅ Prevention Best Practices

To avoid common issues:

1. **Use virtual environments** for isolation
2. **Keep dependencies updated** regularly
3. **Monitor system resources** during ETL runs
4. **Implement proper error handling** in custom code
5. **Set up monitoring and alerting** for production
6. **Regular backups** of data and configuration
7. **Test changes** in development before production
8. **Keep logs** for troubleshooting

Remember: Most issues have solutions, and the Watchtower community is here to help! 🤝
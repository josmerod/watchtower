# Frequently Asked Questions (FAQ)

This comprehensive FAQ addresses common questions about Watchtower installation, usage, troubleshooting, and advanced features. Find quick answers to help you get the most out of your Watchtower experience.

## 📋 Quick Navigation

- [🚀 Getting Started](#-getting-started)
- [⚙️ Installation & Setup](#️-installation--setup)
- [📊 ETL Pipelines](#-etl-pipelines)
- [👁️ Watchers](#️-watchers)
- [🎛️ Dashboard & UI](#️-dashboard--ui)
- [🔧 Configuration](#-configuration)
- [🐛 Troubleshooting](#-troubleshooting)
- [⚡ Performance](#-performance)
- [🔒 Security](#-security)
- [🚀 Deployment](#-deployment)
- [🤝 Contributing](#-contributing)

---

## 🚀 Getting Started

### Q: What is Watchtower and what can I do with it?

**A:** Watchtower is a comprehensive data monitoring and ETL (Extract, Transform, Load) framework designed for:

- **Automated Data Collection**: Scrape data from websites, RSS feeds, and APIs
- **Website Monitoring**: Watch websites for changes and get alerts
- **Data Processing**: Clean, transform, and validate collected data
- **Data Visualization**: View data through an interactive web dashboard
- **Workflow Automation**: Schedule and orchestrate data pipelines

**Common Use Cases:**
- News aggregation and monitoring
- Price tracking for e-commerce
- Social media sentiment analysis
- DevOps metrics collection
- Research data gathering
- Competitor analysis

### Q: Do I need programming experience to use Watchtower?

**A:** Basic Python knowledge is helpful but not strictly required:

**For Basic Usage:**
- Following tutorials and examples requires minimal Python experience
- Configuration is mostly through files and environment variables
- Dashboard usage is point-and-click

**For Custom Development:**
- Python programming skills needed for custom ETL pipelines
- Understanding of web technologies helpful for advanced watchers
- Knowledge of data formats (JSON, CSV) is beneficial

**Getting Started Path:**
1. Start with the [Complete Beginner's Guide](tutorials/getting-started/complete-beginners-guide.md)
2. Use provided examples as templates
3. Gradually customize for your needs
4. Learn Python as you go

### Q: What are the main differences between ETL and Watchers?

**A:** 

| ETL Pipelines | Watchers |
|---------------|----------|
| **Purpose**: Data collection and processing | **Purpose**: Change detection and monitoring |
| **Runs**: On-demand or scheduled batches | **Runs**: Continuous monitoring |
| **Output**: Processed data files/databases | **Output**: Alerts and change events |
| **Use Case**: "Get all news articles daily" | **Use Case**: "Alert me when price changes" |
| **Data Volume**: Large datasets | **Data Volume**: Single values or small data |

**When to Use Each:**
- **ETL**: Regular data collection, analysis, reporting
- **Watchers**: Real-time monitoring, alerts, change tracking

---

## ⚙️ Installation & Setup

### Q: What are the system requirements for Watchtower?

**A:** 

**Minimum Requirements:**
- Python 3.10 or higher
- 4GB RAM
- 1GB free disk space
- Internet connection

**Recommended:**
- Python 3.11+
- 8GB RAM
- 10GB free disk space
- SSD storage for better performance

**Operating Systems:**
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+, CentOS 8+, etc.)

### Q: Should I use Poetry or pip for installation?

**A:** **Poetry is recommended** for these reasons:

**Poetry Advantages:**
- Better dependency management
- Automatic virtual environment handling
- Consistent environments across machines
- Lock file for reproducible builds

**Use pip if:**
- You're already familiar with pip/venv
- Working in a constrained environment
- Corporate restrictions on package managers

**Installation Commands:**
```bash
# Poetry (recommended)
poetry install && poetry shell

# pip alternative
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Q: I'm getting "Playwright browser not found" errors. How do I fix this?

**A:** This is a common issue with several solutions:

**Solution 1: Install Browsers**
```bash
playwright install
```

**Solution 2: Install Specific Browsers**
```bash
playwright install chromium
playwright install firefox
```

**Solution 3: Fix Permissions (Linux/macOS)**
```bash
sudo chown -R $USER:$USER ~/.cache/ms-playwright/
playwright install
```

**Solution 4: Manual Installation**
```bash
# Remove existing installation
rm -rf ~/.cache/ms-playwright/

# Reinstall
playwright install chromium
```

**Verification:**
```bash
playwright --version
python -c "from playwright.sync_api import sync_playwright; print('Playwright working')"
```

### Q: Can I run Watchtower on Windows?

**A:** Yes! Watchtower fully supports Windows:

**Windows-Specific Setup:**
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install Python from python.org (check "Add to PATH")
# Clone and setup
git clone https://github.com/josmerod/watchtower.git
cd watchtower
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

**Common Windows Issues:**
- **Long paths**: Enable long path support in Windows settings
- **Antivirus**: Add project folder to antivirus exclusions
- **Firewall**: Allow Python/Streamlit through firewall

---

## 📊 ETL Pipelines

### Q: How do I create my first ETL pipeline?

**A:** Follow this step-by-step process:

**1. Choose Your ETL Type:**
```python
from src.etl.base import SimpleETL  # For basic data processing
from src.etl.base import DataFrameETL  # For analytics with export features
```

**2. Create Your ETL Class:**
```python
class MyFirstETL(SimpleETL):
    def __init__(self):
        super().__init__(name="my_first_etl", description="My first pipeline")
    
    def extract(self) -> List[Dict[str, Any]]:
        # Get your data (API, RSS, files, etc.)
        return data
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Clean and process data
        return processed_data
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        # Save data (JSON, CSV, database)
        self.save_as_json(data, "output.json")
```

**3. Run Your ETL:**
```python
etl = MyFirstETL()
metrics = etl.run()
print(f"Processed {metrics.records_loaded} records")
```

**Complete Tutorial:** [Your First ETL Pipeline](tutorials/etl/first-etl-pipeline.md)

### Q: How do I handle errors in ETL pipelines?

**A:** Watchtower provides multiple error handling strategies:

**1. Automatic Retries:**
```python
class RobustETL(SimpleETL):
    def __init__(self):
        super().__init__(
            max_retries=3,        # Retry failed operations
            retry_delay=5,        # Wait 5 seconds between retries
            enable_checkpointing=True  # Save progress
        )
```

**2. Error Isolation:**
```python
def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    successful_items = []
    
    for item in data:
        try:
            transformed = self._transform_item(item)
            successful_items.append(transformed)
        except Exception as e:
            self.logger.warning(f"Failed to transform item: {e}")
            # Continue processing other items
    
    return successful_items
```

**3. Circuit Breaker Pattern:**
```python
from src.utils.circuit_breaker import CircuitBreaker

@CircuitBreaker(failure_threshold=5, reset_timeout=300)
def extract_from_api(self, url: str) -> List[Dict[str, Any]]:
    # This will stop calling the API if it fails 5 times
    return requests.get(url).json()
```

### Q: How can I speed up slow ETL pipelines?

**A:** Several optimization strategies:

**1. Batch Processing:**
```python
def __init__(self):
    super().__init__(batch_size=500)  # Process 500 items at once
```

**2. Parallel Processing:**
```python
import concurrent.futures

def extract(self) -> List[Dict[str, Any]]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(self._extract_source, source) for source in sources]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    return results
```

**3. Caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def _fetch_data(self, url: str) -> str:
    return requests.get(url).text
```

**4. Incremental Processing:**
```python
def extract(self) -> List[Dict[str, Any]]:
    last_run = self._get_last_run_timestamp()
    return self._extract_since(last_run)  # Only get new data
```

### Q: How do I save ETL data to a database?

**A:** Watchtower supports multiple database options:

**1. SQLite (Default):**
```python
def load(self, data: List[Dict[str, Any]]) -> None:
    import sqlite3
    
    conn = sqlite3.connect('data/watchtower.db')
    # Insert data into database
    conn.executemany("INSERT INTO articles VALUES (?, ?, ?)", data)
    conn.commit()
    conn.close()
```

**2. PostgreSQL:**
```python
def load(self, data: List[Dict[str, Any]]) -> None:
    import psycopg2
    
    conn = psycopg2.connect(self.settings.database.url)
    cursor = conn.cursor()
    # Bulk insert
    psycopg2.extras.execute_batch(cursor, "INSERT INTO articles VALUES %s", data)
    conn.commit()
    conn.close()
```

**3. Using Pandas for Complex Databases:**
```python
def load(self, data: List[Dict[str, Any]]) -> None:
    import pandas as pd
    
    df = pd.DataFrame(data)
    df.to_sql('articles', self.database_engine, if_exists='append', index=False)
```

---

## 👁️ Watchers

### Q: How do I create a watcher to monitor website changes?

**A:** Here's a complete example:

```python
from src.watchers.base_watcher import BaseWatcher
from bs4 import BeautifulSoup

class PriceWatcher(BaseWatcher):
    def __init__(self, product_url: str):
        super().__init__(
            name="price_watcher",
            url=product_url,
            check_interval=1800  # Check every 30 minutes
        )
    
    def extract_value(self, html_content: str) -> float:
        soup = BeautifulSoup(html_content, 'html.parser')
        price_element = soup.find('span', class_='price')
        
        if price_element:
            price_text = price_element.text.strip()
            # Extract number from "$19.99"
            import re
            price_match = re.search(r'[\d.]+', price_text)
            return float(price_match.group()) if price_match else None
        
        return None
    
    def has_changed(self, old_value, new_value) -> bool:
        if old_value is None or new_value is None:
            return False
        
        # Trigger if price changes by more than $1
        return abs(old_value - new_value) > 1.0
    
    def trigger_alarm(self, old_value, new_value):
        print(f"🚨 Price changed from ${old_value} to ${new_value}")
        # Add your notification logic here

# Use the watcher
watcher = PriceWatcher("https://store.com/product")
watcher.run(continuous=True)
```

### Q: How do I get notifications when watchers detect changes?

**A:** Multiple notification options:

**1. Email Notifications:**
```python
def trigger_alarm(self, old_value, new_value):
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(f"Value changed from {old_value} to {new_value}")
    msg['Subject'] = f"Change detected in {self.name}"
    msg['From'] = "watchtower@yoursite.com"
    msg['To'] = "you@email.com"
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("your_email", "your_password")
    server.send_message(msg)
    server.quit()
```

**2. Slack Notifications:**
```python
def trigger_alarm(self, old_value, new_value):
    import requests
    
    webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    message = {
        "text": f"🚨 {self.name}: Value changed from {old_value} to {new_value}"
    }
    requests.post(webhook_url, json=message)
```

**3. Discord Notifications:**
```python
def trigger_alarm(self, old_value, new_value):
    import requests
    
    webhook_url = "https://discord.com/api/webhooks/YOUR/WEBHOOK"
    data = {
        "content": f"🚨 {self.name}: Value changed from {old_value} to {new_value}"
    }
    requests.post(webhook_url, json=data)
```

### Q: My watcher isn't detecting changes. What's wrong?

**A:** Common issues and solutions:

**1. Check Value Extraction:**
```python
# Debug your extraction
watcher = YourWatcher()
html = watcher.fetch_page()
value = watcher.extract_value(html)
print(f"Extracted value: {value}")
```

**2. Verify Change Detection:**
```python
def has_changed(self, old_value, new_value) -> bool:
    # Add debugging
    print(f"Comparing: {old_value} vs {new_value}")
    
    # Make sure comparison logic is correct
    if old_value is None:
        return False  # Don't trigger on first run
    
    return old_value != new_value
```

**3. Check Website Structure:**
- Websites may have changed their HTML structure
- Use browser developer tools to inspect elements
- Look for alternative selectors

**4. Handle Dynamic Content:**
```python
def extract_value(self, html_content: str) -> str:
    # Wait for dynamic content to load
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(self.url)
        page.wait_for_selector('.target-element')  # Wait for element
        content = page.content()
        browser.close()
        
        # Now extract from content
        soup = BeautifulSoup(content, 'html.parser')
        return soup.find('.target-element').text
```

### Q: How often should my watchers check for changes?

**A:** It depends on your use case:

**Recommended Intervals:**
- **Stock Prices**: 60-300 seconds (1-5 minutes)
- **News Sites**: 300-1800 seconds (5-30 minutes)
- **Product Prices**: 1800-3600 seconds (30 minutes - 1 hour)
- **Social Media**: 300-900 seconds (5-15 minutes)
- **Government Data**: 3600-86400 seconds (1 hour - 1 day)

**Factors to Consider:**
- How quickly the data changes
- How quickly you need to know about changes
- Website's tolerance for requests (respect rate limits)
- Your system resources

**Be Respectful:**
```python
class PolitePriceWatcher(BaseWatcher):
    def __init__(self, url: str):
        super().__init__(
            name="polite_watcher",
            url=url,
            check_interval=1800  # 30 minutes minimum
        )
        
        # Add delays between requests
        self.request_delay = 2  # 2 seconds between requests
    
    def fetch_page(self) -> str:
        import time
        time.sleep(self.request_delay)  # Be polite
        return super().fetch_page()
```

---

## 🎛️ Dashboard & UI

### Q: How do I start the Watchtower dashboard?

**A:** Simple command to launch:

```bash
streamlit run src/web/fullstreamlit/app.py
```

**Custom Settings:**
```bash
# Use different port
streamlit run src/web/fullstreamlit/app.py --server.port 8502

# Bind to all interfaces
streamlit run src/web/fullstreamlit/app.py --server.address 0.0.0.0

# Disable browser auto-open
streamlit run src/web/fullstreamlit/app.py --server.headless true
```

**Expected Output:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.100:8501
```

### Q: The dashboard shows "No data available". How do I fix this?

**A:** This usually means no ETL data exists yet:

**1. Run an ETL Pipeline First:**
```bash
# Run the example ETL
python src/etl/news/news_get_ycombinator.py

# Or run your custom ETL
python my_etl.py
```

**2. Check Data Directory:**
```bash
ls -la data/
ls -la data/*/
```

**3. Verify Data Files:**
```bash
# Check if ETL generated files
find data/ -name "*.json" -o -name "*.csv"

# Check file contents
head data/your_etl_name/output.json
```

**4. Dashboard Configuration:**
```python
# In your dashboard code, check data paths
import os
data_file = "data/your_etl_name/output.json"
print(f"Looking for: {os.path.abspath(data_file)}")
print(f"Exists: {os.path.exists(data_file)}")
```

### Q: Can I customize the dashboard?

**A:** Yes! The dashboard is fully customizable:

**1. Modify Existing Dashboard:**
```python
# Edit src/web/fullstreamlit/app.py
import streamlit as st

def main():
    st.title("My Custom Watchtower Dashboard")
    
    # Add your custom sections
    st.header("My ETL Results")
    # Your custom visualization code
    
    st.header("My Watchers")
    # Your custom watcher status display
```

**2. Create New Dashboard:**
```python
# Create my_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px

def load_my_data():
    # Load your specific data
    return pd.read_json("data/my_etl/output.json")

def main():
    st.title("My Project Dashboard")
    
    data = load_my_data()
    
    # Create custom charts
    fig = px.line(data, x='date', y='value', title='Trend Analysis')
    st.plotly_chart(fig)
    
    # Add filters
    category = st.selectbox("Category", data['category'].unique())
    filtered_data = data[data['category'] == category]
    st.dataframe(filtered_data)

if __name__ == "__main__":
    main()
```

**3. Run Custom Dashboard:**
```bash
streamlit run my_dashboard.py
```

### Q: How do I add charts and visualizations?

**A:** Streamlit supports multiple visualization libraries:

**1. Plotly (Recommended):**
```python
import plotly.express as px
import plotly.graph_objects as go

# Line chart
fig = px.line(df, x='date', y='price', title='Price Trend')
st.plotly_chart(fig, use_container_width=True)

# Bar chart
fig = px.bar(df, x='category', y='count', title='Category Distribution')
st.plotly_chart(fig)

# Custom chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['date'], y=df['value'], mode='lines+markers'))
st.plotly_chart(fig)
```

**2. Built-in Streamlit Charts:**
```python
# Simple line chart
st.line_chart(df[['date', 'value']].set_index('date'))

# Bar chart
st.bar_chart(df[['category', 'count']].set_index('category'))

# Area chart
st.area_chart(df[['date', 'value']].set_index('date'))
```

**3. Matplotlib/Seaborn:**
```python
import matplotlib.pyplot as plt
import seaborn as sns

fig, ax = plt.subplots()
sns.lineplot(data=df, x='date', y='value', ax=ax)
st.pyplot(fig)
```

---

## 🔧 Configuration

### Q: How do I configure Watchtower settings?

**A:** Watchtower uses environment-based configuration:

**1. Environment Variables:**
```bash
# Set in your shell
export DATABASE_URL="postgresql://user:pass@localhost/watchtower"
export LOG_LEVEL="DEBUG"
export ETL_BATCH_SIZE="500"

# Or create .env file
echo "DATABASE_URL=sqlite:///data/watchtower.db" > .env
echo "LOG_LEVEL=INFO" >> .env
echo "DEBUG=false" >> .env
```

**2. Configuration Files:**
```bash
# Copy template
cp .env.template .env

# Edit configuration
nano .env  # or your preferred editor
```

**3. Programmatic Configuration:**
```python
from src.config.settings import get_settings

# Get current settings
settings = get_settings()

# Override settings for development
settings.database.url = "sqlite:///test.db"
settings.logging.level = "DEBUG"
```

### Q: What configuration options are available?

**A:** Complete configuration reference:

**Database Settings:**
```bash
DATABASE__URL=postgresql://user:pass@localhost/db
DATABASE__POOL_SIZE=10
DATABASE__ECHO=false
```

**Logging Settings:**
```bash
LOGGING__LEVEL=INFO
LOGGING__FILE_ENABLED=true
LOGGING__STRUCTURED=false
```

**ETL Settings:**
```bash
ETL__BATCH_SIZE=100
ETL__MAX_WORKERS=4
ETL__TIMEOUT=300
```

**Watcher Settings:**
```bash
WATCHER__DEFAULT_CHECK_INTERVAL=3600
WATCHER__MAX_EVENTS_PER_WATCHER=1000
```

**API Settings:**
```bash
API__HOST=localhost
API__PORT=8000
API__CORS_ORIGINS=["http://localhost:3000"]
```

**Security Settings:**
```bash
SECURITY__SECRET_KEY=your-secret-key-here
SECURITY__ALGORITHM=HS256
```

### Q: How do I use different configurations for development and production?

**A:** Use environment-specific configuration:

**1. Environment Files:**
```bash
# Development
config/development.env

# Staging  
config/staging.env

# Production
config/production.env
```

**2. Load Based on Environment:**
```bash
# Set environment
export ENVIRONMENT=production

# Watchtower will automatically load the right config
python my_etl.py
```

**3. Programmatic Environment Switching:**
```python
from src.config.settings import get_settings, get_production_settings

if os.getenv("ENVIRONMENT") == "production":
    settings = get_production_settings()
else:
    settings = get_settings()  # Development defaults
```

**4. Docker Configuration:**
```dockerfile
# Dockerfile
ENV ENVIRONMENT=production
ENV DATABASE__URL=postgresql://prod_user:pass@db:5432/watchtower
ENV LOG_LEVEL=WARNING
```

---

## 🐛 Troubleshooting

### Q: I'm getting "Permission denied" errors. How do I fix this?

**A:** Common permission issues and solutions:

**1. File/Directory Permissions:**
```bash
# Fix ownership
sudo chown -R $USER:$USER /path/to/watchtower

# Fix permissions
chmod -R 755 /path/to/watchtower
chmod 644 /path/to/watchtower/*.py
```

**2. Virtual Environment Permissions:**
```bash
# Don't use sudo with pip/poetry
pip install --user package_name

# Fix virtual environment ownership
sudo chown -R $USER:$USER .venv/
```

**3. Data Directory Permissions:**
```bash
# Create with correct permissions
mkdir -p data/{etl,watchers,logs}
chmod 755 data/
chmod -R 644 data/*/
```

**4. Windows-Specific:**
```powershell
# Run as Administrator
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Add project directory to antivirus exclusions
```

### Q: ETL pipelines are running very slowly. How can I speed them up?

**A:** Performance optimization strategies:

**1. Profile Your Code:**
```bash
# Profile ETL execution
python -m cProfile -o etl_profile.prof my_etl.py

# Analyze results
python -c "
import pstats
p = pstats.Stats('etl_profile.prof')
p.sort_stats('cumulative').print_stats(20)
"
```

**2. Optimize Data Processing:**
```python
# Use batch processing
def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Process in smaller batches
    return self.process_in_batches(data, self._transform_batch, batch_size=100)

# Use pandas for large datasets
import pandas as pd
df = pd.DataFrame(data)
# Vectorized operations are much faster
df['new_column'] = df['old_column'].str.upper()
```

**3. Parallel Processing:**
```python
from concurrent.futures import ThreadPoolExecutor

def extract(self) -> List[Dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(self._extract_source, source) for source in sources]
        results = []
        for future in futures:
            results.extend(future.result())
    return results
```

**4. Caching and Incremental Processing:**
```python
# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_operation(self, data):
    # This will be cached
    return process_data(data)

# Only process new data
def extract(self) -> List[Dict[str, Any]]:
    last_timestamp = self._get_last_run_timestamp()
    return self._extract_since(last_timestamp)
```

### Q: My watchers keep timing out. What should I do?

**A:** Timeout solutions:

**1. Increase Timeouts:**
```python
def fetch_page(self) -> str:
    response = requests.get(
        self.url,
        timeout=(30, 60)  # (connect_timeout, read_timeout)
    )
    return response.text
```

**2. Implement Retries:**
```python
import time

def fetch_page(self) -> str:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(self.url, timeout=30)
            return response.text
        except requests.Timeout:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

**3. Use Playwright for Dynamic Sites:**
```python
def fetch_page(self) -> str:
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(self.url, timeout=30000)  # 30 seconds
        content = page.content()
        browser.close()
        return content
```

### Q: The dashboard won't start. What could be wrong?

**A:** Dashboard troubleshooting:

**1. Check Dependencies:**
```bash
# Verify Streamlit is installed
pip list | grep streamlit

# Install if missing
pip install streamlit
```

**2. Check Port Conflicts:**
```bash
# Check if port 8501 is in use
lsof -i :8501
netstat -an | grep 8501

# Use different port
streamlit run app.py --server.port 8502
```

**3. Check File Paths:**
```bash
# Verify app file exists
ls -la src/web/fullstreamlit/app.py

# Run from correct directory
cd /path/to/watchtower
streamlit run src/web/fullstreamlit/app.py
```

**4. Check for Code Errors:**
```python
# Test the dashboard code
python -c "
import sys
sys.path.append('src')
try:
    from web.fullstreamlit.app import main
    print('Dashboard code is valid')
except Exception as e:
    print(f'Dashboard error: {e}')
"
```

---

## ⚡ Performance

### Q: How much data can Watchtower handle?

**A:** Performance depends on your system, but here are general guidelines:

**ETL Pipeline Capacity:**
- **Small**: 1K-10K records per run (excellent performance)
- **Medium**: 10K-100K records per run (good performance with optimization)
- **Large**: 100K-1M records per run (requires optimization and batching)
- **Very Large**: 1M+ records (requires streaming and advanced optimization)

**Watcher Capacity:**
- **Concurrent Watchers**: 50-100 watchers on typical hardware
- **Check Frequency**: 1-5 minute intervals for active monitoring
- **Data Storage**: Limited by disk space (recommend 10GB+ for production)

**Optimization for Large Datasets:**
```python
# Stream processing for large datasets
def process_large_dataset(self):
    for batch in self.get_data_in_batches(batch_size=1000):
        processed_batch = self.transform(batch)
        self.load(processed_batch)
        # Clear memory after each batch
        del batch, processed_batch
        gc.collect()
```

### Q: How can I monitor Watchtower performance?

**A:** Built-in and custom monitoring options:

**1. ETL Metrics:**
```python
# ETL pipelines automatically track metrics
etl = MyETL()
metrics = etl.run()

print(f"Duration: {metrics.duration_seconds}s")
print(f"Records: {metrics.records_loaded}")
print(f"Success rate: {metrics.success_rate}%")
print(f"Errors: {metrics.error_count}")
```

**2. System Monitoring:**
```python
import psutil
import time

class MonitoredETL(BaseETL):
    def run(self):
        # Monitor system resources
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        result = super().run()
        end_time = time.time()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        self.logger.info(f"Performance metrics:", extra={
            "duration": end_time - start_time,
            "memory_used_mb": final_memory - initial_memory,
            "cpu_percent": process.cpu_percent()
        })
        
        return result
```

**3. Custom Performance Dashboard:**
```python
# Add to your Streamlit dashboard
import streamlit as st
import plotly.express as px

def show_performance_metrics():
    st.header("Performance Metrics")
    
    # Load performance data
    metrics = load_etl_metrics()
    
    # Duration chart
    fig = px.line(metrics, x='date', y='duration_seconds', title='ETL Duration Trend')
    st.plotly_chart(fig)
    
    # Success rate chart
    fig = px.bar(metrics, x='etl_name', y='success_rate', title='Success Rates by ETL')
    st.plotly_chart(fig)
```

### Q: My system is running out of memory. How do I fix this?

**A:** Memory optimization strategies:

**1. Stream Processing:**
```python
def transform_stream(self, data_iterator):
    """Process data as a stream instead of loading all into memory"""
    for item in data_iterator:
        yield self._transform_item(item)

def load_stream(self, data_stream):
    """Load data in small batches"""
    batch = []
    for item in data_stream:
        batch.append(item)
        if len(batch) >= 100:  # Small batches
            self._save_batch(batch)
            batch.clear()  # Free memory
    
    if batch:
        self._save_batch(batch)
```

**2. Memory Monitoring:**
```python
import gc
import psutil

class MemoryAwareETL(BaseETL):
    def __init__(self):
        super().__init__()
        self.memory_threshold = 1000  # MB
    
    def _check_memory(self):
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        if memory_mb > self.memory_threshold:
            self.logger.warning(f"High memory usage: {memory_mb:.1f}MB")
            gc.collect()  # Force garbage collection
    
    def transform(self, data):
        result = []
        for i, item in enumerate(data):
            result.append(self._transform_item(item))
            
            # Check memory every 1000 items
            if i % 1000 == 0:
                self._check_memory()
        
        return result
```

**3. Use Efficient Data Structures:**
```python
# Instead of storing everything in memory
all_data = []  # Bad for large datasets
for item in huge_dataset:
    all_data.append(process(item))

# Use generators
def process_data_generator(huge_dataset):
    for item in huge_dataset:
        yield process(item)

# Or use pandas for efficient operations
import pandas as pd
df = pd.DataFrame(data)
# Pandas operations are memory-efficient
result = df.groupby('category').sum()
```

---

## 🔒 Security

### Q: Is Watchtower secure for production use?

**A:** Watchtower includes security best practices, but production deployment requires additional configuration:

**Built-in Security Features:**
- Input validation using Pydantic models
- SQL injection protection (when using ORM)
- CORS configuration for API endpoints
- Secret key management through environment variables
- Configurable authentication systems

**Production Security Checklist:**
- [ ] Change default secret keys
- [ ] Use HTTPS for all connections
- [ ] Set up proper authentication
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Use encrypted database connections

### Q: How do I secure API keys and sensitive configuration?

**A:** Multiple approaches for secret management:

**1. Environment Variables:**
```bash
# Set sensitive values as environment variables
export API_KEY="your-secret-api-key"
export DATABASE_PASSWORD="secure-password"

# Don't commit these to version control
echo "API_KEY=your-secret-api-key" >> .env
echo ".env" >> .gitignore
```

**2. External Secret Management:**
```python
# AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Azure Key Vault
from azure.keyvault.secrets import SecretClient

def get_azure_secret(secret_name):
    client = SecretClient(vault_url="https://vault.vault.azure.net/", credential=credential)
    return client.get_secret(secret_name).value
```

**3. Configuration Validation:**
```python
from pydantic import BaseSettings, validator

class SecureSettings(BaseSettings):
    api_key: str
    database_password: str
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if len(v) < 16:
            raise ValueError('API key must be at least 16 characters')
        if v == "default-key":
            raise ValueError('Must set a real API key')
        return v
    
    class Config:
        env_file = ".env"
```

### Q: How do I handle rate limiting and avoid getting blocked?

**A:** Respectful scraping practices:

**1. Built-in Rate Limiting:**
```python
class RateLimitedETL(BaseETL):
    def __init__(self):
        super().__init__()
        self.request_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def extract_from_url(self, url):
        self._rate_limit()
        return requests.get(url).text
```

**2. Respectful Headers:**
```python
def fetch_page(self) -> str:
    headers = {
        'User-Agent': 'Watchtower/1.0 (data research; contact@yoursite.com)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    
    response = requests.get(self.url, headers=headers)
    return response.text
```

**3. Respect robots.txt:**
```python
from urllib.robotparser import RobotFileParser

def can_fetch(self, url: str) -> bool:
    """Check if robots.txt allows access"""
    try:
        rp = RobotFileParser()
        rp.set_url(f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt")
        rp.read()
        return rp.can_fetch('*', url)
    except:
        return True  # If we can't check, assume it's OK
```

**4. Use Rotating Proxies (if needed):**
```python
class ProxyETL(BaseETL):
    def __init__(self):
        super().__init__()
        self.proxies = [
            {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
            {'http': 'http://proxy2:port', 'https': 'https://proxy2:port'},
        ]
        self.current_proxy = 0
    
    def get_next_proxy(self):
        proxy = self.proxies[self.current_proxy]
        self.current_proxy = (self.current_proxy + 1) % len(self.proxies)
        return proxy
    
    def fetch_with_proxy(self, url):
        proxy = self.get_next_proxy()
        return requests.get(url, proxies=proxy)
```

---

## 🚀 Deployment

### Q: How do I deploy Watchtower to production?

**A:** Multiple deployment options:

**1. Server Deployment:**
```bash
# On your production server
git clone https://github.com/josmerod/watchtower.git
cd watchtower

# Set up production environment
cp .env.template .env
# Edit .env with production settings

# Install dependencies
poetry install --no-dev

# Install system service
sudo cp scripts/watchtower.service /etc/systemd/system/
sudo systemctl enable watchtower
sudo systemctl start watchtower
```

**2. Docker Deployment:**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

RUN playwright install chromium

EXPOSE 8501

CMD ["streamlit", "run", "src/web/fullstreamlit/app.py", "--server.address", "0.0.0.0"]
```

```bash
# Build and run
docker build -t watchtower .
docker run -p 8501:8501 -v $(pwd)/data:/app/data watchtower
```

**3. Docker Compose:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  watchtower:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/watchtower
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: watchtower
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Q: How do I schedule ETL pipelines to run automatically?

**A:** Multiple scheduling options:

**1. Cron (Linux/macOS):**
```bash
# Edit crontab
crontab -e

# Add entries
# Run news ETL every hour
0 * * * * cd /path/to/watchtower && /path/to/python news_etl.py

# Run price monitoring every 30 minutes
*/30 * * * * cd /path/to/watchtower && /path/to/python price_etl.py

# Run daily cleanup at 2 AM
0 2 * * * cd /path/to/watchtower && /path/to/python cleanup.py
```

**2. Systemd Timers (Linux):**
```ini
# /etc/systemd/system/watchtower-etl.service
[Unit]
Description=Watchtower ETL Job
After=network.target

[Service]
Type=oneshot
User=watchtower
WorkingDirectory=/opt/watchtower
ExecStart=/opt/watchtower/.venv/bin/python news_etl.py

# /etc/systemd/system/watchtower-etl.timer
[Unit]
Description=Run Watchtower ETL every hour
Requires=watchtower-etl.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable and start timer
sudo systemctl enable watchtower-etl.timer
sudo systemctl start watchtower-etl.timer
```

**3. Python Scheduler:**
```python
# scheduler.py
import schedule
import time
from my_etl import MyETL

def run_etl():
    try:
        etl = MyETL()
        metrics = etl.run()
        print(f"ETL completed: {metrics.records_loaded} records")
    except Exception as e:
        print(f"ETL failed: {e}")

# Schedule jobs
schedule.every().hour.do(run_etl)
schedule.every().day.at("02:00").do(run_cleanup)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

**4. Cloud Scheduling:**
```python
# AWS Lambda function
import json
from my_etl import MyETL

def lambda_handler(event, context):
    etl = MyETL()
    metrics = etl.run()
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'records_processed': metrics.records_loaded,
            'success': metrics.is_successful
        })
    }
```

### Q: How do I monitor Watchtower in production?

**A:** Comprehensive monitoring setup:

**1. Health Checks:**
```python
# health_check.py
import sys
import requests
from src.config.settings import get_settings

def check_dashboard():
    """Check if dashboard is responding"""
    try:
        response = requests.get("http://localhost:8501", timeout=10)
        return response.status_code == 200
    except:
        return False

def check_database():
    """Check database connectivity"""
    try:
        settings = get_settings()
        # Test database connection
        return True
    except:
        return False

def check_data_freshness():
    """Check if ETL data is recent"""
    try:
        # Check last ETL run timestamp
        return True
    except:
        return False

def main():
    checks = {
        'dashboard': check_dashboard(),
        'database': check_database(),
        'data_freshness': check_data_freshness()
    }
    
    all_healthy = all(checks.values())
    
    if all_healthy:
        print("All checks passed")
        sys.exit(0)
    else:
        print(f"Health check failed: {checks}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**2. Log Monitoring:**
```bash
# Monitor logs with logrotate
# /etc/logrotate.d/watchtower
/opt/watchtower/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

**3. Alerting:**
```python
# alerts.py
import smtplib
from email.mime.text import MIMEText

def send_alert(subject: str, message: str):
    """Send email alert"""
    msg = MIMEText(message)
    msg['Subject'] = f"Watchtower Alert: {subject}"
    msg['From'] = "watchtower@yoursite.com"
    msg['To'] = "admin@yoursite.com"
    
    server = smtplib.SMTP('localhost')
    server.send_message(msg)
    server.quit()

def check_and_alert():
    """Check system health and send alerts if needed"""
    if not check_dashboard():
        send_alert("Dashboard Down", "Streamlit dashboard is not responding")
    
    if not check_data_freshness():
        send_alert("Stale Data", "ETL data is more than 24 hours old")
```

---

## 🤝 Contributing

### Q: How can I contribute to Watchtower?

**A:** Multiple ways to contribute:

**1. Code Contributions:**
- Fix bugs or add features
- Improve documentation
- Add new ETL connectors
- Create example use cases

**Process:**
```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/watchtower.git
cd watchtower

# Create feature branch
git checkout -b feature/my-new-feature

# Make changes and test
poetry install
pytest tests/

# Commit and push
git commit -m "Add: new feature description"
git push origin feature/my-new-feature

# Create pull request on GitHub
```

**2. Documentation:**
- Improve existing docs
- Add tutorials or examples
- Create video guides
- Translate documentation

**3. Community Support:**
- Answer questions in GitHub Issues
- Help with troubleshooting
- Share your use cases
- Write blog posts about Watchtower

### Q: What coding standards should I follow?

**A:** Follow the project's coding standards:

**1. Code Style:**
```bash
# Format code with Ruff
ruff format .

# Check for issues
ruff check . --fix

# Type checking
mypy src/
```

**2. Documentation:**
```python
def my_function(param1: str, param2: int) -> List[str]:
    """
    Brief description of the function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        List of strings containing the result
        
    Raises:
        ValueError: If param2 is negative
        
    Example:
        >>> result = my_function("test", 5)
        >>> print(len(result))
        5
    """
    pass
```

**3. Testing:**
```python
# Write tests for new features
import pytest
from src.etl.my_etl import MyETL

def test_my_etl_extract():
    """Test ETL extraction functionality"""
    etl = MyETL()
    data = etl.extract()
    
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(item, dict) for item in data)

def test_my_etl_transform():
    """Test ETL transformation functionality"""
    etl = MyETL()
    test_data = [{"title": "Test", "url": "http://test.com"}]
    
    result = etl.transform(test_data)
    
    assert len(result) == 1
    assert "title" in result[0]
    assert result[0]["title"] == "Test"
```

### Q: How do I report bugs or request features?

**A:** Use GitHub Issues with templates:

**Bug Reports:**
1. Go to [GitHub Issues](https://github.com/josmerod/watchtower/issues)
2. Click "New Issue"
3. Choose "Bug Report" template
4. Fill out all sections:
   - Environment details
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

**Feature Requests:**
1. Use "Feature Request" template
2. Describe the use case
3. Explain why it would be valuable
4. Suggest implementation approach (if you have ideas)

**Before Submitting:**
- Search existing issues
- Try the latest version
- Check documentation

---

*This FAQ is regularly updated based on community questions. Can't find what you're looking for? [Create an issue](https://github.com/josmerod/watchtower/issues/new) and we'll add it to the FAQ!*
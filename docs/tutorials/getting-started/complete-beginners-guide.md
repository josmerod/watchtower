# Complete Beginner's Guide to Watchtower

Welcome to Watchtower! This comprehensive guide will take you from zero to productive in about 30 minutes. By the end of this tutorial, you'll have Watchtower running and understand how to create your first ETL pipeline and watcher.

## 🎯 What You'll Learn

- What Watchtower is and why it's useful
- How to install and configure Watchtower
- How to create your first ETL pipeline
- How to set up a simple watcher
- How to use the dashboard to view your data
- Where to go next for advanced features

## 📋 Prerequisites

- **Computer**: Windows, macOS, or Linux
- **Python**: Version 3.10 or higher ([download here](https://python.org/downloads/))
- **Basic comfort**: Using command line/terminal
- **Time needed**: 30-45 minutes

## 🔍 What is Watchtower?

Watchtower is a comprehensive data monitoring and ETL (Extract, Transform, Load) framework that helps you:

- **Extract data** from websites, APIs, and other sources
- **Transform data** to clean and structure it
- **Load data** into files, databases, or other systems
- **Monitor websites** for changes and get alerts
- **Visualize data** through a web dashboard

**Real-world examples:**
- Monitor news sites and aggregate articles
- Track product prices across e-commerce sites
- Collect social media metrics
- Watch for changes on competitor websites

---

## 🚀 Step 1: Installation

### Option A: Using Poetry (Recommended)

Poetry is a modern Python package manager that handles dependencies elegantly.

1. **Install Poetry** (if not already installed):
   ```bash
   # On Windows (PowerShell)
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   
   # On macOS/Linux
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone Watchtower**:
   ```bash
   git clone https://github.com/josmerod/watchtower.git
   cd watchtower
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   poetry shell
   ```

### Option B: Using pip and venv

If you prefer traditional Python virtual environments:

1. **Clone and setup**:
   ```bash
   git clone https://github.com/josmerod/watchtower.git
   cd watchtower
   python -m venv .venv
   
   # Activate virtual environment
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Install Playwright Browsers

Watchtower uses Playwright for web scraping, which needs browser installations:

```bash
playwright install
```

### Verify Installation

Test that everything works:

```bash
# Test the ETL system
python src/etl/news/news_get_ycombinator.py

# Start the dashboard (optional for now)
streamlit run src/web/fullstreamlit/app.py
```

**Expected output**: The ETL script should run without errors and create data files in the `data/` directory.

---

## 🏗️ Step 2: Understanding the Project Structure

Before we dive in, let's understand how Watchtower is organized:

```
watchtower/
├── src/                    # Main source code
│   ├── etl/               # ETL pipelines
│   ├── watchers/          # Website monitoring
│   ├── web/               # Dashboard interface
│   ├── config/            # Configuration management
│   └── utils/             # Shared utilities
├── data/                  # Generated data files
├── docs/                  # Documentation
├── Tests/                 # Test suite
└── README.md              # Project overview
```

**Key concepts:**
- **ETL Pipelines**: Scripts that extract, transform, and load data
- **Watchers**: Monitors that check websites for changes
- **Dashboard**: Web interface to view and interact with data
- **Configuration**: Settings that control how everything works

---

## 📊 Step 3: Your First ETL Pipeline

Let's create a simple ETL pipeline that extracts data from a JSON API and saves it locally.

### Create Your First ETL Script

Create a new file called `my_first_etl.py` in the root directory:

```python
#!/usr/bin/env python3
"""
My First ETL Pipeline - A simple example that fetches data from a public API
"""

from src.etl.base import SimpleETL
from typing import List, Dict, Any
import requests
from datetime import datetime

class JSONPlaceholderETL(SimpleETL):
    """ETL pipeline that fetches posts from JSONPlaceholder API"""
    
    def __init__(self):
        super().__init__(
            name="jsonplaceholder_etl",
            description="Fetch posts from JSONPlaceholder API"
        )
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract data from the JSONPlaceholder API"""
        self.logger.info("Extracting posts from JSONPlaceholder API...")
        
        try:
            # Fetch data from public API
            response = requests.get("https://jsonplaceholder.typicode.com/posts")
            response.raise_for_status()
            
            posts = response.json()
            self.logger.info(f"Successfully extracted {len(posts)} posts")
            
            return posts
            
        except Exception as e:
            self.logger.error(f"Failed to extract data: {e}")
            raise
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform the extracted data"""
        self.logger.info("Transforming extracted data...")
        
        transformed_posts = []
        
        for post in data:
            # Clean and structure the data
            transformed_post = {
                "id": post.get("id"),
                "title": post.get("title", "").strip().title(),
                "content": post.get("body", "").strip(),
                "user_id": post.get("userId"),
                "word_count": len(post.get("body", "").split()),
                "extracted_at": datetime.now().isoformat()
            }
            
            # Only include posts with meaningful content
            if len(transformed_post["content"]) > 10:
                transformed_posts.append(transformed_post)
        
        self.logger.info(f"Transformed {len(transformed_posts)} posts")
        return transformed_posts
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Load the transformed data to files"""
        self.logger.info("Loading data to files...")
        
        # Save as JSON
        self.save_as_json(data, "posts.json")
        
        # Save as CSV
        self.save_as_csv(data, "posts.csv")
        
        self.logger.info(f"Successfully loaded {len(data)} posts to files")


def main():
    """Run the ETL pipeline"""
    print("🚀 Starting My First ETL Pipeline")
    print("=" * 50)
    
    # Create and run the ETL
    etl = JSONPlaceholderETL()
    metrics = etl.run()
    
    # Display results
    print(f"\n✅ ETL Pipeline Complete!")
    print(f"📊 Records processed: {metrics.records_loaded}")
    print(f"⏱️  Duration: {metrics.duration_seconds:.2f} seconds")
    print(f"📈 Success rate: {metrics.success_rate:.1f}%")
    
    # Show where files were saved
    data_dir = etl.get_data_dir()
    print(f"\n📁 Data saved to: {data_dir}")
    print(f"   - posts.json")
    print(f"   - posts.csv")


if __name__ == "__main__":
    main()
```

### Run Your First ETL

```bash
python my_first_etl.py
```

**Expected Output:**
```
🚀 Starting My First ETL Pipeline
==================================================
[INFO] Extracting posts from JSONPlaceholder API...
[INFO] Successfully extracted 100 posts
[INFO] Transforming extracted data...
[INFO] Transformed 100 posts
[INFO] Loading data to files...
[INFO] Successfully loaded 100 posts to files

✅ ETL Pipeline Complete!
📊 Records processed: 100
⏱️  Duration: 2.34 seconds
📈 Success rate: 100.0%

📁 Data saved to: data/jsonplaceholder_etl/
   - posts.json
   - posts.csv
```

### Explore Your Data

Check what files were created:

```bash
# List the generated files
ls -la data/jsonplaceholder_etl/

# Preview the JSON file
head -20 data/jsonplaceholder_etl/posts.json

# Preview the CSV file
head -10 data/jsonplaceholder_etl/posts.csv
```

**🎉 Congratulations!** You've just created and run your first ETL pipeline with Watchtower!

---

## 👁️ Step 4: Your First Watcher

Now let's create a watcher that monitors a website for changes. We'll monitor a simple webpage and get notified when its content changes.

### Create Your First Watcher Script

Create `my_first_watcher.py`:

```python
#!/usr/bin/env python3
"""
My First Watcher - Monitor a webpage for content changes
"""

from src.watchers.base_watcher import BaseWatcher
from bs4 import BeautifulSoup
from typing import Any

class QuoteWatcher(BaseWatcher):
    """Watch a quotes website for new daily quotes"""
    
    def __init__(self):
        # Monitor a quotes website that changes daily
        super().__init__(
            name="daily_quote_watcher",
            url="http://quotes.toscrape.com/",
            check_interval=300  # Check every 5 minutes
        )
    
    def extract_value(self, html_content: str) -> Any:
        """Extract the first quote from the page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the first quote on the page
        quote_div = soup.find('div', class_='quote')
        if not quote_div:
            return None
        
        # Extract quote text and author
        quote_text = quote_div.find('span', class_='text')
        quote_author = quote_div.find('small', class_='author')
        
        if quote_text and quote_author:
            return {
                "text": quote_text.text.strip(),
                "author": quote_author.text.strip()
            }
        
        return None
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Determine if the quote has changed"""
        if old_value is None:
            return False  # Don't trigger on first check
        
        if new_value is None:
            return True  # Trigger if we can't get the quote anymore
        
        # Check if the quote text or author changed
        return (old_value.get("text") != new_value.get("text") or
                old_value.get("author") != new_value.get("author"))
    
    def trigger_alarm(self, old_value: Any, new_value: Any):
        """Called when a change is detected"""
        print("\n🚨 CHANGE DETECTED!")
        print("=" * 40)
        
        if old_value:
            print(f"📜 Old quote: \"{old_value.get('text')}\"")
            print(f"👤 By: {old_value.get('author')}")
        
        if new_value:
            print(f"📜 New quote: \"{new_value.get('text')}\"")
            print(f"👤 By: {new_value.get('author')}")
        else:
            print("❌ Could not retrieve quote")
        
        # Call parent method to record the event
        super().trigger_alarm(old_value, new_value)


def main():
    """Run the watcher"""
    print("👁️  Starting Quote Watcher")
    print("=" * 40)
    print("This watcher will check for quote changes every 5 minutes.")
    print("Press Ctrl+C to stop.\n")
    
    watcher = QuoteWatcher()
    
    # Run one check to see current state
    print("🔍 Performing initial check...")
    watcher.check()
    
    # Ask user if they want to run continuously
    print("\nOptions:")
    print("1. Run a single check (good for testing)")
    print("2. Run continuously (monitors in background)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "2":
        print("\n🔄 Starting continuous monitoring...")
        print("   (Press Ctrl+C to stop)")
        try:
            watcher.run(continuous=True)
        except KeyboardInterrupt:
            print("\n⏹️  Watcher stopped by user")
    else:
        print("\n✅ Single check completed!")
        print(f"📁 Check the watcher data at: data/watchers/{watcher.name}/")


if __name__ == "__main__":
    main()
```

### Run Your First Watcher

```bash
python my_first_watcher.py
```

**Expected Output:**
```
👁️  Starting Quote Watcher
========================================
This watcher will check for quote changes every 5 minutes.
Press Ctrl+C to stop.

🔍 Performing initial check...
[INFO] Checking URL: http://quotes.toscrape.com/
[INFO] Page fetched successfully (3.2KB)
[INFO] Extracted value: {'text': '"The world as we have...', 'author': 'Albert Einstein'}
[INFO] State saved to: data/watchers/daily_quote_watcher/state.json

Options:
1. Run a single check (good for testing)
2. Run continuously (monitors in background)

Enter your choice (1 or 2):
```

Choose option 1 for now to test it out.

### Explore Watcher Data

```bash
# Check the watcher data directory
ls -la data/watchers/daily_quote_watcher/

# View the current state
cat data/watchers/daily_quote_watcher/state.json

# Check for any events (changes detected)
ls -la data/watchers/daily_quote_watcher/events/
```

**🎉 Great job!** You've created your first watcher that can monitor websites for changes.

---

## 📊 Step 5: Exploring the Dashboard

Watchtower includes a web dashboard built with Streamlit that lets you visualize and interact with your data.

### Start the Dashboard

```bash
streamlit run src/web/fullstreamlit/app.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

### Open the Dashboard

1. Open your web browser
2. Navigate to `http://localhost:8501`
3. Explore the different sections:
   - **Dashboard Overview**: Summary of ETL runs and watcher activity
   - **Data Explorer**: Browse your extracted data
   - **ETL Status**: View pipeline execution history
   - **Watcher Monitoring**: Check watcher states and events

### Dashboard Features

The dashboard provides:
- **Real-time data visualization** with charts and tables
- **ETL pipeline monitoring** with success/failure tracking
- **Watcher event history** showing detected changes
- **Data export capabilities** for downloaded reports
- **Interactive filters** to explore your data

---

## 🎯 Step 6: Understanding What You've Built

Let's review what you've accomplished:

### Your ETL Pipeline
- **Extracted** data from a public API
- **Transformed** it by cleaning and adding metadata
- **Loaded** it into both JSON and CSV formats
- **Monitored** the process with comprehensive logging

### Your Watcher
- **Monitored** a website for content changes
- **Extracted** specific data (quotes) from HTML
- **Detected** changes using custom logic
- **Recorded** events when changes occur

### Key Watchtower Features You Used
- **Configuration management** (automatic settings)
- **Logging system** (detailed execution logs)
- **Data organization** (structured file storage)
- **Error handling** (graceful failure management)
- **Performance tracking** (execution metrics)

---

## 🚀 Next Steps

Now that you understand the basics, here are some great next steps:

### Immediate Next Steps
1. **Customize your ETL**: Modify `my_first_etl.py` to work with a different API
2. **Enhance your watcher**: Update `my_first_watcher.py` to monitor your favorite website
3. **Explore the dashboard**: Spend time with the Streamlit interface

### Intermediate Challenges
1. **[Advanced ETL Patterns](../etl/advanced-etl-patterns.md)**: Learn complex data transformations
2. **[Dashboard Customization](../dashboard/dashboard-customization.md)**: Create custom visualizations
3. **[Error Handling and Recovery](../etl/error-handling-recovery.md)**: Build robust pipelines

### Advanced Topics
1. **[Custom Component Development](../architecture/custom-component-development.md)**: Extend Watchtower
2. **[Production Deployment](../operations/production-deployment.md)**: Deploy to production
3. **[Plugin System](../architecture/plugin-system-tutorial.md)**: Create reusable extensions

### Real-World Projects
1. **[News Aggregation Platform](../use-cases/news-aggregation-platform.md)**: Build a complete news system
2. **[E-commerce Price Monitoring](../use-cases/ecommerce-price-monitoring.md)**: Track product prices
3. **[Social Media Analytics](../use-cases/social-media-analytics.md)**: Monitor social trends

---

## 🆘 Troubleshooting Common Issues

### "Module not found" errors
```bash
# Make sure you're in the right directory
cd watchtower

# Activate your virtual environment
poetry shell  # or source .venv/bin/activate

# Reinstall dependencies
poetry install  # or pip install -r requirements.txt
```

### Playwright browser issues
```bash
# Reinstall browsers
playwright install

# Check if browsers are installed
playwright --version
```

### Permission errors on Windows
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port already in use (Dashboard)
```bash
# Use a different port
streamlit run src/web/fullstreamlit/app.py --server.port 8502
```

### Still having issues?
- Check our [Installation Troubleshooting Guide](installation-troubleshooting.md)
- Browse existing [GitHub Issues](https://github.com/josmerod/watchtower/issues)
- Create a new issue with detailed error information

---

## 🎉 Congratulations!

You've successfully completed the Watchtower beginner's guide! You now know how to:

✅ Install and configure Watchtower  
✅ Create and run ETL pipelines  
✅ Set up website watchers  
✅ Use the dashboard interface  
✅ Understand the project structure  
✅ Know where to go next for advanced features  

**You're ready to start building real-world data monitoring solutions with Watchtower!**

---

## 📚 Additional Resources

- **[Main Documentation](../../README.md)**: Complete project overview
- **[API Reference](../development/api-reference.md)**: Detailed technical documentation
- **[Contributing Guide](../../CONTRIBUTING.md)**: Help improve Watchtower
- **[Use Cases](../use-cases/)**: Real-world application examples
- **[GitHub Repository](https://github.com/josmerod/watchtower)**: Source code and issues

Happy monitoring! 🚀
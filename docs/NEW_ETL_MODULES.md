# New ETL Modules and Mining Tools

This document describes the **7 new data collection tools** implemented for the Watchtower project.

## 📊 Overview

The new tools significantly expand data collection capabilities across:
- **Developer Communities** (DEV Community, Indie Hackers, Lobsters)
- **Product Innovation** (Product Hunt)
- **Open Source Trends** (GitHub Trends)
- **Job Market Analysis** (Tech Jobs)
- **Cryptocurrency Sentiment** (Multi-platform sentiment analysis)

## 🔧 ETL Modules (src/etl/news/)

### 1. DEV Community ETL
**File:** `src/etl/news/news_get_devto.py`

**Purpose:** Fetches articles, discussions, and trending content from DEV Community

**Features:**
- Tracks 20+ popular programming tags (webdev, javascript, python, react, ai, etc.)
- Engagement scoring and trend analysis
- Content classification (tutorial, tips, review, news, career)
- Reading difficulty assessment (beginner, intermediate, advanced)
- Popularity categorization (viral, high, medium, low)

**Usage:**
```bash
python src/etl/news/news_get_devto.py
```

**Output:**
- `data/dev_community/dev_community_latest.json`
- `data/dev_community/dev_community_latest.csv`

### 2. Product Hunt ETL
**File:** `src/etl/news/news_get_producthunt.py`

**Purpose:** Fetches product launches, trending products, and innovation data

**Features:**
- Tracks 15+ topics (AI, developer-tools, SaaS, productivity, fintech, etc.)
- Launch success scoring and potential assessment
- Innovation level categorization (standard, innovative, revolutionary)
- Launch phase tracking (launch_day, launch_week, post_launch, established)
- Maker and hunter information extraction

**Usage:**
```bash
python src/etl/news/news_get_producthunt.py
```

**Output:**
- `data/product_hunt/product_hunt_latest.json`
- `data/product_hunt/product_hunt_latest.csv`

### 3. Indie Hackers ETL
**File:** `src/etl/news/news_get_indiehackers.py`

**Purpose:** Scrapes startup/entrepreneur discussions and revenue sharing posts

**Features:**
- Tracks 10+ groups (bootstrapped, saas, makers, founders, revenue, growth, etc.)
- Post categorization (revenue_sharing, product_launch, growth_marketing, etc.)
- Priority scoring based on content analysis and engagement
- Freshness indicators (very_fresh, fresh, recent, older)
- Interest level assessment (high, medium, low, new)

**Usage:**
```bash
python src/etl/news/news_get_indiehackers.py
```

**Output:**
- `data/indie_hackers/indiehackers_posts_latest.json`
- `data/indie_hackers/indiehackers_posts_latest.csv`

### 4. Lobsters ETL
**File:** `src/etl/news/news_get_lobsters.py`

**Purpose:** Scrapes lobste.rs for high-quality tech discussions and programming content

**Features:**
- Tracks 18+ tags (programming, security, AI, databases, devops, cryptography, etc.)
- Quality indicators (high, medium, decent, emerging)
- Discussion potential scoring
- Content type classification (academic, open_source, blog_post, video, news, etc.)
- Story categorization (ai_ml, security, web_development, etc.)

**Usage:**
```bash
python src/etl/news/news_get_lobsters.py
```

**Output:**
- `data/lobsters/lobsters_stories_latest.json`
- `data/lobsters/lobsters_stories_latest.csv`

### 5. GitHub Trends ETL
**File:** `src/etl/news/news_get_gittrends.py`

**Purpose:** Tracks trending GitHub repositories, popular topics, and open-source innovation

**Features:**
- Monitors 10+ programming languages (Python, JavaScript, TypeScript, Rust, Go, etc.)
- Repository activity scoring and trending analysis
- Project maturity classification (new, young, mature, established)
- Category detection (ai_ml, web_development, mobile, devops, security, etc.)
- Developer activity patterns and popularity metrics

**Usage:**
```bash
python src/etl/news/news_get_gittrends.py
```

**Output:**
- `data/github_trends/github_trends_latest.json`
- `data/github_trends/github_trends_latest.csv`

### 6. Tech Jobs ETL
**File:** `src/etl/news/news_get_techjobs.py`

**Purpose:** Analyzes technology job market trends, salary data, and skill demand

**Features:**
- Tracks 20+ job roles (Software Engineer, Data Scientist, DevOps Engineer, etc.)
- Salary analysis and market trends
- Skills demand tracking with hot skills identification
- Location tier analysis (tier_1, tier_2, tier_3, remote)
- Company tier classification and attractiveness scoring
- Job market analytics with trend analysis

**Usage:**
```bash
python src/etl/news/news_get_techjobs.py
```

**Output:**
- `data/tech_jobs/tech_jobs_latest.json`
- `data/tech_jobs/tech_jobs_latest.csv`
- `data/tech_jobs/tech_jobs_analysis_latest.json`

## ⛏️ Mining Tools (src/miners/)

### 7. Cryptocurrency Sentiment Miner
**File:** `src/miners/crypto_sentiment_miner.py`

**Purpose:** Monitors cryptocurrency sentiment across multiple platforms

**Features:**
- Tracks 16 major cryptocurrencies (Bitcoin, Ethereum, Cardano, Solana, etc.)
- Multi-platform analysis (Reddit, news sources, social media)
- 5-tier sentiment scoring (very_negative to very_positive)
- Platform-specific credibility scoring
- Influence metrics and engagement analysis
- Market trend aggregation and confidence scoring

**Usage:**
```bash
python src/miners/crypto_sentiment_miner.py
```

**Output:**
- `data/crypto_sentiment/crypto_sentiment_raw_latest.json` (Individual posts)
- `data/crypto_sentiment/crypto_sentiment_aggregated_latest.json` (Summary analysis)
- `data/crypto_sentiment/crypto_sentiment_raw_latest.csv`

## 📊 Data Schema

### Common Fields
All ETL modules include these standard fields:
- `id`: Unique identifier
- `title`: Content title
- `url`: Source URL
- `fetched_at`: Timestamp when data was collected
- `platform`: Source platform name
- `engagement_score`: Calculated engagement metric

### Platform-Specific Fields

#### DEV Community
- `reading_time_minutes`: Estimated reading time
- `tag_list`: Programming tags
- `content_type`: tutorial, tips, review, news, career
- `popularity_category`: viral, high, medium, low

#### Product Hunt
- `votes_count`: Number of votes
- `launch_success_score`: Launch performance metric
- `innovation_level`: standard, innovative, revolutionary
- `makers`: Product creator information

#### Indie Hackers
- `post_category`: revenue_sharing, product_launch, etc.
- `priority_score`: Content importance ranking
- `freshness`: Time-based relevance indicator

#### Lobsters
- `score`: Community score
- `quality_indicator`: Content quality assessment
- `discussion_potential`: Likelihood of generating discussion

#### GitHub Trends
- `stars_count`: Repository stars
- `trending_score`: Overall trending metric
- `maturity`: new, young, mature, established
- `category`: ai_ml, web_development, mobile, etc.

#### Tech Jobs
- `salary_amount`: Annual salary
- `attractiveness_score`: Job attractiveness ranking
- `location_tier`: tier_1, tier_2, tier_3, remote
- `job_category`: ai_ml, frontend, backend, fullstack, etc.

#### Crypto Sentiment
- `sentiment_score`: Numerical sentiment (-2 to +2)
- `sentiment_label`: Categorical sentiment
- `detected_cryptos`: List of mentioned cryptocurrencies
- `credibility_score`: Source reliability (news only)

## 🚀 Getting Started

1. **Run Individual ETL Modules:**
   ```bash
   # Run DEV Community ETL
   python src/etl/news/news_get_devto.py
   
   # Run Product Hunt ETL
   python src/etl/news/news_get_producthunt.py
   
   # Run Indie Hackers ETL
   python src/etl/news/news_get_indiehackers.py
   
   # Run Lobsters ETL
   python src/etl/news/news_get_lobsters.py
   
   # Run GitHub Trends ETL
   python src/etl/news/news_get_gittrends.py
   
   # Run Tech Jobs ETL
   python src/etl/news/news_get_techjobs.py
   
   # Run Crypto Sentiment Miner
   python src/miners/crypto_sentiment_miner.py
   ```

2. **Run All New Modules at Once:**
   ```bash
   # Windows
   run_new_etl_modules.bat
   
   # Unix/Linux/Mac
   ./run_new_etl_modules.sh
   ```

3. **Integration with Existing ETL Pipeline:**
   The modules have been integrated into your existing `run_all_etl.bat/sh` scripts and will run alongside your current ETL processes.

4. **Output Analysis:**
   - JSON files contain complete data with nested structures
   - CSV files contain flattened data for easy analysis in spreadsheet applications
   - "latest" files are always updated with the most recent run

## 📈 Performance and Rate Limiting

All modules implement:
- Respectful rate limiting to avoid overwhelming source APIs
- Retry logic for network failures
- Comprehensive error handling and logging
- Duplicate detection and filtering

## 🔧 Configuration

Each module can be customized by modifying:
- Tags/topics to track
- Number of pages to fetch
- Rate limiting delays
- Output formats

## 🛠️ Dependencies

New dependencies introduced:
- `requests`: HTTP client (already in project)
- `pandas`: Data processing (already in project)
- Standard library modules: `json`, `csv`, `datetime`, `re`, `hashlib`

## 📝 Logging

All modules use the project's standard logging system and output detailed information about:
- Data collection progress
- Processing statistics
- Error conditions
- Summary metrics

## 🎯 Next Steps

1. **Schedule Regular Runs:** The new modules are now integrated into your ETL scheduler
2. **Data Analysis:** Use the collected data for trend analysis and insights
3. **Integration:** Connect the data to your existing analytics and visualization tools
4. **Customization:** Adjust tracking parameters based on your specific needs

## 🤝 Contributing

When extending these modules:
1. Follow the existing code patterns
2. Maintain consistent error handling
3. Add comprehensive logging
4. Include data validation
5. Update this documentation 
# Watchtower Project Functions

## ETL Processes

### ArXiv ETL
- Collection of recent ArXiv papers related to generative AI and machine learning
- Classification of papers into clusters using NLP techniques
- Extraction of keywords from paper abstracts
- Detection and extraction of GitHub repository links from papers
- Integration with Papers With Code API to provide additional metadata
- Generation of cluster statistics and visualization data
- Saving processed papers to JSON and CSV formats

### Games ETL
- Collection of game deals from IsThereAnyDeal RSS feed
- Collection of game bundles from various sources including IsThereAnyDeal
- Collection of game giveaways and free games
- Collection of Humble Bundle offers with pricing tiers and included games
- Sorting and categorization of deals by discount percentage
- Extraction of pricing information and discount values
- Saving processed game information to JSON and CSV formats

### News/Goldigging ETL
- Collection of news articles from various tech sources
- Extraction and processing of HackerNews posts and articles
- Collection of content from Medium related to generative AI
- Collection of content from specialized AI/ML blogs
- Processing and categorization of news content
- Storage of processed news in structured formats

## Miners

### Udemy Universal Miner
- Automatic discovery of free and discounted Udemy courses
- Course enrollment automation
- Filtering courses by ratings and reviews
- Data extraction for course metadata (ratings, student counts, etc.)
- Course categorization and organization
- Regular updates of course availability

### Steam ASF Miner (Windows)
- Integration with ArchiSteamFarm for automated Steam operations
- Free game package collection
- Steam wishlist monitoring
- Game deal notifications
- Configuration management for multiple Steam accounts

## Streamlit Dashboard

### Core Functionality
- Responsive layout adapting to different device screen sizes
- Tab-based navigation between different content sections
- Unified styling and theme across the entire application
- Caching of data to improve performance with TTL (time-to-live) settings
- Logging of user interactions and system events

### ArXiv Papers Component
- Display of recent ArXiv papers related to generative AI and machine learning
- Interactive paper cards with links to PDF and ArXiv page
- Filtering papers by cluster/category
- Visualization of paper clusters with interactive charts
- Collapsible paper abstracts to save screen space
- Rating system for papers
- Personal recommendations based on user preferences
- Keyword extraction and highlighting
- Search functionality across paper abstracts and titles
- Integration with user profiles for personalized recommendations

### Games Tab
- Display of current game deals with discount information
- Display of game bundles from various sources
- Display of free game giveaways with expiry dates
- Filtering of game deals by store and discount percentage
- Sorting of deals by various criteria (price, discount, etc.)
- Clickable links to deal pages
- Clean visualization of pricing information

### Courses Tab
- Display of free and discounted online courses from Udemy
- Filtering courses by category, rating, and platform
- Sorting of courses by various criteria
- Course metadata visualization (student count, rating, etc.)
- Direct links to course enrollment pages
- Course expiry date tracking

### Videos Tab
- Curation and display of YouTube videos related to AI/ML topics
- Organization of videos by category and channel
- Embedded video previews
- Video metadata display (views, upload date, etc.)
- Channel subscription suggestions

### News Tab
- Display of recent news articles from various tech sources
- HackerNews integration showing popular technology posts
- Filtering news by source and category
- Article metadata display (publication date, source, etc.)
- Reading time estimates for articles

### Watchers Tab
- Display of data from various automated watchers
- Status monitoring of watcher services
- Configuration options for watcher behavior
- Visualization of watcher activity statistics

### Events Tab
- Display of upcoming technology events and conferences
- Filtering events by category and date
- Calendar view of scheduled events
- Event reminder functionality
- Event metadata display (location, speakers, etc.)

### Shortcuts Tab
- Quick access links to frequently used resources
- Customizable shortcut organization
- Visual categorization of shortcuts
- Quick filtering and search of shortcuts

### Admin Tab
- System monitoring and performance statistics
- Manual trigger of ETL processes
- Log viewing and analysis
- Configuration management for the application
- User management functionality

## Utility Functions

### Data Processing
- File system utilities for ensuring directory structures
- Data loading utilities with error handling
- Caching mechanisms for frequently accessed data
- Format conversion utilities (JSON, CSV, etc.)

### User Experience
- Clickable link formatting in dataframes
- Timestamp formatting for readability
- Responsive column layout calculations
- URL cleaning and normalization

### Recommender System
- Personal recommendation engine based on user interactions
- Interest tracking from user behavior
- Item similarity calculations
- User profile management

### NLP and Processing
- Text classification using machine learning
- Keyword extraction from text
- Clustering of similar content
- Content summarization capabilities

### Logging and Monitoring
- Centralized logging system
- Error handling and reporting
- Performance monitoring
- Operation auditing 

### IDEAS

- Reddit Content Pipeline: Implement data extraction from relevant subreddits using techniques similar to YARS (Yet Another Reddit Scrapper)
  - Relevant subreddits (trending, 5 per subreddit):
    - r/ollama
    - 
- Internet Radio/Music Pipeline: Collect and process music streaming data inspired by the MIRAGE dashboard (use it as a player???) -> MIRAGE online dashboard @ https://mirage-project.org/
  - Academia.edu Miner: Discover academic papers beyond ArXiv
  - Internet Radio/Music Miner: Track music trends and discover internet radio stations 
- Relevant new Github Repositories:
  - Scrap https://github.com/trending?since=weekly&spoken_language_code=en (see if more than 10 can be scraped, is there an API???)
  - 

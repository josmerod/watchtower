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

### GitHub Trending ETL
- Collection of trending GitHub repositories from GitHub's trending page
- Extraction of repository metadata (stars, forks, language, description)
- Filtering repositories by programming language and time period
- Detection of AI/ML related repositories using keyword analysis
- Tracking repository growth metrics and popularity trends
- Integration with GitHub API for enhanced metadata collection
- Saving processed repository data to JSON and CSV formats

### Reddit Content ETL
- Collection of posts from relevant technology and AI subreddits
- Extraction of post metadata (upvotes, comments, awards)
- Content filtering based on relevance scores and engagement metrics
- Subreddit-specific data processing for r/MachineLearning, r/artificial, r/programming
- Comment thread analysis for trending topics
- Integration with Reddit API for real-time data collection
- Saving processed Reddit content to structured formats

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

### Academia Miner
- Discovery of academic papers from multiple sources beyond ArXiv
- Integration with Academia.edu for paper collection
- Cross-referencing papers with citation databases
- Author network analysis and collaboration mapping
- Research trend identification across academic platforms
- Automated paper categorization and tagging

### Music/Radio Discovery Miner
- Collection of internet radio station metadata and streaming information
- Music trend analysis from various streaming platforms
- Discovery of new artists and genres through algorithmic analysis
- Integration with music APIs for enhanced metadata
- Playlist generation based on trending content
- Radio station categorization by genre and region

## Watchers

### Website Content Watchers
- Generic web page monitoring for content changes
- Price tracking for e-commerce products
- News article monitoring for specific keywords
- Social media post tracking for trending topics
- API endpoint monitoring for data availability
- Custom threshold-based alerting system

### GitHub Repository Watchers
- Monitoring specific repositories for new releases
- Tracking star count and fork growth
- Issue and pull request activity monitoring
- Contributor activity analysis
- License and documentation change detection
- Security vulnerability alerts

### Course Platform Watchers
- Monitoring course platforms for new free courses
- Price change detection for paid courses
- Course rating and review tracking
- Instructor activity monitoring
- Platform-specific promotion detection
- Enrollment deadline tracking

## Streamlit Dashboard

### Core Functionality
- Responsive layout adapting to different device screen sizes
- Tab-based navigation between different content sections
- Unified styling and theme across the entire application
- Caching of data to improve performance with TTL (time-to-live) settings
- Logging of user interactions and system events
- Real-time data refresh capabilities
- Export functionality for filtered datasets
- Advanced search and filtering across all data types

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
- Price history tracking and trend analysis
- Wishlist integration with deal alerts

### Courses Tab
- Display of free and discounted online courses from Udemy
- Filtering courses by category, rating, and platform
- Sorting of courses by various criteria
- Course metadata visualization (student count, rating, etc.)
- Direct links to course enrollment pages
- Course expiry date tracking
- Learning path recommendations
- Progress tracking for enrolled courses

### Videos Tab
- Curation and display of YouTube videos related to AI/ML topics
- Organization of videos by category and channel
- Embedded video previews
- Video metadata display (views, upload date, etc.)
- Channel subscription suggestions
- Playlist creation and management
- Video recommendation engine

### News Tab
- Display of recent news articles from various tech sources
- HackerNews integration showing popular technology posts
- Filtering news by source and category
- Article metadata display (publication date, source, etc.)
- Reading time estimates for articles
- Trending topic identification
- News sentiment analysis

### GitHub Tab
- Display of trending GitHub repositories
- Repository filtering by language, stars, and activity
- Repository metadata visualization (contributors, issues, etc.)
- Direct links to repository pages
- Star history tracking and visualization
- Developer activity monitoring
- Repository recommendation engine

### Reddit Tab
- Display of trending posts from technology subreddits
- Post filtering by subreddit, score, and engagement
- Comment thread analysis and visualization
- Trending topic identification across subreddits
- User sentiment analysis
- Subreddit activity monitoring
- Cross-platform content correlation

### Music Tab
- Display of trending music and radio stations
- Genre-based filtering and categorization
- Artist discovery and recommendation
- Playlist management and sharing
- Radio station directory with streaming links
- Music trend analysis and visualization
- Integration with music streaming services

### Watchers Tab
- Display of data from various automated watchers
- Status monitoring of watcher services
- Configuration options for watcher behavior
- Visualization of watcher activity statistics
- Alert management and notification settings
- Watcher performance metrics

### Events Tab
- Display of upcoming technology events and conferences
- Filtering events by category and date
- Calendar view of scheduled events
- Event reminder functionality
- Event metadata display (location, speakers, etc.)
- Virtual event integration
- Event recommendation based on interests

### Shortcuts Tab
- Quick access links to frequently used resources
- Customizable shortcut organization
- Visual categorization of shortcuts
- Quick filtering and search of shortcuts
- Usage analytics for shortcuts
- Dynamic shortcut suggestions

### Admin Tab
- System monitoring and performance statistics
- Manual trigger of ETL processes
- Log viewing and analysis
- Configuration management for the application
- User management functionality
- Database administration tools
- System health monitoring

## Utility Functions

### Data Processing
- File system utilities for ensuring directory structures
- Data loading utilities with error handling
- Caching mechanisms for frequently accessed data
- Format conversion utilities (JSON, CSV, Parquet)
- Data validation and cleaning pipelines
- Batch processing capabilities
- Memory-efficient data streaming

### User Experience
- Clickable link formatting in dataframes
- Timestamp formatting for readability
- Responsive column layout calculations
- URL cleaning and normalization
- Dynamic content loading
- Progressive data rendering
- Accessibility enhancements

### Recommender System
- Personal recommendation engine based on user interactions
- Interest tracking from user behavior
- Item similarity calculations using machine learning
- User profile management and preferences
- Collaborative filtering algorithms
- Content-based recommendation strategies
- Hybrid recommendation approaches

### NLP and Processing
- Text classification using machine learning models
- Keyword extraction from text using TF-IDF and embeddings
- Clustering of similar content using vector similarity
- Content summarization capabilities
- Sentiment analysis for user-generated content
- Named entity recognition for content tagging
- Topic modeling for content organization

### API Integration
- GitHub API integration for repository data
- Reddit API integration for post collection
- Music streaming API integrations
- Academic database API connections
- Rate limiting and quota management
- API response caching and optimization
- Error handling and retry mechanisms

### Monitoring and Analytics
- Real-time system performance monitoring
- User behavior analytics and tracking
- Content engagement metrics
- ETL process performance analysis
- Resource usage optimization
- Automated alerting and notifications
- Custom dashboard metrics

### Logging and Monitoring
- Centralized logging system with structured logs
- Error handling and reporting with context preservation
- Performance monitoring with metrics collection
- Operation auditing and compliance tracking
- Log aggregation and analysis tools
- Real-time monitoring dashboards
- Automated log rotation and archival

## Future Development Ideas

### Content Discovery
- **Academic Paper Discovery**: Expand beyond ArXiv to include IEEE, ACM, and other academic databases
- **Patent Mining**: Track technology patents and innovation trends
- **Conference Proceedings**: Monitor academic conference publications and presentations
- **Technical Blog Aggregation**: Collect content from engineering blogs and technical publications

### Social Media Integration
- **Twitter/X Content Pipeline**: Track trending hashtags and influential tech personalities
- **LinkedIn Professional Content**: Monitor industry insights and professional discussions
- **Discord Community Monitoring**: Track discussions in relevant tech communities
- **Telegram Channel Aggregation**: Collect content from technology-focused channels

### Enhanced Analytics
- **Cross-Platform Trend Analysis**: Identify trending topics across multiple platforms
- **Influence Network Mapping**: Track how information spreads across different sources
- **Predictive Content Modeling**: Predict which content will become popular
- **Automated Content Curation**: AI-driven content selection and ranking

### Advanced Features
- **Multi-Language Support**: Expand content collection to non-English sources
- **Real-Time Notifications**: Push notifications for high-priority content
- **Mobile Application**: Native mobile app for content consumption
- **API Marketplace**: Public API for accessing curated content data

### Integration Opportunities
- **Slack/Discord Bots**: Automated content sharing in team channels
- **Email Digest Generation**: Personalized weekly/daily content summaries
- **Calendar Integration**: Sync events and deadlines with personal calendars
- **Note-Taking Integration**: Connect with Obsidian, Notion, or other knowledge management tools

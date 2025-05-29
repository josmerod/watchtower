# Watchtower Architecture Overview

This document provides a comprehensive overview of Watchtower's **actual implementation**, design patterns, and component interactions based on the current codebase.

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Real Architecture](#real-architecture)
3. [Actual Component Design](#actual-component-design)
4. [Data Flow Patterns](#data-flow-patterns)
5. [Technology Stack](#technology-stack)
6. [Implementation Patterns](#implementation-patterns)
7. [File Organization](#file-organization)

---

## System Overview

Watchtower is a **practical data monitoring and ETL framework** built around **specific use cases** including ArXiv paper monitoring, course aggregation, news tracking, and technology trend analysis.

### Key Implementation Characteristics

- **🎯 Domain-Specific**: Built for specific data sources (ArXiv, courses, news, etc.)
- **📊 Streamlit-Centered**: Web interface built with Streamlit for dashboard visualization
- **🔄 ETL-Focused**: Heavy emphasis on Extract-Transform-Load pipelines
- **📁 File-Based Storage**: Primarily JSON and CSV file storage with some database integration
- **🕸️ Web Scraping**: Extensive use of web scraping and API integration
- **⚡ Performance-Optimized**: Caching and optimization for Streamlit performance

### Actual System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Watchtower System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Streamlit Frontend                     │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │ Dashboard   │ │  Tab System │ │ Data Views  │   │   │
│  │ │ Components  │ │ Navigation  │ │ & Metrics   │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                ETL Pipelines                        │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │ ArXiv ETL   │ │ Course ETL  │ │  News ETL   │   │   │
│  │ │             │ │             │ │             │   │   │
│  │ │• Papers     │ │• Udemy      │ │• HackerNews │   │   │
│  │ │• Classification│• Coursera   │ │• DevCommunity│   │   │
│  │ │• GitHub Links│ │• Skills     │ │• Security   │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Watcher System                        │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │ ArXiv       │ │ MS Skills   │ │ Enhanced    │   │   │
│  │ │ Watcher     │ │ Watcher     │ │ Watchers    │   │   │
│  │ │             │ │             │ │             │   │   │
│  │ │• RSS Feeds  │ │• Web Scraping│ │• Advanced   │   │   │
│  │ │• XML Parsing│ │• Change Det. │ │• Multi-src  │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Data Storage                         │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │    JSON     │ │    CSV      │ │   Events    │   │   │
│  │ │   Files     │ │  Exports    │ │    Files    │   │   │
│  │ │             │ │             │ │             │   │   │
│  │ │• Raw Data   │ │• Processed  │ │• Changes    │   │   │
│  │ │• Metadata   │ │• Analytics  │ │• Alerts     │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Real Architecture

### 1. Actual Layered Structure

Based on the codebase analysis, Watchtower follows this **actual architecture**:

#### **Frontend Layer (`src/web/fullstreamlit/`)**
- **Streamlit Application**: Main dashboard interface (`app.py`)
- **Component System**: Modular tab-based components for different data types
- **Performance Optimization**: Ultra-optimized data services and caching
- **Responsive Design**: Mobile-friendly UI with custom CSS

#### **ETL Layer (`src/etl/`)**
- **BaseETL Framework**: Abstract base class with metrics, checkpointing, and error handling
- **Domain-Specific ETLs**: ArXiv, Course, News, Security, Games pipelines
- **Data Processing**: Transformation, enrichment, and classification
- **File-Based Output**: JSON and CSV exports with structured storage

#### **Watcher Layer (`src/watchers/`)**
- **BaseWatcher**: Abstract monitoring framework with state persistence
- **Specialized Watchers**: ArXiv, Microsoft Skills, Enhanced content monitoring
- **Change Detection**: Value comparison and event recording
- **Event System**: JSON-based event logging and state management

#### **Infrastructure Layer (`src/utils/`, `src/config/`, `src/exceptions/`)**
- **Configuration Management**: Pydantic-based settings with environment support
- **Exception Handling**: Structured error handling with context preservation
- **Logging System**: Structured logging with performance monitoring
- **Utilities**: File system, NLP classification, GitHub integration, course deduplication

### 2. Real Component Interactions

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Streamlit  │      │   ETL       │      │   Storage   │
│  Dashboard  │      │ Pipelines   │      │   System    │
│             │      │             │      │             │
│ • Tab Views │◄────►│ • Data Proc │◄────►│ • JSON      │
│ • Metrics   │      │ • Transform │      │ • CSV       │
│ • Filters   │      │ • Enrich    │      │ • Events    │
│ • Analytics │      │ • Classify  │      │ • State     │
└─────────────┘      └─────────────┘      └─────────────┘
                             ▲
                             │
                     ┌─────────────┐
                     │  Watchers   │
                     │             │
                     │ • Monitor   │
                     │ • Detect    │
                     │ • Alert     │
                     │ • Event Log │
                     └─────────────┘
```

---

## Actual Component Design

### 1. Configuration System (`src/config/`)

**Real Implementation**:
- `Settings`: Main Pydantic settings class with environment detection
- `ConfigModels`: Specialized models for Database, Logging, Scraping, ETL, etc.
- **Environment Variables**: Nested delimiter support (`DATABASE__URL`)
- **Auto-Discovery**: Project root detection and path resolution

**Actual Patterns**:
```python
class Settings(BaseSettings):
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    etl: ETLConfig = Field(default_factory=ETLConfig)
    watchers: WatcherConfig = Field(default_factory=WatcherConfig)
    streamlit: StreamlitConfig = Field(default_factory=StreamlitConfig)
```

### 2. ETL Framework (`src/etl/`)

**Real Implementation**:
- `BaseETL`: Abstract class with metrics, checkpointing, batch processing
- `ArxivETL`: Complete ArXiv paper processing with NLP classification
- `SimpleETL` & `DataFrameETL`: Lightweight ETL variants
- **File-Based Processing**: JSON/CSV input and output

**Actual Processing Pipeline**:
```python
class ArxivETL:
    def extract(self) -> List[Dict[str, Any]]:
        # Extract from ArXiv via watcher
        
    def transform(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # NLP classification, GitHub enrichment, PapersWithCode integration
        
    def load(self, transformed_papers: List[Dict[str, Any]]):
        # Save to JSON/CSV with statistics
```

### 3. Watcher System (`src/watchers/`)

**Real Implementation**:
- `BaseWatcher`: State persistence, event recording, change detection
- `ArxivWatcher`: RSS feed monitoring with XML parsing
- `MSSkillsWatcher`: Complex web scraping with dynamic content
- `EnhancedWatcher`: Advanced multi-source monitoring

**Actual Workflow**:
```python
class BaseWatcher:
    def check(self):
        html_content = self.fetch_page()
        current_value = self.extract_value(html_content)
        if self.has_changed(self.previous_state["last_value"], current_value):
            self.trigger_alarm(old_value, current_value)
            self._record_event("change_detected", old_value, current_value)
```

### 4. Streamlit Frontend (`src/web/fullstreamlit/`)

**Real Implementation**:
- **Tab-Based Architecture**: Modular components for different data types
- **Performance Optimization**: Ultra-optimized data service with caching
- **Component System**: Separate modules for videos, courses, news, papers, etc.
- **Custom Styling**: CSS-based theming with responsive design

**Actual Tab Components**:
- `arxiv_papers.py`: ArXiv paper visualization
- `courses_tab.py`: Course aggregation and filtering
- `news_tab.py`: News feed compilation
- `monitoring_tab.py`: System health and metrics
- `innovation_tab.py`: Technology trend analysis

### 5. Exception System (`src/exceptions/`)

**Real Implementation**:
- `WatchtowerError`: Base exception with error codes and context
- **Domain-Specific Exceptions**: ETLError, WatcherError, ValidationError
- **Context Preservation**: Rich error information with timestamps
- **Structured Logging**: Integration with logging system

```python
class WatchtowerError(Exception):
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        self.timestamp = datetime.utcnow()
```

---

## Data Flow Patterns

### 1. ETL Data Flow (Actual)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  External   │    │   Watcher   │    │     ETL     │    │   Storage   │
│  Sources    │    │             │    │   Process   │    │             │
│             │    │             │    │             │    │             │
│ • ArXiv RSS │───►│ • Monitor   │───►│ • Extract   │───►│ • JSON      │
│ • Course    │    │ • Parse     │    │ • Transform │    │ • CSV       │
│   APIs      │    │ • Store     │    │ • Classify  │    │ • Events    │
│ • News      │    │ • Event     │    │ • Enrich    │    │ • Reports   │
│   Feeds     │    │             │    │ • Load      │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ▼
                                   ┌─────────────┐
                                   │  Streamlit  │
                                   │  Dashboard  │
                                   │             │
                                   │ • Visualize │
                                   │ • Filter    │
                                   │ • Analyze   │
                                   │ • Export    │
                                   └─────────────┘
```

### 2. Watcher Data Flow (Actual)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Target Site │    │   Watcher   │    │   State     │    │   Events    │
│             │    │             │    │ Management  │    │             │
│ • ArXiv     │───►│ • Fetch     │───►│ • Compare   │───►│ • Change    │
│ • MS Skills │    │ • Parse     │    │ • Update    │    │   Events    │
│ • Course    │    │ • Extract   │    │ • Persist   │    │ • Alerts    │
│   Sites     │    │   Value     │    │             │    │ • Logs      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  JSON State │
                   │             │
                   │ • Last Val  │
                   │ • Timestamp │
                   │ • Metadata  │
                   └─────────────┘
```

### 3. Streamlit Data Flow (Actual)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   JSON/CSV  │    │    Data     │    │  Component  │    │    User     │
│   Files     │    │   Service   │    │   System    │    │ Interface   │
│             │    │             │    │             │    │             │
│ • Papers    │───►│ • Cache     │───►│ • Tabs      │───►│ • Dashboard │
│ • Courses   │    │ • Filter    │    │ • Metrics   │    │ • Filters   │
│ • News      │    │ • Aggregate │    │ • Charts    │    │ • Analytics │
│ • Events    │    │ • Optimize  │    │ • Tables    │    │ • Export    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Technology Stack

### Actually Used Technologies

| Component | Technology | Actual Usage |
|-----------|------------|--------------|
| **Language** | Python 3.10+ | Core implementation language |
| **Web Framework** | Streamlit | Main dashboard interface |
| **Data Processing** | pandas, JSON | Primary data manipulation |
| **Web Scraping** | requests, BeautifulSoup | Content extraction |
| **Configuration** | Pydantic Settings | Settings management |
| **File Storage** | JSON, CSV | Primary data persistence |
| **Classification** | scikit-learn | NLP content classification |
| **External APIs** | ArXiv API, GitHub API | Data source integration |
| **Logging** | Python logging | System monitoring |

### Supporting Libraries

| Purpose | Library | Usage |
|---------|---------|-------|
| **RSS Parsing** | feedparser | ArXiv RSS feeds |
| **HTTP Requests** | requests | Web scraping |
| **Data Science** | pandas, numpy | Data processing |
| **Machine Learning** | scikit-learn | Classification |
| **Date/Time** | datetime | Timestamps |
| **File Operations** | pathlib, os | File management |
| **Performance** | @st.cache_data | Streamlit caching |

---

## Implementation Patterns

### 1. Factory Pattern (Configuration)

```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 2. Template Method (ETL)

```python
class BaseETL(ABC):
    def run(self) -> ETLMetrics:
        data = self.extract()           # Implemented by subclass
        transformed = self.transform(data)  # Implemented by subclass  
        self.load(transformed)          # Implemented by subclass
        return self.metrics
```

### 3. State Pattern (Watchers)

```python
class BaseWatcher:
    def __init__(self):
        self.previous_state = self._load_state()
    
    def check(self):
        if self.has_changed(old_state, new_state):
            self._save_state(new_state)
            self._record_event("change_detected")
```

### 4. Component Pattern (Streamlit)

```python
# Tab-based modular architecture
tabs = st.tabs(["ArXiv", "Courses", "News", "Monitoring"])
with tabs[0]:
    arxiv_papers.render()
with tabs[1]:
    courses_tab.render()
```

---

## File Organization

### Actual Directory Structure

```
src/
├── config/              # Pydantic settings management
│   ├── settings.py      # Main settings class
│   └── models.py        # Configuration models
├── etl/                 # ETL pipelines
│   ├── base.py          # BaseETL framework
│   ├── arxiv/           # ArXiv processing
│   ├── news/            # News processing  
│   ├── games/           # Games processing
│   └── security/        # Security processing
├── watchers/            # Monitoring system
│   ├── base_watcher.py  # BaseWatcher framework
│   ├── arxiv_watcher.py # ArXiv monitoring
│   └── ms_skills_watcher.py # MS Skills monitoring
├── web/fullstreamlit/   # Streamlit frontend
│   ├── app.py           # Main application
│   ├── components/      # Tab components
│   └── utils/           # Data services
├── utils/               # Shared utilities
│   ├── logging.py       # Logging system
│   ├── file_system.py   # File operations
│   └── nlp_classifier.py # Classification
└── exceptions/          # Error handling
    ├── base.py          # Base exceptions
    └── etl.py           # ETL exceptions
```

### Data Organization

```
data/
├── arxiv/               # ArXiv papers
│   ├── processed/       # ETL outputs
│   └── events/          # Watcher events
├── courses/             # Course data
├── news/                # News articles
├── watchers/            # Watcher states
│   └── {watcher_name}/
│       ├── state.json   # Current state
│       └── events/      # Change events
└── models/              # ML models
    └── nlp/             # Classification models
```

This architecture represents the **actual working system** as implemented, focusing on practical data processing, monitoring, and visualization rather than theoretical enterprise patterns. The system is designed for specific use cases and optimized for the Streamlit dashboard experience. 
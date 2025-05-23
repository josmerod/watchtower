# Watchtower Architecture Overview

This document provides a comprehensive overview of Watchtower's system architecture, design patterns, and component interactions.

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Component Design](#component-design)
4. [Data Flow Patterns](#data-flow-patterns)
5. [Technology Stack](#technology-stack)
6. [Design Patterns](#design-patterns)
7. [Scalability & Performance](#scalability--performance)

---

## System Overview

Watchtower is a **professional-grade data monitoring and processing framework** built with modern Python practices and enterprise-ready patterns.

### Key Architectural Principles

- **🏗️ Modular Design**: Clear separation of concerns with pluggable components
- **⚡ Async-First**: Modern async/await patterns for scalable I/O operations
- **📊 Type Safety**: Comprehensive type hints with Pydantic validation
- **🛡️ Error Resilience**: Robust exception handling with context preservation
- **📈 Observability**: Built-in logging, metrics, and performance monitoring
- **⚙️ Configuration-Driven**: Environment-based settings with validation

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Watchtower System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ Data Sources│    │  Watchers   │    │   ETL Jobs  │    │
│  │             │    │             │    │             │    │
│  │ • RSS Feeds │    │ • Web Pages │    │ • Extract   │    │
│  │ • APIs      │    │ • Content   │    │ • Transform │    │
│  │ • Web Pages │    │ • Changes   │    │ • Load      │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Core Framework                         │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │Config Mgmt  │ │ Exception   │ │  Logging    │   │   │
│  │ │& Validation │ │ Handling    │ │& Metrics    │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Data Layer                           │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │   Files     │ │  Database   │ │    Cache    │   │   │
│  │ │ JSON/CSV    │ │  (SQLite)   │ │   Memory    │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Presentation Layer                     │   │
│  │                                                     │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │ Streamlit   │ │    API      │ │   Reports   │   │   │
│  │ │ Dashboard   │ │  Endpoints  │ │    & Logs   │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Architecture

### 1. Layered Architecture

Watchtower follows a **layered architecture** pattern with clear separation of concerns:

#### **Presentation Layer**
- **Streamlit Dashboard**: Interactive web interface for data visualization
- **API Layer**: RESTful endpoints for programmatic access (future)
- **CLI Tools**: Command-line interfaces for operations

#### **Business Logic Layer**
- **ETL Framework**: Extract, Transform, Load operations
- **Watcher System**: Content monitoring and change detection
- **Orchestrator**: Process management and scheduling

#### **Infrastructure Layer**
- **Configuration Management**: Settings and environment handling
- **Exception Framework**: Error handling and recovery
- **Logging & Metrics**: Observability and monitoring
- **Utilities**: Common functionality and helpers

#### **Data Layer**
- **File System**: JSON, CSV, and other file formats
- **Database**: SQLite (default), PostgreSQL (production)
- **Cache**: In-memory caching for performance

### 2. Component Interaction Model

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Client    │      │ Application │      │   Storage   │
│             │      │             │      │             │
│ • Dashboard │◄────►│ • ETL       │◄────►│ • Files     │
│ • CLI       │      │ • Watchers  │      │ • Database  │
│ • Scripts   │      │ • API       │      │ • Cache     │
└─────────────┘      └─────────────┘      └─────────────┘
                             │
                             ▼
                     ┌─────────────┐
                     │    Core     │
                     │             │
                     │ • Config    │
                     │ • Logging   │
                     │ • Exceptions│
                     │ • Utils     │
                     └─────────────┘
```

---

## Component Design

### 1. Configuration System (`src/config/`)

**Purpose**: Centralized configuration management with validation

**Key Components**:
- `Settings`: Main configuration class with environment detection
- `*Config`: Specialized configuration models for each component
- Environment variable support with nested configurations

**Design Patterns**:
- **Singleton Pattern**: Cached settings instance
- **Factory Pattern**: Configuration model creation
- **Strategy Pattern**: Environment-specific configurations

```python
# Configuration hierarchy
Settings
├── DatabaseConfig      # Database connections
├── LoggingConfig      # Logging configuration  
├── ScrapingConfig     # Web scraping settings
├── ETLConfig         # ETL pipeline settings
├── WatcherConfig     # Monitoring configuration
└── StreamlitConfig   # Dashboard settings
```

### 2. ETL Framework (`src/etl/`)

**Purpose**: Robust data extraction, transformation, and loading

**Key Components**:
- `BaseETL`: Abstract base class with error handling and metrics
- `SimpleETL`: Dictionary-based ETL for basic use cases
- `DataFrameETL`: DataFrame-based ETL with export capabilities

**Design Patterns**:
- **Template Method Pattern**: ETL workflow structure
- **Strategy Pattern**: Different ETL implementations
- **Observer Pattern**: Metrics and monitoring
- **Command Pattern**: ETL operations as commands

```python
# ETL inheritance hierarchy
BaseETL[InputType, OutputType]
├── SimpleETL[Dict, Dict]
├── DataFrameETL[Dict, Dict]
└── Custom ETL implementations
```

**Processing Pipeline**:
```
Extract → Validate → Transform → Batch → Load → Metrics
    ↓         ↓          ↓        ↓       ↓        ↓
 Source → Pydantic → Business → Chunks → Store → Report
         Models     Logic              
```

### 3. Watcher System (`src/watchers/`)

**Purpose**: Continuous monitoring of web content changes

**Key Components**:
- `BaseWatcher`: Abstract base class for content monitoring
- State persistence and event recording
- Configurable check intervals and change detection

**Design Patterns**:
- **Observer Pattern**: Change detection and notifications
- **State Pattern**: Watcher state management
- **Command Pattern**: Check operations
- **Strategy Pattern**: Different change detection algorithms

```python
# Watcher workflow
fetch_page() → extract_value() → has_changed() → trigger_alarm()
     ↓              ↓              ↓              ↓
  HTTP Get → Content Parse → Compare State → Record Event
```

### 4. Exception Framework (`src/exceptions/`)

**Purpose**: Comprehensive error handling with context preservation

**Key Components**:
- `WatchtowerError`: Base exception with error codes
- Specialized exceptions for each component
- Context preservation and error recovery

**Design Patterns**:
- **Chain of Responsibility**: Exception handling chain
- **Decorator Pattern**: Error handling decorators
- **Factory Pattern**: Exception creation with context

```python
# Exception hierarchy
WatchtowerError
├── ETLError
│   ├── ExtractionError
│   ├── TransformationError
│   └── LoadError
├── WatcherError
├── ConfigurationError
└── ValidationError
```

### 5. Logging System (`src/utils/logging.py`)

**Purpose**: Structured logging with performance monitoring

**Key Features**:
- **Structured JSON Logging**: Machine-readable log format
- **Performance Monitoring**: Automatic timing and metrics
- **Contextual Information**: Rich debugging context
- **Multiple Outputs**: File and console logging

**Design Patterns**:
- **Decorator Pattern**: Automatic instrumentation
- **Factory Pattern**: Logger creation
- **Strategy Pattern**: Different log formatters

---

## Data Flow Patterns

### 1. ETL Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   External  │    │     ETL     │    │   Storage   │
│   Sources   │    │   Process   │    │             │
│             │    │             │    │             │
│ • RSS Feeds │───►│ Extract     │───►│ • JSON      │
│ • APIs      │    │ Transform   │    │ • CSV       │
│ • Web Pages │    │ Load        │    │ • Database  │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Metrics   │
                   │             │
                   │ • Records   │
                   │ • Timing    │
                   │ • Errors    │
                   └─────────────┘
```

### 2. Watcher Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Target Page │    │   Watcher   │    │    Events   │
│             │    │             │    │             │
│ • HTML      │───►│ Monitor     │───►│ • Changes   │
│ • Content   │    │ Compare     │    │ • Alerts    │
│ • Structure │    │ Detect      │    │ • History   │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    State    │
                   │             │
                   │ • Last Val  │
                   │ • Timestamp │
                   │ • Metadata  │
                   └─────────────┘
```

### 3. Configuration Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Environment  │    │Configuration│    │ Components  │
│Variables    │    │ System      │    │             │
│             │───►│             │───►│ • ETL       │
│ • Env Vars  │    │ • Validation│    │ • Watchers  │
│ • .env File │    │ • Defaults  │    │ • Logging   │
│ • CLI Args  │    │ • Override  │    │ • Database  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Language** | Python 3.10+ | Modern Python features and performance |
| **Async** | asyncio, aiohttp | Scalable I/O operations |
| **Validation** | Pydantic v2 | Type-safe data models |
| **Web Scraping** | Playwright, BeautifulSoup | Robust content extraction |
| **Data Processing** | Polars (primary), Pandas | High-performance data manipulation |
| **Web Interface** | Streamlit | Interactive dashboard |
| **Configuration** | Pydantic Settings | Environment-based configuration |
| **Testing** | pytest | Comprehensive testing framework |

### Supporting Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Logging** | structlog | Structured logging |
| **Database** | SQLite/PostgreSQL | Data persistence |
| **Packaging** | Poetry/pip | Dependency management |
| **Code Quality** | Ruff | Linting and formatting |
| **Documentation** | Markdown | Documentation system |

---

## Design Patterns

### 1. Creational Patterns

**Factory Pattern**: Configuration and component creation
```python
def create_etl(etl_type: str, **kwargs) -> BaseETL:
    if etl_type == "simple":
        return SimpleETL(**kwargs)
    elif etl_type == "dataframe":
        return DataFrameETL(**kwargs)
```

**Singleton Pattern**: Configuration management
```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 2. Structural Patterns

**Adapter Pattern**: Different data source adapters
```python
class RSSAdapter(DataSourceAdapter):
    def fetch_data(self) -> List[Dict]:
        # RSS-specific implementation
        pass
```

**Facade Pattern**: Simplified API interfaces
```python
class WatchtowerFacade:
    def run_etl(self, name: str):
        # Simplified interface for complex operations
        pass
```

### 3. Behavioral Patterns

**Template Method Pattern**: ETL workflow
```python
class BaseETL(ABC):
    def run(self) -> ETLMetrics:
        data = self.extract()      # Abstract
        transformed = self.transform(data)  # Abstract
        self.load(transformed)     # Abstract
        return self.metrics
```

**Observer Pattern**: Event handling
```python
class EventEmitter:
    def __init__(self):
        self._observers = []
    
    def notify(self, event):
        for observer in self._observers:
            observer.handle_event(event)
```

**Strategy Pattern**: Different algorithms
```python
class ChangeDetectionStrategy(ABC):
    @abstractmethod
    def has_changed(self, old_value, new_value) -> bool:
        pass
```

---

## Scalability & Performance

### 1. Concurrency Model

**Async I/O**: Non-blocking operations for network requests
```python
async def fetch_multiple_sources():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_source(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

**Thread Pool**: CPU-intensive operations
```python
with ThreadPoolExecutor(max_workers=settings.etl.max_workers) as executor:
    futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
    results = [future.result() for future in futures]
```

### 2. Memory Management

**Batch Processing**: Controlled memory usage
```python
def process_in_batches(data: List[Any], batch_size: int):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]
```

**Streaming**: Large dataset handling
```python
def process_large_file(filepath: Path):
    with open(filepath) as f:
        for line in f:  # Process line by line
            yield process_line(line)
```

### 3. Caching Strategy

**Function-Level Caching**: Expensive operations
```python
@lru_cache(maxsize=1000)
def expensive_computation(input_data: str) -> str:
    # Cached computation
    return result
```

**Data Caching**: Frequently accessed data
```python
class DataCache:
    def __init__(self, ttl: int = 3600):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl
```

### 4. Database Optimization

**Connection Pooling**: Efficient database access
```python
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=30
```

**Indexed Queries**: Fast data retrieval
```sql
CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_watcher_name ON events(watcher_name);
```

---

## Future Architecture Considerations

### 1. Microservices Evolution

Current monolithic structure can evolve into microservices:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ ETL Service │  │Watcher Svc  │  │ API Gateway │
└─────────────┘  └─────────────┘  └─────────────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                 ┌─────────────┐
                 │Config Svc   │
                 └─────────────┘
```

### 2. Event-Driven Architecture

Implement event sourcing for better scalability:

```
Events → Event Store → Event Handlers → Projections
```

### 3. Container Orchestration

Docker and Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: watchtower
spec:
  replicas: 3
  selector:
    matchLabels:
      app: watchtower
```

This architecture provides a solid foundation for current needs while enabling future evolution and scaling requirements. 
# ETL Development Guide

This guide provides comprehensive instructions for developing new ETL processes in the Watchtower platform.

## BaseETL Framework Overview

The `BaseETL` class (`src/etl/base.py`) provides a robust foundation for all data processing pipelines. It implements the Template Method pattern with built-in features for metrics, checkpointing, error handling, and data validation.

### Core Features

- **Template Method Pattern**: Standardized extract → transform → load workflow
- **Metrics Collection**: Automatic performance tracking and success rate calculation
- **Checkpointing System**: Resumable operations for long-running processes
- **Retry Mechanisms**: Exponential backoff for handling transient failures
- **Batch Processing**: Memory-efficient processing of large datasets
- **Data Validation**: Pydantic model validation with detailed error reporting
- **Error Handling**: Custom exception hierarchy with contextual information

## Creating a New ETL Process

### Step 1: Basic ETL Structure

Create a new ETL by inheriting from `BaseETL`:

```python
# src/etl/my_domain/my_custom_etl.py
from typing import List, Dict, Any
from datetime import datetime
import requests
import json

from src.etl.base import BaseETL
from src.models.my_domain import MyDomainModel
from src.utils.logging import get_logger

class MyCustomETL(BaseETL[Dict[str, Any], MyDomainModel]):
    """ETL for processing data from My Custom Source.
    
    This ETL fetches data from an external API, processes it according
    to business rules, and stores it in a structured format.
    """
    
    def __init__(self):
        super().__init__(
            name="my_custom_etl",
            description="ETL for My Custom Data Source",
            batch_size=100,
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=5
        )
        self.api_key = self.settings.api.my_custom_api_key
        
    def extract(self) -> List[Dict[str, Any]]:
        """Extract data from the external API."""
        self.logger.info("Starting data extraction from My Custom API")
        
        # API request with proper error handling
        response = requests.get(
            "https://api.example.com/data",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        self.logger.info(f"Extracted {len(data.get('items', []))} items")
        
        return data.get('items', [])
    
    def transform(self, data: List[Dict[str, Any]]) -> List[MyDomainModel]:
        """Transform raw data into structured models."""
        self.logger.info(f"Transforming {len(data)} items")
        transformed_items = []
        
        for item in data:
            try:
                # Business logic for data transformation
                processed_item = MyDomainModel(
                    title=item.get('title', '').strip(),
                    description=self._clean_description(item.get('description', '')),
                    source_id=item.get('id'),
                    published_at=self._parse_date(item.get('created_at')),
                    category=self._classify_category(item),
                    metadata={
                        'api_source': 'my_custom_api',
                        'processed_at': datetime.utcnow().isoformat(),
                        'raw_data': item  # Preserve original for debugging
                    }
                )
                transformed_items.append(processed_item)
                
            except Exception as e:
                self.logger.warning(f"Failed to transform item {item.get('id', 'unknown')}: {e}")
                self.metrics.records_failed += 1
                continue
                
        self.logger.info(f"Successfully transformed {len(transformed_items)} items")
        return transformed_items
    
    def load(self, data: List[MyDomainModel]) -> None:
        """Load transformed data to JSON files."""
        if not data:
            self.logger.info("No data to load")
            return
            
        # Convert models to dictionaries for JSON serialization
        json_data = [item.model_dump() for item in data]
        
        # Save timestamped file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        timestamped_file = self.output_dir / f"my_custom_data_{timestamp}.json"
        
        with open(timestamped_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
        # Save latest file for dashboard consumption
        latest_file = self.output_dir / "my_custom_data_latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
        self.logger.info(f"Saved {len(data)} items to {timestamped_file}")
        
    def _clean_description(self, description: str) -> str:
        """Clean and normalize description text."""
        return description.strip().replace('\n', ' ')[:500]
        
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.utcnow()
            
    def _classify_category(self, item: Dict[str, Any]) -> str:
        """Classify item into appropriate category."""
        title = item.get('title', '').lower()
        if 'tech' in title or 'ai' in title:
            return 'technology'
        elif 'business' in title:
            return 'business'
        else:
            return 'general'

# Entry point for running the ETL
def main():
    """Main entry point for the ETL process."""
    etl = MyCustomETL()
    try:
        metrics = etl.run()
        print(f"ETL completed successfully. Processed {metrics.records_loaded} items.")
    except Exception as e:
        print(f"ETL failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

### Step 2: Create Data Models

Define Pydantic models for your data:

```python
# src/models/my_domain.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel

class MyDomainModel(TimestampedModel):
    """Model for My Custom Domain data."""
    
    title: str = Field(..., description="Item title", max_length=500)
    description: str = Field("", description="Item description", max_length=2000)
    source_id: str = Field(..., description="Unique identifier from source")
    published_at: datetime = Field(..., description="Publication timestamp")
    category: str = Field(..., description="Item category")
    url: Optional[HttpUrl] = Field(None, description="Item URL if available")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Step 3: Configuration Setup

Add configuration settings if needed:

```python
# src/config/models.py (add to existing file)
class MyCustomAPIConfig(BaseModel):
    """Configuration for My Custom API."""
    
    api_key: str = Field(..., description="API key for My Custom service")
    base_url: str = Field(
        default="https://api.example.com", 
        description="Base URL for the API"
    )
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout")
    rate_limit: float = Field(
        default=1.0, ge=0.1, le=10.0, 
        description="Requests per second limit"
    )
```

### Step 4: Add to Main Settings

```python
# src/config/settings.py (add to Settings class)
my_custom_api: MyCustomAPIConfig = Field(default_factory=MyCustomAPIConfig)
```

## Advanced ETL Patterns

### Using DataFrameETL for Complex Transformations

For data that benefits from pandas operations:

```python
from src.etl.base import DataFrameETL
import pandas as pd

class MyDataFrameETL(DataFrameETL[Dict[str, Any], MyDomainModel]):
    """ETL using pandas for complex data transformations."""
    
    def extract_to_dataframe(self) -> pd.DataFrame:
        """Extract data directly into a DataFrame."""
        # Fetch data and create DataFrame
        data = self._fetch_raw_data()
        df = pd.DataFrame(data)
        
        # Basic cleaning
        df = df.dropna(subset=['id', 'title'])
        df = df.drop_duplicates(subset=['id'])
        
        return df
    
    def transform_dataframe(self, df: pd.DataFrame) -> List[MyDomainModel]:
        """Transform DataFrame into model objects."""
        # Complex pandas operations
        df['category'] = df['title'].apply(self._classify_category)
        df['processed_at'] = pd.Timestamp.utcnow()
        
        # Convert to models
        models = []
        for _, row in df.iterrows():
            model = MyDomainModel(**row.to_dict())
            models.append(model)
            
        return models
```

### Implementing Checkpointing

For long-running ETLs that need to resume from failures:

```python
class CheckpointedETL(BaseETL[Dict[str, Any], MyDomainModel]):
    """ETL with custom checkpointing logic."""
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract with checkpoint support."""
        # Load checkpoint to determine starting point
        checkpoint = self._load_checkpoint()
        last_processed_id = checkpoint.last_processed_id if checkpoint else None
        
        # Fetch data starting from checkpoint
        data = self._fetch_data_since(last_processed_id)
        
        return data
    
    def transform(self, data: List[Dict[str, Any]]) -> List[MyDomainModel]:
        """Transform with checkpoint updates."""
        transformed = []
        
        for i, item in enumerate(data):
            # Process item
            model = self._process_item(item)
            transformed.append(model)
            
            # Update checkpoint every 100 items
            if i % 100 == 0:
                checkpoint = ETLCheckpoint(
                    etl_name=self.name,
                    checkpoint_id=f"batch_{i // 100}",
                    timestamp=datetime.utcnow(),
                    last_processed_id=item['id'],
                    processed_count=i + 1
                )
                self._save_checkpoint(checkpoint)
                
        return transformed
```

### Error Handling and Recovery

Implement robust error handling:

```python
from src.exceptions.etl import ETLError
from src.exceptions.base import WatchtowerError

class RobustETL(BaseETL[Dict[str, Any], MyDomainModel]):
    """ETL with comprehensive error handling."""
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract with retry logic for different error types."""
        try:
            return self._fetch_data()
        except requests.RequestException as e:
            if e.response and e.response.status_code == 429:
                # Rate limit - wait longer
                self.logger.warning("Rate limited, waiting 60 seconds")
                time.sleep(60)
                return self._fetch_data()
            elif e.response and e.response.status_code >= 500:
                # Server error - retry with backoff handled by base class
                raise
            else:
                # Client error - don't retry
                raise ETLError(f"Client error in extract phase: {e}")
                
    def should_stop_on_error(self, error: Exception) -> bool:
        """Custom logic for determining if errors should stop the ETL."""
        if isinstance(error, (KeyboardInterrupt, MemoryError)):
            return True
        if isinstance(error, requests.HTTPError):
            # Stop on authentication errors
            if error.response and error.response.status_code == 401:
                return True
        return False
```

## Testing ETL Processes

### Unit Testing

```python
# Tests/etl/test_my_custom_etl.py
import pytest
from unittest.mock import Mock, patch
from src.etl.my_domain.my_custom_etl import MyCustomETL

class TestMyCustomETL:
    """Test suite for MyCustomETL."""
    
    @pytest.fixture
    def etl(self):
        """Create ETL instance for testing."""
        return MyCustomETL()
    
    @patch('src.etl.my_domain.my_custom_etl.requests.get')
    def test_extract_success(self, mock_get, etl):
        """Test successful data extraction."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [
                {'id': '1', 'title': 'Test Item', 'description': 'Test desc'}
            ]
        }
        mock_get.return_value = mock_response
        
        # Test extraction
        result = etl.extract()
        
        assert len(result) == 1
        assert result[0]['id'] == '1'
        
    def test_transform_valid_data(self, etl):
        """Test data transformation with valid input."""
        raw_data = [
            {
                'id': '1',
                'title': 'AI Technology News',
                'description': 'Latest AI developments',
                'created_at': '2023-01-01T00:00:00Z'
            }
        ]
        
        result = etl.transform(raw_data)
        
        assert len(result) == 1
        assert result[0].title == 'AI Technology News'
        assert result[0].category == 'technology'
        
    def test_transform_invalid_data(self, etl):
        """Test transformation with invalid data."""
        raw_data = [
            {'id': None, 'title': ''},  # Invalid data
            {'id': '2', 'title': 'Valid Item', 'created_at': '2023-01-01T00:00:00Z'}
        ]
        
        result = etl.transform(raw_data)
        
        # Should have 1 valid item, 1 failed
        assert len(result) == 1
        assert etl.metrics.records_failed == 1
```

### Integration Testing

```python
# Tests/integration/test_my_custom_etl_integration.py
import pytest
import tempfile
import json
from pathlib import Path

from src.etl.my_domain.my_custom_etl import MyCustomETL

class TestMyCustomETLIntegration:
    """Integration tests for complete ETL workflow."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
            
    def test_full_etl_workflow(self, temp_output_dir):
        """Test complete ETL workflow from extract to load."""
        # Create ETL with temporary output directory
        etl = MyCustomETL()
        etl.output_dir = temp_output_dir
        
        # Mock external dependencies if needed
        with patch.object(etl, 'extract') as mock_extract:
            mock_extract.return_value = [
                {'id': '1', 'title': 'Test', 'created_at': '2023-01-01T00:00:00Z'}
            ]
            
            # Run ETL
            metrics = etl.run()
            
            # Verify metrics
            assert metrics.records_extracted == 1
            assert metrics.records_loaded == 1
            assert metrics.is_successful
            
            # Verify output files exist
            assert (temp_output_dir / "my_custom_data_latest.json").exists()
            
            # Verify output content
            with open(temp_output_dir / "my_custom_data_latest.json") as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]['title'] == 'Test'
```

## Performance Optimization

### Batch Processing

```python
class OptimizedETL(BaseETL[Dict[str, Any], MyDomainModel]):
    """ETL optimized for large datasets."""
    
    def transform(self, data: List[Dict[str, Any]]) -> List[MyDomainModel]:
        """Transform data in configurable batches."""
        return self.process_in_batches(data, self._transform_batch)
    
    def _transform_batch(self, batch: List[Dict[str, Any]]) -> List[MyDomainModel]:
        """Transform a single batch of data."""
        transformed = []
        for item in batch:
            # Process individual item
            model = self._process_item(item)
            transformed.append(model)
        return transformed
```

### Memory Management

```python
def extract(self) -> List[Dict[str, Any]]:
    """Memory-efficient extraction using generators."""
    # For very large datasets, use generators
    return list(self._extract_generator())
    
def _extract_generator(self):
    """Generator for memory-efficient data extraction."""
    page = 1
    while True:
        batch = self._fetch_page(page)
        if not batch:
            break
            
        for item in batch:
            yield item
            
        page += 1
```

## Best Practices

### 1. Error Handling
- Use specific exception types for different error conditions
- Log errors with sufficient context for debugging
- Implement appropriate retry logic for transient failures
- Fail fast for non-recoverable errors

### 2. Data Validation
- Validate all external data using Pydantic models
- Handle validation errors gracefully
- Preserve original data in metadata for debugging
- Use field validators for complex validation logic

### 3. Performance
- Use batch processing for large datasets
- Implement checkpointing for long-running processes
- Consider memory usage when processing large files
- Use generators for streaming data processing

### 4. Monitoring
- Use the built-in metrics collection
- Log progress at appropriate intervals
- Include performance metrics in logs
- Monitor for data quality issues

### 5. Testing
- Write unit tests for each method
- Include integration tests for complete workflows
- Test error conditions and edge cases
- Use mock objects for external dependencies

### 6. Documentation
- Document the data source and expected format
- Explain any business logic or transformations
- Include examples of input and output data
- Document any external dependencies or configuration

This guide provides the foundation for creating robust, maintainable ETL processes within the Watchtower platform.
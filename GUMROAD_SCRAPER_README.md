# Gumroad Free Products Scraper

A comprehensive ETL scraper for collecting free products from Gumroad's discover page, built following the Watchtower framework patterns.

## Features

- **Playwright-based scraping**: Uses Playwright for robust web scraping with JavaScript support
- **Intelligent pagination**: Handles pagination automatically with configurable limits
- **Dual run modes**: Regular runs (10 pages) and first runs (200 pages)
- **Checkpoint support**: Resumes from where it left off if interrupted
- **Multiple output formats**: JSON, CSV, and scavenging-compatible formats
- **Comprehensive logging**: Detailed logging with debug support
- **Error handling**: Robust error handling with retry mechanisms

## Installation

The scraper is already integrated into the Watchtower project. Ensure you have:

1. **UV package manager** (should already be installed)
2. **Playwright browsers** installed:
   ```bash
   uv run playwright install
   ```

## Usage

### Standalone Usage

```bash
# Regular run (10 pages)
uv run python run_gumroad_scraper.py

# First run (200 pages)
uv run python run_gumroad_scraper.py --first-run

# Custom page limit
uv run python run_gumroad_scraper.py --max-pages 50

# Debug mode
uv run python run_gumroad_scraper.py --debug

# Dry run (testing without saving data)
uv run python run_gumroad_scraper.py --dry-run
```

### Platform-Specific Scripts

**Windows:**
```cmd
# Regular run
run_gumroad_scraper.bat

# First run
run_gumroad_scraper.bat --first-run

# Debug mode
run_gumroad_scraper.bat --debug
```

**Linux/Mac:**
```bash
# Regular run
./run_gumroad_scraper.sh

# First run
./run_gumroad_scraper.sh --first-run

# Debug mode
./run_gumroad_scraper.sh --debug
```

### Integration with ETL Pipeline

The scraper is automatically included in the main ETL pipeline:

```bash
# Windows
run_all_etl.bat

# Linux/Mac
./run_all_etl.sh
```

## Configuration

### Run Modes

- **Regular Run**: Scrapes 10 pages (default)
- **First Run**: Scrapes 200 pages (use `--first-run` flag)
- **Custom**: Override with `--max-pages N`

### URL and Parameters

- **Base URL**: `https://gumroad.com/discover`
- **Filters**: `max_price=1&sort=hot_and_new`
- **Target**: Free products only

## Data Output

### File Locations

```
data/
├── gumroad_scraper/
│   ├── output/
│   │   ├── gumroad_free_products.json
│   │   └── gumroad_free_products.csv
│   └── checkpoints/
│       └── latest.json
└── scavenging/
    └── gumroad_free_products.json
```

### Data Models

#### GumroadProduct Fields

- `product_id`: Unique identifier
- `name`: Product name
- `price`: Price (typically "Free")
- `seller`: Product creator/seller
- `description`: Product description
- `url`: Product URL
- `category`: Product category
- `tags`: Product tags
- `rating`: Product rating
- `num_ratings`: Number of ratings
- `thumbnail_url`: Product thumbnail
- `fetched_at`: Timestamp when scraped
- `parsed_at`: Timestamp when processed

#### Scavenging Format

Compatible with the existing scavenging system:

```json
{
  "title": "Product Name",
  "link": "https://gumroad.com/l/product-id",
  "published": "2025-01-01T00:00:00Z",
  "summary": "Product description",
  "category": "gumroad_free",
  "source": "gumroad_scraper",
  "price": "Free",
  "seller": "Creator Name"
}
```

## Technical Implementation

### Architecture

- **Base Class**: Inherits from `BaseETL[GumroadRawData, GumroadProduct]`
- **Extraction**: Playwright-based web scraping
- **Transformation**: HTML parsing with BeautifulSoup
- **Loading**: JSON/CSV export + scavenging format

### Error Handling

- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Timeout Management**: Page-level and element-level timeouts
- **Graceful Degradation**: Continues processing even if individual products fail
- **Checkpoint Recovery**: Resumes from last successful page

### Performance Optimizations

- **Headless Browser**: Runs in headless mode for speed
- **Disabled Resources**: Disables images and unnecessary resources
- **Batch Processing**: Processes products in batches
- **Memory Management**: Proper resource cleanup

## Logging and Monitoring

### Log Levels

- **INFO**: General progress and status
- **DEBUG**: Detailed scraping information (use `--debug`)
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures

### Log Files

- **Console**: Real-time output
- **File**: `logs/gumroad_scraper.log`
- **ETL Metrics**: Performance and success metrics

### Monitoring

The scraper provides comprehensive metrics:

```python
ETLMetrics(
    duration_seconds=120.5,
    records_extracted=250,
    records_transformed=245,
    records_loaded=245,
    records_failed=5,
    success_rate=98.0
)
```

## Troubleshooting

### Common Issues

1. **Playwright Not Installed**
   ```bash
   uv run playwright install
   ```

2. **Timeout Errors**
   - Check internet connection
   - Gumroad may be rate-limiting
   - Try running with `--debug` for more info

3. **No Products Found**
   - Gumroad may have changed their HTML structure
   - Check the selectors in `_extract_product_data()`

4. **Checkpoint Issues**
   - Delete `data/gumroad_scraper/checkpoints/latest.json` to start fresh

### Debug Mode

Run with `--debug` to see detailed information:

```bash
uv run python run_gumroad_scraper.py --debug
```

This will show:
- Detailed HTTP requests
- HTML parsing steps
- Product extraction details
- Browser automation logs

## Integration with Dashboard

The scraped data is automatically compatible with the Watchtower dashboard:

1. **Scavenging Tab**: Shows products in the scavenging interface
2. **Raw Data**: Available in JSON/CSV formats
3. **Search**: Products are searchable by name, seller, tags

## Development

### Adding New Fields

1. Update the `GumroadProduct` model in `src/models/ecommerce.py`
2. Modify the parsing logic in `_parse_product_html()`
3. Update the scavenging format mapping in `load()`

### Customizing Selectors

Product data is extracted using CSS selectors. Update these in `_parse_product_html()`:

```python
name_selectors = [
    '[data-testid="product-title"]',
    '.product-title',
    'h3',
    'h2',
    '.title'
]
```

### Testing

```bash
# Test without scraping
uv run python run_gumroad_scraper.py --dry-run

# Test with limited pages
uv run python run_gumroad_scraper.py --max-pages 2 --debug
```

## Future Enhancements

- **Category Filtering**: Filter by specific product categories
- **Price Range**: Support for different price ranges
- **Async Processing**: Parallel product processing
- **API Integration**: Use Gumroad API if available
- **Duplicate Detection**: Advanced duplicate detection across runs

## Contributing

Follow the Watchtower development standards:

1. Use type hints
2. Follow the BaseETL pattern
3. Add comprehensive logging
4. Include error handling
5. Update documentation

## License

Part of the Watchtower project. See main project license. 
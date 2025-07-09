#!/bin/bash

echo "Starting Gumroad Free Products Scraper at $(date)"

# Change to the project root directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to run the scraper with logging
run_scraper() {
    local args="$*"
    echo "Running: uv run python run_gumroad_scraper.py $args"
    
    if uv run python run_gumroad_scraper.py $args > logs/gumroad_scraper.log 2>&1; then
        echo "Gumroad scraper completed successfully"
        echo "Check logs/gumroad_scraper.log for details"
        return 0
    else
        echo "Gumroad scraper failed with error code $?"
        echo "Check logs/gumroad_scraper.log for error details"
        return 1
    fi
}

# Check command line arguments
case "$1" in
    --first-run)
        echo "Running first-time scraping (10000 items)"
        run_scraper --first-run
        ;;
    --debug)
        echo "Running with debug logging"
        run_scraper --debug
        ;;
    --dry-run)
        echo "Running dry run (no data saved)"
        run_scraper --dry-run
        ;;
    --help|-h)
        echo "Usage: $0 [--first-run|--debug|--dry-run|--help]"
        echo ""
        echo "Options:"
        echo "  --first-run  Run first-time scraping (10000 items instead of 500)"
        echo "  --debug      Enable debug logging"
        echo "  --dry-run    Run without saving data (for testing)"
        echo "  --help, -h   Show this help message"
        exit 0
        ;;
    "")
        echo "Running regular scraping (500 items)"
        run_scraper
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

echo "Finished at $(date)"

# Show data directories if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "Data directories:"
    echo "- data/gumroad_scraper/output/"
    echo "- data/scavenging/"
fi 
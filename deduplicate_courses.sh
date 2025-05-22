#!/bin/bash

# Deduplicate Courses Utility
# This script runs the course deduplication tool on JSON files

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed or not in the PATH."
    echo "Please install Python and try again."
    exit 1
fi

# Determine the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment if exists
if [ -f "${SCRIPT_DIR}/.venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "${SCRIPT_DIR}/.venv/bin/activate"
fi

# Default values
INPUT_PATH=""
OUTPUT_PATH=""
KEY_FIELD="url"
PREFER_OLDER=""
RECURSIVE=""
BACKUP="--backup"
VERBOSE=""

# Function to show help
show_help() {
    echo "Usage: deduplicate_courses.sh [input_path] [options]"
    echo ""
    echo "Options:"
    echo "  --output-file PATH   Output file path (for single file)"
    echo "  --key-field FIELD    Field to use for deduplication (url or title)"
    echo "  --prefer-older       Keep older entries (default: keep newer)"
    echo "  --recursive          Process directories recursively"
    echo "  --no-backup          Don't create backup files"
    echo "  --verbose            Enable verbose output"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            show_help
            exit 0
            ;;
        --output-file)
            OUTPUT_PATH="--output-file $2"
            shift 2
            ;;
        --key-field)
            KEY_FIELD="$2"
            shift 2
            ;;
        --prefer-older)
            PREFER_OLDER="--prefer-older"
            shift
            ;;
        --recursive)
            RECURSIVE="--recursive"
            shift
            ;;
        --no-backup)
            BACKUP=""
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$INPUT_PATH" ]; then
                INPUT_PATH="$1"
            else
                echo "Unexpected argument: $1"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Check for required arguments
if [ -z "$INPUT_PATH" ]; then
    echo "Error: No input path specified."
    echo "Try 'deduplicate_courses.sh --help' for usage information."
    exit 1
fi

# Execute the deduplication script
echo "Running course deduplication..."
python3 "${SCRIPT_DIR}/src/utils/deduplicate_courses_cli.py" \
    "$INPUT_PATH" \
    $OUTPUT_PATH \
    --key-field "$KEY_FIELD" \
    $PREFER_OLDER \
    $RECURSIVE \
    $BACKUP \
    $VERBOSE

if [ $? -ne 0 ]; then
    echo "Deduplication failed with error code $?"
    exit $?
fi

echo "Deduplication completed successfully."
exit 0 
#!/usr/bin/env python3
"""Command-line interface for deduplicating course JSON files.

This script provides a convenient way to deduplicate existing course files.
It can be used as a standalone tool or as part of an ETL pipeline.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
from utils.course_deduplication import deduplicate_courses_file

# Set up logging
logger = logging.getLogger("deduplicate_courses_cli")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deduplicate courses in JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Primary arguments
    parser.add_argument(
        "input_file",
        help="Path to the input JSON file or directory containing JSON files"
    )

    parser.add_argument(
        "--output-file",
        help="Path to save the deduplicated JSON file (defaults to input file)"
    )

    parser.add_argument(
        "--key-field",
        choices=["url", "title"],
        default="url",
        help="Field to use for deduplication"
    )

    parser.add_argument(
        "--prefer-older",
        action="store_true",
        help="Keep older entries when duplicates are found (default: keep newer)"
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process directories recursively (only if input is a directory)"
    )

    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of original files before modifying"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    return parser.parse_args()


def process_single_file(input_file, output_file, key_field, prefer_newer, backup):
    """Process a single file for deduplication."""
    if backup and output_file == input_file:
        # Create backup
        backup_file = f"{input_file}.bak"
        try:
            import shutil
            shutil.copy2(input_file, backup_file)
            logger.info(f"Created backup at {backup_file}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    try:
        output_path, removed_count = deduplicate_courses_file(
            input_file,
            key_field=key_field,
            prefer_newer=prefer_newer,
            output_path=output_file
        )

        if removed_count > 0:
            logger.info(f"Successfully removed {removed_count} duplicates from {input_file}")
        else:
            logger.info(f"No duplicates found in {input_file}")

        return True
    except Exception as e:
        logger.error(f"Error processing {input_file}: {e}")
        return False


def process_directory(directory, key_field, prefer_newer, backup, recursive):
    """Process all JSON files in a directory."""
    success_count = 0
    error_count = 0

    # Get all json files
    if recursive:
        json_files = list(Path(directory).glob("**/*.json"))
    else:
        json_files = list(Path(directory).glob("*.json"))

    if not json_files:
        logger.warning(f"No JSON files found in {directory}")
        return 0, 0

    logger.info(f"Found {len(json_files)} JSON files to process")

    for json_file in json_files:
        if process_single_file(str(json_file), str(json_file), key_field, prefer_newer, backup):
            success_count += 1
        else:
            error_count += 1

    return success_count, error_count


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Process input
    input_path = args.input_file

    if os.path.isdir(input_path):
        # Process directory
        logger.info(f"Processing directory: {input_path}")
        success_count, error_count = process_directory(
            input_path,
            args.key_field,
            not args.prefer_older,
            args.backup,
            args.recursive
        )
        logger.info(f"Processed {success_count} files successfully, {error_count} files with errors")
    elif os.path.isfile(input_path):
        # Process single file
        output_file = args.output_file if args.output_file else input_path
        logger.info(f"Processing file: {input_path}")
        if process_single_file(input_path, output_file, args.key_field, not args.prefer_older, args.backup):
            logger.info("Processing completed successfully")
        else:
            logger.error("Processing failed")
            sys.exit(1)
    else:
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(1)

    logger.info("All operations completed")


if __name__ == "__main__":
    main()

"""Utility to remove duplicate course entries from JSON files.

This module provides functions to deduplicate course data based on either URL
or title, ensuring that the dataset only contains unique course entries.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Callable, Set, Tuple

# Set up logging
logger = logging.getLogger("course_deduplication")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def deduplicate_courses(
    courses: List[Dict[str, Any]], key_field: str = "url", prefer_newer: bool = True
) -> Tuple[List[Dict[str, Any]], int]:
    """Remove duplicate courses based on a specified key field.

    Args:
        courses: List of course dictionaries to deduplicate
        key_field: Field to use for deduplication ("url" or "title")
        prefer_newer: If True, keeps newer entries when duplicates are found
                     (based on scraped_at field if available)

    Returns:
        Tuple containing the deduplicated course list and the number of duplicates removed
    """
    if not courses:
        return [], 0

    # Check if the key field exists in at least one course
    key_exists = any(key_field in course for course in courses)
    if not key_exists:
        logger.warning(
            f"Key field '{key_field}' not found in any course. Cannot deduplicate."
        )
        return courses, 0

    # Function to get a comparable key from a course
    def get_key(course: Dict[str, Any]) -> str:
        # Get the key, defaulting to empty string if not present
        key = course.get(key_field, "")
        # Normalize to lowercase for case-insensitive comparison (especially for titles)
        return key.lower() if isinstance(key, str) else str(key)

    # To track unique courses
    unique_courses: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0

    # Sort by scraped_at if prefer_newer is True and scraped_at exists
    if prefer_newer and any("scraped_at" in course for course in courses):
        sorted_courses = sorted(
            courses,
            key=lambda c: c.get(
                "scraped_at", ""
            ),  # Default to empty string if not present
            reverse=True,  # Newer entries first
        )
    else:
        sorted_courses = courses

    # Process each course
    for course in sorted_courses:
        key = get_key(course)
        if not key:  # Skip courses with empty key
            continue

        if key in unique_courses:
            duplicate_count += 1
            # If we prefer older entries, skip this one
            if not prefer_newer:
                continue

        # Add/replace in the unique courses dictionary
        unique_courses[key] = course

    logger.info(f"Removed {duplicate_count} duplicate courses based on {key_field}")
    return list(unique_courses.values()), duplicate_count


def deduplicate_courses_file(
    file_path: str,
    key_field: str = "url",
    prefer_newer: bool = True,
    output_path: Optional[str] = None,
) -> Tuple[str, int]:
    """Deduplicate courses in a JSON file and save the result.

    Args:
        file_path: Path to the JSON file containing courses
        key_field: Field to use for deduplication ("url" or "title")
        prefer_newer: If True, keeps newer entries when duplicates are found
        output_path: Optional path to save the deduplicated data. If None,
                     updates the original file.

    Returns:
        Tuple containing the path to the output file and the number of duplicates removed
    """
    # Default output path to input path if not specified
    if output_path is None:
        output_path = file_path

    try:
        # Read courses from file
        with open(file_path, "r", encoding="utf-8") as f:
            courses = json.load(f)

        if not isinstance(courses, list):
            logger.error(f"File {file_path} does not contain a list of courses")
            return file_path, 0

        # Deduplicate courses
        deduplicated_courses, removed_count = deduplicate_courses(
            courses, key_field, prefer_newer
        )

        # Save deduplicated courses
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(deduplicated_courses, f, ensure_ascii=False, indent=2)

        logger.info(f"Deduplicated courses saved to {output_path}")
        return output_path, removed_count

    except Exception as e:
        logger.error(f"Error deduplicating courses file {file_path}: {e}")
        return file_path, 0


if __name__ == "__main__":
    # Example usage as a standalone script
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate courses in a JSON file")
    parser.add_argument("input_file", help="Path to the input JSON file")
    parser.add_argument(
        "--output-file",
        help="Path to save the deduplicated JSON file (defaults to input file)",
    )
    parser.add_argument(
        "--key-field",
        choices=["url", "title"],
        default="url",
        help="Field to use for deduplication (default: url)",
    )
    parser.add_argument(
        "--prefer-older",
        action="store_true",
        help="Keep older entries when duplicates are found (default: keep newer)",
    )

    args = parser.parse_args()

    output_file, removed_count = deduplicate_courses_file(
        args.input_file,
        key_field=args.key_field,
        prefer_newer=not args.prefer_older,
        output_path=args.output_file,
    )

    print(
        f"Removed {removed_count} duplicates. Deduplicated courses saved to {output_file}"
    )

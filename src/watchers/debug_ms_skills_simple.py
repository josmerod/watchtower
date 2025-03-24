import os
import sys
import requests
import re

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("MSSkillsSimpleDebugger")

def main():
    """Simplified script to look for specific strings in the HTML content."""
    url = "https://learn.microsoft.com/es-es/credentials/browse/?credential_types=applied%20skills"
    
    try:
        logger.info(f"Fetching {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        logger.info(f"Content length: {len(html_content)} characters")
        
        # Save first 1000 characters for inspection
        project_root = get_project_root()
        debug_dir = os.path.join(project_root, "data/watchers/debug")
        ensure_directories(["data/watchers/debug"])
        
        # Save a sample of the HTML to a file
        sample_file = os.path.join(debug_dir, "sample_content.txt")
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(html_content[:1000])
        logger.info(f"Sample content saved to {sample_file}")
        
        # Look for mentions of 'applied skills' in the content
        matches = re.findall(r'applied\s+skills', html_content.lower())
        logger.info(f"Found {len(matches)} mentions of 'applied skills'")
        
        # Look for any numbers that might indicate count
        number_matches = re.findall(r'(\d+)\s*resultados', html_content, re.IGNORECASE)
        logger.info(f"Found {len(number_matches)} potential result counts")
        
        if number_matches:
            for match in number_matches:
                logger.info(f"Potential count: {match}")
        
        # Check for specific patterns that might indicate credential count
        count_patterns = [
            r'(\d+)\s*resultados',
            r'(\d+)\s*applied\s*skills',
            r'showing\s*(\d+)',
            r'displaying\s*(\d+)',
            r'total\s*:\s*(\d+)',
            r'count\s*:\s*(\d+)'
        ]
        
        for pattern in count_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                logger.info(f"Pattern '{pattern}' matched: {matches}")
        
        # Check HTTP response headers
        logger.info("HTTP Response Headers:")
        for header, value in response.headers.items():
            logger.info(f"{header}: {value}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 
import os
import sys
import requests
import re
from bs4 import BeautifulSoup

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("MSSkillsDebugger")

def main():
    """Fetch the Microsoft Applied Skills page and save the HTML for analysis."""
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
        
        # Save the HTML content to a file
        project_root = get_project_root()
        debug_dir = os.path.join(project_root, "data/watchers/debug")
        ensure_directories(["data/watchers/debug"])
        
        html_file = os.path.join(debug_dir, "ms_skills_page.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML content saved to {html_file}")
        
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Print overall structure
        logger.info("Overall page structure:")
        if soup.title:
            logger.info(f"Title: {soup.title.text}")
        
        # Check for elements that might contain count info
        logger.info("Looking for elements that might contain count information:")
        
        # Try to find any numbers in spans, divs, or headings
        number_regex = re.compile(r'\d+')
        for tag in soup.find_all(['span', 'div', 'p', 'h1', 'h2', 'h3', 'h4']):
            if tag.text and number_regex.search(tag.text):
                # Only log if text is relatively short (to avoid large chunks)
                if len(tag.text.strip()) < 100:
                    logger.info(f"{tag.name}: {tag.text.strip()}")
        
        # Check for common container classes
        logger.info("\nChecking for common container classes:")
        common_containers = [
            '.card', '.credential-card', '.search-result', '.result', 
            '.list-item', '[role="listitem"]', '.skill-item', '.item'
        ]
        
        for container_selector in common_containers:
            elements = soup.select(container_selector)
            if elements:
                logger.info(f"Found {len(elements)} elements matching '{container_selector}'")
                # Show first element as example
                if elements[0].text.strip():
                    sample_text = elements[0].text.strip()
                    # Truncate if too long
                    if len(sample_text) > 100:
                        sample_text = sample_text[:100] + "..."
                    logger.info(f"Sample: {sample_text}")
        
        # Look at all tags with class attributes to find potential containers
        logger.info("\nClasses found in the document:")
        classes_count = {}
        for tag in soup.find_all(class_=True):
            for cls in tag.get('class', []):
                classes_count[cls] = classes_count.get(cls, 0) + 1
        
        # Show most common classes
        for cls, count in sorted(classes_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"Class '{cls}' appears {count} times")
        
        # Save structure summary
        structure_file = os.path.join(debug_dir, "page_structure.txt")
        with open(structure_file, 'w', encoding='utf-8') as f:
            f.write("Page Structure Summary\n")
            f.write("=====================\n\n")
            
            # Count tag types
            tag_counts = {}
            for tag in soup.find_all():
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
            
            f.write("Tag counts:\n")
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{tag}: {count}\n")
            
            f.write("\nClass counts:\n")
            for cls, count in sorted(classes_count.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{cls}: {count}\n")
        
        logger.info(f"Structure summary saved to {structure_file}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 
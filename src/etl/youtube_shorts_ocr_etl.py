import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse, urlunparse
from dataclasses import dataclass
import cv2
import numpy as np

# Add project root to Python path BEFORE importing src modules
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    if project_root not in sys.path:
        sys.path.append(project_root)
except NameError: # Fallback for environments where __file__ is not defined
    project_root = os.path.abspath(".")
    if project_root not in sys.path:
        sys.path.append(project_root)

# Now import external dependencies
import yt_dlp
from moviepy import VideoFileClip
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure Tesseract path for Windows
if sys.platform.startswith('win'):
    # Common Windows installation paths
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.environ.get('USERNAME', 'user')),
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"[OK] Configured Tesseract path: {path}")
            break
    else:
        print("[WARNING] Tesseract not found in common Windows locations")
        print("   Please install Tesseract or set the path manually")

# Now import src modules after path is set up
from src.utils.file_system import ensure_directories, get_project_root

# Set up logging
logger = logging.getLogger("youtube_shorts_ocr_etl")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration
TARGET_CHANNEL_URL = "https://youtube.com/@setupsaitony/shorts"
OUTPUT_DIR = os.path.join(get_project_root(), "data", "youtube_shorts_ocr")
TEMP_VIDEO_DIR = os.path.join(OUTPUT_DIR, "temp_videos")
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "processing_checkpoint.json")
MAX_SHORTS_TO_PROCESS = 10  # Limiting for development/testing
DEFAULT_DAYS_LOOKBACK = 90 # Process shorts from the last 90 days

# Passive processing configuration
DEFAULT_REQUEST_DELAY = 2.0  # Seconds between requests
DEFAULT_DOWNLOAD_DELAY = 3.0  # Seconds between downloads
DEFAULT_PROCESSING_DELAY = 1.0  # Seconds between OCR processing
MAX_RETRIES = 3  # Maximum retry attempts for failed operations

# OCR Quality Configuration
MIN_TEXT_LENGTH = 4  # Minimum length for text to be considered valid
MIN_CONFIDENCE = 10  # Minimum confidence score for OCR results (lowered for better URL detection)
FRAME_SIMILARITY_THRESHOLD = 0.95  # Skip frames that are too similar


@dataclass
class ExtractedURL:
    """Represents a URL extracted from video content"""
    url: str
    confidence: float
    timestamp: float
    frame_number: int
    cleaned_url: str
    is_valid: bool
    context_text: str
    region: str  # 'browser_bar', 'full_frame', 'bottom_third', etc.


class URLExtractor:
    """Enhanced URL extraction from OCR text with robust post-processing"""
    
    def __init__(self):
        # Primary comprehensive URL regex pattern (robust and handles most cases)
        self.primary_url_regex = re.compile(
            r'''(?i)\b((?:(?:https?|ftp)://)         # protocol
            (?:\S+(?::\S*)?@)?                      # authentication
            (?:                                     # IP address or domain
                (?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])  # IP 1st octet
                (?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}
                (?:\.(?:[0-9]{1,3}))                # IP 4th octet
                |
                (?:[a-z0-9\u00a1-\uffff0-9]+-?)*[a-z0-9\u00a1-\uffff0-9]+  # domain
                (?:\.[a-z\u00a1-\uffff]{2,})+                              # TLD
            )
            (?::\d{2,5})?                            # port
            (?:/\S*)?                                # path
            )''', re.VERBOSE)
        
        # Simplified fallback URL regex patterns for edge cases (ordered by specificity)
        self.fallback_url_patterns = [
            # URLs with www (for cases without protocol)
            r'www\.[\w.-]+\.[\w]{2,6}(?:/[\w./?%&=]*)?',
            # Domain with essential TLDs (for bare domains) - including .art for the specific case
            r'[\w.-]+\.(?:com|net|org|edu|gov|io|co|app|dev|tech|ai|ml|xyz|info|biz|art|live|online|store|site|blog|news|tv|music|photo|design|digital|cloud|api|game|app)(?:/[\w./?%&=]*)?',
            # Localhost variations
            r'localhost(?::\d+)?(?:/[\w./?%&=]*)?',
        ]
        
        # Simplified aggressive post-processing regex patterns for OCR error handling
        self.aggressive_patterns = [
            # Very flexible protocol patterns (handles OCR errors)
            r'h[t]{1,3}ps?[:\s]*[/\\]*[/\\]*\s*\S+',
            # www with flexible dots and spacing
            r'w{2,4}\.?\s*\S+\.(?:com|net|org|edu|gov|io|co|app|dev|tech|ai|ml)',
            # Popular platforms with flexible matching
            r'(?:github|gitlab|twitter|facebook|instagram|linkedin|youtube|tiktok|discord|twitch|medium|reddit|stackoverflow)\.(?:com|org|io|tv)\S*',
            # Cloud/hosting platforms
            r'(?:vercel|netlify|heroku|aws|azure|cloudflare)\.(?:app|com|net|io)\S*',
            # Shortened URLs and common services
            r'(?:bit\.ly|tinyurl|goo\.gl|short\.link|t\.co|youtu\.be|amzn\.to|tiny\.cc)\S*',
            # API endpoints
            r'api\.\S+\.(?:com|net|org|io|dev)\S*',
            # Word boundaries for domains (catches partial URLs)
            r'\b[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|net|org|edu|gov|io|co|app|dev|tech|ai|ml|xyz|info|biz)\b\S*',
            # Flexible IP addresses
            r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]{1,5})?\S*',
            # localhost variations with ports
            r'localhost(?::[0-9]{1,5})?\S*',
            # File extensions that might indicate URLs
            r'\S+\.(?:html?|php|asp|jsp|py|js|css|xml|json|pdf|doc|docx|xls|xlsx|ppt|pptx)\S*',
        ]
        
        # Common domains that might appear fragmented
        self.common_domains = [
            'github.com', 'google.com', 'youtube.com', 'facebook.com', 'twitter.com',
            'instagram.com', 'linkedin.com', 'stackoverflow.com', 'medium.com',
            'discord.com', 'twitch.tv', 'amazon.com', 'netflix.com', 'spotify.com',
            'apple.com', 'microsoft.com', 'openai.com', 'chatgpt.com', 'claude.ai',
            'vercel.app', 'netlify.app', 'heroku.com', 'aws.amazon.com', 'azure.com',
            'reddit.com', 'tiktok.com', 'pinterest.com', 'tumblr.com', 'wordpress.com',
            'wix.com', 'squarespace.com', 'shopify.com', 'etsy.com', 'paypal.com'
        ]
    
    def clean_ocr_text_for_urls(self, text: str) -> str:
        """Clean OCR text specifically for better URL recognition"""
        # Remove common OCR artifacts
        text = re.sub(r'[|\\]', '/', text)  # Common OCR mistakes for forward slash
        text = re.sub(r'[Oo0]', 'o', text)  # Normalize o/O/0 in domains
        text = re.sub(r'[Il1]', 'l', text)  # Normalize l/I/1
        text = re.sub(r'\s+', ' ', text)    # Normalize whitespace
        
        # Fix common URL OCR mistakes
        text = re.sub(r'ht{2,}ps?:', 'https:', text)
        text = re.sub(r'w{2,}\.', 'www.', text)
        text = re.sub(r'\.c[o0]m', '.com', text)
        text = re.sub(r'\.n[e3]t', '.net', text)
        text = re.sub(r'\.o[rg]g', '.org', text)
        
        return text
    
    def extract_urls_from_text(self, text: str, confidence: float = 0.0, 
                              timestamp: float = 0.0, frame_number: int = 0,
                              region: str = 'full_frame') -> List[ExtractedURL]:
        """Extract URLs from OCR text with cleaning and validation"""
        urls = []
        cleaned_text = self.clean_ocr_text_for_urls(text)
        
        # First try the primary comprehensive URL regex
        primary_matches = self.primary_url_regex.finditer(cleaned_text)
        for match in primary_matches:
            raw_url = match.group(1)  # Get the captured group
            cleaned_url = self.clean_and_validate_url(raw_url)
            
            if cleaned_url:
                # Get context around the URL
                start = max(0, match.start() - 50)
                end = min(len(cleaned_text), match.end() + 50)
                context = cleaned_text[start:end].strip()
                
                url_obj = ExtractedURL(
                    url=raw_url,
                    confidence=confidence,
                    timestamp=timestamp,
                    frame_number=frame_number,
                    cleaned_url=cleaned_url,
                    is_valid=True,
                    context_text=context,
                    region=region + '_primary'
                )
                urls.append(url_obj)
        
        # Try fallback patterns for edge cases
        for pattern in self.fallback_url_patterns:
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
            for match in matches:
                raw_url = match.group(0)
                cleaned_url = self.clean_and_validate_url(raw_url)
                
                if cleaned_url:
                    # Get context around the URL
                    start = max(0, match.start() - 50)
                    end = min(len(cleaned_text), match.end() + 50)
                    context = cleaned_text[start:end].strip()
                    
                    url_obj = ExtractedURL(
                        url=raw_url,
                        confidence=confidence * 0.9,  # Slightly lower confidence for fallback
                        timestamp=timestamp,
                        frame_number=frame_number,
                        cleaned_url=cleaned_url,
                        is_valid=True,
                        context_text=context,
                        region=region + '_fallback'
                    )
                    urls.append(url_obj)
        
        # Apply aggressive post-processing extraction
        aggressive_urls = self.aggressive_url_extraction(text, confidence, timestamp, frame_number, region + '_aggressive')
        
        # Combine all URLs and deduplicate
        all_urls = urls + aggressive_urls
        unique_urls = {}
        for url in all_urls:
            key = url.cleaned_url
            if key not in unique_urls or url.confidence > unique_urls[key].confidence:
                unique_urls[key] = url
        
        return list(unique_urls.values())
    
    def clean_and_validate_url(self, url: str) -> Optional[str]:
        """Clean and validate a URL"""
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://', 'ftp://')):
            if url.startswith('www.'):
                url = 'https://' + url
            elif '.' in url and not url.startswith('localhost'):
                url = 'https://' + url
            elif url.startswith('localhost'):
                url = 'http://' + url
        
        # Clean common OCR artifacts
        url = re.sub(r'[<>"\'\s]', '', url)
        url = re.sub(r'\.{2,}', '.', url)
        url = re.sub(r'/{3,}', '//', url)
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if parsed.netloc and ('.' in parsed.netloc or parsed.netloc == 'localhost'):
                return urlunparse(parsed)
        except:
            pass
        
        return None
    
    def aggressive_url_extraction(self, text: str, confidence: float = 0.0, 
                                 timestamp: float = 0.0, frame_number: int = 0,
                                 region: str = 'post_processing') -> List[ExtractedURL]:
        """
        Aggressive post-processing URL extraction with maximum flexibility.
        This catches URLs that might be missed by the primary extraction.
        """
        urls = []
        
        # Pre-process text for aggressive extraction
        processed_text = self.aggressive_text_preprocessing(text)
        
        # Apply aggressive patterns
        for pattern in self.aggressive_patterns:
            matches = re.finditer(pattern, processed_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                raw_url = match.group(0).strip()
                
                # Clean up the aggressive match
                cleaned_url = self.aggressive_url_cleanup(raw_url)
                
                if cleaned_url and self.is_likely_url(cleaned_url):
                    # Get context around the URL
                    start = max(0, match.start() - 30)
                    end = min(len(processed_text), match.end() + 30)
                    context = processed_text[start:end].strip()
                    
                    url_obj = ExtractedURL(
                        url=raw_url,
                        confidence=confidence * 0.8,  # Slightly lower confidence for aggressive extraction
                        timestamp=timestamp,
                        frame_number=frame_number,
                        cleaned_url=cleaned_url,
                        is_valid=True,
                        context_text=context,
                        region=region
                    )
                    urls.append(url_obj)
        
        # Additional domain reconstruction for known services
        urls.extend(self.reconstruct_popular_domains(processed_text, confidence, timestamp, frame_number, region))
        
        return urls
    
    def aggressive_text_preprocessing(self, text: str) -> str:
        """Preprocess text for aggressive URL extraction"""
        # Handle common OCR errors in URLs
        text = re.sub(r'([a-zA-Z0-9])\s+([a-zA-Z0-9])', r'\1\2', text)  # Remove spaces within words
        text = re.sub(r'([a-zA-Z0-9])\s*\.\s*([a-zA-Z0-9])', r'\1.\2', text)  # Fix spaced dots
        text = re.sub(r'([a-zA-Z0-9])\s*:\s*([a-zA-Z0-9])', r'\1:\2', text)  # Fix spaced colons
        text = re.sub(r'([a-zA-Z0-9])\s*/\s*([a-zA-Z0-9])', r'\1/\2', text)  # Fix spaced slashes
        text = re.sub(r'([a-zA-Z0-9])\s*=\s*([a-zA-Z0-9])', r'\1=\2', text)  # Fix spaced equals
        text = re.sub(r'([a-zA-Z0-9])\s*&\s*([a-zA-Z0-9])', r'\1&\2', text)  # Fix spaced ampersands
        
        # Fix common OCR character mistakes
        text = re.sub(r'(?<=[a-zA-Z0-9])[O0](?=[a-zA-Z0-9])', 'o', text)  # O/0 -> o in middle of words
        text = re.sub(r'(?<=[a-zA-Z0-9])[Il1](?=[a-zA-Z0-9])', 'l', text)  # I/l/1 -> l in middle of words
        text = re.sub(r'(?<=[a-zA-Z0-9])[S5](?=[a-zA-Z0-9])', 's', text)  # S/5 -> s in middle of words
        text = re.sub(r'(?<=[a-zA-Z0-9])[Z2](?=[a-zA-Z0-9])', 'z', text)  # Z/2 -> z in middle of words
        
        # Fix protocol patterns
        text = re.sub(r'h[t]{1,3}[p]{1,2}[s]?[:\s]*[/\\]*[/\\]*', 'https://', text)
        text = re.sub(r'[w]{2,4}\.?', 'www.', text)
        
        return text
    
    def aggressive_url_cleanup(self, url: str) -> Optional[str]:
        """Clean up aggressively extracted URLs"""
        url = url.strip()
        
        # Remove trailing punctuation and brackets
        url = re.sub(r'[.,;:!?)\]\}>\'"]+$', '', url)
        
        # Remove leading punctuation and brackets
        url = re.sub(r'^[.,;:!?(\[\{<\'"]+', '', url)
        
        # Fix common protocol issues
        if url.startswith('http') and not url.startswith('http://') and not url.startswith('https://'):
            url = re.sub(r'^https?', 'https://', url)
        
        # Add protocol if missing but looks like a URL
        if not url.startswith(('http://', 'https://', 'ftp://')):
            if url.startswith('www.') or '.' in url:
                url = 'https://' + url
        
        # Clean up multiple slashes
        url = re.sub(r'([^:])/{2,}', r'\1/', url)
        
        # Remove whitespace
        url = re.sub(r'\s+', '', url)
        
        return url if len(url) > 4 else None
    
    def is_likely_url(self, url: str) -> bool:
        """Check if a string is likely to be a URL"""
        # Must contain at least one dot
        if '.' not in url:
            return False
        
        # Must have a valid TLD
        tld_pattern = r'\.(?:com|net|org|edu|gov|io|co|app|dev|tech|ai|ml|xyz|info|biz|us|uk|ca|de|fr|jp|cn|ru|in|au|br|mx|es|it|nl|se|no|dk|fi|pl|ch|at|be|cz|pt|gr|hu|ro|bg|hr|si|sk|lt|lv|ee|is|ie|lu|mt|cy|kr|sg|hk|tw|th|my|id|ph|vn|bd|pk|lk|np|mm|kh|la|mn|kz|uz|kg|tj|tm|af|ir|iq|tr|il|ps|jo|lb|sy|sa|ae|qa|kw|bh|om|ye|eg|ly|tn|dz|ma|sd|et|ke|tz|ug|rw|bi|dj|so|er|mg|mu|sc|km|mz|zm|zw|bw|na|sz|ls|za|ao|cd|cf|cm|ga|gq|st|td|ne|ml|bf|ci|gh|tg|bj|ng|gn|sl|lr|mr|sn|gm|gw|cv|html?|php|asp|jsp|py|js|css|xml|json|pdf|doc|docx|xls|xlsx|ppt|pptx)(?:[/\s?#]|$)'
        if not re.search(tld_pattern, url, re.IGNORECASE):
            return False
        
        # Must have reasonable length
        if len(url) < 4 or len(url) > 2000:
            return False
        
        # Must not be mostly special characters
        alphanumeric = len(re.findall(r'[a-zA-Z0-9]', url))
        if alphanumeric < len(url) * 0.3:
            return False
        
        # Try to parse as URL
        try:
            parsed = urlparse(url)
            if parsed.netloc or parsed.path:
                return True
        except:
            pass
        
        return False
    
    def reconstruct_popular_domains(self, text: str, confidence: float, 
                                   timestamp: float, frame_number: int, 
                                   region: str) -> List[ExtractedURL]:
        """Reconstruct URLs for popular domains that might be fragmented"""
        urls = []
        
        # Popular domain patterns with potential fragments
        domain_patterns = [
            # Social media
            (r'(?:twitter|facebook|instagram|linkedin|youtube|tiktok|discord|twitch|medium|reddit)', 
             r'(?:\.com|\.org|\.io|\.tv)', 'social'),
            # Development platforms
            (r'(?:github|gitlab|bitbucket|stackoverflow)', 
             r'(?:\.com|\.org|\.io)', 'dev'),
            # Cloud services
            (r'(?:vercel|netlify|heroku|aws|azure|cloudflare)', 
             r'(?:\.app|\.com|\.net|\.io)', 'cloud'),
            # Common services
            (r'(?:google|amazon|apple|microsoft|dropbox|slack)', 
             r'(?:\.com|\.net|\.org)', 'service'),
        ]
        
        for base_pattern, tld_pattern, category in domain_patterns:
            # Look for base domain name
            base_matches = re.finditer(base_pattern, text, re.IGNORECASE)
            for base_match in base_matches:
                base_text = base_match.group(0).lower()
                
                # Look for TLD within reasonable distance
                search_start = max(0, base_match.start() - 10)
                search_end = min(len(text), base_match.end() + 50)
                search_area = text[search_start:search_end]
                
                tld_matches = re.finditer(tld_pattern, search_area, re.IGNORECASE)
                for tld_match in tld_matches:
                    tld_text = tld_match.group(0).lower()
                    
                    # Reconstruct the URL
                    reconstructed_url = f"https://{base_text}{tld_text}"
                    
                    # Get context
                    context_start = max(0, base_match.start() - 30)
                    context_end = min(len(text), base_match.end() + 30)
                    context = text[context_start:context_end].strip()
                    
                    url_obj = ExtractedURL(
                        url=f"{base_text}...{tld_text}",
                        confidence=confidence * 0.7,  # Lower confidence for reconstruction
                        timestamp=timestamp,
                        frame_number=frame_number,
                        cleaned_url=reconstructed_url,
                        is_valid=True,
                        context_text=context,
                        region=f"{region}_reconstructed_{category}"
                    )
                    urls.append(url_obj)
        
        return urls


def preprocess_image_for_ocr(image: Image.Image) -> List[Image.Image]:
    """
    Apply multiple preprocessing techniques to improve OCR quality.
    Returns a list of processed images to try different approaches.
    """
    processed_images = []
    
    # Convert PIL to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # 1. Basic grayscale conversion
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    processed_images.append(Image.fromarray(gray))
    
    # 2. High contrast version
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    contrast_enhanced = clahe.apply(gray)
    processed_images.append(Image.fromarray(contrast_enhanced))
    
    # 3. Denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    processed_images.append(Image.fromarray(denoised))
    
    # 4. Binary threshold (black and white)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(Image.fromarray(binary))
    
    # 5. Morphological operations to clean up text
    kernel = np.ones((1,1), np.uint8)
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    processed_images.append(Image.fromarray(morphed))
    
    # 6. Resized version (2x larger for better recognition)
    height, width = gray.shape
    resized = cv2.resize(gray, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
    processed_images.append(Image.fromarray(resized))
    
    # 7. Sharpened version
    pil_gray = Image.fromarray(gray)
    sharpened = pil_gray.filter(ImageFilter.SHARPEN)
    processed_images.append(sharpened)
    
    # 8. High contrast PIL version
    enhancer = ImageEnhance.Contrast(pil_gray)
    high_contrast = enhancer.enhance(2.0)
    processed_images.append(high_contrast)
    
    return processed_images


def extract_text_with_confidence(image: Image.Image, config: str) -> Tuple[str, float]:
    """
    Extract text from image and return text with average confidence score.
    """
    try:
        # Get detailed OCR data with confidence scores
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
        
        # Filter out low-confidence text
        confidences = []
        words = []
        
        for i in range(len(data['text'])):
            confidence = int(data['conf'][i])
            text = data['text'][i].strip()
            
            if confidence > MIN_CONFIDENCE and len(text) >= MIN_TEXT_LENGTH:
                words.append(text)
                confidences.append(confidence)
        
        if not words:
            return "", 0.0
            
        extracted_text = " ".join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return extracted_text, avg_confidence
        
    except Exception as e:
        logger.debug(f"OCR extraction failed: {e}")
        return "", 0.0


def extract_text_from_frame(frame_array: np.ndarray, url_extractor: Optional[URLExtractor] = None, 
                           timestamp: float = 0.0, frame_number: int = 0) -> Dict[str, Any]:
    """
    Extract text and URLs from a single video frame using multiple OCR techniques.
    Returns the best result based on confidence and text quality, plus extracted URLs.
    """
    # Convert frame to PIL Image
    pil_image = Image.fromarray(frame_array)
    
    # Apply multiple preprocessing techniques
    processed_images = preprocess_image_for_ocr(pil_image)
    
    # Different OCR configurations to try (enhanced for URL detection)
    ocr_configs = [
        r'--oem 3 --psm 6',  # Uniform block of text
        r'--oem 3 --psm 8',  # Single word
        r'--oem 3 --psm 7',  # Single text line
        r'--oem 3 --psm 11', # Sparse text
        r'--oem 3 --psm 13', # Raw line (no heuristics)
        r'--oem 1 --psm 6',  # LSTM engine with uniform block
        r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789./:?=&-_',  # URL chars only
    ]
    
    best_result = {
        'text': '',
        'confidence': 0.0,
        'method': 'none',
        'urls': []
    }
    
    all_urls = []
    
    # Try each preprocessing method with each OCR config
    for i, processed_image in enumerate(processed_images):
        for j, config in enumerate(ocr_configs):
            try:
                text, confidence = extract_text_with_confidence(processed_image, config)
                
                # Extract URLs from this text if extractor provided
                if url_extractor and text:
                    urls = url_extractor.extract_urls_from_text(
                        text, confidence, timestamp, frame_number, 'full_frame'
                    )
                    all_urls.extend(urls)
                
                # Score the result (higher is better)
                score = confidence * (len(text) / 100.0)  # Balance confidence and text length
                current_score = best_result['confidence'] * (len(best_result['text']) / 100.0)
                
                if score > current_score and len(text) > MIN_TEXT_LENGTH:
                    best_result = {
                        'text': text,
                        'confidence': confidence,
                        'method': f'preprocess_{i}_config_{j}',
                        'urls': []
                    }
                    
            except Exception as e:
                continue
    
    # Add unique URLs to the result
    unique_urls = {}
    for url in all_urls:
        key = url.cleaned_url
        if key not in unique_urls or url.confidence > unique_urls[key].confidence:
            unique_urls[key] = url
    
    best_result['urls'] = list(unique_urls.values())
    
    return best_result


def are_frames_similar(frame1: np.ndarray, frame2: np.ndarray) -> bool:
    """
    Check if two frames are too similar to warrant separate OCR processing.
    """
    try:
        # Convert to grayscale for comparison
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY) if len(frame1.shape) == 3 else frame1
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY) if len(frame2.shape) == 3 else frame2
        
        # Resize to fixed size for comparison
        gray1 = cv2.resize(gray1, (100, 100))
        gray2 = cv2.resize(gray2, (100, 100))
        
        # Calculate structural similarity
        correlation = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]
        return correlation > FRAME_SIMILARITY_THRESHOLD
        
    except Exception:
        return False


def clean_extracted_text(text: str) -> str:
    """
    Clean up extracted text by removing obvious OCR errors and noise.
    """
    if not text:
        return ""
    
    import re
    
    # Remove single characters that are likely noise
    words = text.split()
    cleaned_words = []
    
    for word in words:
        # Skip very short words unless they're common short words
        if len(word) < 2 and word.lower() not in ['a', 'i', 'to', 'in', 'on', 'at', 'by', 'up', 'or', 'an']:
            continue
            
        # Skip words with too many special characters
        if len(re.sub(r'[a-zA-Z0-9\s]', '', word)) > len(word) * 0.5:
            continue
            
        # Skip words that are all special characters
        if re.match(r'^[^a-zA-Z0-9]+$', word):
            continue
            
        cleaned_words.append(word)
    
    cleaned_text = ' '.join(cleaned_words)
    
    # Remove excessive whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text


def verify_tesseract_installation():
    """Verify that Tesseract is properly configured and accessible."""
    try:
        # Test basic OCR functionality
        from PIL import Image
        import numpy as np
        
        # Create a simple test image with text
        test_image = Image.new('RGB', (200, 50), color='white')
        
        # Try to run OCR on the test image
        pytesseract.image_to_string(test_image)
        logger.info("[OK] Tesseract OCR is properly configured and working")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Tesseract configuration error: {e}")
        logger.error("Please ensure Tesseract is installed and accessible")
        return False


def load_checkpoint() -> Dict[str, Any]:
    """Load processing checkpoint to resume from previous state."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint with {len(checkpoint.get('processed_videos', []))} processed videos")
                return checkpoint
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading checkpoint: {e}. Starting fresh.")
    
    return {
        "processed_videos": [],
        "last_processed_date": None,
        "failed_videos": []
    }


def save_checkpoint(checkpoint: Dict[str, Any]) -> None:
    """Save current processing state to checkpoint file."""
    try:
        ensure_directories([OUTPUT_DIR])
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        logger.debug("Checkpoint saved successfully")
    except IOError as e:
        logger.error(f"Error saving checkpoint: {e}")


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_short_video_urls(channel_url: str, limit: int, lookback_days: int, checkpoint: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fetches URLs and titles of short videos from a given YouTube channel URL.
    Only fetches videos published within the lookback period.
    Filters out already processed videos based on checkpoint.
    """
    logger.info(f"Fetching short video information from {channel_url}...")
    
    # Add reasonable limits to prevent hanging
    if limit > 1000:
        logger.warning(f"[WARNING] Large limit requested ({limit}). Capping at 1000 videos to prevent hanging.")
        limit = 1000
    
    if lookback_days > 365:
        logger.warning(f"[WARNING] Large lookback period requested ({lookback_days} days). Capping at 365 days to prevent hanging.")
        lookback_days = 365
    
    # Add delay before making request to be respectful
    time.sleep(DEFAULT_REQUEST_DELAY)
    
    # Progress tracking for yt-dlp
    last_progress_time = time.time()
    
    def progress_hook(d):
        nonlocal last_progress_time
        current_time = time.time()
        if current_time - last_progress_time > 10:  # Log every 10 seconds
            logger.info(f"[PROGRESS] yt-dlp is working... (status: {d.get('status', 'unknown')})")
            last_progress_time = current_time
    
    ydl_opts = {
        "extract_flat": "discard_in_playlist", # Get individual video info
        "playlistend": min(limit * 2, 500), # Cap the initial request to prevent hanging
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "dateafter": (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d'),
        "socket_timeout": 60,  # Increased socket timeout for large channels
        "fragment_retries": 2,  # Reduced retries to fail faster
        "retries": 2,           # Reduced retries to fail faster
        "progress_hooks": [progress_hook],
        "sleep_interval": 1,    # Add delay between requests
        "max_sleep_interval": 5, # Maximum random delay
    }

    videos_info = []
    processed_ids = set(checkpoint.get("processed_videos", []))
    failed_ids = set(checkpoint.get("failed_videos", []))
    
    logger.info(f"[INFO] Checkpoint status: {len(processed_ids)} already processed, {len(failed_ids)} failed videos")
    logger.info(f"[INFO] Searching for videos from the last {lookback_days} days (limit: {limit})...")
    logger.info(f"[WARNING] Large requests may take several minutes. Initial fetch limited to {min(limit * 2, 500)} videos to prevent hanging...")
    
    try:
        logger.info("[INFO] Connecting to YouTube to fetch video metadata...")
        start_time = time.time()
        
        # Use yt-dlp's built-in timeout mechanisms with progress monitoring
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("[PROGRESS] Starting metadata extraction... This may take a few minutes for large channels.")
            result = ydl.extract_info(channel_url, download=False)
        
        fetch_time = time.time() - start_time
        logger.info(f"[OK] Metadata fetched successfully in {fetch_time:.1f} seconds")
        
        if result and "entries" in result:
            total_entries = len(result["entries"])
            logger.info(f"[INFO] Found {total_entries} total videos from channel, filtering for shorts...")
            
            if total_entries == 0:
                logger.warning("No videos found in the channel or time range")
                return []
            
            processed_count = 0
            skipped_processed = 0
            skipped_failed = 0
            
            for entry in result["entries"]:
                if entry and len(videos_info) < limit: # Respect the actual limit
                    video_id = entry.get("id")
                    title = entry.get("title", "N/A")
                    upload_date = entry.get("upload_date", "")
                    
                    processed_count += 1
                    
                    # Log progress every 50 videos for large batches
                    progress_interval = 50 if total_entries > 200 else 10
                    if processed_count % progress_interval == 0:
                        logger.info(f"[PROGRESS] Processing video {processed_count}/{total_entries} - Found {len(videos_info)} valid shorts so far...")
                    
                    # Skip if already processed or failed
                    if video_id in processed_ids:
                        logger.debug(f"Skipping already processed video: {video_id}")
                        skipped_processed += 1
                        continue
                    if video_id in failed_ids:
                        logger.debug(f"Skipping previously failed video: {video_id}")
                        skipped_failed += 1
                        continue
                    
                    if video_id:
                        videos_info.append({
                            "url": f"https://www.youtube.com/shorts/{video_id}",
                            "title": title,
                            "id": video_id,
                            "upload_date": upload_date
                        })
                        logger.debug(f"[OK] Added video {len(videos_info)}/{limit}: {title[:50]}...")
                    else:
                        logger.warning(f"Could not get video ID for an entry in {channel_url}")
                elif len(videos_info) >= limit:
                    logger.info(f"[INFO] Reached limit of {limit} videos, stopping search...")
                    break
            
            logger.info(f"[INFO] Filter summary: {len(videos_info)} new videos, {skipped_processed} already processed, {skipped_failed} previously failed")
            
        else:
            logger.warning(f"No entries found for channel {channel_url}. Result: {result}")

    except Exception as e:
        logger.error(f"Error fetching video URLs from {channel_url}: {e}")
        if "timed out" in str(e).lower():
            logger.info("[HINT] This might be due to a very large request. Try reducing --limit or --days parameters")
            logger.info("[HINT] Recommended: --limit 50 --days 30 for testing")
        raise  # Re-raise to trigger retry mechanism

    logger.info(f"[OK] Successfully found {len(videos_info)} new shorts to process from the last {lookback_days} days (after filtering already processed).")
    return videos_info


def extract_text_from_video_frames(video_path: str, frame_interval_seconds: int = 2) -> Dict[str, Any]:
    """
    Extracts text and URLs from video frames using advanced OCR techniques.
    Compatible with MoviePy 2.x with improved OCR quality and URL extraction.
    """
    logger.info(f"Starting enhanced OCR with URL extraction for video: {os.path.basename(video_path)}")
    
    # Initialize URL extractor
    url_extractor = URLExtractor()
    
    all_extracted_text = []
    all_urls = []
    video_clip = None
    previous_frame = None

    try:
        # Load video clip (compatible with MoviePy 2.x)
        video_clip = VideoFileClip(video_path)
        duration = video_clip.duration

        if duration is None:
            logger.warning(f"Could not get duration for video {video_path}. Skipping OCR.")
            return {"text": "", "urls": [], "metadata": {}}

        # Process frames with intelligent spacing
        frame_times = []
        
        # For short videos, process more frames
        if duration <= 10:
            interval = max(0.5, frame_interval_seconds / 2)
        elif duration <= 30:
            interval = frame_interval_seconds
        else:
            interval = frame_interval_seconds * 2
            
        # Generate frame timestamps
        current_time = 0
        while current_time < duration:
            frame_times.append(current_time)
            current_time += interval
        
        logger.info(f"Processing {len(frame_times)} frames from {duration:.1f}s video")
        
        processed_frames = 0
        skipped_frames = 0
        
        for i, frame_time in enumerate(frame_times):
            try:
                # Log progress for longer videos
                if len(frame_times) > 10 and (i + 1) % 5 == 0:
                    logger.info(f"[PROGRESS] OCR progress: {i+1}/{len(frame_times)} frames ({((i+1)/len(frame_times)*100):.1f}%)")
                
                # Get frame at specified time
                frame = video_clip.get_frame(frame_time)
                
                # Ensure frame is a valid numpy array
                if frame is None or not isinstance(frame, np.ndarray):
                    logger.warning(f"Invalid frame at {frame_time}s, skipping")
                    continue
                
                # Skip very similar frames
                if previous_frame is not None and are_frames_similar(frame, previous_frame):
                    skipped_frames += 1
                    continue
                
                # Extract text and URLs using enhanced OCR
                ocr_result = extract_text_from_frame(frame, url_extractor, frame_time, i)
                
                if ocr_result['confidence'] > MIN_CONFIDENCE and len(ocr_result['text']) > MIN_TEXT_LENGTH:
                    cleaned_text = clean_extracted_text(ocr_result['text'])
                    if cleaned_text:
                        all_extracted_text.append({
                            'text': cleaned_text,
                            'confidence': ocr_result['confidence'],
                            'timestamp': frame_time,
                            'method': ocr_result['method']
                        })
                        logger.debug(f"OCR @{frame_time:.1f}s (conf: {ocr_result['confidence']:.1f}): {cleaned_text[:100]}...")
                
                # Collect URLs from this frame
                if ocr_result['urls']:
                    all_urls.extend(ocr_result['urls'])
                    logger.info(f"[INFO] Found {len(ocr_result['urls'])} URLs in frame {i+1} at {frame_time:.1f}s")
                
                previous_frame = frame
                processed_frames += 1
                
                # Add small delay between frame processing
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error processing frame at {frame_time}s: {e}")
                continue

        logger.info(f"[OK] OCR complete: processed {processed_frames} frames, skipped {skipped_frames} similar frames")

    except Exception as e:
        logger.error(f"Error opening or processing video file {video_path} with MoviePy: {e}")
        return {"text": "", "urls": [], "metadata": {}}
    
    finally:
        # Always close the video clip to release resources
        if video_clip is not None:
            try:
                video_clip.close()
            except Exception as e:
                logger.warning(f"Error closing video clip: {e}")

    # Process text results
    final_text = ""
    if all_extracted_text:
        # Combine all extracted text, prioritizing high-confidence results
        all_extracted_text.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Create summary with unique text only
        unique_texts = []
        seen_texts = set()
        
        for item in all_extracted_text:
            text_lower = item['text'].lower()
            if text_lower not in seen_texts:
                unique_texts.append(item['text'])
                seen_texts.add(text_lower)
        
        final_text = " | ".join(unique_texts[:10])  # Limit to top 10 unique extractions
    
    # Process URL results
    unique_urls = {}
    for url in all_urls:
        key = url.cleaned_url
        if key not in unique_urls or url.confidence > unique_urls[key].confidence:
            unique_urls[key] = url
    
    final_urls = list(unique_urls.values())
    
    # Calculate metadata
    metadata = {
        'duration': duration,
        'processed_frames': processed_frames,
        'skipped_frames': skipped_frames,
        'total_frames': len(frame_times),
        'text_results': len(all_extracted_text),
        'url_count': len(final_urls)
    }
    
    if all_extracted_text:
        avg_confidence = sum(item['confidence'] for item in all_extracted_text) / len(all_extracted_text)
        metadata['avg_confidence'] = avg_confidence
        logger.info(f"Average confidence: {avg_confidence:.1f}%")
    
    if final_urls:
        url_domains = list(set(urlparse(url.cleaned_url).netloc for url in final_urls))
        metadata['unique_domains'] = len(url_domains)
        logger.info(f"Unique domains found: {url_domains}")
    
    logger.info(f"Enhanced OCR completed for {os.path.basename(video_path)}")
    logger.info(f"Final text length: {len(final_text)}, URLs found: {len(final_urls)}")
    
    return {
        'text': final_text,
        'urls': final_urls,
        'metadata': metadata
    }


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_video(video_id: str, output_path: str) -> Optional[str]:
    """
    Download a YouTube video to the specified path.
    Returns the path to the downloaded video file, or None if download fails.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Create a directory for this specific video
    video_specific_dir = os.path.join(output_path, video_id)
    ensure_directories([video_specific_dir])

    ydl_opts = {
        "format": "worst[ext=mp4]/worst", # Use worst quality for faster download and less bandwidth
        "outtmpl": os.path.join(video_specific_dir, '%(id)s.%(ext)s'),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,  # Add timeout
        "retries": 2,  # Built-in retries
    }

    try:
        logger.info(f"[INFO] Downloading video {video_id} (worst quality for faster processing)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Check for downloaded file with common extensions
        for ext in ['mp4', 'mkv', 'webm', 'flv', 'avi']:
            downloaded_file_path = os.path.join(video_specific_dir, f"{video_id}.{ext}")
            if os.path.exists(downloaded_file_path):
                file_size = os.path.getsize(downloaded_file_path) / 1024 / 1024  # Size in MB
                logger.info(f"[OK] Successfully downloaded video: {video_id}.{ext} ({file_size:.1f} MB)")
                return downloaded_file_path
        
        logger.error(f"Download reported success, but file not found for {video_id}")
        return None

    except Exception as e:
        logger.error(f"Error downloading video {video_id}: {e}")
        raise  # Re-raise to trigger retry mechanism


def process_single_video(video_meta: Dict[str, str], checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single video: download, OCR, and cleanup.
    Returns the processing result and updates checkpoint.
    """
    video_id = video_meta["id"]
    result: Dict[str, Any] = {
        "url": video_meta["url"],
        "title": video_meta["title"],
        "upload_date": video_meta.get("upload_date", ""),
        "processed_at": datetime.now().isoformat(),
        "ocr_description": "",
        "processing_status": "failed"
    }
    
    try:
        logger.info(f"[INFO] Processing video {video_id}: {video_meta['title']}")
        
        # Download video
        video_path = download_video(video_id, TEMP_VIDEO_DIR)
        
        if video_path:
            # Add delay before OCR processing
            logger.info(f"[WAIT] Waiting {DEFAULT_PROCESSING_DELAY}s before OCR processing...")
            time.sleep(DEFAULT_PROCESSING_DELAY)
            
            # Extract text and URLs from video with enhanced OCR
            logger.info(f"[INFO] Starting OCR analysis of video frames...")
            ocr_result = extract_text_from_video_frames(video_path, frame_interval_seconds=2)
            
            result["ocr_description"] = ocr_result["text"] if ocr_result["text"] else "No high-quality text found in video"
            result["extracted_urls"] = ocr_result["urls"]
            # Extract cleaned URLs with robust handling
            all_detected_urls = []
            for url in ocr_result["urls"]:
                if hasattr(url, 'cleaned_url'):  # It's an ExtractedURL object
                    all_detected_urls.append(url.cleaned_url)
                elif isinstance(url, dict) and 'cleaned_url' in url:  # It's a dictionary with cleaned_url
                    all_detected_urls.append(url['cleaned_url'])
                elif isinstance(url, str):  # It's a string URL
                    all_detected_urls.append(url)
            result["all_detected_urls"] = all_detected_urls  # Dedicated field for all URLs
            result["metadata"] = ocr_result["metadata"]
            result["processing_status"] = "success"
            
            # Log success with URL count
            if all_detected_urls:
                logger.info(f"[OK] Successfully processed {video_id} - Found {len(all_detected_urls)} URLs")
            else:
                logger.info(f"[OK] Successfully processed {video_id} - No URLs detected")
            
            # Clean up immediately after processing
            try:
                video_folder_path = os.path.dirname(video_path)
                if os.path.commonpath([TEMP_VIDEO_DIR, video_folder_path]) == TEMP_VIDEO_DIR:
                    shutil.rmtree(video_folder_path)
                    logger.debug(f"[CLEANUP] Cleaned up temporary video folder: {video_folder_path}")
            except Exception as e:
                logger.error(f"Error cleaning up video folder {video_folder_path}: {e}")
            
            # Update checkpoint with successful processing
            checkpoint["processed_videos"].append(video_id)
            
        else:
            logger.warning(f"[ERROR] Skipping OCR for {video_id} as download failed")
            result["ocr_description"] = "Download failed"
            checkpoint["failed_videos"].append(video_id)
            
    except Exception as e:
        logger.error(f"[ERROR] Error processing video {video_id}: {e}")
        result["ocr_description"] = f"Processing error: {str(e)}"
        checkpoint["failed_videos"].append(video_id)
    
    return result


def main(args):
    """Main function to orchestrate the ETL process."""
    logger.info("Starting Enhanced YouTube Shorts OCR ETL process...")
    logger.info(f"Using MoviePy 2.x compatible imports and advanced OCR techniques")
    logger.info(f"Project root: {get_project_root()}")
    
    # Verify Tesseract installation
    if not verify_tesseract_installation():
        logger.error("Tesseract OCR is not properly configured. Exiting.")
        return
    
    ensure_directories([OUTPUT_DIR, TEMP_VIDEO_DIR])

    # Load checkpoint
    checkpoint = load_checkpoint()
    
    logger.info(f"Targeting channel: {TARGET_CHANNEL_URL}")
    logger.info(f"Max shorts to process: {args.limit}")
    logger.info(f"Lookback period: {args.days} days")
    logger.info(f"Request delay: {args.request_delay}s")
    logger.info(f"Download delay: {args.download_delay}s")
    logger.info(f"Processing delay: {args.processing_delay}s")
    logger.info(f"Enhanced OCR: Min confidence {MIN_CONFIDENCE}%, Min text length {MIN_TEXT_LENGTH}")

    try:
        short_videos_meta = get_short_video_urls(TARGET_CHANNEL_URL, args.limit, args.days, checkpoint)
    except Exception as e:
        logger.error(f"Failed to fetch video URLs after retries: {e}")
        return

    if not short_videos_meta:
        logger.info("No new short videos found matching the criteria. Exiting.")
        return

    logger.info(f"[START] Starting to process {len(short_videos_meta)} videos...")
    all_results = []
    successful_processing = 0
    failed_processing = 0
    urls_found = 0
    
    # Track timing for estimates
    processing_start_time = time.time()
    
    # Process videos one by one with passive approach
    for i, video_meta in enumerate(short_videos_meta, 1):
        video_start_time = time.time()
        
        logger.info(f"[PROGRESS] Processing video {i}/{len(short_videos_meta)} ({(i/len(short_videos_meta)*100):.1f}% complete)")
        logger.info(f"[CURRENT] Current video: {video_meta['title']}")
        
        result = process_single_video(video_meta, checkpoint)
        all_results.append(result)
        
        # Update statistics
        if result["processing_status"] == "success":
            successful_processing += 1
            if result.get("all_detected_urls"):
                urls_found += len(result["all_detected_urls"])
        else:
            failed_processing += 1
        
        # Calculate timing estimates
        video_duration = time.time() - video_start_time
        if i > 1:  # Only show estimates after processing at least one video
            avg_time_per_video = (time.time() - processing_start_time) / i
            remaining_videos = len(short_videos_meta) - i
            estimated_time_remaining = remaining_videos * avg_time_per_video
            logger.info(f"[TIMING] Video processed in {video_duration:.1f}s. Estimated time remaining: {estimated_time_remaining/60:.1f} minutes")
        
        # Log progress summary
        logger.info(f"[PROGRESS] Progress: {successful_processing} successful, {failed_processing} failed, {urls_found} URLs found so far")
        
        # Save checkpoint after each video
        checkpoint["last_processed_date"] = datetime.now().isoformat()
        save_checkpoint(checkpoint)
        
        # Add delay between videos for passive processing
        if i < len(short_videos_meta):  # Don't delay after the last video
            logger.info(f"[WAIT] Waiting {args.request_delay}s before next video...")
            time.sleep(args.request_delay)
    
    # Final summary with total time
    total_time = time.time() - processing_start_time
    logger.info(f"[COMPLETE] Processing complete! Final stats: {successful_processing} successful, {failed_processing} failed, {urls_found} total URLs found")
    logger.info(f"[TIMING] Total processing time: {total_time/60:.1f} minutes ({total_time/len(short_videos_meta):.1f}s per video)")

    # Save final results
    output_file_path = os.path.join(OUTPUT_DIR, "youtube_shorts_ocr_results.json")
    try:
        # Load existing results if they exist
        existing_results = []
        if os.path.exists(output_file_path):
            try:
                with open(output_file_path, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Combine with new results
        all_results.extend(existing_results)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result["url"] not in seen_urls:
                # Convert ExtractedURL objects to dictionaries for JSON serialization
                if "extracted_urls" in result:
                    serialized_urls = []
                    for url in result["extracted_urls"]:
                        if hasattr(url, 'cleaned_url'):  # It's an ExtractedURL object
                            serialized_urls.append({
                                'url': url.url,
                                'cleaned_url': url.cleaned_url,
                                'confidence': url.confidence,
                                'timestamp': url.timestamp,
                                'frame_number': url.frame_number,
                                'is_valid': url.is_valid,
                                'context_text': url.context_text,
                                'region': url.region
                            })
                        else:  # It's already a dictionary
                            serialized_urls.append(url)
                    result["extracted_urls"] = serialized_urls
                
                unique_results.append(result)
                seen_urls.add(result["url"])
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(unique_results, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved {len(unique_results)} results to {output_file_path}")
        
    except IOError as e:
        logger.error(f"Error saving results to {output_file_path}: {e}")

    # Clean up empty temp directory
    try:
        if os.path.exists(TEMP_VIDEO_DIR) and not os.listdir(TEMP_VIDEO_DIR):
            shutil.rmtree(TEMP_VIDEO_DIR)
            logger.info(f"Successfully removed empty temporary directory: {TEMP_VIDEO_DIR}")
    except Exception as e:
        logger.error(f"Error removing temporary directory {TEMP_VIDEO_DIR}: {e}")

    # Summary
    successful = len([r for r in all_results if r["processing_status"] == "success"])
    failed = len(all_results) - successful
    
    # URL extraction summary
    total_urls = sum(len(r.get("extracted_urls", [])) for r in all_results)
    videos_with_urls = len([r for r in all_results if r.get("extracted_urls")])
    
    logger.info(f"Enhanced YouTube Shorts OCR ETL process completed. Success: {successful}, Failed: {failed}")
    logger.info(f"URL Extraction Summary: {total_urls} URLs found across {videos_with_urls} videos")
    
    # Show extracted URLs
    if total_urls > 0:
        logger.info("[RESULTS] EXTRACTED URLS:")
        for i, result in enumerate(all_results, 1):
            if result.get("extracted_urls"):
                print(f"\n[VIDEO] Video {i}: {result['title']}")
                for url in result["extracted_urls"]:
                    # Handle both ExtractedURL objects and dictionaries
                    if hasattr(url, 'cleaned_url'):  # It's an ExtractedURL object
                        cleaned_url = url.cleaned_url
                        confidence = url.confidence
                        timestamp = url.timestamp
                        region = url.region
                        context_text = url.context_text
                    else:  # It's a dictionary
                        cleaned_url = url.get('cleaned_url', url.get('url', 'Unknown'))
                        confidence = url.get('confidence', 0)
                        timestamp = url.get('timestamp', 0)
                        region = url.get('region', 'unknown')
                        context_text = url.get('context_text', '')
                    
                    print(f"   [URL] {cleaned_url}")
                    print(f"      Confidence: {confidence:.1f}% | Time: {timestamp:.1f}s | Region: {region}")
                    if context_text:
                        print(f"      Context: {context_text[:100]}...")
                    print()
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced YouTube Shorts OCR ETL with advanced image processing")
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_SHORTS_TO_PROCESS,
        help=f"Maximum number of shorts to process (default: {MAX_SHORTS_TO_PROCESS})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_LOOKBACK,
        help=f"Number of past days to look for shorts (default: {DEFAULT_DAYS_LOOKBACK})",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help=f"Delay between requests in seconds (default: {DEFAULT_REQUEST_DELAY})",
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=DEFAULT_DOWNLOAD_DELAY,
        help=f"Delay between downloads in seconds (default: {DEFAULT_DOWNLOAD_DELAY})",
    )
    parser.add_argument(
        "--processing-delay",
        type=float,
        default=DEFAULT_PROCESSING_DELAY,
        help=f"Delay between OCR processing in seconds (default: {DEFAULT_PROCESSING_DELAY})",
    )
    args = parser.parse_args()

    # Update global delays with command line arguments
    DEFAULT_REQUEST_DELAY = args.request_delay
    DEFAULT_DOWNLOAD_DELAY = args.download_delay
    DEFAULT_PROCESSING_DELAY = args.processing_delay

    main(args)

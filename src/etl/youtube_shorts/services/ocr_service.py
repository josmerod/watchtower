"""OCR service for text extraction from video frames."""

import logging
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance

from ..config import OCRSettings
from ..domain.models import ExtractedURL
from .url_extractor import URLExtractor

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR text extraction from images."""

    def __init__(self, settings: OCRSettings, debug: bool = False):
        """Initialize OCR service.

        Args:
            settings: OCR configuration settings
            debug: Enable debug logging
        """
        self.settings = settings
        self.debug = debug
        self.url_extractor = URLExtractor(debug=debug)

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply preprocessing techniques to improve OCR accuracy.

        Args:
            image: Input image as numpy array (RGB or grayscale)

        Returns:
            Preprocessed image
        """
        if image is None or not isinstance(image, np.ndarray):
            return image

        processed = image.copy()

        # Convert to grayscale if needed
        if len(processed.shape) == 3:
            gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
        else:
            gray = processed

        # Apply denoising
        if self.settings.use_denoising:
            try:
                gray = cv2.fastNlMeansDenoising(gray, h=10)
            except Exception as e:
                if self.debug:
                    logger.debug(f"Denoising failed: {e}")

        # Apply binarization (thresholding)
        if self.settings.use_binarization:
            try:
                # Use adaptive thresholding for better results
                gray = cv2.adaptiveThreshold(
                    gray,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11,
                    2,
                )
            except Exception as e:
                if self.debug:
                    logger.debug(f"Binarization failed: {e}")

        # Apply morphological operations to reduce noise
        if self.settings.use_thresholding:
            try:
                kernel = np.ones((1, 1), np.uint8)
                gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
                gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            except Exception as e:
                if self.debug:
                    logger.debug(f"Morphological operations failed: {e}")

        return gray

    def extract_text_with_confidence(self, image: np.ndarray) -> dict[str, Any]:
        """Extract text from image with confidence score.

        Args:
            image: Input image as numpy array

        Returns:
            Dictionary with text and confidence data
        """
        if image is None:
            return {"text": "", "confidence": 0.0, "method": "none"}

        try:
            # Get text and data from Tesseract
            data = pytesseract.image_to_data(
                image,
                config=self.settings.tesseract_config,
                lang=self.settings.tesseract_lang,
                output_type=pytesseract.Output.DICT,
            )

            # Extract text and calculate average confidence
            confidences = []
            text_parts = []

            for i, conf in enumerate(data["conf"]):
                text = data["text"][i]
                if text and text.strip():
                    text_parts.append(text.strip())
                    # Tesseract returns -1 for low confidence regions
                    if conf > 0:
                        confidences.append(conf)

            extracted_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": extracted_text,
                "confidence": avg_confidence,
                "method": "tesseract",
            }

        except Exception as e:
            if self.debug:
                logger.debug(f"OCR extraction failed: {e}")
            return {"text": "", "confidence": 0.0, "method": "failed"}

    def extract_text_from_frame(self, frame: np.ndarray, frame_time: float, frame_number: int) -> dict[str, Any]:
        """Extract text and URLs from a video frame.

        Args:
            frame: Video frame as numpy array
            frame_time: Timestamp of the frame in seconds
            frame_number: Sequential frame number

        Returns:
            Dictionary with text, URLs, and metadata
        """
        result = {
            "text": "",
            "confidence": 0.0,
            "method": "none",
            "urls": [],
        }

        if frame is None:
            return result

        try:
            # Try multiple approaches for best results
            best_result = None
            best_confidence = 0.0

            # Approach 1: Original frame with Tesseract
            ocr_result = self.extract_text_with_confidence(frame)
            if ocr_result["confidence"] > best_confidence:
                best_result = ocr_result
                best_confidence = ocr_result["confidence"]

            # Approach 2: Preprocessed frame
            preprocessed = self.preprocess_image(frame)
            ocr_result = self.extract_text_with_confidence(preprocessed)
            if ocr_result["confidence"] > best_confidence:
                best_result = ocr_result
                best_confidence = ocr_result["confidence"]

            # Approach 3: Enhanced contrast (if enabled)
            if self.settings.use_enhancement:
                try:
                    # Convert PIL Image for enhancement
                    if len(preprocessed.shape) == 2:
                        pil_image = Image.fromarray(preprocessed)
                    else:
                        pil_image = Image.fromarray(preprocessed)

                    # Enhance contrast
                    enhancer = ImageEnhance.Contrast(pil_image)
                    enhanced = enhancer.enhance(2.0)
                    enhanced_array = np.array(enhanced)

                    ocr_result = self.extract_text_with_confidence(enhanced_array)
                    if ocr_result["confidence"] > best_confidence:
                        best_result = ocr_result
                        best_confidence = ocr_result["confidence"]
                except Exception as e:
                    if self.debug:
                        logger.debug(f"Enhancement failed: {e}")

            # Use best result
            if best_result:
                result["text"] = best_result["text"]
                result["confidence"] = best_result["confidence"]
                result["method"] = best_result["method"]

                # Extract URLs from text
                if result["text"]:
                    urls = self.url_extractor.extract_urls_from_text(result["text"], confidence=best_confidence)
                    for url in urls:
                        extracted_url = ExtractedURL(
                            url=url,
                            confidence=best_confidence,
                            timestamp=frame_time,
                            frame_number=frame_number,
                            cleaned_url=url,
                            is_valid=self.url_extractor.validate_url(url),
                            context_text=result["text"][:100],
                            region="frame",
                        )
                        result["urls"].append(extracted_url.to_dict())

        except Exception as e:
            logger.error(f"Error processing frame {frame_number}: {e}")

        return result

    def are_frames_similar(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if two frames are too similar to warrant separate OCR processing.

        Args:
            frame1: First frame
            frame2: Second frame

        Returns:
            True if frames are similar, False otherwise
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
            return correlation > self.settings.frame_similarity_threshold

        except Exception:
            return False

    def clean_extracted_text(self, text: str) -> str:
        """Clean up extracted text by removing obvious OCR errors and noise.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove single characters that are likely noise
        words = text.split()
        cleaned_words = []

        # Common short words to keep
        common_short_words = {
            "a",
            "i",
            "to",
            "in",
            "on",
            "at",
            "by",
            "up",
            "or",
            "an",
        }

        for word in words:
            # Skip very short words unless they're common short words
            if len(word) < 2 and word.lower() not in common_short_words:
                continue

            # Skip words with too many special characters
            special_char_count = len([c for c in word if not c.isalnum() and not c.isspace()])
            if special_char_count > len(word) * 0.5:
                continue

            # Skip words that are all special characters
            if not any(c.isalnum() for c in word):
                continue

            cleaned_words.append(word)

        # Remove excessive whitespace
        cleaned_text = " ".join(cleaned_words)
        cleaned_text = " ".join(cleaned_text.split())

        return cleaned_text

    def verify_tesseract_installation(self) -> bool:
        """Verify that Tesseract is properly configured and accessible.

        Returns:
            True if Tesseract is working, False otherwise
        """
        try:
            # Create a simple test image with text
            test_image = Image.new("RGB", (200, 50), color="white")

            # Try to run OCR on the test image
            pytesseract.image_to_string(test_image)
            logger.info("[OK] Tesseract OCR is properly configured and working")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Tesseract configuration error: {e}")
            logger.error("Please ensure Tesseract is installed and accessible")
            return False

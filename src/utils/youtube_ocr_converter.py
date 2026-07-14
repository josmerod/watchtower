"""YouTube OCR Results Converter Utility

This module provides utilities to convert YouTube shorts OCR results
into tabular format for dashboard visualization.
"""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class YouTubeOCRConverter:
    """Converter for YouTube OCR results to various table formats."""

    def __init__(self, json_file_path: str):
        """Initialize converter with JSON file path.

        Args:
            json_file_path: Path to the YouTube OCR results JSON file
        """
        self.json_file_path = Path(json_file_path)
        self.data = self._load_json_data()

    def _load_json_data(self) -> list[dict]:
        """Load and validate JSON data."""
        try:
            with open(self.json_file_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("JSON data should be a list of records")

            logger.info(f"Loaded {len(data)} OCR records from {self.json_file_path}")
            return data

        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.json_file_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading JSON data: {e}")
            return []

    def get_basic_video_table(self) -> pd.DataFrame:
        """Get basic video information table.

        Returns:
            DataFrame with video URL, title, processing info, and basic stats
        """
        records = []

        for item in self.data:
            record = {
                "video_url": item.get("url", ""),
                "title": item.get("title", ""),
                "processed_at": item.get("processed_at", ""),
                "processing_status": item.get("processing_status", ""),
                "duration": item.get("metadata", {}).get("duration", 0),
                "processed_frames": item.get("metadata", {}).get("processed_frames", 0),
                "total_frames": item.get("metadata", {}).get("total_frames", 0),
                "url_count": item.get("metadata", {}).get("url_count", 0),
                "unique_domains": item.get("metadata", {}).get("unique_domains", 0),
                "avg_confidence": round(item.get("metadata", {}).get("avg_confidence", 0), 2),
                "ocr_text_length": len(item.get("ocr_description", "")),
                "has_extracted_urls": len(item.get("extracted_urls", [])) > 0,
            }
            records.append(record)

        df = pd.DataFrame(records)

        # Convert processed_at to datetime
        if "processed_at" in df.columns:
            df["processed_at"] = pd.to_datetime(df["processed_at"], errors="coerce")

        return df

    def get_extracted_urls_table(self) -> pd.DataFrame:
        """Get table of all extracted URLs with metadata.

        Returns:
            DataFrame with URL details, confidence scores, and context
        """
        records = []

        for item in self.data:
            video_url = item.get("url", "")
            video_title = item.get("title", "")

            for url_data in item.get("extracted_urls", []):
                record = {
                    "video_url": video_url,
                    "video_title": video_title,
                    "extracted_url": url_data.get("url", ""),
                    "cleaned_url": url_data.get("cleaned_url", ""),
                    "confidence": url_data.get("confidence", 0),
                    "timestamp": url_data.get("timestamp", 0),
                    "frame_number": url_data.get("frame_number", 0),
                    "is_valid": url_data.get("is_valid", False),
                    "context_text": url_data.get("context_text", ""),
                    "region": url_data.get("region", ""),
                    "domain": self._extract_domain(url_data.get("cleaned_url", "")),
                }
                records.append(record)

        df = pd.DataFrame(records)
        return df

    def get_domain_statistics(self) -> pd.DataFrame:
        """Get statistics grouped by domain.

        Returns:
            DataFrame with domain-level statistics
        """
        url_df = self.get_extracted_urls_table()

        if url_df.empty:
            return pd.DataFrame()

        domain_stats = (
            url_df.groupby("domain")
            .agg(
                {
                    "video_url": "nunique",
                    "extracted_url": "count",
                    "confidence": ["mean", "min", "max"],
                    "is_valid": "sum",
                }
            )
            .round(2)
        )

        # Flatten column names
        domain_stats.columns = [
            "unique_videos",
            "total_mentions",
            "avg_confidence",
            "min_confidence",
            "max_confidence",
            "valid_urls",
        ]

        domain_stats = domain_stats.reset_index()
        domain_stats = domain_stats.sort_values("total_mentions", ascending=False)

        return domain_stats

    def get_processing_statistics(self) -> pd.DataFrame:
        """Get processing statistics overview.

        Returns:
            DataFrame with processing metrics
        """
        basic_df = self.get_basic_video_table()

        if basic_df.empty:
            return pd.DataFrame()

        stats = {
            "total_videos": len(basic_df),
            "successful_processing": len(basic_df[basic_df["processing_status"] == "success"]),
            "failed_processing": len(basic_df[basic_df["processing_status"] != "success"]),
            "videos_with_urls": len(basic_df[basic_df["has_extracted_urls"]]),
            "videos_without_urls": len(basic_df[not basic_df["has_extracted_urls"]]),
            "avg_duration": round(basic_df["duration"].mean(), 2),
            "avg_frames_processed": round(basic_df["processed_frames"].mean(), 2),
            "avg_confidence": round(basic_df["avg_confidence"].mean(), 2),
            "total_urls_found": basic_df["url_count"].sum(),
            "unique_domains": basic_df["unique_domains"].sum(),
        }

        return pd.DataFrame([stats])

    def get_text_analysis_table(self) -> pd.DataFrame:
        """Get table focused on OCR text analysis.

        Returns:
            DataFrame with text analysis metrics
        """
        records = []

        for item in self.data:
            ocr_text = item.get("ocr_description", "")

            record = {
                "video_url": item.get("url", ""),
                "title": item.get("title", ""),
                "ocr_text": ocr_text,
                "text_length": len(ocr_text),
                "word_count": len(ocr_text.split()) if ocr_text else 0,
                "contains_website_keywords": any(keyword in ocr_text.lower() for keyword in ["website", "site", ".com", ".org", ".net", "http"]),
                "contains_productivity_keywords": any(keyword in ocr_text.lower() for keyword in ["productivity", "tool", "app", "software"]),
                "contains_design_keywords": any(keyword in ocr_text.lower() for keyword in ["design", "template", "mockup", "graphic"]),
                "processing_status": item.get("processing_status", ""),
                "processed_at": item.get("processed_at", ""),
            }
            records.append(record)

        df = pd.DataFrame(records)

        # Convert processed_at to datetime
        if "processed_at" in df.columns:
            df["processed_at"] = pd.to_datetime(df["processed_at"], errors="coerce")

        return df

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ""

        try:
            # Remove protocol
            if url.startswith(("http://", "https://")):
                url = url.split("://", 1)[1]

            # Extract domain
            domain = url.split("/")[0]

            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]

            return domain.lower()

        except Exception:
            return url

    def export_to_csv(self, output_dir: str = "data/youtube_shorts_ocr/") -> dict[str, str]:
        """Export all tables to CSV files.

        Args:
            output_dir: Directory to save CSV files

        Returns:
            Dictionary mapping table names to file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        tables = {
            "basic_videos": self.get_basic_video_table(),
            "extracted_urls": self.get_extracted_urls_table(),
            "domain_statistics": self.get_domain_statistics(),
            "processing_statistics": self.get_processing_statistics(),
            "text_analysis": self.get_text_analysis_table(),
        }

        file_paths = {}

        for table_name, df in tables.items():
            if not df.empty:
                file_path = output_path / f"{table_name}.csv"
                df.to_csv(file_path, index=False)
                file_paths[table_name] = str(file_path)
                logger.info(f"Exported {table_name} to {file_path}")

        return file_paths

    def get_dashboard_summary(self) -> dict:
        """Get summary statistics for dashboard display.

        Returns:
            Dictionary with key metrics for dashboard
        """
        basic_df = self.get_basic_video_table()
        url_df = self.get_extracted_urls_table()

        if basic_df.empty:
            return {}

        return {
            "total_videos_analyzed": len(basic_df),
            "successful_processing_rate": round(
                len(basic_df[basic_df["processing_status"] == "success"]) / len(basic_df) * 100,
                1,
            ),
            "videos_with_urls": len(basic_df[basic_df["has_extracted_urls"]]),
            "total_urls_extracted": len(url_df),
            "unique_domains": len(url_df["domain"].unique()) if not url_df.empty else 0,
            "avg_confidence_score": round(basic_df["avg_confidence"].mean(), 1),
            "avg_video_duration": round(basic_df["duration"].mean(), 1),
            "total_processing_time": round(basic_df["duration"].sum(), 1),
            "most_common_domains": (url_df["domain"].value_counts().head(5).to_dict() if not url_df.empty else {}),
            "processing_date_range": (
                {
                    "start": basic_df["processed_at"].min(),
                    "end": basic_df["processed_at"].max(),
                }
                if "processed_at" in basic_df.columns
                else {}
            ),
        }


def load_youtube_ocr_data(
    json_file_path: str = "data/youtube_shorts_ocr/youtube_shorts_ocr_results.json",
) -> YouTubeOCRConverter:
    """Convenience function to load YouTube OCR data.

    Args:
        json_file_path: Path to the JSON file

    Returns:
        YouTubeOCRConverter instance
    """
    return YouTubeOCRConverter(json_file_path)


# Example usage
if __name__ == "__main__":
    # Load data
    converter = load_youtube_ocr_data()

    # Export all tables to CSV
    file_paths = converter.export_to_csv()
    print("Exported files:")
    for table_name, path in file_paths.items():
        print(f"  {table_name}: {path}")

    # Print summary statistics
    summary = converter.get_dashboard_summary()
    print("\nSummary Statistics:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

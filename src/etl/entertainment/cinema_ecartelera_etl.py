"""Cinema ETL for eCartelera.com websites."""

import json
import time
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.etl.base import BaseETL
from src.models.base import TimestampedModel


class CinemaMovie(TimestampedModel):
    """Model for cinema movies."""

    title: str
    duration: str = ""
    genre: str = ""
    rating: str = ""
    director: str = ""
    cast: str = ""
    showtimes: List[str] = []
    poster_url: str = ""
    synopsis: str = ""
    trailer_url: str = ""
    cinema_name: str = ""
    date: str = ""
    source_url: str = ""


class CinemaECarteleraETL(BaseETL[dict, CinemaMovie]):
    """ETL for cinema showtimes from eCartelera.com websites."""

    def __init__(self):
        super().__init__(
            name="cinema_ecartelera",
            description="Extract cinema showtimes from eCartelera.com",
            max_retries=3,
            retry_delay=5,
        )
        self.cinema_urls = [
            {
                "name": "Cine Tívoli",
                "url": "https://www.ecartelera.com/cines/cine-tivoli/",
            },
            {
                "name": "Terrassa d'estiu Burjassot",
                "url": "https://www.ecartelera.com/cines/terrassa-destiu-burjassot/",
            },
        ]

    def get_date_range(self, days_ahead: int = 7) -> List[str]:
        """Get list of dates to check (today + next N days)."""
        dates = []
        today = datetime.now()
        for i in range(days_ahead):
            date = today + timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates

    def extract_movies_from_cinema(
        self, cinema_info: dict, page, date: str
    ) -> List[dict]:
        """Extract movies from a specific cinema page for a specific date."""
        movies = []

        try:
            # Navigate to cinema page
            self.logger.info(f"Extracting movies from {cinema_info['name']} for {date}")
            page.goto(cinema_info["url"], wait_until="networkidle")

            # Wait for page to load
            page.wait_for_timeout(2000)

            # Try to find and click date selector if available
            try:
                # Look for date navigation elements
                date_selectors = page.locator(
                    '[class*="date"], [class*="dia"], [data-date]'
                )
                if date_selectors.count() > 0:
                    # Try to find the specific date
                    target_date = datetime.strptime(date, "%Y-%m-%d")
                    date_text_options = [
                        target_date.strftime("%d"),
                        target_date.strftime("%d/%m"),
                        target_date.strftime("%Y-%m-%d"),
                        target_date.strftime("%A %d").lower(),
                    ]

                    for i in range(date_selectors.count()):
                        selector = date_selectors.nth(i)
                        selector_text = selector.inner_text().strip().lower()

                        for date_option in date_text_options:
                            if date_option.lower() in selector_text:
                                self.logger.info(
                                    f"Clicking date selector: {selector_text}"
                                )
                                selector.click()
                                page.wait_for_timeout(2000)
                                break
                        else:
                            continue
                        break
            except Exception as e:
                self.logger.debug(f"Could not interact with date selector: {e}")

            # Extract movie information
            # Look for movie containers with various possible selectors
            movie_selectors = [
                ".titem",  # Common in eCartelera
                '[class*="movie"]',
                '[class*="pelicula"]',
                '[class*="film"]',
                ".movie-item",
                ".film-item",
            ]

            movie_elements = None
            for selector in movie_selectors:
                try:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        movie_elements = elements
                        self.logger.debug(
                            f"Found {elements.count()} movies using selector: {selector}"
                        )
                        break
                except Exception:
                    continue

            if not movie_elements:
                self.logger.warning(
                    f"No movie elements found for {cinema_info['name']} on {date}"
                )
                return movies

            # Extract data from each movie element
            for i in range(movie_elements.count()):
                try:
                    movie_elem = movie_elements.nth(i)
                    movie_data = self.extract_movie_data(
                        movie_elem, cinema_info, date, page
                    )
                    if movie_data and movie_data.get("title"):
                        movies.append(movie_data)
                        self.logger.debug(f"Extracted movie: {movie_data.get('title')}")
                except Exception as e:
                    self.logger.error(f"Error extracting movie {i}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting from {cinema_info['name']}: {e}")

        return movies

    def extract_movie_data(
        self, movie_elem, cinema_info: dict, date: str, page
    ) -> dict:
        """Extract data from a single movie element."""
        movie_data = {
            "cinema_name": cinema_info["name"],
            "date": date,
            "source_url": cinema_info["url"],
        }

        try:
            # Extract title
            title_selectors = [
                "h3",
                "h2",
                "h4",
                ".title",
                '[class*="title"]',
                '[class*="titulo"]',
            ]
            for selector in title_selectors:
                try:
                    title_elem = movie_elem.locator(selector).first
                    if title_elem.count() > 0:
                        movie_data["title"] = title_elem.inner_text().strip()
                        break
                except Exception:
                    continue

            # Extract duration and genre info
            info_selectors = [
                ".info",
                ".datos",
                '[class*="info"]',
                '[class*="datos"]',
                "p",
            ]
            for selector in info_selectors:
                try:
                    info_elements = movie_elem.locator(selector)
                    for j in range(info_elements.count()):
                        info_text = info_elements.nth(j).inner_text().strip()

                        # Look for duration (e.g., "129 min.")
                        if "min" in info_text.lower() and not movie_data.get(
                            "duration"
                        ):
                            movie_data["duration"] = info_text

                        # Look for genre/rating info
                        genre_keywords = [
                            "acción",
                            "drama",
                            "comedia",
                            "thriller",
                            "romance",
                            "ciencia ficción",
                            "terror",
                            "aventura",
                        ]
                        for keyword in genre_keywords:
                            if (
                                keyword.lower() in info_text.lower()
                                and not movie_data.get("genre")
                            ):
                                movie_data["genre"] = info_text
                                break
                except Exception:
                    continue

            # Extract director
            director_selectors = [".director", '[class*="director"]']
            for selector in director_selectors:
                try:
                    director_elem = movie_elem.locator(selector).first
                    if director_elem.count() > 0:
                        director_text = director_elem.inner_text().strip()
                        movie_data["director"] = (
                            director_text.replace("Director:", "")
                            .replace("Dir:", "")
                            .strip()
                        )
                        break
                except Exception:
                    continue

            # Extract cast
            cast_selectors = [
                ".cast",
                ".reparto",
                '[class*="cast"]',
                '[class*="reparto"]',
            ]
            for selector in cast_selectors:
                try:
                    cast_elem = movie_elem.locator(selector).first
                    if cast_elem.count() > 0:
                        cast_text = cast_elem.inner_text().strip()
                        movie_data["cast"] = (
                            cast_text.replace("Reparto:", "")
                            .replace("Cast:", "")
                            .strip()
                        )
                        break
                except Exception:
                    continue

            # Extract showtimes
            showtimes = []
            time_selectors = [
                ".horarios",
                ".sesiones",
                ".times",
                '[class*="hora"]',
                '[class*="sesion"]',
            ]
            for selector in time_selectors:
                try:
                    time_elements = movie_elem.locator(selector)
                    for j in range(time_elements.count()):
                        time_text = time_elements.nth(j).inner_text().strip()
                        # Look for time patterns (HH:MM)
                        import re

                        times = re.findall(r"\b\d{1,2}:\d{2}\b", time_text)
                        showtimes.extend(times)
                except Exception:
                    continue

            movie_data["showtimes"] = list(set(showtimes))  # Remove duplicates

            # Extract poster URL
            try:
                img_elem = movie_elem.locator("img").first
                if img_elem.count() > 0:
                    poster_url = img_elem.get_attribute(
                        "src"
                    ) or img_elem.get_attribute("data-src")
                    if poster_url:
                        movie_data["poster_url"] = urljoin(
                            cinema_info["url"], poster_url
                        )
            except Exception:
                pass

            # Extract rating if available
            rating_selectors = [
                ".rating",
                ".puntuacion",
                '[class*="rating"]',
                '[class*="nota"]',
            ]
            for selector in rating_selectors:
                try:
                    rating_elem = movie_elem.locator(selector).first
                    if rating_elem.count() > 0:
                        rating_text = rating_elem.inner_text().strip()
                        movie_data["rating"] = rating_text
                        break
                except Exception:
                    continue

            # Try to extract trailer link
            try:
                trailer_elem = movie_elem.locator(
                    'a[href*="trailer"], a[href*="youtube"]'
                ).first
                if trailer_elem.count() > 0:
                    trailer_url = trailer_elem.get_attribute("href")
                    if trailer_url:
                        movie_data["trailer_url"] = trailer_url
            except Exception:
                pass

        except Exception as e:
            self.logger.error(f"Error extracting movie data: {e}")

        return movie_data

    def extract(self) -> List[dict]:
        """Extract cinema data using Playwright."""
        all_movies = []
        dates = self.get_date_range(7)  # Check next 7 days

        with sync_playwright() as p:
            # Use Chromium with headless mode
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = context.new_page()

            try:
                for cinema_info in self.cinema_urls:
                    for date in dates:
                        try:
                            movies = self.extract_movies_from_cinema(
                                cinema_info, page, date
                            )
                            all_movies.extend(movies)

                            # Small delay between requests
                            time.sleep(1)

                        except Exception as e:
                            self.logger.error(
                                f"Error processing {cinema_info['name']} for {date}: {e}"
                            )
                            continue

            finally:
                browser.close()

        self.logger.info(f"Extracted {len(all_movies)} movies from all cinemas")
        return all_movies

    def transform(self, data: List[dict]) -> List[CinemaMovie]:
        """Transform raw cinema data into structured models."""
        if not data:
            return []

        models = []
        for movie_data in data:
            try:
                # Clean and validate data
                cleaned_data = self.clean_movie_data(movie_data)
                model = CinemaMovie(**cleaned_data)
                models.append(model)
            except Exception as e:
                self.logger.error(f"Failed to create model for movie: {e}")
                continue

        return models

    def clean_movie_data(self, movie_data: dict) -> dict:
        """Clean and normalize movie data."""
        cleaned = movie_data.copy()

        # Clean title
        if "title" in cleaned:
            cleaned["title"] = cleaned["title"].strip()

        # Clean duration
        if "duration" in cleaned and cleaned["duration"]:
            duration = cleaned["duration"].strip()
            # Extract just the duration part if there's extra text
            import re

            duration_match = re.search(r"\d+\s*min", duration, re.IGNORECASE)
            if duration_match:
                cleaned["duration"] = duration_match.group()

        # Clean genre
        if "genre" in cleaned and cleaned["genre"]:
            genre = cleaned["genre"].strip()
            # Remove rating info if mixed with genre
            import re

            genre_clean = re.sub(r"\+\d+|\b\d+\b", "", genre).strip()
            cleaned["genre"] = genre_clean

        # Ensure showtimes is a list
        if "showtimes" not in cleaned:
            cleaned["showtimes"] = []
        elif isinstance(cleaned["showtimes"], str):
            # Split string showtimes
            import re

            times = re.findall(r"\b\d{1,2}:\d{2}\b", cleaned["showtimes"])
            cleaned["showtimes"] = times

        # Add metadata
        cleaned["metadata"] = {
            "extracted_at": datetime.now().isoformat(),
            "source": "ecartelera.com",
        }

        return cleaned

    def load(self, data: List[CinemaMovie]) -> None:
        """Save cinema data to JSON and CSV files."""
        if not data:
            self.logger.info("No cinema data to load")
            return

        # Convert to dictionaries
        data_dicts = [movie.model_dump() for movie in data]

        # Save JSON
        json_file = self.output_dir / "cinema_showtimes.json"
        json_file.write_text(
            json.dumps(data_dicts, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        self.logger.info(f"Saved {len(data_dicts)} movies to {json_file}")

        # Save CSV
        try:
            import pandas as pd

            csv_file = self.output_dir / "cinema_showtimes.csv"
            pd.DataFrame(data_dicts).to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved CSV to {csv_file}")
        except ImportError:
            self.logger.warning("Pandas not available, skipping CSV export")


def main():
    """Main function to run cinema ETL."""
    etl = CinemaECarteleraETL()
    try:
        metrics = etl.run()
        etl.logger.info(
            f"Cinema ETL completed successfully. Metrics: {metrics.model_dump()}"
        )
    except Exception as e:
        etl.logger.error(f"Cinema ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

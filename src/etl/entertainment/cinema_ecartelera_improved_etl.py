"""Enhanced Cinema ETL for eCartelera.com websites with improved Playwright configuration."""

import json
import random
import re
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


class CinemaECarteleraImprovedETL(BaseETL[dict, CinemaMovie]):
    """Enhanced ETL for cinema showtimes from eCartelera.com websites."""

    def __init__(self):
        super().__init__(
            name="cinema_ecartelera_improved",
            description="Extract cinema showtimes from eCartelera.com with enhanced scraping",
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

    def extract(self) -> List[dict]:
        """Extract cinema data using enhanced Playwright configuration."""
        all_movies = []
        dates = self.get_date_range(3)  # Check next 3 days to reduce load

        with sync_playwright() as p:
            # Enhanced browser configuration with anti-detection
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # Faster loading
                ],
            )

            # Enhanced context with Spanish locale
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-ES",
                timezone_id="Europe/Madrid",
                accept_downloads=False,
            )

            page = context.new_page()

            # Anti-detection script
            page.add_init_script(
                """
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en'],
                });
            """
            )

            try:
                for cinema_info in self.cinema_urls:
                    for date in dates:
                        try:
                            movies = self.extract_movies_from_cinema(
                                cinema_info, page, date
                            )
                            all_movies.extend(movies)

                            # Human-like delay between requests
                            time.sleep(random.uniform(2, 5))

                        except Exception as e:
                            self.logger.error(
                                f"Error processing {cinema_info['name']} for {date}: {e}"
                            )
                            continue

            finally:
                try:
                    context.close()
                    browser.close()
                except Exception as e:
                    self.logger.debug(f"Error closing browser: {e}")

        # Log summary
        self.logger.info(f"Extracted {len(all_movies)} movies from all cinemas")
        if all_movies:
            cinema_counts = {}
            for movie in all_movies:
                cinema = movie.get("cinema_name", "Unknown")
                cinema_counts[cinema] = cinema_counts.get(cinema, 0) + 1

            for cinema, count in cinema_counts.items():
                self.logger.info(f"  {cinema}: {count} movies")

        return all_movies

    def extract_movies_from_cinema(
        self, cinema_info: dict, page, date: str
    ) -> List[dict]:
        """Extract movies from a specific cinema page for a specific date."""
        movies = []

        try:
            self.logger.info(f"Extracting movies from {cinema_info['name']} for {date}")

            # Navigate with proper timeout and wait conditions
            page.goto(cinema_info["url"], wait_until="domcontentloaded", timeout=60000)

            # Wait for initial content
            page.wait_for_timeout(5000)

            # Debug logging
            self.logger.debug(f"Current URL: {page.url}")
            try:
                title = page.title()
                self.logger.debug(f"Page title: {title}")
            except:
                pass

            # Enhanced content loading wait
            try:
                page.wait_for_selector("body", timeout=10000)
                self.logger.debug("Page body loaded")

                # Additional wait for dynamic content
                page.wait_for_timeout(3000)

            except Exception as e:
                self.logger.debug(f"Timeout waiting for body: {e}")

            # Scroll to trigger lazy loading
            try:
                for i in range(3):
                    page.evaluate(
                        f"window.scrollTo(0, document.body.scrollHeight * {(i + 1) / 3})"
                    )
                    page.wait_for_timeout(1000)
            except Exception as e:
                self.logger.debug(f"Error scrolling: {e}")

            # Try to interact with date selectors
            self.try_select_date(page, date)

            # Extract movies using multiple strategies
            movies = self.extract_movies_multiple_strategies(page, cinema_info, date)

        except Exception as e:
            self.logger.error(f"Error extracting from {cinema_info['name']}: {e}")

        return movies

    def try_select_date(self, page, target_date: str):
        """Try to select a specific date on the page."""
        try:
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            date_text_options = [
                target_date_obj.strftime("%d"),
                target_date_obj.strftime("%d/%m"),
                target_date_obj.strftime("%Y-%m-%d"),
                target_date_obj.strftime("%A").lower()[:3],  # mon, tue, etc
                target_date_obj.strftime("%d de %B").lower(),
            ]

            # Various date selector patterns
            date_selectors = [
                '[class*="date"]',
                '[class*="dia"]',
                "[data-date]",
                'a[href*="fecha"]',
                "button[data-date]",
                ".calendar a",
                ".date-picker a",
                'select[name*="date"], select[name*="fecha"]',
                ".day-selector a",
                ".date-nav a",
            ]

            found_date_selector = False
            for selector_pattern in date_selectors:
                try:
                    elements = page.query_selector_all(selector_pattern)
                    if elements:
                        self.logger.debug(
                            f"Found {len(elements)} elements with pattern: {selector_pattern}"
                        )

                        for element in elements[:5]:  # Check first 5
                            try:
                                element_text = element.inner_text().strip().lower()
                                for date_option in date_text_options:
                                    if date_option in element_text:
                                        self.logger.info(
                                            f"Clicking date selector: {element_text}"
                                        )
                                        element.click()
                                        page.wait_for_timeout(3000)
                                        found_date_selector = True
                                        break
                                if found_date_selector:
                                    break
                            except Exception as e:
                                self.logger.debug(f"Error checking element text: {e}")
                                continue

                        if found_date_selector:
                            break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector_pattern}: {e}")
                    continue

            if not found_date_selector:
                self.logger.debug(
                    f"No date selector found for {target_date}, using current page content"
                )

        except Exception as e:
            self.logger.debug(f"Could not interact with date selector: {e}")

    def extract_movies_multiple_strategies(
        self, page, cinema_info: dict, date: str
    ) -> List[dict]:
        """Extract movies using multiple strategies."""
        movies = []

        # Strategy 1: Look for common eCartelera movie selectors
        movie_selectors = [
            ".titem",  # Common in eCartelera
            '[class*="movie"]',
            '[class*="pelicula"]',
            '[class*="film"]',
            ".movie-item",
            ".film-item",
            ".movie-card",
            ".pelicula-item",
            "[data-movie]",
            "article",
            ".content-item",
            'div[class*="cine"]',
            'div[class*="session"]',
            ".cartelera-item",
            ".showtime-item",
        ]

        movie_elements = []
        elements_found = 0

        for selector in movie_selectors:
            try:
                elements = page.query_selector_all(selector)
                element_count = len(elements)
                self.logger.debug(
                    f"Selector '{selector}': found {element_count} elements"
                )

                if element_count > 0 and elements_found == 0:
                    movie_elements = elements
                    elements_found = element_count
                    self.logger.info(
                        f"Using selector '{selector}' with {element_count} elements"
                    )

                    # Log sample content for debugging
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text_content = elem.inner_text().strip()[:100]
                            self.logger.debug(
                                f"Sample element {i + 1}: {text_content}..."
                            )
                        except:
                            pass
                    break

            except Exception as e:
                self.logger.debug(f"Error with selector {selector}: {e}")
                continue

        # Extract data from found elements
        if movie_elements:
            for i, movie_elem in enumerate(movie_elements):
                try:
                    movie_data = self.extract_movie_data_enhanced(
                        movie_elem, cinema_info, date
                    )
                    if movie_data and movie_data.get("title"):
                        movies.append(movie_data)
                        self.logger.debug(f"Extracted movie: {movie_data.get('title')}")
                except Exception as e:
                    self.logger.error(f"Error extracting movie {i}: {e}")
                    continue
        else:
            # Strategy 2: Try to find any movie-related content in page text
            try:
                all_text = page.inner_text()
                if any(
                    keyword in all_text.lower()
                    for keyword in ["película", "movie", "cine", "sesión", "horario"]
                ):
                    self.logger.debug(
                        "Found movie-related content, but no specific movie containers"
                    )

                    # Save debug HTML for analysis
                    debug_file = (
                        self.output_dir
                        / f"debug_{cinema_info['name'].replace(' ', '_')}_{date}.html"
                    )
                    debug_file.write_text(page.content(), encoding="utf-8")
                    self.logger.debug(f"Saved debug HTML to {debug_file}")

                    # Try to extract basic info from text patterns
                    movies = self.extract_from_text_patterns(
                        all_text, cinema_info, date
                    )
                else:
                    self.logger.debug("No movie-related content found")
            except Exception as e:
                self.logger.debug(f"Error analyzing page content: {e}")

        if not movies:
            self.logger.warning(
                f"No movie elements found for {cinema_info['name']} on {date}"
            )

        return movies

    def extract_from_text_patterns(
        self, text: str, cinema_info: dict, date: str
    ) -> List[dict]:
        """Extract movie info from plain text using regex patterns."""
        movies = []

        try:
            # Split text into lines and look for movie patterns
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            current_movie = None
            for line in lines:
                # Look for potential movie titles (capitalized, reasonable length)
                if re.match(r"^[A-Z][A-Za-z\s:,-]{5,50}$", line) and not any(
                    x in line.lower() for x in ["cinema", "cine", "ver", "horario"]
                ):
                    if current_movie:
                        movies.append(current_movie)

                    current_movie = {
                        "title": line,
                        "cinema_name": cinema_info["name"],
                        "date": date,
                        "source_url": cinema_info["url"],
                        "showtimes": [],
                    }

                # Look for showtimes in current line
                if current_movie:
                    times = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", line)
                    valid_times = [t for t in times if 10 <= int(t.split(":")[0]) <= 23]
                    current_movie["showtimes"].extend(valid_times)

            # Add the last movie
            if current_movie:
                movies.append(current_movie)

            # Clean up and validate
            valid_movies = []
            for movie in movies:
                if movie.get("title") and len(movie["title"]) > 3:
                    movie["showtimes"] = list(
                        set(movie["showtimes"])
                    )  # Remove duplicates
                    valid_movies.append(movie)

            self.logger.info(f"Extracted {len(valid_movies)} movies from text patterns")
            return valid_movies

        except Exception as e:
            self.logger.error(f"Error extracting from text patterns: {e}")
            return []

    def extract_movie_data_enhanced(
        self, movie_elem, cinema_info: dict, date: str
    ) -> dict:
        """Enhanced extraction of data from a single movie element."""
        movie_data = {
            "cinema_name": cinema_info["name"],
            "date": date,
            "source_url": cinema_info["url"],
        }

        try:
            # Extract title using multiple strategies
            title_selectors = [
                "h3",
                "h2",
                "h4",
                "h1",
                ".title",
                '[class*="title"]',
                '[class*="titulo"]',
                ".movie-title",
                ".film-title",
                'a[href*="pelicula"]',
                'a[href*="movie"]',
                "strong",
                "b",
            ]

            for selector in title_selectors:
                try:
                    title_elem = movie_elem.query_selector(selector)
                    if title_elem:
                        title_text = title_elem.inner_text().strip()
                        if title_text and len(title_text) > 2:
                            movie_data["title"] = title_text
                            break
                except Exception:
                    continue

            # If no title found with selectors, try text content
            if not movie_data.get("title"):
                try:
                    full_text = movie_elem.inner_text().strip()
                    lines = [
                        line.strip() for line in full_text.split("\n") if line.strip()
                    ]
                    if lines:
                        potential_title = lines[0]
                        if len(potential_title) > 2 and len(potential_title) < 100:
                            movie_data["title"] = potential_title
                except Exception:
                    pass

            # Extract comprehensive info from full text
            try:
                full_text = movie_elem.inner_text()

                # Extract duration
                duration_patterns = [
                    r"(\d+)\s*min",
                    r"(\d+h\s*\d*m?in?)",
                    r"(\d+)\s*minutos",
                ]
                for pattern in duration_patterns:
                    duration_match = re.search(pattern, full_text, re.IGNORECASE)
                    if duration_match:
                        movie_data["duration"] = duration_match.group(0)
                        break

                # Extract genre
                genre_keywords = [
                    "acción",
                    "drama",
                    "comedia",
                    "thriller",
                    "romance",
                    "ciencia ficción",
                    "terror",
                    "aventura",
                    "musical",
                    "animación",
                    "documental",
                    "familiar",
                ]
                for keyword in genre_keywords:
                    if keyword.lower() in full_text.lower():
                        lines = full_text.split("\n")
                        for line in lines:
                            if keyword.lower() in line.lower():
                                movie_data["genre"] = line.strip()
                                break
                        break

                # Extract director and cast
                lines = full_text.split("\n")
                for line in lines:
                    line_lower = line.lower().strip()

                    if (
                        "director" in line_lower or "dirigida" in line_lower
                    ) and not movie_data.get("director"):
                        director_text = line.strip()
                        for prefix in [
                            "Director:",
                            "Dir:",
                            "Dirigida por:",
                            "Directed by:",
                        ]:
                            if director_text.startswith(prefix):
                                director_text = director_text[len(prefix) :].strip()
                        movie_data["director"] = director_text

                    if (
                        "reparto" in line_lower
                        or "actores" in line_lower
                        or "protagonistas" in line_lower
                    ) and not movie_data.get("cast"):
                        cast_text = line.strip()
                        for prefix in [
                            "Reparto:",
                            "Actores:",
                            "Protagonistas:",
                            "Cast:",
                        ]:
                            if cast_text.startswith(prefix):
                                cast_text = cast_text[len(prefix) :].strip()
                        movie_data["cast"] = cast_text

                # Extract showtimes
                times = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", full_text)
                valid_times = []
                for time_str in times:
                    try:
                        hour, minute = map(int, time_str.split(":"))
                        if 10 <= hour <= 23 and 0 <= minute <= 59:
                            valid_times.append(time_str)
                    except:
                        continue

                movie_data["showtimes"] = list(set(valid_times))

                # Extract rating
                rating_patterns = [
                    r"(\d+\.\d+)/10",
                    r"(\d+)/10",
                    r"(\d+\.\d+)★",
                    r"(\d+)★",
                    r"Rating:\s*(\d+\.?\d*)",
                    r"Nota:\s*(\d+\.?\d*)",
                ]

                for pattern in rating_patterns:
                    rating_match = re.search(pattern, full_text)
                    if rating_match:
                        movie_data["rating"] = rating_match.group(1)
                        break

            except Exception as e:
                self.logger.debug(f"Error extracting comprehensive info: {e}")

            # Extract poster URL
            try:
                img_elements = movie_elem.query_selector_all("img")
                for img_elem in img_elements:
                    poster_url = (
                        img_elem.get_attribute("src")
                        or img_elem.get_attribute("data-src")
                        or img_elem.get_attribute("data-lazy")
                    )
                    if poster_url and not poster_url.startswith("data:"):
                        if poster_url.startswith("//"):
                            poster_url = "https:" + poster_url
                        elif poster_url.startswith("/"):
                            poster_url = urljoin(cinema_info["url"], poster_url)
                        elif not poster_url.startswith("http"):
                            poster_url = urljoin(cinema_info["url"], poster_url)

                        movie_data["poster_url"] = poster_url
                        break
            except Exception as e:
                self.logger.debug(f"Error extracting poster: {e}")

            # Extract trailer link
            try:
                trailer_links = movie_elem.query_selector_all(
                    'a[href*="trailer"], a[href*="youtube"], a[href*="youtu.be"]'
                )
                for link in trailer_links:
                    trailer_url = link.get_attribute("href")
                    if trailer_url:
                        movie_data["trailer_url"] = trailer_url
                        break
            except Exception as e:
                self.logger.debug(f"Error extracting trailer: {e}")

        except Exception as e:
            self.logger.error(f"Error extracting movie data: {e}")

        return movie_data

    def transform(self, data: List[dict]) -> List[CinemaMovie]:
        """Transform raw cinema data into structured models."""
        if not data:
            return []

        models = []
        for movie_data in data:
            try:
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
            duration_match = re.search(r"\d+\s*min", duration, re.IGNORECASE)
            if duration_match:
                cleaned["duration"] = duration_match.group()

        # Clean genre
        if "genre" in cleaned and cleaned["genre"]:
            genre = cleaned["genre"].strip()
            genre_clean = re.sub(r"\+\d+|\b\d+\b", "", genre).strip()
            cleaned["genre"] = genre_clean

        # Ensure showtimes is a list
        if "showtimes" not in cleaned:
            cleaned["showtimes"] = []
        elif isinstance(cleaned["showtimes"], str):
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
    """Main function to run enhanced cinema ETL."""
    etl = CinemaECarteleraImprovedETL()
    try:
        metrics = etl.run()
        etl.logger.info(
            f"Enhanced Cinema ETL completed successfully. Metrics: {metrics.model_dump()}"
        )
    except Exception as e:
        etl.logger.error(f"Enhanced Cinema ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

"""Fetches game deals, bundles, and giveaways from IsThereAnyDeal RSS feeds.

This module retrieves information about current game discounts, bundles,
and giveaways from various RSS feeds provided by IsThereAnyDeal.com.
The fetched data is processed and saved into JSON and CSV files.
"""

# Use Case: 01-Get-game-deals

# Pseudocódigo
#
# Acceder a los RSS
# Hacer retrieve de los descuentos, campañas y bundles de juegos en PC (principalmente Steam).
# - Obtener los datos de los RSS
#     -  https://isthereanydeal.com/feeds/ES/EUR/deals.rss
#     -  https://isthereanydeal.com/feeds/ES/EUR/bundles.rss
#     -  https://isthereanydeal.com/feeds/ES/EUR/giveaways.rss
# Guardar los datos de cada RSS en un dataframe
#
# Generar alertas si aplica, guardarlos y triggerear notificaciones.

import os
import re
import sys
from datetime import datetime, timedelta

import feedparser
import pandas as pd

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import fetch_with_retry

# Configurar el logger centralizado
logger = get_logger("Games_ETL")

DEALS_RSS = "https://isthereanydeal.com/feeds/ES/EUR/deals.rss"
BUNDLES_RSS = "https://isthereanydeal.com/feeds/ES/EUR/bundles.rss"
GIVEAWAYS_RSS = "https://isthereanydeal.com/feeds/ES/EUR/giveaways.rss"  # Limited to the last week to avoid issues with stale items


def get_deals():
    """Fetches game deals from IsThereAnyDeal RSS feed and saves them to CSV and JSON.

    Extracts title, link, publication date, price, discount, and store name for each deal.
    The deals are sorted by discount percentage.
    """
    logger.info("Fetching deals...")
    deals_list = []
    try:
        deals_feed = feedparser.parse(fetch_with_retry(DEALS_RSS))
        if deals_feed.bozo:
            logger.warning(f"Deals RSS feed is malformed or could not be parsed properly. Bozo exception: {deals_feed.bozo_exception}")
        logger.debug(f"Retrieved {len(deals_feed.entries)} deals from RSS feed: {DEALS_RSS}")

        for entry in deals_feed.entries:
            try:
                desc = entry.description
                prices_str = re.findall(r"<b>([\d,\.]+)", desc)
                prices_float = [float(price.replace(",", ".")) for price in prices_str]
                lowest_price = min(prices_float) if prices_float else None

                discounts_str = re.findall(r"-\d+%", desc)
                discounts_int = [int(d.strip("%").strip("-")) for d in discounts_str]
                best_discount = max(discounts_int) if discounts_int else None

                store_match = re.search(r"on <a[^>]*>([^<]+)</a>", desc)
                store_name = store_match.group(1) if store_match else None

                pub_date_str = entry.get("published", "")
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z") if pub_date_str else None

                deals_list.append(
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "published": pub_date,
                        "price": lowest_price,
                        "discount": f"-{best_discount}%" if best_discount else None,
                        "store": store_name,
                    }
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(
                    f"Error processing deal entry '{entry.get('title', 'Unknown title')}': {e}",
                    exc_info=True,
                )
                continue  # Skip to next entry

    except Exception as e:
        logger.error(f"Failed to fetch or parse deals RSS feed {DEALS_RSS}: {e}", exc_info=True)
        # Decide if we want to return partial data or nothing
        # For now, we'll proceed with what we have in deals_list

    if not deals_list:
        logger.warning("No deals were successfully processed.")
        return

    try:
        deals_df = pd.DataFrame(deals_list)
        logger.debug(f"Created DataFrame with {len(deals_df)} deals")
        deals_df = deals_df.sort_values(by="discount", ascending=False)

        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/games")
        ensure_directories(["data/games"])

        deals_csv_path = os.path.join(output_dir, "deals.csv")
        deals_json_path = os.path.join(output_dir, "deals.json")

        if os.path.exists(deals_csv_path):
            os.remove(deals_csv_path)
            logger.debug(f"Removed existing {deals_csv_path}")

        deals_df.to_json(deals_json_path, orient="records", date_format="iso")
        logger.info(f"Deals saved to {deals_json_path}")
        deals_df.to_csv(deals_csv_path, index=False, sep="|", date_format="%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"Deals saved to {deals_csv_path}")

    except OSError as e:
        logger.error(f"Error saving deals data: {e}", exc_info=True)
    except ImportError:
        logger.error("Pandas library not found. Cannot save deals to CSV/JSON.", exc_info=True)
    except Exception as e:  # Catch other potential errors during DataFrame ops or saving
        logger.error(f"An unexpected error occurred while saving deals: {e}", exc_info=True)


def get_bundles():
    """Fetches game bundles from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract:
    - title : name of the bundle (of the publisher), not the name of the games
    - link : link to isthereanydeal
    - published : date of publication, in GMT+0100
    - price : highest price of the bundle (highest tier)
    - games : list of all included games in the bundle, using a python list
    """
    logger.info("Fetching bundles...")
    bundles_list = []
    try:
        bundles_feed = feedparser.parse(fetch_with_retry(BUNDLES_RSS))
        if bundles_feed.bozo:
            logger.warning(f"Bundles RSS feed is malformed. Bozo exception: {bundles_feed.bozo_exception}")
        logger.debug(f"Retrieved {len(bundles_feed.entries)} bundles from RSS feed: {BUNDLES_RSS}")

        for entry in bundles_feed.entries:
            try:
                pub_date_str = entry.get("published", "")
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z") if pub_date_str else None

                games = re.findall(
                    r'<a href="https://isthereanydeal.com/game/[^"]+/info/">([^<]+)</a>',
                    entry.description,
                )
                prices_str = re.findall(r"Price: ([0-9,.]+)", entry.description)
                prices_float = [float(price.replace(",", ".")) for price in prices_str]
                highest_price = max(prices_float) if prices_float else None

                bundles_list.append(
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "published": pub_date,
                        "price": highest_price,
                        "games": games,
                    }
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(
                    f"Error processing bundle entry '{entry.get('title', 'Unknown title')}': {e}",
                    exc_info=True,
                )
                continue

    except Exception as e:
        logger.error(
            f"Failed to fetch or parse bundles RSS feed {BUNDLES_RSS}: {e}",
            exc_info=True,
        )

    if not bundles_list:
        logger.warning("No bundles were successfully processed.")
        return

    try:
        bundles_df = pd.DataFrame(bundles_list)
        logger.debug(f"Created DataFrame with {len(bundles_df)} bundles")
        bundles_df = bundles_df.sort_values(by="published", ascending=False)

        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/games")
        ensure_directories(["data/games"])  # Ensure_directories should ideally be called once

        bundles_json_path = os.path.join(output_dir, "bundles.json")
        bundles_csv_path = os.path.join(output_dir, "bundles.csv")

        bundles_df.to_json(bundles_json_path, orient="records", date_format="iso")
        logger.info(f"Bundles saved to {bundles_json_path}")
        bundles_df.to_csv(bundles_csv_path, index=False, sep="|", date_format="%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"Bundles saved to {bundles_csv_path}")

    except OSError as e:
        logger.error(f"Error saving bundles data: {e}", exc_info=True)
    except ImportError:
        logger.error("Pandas library not found. Cannot save bundles to CSV/JSON.", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while saving bundles: {e}", exc_info=True)


def get_giveaways():
    """Fetches game giveaways from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract:
    - title
    - link
    - published
    - expires
    """
    logger.info("Fetching giveaways...")
    giveaways_list = []
    try:
        giveaways_feed = feedparser.parse(fetch_with_retry(GIVEAWAYS_RSS))
        if giveaways_feed.bozo:
            logger.warning(f"Giveaways RSS feed is malformed. Bozo exception: {giveaways_feed.bozo_exception}")
            # Still try to process what we can

        logger.debug(f"Retrieved {len(giveaways_feed.entries)} giveaways from RSS feed: {GIVEAWAYS_RSS}")

        for entry in giveaways_feed.entries:
            try:
                title = entry.title
                link = entry.link
                published_str = entry.get("published", "")
                published = datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S %z") if published_str else None

                description = entry.description
                expires_match = re.search(r"expires on ([^<|]+)", description)
                expires_str = expires_match.group(1).strip() if expires_match else None
                expires = datetime.strptime(expires_str, "%a, %d %b %Y %H:%M:%S %z") if expires_str else None

                if expires and expires < datetime.now(expires.tzinfo):
                    logger.debug(f"Skipping expired giveaway: {title}")
                    continue
                if published and published < datetime.now(published.tzinfo) - timedelta(days=14):
                    logger.debug(f"Skipping old giveaway (published > 14 days ago): {title}")
                    continue

                giveaways_list.append(
                    {
                        "title": title,
                        "link": link,
                        "published": published,
                        "expires": expires,
                    }
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(
                    f"Error processing giveaway entry '{entry.get('title', 'Unknown title')}': {e}",
                    exc_info=True,
                )
                continue

    except Exception as e:
        logger.error(
            f"Failed to fetch or parse giveaways RSS feed {GIVEAWAYS_RSS}: {e}",
            exc_info=True,
        )

    if not giveaways_list:
        logger.warning("No giveaways were successfully processed.")
        # Create empty files to maintain consistency with data structure
        try:
            project_root = get_project_root()
            output_dir = os.path.join(project_root, "data/games")
            ensure_directories(["data/games"])

            giveaways_json_path = os.path.join(output_dir, "giveaways.json")
            giveaways_csv_path = os.path.join(output_dir, "giveaways.csv")

            # Create empty JSON and CSV files
            with open(giveaways_json_path, "w") as f:
                f.write("[]")

            with open(giveaways_csv_path, "w") as f:
                f.write("title|link|published|expires\n")  # Header only

            logger.info(f"Empty giveaways files created at {giveaways_json_path} and {giveaways_csv_path}")
        except Exception as e:
            logger.error(f"Error creating empty giveaways files: {e}")
        return

    try:
        giveaways_df = pd.DataFrame(giveaways_list)
        logger.debug(f"Created DataFrame with {len(giveaways_df)} active giveaways")
        if not giveaways_df.empty:
            giveaways_df = giveaways_df.sort_values(by="published", ascending=False)

        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/games")
        ensure_directories(["data/games"])

        giveaways_json_path = os.path.join(output_dir, "giveaways.json")
        giveaways_csv_path = os.path.join(output_dir, "giveaways.csv")

        giveaways_df.to_json(giveaways_json_path, orient="records", date_format="iso")
        logger.info(f"Giveaways saved to {giveaways_json_path}")
        giveaways_df.to_csv(giveaways_csv_path, index=False, sep="|", date_format="%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"Giveaways saved to {giveaways_csv_path}")

    except OSError as e:
        logger.error(f"Error saving giveaways data: {e}", exc_info=True)
    except ImportError:
        logger.error(
            "Pandas library not found. Cannot save giveaways to CSV/JSON.",
            exc_info=True,
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while saving giveaways: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting Games ETL process")
    try:
        get_deals()
        get_bundles()
        get_giveaways()
        logger.info("Games ETL process completed successfully")
    except Exception as e:
        logger.error(f"Games ETL process failed: {e}", exc_info=True)
        sys.exit(1)

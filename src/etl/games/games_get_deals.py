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
#     -  https://isthereanydeal.com/feeds/ES/giveaways.rss
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
# No currency segment: a giveaway states no price. The old /ES/EUR/ address answers 404.
# Limited to the last week to avoid issues with stale items
GIVEAWAYS_RSS = "https://isthereanydeal.com/feeds/ES/giveaways.rss"

# The site answers 403 to the default "Python-urllib" client and serves any named one. Unnamed, the feeds went
# unread from 2026-07-22 on while every run still ended with exit code 0.
HEADERS = {"User-Agent": "Watchtower/1.0 (https://github.com/josmerod/watchtower)"}
CURRENCY = "EUR"  # the feeds above are the ES/EUR ones: prices come as "10,80 €"


def _save(frame: pd.DataFrame, name: str) -> bool:
    """Write *frame* to data/games/<name>.json and .csv; False when a write failed.

    The JSON is replaced in one step, so a failed write leaves the previous file whole for the dashboard.
    """
    try:
        output_dir = os.path.join(get_project_root(), "data/games")
        ensure_directories(["data/games"])
        json_path = os.path.join(output_dir, f"{name}.json")
        partial_path = f"{json_path}.partial"
        csv_path = os.path.join(output_dir, f"{name}.csv")
        frame.to_json(partial_path, orient="records", date_format="iso")
        os.replace(partial_path, json_path)
        frame.to_csv(csv_path, index=False, sep="|", date_format="%Y-%m-%dT%H:%M:%SZ")
    except OSError as e:
        logger.error(f"Error saving {name} data: {e}", exc_info=True)
        return False
    except Exception as e:  # broad by design: pandas DataFrame/CSV serialization of scraped data
        logger.error(f"An unexpected error occurred while saving {name}: {e}", exc_info=True)
        return False
    logger.info(f"{name.capitalize()} saved to {json_path} and {csv_path}")
    return True


def get_deals() -> bool:
    """Fetches game deals from IsThereAnyDeal RSS feed and saves them to CSV and JSON.

    Extracts title, link, publication date, price, discount, and store name for each deal.
    The deals are sorted by discount percentage.

    Returns:
        True when the feed was read and its deals saved, False when nothing was written.
    """
    logger.info("Fetching deals...")
    deals_list = []
    fetched = True
    try:
        deals_feed = feedparser.parse(fetch_with_retry(DEALS_RSS, headers=HEADERS))
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
                        "currency": CURRENCY,
                    }
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(
                    f"Error processing deal entry '{entry.get('title', 'Unknown title')}': {e}",
                    exc_info=True,
                )
                continue  # Skip to next entry

    except Exception as e:  # broad by design: feed fetch + parse wrapper (feedparser/network)
        logger.error(f"Failed to fetch or parse deals RSS feed {DEALS_RSS}: {e}", exc_info=True)
        fetched = False

    if not fetched:
        return False
    if not deals_list:
        logger.warning("No deals were successfully processed.")
        return False

    try:
        deals_df = pd.DataFrame(deals_list)
        logger.debug(f"Created DataFrame with {len(deals_df)} deals")
        deals_df = deals_df.sort_values(by="discount", ascending=False)
    except Exception as e:  # broad by design: pandas DataFrame operations on scraped data
        logger.error(f"An unexpected error occurred while preparing deals: {e}", exc_info=True)
        return False
    return _save(deals_df, "deals")


def get_bundles() -> bool:
    """Fetches game bundles from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract:
    - title : name of the bundle (of the publisher), not the name of the games
    - link : link to isthereanydeal
    - published : date of publication, in GMT+0100
    - price : highest price of the bundle (highest tier)
    - games : list of all included games in the bundle, using a python list

    Returns:
        True when the feed was read and its bundles saved, False when nothing was written.
    """
    logger.info("Fetching bundles...")
    bundles_list = []
    fetched = True
    try:
        bundles_feed = feedparser.parse(fetch_with_retry(BUNDLES_RSS, headers=HEADERS))
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
                        "currency": CURRENCY,
                    }
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(
                    f"Error processing bundle entry '{entry.get('title', 'Unknown title')}': {e}",
                    exc_info=True,
                )
                continue

    except Exception as e:  # broad by design: feed fetch + parse wrapper (feedparser/network)
        logger.error(
            f"Failed to fetch or parse bundles RSS feed {BUNDLES_RSS}: {e}",
            exc_info=True,
        )
        fetched = False

    if not fetched:
        return False
    if not bundles_list:
        logger.warning("No bundles were successfully processed.")
        return False

    try:
        bundles_df = pd.DataFrame(bundles_list)
        logger.debug(f"Created DataFrame with {len(bundles_df)} bundles")
        bundles_df = bundles_df.sort_values(by="published", ascending=False)
    except Exception as e:  # broad by design: pandas DataFrame operations on scraped data
        logger.error(f"An unexpected error occurred while preparing bundles: {e}", exc_info=True)
        return False
    return _save(bundles_df, "bundles")


def get_giveaways() -> bool:
    """Fetches game giveaways from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract:
    - title
    - link
    - published
    - expires

    Returns:
        True when the feed was read (empty files when it holds no live giveaway), False when it was not.
    """
    logger.info("Fetching giveaways...")
    giveaways_list = []
    fetched = True
    try:
        giveaways_feed = feedparser.parse(fetch_with_retry(GIVEAWAYS_RSS, headers=HEADERS))
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

    except Exception as e:  # broad by design: feed fetch + parse wrapper (feedparser/network)
        logger.error(
            f"Failed to fetch or parse giveaways RSS feed {GIVEAWAYS_RSS}: {e}",
            exc_info=True,
        )
        fetched = False

    if not fetched:
        return False
    if not giveaways_list:
        # Empty files keep the shape of the data for whoever reads it
        logger.warning("No giveaways were successfully processed.")
        return _save(pd.DataFrame(columns=["title", "link", "published", "expires"]), "giveaways")

    try:
        giveaways_df = pd.DataFrame(giveaways_list)
        logger.debug(f"Created DataFrame with {len(giveaways_df)} active giveaways")
        giveaways_df = giveaways_df.sort_values(by="published", ascending=False)
    except Exception as e:  # broad by design: pandas DataFrame operations on scraped data
        logger.error(f"An unexpected error occurred while preparing giveaways: {e}", exc_info=True)
        return False
    return _save(giveaways_df, "giveaways")


def main() -> None:
    """Read the three feeds; the exit code tells the scheduler whether every feed was read."""
    logger.info("Starting Games ETL process")
    ok = True
    for step in (get_deals, get_bundles, get_giveaways):
        try:
            if not step():
                ok = False
        except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
            logger.error(f"Games ETL process failed in {step.__name__}: {e}", exc_info=True)
            ok = False
    if not ok:
        # A feed that could not be read leaves its previous file in place: that is a failed run, not a quiet one
        logger.error("Games ETL process finished with a feed that could not be read")
        sys.exit(1)
    logger.info("Games ETL process completed successfully")


if __name__ == "__main__":
    main()

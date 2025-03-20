# Use Case: 01-Get-game-deals

"""Pseudocódigo

Acceder a los RSS
Hacer retrieve de los descuentos, campañas y bundles de juegos en PC (principalmente Steam).
- Obtener los datos de los RSS
    -  https://isthereanydeal.com/feeds/ES/EUR/deals.rss
    -  https://isthereanydeal.com/feeds/ES/EUR/bundles.rss
    -  https://isthereanydeal.com/feeds/ES/giveaways.rss
Guardar los datos de cada RSS en un dataframe

Generar alertas si aplica, guardarlos y triggerear notificaciones.

"""

import sys
import feedparser
from datetime import datetime, timedelta
import pandas as pd
import re
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils.logging import get_logger

# Add the project root to the path to ensure imports work correctly

# Configurar el logger centralizado
logger = get_logger("Games_ETL")

DEALS_RSS = "https://isthereanydeal.com/feeds/ES/EUR/deals.rss"
BUNDLES_RSS = "https://isthereanydeal.com/feeds/ES/EUR/bundles.rss"
GIVEAWAYS_RSS = "https://isthereanydeal.com/feeds/ES/EUR/giveaways.rss"  # Limited to the last week to avoid issues with stale items


def get_deals():
    logger.info("Fetching deals...")

    # Obtener los datos de los RSS
    deals = feedparser.parse(DEALS_RSS)
    logger.debug(f"Retrieved {len(deals.entries)} deals from RSS feed")

    # Convert feedparser entries to list of dicts for DataFrame
    deals_list = []
    for entry in deals.entries:
        # Extract description content between CDATA tags
        desc = entry.description

        # Find all prices using regex pattern that matches numbers with commas/dots
        # The pattern needs to handle prices like "19,99 €" or "26,36 €"
        prices = re.findall(r"<b>([\d,\.]+)", desc)

        # Convert prices to floats
        prices_float = [float(price.replace(",", ".")) for price in prices]

        if prices_float:
            lowest_price = min(prices_float)
        else:
            lowest_price = None

        # Find all discounts using regex pattern that matches negative percentages
        discounts = re.findall(r"-\d+%", desc)
        # Convert percentage strings to integers
        discounts = [int(d.strip("%").strip("-")) for d in discounts]

        # Get best price (lowest) and best discount (highest)
        best_discount = max(discounts) if discounts else None

        # Find store name
        store = re.search(r"on <a[^>]*>([^<]+)</a>", desc)
        store_name = store.group(1) if store else None

        # Parse publication date
        pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")

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

    # Create DataFrames from lists of dicts
    deals_df = pd.DataFrame(deals_list)
    logger.debug(f"Created DataFrame with {len(deals_df)} deals")

    # Order deals by percentage discount
    deals_df = deals_df.sort_values(by="discount", ascending=False)

    # Create output directory if it doesn't exist
    os.makedirs("data/games", exist_ok=True)
    # Replace current csv file if exists
    if os.path.exists("data/games/deals.csv"):
        os.remove("data/games/deals.csv")
        logger.debug("Removed existing deals.csv file")

    # Save deals to json
    deals_df.to_json("data/games/deals.json", orient="records")
    logger.info("Deals saved to json")

    # Save deals to csv
    deals_df.to_csv("data/games/deals.csv", index=False, sep="|")
    logger.info("Deals saved to csv")


def get_bundles():
    """
    Fetches game bundles from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract: 
    - title : name of the bundle (of the publisher), not the name of the games
    - link : link to isthereanydeal
    - published : date of publication, in GMT+0100
    - price : highest price of the bundle (highest tier)
    - games : list of all included games in the bundle, using a python list
    """

    logger.info("Fetching bundles...")
    bundles = feedparser.parse(BUNDLES_RSS)
    logger.debug(f"Retrieved {len(bundles.entries)} bundles from RSS feed")

    bundles_list = []
    for entry in bundles.entries:
        # Extract bundle name from title
        bundle_name = entry.title

        # Extract link
        bundle_link = entry.link

        # Parse publication date
        pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")

        # Extract games from description
        games = re.findall(
            r'<a href="https://isthereanydeal.com/game/[^"]+/info/">([^<]+)</a>',
            entry.description,
        )

        # Extract prices
        prices = re.findall(r"Price: ([0-9,.]+)", entry.description)
        # Convert prices to float
        if prices:
            prices = [float(price.replace(",", ".")) for price in prices]
            highest_price = max(prices)
        else:
            highest_price = None

        bundles_list.append(
            {
                "title": bundle_name,
                "link": bundle_link,
                "published": pub_date,
                "price": highest_price,
                "games": games,
            }
        )

    # Create DataFrame from list of dicts
    bundles_df = pd.DataFrame(bundles_list)
    logger.debug(f"Created DataFrame with {len(bundles_df)} bundles")

    # Sort bundles by publication date (newest first)
    bundles_df = bundles_df.sort_values(by="published", ascending=False)

    # Create output directory if it doesn't exist
    os.makedirs("data/games", exist_ok=True)

    # Save bundles to json
    bundles_df.to_json("data/games/bundles.json", orient="records")
    logger.info("Bundles saved to json")

    bundles_df.to_csv("data/games/bundles.csv", index=False, sep="|")
    logger.info("Bundles saved to csv")


def get_giveaways():
    """
    Fetches game giveaways from IsThereAnyDeal RSS feed and saves them to CSV.

    Values to extract:
    - title
    - link
    - published
    - expires
    """

    logger.info("Fetching giveaways...")
    # Parse the RSS feed
    giveaways_feed = feedparser.parse(
        "https://isthereanydeal.com/feeds/ES/giveaways.rss"
    )
    logger.debug(f"Retrieved {len(giveaways_feed.entries)} giveaways from RSS feed")

    # Create a list to store giveaway data
    giveaways_list = []

    # Process each entry in the feed
    for entry in giveaways_feed.entries:
        # Extract basic information
        title = entry.title
        link = entry.link
        published = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")

        # Parse the description to extract game info and expiry date
        description = entry.description

        # Extract expiry date
        expires_match = re.search(r"expires on ([^<|]+)", description)
        expires = expires_match.group(1) if expires_match else "unknown expiry"

        # Convert expiry date to datetime object
        if expires != "unknown expiry":
            expires = datetime.strptime(expires.strip(), "%a, %d %b %Y %H:%M:%S %z")

        # Filter if the giveaway is expired
        if expires != "unknown expiry" and expires < datetime.now(expires.tzinfo):
            logger.debug(f"Skipping expired giveaway: {title}")
            continue

        # Filter if the giveaway date is more than 2 weeks old
        if published < datetime.now(published.tzinfo) - timedelta(days=14):
            logger.debug(f"Skipping old giveaway: {title}")
            continue

        # Add to list
        giveaways_list.append(
            {
                "title": title,
                "link": link,
                "published": published,
                "expires": expires,
            }
        )

    # Create DataFrame from list of dicts
    giveaways_df = pd.DataFrame(giveaways_list)
    logger.debug(f"Created DataFrame with {len(giveaways_df)} active giveaways")

    # Sort giveaways by publication date (newest first)
    giveaways_df = giveaways_df.sort_values(by="published", ascending=False)

    # Create output directory if it doesn't exist
    os.makedirs("data/games", exist_ok=True)

    # Save giveaways to json
    giveaways_df.to_json("data/games/giveaways.json", orient="records")
    logger.info("Giveaways saved to json")

    # Save giveaways to csv
    giveaways_df.to_csv("data/games/giveaways.csv", index=False, sep="|")
    logger.info("Giveaways saved to csv")


if __name__ == "__main__":
    logger.info("Starting Games ETL process")
    get_deals()
    get_bundles()
    get_giveaways()
    logger.info("Games ETL process completed successfully")

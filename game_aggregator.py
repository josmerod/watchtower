# game_aggregator.py
from game_fetchers import itchio_fetcher

def get_top_rated_games_prioritizing_free(limit=None):
    """
    Fetches top-rated games and sorts them to prioritize free games.
    The original order from the feed (presumably already ranked) is maintained
    within the 'free' and 'paid' groups.
    """
    top_rated_games = itchio_fetcher.fetch_top_rated_games()
    if not top_rated_games:
        return []

    # Separate into free and paid, maintaining original relative order
    free_games = [game for game in top_rated_games if game.get('is_free', False)]
    paid_games = [game for game in top_rated_games if not game.get('is_free', False)]

    # Combine, with free games first
    prioritized_list = free_games + paid_games

    if limit is not None and isinstance(limit, int):
        return prioritized_list[:limit]
    return prioritized_list

def get_trending_games(limit=None):
    """
    Fetches trending (featured) games.
    """
    trending_games = itchio_fetcher.fetch_featured_games()
    if not trending_games:
        return []

    if limit is not None and isinstance(limit, int):
        return trending_games[:limit]
    return trending_games

def get_dedicated_free_games_list(limit=None):
    """
    Fetches games specifically from the 'free games' feed.
    This list might have different sorting/ranking than 'top_rated' free games.
    """
    free_games_feed = itchio_fetcher.fetch_free_games()
    if not free_games_feed:
        return []

    if limit is not None and isinstance(limit, int):
        return free_games_feed[:limit]
    return free_games_feed

if __name__ == '__main__':
    print("--- Top Rated Games (Free first) ---")
    top_rated_prioritized = get_top_rated_games_prioritizing_free(limit=10)
    if top_rated_prioritized:
        for i, game in enumerate(top_rated_prioritized):
            price = "FREE" if game.get('is_free') else f"${game.get('price_value', 0):.2f}"
            print(f"{i+1}. {game.get('title')} ({price}) - Source: {game.get('fetch_source')}")
    else:
        print("No top-rated games found.")

    print("\n--- Trending Games ---")
    trending = get_trending_games(limit=5)
    if trending:
        for i, game in enumerate(trending):
            price = "FREE" if game.get('is_free') else f"${game.get('price_value', 0):.2f}"
            print(f"{i+1}. {game.get('title')} ({price}) - Source: {game.get('fetch_source')}")
    else:
        print("No trending games found.")

    print("\n--- Dedicated Free Games List ---")
    dedicated_free = get_dedicated_free_games_list(limit=5)
    if dedicated_free:
        for i, game in enumerate(dedicated_free):
            # All these should be free by definition of the feed
            price = "FREE" if game.get('is_free') else f"Check Price (should be free: ${game.get('price_value', 0):.2f})"
            print(f"{i+1}. {game.get('title')} ({price}) - Source: {game.get('fetch_source')}")
    else:
        print("No games found in dedicated free feed.")

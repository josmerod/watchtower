# display_games.py
import game_aggregator # Uses the new game aggregator

def display_game_details(game_list, list_title="Game List"):
    """Prints a list of games to the console, with detailed fields."""
    if not game_list:
        print(f"No games to display for: {list_title}")
        return

    print(f"\n--- {list_title.upper()} ---")
    for i, game in enumerate(game_list):
        print(f"\n--- Game #{i+1} ---")
        print(f"Title:         {game.get('title', 'N/A')}")
        print(f"Link:          {game.get('url', '#')}")

        developer = game.get('developer_name', 'Unknown Developer')
        if game.get('developer_url'):
            developer += f" ({game.get('developer_url')})"
        print(f"Developer:     {developer}") # Placeholder, will be 'Unknown Developer' for now

        print(f"Cover Image:   {game.get('cover_image_url', 'N/A')}")

        if game.get('is_free', False):
            price_display = "FREE"
        else:
            price_display = f"{game.get('price_value', 0.0):.2f} {game.get('price_currency', 'USD')}"
        print(f"Price:         {price_display}")

        print(f"Description:   {game.get('description_short', 'N/A')}") # This is raw HTML from RSS

        pub_date = game.get('published_date')
        if pub_date:
            print(f"Published:     {pub_date.strftime('%Y-%m-%d %H:%M:%S') if pub_date else 'N/A'}")
        else:
            print(f"Published:     N/A")

        # Placeholder fields, will be empty or None for now
        print(f"Platforms:     {', '.join(game.get('platforms', [])) or 'N/A'}")
        print(f"Genres:        {', '.join(game.get('genres', [])) or 'N/A'}")
        print(f"Tags:          {', '.join(game.get('tags', [])) or 'N/A'}")

        if game.get('rating_average') is not None:
            ratings = str(game.get('rating_average'))
            if game.get('rating_count') is not None:
                ratings += f" (from {game.get('rating_count')} ratings)"
            print(f"Rating:        {ratings}") # Placeholder
        else:
            print(f"Rating:        N/A") # Placeholder

        print(f"Fetched From:  {game.get('fetch_source', 'N/A')}")
    print(f"\n--- END OF {list_title.upper()} ---")

if __name__ == "__main__":
    print("Fetching and displaying itch.io game information...")

    # Fetch Top Rated Games (prioritizing free)
    top_rated_games = game_aggregator.get_top_rated_games_prioritizing_free(limit=3) # Limit for brevity
    display_game_details(top_rated_games, "Top Rated Games (Free First)")

    # Fetch Trending Games
    trending_games = game_aggregator.get_trending_games(limit=2) # Limit for brevity
    display_game_details(trending_games, "Trending Games")

    # Fetch Dedicated Free Games List
    free_games_list = game_aggregator.get_dedicated_free_games_list(limit=2) # Limit for brevity
    display_game_details(free_games_list, "Dedicated Free Games List")

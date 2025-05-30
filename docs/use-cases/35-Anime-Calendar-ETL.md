# Use Case 35: Anime Calendar & Guide ETL

## 1. Objective

This ETL process is designed to fetch comprehensive data about anime from the MyAnimeList (MAL) API. It gathers information on currently airing seasonal anime, top popular anime across all time, and top-rated anime. This data is then used to populate the "Anime Calendar & Guide" tab in the Watchtower dashboard, providing users with up-to-date anime insights.

## 2. Data Source

*   **Name:** MyAnimeList (MAL) API v2
*   **Type:** Public API
*   **Documentation:** [MyAnimeList API v2 Reference](https://myanimelist.net/apiconfig/references/api/v2)

## 3. Key Functionality

*   **Seasonal Anime:** Fetches a list of anime airing in the current season (Winter, Spring, Summer, Fall).
*   **Popular Anime:** Retrieves a list of the most popular anime series based on the number of users who have them on their list.
*   **Top-Rated Anime:** Fetches a list of the highest-rated anime series based on user scores.
*   **Data Enrichment:** For each anime, it collects details such as title, synopsis, cover image, mean score, rank, popularity, number of episodes, genres, studios, media type, and source material.

## 4. Script Location

*   `src/etl/anime/mal_etl.py`

## 5. Output

The ETL script processes the fetched data and saves it into the following JSON files:

*   `data/anime/current_season_anime.json`: Contains data for anime in the current airing season.
*   `data/anime/top_popular_anime.json`: Contains data for the most popular anime.
*   `data/anime/top_rated_anime.json`: Contains data for the top-rated anime.

## 6. Configuration

### API Access

This ETL requires access to the MyAnimeList API, which necessitates a Client ID.

*   **Environment Variable:** `MAL_CLIENT_ID`
*   **Obtaining a Client ID:**
    1.  Log in to your MyAnimeList account.
    2.  Navigate to the API configuration page: [https://myanimelist.net/apiconfig](https://myanimelist.net/apiconfig).
    3.  Create a new API client. You'll need to provide details like the application name and purpose.
    4.  Once created, your Client ID will be provided.
    5.  Set this Client ID as the value for the `MAL_CLIENT_ID` environment variable in your Watchtower execution environment.

If the `MAL_CLIENT_ID` is not set, the ETL script will log an error and fail to run.

## 7. Pydantic Model

The raw data fetched from the API is validated and parsed into the `AnimeItem` Pydantic model. This model defines the structure and data types for each anime entry.

*   **Model Location:** `src/models/anime.py`

## 8. Execution

### Standalone Execution

To run this ETL script individually:

```bash
python src/etl/anime/mal_etl.py
```

Ensure the `MAL_CLIENT_ID` environment variable is set before execution.

### Integrated Execution

This ETL is also part of the main ETL runner scripts, which execute multiple ETL processes:

*   `run_all_etl.sh`
*   `run_all_etl.bat`
*   `run_all_etl_powershell.ps1`

Running these scripts will include the execution of the Anime Calendar & Guide ETL.

## 9. Notes

*   The API has rate limits. While the script includes small delays, frequent standalone executions might lead to temporary blocks.
*   The `fields` parameter in the API calls is used to specify the desired data points, optimizing the data fetched.
*   Error handling is implemented to manage API request issues or data parsing problems.

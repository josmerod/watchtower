# YouTube Videos Dashboard

A Streamlit application that visualizes YouTube video data from a JSON file, providing filtering by channel, sort options, and basic analytics.

## Features

- Filter videos by channel
- Date range selection
- Sort by views, publish date, or video duration
- Interactive charts showing video distribution by channel
- Expandable video descriptions
- Download filtered data as CSV

## Setup and Running

1. Ensure you have Python 3.7+ installed

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure the data file exists at `data/youtube/youtube_videos.json`

4. Run the application:
   ```
   cd /path/to/project/root
   streamlit run src/web/demo/youtube/app.py
   ```

## Data Structure

The application expects a JSON file with the following structure:
```json
[
  {
    "title": "Video Title",
    "url": "https://www.youtube.com/watch?v=videoId",
    "channel": "Channel Name",
    "published_at": "YYYY-MM-DDTHH:MM:SSZ",
    "description": "Video description",
    "views": 1234,
    "length": 300.0,
    "metadata": {
      "api_source": "youtube_data_api",
      "processed_at": "YYYY-MM-DDTHH:MM:SS.SSSSSS"
    }
  },
  ...
]
``` 
# Watchtower Legacy Streamlit Dashboard

This is the **legacy** interactive web dashboard for the Watchtower project, built with Streamlit. 

**⚠️ IMPORTANT**: This is now the **legacy dashboard**. The main Watchtower dashboard is now a Dash-based application located at `src/web/new_dashboard_poc/` and accessible at `http://localhost:7777`.

This legacy dashboard provides real-time visualization of data from various modules, including game deals, news, courses, and custom watchers.

## Features

- Multiple tabs for:
  - Shortcuts
  - Videos
  - News
  - Games
  - Courses
  - Watchers
  - Events
  - Admin
- Interactive data tables and charts
- Refreshable data with caching for performance
- Customizable layout and styling

## Requirements

- Python 3.10+
- UV (recommended) or traditional Python environment
- Dependencies as listed in the root `pyproject.toml`

## Setup & Installation

1. Navigate to the project root:
   ```bash
   cd watchtower
   ```
2. Ensure dependencies are installed:
   ```bash
   # With UV (recommended)
   uv sync --all-extras
   
   # Or traditional method
   pip install -r requirements.txt
   ```
3. Install Playwright 
   ```bash
   # With UV (recommended)
   uv run playwright install
   
   # Or traditional method
   playwright install
   ```

## Running the Legacy Dashboard

### Local Development

```bash
# With UV (recommended)
uv run streamlit run src/web/fullstreamlit/app.py

# Or using convenience scripts
# Unix
bash run_streamlit.sh
# Windows
.\run_watchtower.bat
```

Navigate to http://localhost:8501 to view the legacy dashboard.

**Note**: For the main dashboard, use `run_watchtower_dashboard.py` which runs at http://localhost:7777.

### Configuration

- Modify `src/web/fullstreamlit/app.py` to change layout, tabs, or data paths.
- Update CSS styles in `src/web/fullstreamlit/styles/main.py`.

## Project Structure

```
fullstreamlit/
├── app.py               # Main Streamlit application
├── components/          # Individual tab components
├── data/                # Sample or cached data files
├── styles/              # CSS and styling utilities
└── utils/               # Helper functions for data loading and formatting
```

## Contributing

Feel free to add new tabs, custom components, or improve styling. Please follow project conventions and submit a pull request.

## License

This project uses the MIT License. See the root [LICENSE](../../LICENSE) file for details.

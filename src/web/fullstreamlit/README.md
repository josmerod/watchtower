# Watchtower Streamlit Dashboard

This is the interactive web dashboard for the Watchtower project, built with Streamlit. It provides real-time visualization of data from various modules, including game deals, news, courses, and custom watchers.

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
- Dependencies as listed in the root `requirements.txt`

## Setup & Installation

1. Navigate to the project root:
   ```bash
   cd watchtower
   ```
2. Ensure dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright 
   ```bash
   install_playwright.bat  # Windows
   bash install_playwright.sh  # Unix
   ```

## Running the Dashboard

### Local Development

```bash
# Unix
bash run_streamlit.sh
# Windows
.\run_streamlit.bat
```

Navigate to http://localhost:8501 to view the dashboard.

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

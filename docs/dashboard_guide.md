# Watchtower Dashboard: Exploration and Contribution Guide

Welcome to the Watchtower Dashboard guide! This document provides an overview of the dashboard's capabilities, how to navigate its features, and how you can contribute to its development and improvement.

The dashboard is a key component of the Watchtower project, offering a user-friendly web interface built with Streamlit to visualize, explore, and interact with the data collected and processed by the various ETL pipelines and watchers.

For general project information, setup, and overall contribution guidelines, please refer to the main [README.md](../README.md).

## Table of Contents

- [Watchtower Dashboard: Exploration and Contribution Guide](#watchtower-dashboard-exploration-and-contribution-guide)
  - [Table of Contents](#table-of-contents)
  - [Accessing the Dashboard](#accessing-the-dashboard)
  - [Dashboard Overview \& Navigation](#dashboard-overview--navigation)
  - [Key Features \& Sections](#key-features--sections)
    - [Home / Overview Page](#home--overview-page)
    - [Shortcuts](#shortcuts)
    - [Videos](#videos)
    - [News Feeds](#news-feeds)
    - [Game Deals](#game-deals)
    - [Online Courses](#online-courses)
    - [Watchers Status](#watchers-status)
    - [Admin Panel](#admin-panel)
  - [Contributing to the Dashboard](#contributing-to-the-dashboard)
    - [Prerequisites](#prerequisites)
    - [Understanding the Dashboard's Code Structure](#understanding-the-dashboards-code-structure)
    - [Common Types of Contributions](#common-types-of-contributions)
    - [Development Workflow](#development-workflow)
    - [Tips for Streamlit Development](#tips-for-streamlit-development)
    - [Submitting Your Changes](#submitting-your-changes)
  - [Getting Help](#getting-help)

## Accessing the Dashboard

To run the Watchtower dashboard locally:

1.  Ensure you have followed the project [Installation instructions](../README.md#installation) in the main `README.md` and have UV installed (recommended).
2.  Navigate to the project root directory in your terminal.
3.  Run the appropriate script:

### Main Dashboard (Recommended)
-   **Windows**: `.\run_watchtower_dashboard.bat`
-   **macOS/Linux**: `bash run_watchtower_dashboard.sh`
-   **Direct UV command**: `uv run python run_watchtower_dashboard.py`

This will start the main Watchtower Dashboard and open it in your default web browser. The default URL is `http://localhost:7777`.

### Legacy Dashboard (If Needed)
-   **Windows**: `.\run_watchtower.bat`
-   **macOS/Linux**: `bash run_streamlit.sh`
-   **Direct UV command**: `uv run streamlit run src/web/fullstreamlit/app.py`

This will start the legacy Streamlit dashboard at `http://localhost:8501`.

## Dashboard Overview & Navigation

The Watchtower dashboard is designed to be intuitive. Upon launching, you'll typically see:

-   **Sidebar:** On the left, a navigation sidebar allows you to switch between different sections or pages of the dashboard.
-   **Main Content Area:** The central part of the screen displays the content for the currently selected section.

Each section is dedicated to a specific category of data or functionality.

## Key Features & Sections

The dashboard is organized into several key sections, each providing unique insights and interactive capabilities. The exact sections may evolve, but here are some common ones you might find:

### Home / Overview Page
*(If present)*
-   **Purpose:** Provides a general welcome, summary statistics, or quick links to other important sections.
-   **Data:** Might show high-level metrics like total items tracked, recent updates, or system status.
-   **Interactivity:** Could include date range selectors for summaries or links.

### Shortcuts
-   **Purpose:** Displays a curated list of useful links, tools, or resources, often categorized for easy access.
-   **Data:** URLs, descriptions, tags/categories.
-   **Interactivity:** Searchable, filterable by category, direct links to resources.

### Videos
-   **Purpose:** Aggregates videos from monitored YouTube channels or other video sources.
-   **Data:** Video titles, channel names, publication dates, thumbnails, links to videos.
-   **Interactivity:** Search by title or channel, filter by date, sort by recency or popularity, embedded video players (if implemented).

### News Feeds
-   **Purpose:** Presents articles and updates from various news sources (e.g., Hacker News, Bensbites, Future Tools, arXiv papers).
-   **Data:** Article titles, source, publication date, snippets/summaries, links to full articles.
-   **Interactivity:** Filter by news source, search by keywords, sort by date, pagination for large feeds.

### Game Deals
-   **Purpose:** Shows current game deals, bundles, and free offerings from various gaming sites.
-   **Data:** Game titles, original price, sale price, discount percentage, store, platform, deal expiry (if available).
-   **Interactivity:** Filter by store or platform, sort by discount or price, search for specific games.

### Online Courses
-   **Purpose:** Tracks online courses, specializations, or new content from e-learning platforms (e.g., Coursera, DeepLearning.AI).
-   **Data:** Course titles, providers, descriptions, enrollment links, new module announcements.
-   **Interactivity:** Filter by platform or topic, search for courses, direct links to course pages.

### ⛩️ Anime Calendar & Guide Tab
-   **Purpose:** Provides a curated view of anime, including currently airing shows, popular series, and top-rated titles.
-   **Data Source:** Data is sourced from MyAnimeList (MAL) via a dedicated ETL process.
-   **Features:**
    -   **Current Season:** Displays anime currently airing in the ongoing season (Winter, Spring, Summer, Fall).
    -   **Top Popular:** Showcases anime series that are most popular among users.
    -   **Top Rated:** Lists anime series with the highest user scores.
    -   For each anime, details typically include:
        -   Title and cover image.
        -   Average score, overall rank, and popularity rank.
        -   Number of episodes, media type (TV, Movie, OVA), and airing status.
        -   Synopsis, genres, and animation studios.
-   **Updates:** The data for this tab is updated when the main ETL processes (e.g., `run_all_etl.sh`) are executed.

### Watchers Status
-   **Purpose:** Provides an overview of the status of different content watchers.
-   **Data:** Watcher names, last run time, status (e.g., success, failed, changed, unchanged), links to detected changes or logs.
-   **Interactivity:** Filter by watcher status, view logs for a specific watcher, manually trigger a watcher (if implemented).

### Admin Panel
*(If present and accessible based on user roles)*
-   **Purpose:** Offers administrative functionalities like managing configurations, viewing detailed logs, or controlling system processes.
-   **Data:** System logs, configuration parameters, user lists (if multi-user).
-   **Interactivity:** Modifying settings, restarting services, clearing caches.

## Contributing to the Dashboard

Contributions to enhance the dashboard are highly welcome! Whether it's a new feature, a UI improvement, or a bug fix, your help is appreciated.

### Prerequisites

-   **Python:** Strong understanding of Python programming.
-   **Streamlit:** Familiarity with the Streamlit library and its components is essential. Refer to the [Streamlit Documentation](https://docs.streamlit.io/).
-   **Project Setup:** Ensure you have the Watchtower project cloned and your development environment set up as per the main [README.md](../README.md#installation).
-   **Git & GitHub:** Basic knowledge of Git for version control and GitHub for pull requests.

### Understanding the Dashboard's Code Structure

The source code for the Streamlit dashboard is located primarily within the `src/web/fullstreamlit/` directory:

-   `app.py`: This is often the main entry point for the Streamlit application. It might define the overall page structure, navigation, and load initial configurations.
-   `pages/` (if it exists or as a convention): For multi-page Streamlit applications, each `.py` file in this directory typically represents a separate page accessible from the sidebar.
-   `components/`: Contains reusable UI components (custom Streamlit elements or combinations) used across different pages of the dashboard.
-   `utils/`: Holds utility functions specific to the dashboard, such as data loading/processing functions tailored for display, formatting helpers, etc.
-   `styles/`: May contain CSS files if custom styling is applied beyond Streamlit's defaults.
-   `data/`: This sub-directory (or a path defined in config) might be where the dashboard loads its data from, or where cached data is stored. Data is typically sourced from the main `data/` directory of the project.

### Common Types of Contributions

-   **Adding New Pages/Sections:** Introduce a new page to visualize a new data source or provide new functionality.
-   **Improving Existing Pages:** Enhance the UI/UX of current pages, add more interactive elements (e.g., new filters, charts), or improve information density.
-   **New Visualizations:** Integrate new types of charts or visual representations for the data.
-   **Performance Optimization:** Improve the loading speed of pages or responsiveness of interactive components (e.g., by optimizing data handling or using Streamlit's caching more effectively).
-   **Bug Fixes:** Address any reported issues or bugs in the dashboard's functionality or display.
-   **Styling Enhancements:** Improve the visual appeal or consistency of the dashboard.
-   **Backend Logic for UI:** Refactor or improve the Python code that prepares and serves data to the UI components.

### Development Workflow

1.  **Create a Feature Branch:** Before starting your work, create a new branch from the latest `main` or `develop` branch:
    ```bash
    git checkout -b feature/dashboard-my-new-feature
    ```
2.  **Make Your Changes:** Implement your feature or fix in the relevant files within `src/web/fullstreamlit/`.
3.  **Test Locally:** Regularly run the dashboard locally (`.\run_streamlit.bat` or `bash run_streamlit.sh`) to see your changes in action and test all affected functionality.
4.  **Follow Code Standards:**
    *   Adhere to the project's [Development Standards](../README.md#development-standards).
    *   Use **Ruff** for linting and formatting your Python code:
        ```bash
        ruff format .
        ruff check . --fix
        ```
    *   Write clear, **Google-style docstrings** for any new functions or classes.
    *   Use **comprehensive type hints**.
5.  **Testing (if applicable):** While end-to-end UI testing for Streamlit can be complex, any backend logic (e.g., utility functions in `src/web/fullstreamlit/utils/`) should be unit-tested if possible, placing tests in the main `tests/` directory.

### Tips for Streamlit Development

-   **Leverage Streamlit's Caching:** Use `st.cache_data` for functions that return data (like dataframes from files or databases) and `st.cache_resource` for global resources (like ML models or database connections) to improve performance.
-   **Modular Design:** Break down complex pages into smaller, manageable functions or custom components.
-   **Session State:** Use `st.session_state` to store variables across user interactions or reruns.
-   **Layout Options:** Explore Streamlit's layout options like `st.columns`, `st.tabs`, and `st.expander` to organize content effectively.
-   **Consult the Docs:** The official [Streamlit Documentation](https://docs.streamlit.io/) is an excellent resource for components, API references, and best practices.

### Submitting Your Changes

Once you're happy with your changes and have tested them thoroughly:

1.  **Commit Your Changes:** Use clear, descriptive commit messages, following the [Conventional Commits](https://www.conventionalcommits.org/) standard.
    ```bash
    git add .
    git commit -m "feat(dashboard): Add interactive chart to news analysis page"
    ```
2.  **Push to Your Fork:**
    ```bash
    git push origin feature/dashboard-my-new-feature
    ```
3.  **Open a Pull Request (PR):** Go to the GitHub repository of the Watchtower project and open a PR from your feature branch to the main development branch.
    *   Provide a clear title and a detailed description of your changes.
    *   Reference any related issues.
    *   Ensure all automated checks (CI/CD) pass.

Your PR will then be reviewed by the project maintainers.

## Getting Help

If you have questions about contributing to the dashboard, encounter issues, or want to discuss potential improvements:

-   Check the project's **GitHub Issues** page: [Link to Project Issues](../README.md#contact) (Update this link in `README.md` if it's a placeholder).
-   You can open a new issue to ask questions or propose changes.

Thank you for your interest in improving the Watchtower Dashboard! 
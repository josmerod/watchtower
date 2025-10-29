# Proposed New ETL Sources for Watchtower (Spain)

This document outlines a list of potential new Spanish-specific data sources for the Watchtower project's ETL pipelines. The suggestions are categorized and include the recommended method for data extraction.

## I. Government and Public Data

### 1. Datos.gob.es
- **Source**: [datos.gob.es](https://datos.gob.es/es)
- **Data**: A central catalogue of open data from all Spanish public administrations. Datasets cover a wide range of topics, including:
    - Demographics and social statistics
    - Economy and finance
    - Environment and weather
    - Transportation and infrastructure
    - Health and public services
- **Extraction Method**: The portal is a catalogue, so the extraction method will vary for each dataset. Many datasets are available as downloadable files (CSV, XML, JSON), while others may have their own APIs. Each dataset will need to be evaluated on a case-by-case basis.

## II. News and Media

### 1. El País
- **Source**: [elpais.com](https://elpais.com/)
- **Data**: News articles, opinion pieces, and multimedia content from one of Spain's leading newspapers.
- **Extraction Method**: RSS feeds. The newspaper provides a comprehensive list of feeds, categorized by section and region. This is the most reliable and efficient way to ingest their content.

### 2. El Mundo
- **Source**: [elmundo.es](https://www.elmundo.es/)
- **Data**: News articles, investigative journalism, and opinion pieces from another of Spain's top newspapers.
- **Extraction Method**: RSS feeds. Similar to El País, El Mundo offers a variety of RSS feeds for its different sections.

### 3. Other National and Regional Newspapers
- **Source**: A variety of other newspapers, such as ABC, La Vanguardia, and regional papers identified in the [Wikipedia list](https://en.wikipedia.org/wiki/List_of_newspapers_in_Spain).
- **Data**: News and analysis with a national or regional focus.
- **Extraction Method**: Most newspapers provide RSS feeds. For those that don't, web scraping would be the alternative.

## III. Job Market

### 1. Infojobs
- **Source**: [infojobs.net](https://www.infojobs.net/)
- **Data**: Job postings, company information, and salary data.
- **Extraction Method**: A well-documented RESTful API. This is the ideal way to access their data, as it's structured, reliable, and officially supported.

### 2. LinkedIn
- **Source**: [linkedin.com](https://www.linkedin.com/jobs/)
- **Data**: Job postings, professional profiles, and company information.
- **Extraction Method**: LinkedIn has a public API, but access to the job-related endpoints may be restricted. If direct API access is not possible, web scraping would be the alternative, though it can be challenging due to the site's structure and authentication requirements.

### 3. Indeed
- **Source**: [es.indeed.com](https://es.indeed.com/)
- **Data**: A large aggregator of job postings from various sources.
- **Extraction Method**: Indeed has an API for publishers, but it may not be suitable for all use cases. Web scraping is a common method for extracting data from Indeed, but it requires careful handling of the site's structure and potential anti-scraping measures.

## IV. Real Estate

### 1. Idealista
- **Source**: [idealista.com](https://www.idealista.com/)
- **Data**: Real estate listings for sale and rent, property characteristics, and price data.
- **Extraction Method**: Idealista has a private Search API, but it requires an access request. This is the preferred method, but it may not be immediately available. Web scraping is the alternative, but it would need to be carefully designed to handle the site's dynamic content and potential anti-scraping measures.

### 2. Fotocasa
- **Source**: [fotocasa.es](https://www.fotocasa.es/)
- **Data**: Real estate listings, similar to Idealista.
- **Extraction Method**: Fotocasa does not appear to have a public API. Web scraping would be the primary method for data extraction.

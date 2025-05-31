# Metadata

- Caso de uso: Home Server Trends & Applications Discovery
- Plataformas involucradas: GitHub (awesome-selfhosted list)
- Descripción corta: Proceso ETL para extraer aplicaciones y tendencias relevantes para servidores domésticos desde la lista 'awesome-selfhosted' y mostrarlas en el dashboard.
- Patrón de ejecución: Programado (como parte de `run_all_etl.sh`)

## Dependencias

- Fuente de datos principal: [awesome-selfhosted GitHub Repository](https://github.com/awesome-selfhosted/awesome-selfhosted) (específicamente el archivo `README.md`).
- Bibliotecas de Python principales:
  - `requests` (para fetching HTTP)
  - `json` (para manejo de JSON)
  - `csv` (para manejo de CSV)
  - `re` (para parsing de Markdown)
  - `hashlib` (para generar IDs)
  - `pydantic` (para validación del modelo de datos)

## Stack Tecnológico

- Lenguaje de programación: Python
- Framework: N/A (script standalone)
- Almacenamiento de datos: Archivos JSON y CSV en el directorio `data/home_server_trends/`.
- Visualización: Streamlit (a través del componente `home_server_tab.py` en el dashboard principal).
- Orquestación: Script Bash (`run_all_etl.sh`).

## Implementación

La implementación consta de los siguientes componentes:

1.  **Proceso ETL** (`src/etl/news/news_get_home_server_trends.py`):
    - **Funcionalidad Principal:** Este script obtiene el archivo `README.md` del repositorio `awesome-selfhosted/awesome-selfhosted`. Procesa el contenido Markdown para extraer información sobre aplicaciones autoalojables, centrándose en categorías predefinidas de interés para usuarios de servidores domésticos.
    - **Pasos clave del proceso:**
        - `fetch_awesome_selfhosted_readme`: Obtiene el contenido del `README.md`.
        - `parse_markdown`: Analiza el Markdown utilizando expresiones regulares para identificar categorías y extraer detalles de las aplicaciones listadas (nombre, URL, descripción, tags).
        - `process_items`: Convierte los datos extraídos al modelo de datos `HomeServerTrendItem`.
        - `save_data`: Guarda los datos procesados en archivos JSON y CSV en `data/home_server_trends/`, incluyendo un archivo `_latest` para consumo del dashboard.
    - **Modelo de Datos:** Se utiliza el modelo Pydantic `HomeServerTrendItem` (definido en `src/models/home_server.py`) que incluye campos como `id`, `name`, `description`, `url`, `category`, `source`, `tags`, y `added_date`.

2.  **Componente de Dashboard** (`src/web/fullstreamlit/components/home_server_tab.py`):
    - **Funcionalidad Principal:** Muestra los datos de tendencias de servidores domésticos en una nueva pestaña del dashboard de Streamlit.
    - **Características principales:**
        - Carga datos desde `data/home_server_trends/home_server_trends_latest.json` utilizando el `data_service`.
        - Permite filtrar los elementos por categoría.
        - Muestra cada elemento en un expander con su nombre, descripción, URL, y tags (si están disponibles).

## Salida de Datos

- Los datos procesados se almacenan en:
    - `data/home_server_trends/home_server_trends_latest.json`
    - `data/home_server_trends/home_server_trends_latest.csv`
    - Archivos JSON y CSV versionados con timestamp en el mismo directorio.

## Consideraciones Adicionales

- El parsing de Markdown mediante expresiones regulares puede necesitar ajustes si la estructura del `README.md` de `awesome-selfhosted` cambia significativamente.
- Las categorías de interés se definen actualmente en una lista estática dentro del script ETL. Esto podría externalizarse a un archivo de configuración si se requiere mayor flexibilidad.

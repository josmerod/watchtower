# Metadata

- Caso de uso: Home Server Trends & Applications Discovery
- Plataformas involucradas: GitHub (awesome-selfhosted list, other 'awesome list' style repositories e.g., for Home Automation)
- Descripción corta: Proceso ETL para extraer aplicaciones y tendencias relevantes para servidores domésticos desde la lista 'awesome-selfhosted' y mostrarlas en el dashboard.
- Patrón de ejecución: Programado (como parte de `run_all_etl.sh`)

## Dependencias

- Fuentes de datos principales:
  - [awesome-selfhosted GitHub Repository](https://github.com/awesome-selfhosted/awesome-selfhosted)
  - Otros repositorios de GitHub estilo "awesome list" (ej. listas dedicadas a Home Automation). El script está diseñado para ser adaptable a múltiples fuentes de Markdown con estructura similar.
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
    - **Funcionalidad Principal:** Este script obtiene archivos `README.md` de múltiples repositorios configurados (actualmente `awesome-selfhosted` y una lista representativa de `awesome-home-automation`). Procesa el contenido Markdown de cada fuente para extraer información sobre aplicaciones autoalojables, centrándose en categorías predefinidas de interés para cada fuente. Los datos de todas las fuentes se combinan y se de-duplican antes de guardarlos.
    - **Pasos clave del proceso:**
        - `fetch_markdown_content`: Obtiene el contenido Markdown desde una URL dada.
        - `parse_markdown`: Analiza el Markdown (de cualquier fuente configurada) utilizando expresiones regulares y una lista de categorías objetivo para esa fuente, para identificar y extraer detalles de las aplicaciones (nombre, URL, descripción, tags). Atribuye un nombre de fuente a cada item.
        - `De-duplicación`: Antes del procesamiento final, los elementos recolectados de todas las fuentes son de-duplicados basados en un ID único (hash de nombre+URL) para evitar entradas repetidas en el conjunto de datos final.
        - `process_items`: Convierte los datos extraídos al modelo de datos `HomeServerTrendItem`.
        - `save_data`: Guarda los datos combinados y de-duplicados en archivos JSON y CSV en `data/home_server_trends/`, incluyendo un archivo `_latest` para consumo del dashboard.
    - **Modelo de Datos:** Se utiliza el modelo Pydantic `HomeServerTrendItem` (definido en `src/models/home_server.py`) que incluye campos como `id`, `name`, `description`, `url`, `category`, `source` (que ahora indica la lista de origen, ej. 'awesome-selfhosted' o 'awesome-home-automation'), `tags`, y `added_date`.

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

- El parsing de Markdown mediante expresiones regulares puede necesitar ajustes si la estructura del `README.md` de `awesome-selfhosted` (o cualquier otra fuente) cambia significativamente.
- Las categorías de interés para cada fuente se definen actualmente en listas estáticas dentro del script ETL. Esto podría externalizarse a un archivo de configuración si se requiere mayor flexibilidad.
- La correcta extracción de datos de nuevas fuentes depende de la disponibilidad de URLs válidas y de la definición precisa de sus categorías de interés en el script ETL.
- El script ahora está estructurado para manejar múltiples fuentes, pero la lógica de parsing de Markdown podría necesitar ajustes específicos si la estructura de una nueva fuente difiere considerablemente de las actuales.

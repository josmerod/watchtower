# ADHD Research Papers and Resources ETL

- **Caso de uso**: Extracción y visualización de trabajos de investigación sobre TDAH (Trastorno por Déficit de Atención e Hiperactividad).
- **Plataformas involucradas**: PubMed, Streamlit.
- **Descripción corta**: Este caso de uso implementa un proceso ETL para extraer datos de publicaciones sobre TDAH desde PubMed y los presenta en una pestaña dedicada dentro de la aplicación Streamlit para su consulta y búsqueda.
- **Patrón de ejecución**: Puntual (puede ser programado para actualizaciones periódicas).

## Dependencias

- **APIs/Servicios Externos**:
    - PubMed E-utilities API (para búsqueda y obtención de detalles de artículos).
- **Bibliotecas de Python Principales**:
    - `requests` (para realizar peticiones HTTP a la API de PubMed).
    - `xml.etree.ElementTree` (para parsear las respuestas XML de PubMed).
    - `pandas` (para la manipulación de datos y guardado en CSV).
    - `pydantic` (para la validación y estructuración de datos - modelo `ADHDPublication`).
    - `streamlit` (para la creación del componente de visualización).

## Stack Tecnológico

- **Lenguaje de programación**: Python
- **Framework**: Streamlit (para la interfaz de usuario).
- **Almacenamiento de datos**: Archivos JSON y CSV en el sistema de ficheros local.
- **Visualización**: Streamlit.
- **Orquestación**: N/A (ejecución manual o mediante scripts programados por el sistema operativo).
- **Logging**: Utiliza el logger configurado en `BaseETL` y la aplicación Streamlit.

## Implementación

La implementación consta de los siguientes componentes:

1.  **Proceso ETL** (`src/etl/adhd/adhd_publications_etl.py`):
    *   **Fuente**: PubMed (base de datos de literatura biomédica).
    *   **Extracción**:
        *   Utiliza las E-utilities de PubMed (`esearch` y `efetch`).
        *   Busca artículos utilizando términos como "ADHD", "Attention Deficit Hyperactivity Disorder".
        *   Recupera una lista de PMIDs (PubMed IDs) y luego los detalles completos de cada artículo.
    *   **Transformación**:
        *   Parsea los datos XML recibidos de PubMed.
        *   Extrae campos clave: título, autores, resumen (abstract), fecha de publicación, DOI (Digital Object Identifier) y URL de PubMed.
        *   Estructura los datos utilizando el modelo Pydantic `ADHDPublication` (`src/models/adhd.py`).
    *   **Carga (Output)**:
        *   Guarda la lista de artículos procesados en formato JSON y CSV.
        *   Los archivos se guardan como `latest_papers.json` y `latest_papers.csv` en los subdirectorios `json/` y `csv/` dentro de `data/adhd_publications/output/`. También se guardan versiones con timestamp.

2.  **Componente Streamlit** (`src/web/fullstreamlit/components/adhd_tab.py`):
    *   **Nombre de la Pestaña**: "ADHD Research".
    *   **Funcionalidad**:
        *   Muestra una lista de los trabajos de investigación sobre TDAH recuperados por el proceso ETL.
        *   Cada trabajo se presenta en una tarjeta expandible con su título, autores, fecha, DOI, enlace al artículo y resumen.
        *   Permite a los usuarios buscar dentro de los títulos y resúmenes de los artículos mostrados.
    *   **Fuente de Datos**: Lee el archivo `latest_papers.json` (o CSV) generado por el proceso ETL.

## Cómo Ejecutar el ETL

El proceso ETL puede ser ejecutado directamente desde la línea de comandos:

```bash
python src/etl/adhd/adhd_publications_etl.py
```
Esto poblará o actualizará los archivos de datos en `data/adhd_publications/output/`.

## Archivos Clave

-   `src/etl/adhd/adhd_publications_etl.py`: Contiene la lógica principal del ETL para PubMed.
-   `src/models/adhd.py`: Define el modelo Pydantic `ADHDPublication` para los datos de los artículos.
-   `src/web/fullstreamlit/components/adhd_tab.py`: Implementa la pestaña y la visualización en Streamlit.
-   `data/adhd_publications/output/`: Directorio donde se almacenan los datos procesados (archivos JSON y CSV).

## Posibles Mejoras Futuras

-   **Ampliación de Fuentes**: Integrar otras fuentes de datos como Google Scholar, Semantic Scholar o revistas científicas específicas.
-   **Procesamiento NLP Avanzado**:
    *   Resumen automático de los abstracts.
    *   Análisis de tendencias temáticas dentro de la investigación sobre TDAH.
    *   Clasificación de artículos por subtemas específicos.
-   **Funcionalidades de Usuario**:
    *   Cuentas de usuario para guardar artículos favoritos o establecer preferencias de búsqueda.
    *   Sistema de notificaciones para nuevos artículos relevantes.
-   **Filtros Sofisticados**:
    *   Filtrar por tipo de estudio, metodología, factor de impacto de la revista (si se puede obtener).
    *   Filtrar por autores específicos o instituciones.
-   **Visualizaciones de Datos**: Gráficos sobre la evolución temporal de las publicaciones, nubes de palabras clave, etc.

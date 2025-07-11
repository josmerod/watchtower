---
Caso de uso: New Game Releases Watcher / Observador de Nuevos Lanzamientos de Videojuegos
Plataformas involucradas: RAWG.io API, Streamlit Dashboard
Descripción corta: ETL para obtener información sobre lanzamientos recientes y futuros de videojuegos filtrados por calidad (Metacritic score) y su visualización en el dashboard.
Patrón de ejecución: Periódico (e.g., cada 12-24 horas)
---

## Dependencias

*   **Fuentes de datos externas**:
    *   RAWG API: `https://api.rawg.io/api/games`
*   **Bibliotecas de Python principales**:
    *   `requests` (para interactuar con la API de RAWG)
    *   `pandas` (para procesamiento de datos)
    *   `streamlit` (para la visualización en el dashboard)

## Stack Tecnológico

*   **Lenguaje de programación**: Python 3.10+
*   **Framework**:
    *   Consumo de API para ETL.
    *   Streamlit para la interfaz de usuario y visualización.
*   **Almacenamiento de datos**:
    *   JSON: `new_releases.json` (para datos estructurados flexibles)
    *   CSV: `new_releases.csv` (para compatibilidad y análisis tabulares)

## Implementación

### Script ETL (`src/etl/games/games_get_new_releases.py`)

El script ETL está diseñado para automatizar la recolección de información sobre videojuegos de próximo lanzamiento o recientemente lanzados. Los pasos principales son:

1.  **Conexión a la API de RAWG**: Utiliza una clave de API para autenticarse.
2.  **Filtrado por Fecha**: Obtiene juegos lanzados en los últimos `30` días y aquellos programados para los próximos `90` días.
3.  **Filtrado por Calidad**: Selecciona juegos que tengan una puntuación Metacritic igual o superior a `70`.
4.  **Extracción de Datos**: Recopila información relevante como:
    *   ID del juego en RAWG
    *   Título (nombre)
    *   Fecha de lanzamiento
    *   Plataformas (PC, PlayStation, Xbox, Nintendo Switch, etc.)
    *   Géneros
    *   Puntuación Metacritic
    *   Descripción breve (raw)
    *   Enlace directo a la página del juego en RAWG.io
5.  **Almacenamiento**: Guarda los datos procesados en formatos JSON y CSV en el directorio `data/games/`.

### Integración en el Dashboard

La información recolectada se integra en el dashboard de Streamlit para fácil acceso y visualización:

*   **Ubicación**: Se añade una nueva pestaña "Nuevos Lanzamientos" dentro de la sección principal "Juegos".
*   **Componente de Visualización** (`src/web/fullstreamlit/components/new_releases_tab.py`):
    *   Muestra cada juego en un formato expandible (`st.expander`).
    *   Dentro de cada expansor, se detallan el título, fecha de lanzamiento, plataformas, puntuación Metacritic, una descripción y un enlace directo a RAWG.io para más detalles.
*   **Servicio de Datos** (`src/web/fullstreamlit/utils/data_service_ultra_optimized.py`): Se actualiza para cargar los datos desde `new_releases.json`.
*   **Aplicación Principal** (`src/web/fullstreamlit/app.py`): Se modifica para pasar los datos al nuevo componente de la pestaña.

## Características Principales

*   **Curación de Lanzamientos**: Filtra automáticamente los juegos por puntuación Metacritic, presentando solo aquellos con una recepción crítica favorable.
*   **Vista Unificada**: Ofrece una perspectiva combinada de juegos que acaban de salir al mercado y aquellos que están por llegar, facilitando el seguimiento de novedades.
*   **Acceso Directo a Detalles**: Proporciona enlaces directos a RAWG.io para cada juego, permitiendo a los usuarios explorar más a fondo (reseñas completas, imágenes, videos, etc.).
*   **Actualización Periódica**: Diseñado para ejecutarse regularmente, asegurando que la información esté siempre actualizada.

## Outputs Generados

*   **Archivo JSON**: `data/games/new_releases.json`
*   **Archivo CSV**: `data/games/new_releases.csv`
*   **Visualización en Dashboard**: Interfaz interactiva en la pestaña "Juegos" -> "Nuevos Lanzamientos".

## Configuración (API Key)

Para que el script ETL funcione correctamente, es necesario configurar la clave de API de RAWG. Esto se realiza estableciendo la variable de entorno `RAWG_API_KEY` con la clave personal obtenida de [RAWG.io](https://rawg.io/apikey).

Ejemplo: `export RAWG_API_KEY="TU_API_KEY_AQUI"`

El script tiene un valor placeholder (`"YOUR_RAWG_API_KEY"`) y emitirá una advertencia si la clave real no está configurada.

## Uso en el Dashboard

Los usuarios pueden encontrar la información sobre nuevos lanzamientos de videojuegos accediendo a la sección "Juegos" en la barra de pestañas principal del dashboard y luego seleccionando la sub-pestaña "Nuevos Lanzamientos". Cada juego se muestra en una tarjeta expandible con sus detalles más importantes.

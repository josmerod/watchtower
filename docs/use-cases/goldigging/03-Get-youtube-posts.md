# Metadata

- Caso de uso: Extraer los últimos videos de una serie de canales de Youtube
- Plataformas involucradas: 
    - Youtube (mediante API???)
- Descripción corta: Extraer los últimos videos de una serie de canales de Youtube. Aplicar un filtro para seleccionar los videos que cumplen con ciertas características (edad máxima, incluir/excluir shorts, etc)
- Patrón de ejecución: Periódico (cada 6 horas mediante el orquestador ETL)

## Dependencias

- Bibliotecas de Python principales:
    - google-api-python-client
    - pandas
    - json

## Stack Tecnológico

- Lenguaje de programación: Python
- Framework: 
    - google-api-python-client
- Almacenamiento de datos: 
    - data/goldigging/youtube_posts.json
    - data/goldigging/youtube_posts.csv
- Visualización (demo): Streamlit
- Orquestación: etl_orchestrator.py
- Logging: Sistema centralizado de logging

## Implementación

La implementación consta de los siguientes componentes:

1. **Proceso ETL** (`src/etl/news/news_get_futurenews.py`):
    - Obtener los últimos videos de una serie de canales de Youtube
    - Aplicar un filtro para seleccionar los videos que cumplen con ciertas características (edad máxima, incluir/excluir shorts, etc)
    - Guardar los videos en un archivo JSON y CSV

2. **Orquestador ETL** (`src/orchestrator/etl_orchestrator.py`):
    - Ejecutar el proceso ETL cada 6 horas

3. **Dashboard de Visualización** (`src/web/demo/genai/app.py`):
    - Mostrar los videos en un dashboard de Streamlit sencillo.

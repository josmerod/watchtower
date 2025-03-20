# Metadata

- Caso de uso: Obtener noticias del portal futurenews.io/news
- Plataformas involucradas: 
    - futurenews.io/news (no tiene RSS)
- Descripción corta: Obtener las noticias más recientes del portal futurenews.io/news
- Patrón de ejecución: Periódico (cada 6 horas mediante el orquestador ETL)

## Dependencias

- Listar APIs, servicios externos, o fuentes de datos
- Bibliotecas de Python principales:
  - Listar bibliotecas clave

## Stack Tecnológico

- Lenguaje de programación: Python
- Framework: 
    - requests
- Almacenamiento de datos: 
    - data/genai/futurenews.json
    - data/genai/futurenews.csv
- Visualización (demo): Streamlit
- Orquestación: etl_orchestrator.py
- Logging: Sistema centralizado de logging

## Implementación

La implementación consta de los siguientes componentes:

1. **Proceso ETL** (`src/etl/genai/genai_get_futurenews.py`):
    - Obtener las noticias más recientes del portal futurenews.io/news
    - Guardar las noticias en un archivo JSON y CSV

2. **Orquestador ETL** (`src/orchestrator/etl_orchestrator.py`):
    - Ejecutar el proceso ETL cada 6 horas

3. **Dashboard de Visualización** (`src/web/demo/genai/app.py`):
    - Mostrar las noticias en un dashboard de Streamlit sencillo.


## Pseudocódigo

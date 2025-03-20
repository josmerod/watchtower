# Proceso ETL de Ofertas de juegos, bundles y juegos regalados

- Caso de uso: Obtener los últimos descuentos, bundles y regalos de juegos en PC (principalmente Steam)
- Plataformas involucradas: 
    - Feeds RSS de IsThereAnyDeal
- Descripción corta: De forma periódica, obtener los últimos descuentos, bundles y regalos de juegos en PC y guardarlos en archivos JSON para su visualización a través de un dashboard en Streamlit.
- Patrón de ejecución: Periódico (cada 6 horas mediante el orquestador ETL)

## Dependencias

- Feeds RSS de IsThereAnyDeal
- Sistema de archivos para almacenamiento de datos
- Bibliotecas de Python:
  - feedparser (para análisis de RSS)
  - pandas (para manipulación de datos)
  - tabulate (para salida en consola)
  - streamlit (para dashboard de visualización)
  - plotly (para visualizaciones interactivas)

## Stack Tecnológico

- Lenguaje de programación: Python
- Framework: feedparser para análisis de RSS
- Almacenamiento de datos: Archivos JSON en el directorio `data/games`
- Visualización: Dashboard en Streamlit
- Orquestación: Módulo schedule para programación de tareas
- Logging: Sistema centralizado de logging con rotación de archivos

## Implementación

La implementación consta de tres componentes principales:

1. **Proceso ETL** (`src/etl/games/games_get_deals.py`):
   - Accede a los feeds RSS de IsThereAnyDeal
   - Obtiene descuentos, bundles y regalos de juegos para PC
   - Procesa y transforma los datos
   - Guarda los datos en archivos JSON en el directorio `data/games`

2. **Orquestador ETL** (`src/orchestrator/etl_orchestrator.py`):
   - Asegura que los directorios necesarios existan
   - Programa la ejecución del proceso ETL cada 6 horas
   - Ejecuta el proceso ETL inmediatamente al inicio
   - Proporciona logging detallado de las ejecuciones

3. **Dashboard de Visualización** (`src/web/demo/games/app.py`):
   - Lee los archivos JSON generados por el proceso ETL
   - Implementa caché de datos con tiempo de vida de 1 hora
   - Proporciona un dashboard interactivo con:
     - Resumen de estadísticas de ofertas de juegos
     - Vista detallada de ofertas con opciones de filtrado
     - Exploración de bundles
     - Listado de regalos activos con indicador de estado (activo/expirado)
     - Visualizaciones interactivas con Plotly

## Consideraciones

- El proceso ETL se ejecuta cada 6 horas a través del orquestador, manteniendo los datos relativamente actualizados
- El sistema de logging centralizado registra todas las operaciones en archivos con rotación diaria
- El dashboard implementa caché de datos para mejorar el rendimiento
- Los datos se almacenan localmente en archivos JSON, lo que simplifica la arquitectura pero limita la escalabilidad
- La implementación se centra en datos de IsThereAnyDeal, que principalmente cubre plataformas de juegos para PC
- El sistema está diseñado para funcionar de manera autónoma con mínima intervención manual

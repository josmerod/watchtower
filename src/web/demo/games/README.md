# Panel de Ofertas de Juegos

Un dashboard en Streamlit que visualiza ofertas, bundles y regalos de juegos de IsThereAnyDeal.

## Características

- **Resumen**: Estadísticas generales de todas las ofertas de juegos
- **Ofertas**: Explorar y filtrar ofertas de juegos
- **Bundles**: Explorar paquetes de juegos
- **Regalos**: Encontrar juegos gratuitos activos

## Fuentes de Datos

El dashboard utiliza datos de los siguientes archivos JSON:
- `data/games/deals.json`: Ofertas de juegos con descuentos
- `data/games/bundles.json`: Paquetes de juegos con títulos incluidos
- `data/games/giveaways.json`: Regalos de juegos gratuitos

Estos archivos son generados por el script ETL en `src/etl/games/games_get_deals.py`.

## Instalación

1. Clona este repositorio
2. Instala las dependencias requeridas:

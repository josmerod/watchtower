# Metadata

- Caso de uso: Gaming Deals and Bundle Intelligence System
- Plataformas involucradas: Humble Bundle, Steam, Epic Games Store, GOG, Bundle aggregators
- Descripción corta: Sistema de inteligencia para ofertas y bundles de videojuegos con análisis de valor, precios históricos y detección de ofertas premium
- Patrón de ejecución: Periódico (cada 6-12 horas) con alertas inmediatas para ofertas excepcionales

## Dependencias

- Fuentes de datos externas:
  - Humble Bundle website (web scraping con Playwright)
  - Steam API y web scraping
  - Epic Games Store API
  - GOG API
  - Deal aggregator sites (IsThereAnyDeal, etc.)
- Bibliotecas de Python principales:
  - `playwright`: Automatización de navegador para scraping avanzado
  - `beautifulsoup4`: Parsing HTML y extracción de datos
  - `asyncio`: Procesamiento asíncrono para múltiples fuentes
  - `requests`: Comunicación HTTP con APIs
  - `datetime`: Manejo de fechas y duración de ofertas
  - `re`: Análisis de patrones y extracción de información

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: ETL con web scraping avanzado y anti-detection
- Automatización de navegador: Playwright con configuración stealth
- Almacenamiento de datos: JSON estructurado con historial de precios
- Anti-Detection: Headers rotativos, user agents, cookies management
- Logging: Sistema centralizado con debug screenshots y HTML

## Implementación

La implementación consta de los siguientes componentes:

1. **Humble Bundle Scraper** (`src/etl/games/games_get_humblebundles.py`):
   - Web scraping avanzado con Playwright
   - Detección automática de bundles activos
   - Análisis de valor y descuentos
   - Extracción de metadatos completos de bundles

2. **General Gaming Deals ETL** (`src/etl/games/games_get_deals.py`):
   - Agregación de ofertas de múltiples plataformas
   - Comparación de precios entre tiendas
   - Análisis de historial de precios
   - Detección de ofertas excepcionales

3. **Stealth Web Scraping Engine**:
   - Configuración anti-detección para evitar bloqueos
   - Rotación de user agents y headers
   - Manejo inteligente de cookies y sesiones
   - Screenshots y HTML debug para troubleshooting

4. **Value Analysis Engine**:
   - Cálculo de valor real de bundles
   - Comparación con precios individuales
   - Análisis de calidad de juegos incluidos
   - Scoring de ofertas por valor percibido

## Características Avanzadas

### 1. **Advanced Web Scraping**
- **Playwright Integration**: Navegador real para sitios con JavaScript pesado
- **Anti-Detection Measures**: 
  - User agent rotation
  - Viewport randomization
  - Automation markers removal
  - Cookie persistence
- **Dynamic Content Handling**: Espera inteligente para carga de contenido
- **Error Recovery**: Retry logic con backoff exponencial

### 2. **Bundle Analysis Intelligence**
- **Value Calculation**: Cálculo automático de valor de bundles vs precios individuales
- **Game Quality Assessment**: Análisis de calidad basado en reviews y ratings
- **Historical Price Tracking**: Seguimiento de precios históricos
- **Deal Scoring**: Puntuación de ofertas basada en múltiples factores

### 3. **Multi-Platform Aggregation**
- **Humble Bundle**: Bundles de games, books, y software
- **Steam Deals**: Ofertas diarias y semanales de Steam
- **Epic Games**: Juegos gratuitos semanales y ofertas
- **GOG**: Ofertas DRM-free y juegos clásicos
- **Third-party Aggregators**: Sitios de comparación de precios

### 4. **Real-time Deal Detection**
- **New Bundle Alerts**: Detección inmediata de nuevos bundles
- **Price Drop Notifications**: Alertas por caídas significativas de precios
- **Limited Time Offers**: Tracking de ofertas con tiempo limitado
- **Flash Sale Detection**: Identificación de ofertas relámpago

### 5. **Advanced Data Extraction**
- **JavaScript Evaluation**: Extracción de datos desde variables JavaScript
- **Multiple Selector Strategies**: Múltiples estrategias de selección CSS
- **Fallback Mechanisms**: Métodos alternativos si falla extracción primaria
- **Debug and Monitoring**: Screenshots y HTML saves para debugging

## Pseudocódigo

```python
async def gaming_deals_etl_process():
    # 1. Initialize Stealth Browser Environment
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=get_random_user_agent()
        )
        
        # Anti-detection measures
        await context.add_init_script(stealth_script)
        
        # 2. Multi-Source Data Collection
        all_deals = []
        
        # Humble Bundle scraping
        humble_bundles = await scrape_humble_bundles(context)
        all_deals.extend(humble_bundles)
        
        # Steam deals scraping
        steam_deals = await scrape_steam_deals(context)
        all_deals.extend(steam_deals)
        
        # Epic Games free games
        epic_deals = await scrape_epic_games(context)
        all_deals.extend(epic_deals)
        
        # 3. Deal Analysis and Enrichment
        for deal in all_deals:
            # Value analysis
            deal.value_score = calculate_value_score(deal)
            
            # Historical price comparison
            deal.historical_low = get_historical_low_price(deal)
            deal.price_trend = analyze_price_trend(deal)
            
            # Game quality assessment
            deal.quality_score = assess_game_quality(deal)
            
            # Deal urgency (time remaining)
            deal.urgency_score = calculate_urgency(deal.end_date)
        
        # 4. Deal Scoring and Prioritization
        scored_deals = score_and_prioritize_deals(all_deals)
        
        # 5. Alert Generation
        exceptional_deals = filter_exceptional_deals(scored_deals)
        send_deal_alerts(exceptional_deals)
        
        # 6. Data Storage and Reporting
        save_deals_data(scored_deals)
        generate_deals_report(scored_deals)
        update_price_history(scored_deals)
```

## Bundle Value Analysis

### Value Score Calculation
```python
def calculate_bundle_value_score(bundle):
    individual_prices = sum(game.regular_price for game in bundle.games)
    bundle_price = bundle.current_price
    
    # Base discount percentage
    discount_rate = (individual_prices - bundle_price) / individual_prices
    
    # Quality weighted value
    quality_multiplier = calculate_quality_multiplier(bundle.games)
    
    # Platform preference bonus
    platform_bonus = calculate_platform_bonus(bundle.platforms)
    
    # Time sensitivity factor
    urgency_factor = calculate_urgency_factor(bundle.time_remaining)
    
    value_score = (
        discount_rate * 0.4 +
        quality_multiplier * 0.3 +
        platform_bonus * 0.2 +
        urgency_factor * 0.1
    ) * 100
    
    return min(value_score, 100.0)
```

### Quality Assessment Factors
1. **Metacritic Scores**: Puntuaciones de crítica profesional
2. **Steam Reviews**: Porcentaje de reviews positivas
3. **Popularity Metrics**: Número de propietarios, wishlists
4. **Age and Relevance**: Factores de antigüedad del juego
5. **Genre Preferences**: Preferencias por género de usuario

## Métricas y KPIs

### Métricas de Cobertura
- **Platforms Monitored**: Número de plataformas activamente monitoreadas
- **Deals Discovered**: Ofertas nuevas descubiertas por día
- **Bundle Coverage**: Porcentaje de bundles capturados vs disponibles
- **Update Frequency**: Frecuencia de actualización por plataforma

### Métricas de Calidad
- **Value Score Accuracy**: Precisión en cálculo de valor de ofertas
- **False Positive Rate**: Tasa de alertas de ofertas incorrectas
- **Historical Price Accuracy**: Exactitud de datos de precios históricos
- **Deal Relevance**: Relevancia de ofertas detectadas para usuarios

### Métricas de Performance
- **Scraping Success Rate**: Tasa de éxito en web scraping
- **Page Load Time**: Tiempo promedio de carga de páginas
- **Detection Bypass Rate**: Tasa de éxito evitando detección anti-bot
- **Data Extraction Speed**: Velocidad de extracción de datos

## Casos de Uso Específicos

1. **Gaming Enthusiasts**: Descubrimiento de ofertas y bundles de calidad
2. **Budget Gamers**: Maximización de valor en compras de juegos
3. **Deal Hunters**: Identificación de ofertas excepcionales y limitadas
4. **Gaming Content Creators**: Source de contenido sobre ofertas
5. **Game Collectors**: Tracking de juegos raros en ofertas
6. **Parents**: Ofertas de juegos familiares y educativos

## Anti-Detection Strategies

### Browser Fingerprinting Evasion
- **User Agent Rotation**: Rotación de user agents realistas
- **Viewport Randomization**: Tamaños de ventana variables
- **WebGL Fingerprinting**: Modificación de fingerprints WebGL
- **Canvas Fingerprinting**: Alteración de canvas fingerprints

### Behavioral Mimicking
- **Human-like Timing**: Delays realistas entre acciones
- **Mouse Movement Simulation**: Movimientos de ratón naturales
- **Scroll Behavior**: Patrones de scroll humanos
- **Click Patterns**: Patrones de click naturales

### Session Management
- **Cookie Persistence**: Mantenimiento de cookies entre sesiones
- **Session Rotation**: Rotación periódica de sesiones
- **IP Rotation**: Uso de proxies rotativos (opcional)
- **Request Spacing**: Espaciado inteligente de requests

## Configuración Avanzada

### Scraping Parameters
```python
SCRAPING_CONFIG = {
    "humble_bundle": {
        "delay_range": (3, 8),  # seconds
        "retry_attempts": 3,
        "timeout": 60000,  # milliseconds
        "selectors": [
            "div.tile, div.mosaic-tile",
            "a[href*='/games/'], a[href*='/books/']",
            "article.bundle, div.bundle-info"
        ]
    },
    "steam": {
        "delay_range": (2, 5),
        "retry_attempts": 5,
        "api_key_rotation": True
    }
}
```

### Value Thresholds
```python
VALUE_THRESHOLDS = {
    "exceptional_deal": 85,  # Score above 85 = exceptional
    "good_deal": 70,         # Score 70-85 = good deal
    "average_deal": 50,      # Score 50-70 = average
    "poor_deal": 30          # Score below 30 = poor value
}
```

## Outputs Generados

1. **Deals Data**:
   - `gaming_deals_latest.json`: Ofertas actuales con análisis completo
   - `humble_bundles_active.json`: Bundles activos de Humble Bundle
   - `historical_prices.json`: Historial de precios por juego

2. **Analysis Reports**:
   - `exceptional_deals_report.json`: Ofertas excepcionales identificadas
   - `value_analysis_report.json`: Análisis de valor de bundles
   - `price_trend_analysis.json`: Análisis de tendencias de precios

3. **Debug Information**:
   - `debug/`: Screenshots y HTML saves para troubleshooting
   - `scraping_metrics.json`: Métricas de performance de scraping
   - `error_logs.json`: Logs detallados de errores

## Alertas y Notificaciones

### Tipos de Alertas
1. **New Bundle Alert**: Nuevo bundle disponible con high value score
2. **Price Drop Alert**: Caída significativa de precio en wishlist games
3. **Flash Sale Alert**: Oferta de tiempo limitado detectada
4. **Free Game Alert**: Juego gratuito disponible (Epic, Steam, etc.)
5. **Exceptional Value Alert**: Bundle con value score > 85

### Canales de Notificación
- **Email**: Newsletters diarias y alertas inmediatas
- **Discord/Slack**: Notificaciones en tiempo real
- **Telegram Bot**: Updates instantáneos
- **RSS Feed**: Feed agregado para readers
- **Web Dashboard**: Interface visual con todas las ofertas

## Consideraciones Legales y Éticas

### Web Scraping Ethics
- **Rate Limiting**: Respeto por limitaciones de servidor
- **Robots.txt Compliance**: Seguimiento de directrices robots.txt
- **Terms of Service**: Respeto por términos de servicio
- **Fair Use**: Uso razonable y no abusivo de recursos

### Data Usage
- **Attribution**: Crédito apropiado a fuentes de datos
- **No Redistribution**: No redistribución comercial de datos
- **Personal Use**: Enfoque en uso personal y educativo
- **Privacy**: No recolección de datos personales de usuarios 
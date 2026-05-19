# Watchtower (MEGALITH) — Resumen del Codebase

> Generado automáticamente el 10 de abril de 2026
> Repo: `josmerod/watchtower` — rama `main`
> ~119.000 líneas de Python en 300+ archivos fuente

---

## 1. Qué hace el proyecto

Watchtower es una **plataforma de inteligencia de datos** que automatiza la recolección, procesamiento y visualización de información procedente de **50+ fuentes online**. Funciona en tres capas:

1. **ETL Pipelines** (62 ETLs en 25 dominios): scrapers que extraen datos de ArXiv, GitHub, Reddit, HackerNews, YouTube, game stores, plataformas de cursos (Udemy, Coursera), plataformas de IA (OpenAI, Anthropic, HuggingFace, Replicate), noticias (TechCrunch, Lobste.rs, Medium), y muchos más.
2. **Watchers**: monitores event-driven que detectan cambios en webs con persistencia de estado en JSON.
3. **Dashboard**: interfaz web interactiva con ~25 pestañas (Dash + Bootstrap, puerto 7780) para visualizar y filtrar toda la información agregada. También tiene un dashboard legacy en Streamlit (puerto 8501).

Además incluye:
- **Motor de recomendaciones** personalizado basado en contenido y perfiles de usuario.
- **Motor de alertas** configurable con reglas.
- **API REST** (FastAPI) en `/api/v1/` para acceso programático.
- **Deduplicación** de contenido con engine dedicado.
- **Circuit breakers**, **proxy rotation**, **checkpointing** para resiliencia.

---

## 2. Estructura de directorios

```
watchtower/
├── src/                          # Código fuente principal
│   ├── config/                   # Configuración Pydantic Settings
│   │   ├── models.py             # Modelos de config anidados (DB, scraping, API...)
│   │   └── settings.py           # Settings principal con env vars (WATCHTOWER_*)
│   ├── etl/                      # 62 ETLs en 25 subdominios
│   │   ├── base.py               # BaseETL (Template Method, 781 líneas)
│   │   ├── base_refactored.py    # Versión refactorizada en progreso
│   │   ├── circuit_breaker.py    # Aislamiento de fallos
│   │   ├── proxy_manager.py      # Rotación de IPs
│   │   ├── factory/              # Factory + Registry pattern
│   │   ├── arxiv/                # Papers de investigación (con services separados)
│   │   ├── ai_platforms/         # OpenAI, Anthropic, HuggingFace, Replicate, Gemini, Copilot, PwC
│   │   ├── news/                 # ~25 scrapers: HN, Reddit, TechCrunch, Lobste.rs, DevTo, etc.
│   │   ├── games/                # Deals, GOG, Humble, Itch.io, Metacritic, IsThereAnyDeal
│   │   ├── goldigging/           # Cursos (Udemy, Coursera, DeepLearning.AI, Pluralsight) + scavenging
│   │   ├── entertainment/        # Cine, Spotify, Trakt, memes
│   │   ├── intelligence/         # SEC EDGAR, WHO, LessWrong, developer news, cloud, open source
│   │   ├── youtube_shorts/       # OCR de vídeos cortos con Tesseract
│   │   ├── ecommerce/            # Shoppy
│   │   ├── museums/              # Exposiciones de museos
│   │   ├── fourchan/             # Hilos de 4chan
│   │   ├── spanish_public_aid/   # Ayudas públicas españolas (refactorizado con services)
│   │   ├── anime/                # MAL, AniList
│   │   ├── adhd/                 # Publicaciones ADHD
│   │   ├── neurodivergent/       # Localizaciones ADHD-friendly
│   │   ├── deals/                # Lifetimo
│   │   ├── courses/              # AWS Skill Builder, GCP Skills Boost, MS Applied Skills
│   │   ├── rss_feeds/            # ETL genérico para feeds RSS
│   │   ├── substack/             # Newsletters Substack
│   │   ├── trendshift/           # Tendencias tech
│   │   ├── expanded/             # Hashnode, Kaggle, OpenAlex, StackExchange, RapidAPI, etc.
│   │   ├── github/               # GitHub trending via RSS
│   │   └── opensource/           # Proyectos open source
│   ├── models/                   # 38 modelos Pydantic
│   │   ├── base.py               # TimestampedModel base
│   │   ├── news.py, arxiv.py, games.py, course.py, anime.py...
│   │   └── ...                   # Un modelo por dominio
│   ├── watchers/                 # Sistema de monitores
│   │   ├── base_watcher.py       # ABC con estado JSON, eventos, logging
│   │   ├── enhanced_watcher.py   # Versión mejorada
│   │   ├── arxiv_watcher.py      # Watcher específico ArXiv
│   │   ├── ms_skills_watcher.py  # Watcher MS Skills
│   │   └── run_watcher.py        # CLI para ejecutar watchers
│   ├── web/
│   │   ├── dashboard/            # Dash (principal)
│   │   │   ├── app.py            # App principal con contenedor de pestañas (401 líneas)
│   │   │   ├── components/       # 38 componentes de pestañas
│   │   │   │   ├── news_tab.py, arxiv_research_tab.py, games_tab.py
│   │   │   │   ├── courses_tab.py, entertainment_tab.py, crypto_tab.py
│   │   │   │   ├── intelligence_tab.py, recommendations_tab.py
│   │   │   │   ├── shortcuts_tab.py, deals_tab.py, museums_tab.py
│   │   │   │   └── ... (~25 tabs activos + backups/broken)
│   │   │   ├── assets/           # CSS + JS (mobile responsive, drag-drop, shortcuts)
│   │   │   └── managers/         # Gestores de datos (course_data_manager)
│   │   └── api/                  # FastAPI REST API
│   │       └── routes.py         # Endpoints /api/v1/
│   ├── api/                      # API layer
│   │   ├── main.py               # FastAPI app con CORS y health check
│   │   ├── routers.py            # Routers de la API
│   │   └── models.py             # Modelos de request/response
│   ├── intelligence/             # Motor de IA
│   │   ├── recommendation_engine.py  # Recomendaciones basadas en contenido
│   │   ├── llm_client.py        # Cliente LLM (OpenAI)
│   │   ├── enrichment.py        # Enriquecimiento de datos
│   │   └── news_intelligence.py # Análisis de noticias
│   ├── alerts/                   # Sistema de alertas
│   │   ├── engine.py             # Motor de reglas de alerta
│   │   └── models.py             # Modelos de alertas
│   ├── recommendations/          # Sistema de recomendaciones
│   │   ├── recommendation_engine.py
│   │   ├── activity_tracker.py   # Tracking de actividad de usuario
│   │   └── models.py
│   ├── analytics/                # Analíticas
│   │   ├── trends.py             # Análisis de tendencias
│   │   └── technology_adoption.py
│   ├── data_quality/             # Calidad de datos
│   │   ├── deduplication.py      # Motor de deduplicación
│   │   └── user_profile_manager.py
│   ├── di/                       # Inyección de dependencias
│   │   ├── container.py
│   │   └── service_registry.py
│   ├── repositories/             # Repository pattern
│   │   ├── base_repository.py
│   │   └── repository_manager.py
│   ├── scraping/                 # Gestión de scraping
│   │   └── strategy/             # Strategy pattern para scrapers
│   ├── exceptions/               # Jerarquía de excepciones custom
│   │   ├── base.py, etl.py, scraping.py, watcher.py
│   ├── launcher/                 # Launcher unificado
│   │   ├── main.py               # Entry point multi-modo (531 líneas)
│   │   ├── cli.py                # CLI interface
│   │   └── health_monitor.py     # Monitor de salud de procesos
│   ├── miners/                   # Scrapers especializados
│   │   ├── udemy-universal/      # Udemy course miner (proyecto embebido)
│   │   ├── asf-winonly/          # ArchiSteamFarm (binario Win)
│   │   └── crypto_sentiment_miner.py
│   ├── constants/                # Constantes (etl categories)
│   ├── services/                 # Data loader service
│   └── utils/                    # Utilidades compartidas
│       ├── logging.py, file_system.py, backup_utils.py
│       ├── nlp_classifier.py     # Clasificación NLP con NLTK
│       ├── trend_scheduler.py    # Scheduler de tendencias
│       ├── date_parser.py, deduplicate_courses_cli.py
│       └── youtube_ocr_converter.py
├── Tests/                        # 79 archivos de test
│   ├── etl/, alerts/, analytics/, api/
│   ├── dashboard/, recommendations/, models/
│   ├── e2e/                      # Tests end-to-end (Playwright)
│   ├── integration/              # Tests de integración
│   ├── performance/              # Tests de rendimiento
│   └── unit/                     # Tests unitarios
├── data/                         # Datos JSON (output de ETLs, con timestamps)
│   └── shortcuts/                # Shortcuts predefinidos
├── docs/                         # Documentación extensa
│   ├── technical/                # Guías técnicas
│   ├── potentialsources/         # Fuentes potenciales futuras
│   └── ... (PRD, arquitectura, refactorización, etc.)
├── deployment/                   # Scripts de deployment
│   ├── Dockerfile, deploy.py, supervisord.conf
├── services/                     # Systemd/launchd services
│   ├── watchtower.service, com.watchtower.platform.plist
├── scripts/                      # Scripts varios
│   ├── deploy/                   # Scripts por OS (Mac, Linux, Windows)
│   └── manual_demo_tests/
├── .bmad/                        # BMad Method (agentes AI para desarrollo)
│   ├── agents/                   # PM, Dev, Architect, UX, TEA, Writer, SM
│   ├── workflows/                # Workflows BMM completos (4 fases)
│   └── tasks/                    # Tareas reutilizables
├── .bmad-ephemeral/              # Sprint status y stories BMM
├── .gemini/commands/             # Comandos Gemini IDE
├── .agent/                       # Config de agente AI
├── .continue/                    # Config Continue IDE
│
├── pyproject.toml                # Config del proyecto (hatchling + UV)
├── setup.py                      # Setup legacy (setuptools)
├── uv.lock                       # Lock file de UV
├── Dockerfile                    # Multi-stage build (Python 3.11-slim)
├── Dockerfile.dev                # Dev container
├── docker-compose.yml            # Compose básico (puerto 7777)
├── docker-compose.dev.yml        # Compose dev
├── docker-compose.enhanced.yml   # Compose enhanced
├── .env.template                 # Template de env vars
├── .pre-commit-config.yaml       # Pre-commit hooks
├── .flake8                       # Config flake8
├── playwright.config.py          # Config e2e tests
├── openapi.json                  # OpenAPI schema exportado
├── run_watchtower_dashboard.py   # Entry point del dashboard
├── run_all_etl.sh/.bat           # Ejecutar todos los ETLs
├── watchtower.py                 # Script principal legacy
└── AGENTS.md                     # Referencia de agentes BMM
```

---

## 3. Archivos clave y sus roles

| Archivo | Rol |
|---------|-----|
| `src/etl/base.py` (781 líneas) | **Core del framework ETL**. Template Method pattern: `extract()` → `transform()` → `load()`. Gestiona métricas, checkpoints, deduplicación, logging, errores. Toda ETL hereda de `BaseETL`. |
| `src/web/dashboard/app.py` (401 líneas) | **Dashboard principal**. Inicializa Dash + Bootstrap, registra las ~25 pestañas, configura callbacks, assets CSS/JS. |
| `src/launcher/main.py` (531 líneas) | **Launcher unificado**. Soporta 4 modos (dev, prod, etl_only, dashboard_only). Health monitoring, hot reload, gestión de procesos con psutil. |
| `src/config/settings.py` | **Configuración centralizada**. Pydantic Settings con env vars (`WATCHTOWER_*`), config anidada (DB, scraping, API, LLM, logging...). Singleton vía `@lru_cache`. |
| `src/config/models.py` | **Modelos de configuración**. DatabaseConfig, ScrapingConfig, APIConfig, ETLConfig, LLMConfig, etc. |
| `src/watchers/base_watcher.py` | **Framework de watchers**. ABC con estado persistente (JSON), generación de eventos, integración con AlertEngine. |
| `src/api/main.py` | **API REST**. FastAPI con CORS, health check, router en `/api/v1/`. |
| `src/intelligence/recommendation_engine.py` | **Motor de recomendaciones**. Content-based filtering con perfil de usuario y scoring multi-criterio. |
| `src/intelligence/llm_client.py` | **Cliente LLM**. Integración con OpenAI para enriquecimiento de datos. |
| `src/data_quality/deduplication.py` | **Motor de deduplicación**. Elimina contenido duplicado entre fuentes. |
| `src/alerts/engine.py` | **Motor de alertas**. Reglas configurables para notificaciones. |
| `src/di/container.py` | **Contenedor DI**. Inyección de dependencias para servicios. |
| `src/etl/circuit_breaker.py` | **Circuit breaker**. Aislamiento de fallos en ETLs. |
| `src/etl/proxy_manager.py` | **Gestión de proxies**. Rotación de IPs para scraping. |
| `src/etl/factory/etl_factory.py` | **Factory**. Creación de ETLs por nombre/tipo. |
| `pyproject.toml` | **Config del proyecto**. Dependencias, tool configs (ruff, mypy, pytest), build system (hatchling). |
| `Dockerfile` | **Docker**. Multi-stage build, UV, Playwright, non-root user. |
| `run_watchtower_dashboard.py` | **Entry point** para arrancar el dashboard directamente. |

---

## 4. Dependencias y tech stack

### Lenguaje y runtime
- **Python 3.10+** (target 3.11 en Docker)
- **UV** como package manager (10-100x más rápido que pip)
- **hatchling** como build backend

### Procesamiento de datos
- `pandas` >= 2.2.3, `polars` >= 0.20, `numpy` >= 2.2.5
- `scikit-learn` >= 1.6.1 (clasificación NLP)
- `pyarrow` >= 20.0.0 (formato columnar)

### Web scraping
- `playwright` >= 1.51.0 (scraping dinámico con headless browser)
- `beautifulsoup4` + `html5lib` (parsing HTML)
- `feedparser` (RSS/Atom feeds)
- `cloudscraper` (bypass Cloudflare)
- `aiohttp` (async HTTP)
- `requests` (HTTP síncrono)
- `yt-dlp` (descarga YouTube)
- `pytesseract` + `opencv-python` (OCR para YouTube Shorts)

### Dashboard y UI
- `dash` >= 2.0 + `dash-bootstrap-components` (dashboard principal, puerto 7780)
- `streamlit` >= 1.45 (dashboard legacy, puerto 8501)
- `plotly` >= 5.0 (gráficos interactivos)
- `altair` >= 5.5 (visualizaciones declarativas)

### API
- `fastapi` >= 0.110 + `uvicorn` >= 0.27 (REST API)
- `httpx` >= 0.27 (cliente HTTP async)

### Configuración y validación
- `pydantic` >= 2.11 + `pydantic-settings` >= 2.9 (modelos y config)
- `python-dotenv` (env vars)
- `pydantic` BaseModel para los 38 modelos de datos

### NLP y ML
- `nltk` >= 3.9 (clasificación de texto)
- `openai` >= 2.11 (LLM para enriquecimiento)

### DevOps y calidad
- `ruff` (lint + format, line-length 210)
- `pytest` + `pytest-cov` (tests y cobertura)
- `mypy` (type checking, configuración permisiva)
- `pre-commit` (hooks de calidad)
- `detect-secrets` (prevención de leaks)
- `playwright` (e2e tests)

### Infraestructura
- `docker` + `docker-compose` (containerización)
- `paramiko` >= 4.0 (SSH para deployment en Unraid)
- `psutil` >= 6.0 (monitorización de procesos)
- `watchdog` >= 6.0 (file system watching, hot reload)

### Storage
- **JSON files** con timestamps (no usa base de datos)
- Estructura: `data/{etl_name}/output/`

---

## 5. Cómo ejecutarlo

### Instalación

```bash
# Clonar
git clone https://github.com/josmerod/watchtower.git
cd watchtower

# Instalar UV
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux

# Instalar dependencias
uv sync --all-extras

# Instalar browsers para Playwright
uv run playwright install
```

### Dashboard

```bash
# Dash (recomendado, puerto 7780)
uv run python run_watchtower_dashboard.py

# Streamlit legacy (puerto 8501)
uv run streamlit run src/web/fullstreamlit/app.py
```

### ETLs

```bash
# Ejecutar todos
./run_all_etl.sh              # Linux/Mac
.\run_all_etl.bat             # Windows

# ETL específico
uv run python src/etl/arxiv/arxiv_etl.py
uv run python src/etl/news/news_get_ycombinator.py
```

### Watchers

```bash
# Todos continuamente
uv run python src/watchers/run_watcher.py

# Uno específico, una vez
uv run python src/watchers/run_watcher.py arxiv_watcher --once
```

### API REST

```bash
# Iniciar API
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health
```

### Launcher unificado

```bash
# Modo desarrollo (con hot reload)
uv run python src/launcher/main.py --mode development

# Modo producción
uv run python src/launcher/main.py --mode production

# Solo ETLs
uv run python src/launcher/main.py --mode etl_only

# Solo dashboard
uv run python src/launcher/main.py --mode dashboard_only
```

### Docker

```bash
# Build
docker build -t watchtower-app .

# Run
docker run -p 7777:7777 --env-file .env watchtower-app

# Docker Compose
docker-compose up -d
```

### Tests

```bash
uv run pytest                           # Todos
uv run pytest Tests/unit/               # Unitarios
uv run pytest Tests/e2e/                # E2E (Playwright)
uv run pytest --cov=src                 # Con cobertura
uv run ruff check . && uv run pytest    # Lint + tests
```

---

## 6. Issues, TODOs y observaciones

### Arquitectura

1. **Sin base de datos**: Todo se almacena en JSON files con timestamps. Escala mal para grandes volúmenes. El `DatabaseConfig` existe en los modelos pero no hay implementación real de DB.
2. **Código muerto / duplicado**: Hay versiones `_refactored.py`, `_backup.py`, `_broken.py` en el repo (ej: `rule_form_backup.py`, `notifications_tab_broken.py`, `crypto_tab_basic.py`). Deberían limpiarse.
3. **`base.py` vs `base_refactored.py`**: La refactorización de BaseETL está a medias. Ambos ficheros coexisten.
4. **`setup.py` + `pyproject.toml`**: Duplicación de configuración. `setup.py` referencia ficheros `requirements-*.txt` que no existen en el repo. Debería eliminarse y usar solo `pyproject.toml`.

### Configuración

5. **API key hardcodeada**: `API_MASTER_KEY: str = Field(default="watchtower-dev-key")` en `settings.py`. Debería ser obligatoria en producción.
6. **CORS wildcard**: `allow_origins=["*"]` en FastAPI. Inseguro en producción.
7. **Secretos en `.env.template`**: El template tiene `***` como placeholders, pero hay que verificar que no hay secretos reales en el repo.

### Dependencias

8. **Dependencias pesadas en core**: `opencv-python`, `moviepy`, `pytesseract` son solo para YouTube Shorts OCR. Deberían ser optional.
9. **`black` + `ruff`**: Ambos están como dev dependencies. Ruff ya formatea, black es redundante.
10. **ML dependencies sin uso**: `langgraph`, `faiss-cpu`, `chromadb` están en `[ml]` pero no hay código que los use.
11. **Línea 210**: El `line-length = 210` es inusualmente alto. Dificulta lectura.

### Testing

12. **79 archivos de test** pero cobertura real desconocida. Muchos tests son de verificación/manual más que unitarios automáticos.
13. **Tests e2e** dependen de Playwright y de que los ETLs tengan datos reales.

### Deployment

14. **Puertos inconsistentes**: Dockerfile/healthcheck usa 7777, README dice 7780, docker-compose.yml usa 7777. Necesita unificación.
15. **`playwright install --with-deps`** en Dockerfile: instala browsers completos dentro del container, incrementando el tamaño de imagen significativamente.

### BMad / Agentes AI

16. El proyecto incluye un framework completo de **BMad Method** (`.bmad/`) con 8 agentes AI (PM, Dev, Architect, UX, Analyst, TEA, Writer, SM) y workflows de 4 fases. Es metadocumentación para desarrollo asistido por AI, no parte del runtime.

### Tamaño y mantenimiento

17. **~119K líneas de Python** es considerable para un proyecto personal. Hay 25 dominios ETL, cada uno con su propio scraper.
18. **Archivos de datos en repo**: `src/miners/udemy-universal/Courses/` tiene cientos de archivos `.txt` diarios desde diciembre 2025. Debería estar en `.gitignore`.
19. **`src/miners/asf-winonly/`**: Contiene el binario completo de ArchiSteamFarm (~30MB de DLLs y assets). No debería estar en el repo.

### Otros

20. **`openapi.json`** en el root: debería generarse automáticamente, no commitearse.
21. **Múltiples scripts sueltos** en el root (debug, check, verify, test, emergency...): deberían consolidarse bajo `scripts/`.
22. **`gcp_test.json`, `cc_parsed.json`**: Archivos de test/debug commiteados.

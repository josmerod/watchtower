# Especificación de mejora — Tab 🛰️ Tech Radar

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/tech_radar_tab.py` + ETLs de noticias asociados

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"Technology Radar — cloud, GenAI, AI y self-hosting trends." El tab más joven (T-015). Grid responsive de 4 columnas, una por fuente (Google AI Blog, KDnuggets, Cloud Updates, Selfh.st), cards con título enlazado + fecha + resumen 200 chars, cap 25 por fuente. **Sin callbacks** (estático).

- Componente: `tech_radar_tab.py` (118 líneas — el más pequeño). ✅ Usa `get_project_root()`.
- Fuentes = 4 ficheros JSON producidos por ETLs del tab News (`news_get_google_ai_blog`, `news_get_kdnuggets`, `news_get_cloud_updates`, `news_get_selfhosted` → selfh.st/rss).

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| TR1 | **P0** (UX) | La caja de búsqueda `tech-radar-search` **no tiene callback** — decoración no funcional (grep: el id solo aparece en el layout). |
| TR2 | **P0** (datos) | KDnuggets: el ETL anida summary/tags en `metadata` y usa `published_at`, pero el tab lee `summary/description` y `published` top-level → cards sin resumen ni fecha aunque haya datos. |
| TR3 | P1 | Fuentes **duplicadas con News**: Google AI, KDnuggets y Cloud Updates siguen siendo subtabs del tab News (comentario del propio tech_radar dice "consolida fuentes que estaban en News" — la consolidación no se completó). |
| TR4 | P1 | `category` definida en `RADAR_SOURCES` ("AI", "Data Science"…) y nunca mostrada; sin merge cross-fuente, sin orden cronológico (file order), sin paginación (cap 25), sin refresh. |
| TR5 | P2 | Retención inconsistente: cloud_updates solo escribe `latest.json`; kdnuggets pisa un único fichero — sin histórico para tendencias. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **InfoQ RSS** (`feed.infoq.com`) | RSS | Arquitectura/dev a nivel profesional, complemento senior de HN | Bajo | ⭐⭐ |
| **The New Stack RSS** (`thenewstack.io/feed`) | RSS | Cloud-native/infraestructura | Bajo | ⭐⭐ |
| **Changelog Nightly/Weekly** (`changelog.com/nightly/feed`) | RSS | Repos GitHub trending curados a diario — puente natural con Knowledge Garden/Git Trends | Bajo | ⭐⭐⭐ |
| **CNCF Blog + Landscape** (`cncf.io/feed` ya en cloud_updates; landscape `landscape.cncf.io/data.json` público) | JSON | Estado del ecosistema cloud-native por categoría/madurez | Medio | ⭐⭐ |
| **ThoughtWorks Technology Radar** (publicación semestral; HTML scrapeable o datos de su herramienta open-source `thoughtworks/build-your-own-radar`) | Scrape/JSON | El "radar" de referencia con cuadrantes Adopt/Trial/Assess/Hold — vocabulario y estructura para TR-**F1** | Medio | ⭐⭐⭐ |
| **r/SelfHosted + r/homelab** (infra reddit_unified existente) | Dato existente | Pulso real de la comunidad self-hosting (selfh.st es agregador, esto es conversación) | Muy bajo | ⭐⭐ |
| **GitHub Blog/Changelog** ya está; añadir **GitHub Spark? no**. **Hacker News front page** via Algolia (`hn.algolia.com/api/v1/search?tags=front_page`) | REST | Radar de "qué se está discutiendo", no solo "qué se publica" | Bajo | ⭐⭐ |

## 3. Mejoras a funcionalidad existente

### M1 — Buscador funcional (fix TR1)
1 callback `tech-radar-search` (salida: grid re-renderizado) con debounce; incluye cross-fuente (ver F1). Elimina el estado actual de caja muerta.

### M2 — Normalizar el reader (fix TR2)
Añadir KDnuggets a la lógica de fallbacks: leer `metadata.summary`/`published_at` (el helper `get_sortable_date` de `data_loader` ya soporta cadenas de aliases — reutilizar el patrón del tab News en vez de acceso directo a keys). Test con fixture del output real del ETL.

### M3 — Completar la consolidación (fix TR3)
Decidir fuente canónica por feed: Tech Radar = análisis/radar; News = medios generales. Mover Google AI + KDnuggets + Cloud Updates **solo** a Tech Radar y dejar en News un link/subtab fantasma con redirect, o mantener duplicado pero con badge "ver en Tech Radar". Recomendado: mover y aceptar el ahorro de 3 subtabs en News (que tiene 22).

### M4 — Orden, paginación y refresh
Orden fecha desc global (hoy file order); botón 🔄 (TTL de lectura 5 min); cap configurable con "ver más" (patrón items_per_page).

### M5 — Retención homogénea (fix TR5)
Todos los ETLs del radar con snapshot timestamped + `latest` (estándar BaseETL) — habilita F2/tendencias.

## 4. Funcionalidades nuevas propuestas

### TR-F1 — El radar de verdad (visualización por cuadrantes)
**Objetivo:** que el tab parezca y funcione como un radar, no como 4 columnas de cards.
**UI:** vista "Radar": scatter plotly polar/categorizado con anillos (Adopt/Trial/Assess/Hold por madurez estimada) y cuadrantes (Técnicas/Herramientas/Plataformas/Lenguajes — vocabulario ThoughtWorks). Cada item = tecnología detectada (ver datos), tamaño por nº menciones, color por fuente. Click → panel con artículos relacionados.
**Datos:** extracción de "tecnologías" de los títulos/resúmenes: diccionario conocido (k8s, terraform, llama, rust, n8n…) + heuristicas de mayúsculas/versiones; conteo de menciones por snapshot (con M5 hay serie temporal).
**Callbacks:** 1 render del radar + 1 detalle de burbuja.
**Aceptación:** ≥20 tecnologías posicionadas; burbuja con ≥1 artículo enlazado; radar regenerable sin restart.
**Esfuerzo:** A (2–3 jornadas — el extraction de entidades es la parte dura; empezar con diccionario curado).
**Nota:** es la feature con mayor identidad potencial del tab; todo lo demás son cards.

### TR-F2 — Detección de "momentum"
Por tecnología (F1): menciones esta semana vs media móvil 4 semanas → lista "Subiendo 🔺 / Bajando 🔻" bajo el radar. Requiere M5. Esfuerzo: M (una vez existe F1).

### TR-F3 — Feed unificado con filtros
Vista "Todos": merge cronológico de las fuentes con filtros fuente/categoría/fecha + búsqueda global (M1 apunta aquí). Esfuerzo: B–M.

### TR-F4 — Radar self-hosting personal
Cruce con `docs/potentialsources/home-server-automation-projects.md`: subtab "Mi stack" — checklist de servicios que corro (input manual) vs menciones del radar → "novedades relativas a tu stack" (ej. nueva release mayor de n8n). Esfuerzo: M.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M1 buscador, M2 fix KDnuggets, TR4 orden/refresh |
| **Corto plazo** | M3 consolidación News↔Radar, Changelog Nightly (⭐⭐⭐) + r/SelfHosted, TR-F3 feed unificado |
| **Medio plazo** | TR-F1 radar por cuadrantes (con diccionario curado v1), M5 retención |
| **Estratégico** | TR-F2 momentum, TR-F4 "mi stack", ThoughtWorks Radar como import semestral que calibre los anillos |

**Criterios de éxito:** 0 UI muerta; 0 duplicación News/Radar sin decidir; feed unificado ordenado; el tab tiene al menos una visualización que ningún lector RSS da (el radar F1 o momentum F2).

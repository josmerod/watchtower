# Especificación de mejora — Tab Learning (Cursos)

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/courses_tab.py` + `src/etl/{courses,goldigging}/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"Cursos Online": 6 subtabs — Coursera, Udemy, MS Credentials, AWS Skill Builder, GCP Skills Boost, 📚 freeCodeCamp. Búsqueda + filtros por subtab; paginación propia (PAGE_SIZE=15) **solo** en Coursera y Udemy; MS/AWS/GCP renderizan el dataframe filtrado completo por cada tecla.

- Componente: `courses_tab.py` (1.268 líneas, el más largo del dashboard). Carga datos **al importar el módulo** (`load_all_courses_data()` a nivel de módulo → sin refresh nunca).
- No usa `data_loader.py` ni `search_utils.py` (rehace parsing de fechas con `parse_course_date`, duplicando `parse_date_universal`).

### 1.2 Fuentes actuales

| Subtab | Fichero leído | ETL | Upstream real | Problema |
|---|---|---|---|---|
| Coursera | `data/classcentral/coursera_courses.json` | `goldigging/goldigging_deeplearningai_courses.py` (¡nombre engañoso!) | **Class Central** `classcentral.com/provider/coursera` (Playwright) | El ETL "coursera" registrado (`goldigging_coursera_courses.py`) escribe a `data/coursera/` que **nadie lee**; pluralsight ETL → `data/pluralsight_courses/` sin consumidor; el verdadero DeepLearning.AI no se scrapea |
| Udemy | `data/udemy/udemy_courses.json` | `courses/udemy_spreadsheet_etl.py` | Google Sheet público (CSV export) | `goldigging_udemy_courses.py` (NO registrado) escribe el **mismo fichero** (gid distinto) → riesgo de colisión |
| MS | `data/courses/ms_applied_skills.json` | `courses/ms_applied_skills_etl.py` | Microsoft Learn Catalog API (appliedSkills + certifications) | OK |
| AWS | `data/courses/aws_skill_builder.json` | `courses/aws_skill_builder_etl.py` | Class Central provider aws-skill-builder (con detección Cloudflare) | Según `stale_sources_report.txt`: NEVER/EMPTY |
| GCP | `data/courses/gcp_skills_boost.json` | `courses/gcp_skills_boost_etl.py` | `partner.skills.google` API JSON | NEVER/EMPTY |
| freeCodeCamp | `data/news/freecodecamp_latest.json` | `news/news_get_freecodecamp.py` | RSS fCC | Render estático de 50 artículos, sin búsqueda |

### 1.3 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| C1 | **P0** | Triple desalineación Coursera: ETL-que-suena-a-Coursera escribe a `data/coursera/` (huérfano), el tab lee `data/classcentral/` escrito por un ETL llamado "deeplearningai" que nunca toca deeplearning.ai. Pluralsight (registrado) y DeepLearning.AI (nominal) sin representación en UI. |
| C2 | **P0** | Dos ETLs (uno no registrado) escriben `data/udemy/udemy_courses.json`. Ejecutar el equivocado silenciosamente sustituye el catálogo. |
| C3 | **P0** (datos) | AWS y GCP llevan meses sin datos (NEVER/EMPTY en audit) — 2 de 6 subtabs estructuralmente vacías; freeCodeCamp es la tercera vía (artículos, no cursos). |
| C4 | P1 | Carga al importar + globals mutables: sin refresh, sin TTL; el resto del dashboard usa repos con TTL. |
| C5 | P1 | MS/AWS/GCP sin paginación y re-render total por tecla sin debounce. |
| C6 | P1 | Coursera: rating, cost, certificate_offered, start_date capturados y no mostrados; el filtro "solo gratis" (`df[df["is_free"]]`) descarta NaN silenciosamente (comentario en el código lo admite). |
| C7 | P2 | `print("DEBUG: ...")` residuales (líneas 391, 762, 850, 978…). |
| C8 | P2 | Formatos de fecha inconsistentes entre subtabs (`%Y-%m-%d %H:%M` vs `%Y-%m-%d`); sin orden user-facing ni export. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Class Central universitario** (`classcentral.com` providers: edx, futurelearn, stanford-online…) | Scrape (patrón ya probado en 2 ETLs propios) | Un solo patrón de ETL → N proveedores; Class Central es el agregador más completo | Medio (1 ETL paramétrico) | ⭐⭐⭐ |
| **Hugging Face Learn** (`huggingface.co/learn` — cursos NLP/LLM/agents, gratis) | Scrape ligero / API no oficial | Alineado con el perfil AI del usuario; contenido que ninguna otra fuente da | Bajo | ⭐⭐⭐ |
| **DeepLearning.AI real** (`deeplearning.ai/courses` shortcourses) | Scrape | Cumplir el nombre del ETL actual; short courses gratis de LLMs | Bajo | ⭐⭐⭐ |
| **edX catalog** (API pública descatalogada → usar `course-catalog-api` o scrape) | REST/scrape | MOOCs universitarios | Medio | ⭐⭐ |
| **Microsoft Learn — add paths/learning paths** (la misma Catalog API tiene `learningPaths` además de appliedSkills) | REST ya integrada | Amplía "MS Credentials" con learning paths y módulos | Muy bajo | ⭐⭐ |
| **Google Cloud Skills Boost ya está**; añadir **Google Career Certificates** vía Class Central | Scrape | Certificaciones | Bajo | ⭐ |
| **MIT OpenCourseWare RSS** (`ocw.mit.edu/rss`) + **Stanford Online** (`online.stanford.edu` RSS) | RSS | CS universitario de élite, gratis, RSS estable | Bajo | ⭐⭐ |
| **freeCodeCamp curriculum** (API `api.freecodecamp.org`? inestable — mejor mantener RSS + añadir `/rss/` de categorías) | RSS | Granularidad por track (Data Analysis, ML…) | Bajo | ⭐ |
| **Coursera API oficial** | Partner-only | No viable sin afiliación — mantener Class Central como proxy | — | — |

## 3. Mejoras a funcionalidad existente

### M1 — Resolver el triángulo Coursera/ClassCentral/DeepLearning.AI (fix C1)
1. Renombrar ETLs para que el nombre refleje el upstream: `classcentral_coursera_etl.py`, `classcentral_aws_etl.py`.
2. Unificar el output del ETL coursera registrado con lo que el tab lee (una sola ruta: `data/classcentral/coursera_courses.json`), deprecar `data/coursera/`.
3. Crear `classcentral_etl.py` paramétrico (`--provider coursera|edx|aws-skill-builder|futurelearn`): un solo fichero, N proveedores (base para §2).
Aceptación: `run_all_etl_orchestrator.py` sin duplicados; ninguna ruta huérfana; `audit_stale_sources.py` limpio de falsos COURSERA.

### M2 — Desactivar o registrar el Udemy duplicado (fix C2)
Eliminar `goldigging_udemy_courses.py` o registrarlo con output distinto (`data/udemy_capgemini/`). Añadir test que verifique que ningún par (ETL registrado, fichero de output) colisiona.

### M3 — Refresco con TTL + botón (fix C4)
Mover la carga a un `CourseRepository(BaseRepository)` con TTL 15 min y añadir 🔄 en el header (patrón propuesto en Videos M1). Elimina los globals `ALL_COURSES_DATA/COURSES_DATA_LOADED`.

### M4 — Paginación y debounce homogéneos (fix C5)
Extender el patrón prev/next de Coursera/Udemy a MS/AWS/GCP (extraer helper `paginated_table(...)` dentro del tab) + `debounce=True` en todos los buscadores. Considerar `dash_table.DataTable` con `page_action="native"` como en Ayudas (menos código propio).

### M5 — Mostrar y filtrar por rating/precio/certificado (fix C6)
- Columnas extra Coursera: ⭐ rating, coste (badge gratis/de pago — con `is_free.fillna(False)`), 🎓 certificado, fecha inicio.
- Filtros transversales: "Solo gratis", "Con certificado", rating ≥ 4.
- freeCodeCamp subtab: búsqueda + cards (reutilizar patrón News) en vez de render estático.

### M6 — Limpieza (fix C7/C8)
`print→logger`; `parse_course_date` → `utils.parse_date_universal`; formato de fecha único `%Y-%m-%d`.

## 4. Funcionalidades nuevas propuestas

### F1 — Catálogo unificado multi-proveedor
**Objetivo:** una sola vista searchable de todos los cursos con facetas proveedor/gratis/certificado/nivel/idioma.
**UI:** subtab "🔎 Todos" primera; filtros facetados (Checklist proveedor, Radio gratis, rating mínimo) + tabla común (Título, Proveedor, Institución, Nivel, Idioma, ⭐, Gratis, Certificado, Fecha).
**Datos:** normalizar a un record común (CourseModel de `src/models/` ya existe) en un index combinado generado por el repositorio.
**Dedup cross-proveedor:** `src/utils/course_deduplication.deduplicate_courses` ya existe — usarlo contra el catálogo combinado (mismo curso en Class Central y Udemy).
**Aceptación:** búsqueda "python gratis certificado" devuelve resultados combinados; duplicados colapsados con badge.
**Esfuerzo:** M–A.

### F2 — Seguimiento de cursos ("mi lista" + progreso)
⭐ guardar + estado (interesante/matriculado/en curso/terminado) persistido en `localStorage`; subtab "Mis cursos"; % completado manual opcional. Integrable con activity_tracker. Esfuerzo: M.

### F3 — Alertas de cursos nuevos (watcher)
`BaseWatcher` (`src/watchers/`) que compare catálogos entre runs y emita eventos "nuevo curso de {proveedor} coincide con keywords {…}" → eventos a `data/watchers/courses/events/` + futuro canal de notificaciones (ver spec 14). Esfuerzo: M.

### F4 — Export y compartir
CSV de la vista filtrada + deep-link con query params. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M2 (duplicado Udemy), M6 (prints/fechas), renombrados M1 (sin cambiar rutas aún), filtro gratis con fillna |
| **Corto plazo** | M1 unificación rutas Coursera, M3 repositorio+refresh, M5 columnas rating/certificado, Hugging Face Learn + DeepLearning.AI (⭐⭐⭐) |
| **Medio plazo** | M4 paginación homogénea, F1 catálogo unificado, ETL Class Central paramétrico (edx/futurelearn) |
| **Estratégico** | F2 mi lista, F3 watcher de novedades, AWS/GCP: si siguen vacíos tras 1 intento de fix (Cloudflare/API), sustituir por equivalentes de Class Central |

**Criterios de éxito:** 0 rutas huérfanas ni ETLs con nombre engañoso; 6/6 subtabs con datos o deprecadas explícitamente; búsqueda gratis/certificado/rating operativa; catálogo unificado como vista principal.

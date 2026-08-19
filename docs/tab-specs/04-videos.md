# Especificación de mejora — Tab Videos

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/videos_tab.py` + `src/etl/goldigging/goldigging_youtube_posts.py` + `src/etl/youtube_shorts_ocr_etl.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Galería responsive de vídeos de YouTube agregados por canal/tema desde `data/youtube/<dir>/youtube_videos.json`. Filtros: canal (dropdown), búsqueda (título/descripción/canal), ventana de fecha (7/30/90/todos) y "items por página" (12/24/48/96, persistido en localStorage). Es el **único adoptante** de `items_per_page_selector.py`.

- Componente: `videos_tab.py` (532 líneas, clase `VideoManager` singleton).
- ETLs alimentadores:
  - `goldigging_youtube_posts.py` (registrado): yt-dlp sobre **20 temas / ~300 canales** de `src/etl/goldigging/channels.json` (aa-dev 57 canales, aa-gen-ai, zz-memes, zz-viajes…). `MAX_VIDEOS_PER_CHANNEL=50`, lookback 42 días.
  - `youtube_shorts_ocr_etl.py` (registrado, nombre engañoso): yt-dlp flat de UN canal hardcoded (`@setupsaitony/shorts`).
  - `src/etl/youtube_shorts/youtube_shorts_etl.py` (NO registrado, requiere Tesseract): el que el propio empty-state del tab recomienda ejecutar — **recomendación rota**.

### 1.2 Funcionalidad actual

1 callback combinado (`update_videos_combined`) con 4 inputs → summary alert + grid de tarjetas (thumbnail, título 2 líneas, canal, fecha). Dedup: fold canónico de nombres de directorio (`MatthewBerman` ≡ `matthew-berman`) + dedup por URL.

### 1.3 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| V1 | **P0** | `VideoManager` se carga **una vez al importar** (`loaded` flag, sin TTL): los outputs nuevos del ETL son invisibles hasta reiniciar el servidor. No hay botón refresh. |
| V2 | **P0** | Paginación vestigial: existe `html.Div(id="videos-pagination")` pero ningún callback la escribe; "items per page" es en realidad un tope duro. |
| V3 | **P0** (UX) | El empty-state recomienda `uv run python -m src.etl.youtube_shorts.youtube_shorts_etl` — ETL no registrado que escribe a otro directorio y exige Tesseract. |
| V4 | P1 | `views` y `length` se capturan en ambos ETLs y **jamás se renderizan**; `description` solo se usa para buscar. |
| V5 | P1 | Vídeos sin `published_at` parseable se descartan silenciosamente (`dropna`). |
| V6 | P1 | El dropdown "Channel" mezcla canales reales con directorios-tema (aa-*, zz-*): etiquetas inconsistentes para el usuario. |
| V7 | P2 | Cada callback itera todos los DataFrames → `to_dict("records")` → re-dedup → re-filtro → re-sort en Python antes de cortar a ≤96; sin caché de resultados. |
| V8 | P2 | Sin orden alternativo (solo fecha desc), sin "visto/no visto", sin export, sin vista detalle (link directo a YouTube). |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **YouTube Data API v3** (`googleapis.com/youtube/v3`, cuota gratuita 10k/día) | REST con key | Metadatos fiables (views/likes/duración ISO8601), búsquedas por tema, playlist feeds; elimina fragilidad yt-dlp para metadatos | Medio | ⭐⭐⭐ |
| **Invidious/Piped instances** (APIs públicas JSON `api/v1/trending?region=ES`, `/api/v1/channels/{id}/videos`) | REST sin key | Trending por país + metadatos de canal sin API key; instances inestables → mantener lista de fallbacks | Bajo | ⭐⭐ |
| **RSS por canal** (`youtube.com/feeds/videos.xml?channel_id=…`) | RSS | Descubrimiento incremental barato de nuevos vídeos por canal (15 últimos) — complemento ideal al ETL masivo | Bajo | ⭐⭐⭐ |
| **Podcasts ya indexados** (`news_get_podcasts.py` tiene 18 feeds; los de YouTube podrían dual-listarse aquí) | Dato ya existente | Cero ETL nuevo: cross-listar episodios con vídeo | Muy bajo | ⭐⭐ |
| **Temas nuevos en `channels.json`** | Config | El ETL es genérico por temas; añadir p.ej. aa-opensource, zz-ia-es es solo config | Muy bajo | ⭐⭐ |
| **Periscope/Superchat? no**; **Peertube sefloatright? no** — mantener foco YouTube | — | — | — | — |

## 3. Mejoras a funcionalidad existente

### M1 — Refresco de datos (fix V1)
Opciones (recomendada la b):
a) TTL de 5 min en `VideoManager.load_data()` + botón 🔄 "Recargar" que fuerce `force_refresh`.
b) Adoptar `BaseRepository` como el resto de tabs.
Aceptación: tras un run del ETL, el dato aparece ≤5 min sin restart.

### M2 — Paginación real (fix V2)
Implementar prev/next + contador "Página X de Y" escribiendo en el div `videos-pagination` ya existente. El "items per page" pasa a ser tamaño de página de verdad. Callback único con `State("videos-page-store","data")` + `dcc.Store` para la página actual. Esfuerzo: M.

### M3 — Corregir empty-state y nombres de ETL (fix V3)
Mensaje correcto (`goldigging_youtube_posts.py`) y renombrado de `youtube_shorts_ocr_etl.py` → coherente con lo que hace (metadatos de shorts). Añadir nota de que OCR no es necesario. Esfuerzo: B.

### M4 — Renderizar views/length (fix V4)
Badge de duración (mm:ss) sobre la thumbnail (esquina, estilo YouTube) y views ("12K vistas") bajo el canal. `length` requiere normalización (segundos ↔ "HH:MM:SS" según ETL de origen — unificar en transform). Esfuerzo: B–M.

### M5 — Separar "Temas" y "Canales" (fix V6)
Dos dropdowns: Tema (aa-*/zz-* o ninguno) y Canal (derivado de los `channel` de los records del tema activo). Búsqueda sigue siendo transversal. Esfuerzo: M.

### M6 — Vídeos sin fecha (fix V5)
No descartar: asignarles fecha `fetched_at` y marcarlos con badge "⏳ sin fecha" ordenando al final; o `published_date` nullable con sort `na_position="last"`. Esfuerzo: B.

## 4. Funcionalidades nuevas propuestas

### F1 — Visto / Ver más tarde
**Objetivo:** gestionar la cola de visualización dentro del dashboard.
**UI:** botón ✓ "visto" y ⏰ "más tarde" por tarjeta (hover); filtros "Solo nuevos" / "Mi lista"; contador de pendientes en el header del tab.
**Persistencia:** `localStorage` con hash de URL del vídeo (clientside, sin servidor); opcionalmente sincronizar con `src/recommendations/activity_tracker.py` para alimentar recomendaciones.
**Aceptación:** estado sobrevive recarga; "Solo nuevos" oculta los vistos; el grid no re-ordena al marcar (evitar layout-shift: `n_clicks` con `prevent_initial_call`).
**Esfuerzo:** M.

### F2 — Orden y modo de vista
Dropdown Orden: Fecha ⬇ (default), Fecha ⬆, Más vistos, Más recientes-vistos. Toggle Grid/Lista compacta (tabla: título, canal, duración, views, fecha) reutilizando el patrón tabla de otros tabs. Esfuerzo: B–M.

### F3 — Página de detalle in-dashboard
Click en tarjeta → `dbc.Modal` con embed `iframe youtube-nocookie.com/embed/{id}`, descripción completa, canal (link a su listado en el tab) y relacionados (motor de recomendaciones sobre tags/descripción). Evita salir del dashboard para previsualizar. Esfuerzo: M.

### F4 — Panel "Temas" con gestión de canales
Vista admin mínima: tabla de temas de `channels.json` (canal → tema) con contador de vídeos y última descarga, + export/edit del JSON (o al menos link al fichero y validación). Bajo esfuerzo si se hace read-only. Esfuerzo: B (read-only) / A (editable).

### F5 — "Nuevo desde mi última visita"
Comparar `localStorage.last_visit` con fechas: badge "NUEVO" + contador en el header ("37 vídeos nuevos"). Actualizar timestamp al离开 el tab. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M3 empty-state, M4 badges duración/views, M6 sin-fecha, M1 botón refresh |
| **Corto plazo** | M2 paginación real, F5 nuevos desde última visita, F2 orden/vistas, RSS por canal como descubrimiento incremental |
| **Medio plazo** | F1 visto/más-tarde (+activity tracker), F3 detalle con embed, M5 separación temas/canales |
| **Estratégico** | YouTube Data API v3 como fuente canónica de metadatos (yt-dlp solo para descubrimiento); F4 gestión de catálogo de canales |

**Criterios de éxito:** 0 UI muerta (pagination div); datos frescos sin restart; duración y views visibles; el flujo "descubrir → decidir → ver" resuelve dentro del dashboard.

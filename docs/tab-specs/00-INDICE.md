# Watchtower — Especificaciones de mejora por tab (índice y roadmap)

> Generado: 2026-08-17 a partir de auditoría exhaustiva de `src/web/dashboard/` (13 tabs wired), ETLs de `src/etl/`, componentes compartidos y ~15 componentes dormidos.
> Método: 6 análisis paralelos de código (componentes + ETLs + upstreams reales) + catálogos existentes (`docs/potentialsources/`).

## Documentos

| Doc | Tab / ámbito | Resumen del diagnóstico |
|---|---|---|
| [01-news.md](01-news.md) | 📰 News | 22 subtabs, 26 fuentes; 3 búsquedas muertas, modal related muerto, path Microsiervos roto |
| [02-shortcuts.md](02-shortcuts.md) | 🔗 Shortcuts | 177 atajos estáticos; sin CRUD (custom_shortcuts.json sin writer); icono/descripción sin render |
| [03-knowledge-garden.md](03-knowledge-garden.md) | 🌱 Knowledge Garden | 18 subtabs; 2 muertas (Dev.to, SO); 0 interactividad; campos ricos (score/votos/stars) descartados; bug postedAfter Product Hunt |
| [04-videos.md](04-videos.md) | 📺 Videos | Grid yt-dlp ~300 canales; sin refresh nunca; paginación vestigial; views/duración sin render |
| [05-courses.md](05-courses.md) | 🎓 Learning | Triple desalineación Coursera/ClassCentral/DeepLearning.AI; Udemy duplicado; AWS/GCP sin datos |
| [06-4chan.md](06-4chan.md) | 📑 4chan Generals | 15 boards; CWD-relativo; OP (mejor campo) sin render; boards duplicados ETL/UI |
| [07-scavenging.md](07-scavenging.md) | ⛏️ Scavenging | 🔴 **PASSKEY IPTORRENTS COMMITeada**; cap 100 pre-búsqueda; highlight literal; ventana Audible vencida |
| [08-valencia-events.md](08-valencia-events.md) | 🌆 Valencia Events | Stat "gratis" falsa; "próximos" incluye pasados; legacy 505 l muerto; sin venue/precio en modelo |
| [09-spanish-public-aid.md](09-spanish-public-aid.md) | 🏛️ Ayudas Públicas | closing_date/amount nunca poblados (timeline decorativa); 6 controles muertos; refactor a medias |
| [10-arxiv-research.md](10-arxiv-research.md) | 📄 ArXiv Research | 5 subtabs subalimentadas (query≠split); abstract/clusters/17 campos GitHub sin render |
| [11-deals.md](11-deals.md) | 🏷️ Deals | Sin precios (modelo los tiene, ETL no); rama multi-fuente con NameError; fuente única |
| [12-benchmarks.md](12-benchmarks.md) | 🏆 Benchmarks | `_fmt_score` duplicado (formato roto); link API inexistente; BridgeBench muerto; filtros latentes sin cablear |
| [13-tech-radar.md](13-tech-radar.md) | 🛰️ Tech Radar | Buscador decorativo; KDnuggets field-mismatch; duplicación con News sin resolver |
| [14-componentes-dormidos.md](14-componentes-dormidos.md) | 15 componentes sin conectar | Games/Notifications/Metrics = revival ⭐⭐⭐; travel/ecommerce/github_trending/ai_research = eliminar |
| [15-infraestructura-compartida.md](15-infraestructura-compartida.md) | Shared UX + alerts + recos + API | 3 componentes compartidos con 0 adoptantes; 3 antipatrones de caché; productor de trends inexistente |

## Matriz de salud

| Tab | Wired | Datos hoy | Bugs P0 | Quick wins | Apuesta estratégica |
|---|---|---|---|---|---|
| News | ✅ | ✅ mayoría | 3 | fix search ids + Microsiervos | Búsqueda global + leído/no-leído |
| Shortcuts | ✅ | ✅ | 1 | iconos/tooltips | CRUD + command palette (Ctrl+K) |
| Knowledge Garden | ✅ | ⚠️ parcial | 3 | postedAfter + catálogos | Garden global search + guardados |
| Videos | ✅ | ⚠️ server | 3 | refresh + badges duración | Visto/más-tarde + detalle embed |
| Courses | ✅ | ⚠️ 3/6 | 3 | des-duplicar Udemy | Catálogo unificado multi-proveedor |
| 4chan | ✅ | ⚠️ server | 1 | ruta absoluta + OP preview | Watcher de generals + alertas |
| Scavenging | ✅ | ⚠️ stale | 3 (+seguridad) | **rotar passkey YA** | Countdown de deadlines (Epic/Steam) |
| Valencia Events | ✅ | ⚠️ server | 2 | fix próximos + stats honestas | Feed ICS subscrivible + calendario |
| Ayudas Públicas | ✅ | ⚠️ 1 record | 2 | cablear controles muertos | BDNS API (fechas/cuantías) + alertas |
| ArXiv | ✅ | ⚠️ server | 1 | — | Clusters + citaciones (S2/OpenAlex) |
| Deals | ✅ | ⚠️ stale | 2 | scrape de precios | Multi-fuente (AppSumo/Shoppy) |
| Benchmarks | ✅ | 1/3 fuentes | 2 | formato + link | LiveBench/SWE-bench + series temporales |
| Tech Radar | ✅ | 1/4 fuentes | 2 | buscador + KDnuggets | Radar por cuadrantes real (plotly) |
| (Dormidos) | ❌ 15 | — | — | borrar legacy | Games + Notifications + Metrics |

## Roadmap global priorizado

### P0 — Esta semana (seguridad y datos falsos)
1. **Seguridad:** rotar passkey IPTorrents, mover a env vars, purgar `scavenging.json` (07/M1). Es lo único que no puede esperar.
2. **Fixes de datos falsos/rotos:** stat "Free Events" (08/VE1), "upcoming" sin cota inferior (08/VE2), formato `_fmt_score` Benchmarks (12/B1), postedAfter Product Hunt (03/K3), rutas relativas CWD (4chan/valencia/scavenging).
3. **Higiene:** eliminar `*_broken/_backup/_basic/_minimal` + legacy valencia + `github_trending/__init__` roto (14, 15/M6).

### P1 — Próximas 2–4 semanas (features muertas y fuentes ⭐⭐⭐ de bajo coste)
4. Búsquedas/filtros donde faltan: 3 subtabs News (01/M1), Knowledge Garden completo (03/M2), Tech Radar (13/M1), controles muertos de Ayudas (09/M2).
5. Fuentes nuevas de bajo esfuerzo y alto valor: Dev.to + StackExchange APIs (revive 2 subtabs), Hugging Face Learn + DeepLearning.AI real, Epic Free Games + r/FreeGameFindings, LiveBench + SWE-bench + OpenRouter, Semantic Scholar/OpenAlex para ArXiv, Ticketmaster Discovery para Valencia, BDNS API para Ayudas.
6. Revivals ⭐⭐⭐: Metrics (observabilidad), Notifications (cara del sistema de alertas), Games (pipeline ya pagado) — spec 14.

### P2 — 1–3 meses (experiencia)
7. Paginación/dedup/presets compartidos adoptados por todos los tabs (15/M1–M4); productor de tendencias para los badges 🔥 (15/M5).
8. Features estrella por tab: búsqueda global News, feed ICS Valencia, catálogo unificado Courses, radar por cuadrantes Tech Radar, clusters+BibTeX ArXiv, countdown deals/scavenging, wishlist Games.
9. Estado de usuario unificado + panel "Para ti" (15/T2, 14/3.6).

### P3 — Estratégico
10. Watchers con keywords en 5 dominios (courses/4chan/scavenging/ayudas/deals) + bandeja de notificaciones end-to-end + digest semanal.
11. Decisión arquitectónica dashboard↔API (15/T1) y catálogo único config-driven de fuentes.
12. Consolidaciones: News↔Tech Radar sin duplicados; travel/ecommerce disueltos en Scavenging/Deals.

## Patrones repetidos (atacar en bloque, no por tab)

- **Highlight `<mark>` literal** en 3 tabs → un helper `highlight_segments` (15/M1).
- **Tabla duplicada layout/callback** en 4+ tabs → `shared/table.py` (15/M1).
- **Caché `global`+`NameError`** en 3 tabs → `BaseRepository` + botón refresh (15/M2).
- **Caps ciegos** (50/100/150) aplicados antes de buscar → mover el límite a render y paginar (07/M3, 10, 11).
- **ETL registrado sin consumidor** (pluralsight, shoppy, entertainment, intelligence, museums, games…) → revival o baja (14).
- **Refactorizaciones a medias** (spanish_aid services/, arxiv services/, EnhancedArxivConfig) → completar o eliminar (09/M6, 10/M5).

## Cómo usar estos documentos

Cada spec es autónoma: diagnóstico con bugs identificados por severidad, fuentes adicionales con evaluación de esfuerzo/prioridad, mejoras concretas (M*) y funcionalidades nuevas con objetivo/UI/callbacks/criterios de aceptación/esfuerzo (F*). El orden sugerido de ejecución es el roadmap global; dentro de cada tab, los quick wins no requieren decisiones y las features F* pueden entrar en el `docs/TASK_BOARD.md` como tareas individuales (workflow task-board del repo).

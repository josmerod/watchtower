# Re-audit de las 15 tab-specs (T-059)

> 2026-08-28. Petición del usuario (FEEDBACK): "revisar una por una las
> tab-specs y refinar o añadir las fuentes y features que se mencionan".
> Estado por item M/F: ✅ hecho · ⏳ pendiente (tarea creada) · ❌ descartado
> (motivo). Fuente de verdad del histórico: `PROGRESS.md` (programa A–J,
> 2026-08-17/18) + tareas T-037..T-063.

## Resumen por spec

| Spec | Items hechos | Pendientes (→ tarea) | Descartados (motivo) |
| :-- | :-- | :-- | :-- |
| 01 News | M1 (ids dinámicos), M2*, M7 parcial, F1 global, F2 leído, F3 export, M8 trends-productor (batch F) | M4 items-per-page (→T-064), M5 toggle dedup en Top Tech (→T-064) | F4 dots — **eliminados a petición del usuario** (T-062); M3 presets de News — el patrón existe en Videos, sin adoptantes |
| 02 Shortcuts | M1–M4 (batch B), F1 palette (batch I) | — | **Toda la spec congelada**: tab oculto por decisión del usuario (T-060). F2 pins/F3 chips/F4 health-check no se construyen sobre un tab descartado |
| 03 Knowledge Garden | M1 devto/SO (T-025), M2 búsqueda (C), M5 caché repo (F), F1 global (G), F3 guardados (H), F4 dots | F2 vista tarjetas toggle (→backlog P3), M6 first_seen (→backlog) | M3 columnas Score/comentarios reddit — **imposible tras migración RSS** (los feeds no traen score; OAuth fuera de la regla keyless) |
| 04 Videos | M1 paginación (D), M3 badges (D), M5 sin-fecha (D), F2 orden (I), F1 visto/watch-later (T-046), M2 parcial | F3 modal embed (→T-065), F5 badge NUEVO + contador (→T-065), F4 vista admin canales (→backlog P3), M4 dropdown tema (→backlog) |
| 05 Courses | M2 colisión resuelta (T-025), M3 TTL (D), M4 paginación unificada (I), F1 catálogo unificado (I) | F3 CoursesWatcher "nuevo curso que matchea keywords" (→T-066) — **ahora viable: el bug de BaseWatcher.check() se arregló en T-049**; M5 columnas Coursera (→backlog); F2 mis-cursos (→backlog, requiere estado usuario ampliado) | M1 renombres — resuelto con docstrings honestos (T-025), renombrar ficheros rompería referencias |
| 06 4chan | M1 ruta (A), M2 fechas relativas (C), M3 boards compartidas (D), M4 empty-state (A) | — | — |
| 07 Scavenging | M1 passkey env (T-025), M2 ruta (A), M3 Store completo (C), M4 highlight real (C), M5 ventana fechas (A) | M6 outputs canónicos sin copias (→T-067, higiene de rutas) | — |
| 08 Valencia | M2 legacy eliminado (A), M3 ruta (A), M1 parcial (is_free honesto, venue/geo sin extraer) | ICS exportable de eventos (→T-068); venue/precio en modelo (→backlog, depende de lo que la fuente exponga) | M4 paginación Meetup — fuente deprecada/fuera de keyless estable |
| 09 Ayudas | M2 ámbito (A), M3 urgente (A), M4 last-updated (A), M5 stats cards (A) | M1 priorizar BDNS API con fechas/cuantías (→backlog P3) | M6 decisión extracción/classification — deuda técnica heredada, no bloqueante |
| 10 ArXiv | M1 query-split (D, 583 papers), M4 parcial | M2 fila expandible con abstract+cluster (→backlog P3); M5 integrar-o-eliminar services (→backlog deuda) | — |
| 11 Deals | M1 NameError+descripción+badges (C) | — | — |
| 12 Benchmarks | M-fix _fmt_score duplicado (A), filtros AA (C, inertes sin key) | LiveBench re-probe: verificar si hoy hay API/JSON estable (→T-069) | AA modalidades — API key (T-038 bloqueada) |
| 13 Tech Radar | M1 buscador, M2 normalizador, M3 consolidación (T-044), M4 orden/refresh (T-037), M5 snapshots (T-037); TR-F1 radar (H), TR-F3 feed unificado (T-041) | TR-F2 momentum (→T-048, ~09-16); TR-F4 mi-stack (→T-051) | — |
| 14 Dormidos | Games/Notifications/Metrics revividos (E) | — | — |
| 15 Infra | M1 tabla compartida, M2 caché TTL, M5 trends (F), M6 sys.path (G), M3 presets en Videos (J) | M3 FilterPresetsComponent genérico — refactor sin adoptantes (→backlog) | — |

## Fuentes mencionadas en specs, nunca cableadas (estado 2026-08-28)

| Fuente (spec) | Estado | Acción |
| :-- | :-- | :-- |
| DeepLearning.AI (05) | Diferida: JS-rendered | **Re-probe viable**: el contenedor monta `BROWSERLESS_ENDPOINT` — scrape vía browserless (→T-069 junto a LiveBench) |
| LiveBench (12) | Diferida: sin fichero estable | Re-probe de API pública (→T-069) |
| Semantic Scholar (10) / AA modalidades (12) / Ticketmaster (08) | API key | Excluidas por la regla keyless del usuario |
| Epic free games (07) | Endpoint comunitario muerto (NXDOMAIN) | Revisar si Epic publica endpoint nuevo (permanece en anti-backlog hasta señal) |
| ICS Valencia (08) | Diferida por "estado de usuario" | Re-evaluada: un export .ics descargable NO requiere estado de usuario → T-068 |

## Tareas derivadas de este re-audit

- **T-064** — News: items-per-page (25/50/100/250) + toggle "mostrar duplicados" en Top Tech (spec 01 M4+M5)
- **T-065** — Videos: modal de previsualización (embed nocookie) + badge "NUEVO" con contador desde última visita (spec 04 F3+F5)
- **T-066** — CoursesWatcher: eventos "nuevo curso de {proveedor} que matchea keywords" (spec 05 F3) — desbloqueado por el fix de BaseWatcher.check() (T-049)
- **T-067** — Scavenging: outputs canónicos, eliminar copias en data/scavenging/ (spec 07 M6)
- **T-068** — Valencia: export .ics de eventos (spec 08, pieza ICS re-evaluada)
- **T-069** — Investigación: LiveBench API + DeepLearning.AI vía browserless (specs 12/05)

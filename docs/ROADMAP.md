# Watchtower — Roadmap

> Horizonte priorizado de trabajo, derivado del valor entregado y los gaps
> observados (brainstorm 2026-08-27). El execution vive en `docs/TASK_BOARD.md`;
> el historial en `docs/TASK_BOARD_ARCHIVE.md`; el feedback del usuario en
> `docs/FEEDBACK.md`.

## 1. Dónde estamos (valor entregado, con evidencia)

| Área | Qué existe hoy | Evidencia de producción |
| :--- | :--- | :--- |
| **Fuentes tech** | Tech Radar con 12 fuentes keyless (AI, cloud, self-hosting, discussion, media premium) + feed unificado "Todos" | 426 artículos fusionados; filtros fuente/categoría validados |
| **Investigación** | ArXiv por categorías + 🔥 HF Trending (sucesor de PWC, upvotes + repos GitHub) | 50 papers/día, 33 con repo, 55 iconos GitHub renderizados |
| **Mercados** | Tab 📈 Markets (CoinGecko top-50, 24h/7d, cap, volumen, vs-ATH) | 50 monedas, Bitcoin fila 1, cards de resumen |
| **Comunidad** | Pulso reddit (r/SelfHosted + r/homelab + 37 subreddits vía RSS adaptativo) | 25 cards frescas tras migración anti-rate-limit |
| **UX personal** | Leído/no-leído (News), visto/ver-más-tarde (Videos), ⭐ guardados (KG), presets (Videos), palette Ctrl+K, CSV export | Persistencia localStorage verificada tras reload |
| **Observabilidad** | DataFreshnessWatcher + card 🩺 en Metrics, trends 🔥 cross-source, orquestador de 95+ ETLs cada 2h | 20 fresh / 0 stale / 1 critical flaggeado solo |
| **Calidad** | Suite 260 passed / 5 skipped, ruff + pre-commit blocking, CI con gates de lint | Verde continuo desde 2026-08-19 |

## 2. Gaps y oportunidades (brainstorm)

### A. Security intelligence — área nueva, cero cobertura hoy
El plataforma no tiene ninguna señal de seguridad. Para un homelab con servicios
expuestos (Unraid + reverse proxy), la conciencia de CVEs explotados activamente
es el gap de mayor valor personal. Fuentes keyless: **CISA KEV** (JSON oficial),
**BleepingComputer** (RSS), **The Hacker News** (RSS). → **T-050 (P1)**

### B. "Mi stack" release radar — personalización de alto valor
Los releases de GitHub exponen atom feeds sin key. Un ETL multi-feed (patrón
selfhosted) sobre una lista configurable del stack personal (n8n, Home Assistant,
Immich, Jellyfin, ASF…) da "novedades relativas a tu stack" — la feature más
personal posible. Futuro: cruzar releases con CISA (CVEs que te afectan). → **T-051 (P2)**

### C. Endurecimiento del pipeline de calidad
La suite está verde pero CI aún trata pytest como advisory (`continue-on-error`
de la era T-023). Hacerlo bloqueante es un quick win que protege todo lo
anterior. → **T-049 (P1)**

### D. Cerrar loops de observabilidad
El watcher graba eventos pero no crea alertas; Notifications tiene motor de
reglas sin productor automático. Conectarlos convierte "ver la card" en
"recibir la alerta". → **T-052 (P2)**

### E. Consistencia cross-tab de features probadas
⭐ guardados existe solo en KG; watch-later solo en Videos. `saved_items.py` es
genérico — extender a News global / Radar "Todos" / Markets es bajo esfuerzo y
unifica la experiencia. → **T-053 (P2)**

### F. De dashboard a ritual: digest semanal
Un compilado dominical (top términos 🔥, lo mejor del radar, movers de mercados)
convierte el dashboard en una revisión de 5 minutos en vez de un hábito de
vigilancia constante. Patrón ETL local-files ya probado (trends_etl). → **T-054 (P2)**

### G. Higiene y automatización a largo plazo
- Retención de snapshots (95 ETLs × cada 2h = crecimiento ilimitado). → **T-055**
- API pública de los datasets nuevos para n8n del usuario. → **T-056**
- Búsqueda global unificada cross-tab. → **T-057**

### H. Momentum analítico (TR-F2)
Diferido hasta ~2026-09-16: los snapshots M5 empezaron el 2026-08-19 y la media
móvil de 4 semanas necesita historia. La feature (Subiendo 🔺/Bajando 🔻 por
tecnología) ya tiene productor de datos corriendo. → **T-048**

## 3. Anti-backlog (evaluado y descartado, con motivo)

| Propuesta | Motivo del descarte |
| :--- | :--- |
| Google News tech RSS | Duplicaría la cobertura de las 12 fuentes del radar |
| Papers With Code | API muerta (302→HF); sustituido por HF Daily Papers (T-040) |
| Reddit OAuth | RSS + pacing adaptativo cubre la necesidad; OAuth añade complejidad sin beneficio |
| Twitter/X, LinkedIn, APIs financieras premium, Semantic Scholar, Ticketmaster | Requieren API key — contra la restricción keyless del usuario |
| DeepLearning.AI scrape | JS-rendered; requiere Playwright en producción |
| Epic free games | Endpoint comunitario muerto (NXDOMAIN global) |
| BridgeBench scrape | Migró a client-side rendering; re-evaluar tras V3 (T-047) |

## 4. Reglas de trabajo ( cómo seguimos )

1. **Keyless-first**: ninguna fuente nueva que exija API key salvo decisión
   explícita del usuario.
2. **Board discipline**: una tarea in-progress, cierre solo con evidencia
   (comando + output + validación visual en producción).
3. **Loop de feedback**: `docs/FEEDBACK.md` se lee al inicio de cada sesión y
   se triajea a tareas T-NNN.
4. **Loop de validación**: suite + ruff + pre-commit → deploy → health →
   ETL in-container → inspección visual (Playwright) → cierre en board.
5. **Compactación**: las filas done se archivan íntegras en
   `TASK_BOARD_ARCHIVE.md`; el board operativo se mantiene pequeño.

## 5. Horizontes

| Horizonte | Tareas |
| :--- | :--- |
| **Ahora (P1)** | T-049 CI bloqueante · T-050 Security keyless |
| **Próximo (P2)** | T-051 Mi stack · T-052 watcher→alerts · T-053 guardados multi-tab · T-054 digest · T-048 momentum (desde ~09-16) |
| **Después (P3)** | T-055 retención · T-056 API pública · T-057 búsqueda global · T-058 CrossRef (investigar) · T-047 BridgeBench V3 |
| **Bloqueado** | T-038 Artificial Analysis (requiere key del usuario) · T-003/T-010 (deuda mypy/excepciones, avance gradual) |

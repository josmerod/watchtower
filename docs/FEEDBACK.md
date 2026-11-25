# FEEDBACK — cajón de sastre del usuario

> Cuaderno de campo para apuntar **sobre la marcha** lo que veas usando el
> dashboard: bugs, cosas raras, ideas, fuentes que echas de menos, cosas que
> sobran. Sin formato obligatorio — escribe lo que quieras, como quieras.
>
> **Cómo se consume:** al inicio de cada sesión de trabajo, el agente lee este
> fichero, triea cada entrada (bug → tarea P1/P2, idea → propuesta, fuente →
> investigación keyless) y la convierte en filas del `docs/TASK_BOARD.md` con
> nuevo ID `T-NNN`. Después marca abajo lo ya triajeado con `[x]`.

---

## Entradas

<!-- Añade entradas con este patrón (o el que quieras):

- [ ] 2026-08-27 — En el tab X, cuando hago Y pasa Z. (tab: nombre)

Ejemplos:
- [ ] 2026-08-27 — El buscador del tab News no encuentra acentos ("gestion" vs "gestión").
- [ ] 2026-08-27 — Idea: poder ordenar el radar por categoría.
- [ ] 2026-08-27 — Fuente que echo de menos: feed RSS de X.
- [ ] 2026-08-27 — El tab Y tarda mucho en cargar.
-->

## 2026-11-25 — Oleada: mejora y ampliación (9 tareas, rama PR #31, sin push)

- [ ] **Oleada cerrada localmente** (verificación local verde: ruff, suite completa, pre-commit — evidencia en el changelog del board): **T-048** momentum 🔺/🔻 bajo el radar; **T-108** tests de BaseETL aislados de `data/` real; **T-110** shoppy (mock que escribía datos falsos) eliminado + `linkedin_learning` registrado; **T-111** watcher de frescura tras el pool; **T-112** kill del árbol de procesos multiplataforma; **T-113** minero Udemy importable sin sus 4 librerías; **T-116** pre-push selectivo por rutas; **T-118** archive de despliegue normalizado a LF. Parciales abiertas: **T-114** (intervalo ya honrado; falta decidir el destino de `src/launcher/main.py`), **T-119** (scripts muertos fuera; resto requiere decisiones).
- [ ] **Pendiente de decisión del usuario (las 2 P1)**: **T-106** backups — ¿volumen persistente `/app/backups` en Unraid antes de incluir `run_backup.py` en el archive? **T-107** claves — ¿montar `.env` read-only en `/app/.env` o `--env-file`? (política actual: keyless-first).
- [ ] **Checklist de validación en prod tras desplegar** (lo que CI no puede ver): (1) panel 🔺/🔻 bajo el radar con datos frescos — "esta semana" se ancla a la snapshot más nueva, se auto-corrige al correr los ETLs; (2) primer run de `linkedin_learning_etl` (Playwright, hasta 50 páginas la 1ª vez, 5 después); (3) el log del orquestador muestra `Running data freshness watcher (after the pool)` DESPUÉS del resumen del pool; (4) el archive desplegado ya no lleva CRLF (comparar md5 contra el commit, T-118); (5) supervisor loguea `ETL Scheduler started. Interval: 7200 s.` y `WATCHTOWER_ETL_INTERVAL` ya tiene efecto.
- [ ] **Nota T-116**: un push que SOLO borre ficheros de código no dispara la suite (limitación conocida del filtro `files` de pre-commit); los push docs/board sí saltan el gate de ~8 min.
- [ ] **Nota T-114**: la docs (ADVANCED_DEPLOYMENT_GUIDE) prometían default 3600 s pero el scheduler dormía 7200 s fijos; ahora honra la variable con default 7200 (cadencia actual, sin sorpresa en prod).
- [ ] **Para T-119**: `scripts/install_watchtower.py` recomienda `deploy_windows.bat`/`deploy_mac.sh`/`deploy_linux.sh`, que ya no existen en el repo. Candidato a podar o reescribir.

## Triajeado (archivo histórico)

<!-- El agente mueve aquí las entradas ya convertidas a tareas, con su ID -->

- [x] 2026-08-27 — Estaría bien revisar una por una las tab-specs que están en docs y refinar o añadir las fuentes y features que se mencionan → **T-059** (re-audit sistemático de las 15 specs)
- [x] 2026-08-27 — Descartaría la tab de shortcuts, por el momento → **T-060** (ocultada del nav de forma reversible; palette Ctrl+K intacta)
- [x] 2026-08-27 — A nivel de news, la tab de búsqueda global la pondría al final o algo, por si acaso → **T-061** (🔎 Global pasa a último subtab; el primero es Top Tech)
- [x] 2026-08-27 — Los indicadores de estado de las news pueden aportar valor, pero siempre están en gris, creo que ya con el indicador de estado de arriba está bien → **T-062** (dots de News eliminados; el estado vive en la card 🩺 de Metrics)
- [x] 2026-08-27 — El summary de estado que está arriba del todo debería ser colapsable, no hace falta verlo todo el rato → **T-063** (botón "Estado del sistema", colapsado por defecto)

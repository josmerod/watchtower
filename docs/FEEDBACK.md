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

## 2026-11-26 — T-107: las claves llegan al contenedor (misma rama, PR #31)

> Notas del agente para tu revisión. Cada punto ya está triajeado (tarea en el board o decisión tuya anotada en `docs/ROADMAP.md`), por eso van marcados: una casilla vacía aquí significa "pendiente de triajear".

- [x] **Tu decisión del 2026-11-26: pasar las claves al contenedor.** Hecho en `deployment/deploy.py`: una lista cerrada de nombres (`CONTAINER_ENV_KEYS`) viaja a un fichero solo-legible-por-root en el servidor y de ahí al contenedor con `--env-file`. Nada más de `.env` viaja: las credenciales `UNRAID_*` se quedan en tu máquina. Si el despliegue falla y hay que retroceder, el rollback se reintenta sin las claves antes que dejarte sin contenedor. **En producción desde el despliegue de las 14:44 CET** (rama `main`, PR #31 mergeado): probado en el servidor con variables ficticias en un contenedor desechable; en el despliegue real no había nada que pasar.
- [x] **Hoy no hay ninguna clave que pasar.** `.env` de este clone solo define `UNRAID_HOST`, `UNRAID_USER` y `UNRAID_PASSWORD` (comprobado por nombres, sin leer valores). El contenedor seguirá sin claves hasta que añadas las que quieras en `.env` bajo los nombres de la sección *Keys and variables the ETLs read* de `.env.example` y vuelvas a desplegar. Las que hoy se quedan cortas sin clave: GitHub (límite anónimo), Product Hunt (cae a RSS), NVD, Artificial Analysis (401 — T-038), Replicate, IsThereAnyDeal, NewsAPI, RapidAPI y los RSS de IPTorrents.
- [x] **Hallazgo en el servidor (no tocado):** en `/mnt/user/appdata/watchtower/`, junto a `data` y `logs`, hay una copia del repo de la época compose (abril–junio 2026) y **un `.env` de root con modo 644 de mayo**, legible por cualquier usuario del servidor o del share. Nada lo usa. → T-125: es tu decisión (borrar es irreversible); conviene rotar lo que siga vivo.
- [x] **Corrección a lo que te conté el 25:** registré `linkedin_learning_etl` en el ciclo diciendo que alimentaba el tab Learning, y no es cierto — nada lee su salida. Lo he retirado del ciclo (el test fija ahora que no está) y abierto T-124 para cablearlo bien: primero el consumidor, luego el registro.
- [x] **Validación en prod tras el despliegue de las 14:44 CET — todo en verde** (lo que CI no puede ver): (1) panel 🔺/🔻 bajo el radar visible en la URL pública, con datos y sin errores de consola; (3) primer ciclo tras el despliegue (14:44:08 → 15:30:55): `Running data freshness watcher (after the pool)` después del último script del pool y antes del resumen y de la poda de snapshots, y `Successful: 108 \| Failed: 0` en 2799 s, sin ningún fallo ni aviso; (4) md5 de 8 ficheros desplegados = commit; (5) `ETL Scheduler started. Interval: 7200 s.`; (6) nombres de variable del contenedor sin cambios: ningún `UNRAID_*` y ninguna clave (no había nada que pasar). Al acabar el ciclo la API se reinició sola y `/health` responde `ok`. El punto (2) del checklist del 25 (primer run de LinkedIn Learning) queda anulado por la corrección de arriba. El ciclo lo marcan dos ETLs largos: `goldigging_youtube_posts` (2705 s) y `reddit_unified` (2285 s).

## 2026-11-25 — Oleada: mejora y ampliación (9 tareas, rama PR #31, sin push)

> Desplegada y validada en prod el 2026-11-26 (ver la sección de arriba y el changelog del board).

- [x] **Oleada cerrada localmente** (verificación local verde: ruff, suite completa, pre-commit — evidencia en el changelog del board): **T-048** momentum 🔺/🔻 bajo el radar; **T-108** tests de BaseETL aislados de `data/` real; **T-110** shoppy (mock que escribía datos falsos) eliminado + `linkedin_learning` registrado *(corregido el 26: retirado, ver T-124)*; **T-111** watcher de frescura tras el pool; **T-112** kill del árbol de procesos multiplataforma; **T-113** minero Udemy importable sin sus 4 librerías; **T-116** pre-push selectivo por rutas; **T-118** archive de despliegue normalizado a LF. Parciales abiertas: **T-114** (intervalo ya honrado; falta decidir el destino de `src/launcher/main.py`), **T-119** (scripts muertos fuera; resto requiere decisiones).
- [x] **Pendiente de decisión del usuario (las 2 P1)**: **T-106** backups — ¿volumen persistente `/app/backups` en Unraid antes de incluir `run_backup.py` en el archive? **T-107** claves — decidido el 26 (ver arriba).
- [x] **Nota T-116**: un push que SOLO borre ficheros de código no dispara la suite (limitación conocida del filtro `files` de pre-commit); los push docs/board sí saltan el gate de ~8 min.
- [x] **Nota T-114**: la docs (ADVANCED_DEPLOYMENT_GUIDE) prometían default 3600 s pero el scheduler dormía 7200 s fijos; ahora honra la variable con default 7200 (cadencia actual, sin sorpresa en prod).
- [x] **Para T-119**: `scripts/install_watchtower.py` recomienda `deploy_windows.bat`/`deploy_mac.sh`/`deploy_linux.sh`, que ya no existen en el repo. Candidato a podar o reescribir.

## Triajeado (archivo histórico)

<!-- El agente mueve aquí las entradas ya convertidas a tareas, con su ID -->

- [x] 2026-08-27 — Estaría bien revisar una por una las tab-specs que están en docs y refinar o añadir las fuentes y features que se mencionan → **T-059** (re-audit sistemático de las 15 specs)
- [x] 2026-08-27 — Descartaría la tab de shortcuts, por el momento → **T-060** (ocultada del nav de forma reversible; palette Ctrl+K intacta)
- [x] 2026-08-27 — A nivel de news, la tab de búsqueda global la pondría al final o algo, por si acaso → **T-061** (🔎 Global pasa a último subtab; el primero es Top Tech)
- [x] 2026-08-27 — Los indicadores de estado de las news pueden aportar valor, pero siempre están en gris, creo que ya con el indicador de estado de arriba está bien → **T-062** (dots de News eliminados; el estado vive en la card 🩺 de Metrics)
- [x] 2026-08-27 — El summary de estado que está arriba del todo debería ser colapsable, no hace falta verlo todo el rato → **T-063** (botón "Estado del sistema", colapsado por defecto)

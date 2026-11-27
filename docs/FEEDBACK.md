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

## 2026-11-27 (tarde) — Cursos en español e inglés, fechas de Valencia y tres arreglos visuales en producción

> Notas del agente para tu revisión. Cada punto ya está triajeado (tarea en el board), por eso van marcados.

- [x] **Desplegado dos veces más, entre ciclos y con exit 0:** `main` `e049c40` a las 13:07 CET (PR #37) y `main` `defdfc3` a las 14:54 CET (PR #38). El ciclo tras el segundo (14:54 → 15:41) terminó con `Successful: 102 \| Failed: 0`, sin un solo aviso en el log; lo mismo el del primero (13:07 → 13:53).
- [x] **Lo que se usa ya en producción:** AWS Skill Builder y GCP Skills Boost con filtro de idioma Español / English (T-146, T-147): 55 cursos de AWS (30 en español, 25 en inglés) y 715 de GCP (137 con versión en español). Valencia Events con una fecha legible para cada fuente («vie 27/11/2026 · 19:30») y ordenada por inicio (T-178). La tarjeta **ETL Sources** de Ayudas pasa de «—» a 3 (T-183): su ETL nunca había escrito el fichero de estadísticas que lee la pestaña.
- [x] **Tres fallos que no estaban en la libreta, vistos al validar en el navegador, ya arreglados:** (1) **todos los menús desplegables del dashboard abrían fuera de pantalla**, en Learning, Videos, Ayudas, Tech Radar y News, y la página se desplazaba sola ~450 px al abrir uno (T-181); (2) **en el móvil la barra de subpestañas salía vacía** en News, Knowledge Garden, Learning, ArXiv, Tech Radar, Games, Scavenging y Valencia Events: no se podía cambiar de subtab desde un teléfono (T-182); (3) **los botones primarios eran ilegibles**, oscuro sobre oscuro: «Open API» de la cabecera, «Create Alert Rule» y «Search» de Ayudas (T-184). El (2) solo pasa por debajo de 768 px de ancho.
- [x] **Dos efectos previstos del filtro de idioma:** GCP Skills Boost marcó **529 cursos como nuevos una sola vez** (sus URLs cambiaron al quitarles un parámetro de ranking) y **los 15 cursos en coreano de AWS desaparecieron** del catálogo.
- [x] **Un test ya no escribe en tu `data/` local** (T-161). Los 25 resúmenes que dejaron ejecuciones antiguas en `data/spanish_public_aid/output/` de tu máquina siguen ahí; no he tocado nada de `data/`. Se pueden borrar a mano si quieres.
- [x] **Sigue en marcha sin esperar respuesta:** backups en producción (T-106, en ensayo en el servidor), Indie Hackers por RSS (T-153), las fuentes de News muertas (T-176), los callbacks sin clic (T-162), columnas de Games (T-155), enlaces de Udemy (T-156), texto plano en los resúmenes (T-164) y una nueva: la columna FIRST DETECTED de GCP enseña la hora en UTC (T-185).

## 2026-11-27 — Libreta: primera oleada en producción, segunda en marcha

> Notas del agente para tu revisión. Cada punto ya está triajeado (tarea en el board), por eso van marcados.

- [x] **Tu libreta está entera en el board** (36 filas el 26: T-126…T-161) y la primera oleada está desplegada: dos despliegues desde `main` el 27, a las 01:36 CET (PR #32, `b928fa1`) y a las 10:49 CET (PR #33, #34 y #35; `b1841c2`), los dos entre ciclos y con exit 0. Lo que salió de tu libreta y ya se usa en producción: fuera freeCodeCamp, Kagi USA y Kagi World de News (T-126); fuera Reddit AI/ML, Programming, DevOps y All, Git Trends, Stack Overflow y TrendShift (T-127); fuera freeCodeCamp, HF Learn y DeepLearning.AI de Learning (T-128); Lobsters en Knowledge Garden (T-130); Knowledge Garden abre con 3 peticiones en vez de 62 (T-136); los eventos de hoy entran en «Upcoming» de Valencia Events (T-160); Humble Books enseña sus 451 libros, no 15 (T-149); Audible estrena ventana móvil, 500 novedades (450 títulos distintos) y paginación (T-150); MS Learn en dos subtabs, Certificaciones y Applied Skills (T-144); las insignias de Scavenging vuelven a leerse (T-171). Todo comprobado en el navegador de la URL pública, sin errores de consola, y con `Successful: 102 | Failed: 0` en los ciclos tras el primer despliegue.
- [x] **Tres arreglos que no estaban en la libreta**, encontrados al validar: News abría con 18 peticiones y buscaba en cada tecla → 3 peticiones y una búsqueda por pausa (T-163); ArXiv se quedaba colgado al buscar (T-172); el ▶ de un vídeo no abría el reproductor (T-173).
- [x] **Corrección a lo que te conté:** dije que Scavenging tardaba ~15 s en abrir en producción. Era un error de mi medición, no del dashboard. Medido con el reloj de la propia página: las 18 pestañas pintan su contenido entre 0,05 y 0,73 s después del clic (Scavenging, la más lenta, a 0,73 s; la primera tabla al cargar la página, a 0,7 s). Lo que sí es cierto y sigue en el board: Scavenging baja **3,9 MB en una sola respuesta**, pesado en móvil (T-170).
- [x] **Hallazgos nuevos, ya en el board:** **T-176 (P1)** tres fuentes de News llevan meses sin publicar y el ciclo las daba por buenas: Ben's Bites (abril), Indie Hackers (mayo, T-153) y **FutureTools, cuyo feed paró en mayo de 2024** — importa para «renombrar a FutureTools»: hoy no queda ninguna fuente viva detrás de ese nombre (T-129). **T-174 (P2)** el ciclo dura ≈47 min y lo marcan dos ETLs: goldigging de YouTube (≈45 min) y Reddit (≈38 min). **T-177** Learning abre con 7 peticiones, 6 en vacío. **T-179** Tech Radar renderiza dos veces (617 + 608 KiB). **T-178** Valencia Events muestra fechas ISO en bruto y sin ordenar. **T-180** dos paradas de ≈4,3 s del dashboard a las 11:20, sin causa asignada. **T-175** tres errores 500 del dashboard el 26 a las 22:49. Con datos de producción: **T-146** AWS Skill Builder solo trae la primera página de Class Central, con 15 títulos en coreano (hay ≈7.464 cursos en inglés y ≈1.134 en español); **T-147** GCP Skills Boost solo trae 200 de 715 cursos y 165 de esos 200 comparten URL por un parámetro de ranking; **T-120** Dependabot marca 134 alertas (8 críticas, 64 altas).
- [x] **Lo que sigo haciendo sin esperar respuesta:** AWS Skill Builder y GCP Skills Boost con filtro es/en (T-146, T-147), backups en producción (T-106), Indie Hackers por RSS (T-153), columnas de Games (T-155), enlaces de Udemy (T-156), un test que escribe en `data/` real (T-161) y texto plano en los resúmenes (T-164).
- [x] **Dudas de la libreta que frenan tareas** (te las pregunto en tandas de 4; si no respondes, sigo con lo demás): dónde vive y cómo se llama la sección de contenidos (T-131) y qué es «media»; Product Hunt, ¿una sección «Shopping» nueva o renombrar Scavenging a «Shopping + Scavenging»? (T-132, T-148); qué significa el filtro por defecto de vídeos «sin z, zz, zzz» (T-138); si «STL» es impresión 3D (T-152); si tienes cuenta en ABTorrents, porque el feed necesita una passkey (T-135); qué le faltaba al formato de Humble Books (T-149) y si Audible va solo en español o también en inglés (T-150).
- [x] **Pendiente de tu decisión, no bloquea:** **T-106** backups — lo montaré así salvo que digas lo contrario: carpeta `backups` junto a `data` en el disco de appdata, una copia al día de `data` y `logs`, 7 conservadas. Aviso: es el mismo disco que los datos, no protege de un fallo del disco; para eso haría falta sacar copias fuera del servidor. **T-166** hay 47 registros marcados como guardados en producción que tú no marcaste; no los toco sin tu visto. **T-125** la copia heredada y el `.env` legible por todos en el servidor (te lo conté el 26).

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

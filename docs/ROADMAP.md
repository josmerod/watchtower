# Watchtower — Roadmap

> Horizonte priorizado de trabajo, derivado del valor entregado y de los gaps
> observados. La ejecución vive en `docs/TASK_BOARD.md`; el historial en
> `docs/TASK_BOARD_ARCHIVE.md`; el feedback del usuario en `docs/FEEDBACK.md`.
>
> Estado al 2026-11-26. Las cifras de la primera sección se midieron el
> 2026-11-24 contra la API del contenedor recién desplegado, salvo las que
> llevan su propia fecha; no se heredan de versiones anteriores de este
> documento.

## 1. Dónde estamos (valor entregado, con evidencia)

| Área | Qué existe hoy | Evidencia (2026-11-24) |
| :--- | :--- | :--- |
| **Pipeline** | 101 entradas en el orquestador (98 ETLs, 2 watchers, 1 miner) más el watcher de frescura tras el pool: 102 scripts por ciclo desde la limpieza de fuentes del 2026-11-27 (T-126, T-127, T-128; hasta desplegar, producción sigue en 108), cada 2 horas, 4 workers | Primer ciclo tras el despliegue del 2026-11-26 (108 scripts): `Found 107 ETL scripts to run, plus the data-freshness watcher after the pool.`, watcher de frescura tras el pool y antes del resumen, `Successful: 108 \| Failed: 0` en 2799 s (14:44→15:30 CET), sin fallos ni avisos; su duración la marcan dos ETLs largos (`goldigging_youtube_posts` 2705 s, `reddit_unified` 2285 s). El del 2026-11-24 (109 scripts entonces) fue `109 \| 0` en 2813 s y el siguiente arrancó a las 2 h |
| **Fuentes tech** | Tech Radar de 23 fuentes y feed unificado «Todas» | `/api/v1/radar` → JSON 200; `/api/v1/news` → 1087 items |
| **Investigación** | ArXiv por categorías, HF Daily Papers con citas (OpenAlex, CrossRef de respaldo), tab de benchmarks | `/api/v1/benchmarks` → 146 modelos; BridgeBench y Artificial Analysis siguen sin datos propios (T-047, T-038) |
| **Mercados** | Tab 📈 Markets con las 50 primeras monedas de CoinGecko y cartera local | 50 monedas; «💼 Mi cartera» abre su formulario |
| **Comunidad** | Pulso reddit por RSS, Knowledge Garden | `/api/v1/knowledge-garden` → JSON 200; 789 filas con fecha, chip «21 NUEVO» |
| **Seguridad** | CISA KEV, 3 feeds RSS, advisories OSV del propio stack y EOL del stack (endoflife.date) | 130 items (60 KEV, 70 noticias), 33 advisories OSV de severidad alta o crítica |
| **Territorio** | Agenda de Valencia y ayudas públicas (BDNS, GVA, DOGV y otros) | `/api/v1/valencia/events` → 32 eventos |
| **Juegos y cursos** | Ofertas, bundles y reseñas; cursos de varios proveedores | `/api/v1/games` → 206 items |
| **API** | FastAPI con 20 rutas GET (19 bajo `/api/v1` y `/health`), documentación in-app | Las 11 rutas que lista `/docs` devuelven JSON 200 contra el contenedor; la API pública responde en su propio hostname |
| **Observabilidad** | DataFreshnessWatcher + card 🩺 en Metrics; retención de snapshots (`keep_last=30`) | 20 fuentes frescas, 0 obsoletas, 3 críticas |
| **Calidad** | Suite de 1253 tests, Ruff, mypy, hooks de commit y push, CI que construye la imagen desplegada | `1246 passed, 7 skipped` en local (2026-11-26, 7:41, re-ejecutada sobre el código desplegado); `1244 passed, 9 skipped` en la CI de Linux; `Success: no issues found in 242 source files`; CI y `Docker Build` en verde sobre `main` (`b3882e6`) |
| **Despliegue** | `deploy.py` con etiqueta `previous`, espera de salud, rollback y reenvío de claves por lista cerrada; imagen sobre `python:3.11-slim` + uv fijado; archivo normalizado a LF | Contenedor `healthy`, `latest` y `previous` disponibles, rollback probado con SSH falso. El 2026-11-26, desde `main` (`b3882e6`): `healthy` 12 s tras el cambio, md5 de 8 ficheros desplegados igual al commit y primer ciclo `Successful: 108 \| Failed: 0` en 2799 s |

Dos cosas de esa columna conviene no olvidarlas al leerla: no hay backups en
producción (T-106), y ninguna clave API llega al contenedor porque ninguna está
configurada — `deploy.py` reenvía desde el 2026-11-26 las que haya en `.env`,
y solo esas (T-107, cerrada).

## 2. Gaps y oportunidades

Los IDs remiten a `docs/TASK_BOARD.md`. El orden dentro de cada bloque es el de
prioridad del board.

### A. Producción sin red de seguridad

El despliegue funciona, pero a su alrededor quedan tres huecos verificados el
2026-11-24. `run_backup.py` no viaja al contenedor, así que no hay backups
desde el 2026-09-10. → **T-106 (P1)**. Ninguna clave API llega al contenedor:
los ETLs que la necesitan corren sin ella. Es una decisión, no un fallo; desde
el 2026-11-26 `deploy.py` reenvía las claves que haya en `.env` (lista cerrada
`CONTAINER_ENV_KEYS` + `--env-file`), y hoy no hay ninguna configurada.
→ **T-107 (P1, cerrada 2026-11-26)**. Hay dos recetas de imagen que compilan distinto y `deploy.py`
nunca refresca la etiqueta base del servidor. → **T-109 (P2)**. Dos cosas
menores: la capa de Playwright se reconstruye en cada despliegue porque está
después de `COPY . .`. → **T-123 (P3)**. Y el ensayo que destapó tres fallos
de imagen invisibles para CI vive fuera del repo. → **T-117 (P3)**.

### B. "Éxito" no significa "datos escritos"

El orquestador da por bueno un script que sale con 0 aunque no haya hecho nada:
`shoppy_etl.py` está registrado sin bloque `__main__`. Y no se sabe qué escribió
cada uno de los 109 en el último ciclo. → **T-110 (P2, cerrada 2026-11-25)**.
El watcher de frescura está marcado "MUST BE LAST" pero compite en el mismo
pool. → **T-111 (P2, cerrada 2026-11-25)**. El minero de Udemy importa cuatro
librerías que no están en el lock. → **T-113 (P3, cerrada 2026-11-25)**. Hay
dos planificadores con listas distintas (44 y 102 scripts). → **T-114 (P3)**.
Un ETL sin consumidor no entra al ciclo: `linkedin_learning_etl.py` espera a
que algo lea su salida. → **T-124 (P2, abierta 2026-11-26)**.

### C. Calidad que se cree a sí misma

La suite está verde, pero `test_base_etl.py` escribe en `data/` real y borra
circuit breakers. → **T-108 (P2, cerrada 2026-11-25)**. El hook de push corre
la suite entera (≈8 min por push) y, por SSH, el push muere al terminar si la
sesión no lleva keepalive. → **T-116 (P3, cerrada 2026-11-25)**. GitHub avisa de
133 vulnerabilidades en `main` (recontado el 2026-11-26 tras el merge del
PR #31: 8 críticas, 64 altas; 13 paquetes, todas con parche), y el job de
seguridad de Dependabot termina sin abrir PR porque cree que ya hay uno; los
bumps de T-103 cubren parte. → **T-120 (P2)**. El timeout del orquestador no mata al hijo en Windows.
→ **T-112 (P3, cerrada 2026-11-25)**.

### D. Seguridad e higiene

Los orígenes CORS por defecto contienen direcciones de LAN en un fichero de un
repo público. → **T-115 (P2)**. Sin `LICENSE`, `CODE_OF_CONDUCT` ni plantilla
de PR; scripts y ramas que ya no sirven. → **T-119 (P3)**. En el servidor, la
carpeta de la app guarda aún una copia del repo de la época compose y un `.env`
legible por todos desde mayo. → **T-125 (P2, abierta 2026-11-26)**.

### E. Producto

Momentum por tecnología (TR-F2): la historia de 4 semanas ya existe.
→ **T-048 (P2, cerrada 2026-11-25)**. BridgeBench vía browserless: el servicio vuelve a responder.
→ **T-047 (P3)**. La paleta Ctrl+K no busca en la URL pública porque la API
vive en otro hostname. → **T-121 (P3)**.

**Libreta del usuario (triajeada el 2026-11-26, T-126…T-161).** Lo que hay que
sacar del camino: fuentes de baja calidad en News, Knowledge Garden y Learning
y una sección de contenidos mal ubicada. → **T-126…T-131 (P1)**. Lo que tarda:
Knowledge Garden pinta sus 18 subtabs a la vez (606 KiB por respuesta, 492
lecturas de `saved_items.json` por render). → **T-136 (P1)**. Lo que está roto
y no se veía: los eventos de hoy no salen en Valencia Events (T-160), Indie
Hackers lee una API de Reddit que da 403 (T-153), las columnas de precio de
Games salen en «N/A» (T-155), Humble Books pierde todos los libros de un
bundle salvo el primero (T-149), Audible tiene una ventana de fechas caducada
(T-150) y el ETL de ayudas no devuelve ni un registro de Burjassot (T-142).
Todo P1 salvo T-142, T-153 y T-155. Lo que falta: cine, portales de
transparencia, ofertas de videojuegos y gift cards, watch de precios, XTeink,
trendshift.io, skills y agentes de Watchtower (T-132…T-152, P2/P3).

## 3. Anti-backlog (evaluado y descartado, con motivo)

| Propuesta | Motivo del descarte |
| :--- | :--- |
| Google News tech RSS | Duplicaría la cobertura de las fuentes del radar |
| Papers With Code | API muerta (302 → HF); sustituido por HF Daily Papers (T-040) |
| Reddit OAuth | RSS + pacing adaptativo cubre la necesidad; OAuth añade complejidad sin beneficio |
| Twitter/X, LinkedIn, APIs financieras premium, Semantic Scholar, Ticketmaster | Requieren API key — contra la restricción keyless del usuario |
| DeepLearning.AI scrape con Playwright | Implementado vía sitemap estático (T-069), sin navegador; toda la fuente se retiró de Learning el 2026-11-26 (T-128) |
| Epic free games | Endpoint comunitario muerto (NXDOMAIN global) |
| BridgeBench scrape estático | Migró a client-side rendering; solo queda la vía browserless (T-047) |
| Artificial Analysis sin clave | La API v2 responde 401 sin una clave de pago; bloqueado hasta que el usuario aporte una (T-038) |
| `ghcr.io/astral-sh/uv:python3.11-*` como imagen base | El registro no la reconstruye con cada parche de Python: el 2026-11-24 seguía en 3.11.14 sobre Debian 12. Base `python:3.11-slim` + uv fijado (T-099) |
| Incluir `run_backup.py` sin volumen de backups | Comprimiría ~3 GB de datos en la capa del contenedor; primero el volumen (T-106) |

## 4. Reglas de trabajo (cómo seguimos)

1. **Keyless-first**: ninguna fuente nueva que exija API key salvo decisión
   explícita del usuario.
2. **Board discipline**: una tarea in-progress, cierre solo con evidencia
   (comando + output + validación visual en producción).
3. **Loop de feedback**: `docs/FEEDBACK.md` se lee al inicio de cada sesión y
   se triajea a tareas T-NNN.
4. **Loop de validación**: suite + ruff + pre-commit → CI verde → deploy →
   health → ciclo de ETLs en el contenedor → inspección visual (Playwright) →
   cierre en board.
5. **Ensayar antes de desplegar** lo que toque `deployment/Dockerfile`,
   `pyproject.toml` o `uv.lock`: construir el archivo en el servidor con una
   etiqueta desechable. "CI lo construyó" no prueba que el servidor pueda.
6. **Comprobar el cuerpo, no solo el código HTTP.** En la URL pública del
   dashboard, `/api/v1/*` devuelve 200 con HTML; la API pública es otro
   hostname. Verificar JSON contra el contenedor o contra ese hostname.
7. **Compactación**: las filas done se archivan íntegras en
   `TASK_BOARD_ARCHIVE.md`; el changelog del board conserva dos meses.

## 5. Horizontes

> Refrescado 2026-11-26. Fuente de ejecución: `docs/TASK_BOARD.md`.

| Horizonte | Tareas |
| :--- | :-- |
| **Ahora (P1)** | **Libreta:** T-126 · T-127 · T-128 limpieza de News, KG y Learning · T-129 FutureTools · T-130 Lobsters a KG · T-131 sección de contenidos · T-136 rendimiento de KG · T-138 canales de YouTube · T-144 MS Learn en dos · T-149 Humble Books · T-150 Audible · T-160 eventos de hoy. **Anteriores:** T-106 backups en prod · T-115 CORS sin direcciones de LAN |
| **Después (P2)** | **Libreta:** T-132 · T-133 · T-134 · T-135 · T-137 · T-139 · T-140 · T-141 · T-142 · T-143 · T-145 · T-146 · T-147 · T-148 · T-151. **Hallazgos del mapeo:** T-153 · T-154 · T-155 · T-156 · T-161. **Anteriores:** T-109 receta de imagen única · T-120 alerts de Dependabot · T-124 LinkedIn Learning con consumidor · T-125 copia heredada y `.env` viejo en el servidor |
| **Más adelante (P3)** | T-047 BridgeBench vía browserless · T-096 convención de logging · T-114 dos planificadores · T-117 ensayo en el repo · T-119 higiene · T-121 paleta pública · T-123 capa de Playwright · T-152 STL · T-157 Scavenging sin datos · T-158 docs caducadas · T-159 recortes de Learning |
| **Bloqueado** | T-038 Artificial Analysis (clave del usuario) |

Cerradas entre el 2026-11-24 y el 2026-11-26: T-048, T-107, T-108, T-110,
T-111, T-112, T-113, T-116 y T-118. Sus filas íntegras están en
`docs/TASK_BOARD_ARCHIVE.md`.

Fuera del board y pendiente del usuario: añadir a `.env` las claves que quiera
(hoy no hay ninguna) y redesplegar para que lleguen al contenedor; decidir sobre
T-106 (volumen de backups) y T-125 (limpiar la carpeta de la app en el
servidor).

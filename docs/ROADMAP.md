# Watchtower — Roadmap

> Horizonte priorizado de trabajo, derivado del valor entregado y de los gaps
> observados. La ejecución vive en `docs/TASK_BOARD.md`; el historial en
> `docs/TASK_BOARD_ARCHIVE.md`; el feedback del usuario en `docs/FEEDBACK.md`.
>
> Estado al 2026-11-27 (filas Pipeline, Calidad y Despliegue actualizadas ese
> día). Las cifras de la primera sección se midieron el 2026-11-24 contra la API
> del contenedor recién desplegado, salvo las que llevan su propia fecha; no se
> heredan de versiones anteriores de este documento.

## 1. Dónde estamos (valor entregado, con evidencia)

| Área | Qué existe hoy | Evidencia (2026-11-24) |
| :--- | :--- | :--- |
| **Pipeline** | 101 entradas en el orquestador (98 ETLs, 2 watchers, 1 miner) más el watcher de frescura tras el pool: **102 scripts por ciclo** desde la limpieza de fuentes del 2026-11-27 (T-126, T-127, T-128), en producción desde el despliegue de esa noche; cada 2 horas, 4 workers | Tras el despliegue del 2026-11-27 a las 01:36 CET (`b928fa1`): `Successful: 102 \| Failed: 0` en el primer ciclo y en los tres siguientes (≈47 min cada uno), y también en el primero tras el segundo despliegue del día (10:49→11:36 CET); la duración la marcan dos ETLs largos (`goldigging_youtube_posts` 2708 s, `reddit_unified` 2284 s → T-174). Los anteriores: `108 \| 0` en 2799 s (2026-11-26) y `109 \| 0` en 2813 s (2026-11-24), en ambos con el watcher de frescura tras el pool y antes del resumen |
| **Fuentes tech** | Tech Radar de 23 fuentes y feed unificado «Todas» | `/api/v1/radar` → JSON 200; `/api/v1/news` → 1087 items |
| **Investigación** | ArXiv por categorías, HF Daily Papers con citas (OpenAlex, CrossRef de respaldo), tab de benchmarks | `/api/v1/benchmarks` → 146 modelos; BridgeBench y Artificial Analysis siguen sin datos propios (T-047, T-038) |
| **Mercados** | Tab 📈 Markets con las 50 primeras monedas de CoinGecko y cartera local | 50 monedas; «💼 Mi cartera» abre su formulario |
| **Comunidad** | Pulso reddit por RSS, Knowledge Garden | `/api/v1/knowledge-garden` → JSON 200; 789 filas con fecha, chip «21 NUEVO». Desde T-136 (cerrada 2026-11-27) la pestaña abre con 3 peticiones y 169 KiB (antes 62 peticiones) y pinta una subtab por clic |
| **Seguridad** | CISA KEV, 3 feeds RSS, advisories OSV del propio stack y EOL del stack (endoflife.date) | 130 items (60 KEV, 70 noticias), 33 advisories OSV de severidad alta o crítica |
| **Territorio** | Agenda de Valencia y ayudas públicas (BDNS, GVA, DOGV y otros) | `/api/v1/valencia/events` → 32 eventos |
| **Juegos y cursos** | Ofertas, bundles y reseñas; cursos de varios proveedores | `/api/v1/games` → 206 items |
| **API** | FastAPI con 20 rutas GET (19 bajo `/api/v1` y `/health`), documentación in-app | Las 11 rutas que lista `/docs` devuelven JSON 200 contra el contenedor; la API pública responde en su propio hostname |
| **Observabilidad** | DataFreshnessWatcher + card 🩺 en Metrics; retención de snapshots (`keep_last=30`) | 20 fuentes frescas, 0 obsoletas, 3 críticas |
| **Calidad** | Suite de 1438 tests, Ruff, mypy, hooks de commit y push, CI que construye la imagen desplegada | `1431 passed, 7 skipped` en local (2026-11-27, 7:37, sobre `b1841c2`, el código desplegado); `Success: no issues found in 235 source files` (mypy, 2026-11-27); CI y `Docker Build` en verde sobre `main` (`b1841c2`) |
| **Despliegue** | `deploy.py` con etiqueta `previous`, espera de salud, rollback y reenvío de claves por lista cerrada; imagen sobre `python:3.11-slim` + uv fijado; archivo normalizado a LF | Contenedor `healthy`, `latest` y `previous` disponibles, rollback probado con SSH falso. El 2026-11-27, dos despliegues desde `main` entre ciclos: 01:36 CET (`b928fa1`, imagen `4c2e2732e449`) y 10:49 CET (`b1841c2`, imagen `60180b9cdb72`), los dos con exit 0, `healthy`, md5 de los ficheros cambiados igual al commit y las novedades comprobadas en el navegador de la URL pública (Scavenging, ArXiv, modal de vídeo, búsqueda de News, Knowledge Garden) |

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
que algo lea su salida. → **T-124 (P2, abierta 2026-11-26)**. Y el caso
contrario: tres fuentes de News llevan meses sin publicar nada (Ben's Bites,
Indie Hackers, FutureTools) y el ciclo las da por buenas porque el script sale
con 0. → **T-176 (P1, abierta 2026-11-27)**.

### C. Calidad que se cree a sí misma

La suite está verde, pero `test_base_etl.py` escribe en `data/` real y borra
circuit breakers. → **T-108 (P2, cerrada 2026-11-25)**. El hook de push corre
la suite entera (≈8 min por push) y, por SSH, el push muere al terminar si la
sesión no lleva keepalive. → **T-116 (P3, cerrada 2026-11-25)**. GitHub avisa de
134 vulnerabilidades en `main` (recontado el 2026-11-27 sobre `b1841c2`: 8
críticas, 64 altas, 55 moderadas, 7 bajas; las 133 contadas el 2026-11-26
tenían parche), y el job de
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

**Libreta del usuario (triajeada el 2026-11-26, T-126…T-161; primera oleada
en producción el 2026-11-27).** Fuera del camino y comprobado en la URL
pública: las fuentes de baja calidad de News, Knowledge Garden y Learning
(→ **T-126, T-127, T-128, cerradas**) y Lobsters en Knowledge Garden (→
**T-130, cerrada**). Knowledge Garden abre con 3 peticiones y 169 KiB en vez de
62 (→ **T-136, cerrada**). Arregladas igualmente: los eventos de hoy en
Valencia Events (→ **T-160**), Humble Books con sus 451 libros (→ **T-149**),
Audible con ventana móvil, 500 novedades y paginación (→ **T-150**) y MS Learn en dos
subtabs (→ **T-144**). Lo que sigue roto: Indie Hackers lee una API de Reddit
que da 403 (→ **T-153 (P1)**), tres fuentes de News llevan meses sin publicar
(→ **T-176 (P1)**), las columnas de precio de Games salen en «N/A» (T-155) y el
ETL de ayudas no devuelve ni un registro de Burjassot (T-142). Lo que falta:
una fuente viva detrás del nombre «FutureTools» (T-129), la sección de
contenidos (T-131), cine, portales de transparencia, ofertas de videojuegos y
gift cards, watch de precios, XTeink, trendshift.io, skills y agentes de
Watchtower (T-132…T-152, P1/P2).

### F. Rendimiento del dashboard y del ciclo

Medido en la URL pública el 2026-11-27 (clic → primer pintado, con el reloj
de la propia página): 0,05–0,73 s en las 18 pestañas y 0,7 s hasta la primera
tabla al cargar. News pasó de 18 peticiones a 3 (→ **T-163, cerrada**) y ArXiv
abre con una sola categoría (→ **T-172, cerrada**). Queda: Scavenging responde
3,9 MB en una petición (→ **T-170 (P3)**), Learning abre con 7 peticiones, 6
en vacío (→ **T-177 (P3)**), Tech Radar renderiza dos veces, 617 + 608 KiB
(→ **T-179 (P3)**), dos paradas de ≈4,3 s sin causa asignada (→ **T-180
(P3)**) y, en el ciclo, dos ETLs que marcan su duración: ≈45 y ≈38 minutos de
≈47 (→ **T-174 (P2)**).

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

> Refrescado 2026-11-27. Fuente de ejecución: `docs/TASK_BOARD.md`.

| Horizonte | Tareas |
| :--- | :--- |
| **Ahora (P1)** | **Libreta:** T-129 FutureTools · T-131 sección de contenidos · T-138 canales de YouTube. **Hallazgos:** T-153 Indie Hackers por RSS · T-162 callbacks sin clic · T-176 fuentes de News muertas. **Anteriores:** T-106 backups en prod |
| **Después (P2)** | **Libreta:** T-132 · T-133 · T-134 · T-135 · T-137 · T-139 · T-140 · T-141 · T-142 · T-143 · T-145 · T-146 · T-147 · T-148 · T-151. **Hallazgos:** T-154 Reddit · T-155 Games · T-156 Udemy · T-161 test en `data/` real · T-164 texto plano · T-165 MS Learn retiradas · T-166 guardados de producción · T-174 duración del ciclo. **Anteriores:** T-109 receta de imagen única · T-115 CORS sin direcciones de LAN · T-120 alerts de Dependabot · T-124 LinkedIn Learning con consumidor · T-125 copia heredada y `.env` viejo en el servidor |
| **Más adelante (P3)** | T-047 BridgeBench vía browserless · T-096 convención de logging · T-114 dos planificadores · T-117 ensayo en el repo · T-119 higiene · T-121 paleta pública · T-123 capa de Playwright · T-152 STL · T-157 Scavenging sin datos · T-158 docs caducadas · T-159 recortes de Learning · T-167 iconos · T-168 coste por respuesta de KG · T-169 restos de T-136 · T-170 Scavenging 3,9 MB · T-175 `KeyError: 'id'` · T-177 Learning 7 peticiones · T-178 fechas de Valencia · T-179 Tech Radar doble render · T-180 paradas de 4 s |
| **Bloqueado** | T-038 Artificial Analysis (clave del usuario) |

Cerradas entre el 2026-11-24 y el 2026-11-27: T-048, T-107, T-108, T-110,
T-111, T-112, T-113, T-116, T-118, T-126, T-127, T-128, T-130, T-136, T-144,
T-149, T-150, T-160, T-163, T-171, T-172 y T-173. Sus filas íntegras están en
`docs/TASK_BOARD_ARCHIVE.md`.

Fuera del board y pendiente del usuario: añadir a `.env` las claves que quiera
(hoy no hay ninguna) y redesplegar para que lleguen al contenedor; decidir
sobre T-106 (volumen de backups: el disco de appdata, una copia al día, 7
conservadas, ninguna fuera del servidor) y T-125 (limpiar la carpeta de la app
en el servidor); responder las dudas de la libreta que frenan T-131, T-132,
T-135, T-138, T-145, T-148, T-149, T-150 y T-152 (dónde y cómo se llama la
sección de contenidos, qué es «media» y los «STL», etc.); y decir qué hacer
con los 47 registros marcados como guardados en producción sin que él los
marcara (T-166).

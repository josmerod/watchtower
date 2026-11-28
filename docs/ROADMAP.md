# Watchtower — Roadmap

> Horizonte priorizado de trabajo, derivado del valor entregado y de los gaps
> observados. La ejecución vive en `docs/TASK_BOARD.md`; el historial en
> `docs/TASK_BOARD_ARCHIVE.md`; el feedback del usuario en `docs/FEEDBACK.md`.
>
> Estado al 2026-11-27, por la noche (ese día se actualizaron las filas
> Pipeline, Mercados, Juegos y cursos, Observabilidad, Calidad y Despliegue, y
> los bloques A, B, E y F). Las cifras de la primera sección se midieron el
> 2026-11-24 contra la API del contenedor recién desplegado, salvo las que
> llevan su propia fecha; no se heredan de versiones anteriores de este
> documento.

## 1. Dónde estamos (valor entregado, con evidencia)

| Área | Qué existe hoy | Evidencia (2026-11-24) |
| :--- | :--- | :--- |
| **Pipeline** | 101 entradas en el orquestador (98 ETLs, 2 watchers, 1 miner) más el watcher de frescura tras el pool: **102 scripts por ciclo** desde la limpieza de fuentes del 2026-11-27 (T-126, T-127, T-128), en producción desde el despliegue de esa noche; cada 2 horas, 4 workers | Tras el despliegue del 2026-11-27 a las 01:36 CET (`b928fa1`): `Successful: 102 \| Failed: 0` en el primer ciclo y en los tres siguientes (≈47 min cada uno), y también en el primero tras el segundo despliegue del día (10:49→11:36 CET), tras el tercero (13:07:05→13:53:50 CET, `e049c40`) y tras el cuarto (14:54:35→15:41:49 CET, `defdfc3`), los dos sin un solo aviso en el log, y lo mismo tras los tres de la tarde y la noche: 16:44:23→17:31 CET (`15bcdb1`), 18:38:06→19:23:55 CET (`d81e728`) y 20:34:50→21:20:52 CET (`50e639f`) y 03:45:05→04:30:57 CET del 2026-11-28 (`260bcf4`), todos de ≈46 min; la duración la marca `goldigging_youtube_posts` (≈2700 s), porque `reddit_unified` (2284 s antes del corte de T-154) no recibe nada desde el 2026-11-17 y desde T-154 corta a los 188 s (→ T-174). Los anteriores: `108 \| 0` en 2799 s (2026-11-26) y `109 \| 0` en 2813 s (2026-11-24), en ambos con el watcher de frescura tras el pool y antes del resumen |
| **Fuentes tech** | Tech Radar de 23 fuentes y feed unificado «Todas» | `/api/v1/radar` → JSON 200; `/api/v1/news` → 1087 items |
| **Investigación** | ArXiv por categorías, HF Daily Papers con citas (OpenAlex, CrossRef de respaldo), tab de benchmarks | `/api/v1/benchmarks` → 146 modelos; BridgeBench y Artificial Analysis siguen sin datos propios (T-047, T-038) |
| **Mercados** | Tab 📈 Markets con las 50 primeras monedas de CoinGecko y cartera local que añade y borra posiciones (T-186) | 50 monedas; en la URL pública (2026-11-27) «💼 Mi cartera» añade una posición con su valor al precio actual y la elimina — Añadir y Eliminar no hacían nada desde el 2026-09-10 — y «BTC Dominance» sale sin signo (58.75%, T-188) |
| **Comunidad** | Pulso reddit por RSS, Knowledge Garden | `/api/v1/knowledge-garden` → JSON 200; 789 filas con fecha, chip «21 NUEVO». Desde T-136 (cerrada 2026-11-27) la pestaña abre con 3 peticiones y 169 KiB (antes 62 peticiones) y pinta una subtab por clic |
| **Seguridad** | CISA KEV, 3 feeds RSS, advisories OSV del propio stack y EOL del stack (endoflife.date) | 130 items (60 KEV, 70 noticias), 33 advisories OSV de severidad alta o crítica |
| **Territorio** | Agenda de Valencia con fecha legible y orden por inicio (T-178), y ayudas públicas (BDNS, GVA, DOGV y otros) | `/api/v1/valencia/events` → 32 eventos; en la URL pública (2026-11-27) la pestaña lista 31 eventos por inicio, de «vie 27/11/2026 · 19:30» a mayo de 2027, y Ayudas cuenta 3 fuentes (T-183) |
| **Juegos y cursos** | Ofertas, paquetes y regalos de IsThereAnyDeal y paquetes de Humble con fecha y recuento reales (T-192, T-193 y T-195, cerradas 2026-11-27); cursos de varios proveedores | `/api/v1/games` → 206 items (2026-11-24). En el contenedor (2026-11-27, 20:44 CET): `deals.json` 150 ofertas del día en EUR (0,49 a 59,60 €), `bundles.json` 38, `giveaways.json` 5 y `humblebundles.json` 59 con fin (28/11 → 18/12) y número de juegos; hasta ese despliegue las ofertas eran las del 2026-07-22 |
| **API** | FastAPI con 20 rutas GET (19 bajo `/api/v1` y `/health`), documentación in-app | Las 11 rutas que lista `/docs` devuelven JSON 200 contra el contenedor; la API pública responde en su propio hostname |
| **Observabilidad** | DataFreshnessWatcher + card 🩺 en Metrics; retención de snapshots (`keep_last=30`); desde el 2026-11-27 vigila también las 21 fuentes de News y los dos feeds de Games (T-176, T-192) | 38 frescas, 0 obsoletas y 5 críticas (2026-11-27, 21:20 CET): los dos ficheros de Reddit (sin respuesta desde el 17/11), FutureTools, Indie Hackers y BridgeBench. El 2026-11-24 eran 20 / 0 / 3 con una lista más corta |
| **Calidad** | Suite de 1795 tests, Ruff, mypy, hooks de commit y push, CI que construye la imagen desplegada; desde el 2026-11-28 `board_check.py` revisa los documentos de tareas antes de cada commit (T-137) | `1786 passed, 9 skipped` en local (2026-11-28, sobre el código de `2f31c68`, en 7:57) y otra vez en el hook de push; CI en Linux `build` en 59 s y `ci` en 8m03s (PR #45); `Success: no issues found in 237 source files` (mypy, 2026-11-28); CI y `Docker Build` en verde sobre `main` (`100a080`) |
| **Despliegue** | `deploy.py` con etiqueta `previous`, espera de salud, rollback y reenvío de claves por lista cerrada; imagen sobre `python:3.11-slim` + uv fijado; archivo normalizado a LF; copia diaria verificada de `data/` y `logs/` en un volumen propio desde el 2026-11-27 (T-106) | Contenedor `healthy`, `latest` y `previous` disponibles, rollback probado con SSH falso. Entre el 2026-11-27 y la madrugada del 28, ocho despliegues desde `main` entre ciclos: 01:36 CET (`b928fa1`, imagen `4c2e2732e449`), 10:49 CET (`b1841c2`, imagen `60180b9cdb72`), 13:07 CET (`e049c40`, imagen `e0793730de00`), 14:54 CET (`defdfc3`, imagen `5065b26ce8fc`), 16:44 CET (`15bcdb1`), 18:38 CET (`d81e728`, imagen `608d2531d03b`) y 20:35 CET (`50e639f`, imagen `a4dfa9218b02`) y 03:45 CET del 28 (`260bcf4`, imagen `fd5a68749990`), los ocho con exit 0, `healthy`, md5 de los ficheros cambiados igual al commit y las novedades comprobadas en el navegador de la URL pública (Scavenging, ArXiv, modal de vídeo, búsqueda de News, Knowledge Garden, filtro de idioma y menús desplegables, fechas de Valencia, tarjetas de Ayudas, subtabs y botones a 480 px; y por la tarde-noche «Mi cartera», la exportación a CSV de News, la hora de GCP, el aviso de fuente callada, el texto plano de Knowledge Garden, el paginador de Videos y los tres subtabs de Games; y en la madrugada del 28 el radar, las gráficas de Metrics y de Ayudas, la barra principal, Learning con las credenciales retiradas, el desplegable de Tema de Videos y los subtabs de Scavenging) |

Dos cosas de esa columna conviene no olvidarlas al leerla: las copias de
seguridad viven en el mismo disco que `data/` — desde el 2026-11-27 sale una
verificada al día y se conservan 7, pero no hay ninguna fuera del servidor, así
que no protegen de un fallo del disco (T-106, cerrada con ese límite) —, y
ninguna clave API llega al contenedor porque ninguna está configurada —
`deploy.py` reenvía desde el 2026-11-26 las que haya en `.env`, y solo esas
(T-107, cerrada).

## 2. Gaps y oportunidades

Los IDs remiten a `docs/TASK_BOARD.md`. El orden dentro de cada bloque es el de
prioridad del board.

### A. Producción sin red de seguridad

El despliegue funciona, pero a su alrededor quedan huecos. El primero, el de
las copias, se cerró el 2026-11-27: `run_backup.py` viaja en el contenedor con
su propio volumen y saca una copia verificada al día de `data/` y `logs/`
(primer archivo: 793.1 MiB, 59137 archivos, a las 17:35 CET), con el límite
dicho arriba — mismo disco que los datos, ninguna copia fuera del servidor.
→ **T-106 (P1, cerrada 2026-11-27)**. Ninguna clave API llega al contenedor:
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
contrario: tres fuentes de News llevaban meses sin publicar nada (Ben's Bites,
Indie Hackers, FutureTools) y el ciclo las daba por buenas porque el script
salía con 0. → **T-176 (P1, cerrada 2026-11-27)**: Ben's Bites lee el feed de
Substack y vuelve a publicar, el watcher de frescura juzga los 21 ficheros de
News por la antigüedad de su entrada más nueva y la pestaña avisa de la fuente
callada; lo que queda de cada fuente sigue en su fila (T-153, T-129). El mismo
vicio costó en Games cuatro meses de ofertas sin leer (→ **T-192, cerrada**) y
sigue en tres scripts registrados que no producen nada (→ **T-196 (P2)**).

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
subtabs (→ **T-144**). Lo que sigue roto: Indie Hackers no tiene fuente — la
API de Reddit da 403 y sus feeds RSS también lo rechazan (→ **T-153 (P1)**) —
y el ETL de ayudas no devuelve ni un registro de Burjassot (T-142). Arreglado
el 2026-11-27 por la noche y comprobado en la URL pública: Ben's Bites y el
aviso de fuente callada (→ **T-176, cerrada**), las columnas de Games y, detrás,
cuatro meses de ofertas sin leer y las fechas inventadas de Humble (→ **T-155,
T-192, T-193, T-194 y T-195, cerradas**), «Mi cartera» y la exportación a CSV
de News, que no funcionaban (→ **T-186 y T-187, cerradas**), los resúmenes en
texto plano (→ **T-164, cerrada**) y los callbacks que corrían sin clic (→
**T-162, cerrada**). Lo que falta:
una fuente viva detrás del nombre «FutureTools» (T-129), la sección de
contenidos (T-131), cine, portales de transparencia, ofertas de videojuegos y
gift cards, watch de precios, XTeink, trendshift.io, skills y agentes de
Watchtower (T-132…T-152, P1/P2).

### F. Rendimiento del dashboard y del ciclo

Medido en la URL pública el 2026-11-27 (clic → primer pintado, con el reloj
de la propia página): 0,05–0,73 s en las 18 pestañas y 0,7 s hasta la primera
tabla al cargar. News pasó de 18 peticiones a 3 (→ **T-163, cerrada**) y ArXiv
abre con una sola categoría (→ **T-172, cerrada**). Cerradas el 2026-11-28
con el despliegue de la madrugada, medidas en la URL pública: Scavenging abre
con 135 KiB frente a 3,9 MB (→ **T-170**), Learning con 2 peticiones frente a
7 (→ **T-177**), Tech Radar con una petición de 69 KiB frente a 617 + 608
(→ **T-179**) y los cuatro ETLs de News guardan texto plano (→ **T-190**); por
el camino aparecieron los gráficos tapados desde el 2025-08 (→ **T-199**) y la
caché de los repositorios, que no miraba el fichero (→ **T-197**). Queda: dos
paradas de ≈4,3 s sin causa asignada (→ **T-180 (P3)**), Videos y Deals vuelven
a pintar la tabla al abrir (→ **T-211 (P3)**), una pestaña abierta durante un
despliegue no responde hasta recargarla (→ **T-191 (P3)**) y, en el ciclo, un
ETL que marca su duración: ≈45 de los ≈46 minutos (`goldigging_youtube_posts`;
Reddit, que lo marcaba con él, no responde desde el 2026-11-17 y corta a los
188 s) (→ **T-174 (P2)**). Las estrellas no gastan peticiones (T-189, medido y
cerrado).

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

> Refrescado 2026-11-28. Fuente de ejecución: `docs/TASK_BOARD.md`.

| Horizonte | Tareas |
| :--- | :--- |
| **Ahora (P1)** | **Libreta:** T-129 FutureTools (Ben's Bites vuelve a publicar) · T-131 sección de contenidos · T-138 canales de YouTube (el desplegable de tema y los presets ya están; quedan sus decisiones). **Hallazgos:** T-153 Indie Hackers sin fuente · T-204 «Open Source Projects» congelado desde el 29 de abril. Cerradas el 2026-11-28: T-137 (skills y agentes) y T-199 (los gráficos tapados) |
| **Después (P2)** | **Libreta:** T-132 · T-133 · T-134 · T-135 · T-139 · T-140 · T-141 · T-142 · T-143 · T-145 · T-148 · T-151. **Hallazgos:** T-154 Reddit · T-166 guardados de producción · T-174 duración del ciclo · T-196 tres scripts de Games sin datos · T-201 alias duplicados en el radar · T-206 barra de subtabs de News · T-208 `html_to_text` · T-212 columna Retirada de Learning. **Anteriores:** T-109 receta de imagen única · T-115 CORS sin direcciones de LAN · T-120 alerts de Dependabot · T-124 LinkedIn Learning con consumidor · T-125 copia heredada y `.env` viejo en el servidor |
| **Más adelante (P3)** | T-047 BridgeBench vía browserless · T-096 convención de logging · T-114 dos planificadores · T-117 ensayo en el repo · T-119 higiene · T-121 paleta pública · T-123 capa de Playwright · T-152 STL · T-157 Scavenging sin datos · T-158 docs caducadas · T-167 iconos · T-168 coste por respuesta de KG · T-169 restos de T-136 · T-180 paradas de 4 s · T-191 recargar tras un despliegue · T-202 etiquetas del radar que se pisan · T-203 títulos de Metrics · T-205 hoja de estilos dos veces · T-207 importar `src` crea carpetas · T-209 ids `tab-null` · T-210 títulos de Microsoft · T-211 Videos y Deals repintan |
| **Bloqueado** | T-038 Artificial Analysis (clave del usuario) |

Cerradas entre el 2026-11-24 y el 2026-11-28: T-048, T-106, T-107, T-108,
T-110, T-111, T-112, T-113, T-116, T-118, T-126, T-127, T-128, T-130, T-136,
T-137, T-144, T-146, T-147, T-149, T-150, T-155, T-156, T-159, T-160, T-161,
T-162, T-163, T-164, T-165, T-170, T-171, T-172, T-173, T-175, T-176, T-177,
T-178, T-179, T-181, T-182, T-183, T-184, T-185, T-186, T-187, T-188, T-189,
T-190, T-192…T-195 y T-197…T-200. Sus filas íntegras están en
`docs/TASK_BOARD_ARCHIVE.md`.

Fuera del board y pendiente del usuario: añadir a `.env` las claves que quiera
(hoy no hay ninguna) y redesplegar para que lleguen al contenedor; decidir
sobre T-125 (limpiar la carpeta de la app en el servidor); responder las dudas
de la libreta que frenan T-131, T-132, T-135, T-138, T-145, T-148, T-149, T-150
y T-152 (dónde y cómo se llama la sección de contenidos, qué es «media» y los
«STL», etc.); y decir qué hacer con T-153 (Indie Hackers se ha quedado sin
fuente), T-129 (Ben's Bites vuelve a publicar: ¿basta con cambiar la
etiqueta?), T-196 (tres scripts de Games: la clave gratuita de IsThereAnyDeal,
otra fuente, o sacarlos del ciclo), T-191 (¿recargar sola la pestaña tras un
despliegue?) y los 47 registros marcados como guardados en producción sin que
él los marcara (T-166). Dudas abiertas el 2026-11-28: T-206 (la barra de subtabs de News, ¿en varias filas o con un desplegable «Más ▾»?).

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

## Triajeado (archivo histórico)

<!-- El agente mueve aquí las entradas ya convertidas a tareas, con su ID -->

- [x] 2026-08-27 — Estaría bien revisar una por una las tab-specs que están en docs y refinar o añadir las fuentes y features que se mencionan → **T-059** (re-audit sistemático de las 15 specs)
- [x] 2026-08-27 — Descartaría la tab de shortcuts, por el momento → **T-060** (ocultada del nav de forma reversible; palette Ctrl+K intacta)
- [x] 2026-08-27 — A nivel de news, la tab de búsqueda global la pondría al final o algo, por si acaso → **T-061** (🔎 Global pasa a último subtab; el primero es Top Tech)
- [x] 2026-08-27 — Los indicadores de estado de las news pueden aportar valor, pero siempre están en gris, creo que ya con el indicador de estado de arriba está bien → **T-062** (dots de News eliminados; el estado vive en la card 🩺 de Metrics)
- [x] 2026-08-27 — El summary de estado que está arriba del todo debería ser colapsable, no hace falta verlo todo el rato → **T-063** (botón "Estado del sistema", colapsado por defecto)

# Especificación de mejora — Tab Shortcuts

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/shortcuts_tab.py`, `data/shortcuts/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Launcher personal de bookmarks: tarjetas por categoría ("Development Tools", "AI & Machine Learning", "Valencia Tech", …) con botones que abren URLs en pestaña nueva. **Sin ETL** — es el único tab 100% estático.

- Componente: `shortcuts_tab.py` (240 líneas). Único tab que usa el patrón Repository (`ShortcutsRepository(BaseRepository[dict])`, TTL 1 h).
- Datos: `data/shortcuts/predefined_shortcuts.json` (28 categorías, **177 items**, campos `name/url/icon/description`). `data/shortcuts/custom_shortcuts.json` **se lee pero no existe** y no hay ningún writer.
- 1 callback: `update_filtered_shortcuts` re-renderiza todas las tarjetas por cada pulsación de tecla del buscador (match sobre name/url/description).

### 1.2 Bugs y deuda

| # | Severidad | Problema |
|---|---|---|
| S1 | **P0** (producto) | Sin capacidad de añadir/editar/borrar: el fichero `custom_shortcuts.json` se contempla en el código pero no existe UI, CLI ni script que lo escriba. La personalización exige editar JSON a mano + esperar TTL/restart. |
| S2 | P1 | `icon` está en el 100% de los items y nunca se renderiza; `description` solo se usa para buscar, nunca se muestra. |
| S3 | P1 | Re-render server-side de 177 botones por tecla; sin debounce. |
| S4 | P2 | `print()` para warnings (líneas 172, 194) en vez de logging. |
| S5 | P2 | Parsing de formato legacy/nuevo duplicado entre `transform_data` y `get_all_shortcuts`. |
| S6 | P2 | Sin navegación por categorías (anclas), sin favoritos, sin contadores de uso, sin comprobar enlaces muertos. |

## 2. Fuentes adicionales

No aplica scraping externo (es un tab de datos propios), pero sí tres "fuentes" de contenido:

1. **Import de bookmarks del navegador** (parse HTML de export Netscape — formato estándar de Chrome/Firefox): script único `scripts/import_bookmarks.py` que genere/merge en `custom_shortcuts.json` clasificando por carpeta.
2. **Detección de enlaces muertos**: ETL ligero (HEAD requests concurrentes, circuit breaker de `BaseETL`) que marque `last_status/last_checked` por URL y alimente el badge de salud de F4.
3. **Auto-sugerencia desde el historial de uso** (F3): las URLs más abiertas desde el tab pasan a proponerse como "fijas".

## 3. Mejoras a funcionalidad existente

### M1 — CRUD completo de atajos (fix S1)
**Datos:** escribir `custom_shortcuts.json` (formato idéntico al predefined; el merge custom-sobre-predefined ya está implementado). IDs estables `slugify(name)`.
**UI:** botón "+ Añadir atajo" por tarjeta y "✎ Editar" por item → `dbc.Modal` con campos nombre/URL/icono/emoji/descripción/categoría (datalist de las 28 existentes) + confirmación de borrado con `is_open`.
**Callbacks (single-callback, `prevent_initial_call=True`):**
- `shortcut-save` → valida URL (`urllib.parse`), mergea, persiste con `json.dump(..., indent=2)`, invalida caché del repo (`force_refresh=True`), re-renderiza.
- `shortcut-delete` → confirma y elimina.
**Validación:** rechazar duplicados de URL exacta dentro de la misma categoría (warning no bloqueante).
**Aceptación:** añadir/editar/borrar sin reiniciar el servidor; los cambios sobreviven un restart; `predefined_shortcuts.json` queda intacto.
**Esfuerzo:** M (1 jornada).

### M2 — Render de icono + tooltip de descripción (fix S2)
Mostrar `icon` (emoji o clase FontAwesome) dentro del botón; `title=` o tooltip Bootstrap con `description`. Esfuerzo: B (<1 h).

### M3 — Rendimiento del buscador
`debounce=True` + ocultar categorías con `style={"display": "none"}` en clientside en lugar de re-render completo server-side. Esfuerzo: B.

### M4 — Logging y limpieza
Sustituir `print()` por `logger` (S4); unificar parsing de formato en `ShortcutsRepository.transform_data` (S5). Esfuerzo: B.

## 4. Funcionalidades nuevas propuestas

### F1 — Command palette (Ctrl/Cmd+K)
**Objetivo:** abrir cualquier atajo desde cualquier tab del dashboard sin tocar el ratón.
**UI:** overlay global (asset JS en `/assets/js/command_palette.js`) con fuzzy-search sobre los 177 items + acciones ("Abrir X", "Buscar X en News", "Ir a tab Y"). Integración con `dcc.Location` para navegación entre tabs.
**Aceptación:** <50 ms de filtrado; navegable con teclado; funciona con los datos de ambos ficheros.
**Esfuerzo:** M–A (1–2 jornadas; el asset JS es la parte mayor).

### F2 — Favoritos y "más usados"
Pin ⭐ por atajo (persistido en `localStorage`) que sube el item a una tarjeta "Favoritos" arriba. Contador de clicks por atajo (clientside `localStorage` + flush opcional a `data/analytics/shortcut_usage.json` — integración natural con el `activity_tracker` de `src/recommendations/`). Esfuerzo: M.

### F3 — Navegación por categorías
Barra de chips/anchor-links con las 28 categorías y contadores, con scroll suave a cada tarjeta; en móvil, un `dbc.Select` de salto. Esfuerzo: B.

### F4 — Salud de enlaces
Columna/badge 🟢🔴 por atajo según el ETL de comprobación (ver §2.2), con "última comprobación" en tooltip y acción "abrir igualmente". Esfuerzo: M (ETL) + B (UI).

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M2 iconos+tooltips, M3 debounce, M4 logging |
| **Corto plazo** | M1 CRUD completo (es el gap de producto más grave del tab), F3 navegación |
| **Medio plazo** | F2 favoritos/uso, F4 salud de enlaces |
| **Estratégico** | F1 command palette como capa global del dashboard (beneficia a todos los tabs, no solo Shortcuts); evaluar import de bookmarks |

**Criterios de éxito:** edición sin restart; 0 campos de datos sin renderizar; búsqueda fluida en los 177+ items.

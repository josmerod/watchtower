# Especificación de mejora — Tab 🏷️ Deals

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/deals_tab.py` + `src/etl/deals/lifetimo_etl.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"Exclusive Lifetime Deals" — un solo subtab "Lifetimo Lifetime Deals". Tabla de 3 columnas (Título enlazado, Categorías en 1 badge, Fecha), búsqueda sobre `dcc.Store` con clear button, caché 60 s, cap 50.

- Componente: `deals_tab.py` (239 líneas) con `sys.path.append` hack.
- ETL: `lifetimo_etl.py` (registrado): scrape de `lifetimo.com/dealbox/?_deal_categories=productivity,ai,bundles,self-hosted,backup,learning,automation,scheduling` (WordPress/Elementor), categorías extraídas de clases CSS `platform-*`, checkpointed.
- Modelo: `LifetimeDeal` (`src/models/ecommerce.py`) con `price_info`, `original_price`, `discount_pct`… **siempre null** (el ETL no los scrapea).

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| D1 | **P0** (producto) | **Un tab de ofertas sin precios**: `price_info/original_price/discount_pct` existen en el modelo y no se extraen. La promesa del tab (chollos lifetime) no se cumple sin cifras. |
| D2 | **P0** | Rama multi-fuente rota: `create_deals_source_tab_content(["a","b"])` (uso documentado por el parámetro `source_keys` lista) lanza `NameError` — `source_display_name` solo se asigna en la rama string. La infra multi-fuente es decorativa. |
| D3 | P1 | `description` buscable pero no visible; categorías colapsadas en 1 badge; highlight `<mark>` literal (mismo bug SC4). |
| D4 | P1 | Cap 50 aplicado antes del Store → búsqueda solo sobre los 50 más recientes. |
| D5 | P2 | Serialización inconsistente del Store (json string aquí, lista en scavenging); `combined_name` parámetro muerto; tabla duplicada layout/callback; sin paginación/fechas/export. |
| D6 | P2 | Lifetimo es fuente única — el tab se llama "Deals" en plural pero hay 1 proveedor; el catálogo de ETLs relacionados (`ecommerce/shoppy_etl.py` registrado) escribe datos que nadie consume. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **AppSumo** (`appsumo.com` — JSON interno de listings/scrape con Playwright ya probado en el repo) | Scrape | El marketplace LTD por excelencia; precios, descuentos, fechas de fin de promo | Medio | ⭐⭐⭐ |
| **StackSocial RSS** (`stacksocial.com/feed`) + `stacksocial.com/lifetime` | RSS/scrape | Deals tech con lifetime explícito | Bajo | ⭐⭐ |
| **SaaSMantra / PitchGround / DealMirror** (marketplaces LTD) | Scrape | Volumen de LTDs SaaS | Medio | ⭐⭐ |
| **Shoppy ETL ya registrado** (`src/etl/ecommerce/shoppy_etl.py` → `data/shoppy/shoppy_processed_data.json`) | Dato existente | Cero ETL nuevo: consumirlo como segunda fuente (arregla D6 parcialmente) | Muy bajo | ⭐⭐⭐ |
| **Gumroad free** (ya scrapeado para Scavenging) | Dato existente | Cross-listar productos free aquí como "deals 100% off" | Muy bajo | ⭐ |
| **r/deals, r/lifetimedeals** (Reddit JSON, infra reddit_unified existente) | REST | Descubrimiento comunitario con comentarios críticos (señal de calidad) | Bajo | ⭐⭐ |
| **Notion? no** — mantener foco SaaS/LTD | — | — | — | — |

## 3. Mejoras a funcionalidad existente

### M1 — Scrapear precios y descuentos (fix D1)
En la card de Lifetimo el precio está en el DOM (`.elementor-post__meta` / botones). Extraer precio actual, precio original (tachado) y calcular `discount_pct`. Validación: registro con `price_info` no-null en ≥80% de deals. Mostrar columnas: Precio (badge verde), Tachado, -X%, Categorías (1 badge por categoría, fix D3).

### M2 — Arreglar y estrenar la multi-fuente (fix D2)
Asignar `source_display_name` antes de ramificar string/lista + test con ambos tipos. Añadir segunda fuente real: Shoppy (dato existente) → el tab pasa a 2 subtabs o tabla unificada con columna Fuente.

### M3 — Búsqueda sobre el dataset completo (fix D4)
Igual que Scavenging M3: Store con dataset íntegro, límite en render/paginación.

### M4 — Descripción visible + highlight funcional
Subtítulo con descripción truncada (2 líneas, patrón Scavenging "Details") + helper `highlight_segments` compartido (fix del bug `<mark>` en los 3 tabs afectados de una vez).

### M5 — Higiene
Eliminar `sys.path.append` (import normal del paquete), unificar serialización del Store (lista, no json-string), extraer `render_deals_table(...)` común, `combined_name` usarlo o quitarlo.

## 4. Funcionalidades nuevas propuestas

### DE1 — Comparador de LTDs
**Objetivo:** comparar ofertas lado a lado antes de comprar.
**UI:** checkbox por fila (máx 3) → panel comparación (modal) con tabla campo-a-campo: precio, precio original, descuento, categorías, fecha fin, fuente, link.
**Callbacks:** 1 callback del modal; estado en `dcc.Store` de seleccionados.
**Aceptación:** selección persiste al filtrar; comparación se limpia con botón.
**Esfuerzo:** M.

### DE2 — "Termina pronto" + precio-historia
Columna countdown si el deal tiene fecha fin (extraer del ETL cuando exista; AppSumo la tiene). Con snapshots timestamped ya existentes: sparkline de precio (dcc.Graph mini) por deal — detectar "fake discount" (precio subiendo antes de la oferta). Esfuerzo: M.

### DE3 — Watcher de keywords
Igual que Courses F3 / Scavenging SA3: eventos al aparecer un deal que matchee keywords ("n8n", "api", "backup") → notificaciones. Esfuerzo: M.

### DE4 — Filtros por categoría/precio/descuento
Dropdown categoría (derivado de datos), slider descuento mínimo, switch "Solo con lifetime real". 1 callback. Esfuerzo: B–M.

### DE5 — Valoración "¿merece la pena?"
Cruce barato: si el producto aparece en Reddit (deals/lifetimedeals) adjuntar score y nº comentarios como columna de señal social. Esfuerzo: M.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M1 precios (el fix de mayor valor/effort del tab), M2 multi-fuente + Shoppy, M5 higiene |
| **Corto plazo** | M3 búsqueda completa, M4 descripción+highlight, DE4 filtros, AppSumo (⭐⭐⭐) |
| **Medio plazo** | DE2 countdown+historia de precio, DE1 comparador, StackSocial/SaaSMantra |
| **Estratégico** | DE3 watcher keywords, DE5 señal social; consolidación conceptual Deals(LTD SaaS) ↔ Scavenging(gratis) ↔ Games(deals de juegos) en un patrón común "oferta con deadline" |

**Criterios de éxito:** precios visibles en ≥80% de deals; ≥2 fuentes activas; 0 código muerto (`combined_name`, rama lista); búsqueda sobre histórico completo.

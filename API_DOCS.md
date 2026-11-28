# Watchtower API Documentation

The Watchtower API is a read-only FastAPI service that serves the data collected by the ETL pipelines. It exposes 20 GET routes: 19 under `/api/v1` plus `/health`.

## Running locally

```bash
uv run uvicorn src.api.main:app --port 45714
```

The API then answers on `http://localhost:45714`. The interactive documentation is served by the API itself: Swagger UI at `http://localhost:45714/docs` and ReDoc at `http://localhost:45714/redoc`, both generated from the schema at `/openapi.json`. On the deployed instance, the dashboard's `/api-docs` route redirects to the Swagger UI.

## Routes

The nine content routes (every route from `routers.py` except `/api/v1/benchmarks` and `/api/v1/sources`) return a JSON list of items with the fields `title`, `url`, `source`, `published_at` and `category`. `source` selects one source key and is optional; an unknown key returns an empty list.

| Method | Path | Query parameters | Returns | Defined in |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/health` | None | `{"status": "ok"}` | `src/api/main.py` |
| GET | `/api/v1/health` | None | `{"status": "ok"}` | `src/api/main.py` |
| GET | `/api/v1/news` | `source` (optional), `limit` (default 10000, range 1–10000) | News items | `src/api/routers.py` |
| GET | `/api/v1/knowledge-garden` | `source` (optional), `limit` (default 10000, range 1–10000) | Knowledge Garden items | `src/api/routers.py` |
| GET | `/api/v1/games` | `source` (optional), `limit` (default 10000, range 1–10000) | Games | `src/api/routers.py` |
| GET | `/api/v1/benchmarks` | `source` (optional) | `{"count", "models"}`: AI coding benchmark data from BridgeBench.ai | `src/api/routers.py` |
| GET | `/api/v1/arxiv` | `source` (optional), `limit` (default 10000, range 1–10000) | ArXiv papers | `src/api/routers.py` |
| GET | `/api/v1/ai-platforms` | `source` (optional), `limit` (default 10000, range 1–10000) | AI platform model data | `src/api/routers.py` |
| GET | `/api/v1/expanded` | `source` (optional), `limit` (default 10000, range 1–10000) | Expanded intelligence data (GitHub, StackExchange, OpenAlex, packages, Kaggle) | `src/api/routers.py` |
| GET | `/api/v1/spanish-aid` | `source` (optional), `limit` (default 10000, range 1–10000) | Spanish public aid and subsidies | `src/api/routers.py` |
| GET | `/api/v1/cloud-updates` | `source` (optional), `limit` (default 10000, range 1–10000) | Cloud provider updates (AWS, GCP, CNCF, GitHub Blog) | `src/api/routers.py` |
| GET | `/api/v1/valencia-local` | `source` (optional), `limit` (default 10000, range 1–10000) | Valencia local news and transport updates | `src/api/routers.py` |
| GET | `/api/v1/sources` | None | Per data route, a `{source key: source name}` mapping | `src/api/routers.py` |
| GET | `/api/v1/markets` | `limit` (default 200, range 1–500) | `{"generated_at", "count", "items"}`: crypto market quotes (CoinGecko) | `src/api/public.py` |
| GET | `/api/v1/radar` | `limit` (default 200, range 1–500) | `{"generated_at", "count", "items"}`: merged technology-radar feed, newest first | `src/api/public.py` |
| GET | `/api/v1/freshness` | None | Data-freshness summary plus a `stale_sources` list | `src/api/public.py` |
| GET | `/api/v1/digest` | None | The weekly digest, as stored | `src/api/public.py` |
| GET | `/api/v1/security/kev` | `limit` (default 100, range 1–500) | `{"generated_at", "kev_count", "items", "stack_matches"}`: known exploited vulnerabilities and matches against the self-hosted stack | `src/api/public.py` |
| GET | `/api/v1/valencia/events` | `days` (default 0, meaning all; range 0–365; ignored when `from` or `to` is given), `from` and `to` (optional, `YYYY-MM-DD`, inclusive, read in València's time), `category` (optional, as the ETL names it: `música`, `teatro`, `arte`, `tech`, `ferias`, `infantil`, `deporte`, `otro`…; case and accents do not count), `limit` (default 200, range 1–500) | `{"generated_at", "count", "items"}`: Valencia events, from thirteen public agendas | `src/api/public.py` |
| GET | `/api/v1/search` | `q` (required), `limit` (default 25, range 1–100) | `{"query", "count", "items"}`: search results across news, releases, coins, videos and papers | `src/api/search.py` |

- `/api/v1/sources` keys its mappings by `news`, `knowledge_garden`, `games`, `benchmarks`, `arxiv`, `ai_platforms`, `expanded`, `spanish_aid`, `cloud_updates` and `valencia_local`. A `source` written with `-` where the key has `_` is also accepted.
- When a data file is missing, the routes in `routers.py` return an empty list and the routes in `public.py` return 404 with `{"error": ...}`. The routes in `public.py` and `search.py` send `Cache-Control: no-store`.
- `/api/v1/search` returns 400 for an empty `q` and 200 with `count` 0 when there is no indexed data. Its index is built on the first request and reused until the process restarts; in the deployed container, the ETL scheduler restarts the API after every run.
- A parameter outside its range is rejected with 422.

## Deployment
The API runs automatically alongside the dashboard on port **45714**.
To deploy updates:
```bash
uv run --with paramiko python deployment/deploy.py
```

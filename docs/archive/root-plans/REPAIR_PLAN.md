# 🗼 Watchtower Audit & Fix Plan — May 21, 2026

## Current State Summary

| Category | Items | Sources | Freshness | Status |
|---|---|---|---|---|
| News | 1070+ | 23 sources (7 active) | Fresh (May 21) | ✅ |
| Knowledge Garden | 10000+ | 19 sources | Mixed (PH stale) | ⚠️ |
| Games | 207 | 3 sources (deals/bundles/trending) | Fresh (May 21) | ✅ |
| Entertainment | 100 | Trakt only | **FROZEN Jan 5** | 🔴 |
| Intelligence | 75 | WHO + NVD | WHO fresh, NVD **1988** | 🔴 |
| Ecommerce | 200+ | Gumroad only | Fresh (May 21) | ✅ |
| Travel | 114 | Viajeros Piratas | Fresh (May 21) | ✅ |
| Research | 200 | ADHD publications | No dates | ⚠️ |
| Museums | **1** | Wikidata SPARQL | Fresh but wrong count | 🔴 |
| Benchmarks | ✅ | BridgeBench | Fresh | ✅ |

## Diagnosed Issues

### 🔴 CRITICAL
1. **NVD CVE returning 1988 data** — NVD API 2.0 returns 404 (service down/rate-limited). Container has stale data from last successful run. ETL appears to succeed but returns historical CVEs.
2. **Entertainment frozen Jan 5** — Trakt CLIENT_ID missing. ETL silently skips (by design), data never updates.
3. **Museums only 1 item** — Wikidata SPARQL returns 100 results but 99 fail Pydantic validation (VirtualMuseumModel). Only 1 passes.
4. **SEC EDGAR returns 0 items** — feedparser doesn't send User-Agent header. SEC blocks default UA. Fix: pass request_headers.

### 🟡 MEDIUM
5. **3 WT cron jobs NEVER RUN** — CVE (0681999912af), KG (4b6c5e512e5a), Travel (4c0789ed8fe5). All have null last_run.
6. **CVE cron uses wrong skill** — loads watchtower-news (news category) for intelligence/nvd_cve data.
7. **/health returns 404 from outside** — API listens on prefix `/api/v1`, health is at `/health` (root). CORS/behind proxy may block it.
8. **Product Hunt stale** — in news feed but unknown if ETL runs. Sources show `product_hunt` exists.
9. **Trakt data baked into container image** — code changes need container rebuild.
10. **78 Dependabot vulns** (from previous audit, some may be resolved).

### ✅ GOOD
- Scheduler fixed: 2h interval, API-only restart (not dashboard)
- CORS properly scoped (not wildcard)
- ThreadPoolExecutor with configurable workers (default 4)
- WHO Outbreaks working perfectly
- Gumroad, Viajeros Piratas, Game Deals all fresh

## Fix Plan

### Phase 1 — Code Fixes (repo only, needs rebuild)
- [ ] Fix SEC EDGAR: pass User-Agent to feedparser
- [ ] Fix Museums: relax Pydantic validation or fix SPARQL query
- [ ] Fix NVD: add API key support + better error handling + fallback
- [ ] Fix Entertainment: document Trakt CLIENT_ID requirement

### Phase 2 — Cron Fixes (no rebuild needed)
- [ ] Fix CVE cron: remove wrong skill, add `web` toolset
- [ ] Fix KG cron: add `web` toolset
- [ ] Fix Travel cron: add `web` toolset
- [ ] Force-run all 3 broken crons to verify
- [ ] Remove stale audit files from container (AUDIT_*.md)

### Phase 3 — Improvements
- [ ] Add new cron: Entertainment weekly digest
- [ ] Add new cron: Museums weekly digest
- [ ] Add Research digest cron (ADHD publications)
- [ ] Consider NVD alternatives (OSV.dev, GitHub Advisory DB)
- [ ] API rate limiting
- [ ] Add /health under /api/v1 prefix

## Cron Job Integration Map

| Cron | WT Category | Schedule | Status |
|---|---|---|---|
| Daily News Digest | news | Daily 08:00 | ✅ |
| Daily Loot | games + ecommerce | Daily 20:00 | ✅ |
| Weekly CVE | intelligence/nvd | Tue 09:00 | 🔴 never run |
| Weekly KG | knowledge-garden | Wed 11:00 | 🔴 never run |
| Weekly Travel | travel | Fri 10:00 | 🔴 never run |
| — | entertainment | — | ❌ no cron |
| — | museums | — | ❌ no cron |
| — | research | — | ❌ no cron |
| — | benchmarks | — | ❌ no cron |

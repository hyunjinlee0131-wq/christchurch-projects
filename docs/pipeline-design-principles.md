# Pipeline Design Principles — Christchurch Projects

Date: 2026-11-01 · Companion to `docs/superpowers/specs/2026-11-01-ccc-spatial-projects-design.md` (the "design") and `docs/baseline.md` (the "baseline").

## 0. Status: code vs intention

This document has to match both the code and the intentions, so it starts with what actually exists (updated after the foundation plan, `docs/superpowers/plans/2026-11-01-foundation-ccc-data.md`).

| Piece | Status | Where |
|---|---|---|
| Catalog stage: Hub catalog → `datasets.md` | **Exists**, reproducible | `ccc_data.catalog()`, `build.py` |
| HTTP client (SSL fix, retries, ArcGIS error bodies) | **Exists** | `ccc_data/http.py` |
| Resolve by name (§3 step 2) | **Exists** | `ccc_data.resolve()` |
| Fetch, validate, cache, log (§3 steps 3–4) | **Exists** | `ccc_data.fetch()` |
| Project helpers: `layers.toml`, transform log, web export, manifest (§3 steps 6, 9, 11) | **Exists** | `ccc_data/project.py` |
| Profiling (§3 steps 5, 7) | Planned (plan 3) | — |
| Per-project pipelines and `check()` (§3 steps 8, 10) | Planned (plans 2–4) | `projects/<slug>/pipeline.py` |
| Refresh workflow | Planned (plan 2) | `.github/workflows/refresh.yml` |

Sections marked **(exists)** describe code that runs today. Everything else describes intended behaviour, and the code must be made to match it.

**Public API of `ccc_data` (exists):**
- `catalog(*, page_size=100) -> list[dict]`
- `resolve(service, name) -> LayerRef`
- `fetch(ref, *, exclude_fields=(), refresh=False, max_age_days=35, page_size=None, cache_dir=Path("data/raw"), accept_schema_change=False) -> GeoDataFrame` (EPSG:2193; `.attrs["pulled_at"]` set)
- `load_layers(slug, *, refresh=False, root=Path("projects")) -> dict[str, GeoDataFrame]`
- `log_step(log, step, rows_in, rows_out, note="")`
- `export_web(gdf, path, *, keep, max_mb=5.0, simplify_m=None) -> Path`
- `write_manifest(slug, *, outputs, transform_log, root=Path("projects")) -> Path`
- Exceptions: `ArcGISError`, `LayerNotFound`, `AmbiguousLayer`, `CountMismatch`, `SchemaDrift`

---

## 1. Inputs

### 1.1 CCC open data (primary)
- **Catalog:** the ArcGIS Hub search API, `https://opendata-christchurchcity.hub.arcgis.com/api/search/v1/collections/dataset/items`, 483 dataset records. **(exists, used by `build.py`)**
- **Layers:** ArcGIS REST FeatureServer layers, `https://gis.ccc.govt.nz/server/rest/services/OpenData/<Service>/FeatureServer/<id>`. About 45 distinct layers for the first 10 projects, roughly 1.1 M records (design §7).
- **Observed server facts** (checked 2026-11-01):
  - `maxRecordCount` = 2000 per request (Tree layer); pagination is supported.
  - Native CRS is **NZTM2000, EPSG:2193** (metres).
  - The object-ID field name differs by layer (e.g. `TreeID`, not `OBJECTID`).
  - Output formats: JSON, GeoJSON, PBF.
  - Rows carry `LastEditDate`; layers don't publish a layer-level edit timestamp.

### 1.2 External data (only where the design allows it)
- **OpenStreetMap** `highway=street_lamp` via Overpass, for project 31 only (user decision). Licence ODbL, attribution required. Reachability from this machine is unverified (curl exit 35).

### 1.3 User-generated (runtime, not pipeline input)
- Park votes and 👍/👎 feedback in Supabase. The pipeline **may read aggregates** of these (e.g. vote counts for the People's Choice table) but never writes to them.

### 1.4 Configuration
- One file per project, `projects/<slug>/layers.toml`, listing the layers it needs by **service + layer name** (never by URL or numeric id), plus any fields to drop (e.g. owner fields, which are never fetched).

## 2. Outputs

| Output | Location | Committed? | Consumer |
|---|---|---|---|
| Category list of all datasets **(exists)** | `datasets.md` | yes | humans |
| Raw layer cache (GeoParquet, EPSG:2193, plus `.meta.json`) **(exists)** | `data/raw/<service>__<layer>.parquet` | **no** (gitignored) | pipelines |
| Fetch log (url, record count, cached file bytes, pulled_at, field list hash, from_cache) **(exists)** | `data/raw/_fetch_log.jsonl` | no | pipelines, refresh PR |
| Clean data | `data/clean/<slug>/…parquet` | no | pipelines |
| Profiling (serious projects) | `projects/<slug>/reports/profile_{pre,post}.html`, plus `profile_summary.md` | summary only | humans (baseline A4/A6) |
| Data dictionary | `projects/<slug>/data_dictionary.md` | yes | humans (baseline A3) |
| **Result files** (small, web-ready, EPSG:4326) | `projects/<slug>/outputs/*.{geojson,parquet,json}` | **yes** | site, app |
| Headline metrics | `projects/<slug>/outputs/metrics.json` | yes | home page cards, refresh PR diff |
| Model artefacts (20+21, 39) | `projects/<slug>/outputs/model/` (coefficients, SHAP summaries, metrics) | yes, if small | app, refresh PR |
| Run manifest | `projects/<slug>/outputs/manifest.json` | yes | site/app footer ("data pulled …") |

Every result file has a matching `manifest.json` entry: `data_pulled_at`, source layers with record counts, pipeline git SHA, and a schema version.

## 3. Main steps

```
catalog ─► resolve ─► fetch+cache ─► validate raw ─► [pre-profile] ─► clean ─► [post-profile, go/no-go]
        ─► analyse/model ─► export (4326, slim) ─► self-check ─► manifest
```

Bracketed steps run only for serious projects (baseline A4/A6); fun projects skip them (user override).

1. **Catalog** **(exists: `ccc_data.catalog()`, used by `build.py`)**: page through the Hub search API **with a stable sort** (`sortBy=properties.created`). Without it, pages overlapped and returned only 386 unique datasets out of 483 (observed bug, fixed). Normalise category typos (`Utilties`, `Green Assets`).
2. **Resolve** **(exists)**: for each `(service, layer name)` in `layers.toml`, read the live service listing (`…/FeatureServer?f=json`) and find the layer id. Catalog URLs are not trusted: "Walking Track" no longer exists, and "River Urban Impact" moved to `WaterCharacteristic/22`. A missing layer fails loudly with a list of the nearest names.
3. **Fetch + cache** **(exists)**:
   - Page by `resultOffset` / `resultRecordCount` (≤ `maxRecordCount`), ordered by the layer's own `objectIdField`, in native EPSG:2193.
   - Retry with backoff.
   - HTTPS keeps certificate verification on and clears **only** `ssl.VERIFY_X509_STRICT` (the server's CA lacks a critical Basic Constraints flag).
   - Results are cached as GeoParquet, keyed by layer. A cache hit is reused unless `--refresh` is passed or the cache is older than the configured max age.
   - Each fetch appends to `_fetch_log.jsonl`.
4. **Validate raw** **(exists)**: fetched rows must equal `returnCountOnly`; the field-list hash is compared with the last pull (a change raises `SchemaDrift`). Schema drift stops the pipeline.
5. **Pre-profile** (serious): ydata-profiling report plus `profile_summary.md` (types, missingness, cardinality, outliers, leakage notes, hypotheses).
6. **Clean:** project-specific transforms written as small named functions. Each call appends `(step, rows_in, rows_out, note)` to a transformation log saved with the outputs. No silent row drops.
7. **Post-profile + go/no-go** (serious): re-profile, diff distributions against pre-clean, and write an explicit `GO` / `NO-GO` line into `profile_summary.md`. A `NO-GO` stops the run before analysis.
8. **Analyse / model:** spatial joins and metrics in EPSG:2193 (true metres). Models only where the design lists them (20+21, 39): a baseline first, interpretable models, SHAP for explanations, held-out validation.
9. **Export:** reproject to EPSG:4326, keep only the fields the page shows, simplify geometry for the web, and enforce size budgets (aim < 5 MB per static-site file).
10. **Self-check:** one `check()` per project asserting output invariants (e.g. scores within 0–100, every park has a slug, blockage counts ≥ 0, no owner fields present).
11. **Manifest:** write `manifest.json` and `metrics.json`.

**Refresh (monthly GitHub Action):** runs steps 2–11 with `--refresh` for every project, then opens a **pull request** (it never commits directly) with the `metrics.json` diff in the description. A human merges, and the merge triggers the site deploy.

## 4. Coding and software strategies

- **P1 — Shared core, thin projects.** All network and caching code lives in `ccc_data`. A project pipeline is `layers.toml` plus clean/analyse/export functions. Adding project #11 should not touch `ccc_data`.
- **P2 — Precompute everything; serve static files.** The site and the app never call the council's API at runtime. Visitors only load committed result files, which keeps pages fast and independent of council uptime.
- **P3 — Scripts, not hand downloads.** Every input is fetched by code (baseline A3). `build.py` currently violates this (§0) and will be fixed first.
- **P4 — Resolve by name, verify by count.** Catalog metadata is treated as hints. The live server is the source of truth, and every fetch is checked against the server's own count.
- **P5 — Fail loudly, never silently degrade.** Schema drift, count mismatch, a missing layer or a `NO-GO` stop the run with a clear message. Users see stale-but-dated data rather than wrong data.
- **P6 — Metres for maths, degrees for maps.** Analysis in EPSG:2193; export to EPSG:4326 only at the end.
- **P7 — Idempotent and cached.** Re-running a pipeline with a warm cache gives the same outputs. Raw data stays out of git; results go into git so changes are reviewable as diffs.
- **P8 — Provenance on every output.** A manifest with the pull date, sources and code SHA. Pages display the pull date and attribution (CCC, CC BY 4.0 to be confirmed; OSM ODbL for project 31).
- **P9 — Privacy by omission.** Owner/person fields are excluded at fetch time (not fetched, not just hidden). The self-check asserts they are absent.
- **P10 — Humans gate changed findings.** Automated refresh proposes changes through a PR; it never publishes new findings unreviewed.
- **P11 — One pinned environment.** A root `requirements.txt` with exact versions; Python 3.13 through the `py` launcher on Windows; the same versions in CI.
- **P12 — Minimal, purposeful tests.** One runnable `check()` per pipeline plus one self-check for `ccc_data` (pagination and resolve-by-name against a small layer). No test framework sprawl.
- **P13 — Boring code.** Plain functions, pandas/geopandas, no class hierarchies or plugin systems until a second real use demands one. Deliberate shortcuts are marked `# ponytail:` with their limit and upgrade path.

## 5. How to keep this document true

When pipeline code changes any input, output path, step or principle above, this file changes in the same commit. §0 is updated as planned pieces start to exist.

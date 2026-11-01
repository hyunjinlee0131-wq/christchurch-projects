# Foundation: Repo + `ccc_data` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public Git repo with the shared `ccc_data` package. It fetches any CCC open-data layer by service + layer name, verifies it, caches it, and logs it; it also loads a project's layers from `layers.toml` and writes manifests and web exports. `build.py` is rebuilt on top of it so it's reproducible.

**Architecture:** A plain-function Python package using stdlib `urllib` for HTTP (with the custom SSL context) and geopandas/GeoParquet for data and cache. Unit tests run against fake server responses. Tests marked `live` hit the real CCC server using a 9-record layer.

**Tech Stack:** Python 3.13 (`py` launcher, `.venv`), geopandas, pyogrio, shapely, pyproj, pandas, pyarrow, pytest. Stdlib only for HTTP (`urllib`, `ssl`), TOML (`tomllib`) and fuzzy names (`difflib`).

**Spec:** `docs/superpowers/specs/2026-11-01-ccc-spatial-projects-design.md` and `docs/pipeline-design-principles.md` (the "principles", cited as P1–P13 and §1–§4). Executors read both.

**Plan series** (this is plan 1 of several; later plans are written after this one ships):
1. **Foundation (this plan).**
2. Project 1 Best Park: Astro site, Supabase votes, GitHub Pages deploy, monthly refresh workflow.
3. Project 20+21 Pipes: Streamlit app, profiling template (baseline A1–A9).
4. The remaining eight projects, reusing the two templates.

## Global Constraints

- Python 3.13 run through `py`. Bare `python` is the Windows Store stub; never use it. The venv is `py -3.13 -m venv .venv`, used as `.venv/Scripts/python`.
- HTTPS: `ssl.create_default_context()` with **only** `ssl.VERIFY_X509_STRICT` cleared. Verification stays on (Constraints, design §3).
- Layers are resolved by **service + layer name** from the live listing `https://gis.ccc.govt.nz/server/rest/services/OpenData/<Service>/FeatureServer?f=json`, never from catalog URLs (P4).
- Hub catalog: `https://opendata-christchurchcity.hub.arcgis.com/api/search/v1/collections/dataset/items`, paged with `limit=100&startindex=N&sortBy=properties.created` (the stable sort is required; principles §3 step 1).
- Analysis CRS is EPSG:2193. Web export CRS is EPSG:4326 (P6).
- The raw cache lives in `data/raw/` and is gitignored; outputs are committed (P7).
- All text files are read and written with `encoding="utf-8"` (names with macrons, e.g. Ōtākaro).
- Fail loudly: count mismatch, schema drift and a missing layer each raise a named exception (P5).
- Repo: **public** `hyunjinlee0131-wq/christchurch-projects` (design §4, §11).
- Plain functions, no class hierarchies; deliberate shortcuts are marked `# ponytail:` (P13).
- Tests: `py`-venv `pytest`. Unit tests are the default; live tests run only with `-m live`.

## Review Focus

1. **ArcGIS error bodies arrive as HTTP 200** (seen for removed layers: `{"error":{"code":400,...}}`). These must raise `ArcGISError`, never be parsed as data. Test: Task 2 `test_get_json_raises_on_error_body`.
2. **A network failure or 5xx partway through paging** must retry, then fail without leaving a partial cache file. Test: Task 4 `test_fetch_failure_leaves_no_cache`.
3. **Non-spatial layers (tables)** must still fetch and cache, returning a GeoDataFrame whose geometry is all `None`. Test: Task 4 `test_fetch_table_without_geometry`.
4. **Name variants between catalog and server** ("River Urban Impact" vs `RiverUrbanImpact`, "On-Street Parking Casual") must match after normalisation, and an ambiguous match raises rather than guessing. Test: Task 3 `test_resolve_normalises_names`, `test_resolve_ambiguous_raises`.
5. **A stale or corrupt cache** (older than `max_age_days`, or an unreadable parquet) must trigger a refetch, not a crash or a silent reuse. Test: Task 4 `test_fetch_refetches_stale_cache`, `test_fetch_refetches_corrupt_cache`.

---

## File Structure

```
.gitignore                     data/, .venv/, __pycache__/, *.html under reports/
requirements.txt               direct deps, == pinned
pyproject.toml                 pytest config only (markers, testpaths)
intent.md                      short intent, links to spec (replaces the empty template)
build.py                       MODIFY: uses ccc_data.catalog(), no local items_*.json
ccc_data/__init__.py           re-exports public API
ccc_data/http.py               get_json + SSL context + ArcGISError
ccc_data/catalog.py            catalog()
ccc_data/layers.py             LayerRef, resolve(), LayerNotFound, AmbiguousLayer
ccc_data/fetch.py              fetch(), CountMismatch, SchemaDrift, cache + fetch log
ccc_data/project.py            load_layers(), log_step(), export_web(), write_manifest()
tests/conftest.py              fake_server fixture (routes URL→JSON for get_json)
tests/test_http.py, test_catalog.py, test_layers.py, test_fetch.py, test_project.py
tests/test_live.py             @pytest.mark.live against Recreation / "Dog Exercise Area" (9 rows)
projects/_example/layers.toml  fixture project used by test_project.py
```

---

### Task 1: Repo, environment, HTTP client

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pyproject.toml`, `ccc_data/__init__.py`, `ccc_data/http.py`, `tests/conftest.py`, `tests/test_http.py`
- Modify: `intent.md` (replace the template with a 10-line intent: purpose, the two kinds of project, links to the spec, principles and `datasets.md`)

**Interfaces:**
- Produces:
  - `ccc_data.http.SSL_CONTEXT: ssl.SSLContext`
  - `ccc_data.http.get_json(url: str, params: dict | None = None, *, retries: int = 3, timeout: float = 60.0) -> dict`
  - `ccc_data.http.ArcGISError(Exception)`
  - fixture `fake_server(routes: dict[str, dict | Exception | list])`, which monkeypatches `ccc_data.http._open` so that a URL **without its query string** maps to a response. A list is consumed one item per call, so tests can script paging and failures.

- [ ] **Step 1: Init repo and venv.** `git init`; `py -3.13 -m venv .venv`; `.venv/Scripts/python -m pip install geopandas pyogrio shapely pyproj pandas pyarrow pytest`; write `requirements.txt` with each direct dependency `==` its installed version (`pip show` / `pip freeze | grep`). `.gitignore` covers `data/`, `.venv/`, `__pycache__/`, `projects/*/reports/*.html`. `pyproject.toml` has only `[tool.pytest.ini_options]` with `testpaths=["tests"]`, `markers=["live: hits the real CCC server"]` and `addopts="-m 'not live'"`.
- [ ] **Step 2: Write failing tests** in `tests/test_http.py`:

```python
def test_ssl_context_keeps_verification_but_not_strict():
    from ccc_data.http import SSL_CONTEXT
    import ssl
    assert SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED
    assert SSL_CONTEXT.check_hostname is True
    assert not (SSL_CONTEXT.verify_flags & ssl.VERIFY_X509_STRICT)

def test_get_json_raises_on_error_body(fake_server):
    fake_server({"https://x/layer/5/query": {"error": {"code": 400, "message": "Invalid Layer or Table ID: 5."}}})
    with pytest.raises(ArcGISError, match="Invalid Layer"):
        get_json("https://x/layer/5/query", {"f": "json"})

def test_get_json_retries_then_succeeds(fake_server):
    fake_server({"https://x/q": [URLError("boom"), {"count": 9}]})
    assert get_json("https://x/q", retries=3) == {"count": 9}

def test_get_json_gives_up_after_retries(fake_server):
    fake_server({"https://x/q": [URLError("a"), URLError("b"), URLError("c")]})
    with pytest.raises(URLError):
        get_json("https://x/q", retries=3)
```

- [ ] **Step 3: Run** `.venv/Scripts/python -m pytest tests/test_http.py -v`. Expected: FAIL (import error).
- [ ] **Step 4: Implement `ccc_data/http.py`.** `_open(url: str, timeout: float) -> bytes` is the only function that touches the network (`urllib.request.urlopen(..., context=SSL_CONTEXT)`), so tests patch it. `get_json` URL-encodes `params`, retries on `URLError` and HTTP 5xx with backoff `0.5 * 2**attempt` seconds, parses JSON, and raises `ArcGISError(message + details)` if the body has a top-level `"error"`. Set the `User-Agent` to `christchurch-projects/0.1`.
- [ ] **Step 5: Run tests.** Expected: 4 passed.
- [ ] **Step 6: Commit** `git add -A && git commit -m "chore: repo, env, ccc_data http client"`.

### Task 2: Catalog + reproducible `build.py`

**Files:**
- Create: `ccc_data/catalog.py`, `tests/test_catalog.py`
- Modify: `build.py`. Replace the `glob('items_*.json')` loading with `ccc_data.catalog()`; the output path stays the CLI argument, defaulting to `datasets.md`; the category normalisation, most-specific rule and table format stay as they are.

**Interfaces:**
- Consumes: `get_json`
- Produces: `ccc_data.catalog.catalog(*, page_size: int = 100) -> list[dict]`, the Hub GeoJSON features (each has `id` and `properties`), unique by `id`.

- [ ] **Step 1: Write failing tests:**

```python
def test_catalog_pages_with_stable_sort_and_dedupes(fake_server, monkeypatch):
    # scripted pages: 2 pages of 2, with numberMatched=3 and one overlapping id
    ...
    feats = catalog(page_size=2)
    assert [f["id"] for f in feats] == ["a", "b", "c"]
    assert all("sortBy=properties.created" in u for u in fake_server.calls)

def test_catalog_stops_when_no_next_link(fake_server): ...  # single page, no rel=next -> 1 request
```

`fake_server.calls` records the full requested URLs; add it to the fixture in this task.
- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement `catalog`.** Request `startindex=1, 1+page_size, …` with `sortBy=properties.created`; stop when the page has no `rel=next` link or `features` is empty; dedupe by `id`, keeping first occurrence.
- [ ] **Step 4: Add the live test** in `tests/test_live.py`: `test_catalog_live_matches_number_matched`, asserting `len(catalog()) == first_page["numberMatched"]` and that the ids are unique.
- [ ] **Step 5: Run** `pytest tests/test_catalog.py -v` (pass), then `pytest -m live tests/test_live.py::test_catalog_live_matches_number_matched -v` (pass, about 483).
- [ ] **Step 6: Verify `build.py`.** Run `.venv/Scripts/python build.py datasets.md`; expected stdout `<N> <M>` with N equal to the live `numberMatched`; `git diff --stat datasets.md` shows only count/row churn, not format changes.
- [ ] **Step 7: Commit** `feat: ccc_data.catalog; build.py now self-contained`.

### Task 3: Resolve layers by name

**Files:**
- Create: `ccc_data/layers.py`, `tests/test_layers.py`

**Interfaces:**
- Consumes: `get_json`
- Produces:
  - `@dataclass(frozen=True) LayerRef: service: str; name: str; layer_id: int; url: str; object_id_field: str; max_record_count: int; has_geometry: bool; fields: tuple[str, ...]`
  - `resolve(service: str, name: str) -> LayerRef`
  - `normalise(name: str) -> str`: lowercase, keeping only `[a-z0-9]`
  - `LayerNotFound(Exception)`, whose message lists up to 5 nearest names (`difflib.get_close_matches`, cutoff 0.5)
  - `AmbiguousLayer(Exception)`

- [ ] **Step 1: Write failing tests.** Use a fake service listing with layers `{22: "RiverUrbanImpact", 29: "FishObstruction", 6: "WalkingMountainBikeRoute"}` and a fake layer detail for id 22 (`objectIdField: "RiverUrbanImpactID"`, `maxRecordCount: 2000`, `geometryType: "esriGeometryPolygon"`, `fields: [...]`):

```python
def test_resolve_normalises_names(fake_server):
    ref = resolve("WaterCharacteristic", "River Urban Impact")
    assert ref.layer_id == 22 and ref.object_id_field == "RiverUrbanImpactID"
    assert ref.url.endswith("/OpenData/WaterCharacteristic/FeatureServer/22")
    assert ref.has_geometry is True

def test_resolve_missing_suggests_nearest(fake_server):
    with pytest.raises(LayerNotFound, match="WalkingMountainBikeRoute"):
        resolve("WaterCharacteristic", "Walking Track")

def test_resolve_ambiguous_raises(fake_server):  # listing with "Ward" and "WARD" in one service
    with pytest.raises(AmbiguousLayer): resolve("Electoral", "Ward")

def test_resolve_searches_tables_too(fake_server):  # name present only under "tables"
    assert resolve("Property", "RevaluationValuationRoll").has_geometry is False
```

- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement.** Read `…/FeatureServer?f=json`, search `layers + tables` by `normalise(name)`, then read `…/FeatureServer/<id>?f=json` for the details; `has_geometry = "geometryType" in detail`. Cache listings in a module-level dict for the process lifetime.
- [ ] **Step 4: Run.** Expected 4 passed.
- [ ] **Step 5: Commit** `feat: resolve layers by service + name`.

### Task 4: Fetch, verify, cache, log

**Files:**
- Create: `ccc_data/fetch.py`, `tests/test_fetch.py`
- Modify: `tests/test_live.py`

**Interfaces:**
- Consumes: `get_json`, `LayerRef`
- Produces:
  - `fetch(ref: LayerRef, *, exclude_fields: Iterable[str] = (), refresh: bool = False, max_age_days: int = 35, page_size: int | None = None, cache_dir: Path = Path("data/raw"), accept_schema_change: bool = False) -> gpd.GeoDataFrame` (EPSG:2193; `geometry` is all `None` for tables)
  - `cache_path(ref, cache_dir) -> Path` = `cache_dir / f"{ref.service}__{normalise(ref.name)}.parquet"`, plus a sidecar `.meta.json` holding `{pulled_at (ISO UTC), count, fields_hash, url}`
  - `CountMismatch(Exception)`, `SchemaDrift(Exception)`
  - an appended line in `cache_dir / "_fetch_log.jsonl"`: `{url, service, name, count, bytes, pulled_at, fields_hash, from_cache}`

- [ ] **Step 1: Write failing tests:**

```python
def test_fetch_pages_and_verifies_count(fake_server, tmp_path):
    # count=5, page_size=2 -> 3 query calls ordered by object_id_field
    gdf = fetch(REF, page_size=2, cache_dir=tmp_path)
    assert len(gdf) == 5 and gdf.crs.to_epsg() == 2193
    assert sum("resultOffset" in u for u in fake_server.calls) == 3
    assert all(f"orderByFields={REF.object_id_field}" in u for u in query_calls)

def test_fetch_count_mismatch_raises(fake_server, tmp_path): ...  # count=5 but pages return 4 -> CountMismatch

def test_fetch_failure_leaves_no_cache(fake_server, tmp_path):
    # page 2 raises URLError on every retry
    with pytest.raises(URLError): fetch(REF, page_size=2, cache_dir=tmp_path)
    assert not cache_path(REF, tmp_path).exists()

def test_fetch_uses_cache_then_refetches_stale_cache(fake_server, tmp_path): ...  # 2nd call: 0 network calls; set meta pulled_at 40 days ago -> refetch

def test_fetch_refetches_corrupt_cache(fake_server, tmp_path): ...  # write garbage bytes to the parquet -> refetch, no exception

def test_fetch_excludes_fields_at_request(fake_server, tmp_path):
    fetch(REF, exclude_fields=["OwnerName"], cache_dir=tmp_path)
    assert "OwnerName" not in query_calls[0]  # outFields lists the others explicitly

def test_fetch_schema_drift_raises(fake_server, tmp_path): ...  # cached fields_hash differs from ref.fields -> SchemaDrift on refresh; accept_schema_change=True passes

def test_fetch_table_without_geometry(fake_server, tmp_path): ...  # has_geometry=False -> rows kept, geometry all None, cached

def test_fetch_writes_fetch_log(fake_server, tmp_path): ...  # one jsonl line with count=5, from_cache False; then from_cache True
```

- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement `fetch`.**
  - Count via `returnCountOnly=true`.
  - Page with `where=1=1`, `outFields=<ref.fields minus exclude, comma-joined, or * if no exclude>`, `orderByFields=<oid>`, `resultOffset`, `resultRecordCount=page_size or ref.max_record_count`, and `f=geojson` (geometry layers) or `f=json` (tables).
  - Build the frame with `gpd.GeoDataFrame.from_features(..., crs=4326).to_crs(2193)`; tables get a frame from `attributes` with `geometry=None, crs=2193`.
  - Assert the row count equals the server count, else raise `CountMismatch`.
  - Write the cache **atomically**: write to `*.parquet.tmp`, then `os.replace`. Write the meta, then the log.
  - Cache validity: the meta exists, `pulled_at` is within `max_age_days`, the parquet reads, and `refresh` is False. Any failure means refetch.
  - `fields_hash` = sha256 of the sorted field names.
- [ ] **Step 4: Run.** Expected 9 passed.
- [ ] **Step 5: Live test** `test_fetch_live_dog_exercise_area` in `tests/test_live.py`: `ref = resolve("Recreation", "Dog Exercise Area")`; `gdf = fetch(ref, page_size=4, cache_dir=tmp_path, refresh=True)`. Assert `len(gdf) == 9` (as of 2026-11-01; compare against `returnCountOnly` rather than the literal), `gdf.crs.to_epsg() == 2193`, and that every geometry is valid and inside the Christchurch bounds (2193 easting 1,540,000–1,620,000). Run with `pytest -m live -v`; expected PASS (proves the SSL fix, paging and reprojection end to end).
- [ ] **Step 6: Commit** `feat: fetch with paging, count check, atomic cache, fetch log`.

### Task 5: Project helpers: layers.toml, transform log, web export, manifest

**Files:**
- Create: `ccc_data/project.py`, `projects/_example/layers.toml`, `tests/test_project.py`
- Modify: `ccc_data/__init__.py` (re-export `catalog, resolve, fetch, load_layers, log_step, export_web, write_manifest`, plus the exceptions)

**Interfaces:**
- Consumes: `resolve`, `fetch`
- Produces:
  - `load_layers(slug: str, *, refresh: bool = False, root: Path = Path("projects")) -> dict[str, gpd.GeoDataFrame]`. It reads `root/slug/layers.toml`:
    ```toml
    [layers.park]
    service = "GreenAsset"
    name = "Park"
    exclude = []          # optional
    ```
    Keys are the TOML table names. It records each source `(key, service, name, url, count, pulled_at)` in a module-level `last_sources: list[dict]` for `write_manifest`.
  - `log_step(log: list[dict], step: str, rows_in: int, rows_out: int, note: str = "") -> None`, which appends `{step, rows_in, rows_out, dropped: rows_in - rows_out, note}`
  - `export_web(gdf: gpd.GeoDataFrame, path: Path, *, keep: list[str], max_mb: float = 5.0, simplify_m: float | None = None) -> Path`. It simplifies in 2193 if asked, keeps `keep + ["geometry"]`, writes GeoJSON in 4326 (`.geojson`) or parquet (`.parquet`) based on the suffix, and raises `ValueError` if the file exceeds `max_mb`.
  - `write_manifest(slug: str, *, outputs: list[Path], transform_log: list[dict], root: Path = Path("projects")) -> Path`, which writes `root/slug/outputs/manifest.json` = `{schema_version: 1, data_pulled_at: min(pulled_at of sources), sources: last_sources, outputs: [relative paths], git_sha: <git rev-parse HEAD or "uncommitted">, transform_log}`

- [ ] **Step 1: Write failing tests** (monkeypatch `resolve`/`fetch` with fakes returning a 3-row GeoDataFrame in 2193):

```python
def test_load_layers_reads_toml_and_records_sources(tmp_path, fakes):
    layers = load_layers("_example", root=PROJECTS_FIXTURE)
    assert set(layers) == {"park"} and project.last_sources[0]["count"] == 3

def test_log_step_records_drops():
    log = []; log_step(log, "drop tiny parks", 10, 7, "area < 500 m2")
    assert log == [{"step": "drop tiny parks", "rows_in": 10, "rows_out": 7, "dropped": 3, "note": "area < 500 m2"}]

def test_export_web_reprojects_and_slims(tmp_path):
    out = export_web(gdf_2193, tmp_path / "x.geojson", keep=["name"])
    back = gpd.read_file(out)
    assert back.crs.to_epsg() == 4326 and list(back.columns) == ["name", "geometry"]

def test_export_web_enforces_size_budget(tmp_path):
    with pytest.raises(ValueError, match="MB"): export_web(big_gdf, tmp_path / "x.geojson", keep=["name"], max_mb=0.001)

def test_write_manifest_has_provenance(tmp_path, fakes):
    p = write_manifest("_example", outputs=[...], transform_log=[], root=tmp_path)
    m = json.loads(p.read_text(encoding="utf-8"))
    assert m["schema_version"] == 1 and m["data_pulled_at"] and m["sources"] and "git_sha" in m
```

- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement** with `tomllib` for the TOML. Get `git_sha` from `subprocess.run(["git","rev-parse","HEAD"])`, falling back to `"uncommitted"` on error.
- [ ] **Step 4: Run** the whole unit suite: `.venv/Scripts/python -m pytest -v`. Expected: all pass (about 24).
- [ ] **Step 5: Update `docs/pipeline-design-principles.md` §0.** Mark `ccc_data` as **Exists**, `build.py` as reproducible (remove the "Known gap" paragraph), and correct any names that differ from this plan's Interfaces (principles §5: the doc changes in the same commit).
- [ ] **Step 6: Commit** `feat: project helpers (layers.toml, log, export, manifest)`.

### Task 6: Publish the repo

**Files:** none new.

- [ ] **Step 1: Check what will be published.** Run `git status --ignored` and confirm that `data/` and `.venv/` are ignored and no scratch files (`items_*.json`, `dcat.json`, `counts.py`) are tracked.
- [ ] **Step 2: Run the full checks.** `pytest -v` (unit) and `pytest -m live -v`: both pass.
- [ ] **Step 3: Create and push** with `gh repo create hyunjinlee0131-wq/christchurch-projects --public --source . --push --description "Projects built on Christchurch City Council open spatial data"`. Expected: the repo URL is printed, and `gh repo view hyunjinlee0131-wq/christchurch-projects --json visibility` gives `{"visibility":"PUBLIC"}`.

# Pipe Blockages + Tree Roots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship project 20+21: which Christchurch wastewater pipes block most, why, and do nearby trees make it worse? It's built on the full Data Science Baseline (A1–A9). It's delivered as the first page of a Streamlit app, with a landing card on the static site. This plan also creates the reusable "serious project" template: profiling, the EDA notebook, modelling with SHAP, the Streamlit app shell and its deploy.

**Architecture:**
- **Pipeline:** `projects/pipe_blockages/pipeline.py` uses `ccc_data` to fetch pipes, blockage counts, trees and street centre lines. It cleans them, engineers features in EPSG:2193, fits models, and writes small committed outputs: a parquet of every modelled pipe with a risk score and a plain-language reason, `metrics.json`, `model/` summaries and the manifest.
- **App:** a slim Streamlit app (`app/`, with its own small `requirements.txt`) reads only those outputs. There's no geopandas or modelling at runtime.
- **Static site:** gets a `/pipes/` landing page and a home card with the headline finding, linking to the app.

**Tech Stack:**
- Python 3.13: `ccc_data`, geopandas, pandas, numpy, statsmodels (negative binomial GLM), scikit-learn (CV utilities), lightgbm (Poisson GBM), shap, ydata-profiling, matplotlib/seaborn, jupyter/nbconvert (executes `eda.ipynb`).
- App: streamlit, pydeck, pandas, pyarrow, requests.
- Hosting: Streamlit Community Cloud.

**Spec:** `docs/superpowers/specs/2026-11-01-ccc-spatial-projects-design.md` (§5 baseline, §6 quality bar, §7 project "20 + 21") and `docs/pipeline-design-principles.md`; the baseline itself is `docs/baseline.md`. Executors read all three.

## Global Constraints

- **Population (design §7, Claude's call, made in this plan):** in-service (`ServiceStatus = "In Service"`), CCC-owned (`Ownership = "CCC"`) gravity pipes (`Type ∈ {"Gravity", "Gravity Collector"}`). Pressure, vacuum, vent and overflow pipes are excluded because they fail differently. Every exclusion goes through `log_step`.
- **Target:** `NumberOfBlockages` joined on `WwPipeID`. Pipes absent from the blockage layer count as 0. The layer has no zero rows (checked 2026-11-02), so "absent" means "no recorded blockage". This is cumulative with no dates, so there's no trend analysis anywhere (design §7 data limit). Every page and summary must say "recorded blockages (all time, undated)".
- **Exposure:** pipe length. Models use a `log(length_m)` offset, or rate per km for baselines.
- **Fetch only the needed columns** (`fields` in `layers.toml`; P4/§3):
  - `ww_pipe`: Type, ServiceStatus, Ownership, Construction, NominalDiameter, CommissionDate, Depth, Grade, Treatment, TreatmentDate, drvLength
  - `blockage`: NumberOfBlockages
  - `tree`: Genus, CrownSpread, DiameterAtBreastHeight, Height
  - `street`: (Road layer) the road-name field. Discover it with `resolve("Road", "Street Centre Line").fields` in Task 1 and record it in `layers.toml`.
- **Leakage and reverse causality (A4, A8):** relining (`Treatment`) is often done *because* a pipe blocked. Keep `relined` as a control in the GLM, but report it as "associated with", never "prevents". Exclude it from the GBM risk score used to rank unblocked pipes. Never use anything derived from the target as a feature.
- **Spatial validation:** cross-validation is grouped by a 1 km grid cell (`GroupKFold`, 5 folds), so neighbouring pipes don't leak between train and test.
- **Plain language and honesty (design §2 anti-goals):** association, not causation. Effect sizes come with 95% CIs. Don't call any pipe "safe".
- **Output size:** the app parquet is ≤ 25 MB, using a geometry simplified 1 m and stored as a list of `[lon, lat]` pairs. Static-site files are ≤ 5 MB.
- **Environment:** the root `requirements.txt` gains the pinned modelling and profiling packages; `app/requirements.txt` holds only the app's runtime packages. Use `.venv/Scripts/python` locally.
- **Feedback (baseline B5):** 👍/👎 posts to the existing Supabase `feedback` table (`project = "pipe_blockages"`) via REST with the anon key, read from Streamlit secrets `SUPABASE_URL` / `SUPABASE_ANON_KEY` and hidden if absent. GA4 isn't practical inside Streamlit; Streamlit Cloud's built-in viewer analytics are used instead (Claude's call, recorded in `SUMMARY.md`).

## Review Focus

1. **Pipes with missing attributes** (2,570 have no `CommissionDate`; about 1,900 have no `Construction`; depth and grade are sometimes null): they're kept, with explicit "unknown" categories or median-plus-missing-flag imputation, so they still get a risk score and the counts reconcile. Test: Task 2 `test_features_keep_pipes_with_missing_attributes`.
2. **Zero-length or tiny pipes** (`drvLength` ≤ 0 or < 1 m): `log(0)` offsets would crash or give infinite rates. Pipes under 1 m are dropped through `log_step`, and per-km rates are never computed on them. Test: Task 2 `test_features_drop_degenerate_lengths`.
3. **A blockage `WwPipeID` that isn't in the pipe population** (abandoned or private pipe, or a non-gravity type): it's dropped, the drop is counted and reported, and it never crashes the join. Test: Task 2 `test_join_reports_unmatched_blockage_ids`.
4. **Street search in the app with no match or odd input** (empty, macrons, partial names): the app shows "no pipes on that street" rather than an exception, and the search ignores macrons and case. Test: Task 6 `test_app_street_search_handles_no_match`.
5. **App starting without secrets or with a missing outputs file:** the app renders its results, hides 👍/👎, and shows a clear message if outputs are missing. Test: Task 6 `test_app_runs_without_secrets`.

---

## File Structure

```
projects/pipe_blockages/__init__.py
projects/pipe_blockages/layers.toml
projects/pipe_blockages/README.md            A1: PROJECT CONTEXT block + problem statement
projects/pipe_blockages/data_dictionary.md   A3: generated from layer fields + notes (Task 1)
projects/pipe_blockages/features.py          A5: clean + feature engineering (pure functions)
projects/pipe_blockages/profile.py           A4/A6: pre/post profiling + go/no-go writer
projects/pipe_blockages/model.py             A8: baseline, NB GLM, LightGBM + SHAP, spatial CV
projects/pipe_blockages/pipeline.py          run() + check() + __main__
projects/pipe_blockages/eda.ipynb            A7: executed notebook with annotated figures
projects/pipe_blockages/SUMMARY.md           A9: SCQA executive summary + actions + readiness
projects/pipe_blockages/LAUNCH.md
projects/pipe_blockages/reports/             profile_pre.html, profile_post.html (gitignored), profile_summary.md (committed)
projects/pipe_blockages/outputs/             pipes.parquet, metrics.json, model/*.json, figures/*.png, manifest.json
tests/test_pipe_features.py, tests/test_pipe_model.py, tests/test_pipe_outputs.py
app/Home.py                                  app shell: project list
app/pages/1_Pipe_Blockages.py
app/lib/data.py, app/lib/feedback.py, app/lib/text.py
app/.streamlit/config.toml                   theme = site tokens
app/requirements.txt                         streamlit, pydeck, pandas, pyarrow, requests (pinned)
tests/test_app.py                            streamlit.testing.v1.AppTest
site/src/pages/pipes/index.astro             landing page with headline findings + "Open the tool"
```

---

### Task 1: Problem framing, ingestion, data dictionary, pre-profiling (A1, A3, A4)

**Files:** Create `projects/pipe_blockages/{__init__.py, layers.toml, README.md, data_dictionary.md, profile.py}` and `tests/test_pipe_features.py` (profile part). Modify `requirements.txt` (add pinned statsmodels, scikit-learn, lightgbm, shap, ydata-profiling, matplotlib, seaborn, jupyter, nbconvert, ipykernel).

**Interfaces:**
- Produces:
  - `profile.profile_report(df: pd.DataFrame, title: str, out_html: Path) -> dict`, which writes an HTML report (ydata-profiling, `minimal=True`) and returns a summary `{rows, cols, missing_pct: {col: float}, n_unique: {col: int}}`
  - `profile.write_summary(pre: dict, post: dict | None, notes: list[str], go: bool | None, path: Path) -> None`, which writes `reports/profile_summary.md` with a pre/post table of rows, missing % and unique counts per column, the notes, and a `GO` / `NO-GO` line when `go` is given
- `README.md` holds the baseline's PROJECT CONTEXT block, filled in:
  - **Project name:** Wastewater pipe blockages
  - **Persona:** CCC three-waters asset planners (primary) and residents (secondary)
  - **Value prop:** "Asset planners enter nothing and get a ranked, explained list of gravity pipes most likely to block, plus the measured effect of nearby trees."
  - **Decision:** where to target proactive CCTV inspection, root cutting and relining
  - **KPIs:**
    - top-decile capture: the share of recorded blockages in the 10% of pipe length the model ranks riskiest (target ≥ 40%);
    - the tree effect's IRR with 95% CI;
    - app 👍 ratio.
  - **Cost of inaction:** unplanned blockages cause overflows and callouts.
  - **Constraints:** cumulative undated counts, observational data.
  - **Data sources.**
- `data_dictionary.md` lists, for each fetched field: source layer, type, meaning, % missing, and how it's used (feature, target, filter or dropped).

- [ ] **Step 1: Write the failing test** `test_profile_summary_reports_missingness`. Profile a 4-row frame where one column has 2 of 4 values null; assert `missing_pct[col] == 50.0`. Then call `write_summary(..., go=False)` and assert the file contains "NO-GO".
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_pipe_features.py -q`. Expected: FAIL (import).
- [ ] **Step 3: Implement `profile.py`.** Write `layers.toml` (the four layers with the `fields` lists in Global Constraints), `README.md` and `data_dictionary.md`. The dictionary's % missing values come from Step 5's run.
- [ ] **Step 4: Run tests.** Expected: PASS.
- [ ] **Step 5: Pre-profile the real data** with a `pipeline.py` stub (`python -m projects.pipe_blockages.pipeline --profile-only`): fetch, join (no cleaning), then `profile_report` per layer, then `write_summary(pre, None, notes, None)`. Record the initial hypotheses in the notes:
  - H1: earthenware (EW) and concrete pipes have higher blockage rates than plastic;
  - H2: more trees within 5 m raise the rate after controlling for material and age;
  - H3: certain genera are worse;
  - H4: older and shallower pipes block more;
  - H5: relining is associated with lower rates *after* treatment, but is confounded.
- [ ] **Step 6: Commit** `feat(pipe_blockages): problem framing, ingestion, data dictionary, pre-profiling`.

### Task 2: Cleaning, features, post-profiling go/no-go (A5, A6)

**Files:** Create `projects/pipe_blockages/features.py`. Modify `tests/test_pipe_features.py` and `pipeline.py`.

**Interfaces:**
- Produces (`features.py`; every function takes and returns GeoDataFrames in EPSG:2193, and logs via `log_step`):
  - `MATERIAL_GROUPS: dict[str, str]`:
    - `EW → "Earthenware"`;
    - `CONC`, `RCRR` and other concrete codes → `"Concrete"`;
    - `AC → "Asbestos cement"`;
    - `UPVC`, `PVC`, `PE100`, `HDPE`, other plastics → `"Plastic"`;
    - `CI`, `DI`, `GALV`, steel → `"Metal"`;
    - anything else or null → `"Unknown"`.

    Build the full mapping from the real value list printed in Task 1 Step 5.
  - `ROOT_AGGRESSIVE_GENERA = {"Populus", "Salix", "Eucalyptus", "Ulmus", "Platanus", "Fraxinus", "Quercus", "Acer", "Betula", "Liquidambar"}`. These are commonly cited for sewer root intrusion; cite the source used in `SUMMARY.md`. It's a Claude's call and the list is tunable.
  - `select_population(pipes, log) -> GeoDataFrame`: the in-service, CCC, gravity filter from Global Constraints, plus a drop of pipes with length < 1 m
  - `join_blockages(pipes, blockages, log) -> GeoDataFrame`: left join on `WwPipeID`; `blockages` is filled with 0; it logs how many blockage ids were unmatched and returns them in `gdf.attrs["unmatched_blockage_ids"]`
  - `pipe_features(pipes, as_of: date) -> GeoDataFrame`, which adds:
    - `material` (group);
    - `diameter_mm` (with a `diameter_missing` flag and median imputation);
    - `age_years` from `CommissionDate` (with an `age_missing` flag and median imputation by material);
    - `depth_m` and `grade` (missing flag plus median);
    - `relined` (bool, `Treatment` not null);
    - `length_m`.
  - `tree_features(pipes, trees, radii=(5.0, 10.0)) -> GeoDataFrame`, which adds:
    - `trees_5m` and `trees_10m` (counts within a buffer of the pipe line);
    - `aggressive_trees_10m`;
    - `crown_sum_10m` (sum of `CrownSpread`; null → 0);
    - `trees_per_100m_10m`.

    It uses the `sjoin` + `groupby` pattern from `best_park.score._count`.
  - `street_names(pipes, streets, max_m=40.0) -> Series`: the nearest street centre line name within `max_m` (`gpd.sjoin_nearest`), else `""`
  - `grid_cell(pipes, size_m=1000) -> Series`: `"{x//1000}_{y//1000}"` from the line midpoint; it's the CV group

- [ ] **Step 1: Write failing tests** with synthetic lines and points in EPSG:2193:
  - `test_select_population_filters_type_status_owner_length`: 6 pipes, one per exclusion reason plus one kept; assert the logged drops.
  - `test_join_reports_unmatched_blockage_ids` (Review Focus 3).
  - `test_features_keep_pipes_with_missing_attributes` (Review Focus 1): null CommissionDate and Construction leave the row count unchanged, `age_missing=True`, `material="Unknown"`.
  - `test_features_drop_degenerate_lengths` (Review Focus 2).
  - `test_tree_features_counts_within_radius`: a pipe along y=0 with trees at 3 m, 7 m and 15 m off it gives `trees_5m=1`, `trees_10m=2`.
  - `test_aggressive_trees_counted_by_genus`.
  - `test_street_names_nearest_within_max`.
  - `test_grid_cell_groups_by_km`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement `features.py`.** Wire `pipeline.run()` to load, select, join, add features, tree features and street names. Post-profile the model table and write the go/no-go. **GO** requires:
  - modelled pipes ≥ 30,000;
  - pipes with ≥ 1 blockage ≥ 800;
  - no feature with > 20% missing after imputation flags;
  - unmatched blockage ids ≤ 25% of all blockage ids.

  Otherwise **NO-GO** stops the run with the reason.
- [ ] **Step 4: Run tests** (PASS), then run the real pipeline up to post-profiling. Expected: `profile_summary.md` shows GO with the numbers. Read it; if NO-GO, ledger the reason and adjust the population, with a Ruling.
- [ ] **Step 5: Commit** `feat(pipe_blockages): cleaning, features, post-profiling go/no-go`.

### Task 3: EDA notebook (A7)

**Files:** Create `projects/pipe_blockages/eda.ipynb` and `outputs/figures/*.png`.

**Interfaces:**
- Consumes the cleaned model table, which `pipeline.py` saves as `data/clean/pipe_blockages/model_table.parquet` (gitignored).
- Produces an executed notebook (`jupyter nbconvert --execute --to notebook --inplace`). Each figure has a one-line "what this tells us" markdown cell under it:
  1. blockage rate per km by material, with Poisson CIs;
  2. rate by age decade × material;
  3. rate by `trees_5m` bins (0, 1, 2, 3–5, 6+);
  4. the same, split plastic vs earthenware (interaction);
  5. rate by genus group (aggressive vs other vs none);
  6. a map of the top 200 blocked pipes;
  7. a correlation heatmap of the numeric features;
  8. the relined vs not comparison, with a confounding note.
- It ends with "Modelling hypotheses", which confirms or revises H1–H5 against what the plots show.
- Each figure in 1–6 is saved to `outputs/figures/` (PNG, ≤ 300 KB each) for the app and site.

- [ ] **Step 1: Write the notebook.**
- [ ] **Step 2: Execute** with `.venv/Scripts/python -m jupyter nbconvert --execute --to notebook --inplace projects/pipe_blockages/eda.ipynb`. Expected: exit 0 and 6 PNGs written.
- [ ] **Step 3: Read the figures by eye** and write the hypothesis verdicts into the final cell.
- [ ] **Step 4: Commit** `feat(pipe_blockages): EDA notebook and figures`.

### Task 4: Models: baseline, NB GLM (tree effect), LightGBM + SHAP risk (A8)

**Files:** Create `projects/pipe_blockages/model.py` and `tests/test_pipe_model.py`.

**Interfaces:**
- Produces:
  - `FEATURES_GLM = ["material", "diameter_mm", "age_years", "age_missing", "depth_m", "depth_missing", "grade", "relined", "trees_5m", "aggressive_trees_10m"]`
  - `FEATURES_GBM`: the same minus `relined` (leakage rule), plus `crown_sum_10m`, `trees_10m`, `trees_per_100m_10m`
  - `baseline_rates(df) -> DataFrame`: blockages per km by material, with exact Poisson 95% CIs
  - `fit_glm(df) -> GlmResult`, a dataclass of `params`, `irr`, `ci_low`, `ci_high`, `p`, `alpha`, `aic` per term. It's a statsmodels negative binomial GLM with `offset=log(length_m)`, Plastic as the material reference, and α estimated by `NegativeBinomial` ML then passed to the GLM.
  - `tree_effect(glm: GlmResult) -> dict = {"irr_per_tree_5m", "ci", "p", "irr_aggressive_10m", "ci_aggr", "p_aggr", "sentence"}`. The `sentence` is plain English, e.g. "Each extra tree within 5 m of a pipe is associated with 12% more recorded blockages (95% CI 8–16%), after allowing for material, age, size, depth and relining."
  - `cv_gbm(df, groups, seed=7) -> dict`: 5-fold `GroupKFold` LightGBM (`objective="poisson"`, offset as `init_score=log(length_m)`), returning out-of-fold predictions plus:
    - `poisson_deviance` (GBM vs GLM vs the material-baseline);
    - `top_decile_capture` (the share of blockages in the top 10% of *pipe length* by predicted rate);
    - `auc_any_blockage`.
  - `fit_gbm_and_explain(df) -> (model, shap_values: ndarray, expected_value)`: final fit on all data, with `shap.TreeExplainer`
  - `reasons(shap_row, feature_values, top=2) -> str`: plain-language top drivers with percentage shares of positive SHAP, e.g. "Earthenware pipe (45%), 6 trees within 10 m (30%)", using a `FEATURE_PHRASES` mapping
  - `risk_band(pred_rate_pct) -> "Very high" | "High" | "Medium" | "Low"`, by percentile of predicted rate: ≥ 95th, ≥ 80th, ≥ 50th, else Low. Never "safe".

- [ ] **Step 1: Write failing tests** on simulated data, where the truth is known:
  - `test_glm_recovers_planted_tree_effect`: simulate 20,000 pipes with NB counts where IRR(tree_5m)=1.15, earthenware=2.0 and other covariates random; assert the fitted IRR CI contains 1.15 and the earthenware IRR CI contains 2.0.
  - `test_baseline_rates_per_km_with_ci`: 2 materials with known totals; check rate and CI ordering.
  - `test_cv_gbm_beats_baseline_on_signal`: on the simulated data, GBM top-decile capture > baseline's and > 0.10.
  - `test_reasons_names_top_drivers`: hand-made SHAP row gives the expected phrase order and percentages summing to ≤ 100.
  - `test_risk_band_never_says_safe`: every output value is in the 4 labels.
  - `test_gbm_features_exclude_relined` (leakage rule).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement `model.py`.**
- [ ] **Step 4: Run tests.** Expected: PASS. The full suite stays green.
- [ ] **Step 5: Run on the real data.** Print the baseline rates, the GLM table, the tree effect sentence and the CV metrics. **Sanity gate:**
  - GLM converges;
  - earthenware IRR > 1;
  - CV top-decile capture is greater than the material-only baseline's.

  If the tree effect isn't significant, report that honestly; it's a valid answer to Q21. Ledger the numbers.
- [ ] **Step 6: Commit** `feat(pipe_blockages): baseline, NB GLM tree effect, LightGBM + SHAP with spatial CV`.

### Task 5: Outputs, check(), executive summary (A9)

**Files:** Modify `pipeline.py`. Create `tests/test_pipe_outputs.py`, `SUMMARY.md`, `outputs/*`.

**Interfaces:**
- `outputs/pipes.parquet`: one row per modelled pipe. Columns:
  - `id`, `street`, `material`, `diameter_mm`, `age_years` (null if unknown), `length_m`, `blockages`;
  - `pred_rate_per_km`, `risk_band`, `risk_pct` (percentile 0–100), `reason` (string);
  - `trees_5m`, `trees_10m`, `aggressive_trees_10m`;
  - `path` (list of `[lon, lat]`, 4326, simplified 1 m).

  It's ≤ 25 MB.
- `outputs/metrics.json`:
  ```json
  {"schema_version": 1, "data_pulled_at": "...", "n_pipes": 0, "n_blocked": 0, "total_blockages": 0,
   "tree_effect": {"irr_per_tree_5m": 0, "ci": [0, 0], "p": 0, "sentence": "..."},
   "aggressive_effect": {"irr": 0, "ci": [0, 0], "p": 0},
   "cv": {"top_decile_capture": 0, "baseline_top_decile_capture": 0, "poisson_deviance": {"glm": 0, "gbm": 0, "baseline": 0}, "auc_any_blockage": 0},
   "rates_by_material": [{"material": "...", "per_km": 0, "ci": [0, 0], "km": 0}],
   "headline": "..."}
  ```
- `outputs/model/glm_table.json` (term, IRR, CI, p) and `outputs/model/shap_importance.json` (feature, mean |SHAP|).
- `check(out_dir)` asserts:
  - the files exist;
  - `n_pipes ≥ 30000`;
  - `risk_band` is in the 4 labels;
  - `risk_pct` is in 0–100;
  - the `blockages` sum equals `total_blockages`;
  - `pred_rate_per_km ≥ 0`;
  - every `path` has ≥ 2 points inside lon 172.3–173.2 and lat −43.95 to −43.35;
  - the tree-effect CI is ordered and contains the IRR;
  - the parquet is ≤ 25 MB;
  - the word "safe" appears in no `reason`.
- `SUMMARY.md` in SCQA form (Situation, Complication, Question, Answer):
  - the headline numbers;
  - the tree effect sentence;
  - the material ranking;
  - recommended actions (e.g. CCTV-inspect the "Very high" earthenware pipes with ≥ N trees within 5 m first; the km involved; expected blockage share covered);
  - limitations (undated cumulative counts, observational data, relining confounding, recorded-tree coverage);
  - next steps;
  - readiness: "MVP ready" or not, with reasons.

- [ ] **Step 1: Write failing tests** in `test_pipe_outputs.py`: `test_committed_outputs_pass_check`, `test_check_rejects_safe_wording`, `test_check_rejects_blockage_total_mismatch`.
- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement** the output writing, `check()` and `__main__` (`python -m projects.pipe_blockages.pipeline [--refresh]` prints `pipe_blockages: <n> pipes, top-decile capture <x>%, trees IRR <y>`). Write `SUMMARY.md` from the real numbers.
- [ ] **Step 4: Run the full pipeline and tests.** Expected: PASS and the summary line printed.
- [ ] **Step 5: Update the principles doc** (§0: pipelines exist for `pipe_blockages`; profiling exists) **and the refresh workflow.** It runs all pipelines already; add `--refresh` timing to the PR body, since this pipeline is heavier.
- [ ] **Step 6: Commit** `feat(pipe_blockages): outputs, check, executive summary`.

### Task 6: Streamlit app shell + Pipe Blockages page (B1–B3, B5)

**Files:** Create `app/Home.py`, `app/pages/1_Pipe_Blockages.py`, `app/lib/{data.py, feedback.py, text.py}`, `app/.streamlit/config.toml`, `app/requirements.txt` and `tests/test_app.py`.

**Interfaces:**
- `app/lib/data.py`:
  - `OUTPUTS = Path(__file__).parents[2] / "projects"`;
  - `load_pipes() -> pd.DataFrame | None` (`st.cache_data`; None if the file is missing);
  - `load_metrics(slug) -> dict | None`;
  - `fold(s) -> str` (NFKD, no combining marks, lowercase);
  - `search_street(df, q) -> pd.DataFrame`.
- `app/lib/feedback.py`: `send_feedback(project, item_id, value) -> bool`, which POSTs to `{SUPABASE_URL}/rest/v1/feedback` with a 5 s timeout and returns False on any error or when no secrets are set. Also `feedback_enabled() -> bool`.
- `app/lib/text.py`: `plural(n, word)` and `pct(x)`.
- **Page layout, first screen, with no input needed (B1):**
  - a headline `st.metric` row: pipes analysed, recorded blockages, the tree effect ("+12% per tree within 5 m") and top-decile capture;
  - a one-paragraph plain-language answer;
  - a pydeck `PathLayer` map coloured by `risk_band`, showing "Very high" and "High" by default with a toggle for all. Its tooltip shows street, material, age, blockages, risk band and reason.
- **Below the map:**
  - "Search your street" (`st.text_input`) shows a table of that street's pipes with risk band and reason, or "No pipes found on that street" (Review Focus 4);
  - a "Top 20 pipes to inspect first" table (unblocked pipes ranked by risk, plus the most-blocked pipes);
  - a "Why" section with the material rate chart (from `rates_by_material`) and the SHAP importance bar chart, each with a "what to do with this" caption (B3);
  - a "How this was worked out" expander: data, population, model, validation and limitations;
  - 👍/👎 under the answer when feedback is enabled (B5), plus the data date and attribution.
- **Theme:** `app/.streamlit/config.toml` uses `primaryColor = "#1f6f5c"`, `backgroundColor = "#f7f6f2"` and `textColor = "#1c2321"`, matching `site/src/styles/tokens.css`.
- **`app/requirements.txt`:** streamlit, pydeck, pandas, pyarrow, requests, `==`-pinned to the versions installed in `.venv`.

- [ ] **Step 1: Write failing tests** in `tests/test_app.py` with `streamlit.testing.v1.AppTest`:
  - `test_app_page_renders_headline_metrics` (at least 4 `metric` elements, no exceptions);
  - `test_app_street_search_handles_no_match` (enter "zzzz", then the "No pipes found" text shows and nothing raises);
  - `test_app_street_search_ignores_macrons`;
  - `test_app_runs_without_secrets` (no 👍/👎 buttons, no exceptions);
  - `test_app_missing_outputs_shows_message` (monkeypatch `OUTPUTS` to an empty temp dir, then the info message shows).
- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement the app.** Run it locally with `.venv/Scripts/python -m streamlit run app/Home.py`. Take Playwright screenshots of the page at 390 and 1280 wide, and check by eye: results on the first screen, no horizontal scroll, readable map.
- [ ] **Step 4: Run tests.** Expected: PASS. The full Python suite stays green.
- [ ] **Step 5: Commit** `feat(app): Streamlit shell and Pipe Blockages page`.

### Task 7: Site landing page, deploy, launch notes

**Files:** Create `site/src/pages/pipes/index.astro` and `projects/pipe_blockages/LAUNCH.md`. Modify `site/src/pages/index.astro` (second card), `site/src/layouts/Base.astro` (nav link), `site/e2e/smoke.spec.ts`, `.github/workflows/deploy.yml` (env `PUBLIC_STREAMLIT_URL`) and `SETUP.md`.

**Interfaces:**
- `/pipes/` shows:
  - the headline answer from `metrics.json` (tree effect sentence, top-decile capture);
  - figures from `outputs/figures` (copied by `sync-data.mjs`, so extend it to copy `figures/*.png` into `public/data/<project>/figures/`);
  - an "Open the interactive tool" button linking to `PUBLIC_STREAMLIT_URL`. If that's unset, it says "Interactive tool coming soon".
- The home card is "Serious · tool": "Which sewer pipes block, and do trees cause it?", with the headline from `metrics.json`.
- **Deploy needs the user** (Streamlit Community Cloud can't be created from the CLI). `SETUP.md` §Streamlit covers:
  1. sign in at share.streamlit.io with GitHub;
  2. New app: repo `hyunjinlee0131-wq/christchurch-projects`, branch `main`, file `app/Home.py`, Python 3.13;
  3. Advanced → Secrets: `SUPABASE_URL` / `SUPABASE_ANON_KEY` (the same values as the site);
  4. copy the app URL into the repo secret `PUBLIC_STREAMLIT_URL` and re-run "Deploy site".
- `LAUNCH.md`: a story post ("Do street trees really block our sewers? I checked 46,000 pipes"). Targets: r/chch, LinkedIn (asset management and water industry), Water New Zealand community groups. First-week checks.

- [ ] **Step 1: Write failing e2e tests:** `pipes page shows headline finding and tool link or coming-soon`, and `home lists both projects`.
- [ ] **Step 2: Run.** Expected FAIL.
- [ ] **Step 3: Implement** the page, card, nav, sync of figures, deploy env, SETUP and LAUNCH.
- [ ] **Step 4: Run** vitest, build and the whole Playwright suite. Expected: all pass.
- [ ] **Step 5: Commit**, then hand the Streamlit deploy steps to the user. The final whole-branch review happens before merge and push (as in plan 2).

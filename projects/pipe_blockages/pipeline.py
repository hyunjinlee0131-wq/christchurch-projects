"""Pipe blockages + tree roots pipeline.

Run: python -m projects.pipe_blockages.pipeline [--refresh] [--profile-only] [--table-only]
"""
import json
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd

from ccc_data import load_layers

from .features import grid_cell, join_blockages, pipe_features, select_population, street_names, tree_features
from .profile import profile_report, write_summary

SLUG = "pipe_blockages"
HERE = Path(__file__).parent
REPORTS = HERE / "reports"
CLEAN = Path("data/clean") / SLUG
TABLE = CLEAN / "model_table.parquet"

HYPOTHESES = [
    "H1: earthenware (EW) and concrete pipes have higher blockage rates per km than plastic.",
    "H2: more trees within 5 m of a pipe raise its blockage rate after allowing for material and age.",
    "H3: root-aggressive genera (willow, poplar, gum, elm, plane, ash, oak, maple, birch, liquidambar) matter more than tree count alone.",
    "H4: older and shallower pipes block more.",
    "H5: relined pipes show lower rates, but relining is often done because a pipe blocked (confounded).",
]

# Go/no-go thresholds for modelling (baseline A6).
MIN_PIPES = 30_000
MIN_BLOCKED = 800
MAX_MISSING_PCT = 20.0
MAX_UNMATCHED_SHARE = 0.25
MODEL_COLUMNS = ["material", "diameter_mm", "age_years", "depth_m", "grade", "relined", "length_m", "trees_5m",
                 "trees_10m", "aggressive_trees_10m", "crown_sum_10m", "trees_per_100m_10m", "street", "cell", "blockages"]


def build_table(*, refresh: bool = False, as_of: date | None = None) -> tuple[gpd.GeoDataFrame, list[dict]]:
    """Fetch → clean → features → post-profile → go/no-go. Returns the model table and the transform log."""
    layers = load_layers(SLUG, refresh=refresh)
    raw = layers["ww_pipe"]
    pre = profile_report(raw, "Wastewater pipes (raw)", REPORTS / "profile_pre.html")

    log: list[dict] = []
    pipes = select_population(raw, log)
    pipes = join_blockages(pipes, layers["blockage"], log)
    unmatched = pipes.attrs["unmatched_blockage_ids"]
    pipes = pipe_features(pipes, as_of=as_of or date.today())
    pipes = tree_features(pipes, layers["tree"])
    pipes["street"] = street_names(pipes, layers["street"])
    pipes["cell"] = grid_cell(pipes)
    table = pipes[["WwPipeID", *MODEL_COLUMNS, "diameter_missing", "age_missing", "depth_missing", "grade_missing", "geometry"]]
    table = table.rename(columns={"WwPipeID": "id"}).reset_index(drop=True)
    table.attrs = {}

    post = profile_report(table, "Pipe model table (clean)", REPORTS / "profile_post.html")
    n_blocked = int((table["blockages"] > 0).sum())
    unmatched_share = len(unmatched) / max(1, len(layers["blockage"]))
    worst_missing = max(post["missing_pct"].values())
    reasons = []
    if len(table) < MIN_PIPES:
        reasons.append(f"only {len(table)} pipes (< {MIN_PIPES})")
    if n_blocked < MIN_BLOCKED:
        reasons.append(f"only {n_blocked} blocked pipes (< {MIN_BLOCKED})")
    if worst_missing > MAX_MISSING_PCT:
        reasons.append(f"a column is {worst_missing}% missing after imputation (> {MAX_MISSING_PCT}%)")
    if unmatched_share > MAX_UNMATCHED_SHARE:
        reasons.append(f"{unmatched_share:.0%} of blocked pipe ids fall outside the population (> {MAX_UNMATCHED_SHARE:.0%})")
    go = not reasons
    notes = [
        f"Modelled pipes: {len(table):,}; with ≥1 recorded blockage: {n_blocked:,}; recorded blockages: {int(table.blockages.sum()):,}.",
        f"Blocked pipe ids outside the population: {len(unmatched):,} of {len(layers['blockage']):,} ({unmatched_share:.0%}).",
        "Missing values are imputed (median; age by material first) with *_missing flags kept as features.",
        *[f"Transform: {s['step']} ({s['rows_in']:,} → {s['rows_out']:,})" for s in log],
        *HYPOTHESES,
        *(f"NO-GO reason: {r}" for r in reasons),
    ]
    write_summary(pre, post, notes, go, REPORTS / "profile_summary.md")
    if not go:
        raise SystemExit(f"{SLUG}: NO-GO for modelling: {'; '.join(reasons)}")
    CLEAN.mkdir(parents=True, exist_ok=True)
    table.to_parquet(TABLE)
    (CLEAN / "transform_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    return table, log


OUT = HERE / "outputs"
APP_MAX_MB = 25.0
LON, LAT = (172.3, 173.2), (-43.95, -43.35)


def run(*, refresh: bool = False, out_dir: Path = OUT) -> Path:
    """Full pipeline: table → models → outputs (pipes.parquet, metrics.json, model/*.json, manifest.json)."""
    import numpy as np
    import pandas as pd

    from ccc_data import project, write_manifest

    from .model import (band_capture, baseline_rates, cv_gbm, fit_gbm_and_explain, fit_glm, headline, reasons,
                        risk_band, tree_claim, tree_effect)

    table, log = build_table(refresh=refresh)
    rates = baseline_rates(table)
    # Lead model leaves relining out: pipes are relined *because* they blocked, so adjusting for it can hide effects.
    glm = fit_glm(table, exclude=("relined",))
    eff = tree_effect(glm)
    claim = tree_claim(eff["irr_per_tree_5m"], eff["ci"])
    sens = {"with_relined": tree_effect(fit_glm(table)),
            "without_depth_missing": tree_effect(fit_glm(table, exclude=("relined", "depth_missing")))}
    t = glm.table.set_index("term")
    aggr = t.loc["aggressive_trees_10m"]
    cv = cv_gbm(table, table["cell"])
    _, shap_values, _, X, pred = fit_gbm_and_explain(table)

    df = table.copy()
    df["pred_rate_per_km"] = (pred / df["length_m"] * 1000).round(3)
    df["risk_pct"] = (df["pred_rate_per_km"].rank(pct=True) * 100).round(1)
    df["risk_band"] = df["risk_pct"].map(risk_band)
    cols = list(X.columns)
    df["reason"] = [reasons(dict(zip(cols, row)), X.iloc[i].to_dict()) for i, row in enumerate(shap_values)]
    df.loc[df["age_missing"], "age_years"] = np.nan
    geo = df.geometry.line_merge().simplify(1.0).to_crs(4326)
    # A few pipes are multi-part; the app draws one path per pipe, so use the longest part.
    geo = geo.map(lambda g: max(g.geoms, key=lambda part: part.length) if g.geom_type.startswith("Multi") else g)
    df["path"] = [[[round(x, 6), round(y, 6)] for x, y in g.coords] for g in geo]

    out_dir = Path(out_dir)
    (out_dir / "model").mkdir(parents=True, exist_ok=True)
    keep = ["id", "street", "material", "diameter_mm", "age_years", "length_m", "blockages", "pred_rate_per_km",
            "risk_band", "risk_pct", "reason", "trees_5m", "trees_10m", "aggressive_trees_10m", "path"]
    pd.DataFrame(df[keep]).round({"length_m": 1, "age_years": 0, "diameter_mm": 0}).to_parquet(out_dir / "pipes.parquet", index=False)

    shap_imp = pd.Series(np.abs(shap_values).mean(axis=0), index=cols).sort_values(ascending=False)
    (out_dir / "model" / "glm_table.json").write_text(json.dumps({"terms": glm.table.round(4).to_dict("records"),
        "alpha": round(glm.alpha, 3), "aic": round(glm.aic, 1), "dropped": glm.dropped}, indent=2), encoding="utf-8", newline="\n")
    (out_dir / "model" / "shap_importance.json").write_text(json.dumps(
        [{"feature": k, "mean_abs_shap": round(float(v), 5)} for k, v in shap_imp.items()], indent=2), encoding="utf-8", newline="\n")

    pulled = min(s["pulled_at"] for s in project.last_sources if s.get("pulled_at"))
    km = df["length_m"].sum() / 1000
    top10_km = 0.1 * km
    metrics = {
        "schema_version": 1, "data_pulled_at": pulled,
        "n_pipes": int(len(df)), "km": round(float(km), 1), "n_blocked": int((df.blockages > 0).sum()),
        "total_blockages": int(df.blockages.sum()),
        "tree_effect": {"irr_per_tree_5m": round(float(eff["irr_per_tree_5m"]), 4), "ci": [round(float(x), 4) for x in eff["ci"]],
                        "p": round(float(eff["p"]), 4), "sentence": eff["sentence"], **claim},
        "tree_effect_sensitivity": {k: {"irr_per_tree_5m": round(float(v["irr_per_tree_5m"]), 4),
                                        "ci": [round(float(x), 4) for x in v["ci"]]} for k, v in sens.items()},
        "very_high_out_of_sample": band_capture(cv["oof_pred"] / table["length_m"].to_numpy(), table["blockages"].to_numpy(),
                                                table["length_m"].to_numpy(), top_pct=5),
        "aggressive_effect": {"irr": round(float(aggr.irr), 4), "ci": [round(float(aggr.ci_low), 4), round(float(aggr.ci_high), 4)],
                              "p": round(float(aggr.p), 4)},
        "cv": {"top_decile_capture": round(cv["top_decile_capture"], 4), "glm_top_decile_capture": round(cv["glm_top_decile_capture"], 4),
               "baseline_top_decile_capture": round(cv["baseline_top_decile_capture"], 4),
               "poisson_deviance": {k: round(v, 4) for k, v in cv["poisson_deviance"].items()}, "auc_any_blockage": round(cv["auc_any_blockage"], 4)},
        "rates_by_material": [{"material": r.material, "per_km": round(float(r.per_km), 3), "ci": [round(float(r.ci_low), 3), round(float(r.ci_high), 3)],
                               "km": round(float(r.km), 1), "blockages": int(r.blockages)} for r in rates.itertuples() if r.km >= 5],
        "drivers": [{"term": r.term, "irr": round(r.irr, 3), "ci": [round(r.ci_low, 3), round(r.ci_high, 3)], "p": round(r.p, 4)}
                    for r in glm.table.itertuples()],
        "headline": headline(cv["top_decile_capture"], top10_km, claim),
        "answer": _answer(glm.table),
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    figures = sorted((out_dir / "figures").glob("*.png"))
    write_manifest(SLUG, outputs=[out_dir / "pipes.parquet", out_dir / "metrics.json", out_dir / "model" / "glm_table.json",
                                  out_dir / "model" / "shap_importance.json", *figures], transform_log=log, root=HERE.parent)
    return out_dir


def _answer(table) -> str:
    """Plain-language summary of the clearest drivers, built from the fitted model (never hard-coded)."""
    t = table.set_index("term")

    def pct(term: str) -> str | None:
        if term not in t.index or t.loc[term, "ci_low"] < 1 < t.loc[term, "ci_high"]:
            return None
        irr = t.loc[term, "irr"]
        return f"{irr - 1:+.0%}" if irr >= 1 else f"{irr - 1:+.0%}"

    parts = []
    if (a := pct("age (per 10 years)")):
        parts.append(f"older pipes have more recorded blockages ({a} per extra 10 years, partly because they've had longer to block)")
    if (d := pct("diameter (per 100 mm)")):
        parts.append(f"wider pipes have fewer ({d} per extra 100 mm)")
    return ("Small, old pipes stand out: " + "; ".join(parts) + ".") if parts else ""


def check(out_dir: Path = OUT) -> None:
    import pandas as pd

    from .model import RISK_BANDS

    out_dir = Path(out_dir)
    for f in ["pipes.parquet", "metrics.json", "manifest.json", "model/glm_table.json", "model/shap_importance.json"]:
        assert (out_dir / f).exists(), f"missing {f}"
    assert (out_dir / "pipes.parquet").stat().st_size <= APP_MAX_MB * 1e6, "pipes.parquet over size budget"
    m = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(out_dir / "pipes.parquet")
    assert m["schema_version"] == 1 and m["n_pipes"] == len(df) >= MIN_PIPES, "pipe count"
    assert int(df["blockages"].sum()) == m["total_blockages"], "blockages total does not match metrics"
    assert set(df["risk_band"]) <= set(RISK_BANDS), "unknown risk band"
    assert df["risk_pct"].between(0, 100).all() and (df["pred_rate_per_km"] >= 0).all(), "risk out of range"
    assert not df["reason"].str.contains(r"\bsafe\b", case=False).any(), "a reason calls a pipe safe"
    eff = m["tree_effect"]
    assert eff["ci"][0] <= eff["irr_per_tree_5m"] <= eff["ci"][1], "tree effect CI does not contain the estimate"
    unclear = eff["ci"][0] < 1 < eff["ci"][1]
    assert ("no clear sign" in m["headline"]) == unclear, "headline contradicts the tree-effect CI"
    assert ("no clear evidence" in eff["sentence"]) == unclear and eff["clear"] == (not unclear), "tree wording contradicts the CI"
    for path in df["path"]:
        assert len(path) >= 2, "pipe path too short"
        for lon, lat in path:
            assert LON[0] <= lon <= LON[1] and LAT[0] <= lat <= LAT[1], "pipe outside Christchurch"


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    if "--table-only" in sys.argv or "--profile-only" in sys.argv:
        t, _ = build_table(refresh=refresh)
        print(f"{SLUG}: model table {len(t):,} pipes, {int((t.blockages > 0).sum()):,} blocked — GO")
    else:
        out = run(refresh=refresh)
        check(out)
        m = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
        print(f"{SLUG}: {m['n_pipes']:,} pipes, top-decile capture {m['cv']['top_decile_capture']:.1%}, "
              f"trees IRR {m['tree_effect']['irr_per_tree_5m']:.3f}")

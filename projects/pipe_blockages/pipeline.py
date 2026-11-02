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


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    if "--table-only" in sys.argv or "--profile-only" in sys.argv:
        t, _ = build_table(refresh=refresh)
        print(f"{SLUG}: model table {len(t):,} pipes, {int((t.blockages > 0).sum()):,} blocked — GO")

"""Pipe blockages + tree roots pipeline. Run: python -m projects.pipe_blockages.pipeline [--refresh] [--profile-only]"""
import sys
from pathlib import Path

from ccc_data import load_layers

from .profile import profile_report, write_summary

SLUG = "pipe_blockages"
HERE = Path(__file__).parent
REPORTS = HERE / "reports"

HYPOTHESES = [
    "H1: earthenware (EW) and concrete pipes have higher blockage rates per km than plastic.",
    "H2: more trees within 5 m of a pipe raise its blockage rate after allowing for material and age.",
    "H3: root-aggressive genera (willow, poplar, gum, elm, plane, ash, oak, maple, birch, liquidambar) matter more than tree count alone.",
    "H4: older and shallower pipes block more.",
    "H5: relined pipes show lower rates, but relining is often done because a pipe blocked (confounded).",
]


def profile_only(refresh: bool = False) -> None:
    layers = load_layers(SLUG, refresh=refresh)
    pre = profile_report(layers["ww_pipe"], "Wastewater pipes (raw)", REPORTS / "profile_pre.html")
    notes = [f"{k}: {len(v):,} rows" for k, v in layers.items()] + HYPOTHESES
    write_summary(pre, None, notes, None, REPORTS / "profile_summary.md")
    print(f"{SLUG}: pre-profile written for {pre['rows']:,} pipes")


if __name__ == "__main__":
    if "--profile-only" in sys.argv:
        profile_only(refresh="--refresh" in sys.argv)

"""Pre/post profiling (baseline A4, A6): an HTML report per table plus a committed markdown summary."""
from pathlib import Path

import pandas as pd


def profile_report(df: pd.DataFrame, title: str, out_html: Path) -> dict:
    from ydata_profiling import ProfileReport  # heavy import, only when profiling

    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    plain = pd.DataFrame(df.drop(columns="geometry", errors="ignore"))
    ProfileReport(plain, title=title, minimal=True, progress_bar=False).to_file(out_html)
    return {
        "rows": len(plain),
        "cols": plain.shape[1],
        "missing_pct": {c: round(100 * float(plain[c].isna().mean()), 1) for c in plain.columns},
        "n_unique": {c: int(plain[c].nunique(dropna=True)) for c in plain.columns},
    }


def write_summary(pre: dict, post: dict | None, notes: list[str], go: bool | None, path: Path) -> None:
    cols = list(dict.fromkeys(list(pre["missing_pct"]) + list((post or {}).get("missing_pct", {}))))
    lines = ["# Data quality summary", "", f"Rows before cleaning: **{pre['rows']}**"
             + (f" · after: **{post['rows']}**" if post else ""), "",
             "| column | missing % (pre) | unique (pre) |" + (" missing % (post) | unique (post) |" if post else ""),
             "|---|---|---|" + ("---|---|" if post else "")]
    for c in cols:
        row = f"| {c} | {pre['missing_pct'].get(c, '—')} | {pre['n_unique'].get(c, '—')} |"
        if post:
            row += f" {post['missing_pct'].get(c, '—')} | {post['n_unique'].get(c, '—')} |"
        lines.append(row)
    lines += ["", "## Notes and hypotheses", ""] + [f"- {n}" for n in notes]
    if go is not None:
        lines += ["", f"## Decision: **{'GO' if go else 'NO-GO'}** for modelling"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

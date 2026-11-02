"""Models for pipe blockages (baseline A8).

- baseline_rates: blockages per km by material (exact Poisson CIs)
- fit_glm: negative-binomial GLM with a log(length) offset → interpretable effects (incl. the tree question)
- cv_gbm: LightGBM Poisson with spatial GroupKFold → risk ranking, validated against the GLM and the material baseline
- fit_gbm_and_explain + reasons: SHAP → plain-language "why" per pipe
"""
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2
from sklearn.metrics import mean_poisson_deviance, roc_auc_score
from sklearn.model_selection import GroupKFold

FEATURES_GLM = ["material", "diameter_mm", "age_years", "age_missing", "depth_m", "depth_missing", "grade",
                "grade_missing", "relined", "trees_5m", "aggressive_trees_10m"]
# relined is excluded from the risk score: pipes are relined *because* they blocked (reverse causation).
FEATURES_GBM = ["material", "diameter_mm", "age_years", "age_missing", "depth_m", "depth_missing", "grade",
                "grade_missing", "trees_5m", "trees_10m", "aggressive_trees_10m", "crown_sum_10m", "trees_per_100m_10m"]
RISK_BANDS = ["Very high", "High", "Medium", "Low"]
MATERIAL_REF = "Plastic"
GBM_PARAMS = dict(objective="poisson", n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=50,
                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)

# Units for readable GLM terms (IRR per unit shown).
_SCALE = {"diameter_mm": (100.0, "diameter (per 100 mm)"), "age_years": (10.0, "age (per 10 years)"),
          "depth_m": (1.0, "depth (per m)"), "grade": (1.0, "slope (per 1%)")}


def _clean_material(s: pd.Series) -> pd.Series:
    # Groups with no blockages (Other, Unknown) can't be estimated on their own; pool them.
    return s.where(~s.isin(["Other", "Unknown"]), "Other/unknown")


def baseline_rates(df: pd.DataFrame, by: str = "material") -> pd.DataFrame:
    g = df.groupby(by).agg(blockages=("blockages", "sum"), km=("length_m", lambda s: s.sum() / 1000)).reset_index()
    lo = np.nan_to_num(chi2.ppf(0.025, 2 * g.blockages) / 2)
    hi = chi2.ppf(0.975, 2 * (g.blockages + 1)) / 2
    g["per_km"] = g.blockages / g.km
    g["ci_low"], g["ci_high"] = lo / g.km, hi / g.km
    return g


@dataclass
class GlmResult:
    table: pd.DataFrame  # term, irr, ci_low, ci_high, p
    alpha: float
    aic: float
    model: object
    dropped: list[str]  # what was left out of the fit, and why


def _glm_frame(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["material"] = _clean_material(d["material"])
    for col, (unit, _) in _SCALE.items():
        d[col] = d[col] / unit
    for c in ["age_missing", "depth_missing", "grade_missing", "relined"]:
        d[c] = d[c].astype(int)
    d["log_len"] = np.log(d["length_m"])
    return d


def _estimable(d: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Drop what a count model can't estimate: groups or flags with no recorded blockages (infinite CIs)."""
    dropped = []
    events = d.groupby("material")["blockages"].sum()
    empty = sorted(events[events == 0].index)
    if empty:
        n = int(d["material"].isin(empty).sum())
        dropped.append(f"material {', '.join(empty)} ({n} pipes, no recorded blockages) not modelled")
        d = d[~d["material"].isin(empty)]
    terms = []
    for f in FEATURES_GLM:
        if f == "material":
            continue
        if d[f].nunique() < 2:
            dropped.append(f"{f}: no variation")
        elif f.endswith("_missing") or f == "relined":
            if d.loc[d[f] == 1, "blockages"].sum() == 0:
                dropped.append(f"{f}: those {int((d[f] == 1).sum())} pipes have no recorded blockages")
            else:
                terms.append(f)
        else:
            terms.append(f)
    return d, terms, dropped


def _formula(d: pd.DataFrame, terms: list[str]) -> str:
    ref = MATERIAL_REF if MATERIAL_REF in set(d["material"]) else d["material"].mode()[0]
    return "blockages ~ " + " + ".join([f"C(material, Treatment('{ref}'))", *terms])


def fit_glm(df: pd.DataFrame) -> GlmResult:
    d, terms, dropped = _estimable(_glm_frame(df))
    formula = _formula(d, terms)
    # α by maximum likelihood (NB2), then a GLM with that α for clean IRRs and CIs.
    nb = smf.negativebinomial(formula, d, offset=d["log_len"]).fit(disp=0, maxiter=200)
    alpha = float(nb.params["alpha"])
    glm = smf.glm(formula, d, offset=d["log_len"], family=sm.families.NegativeBinomial(alpha=alpha)).fit()
    ci = glm.conf_int()
    rows = []
    for term in glm.params.index:
        if term == "Intercept":
            continue
        name = term
        if term.startswith("C(material"):
            name = "material: " + term.split("[T.")[1].rstrip("]")
        elif term in _SCALE:
            name = _SCALE[term][1]
        rows.append({"term": name, "irr": float(np.exp(glm.params[term])), "ci_low": float(np.exp(ci.loc[term, 0])),
                     "ci_high": float(np.exp(ci.loc[term, 1])), "p": float(glm.pvalues[term])})
    return GlmResult(pd.DataFrame(rows), alpha, float(glm.aic), glm, dropped)


def _effect_sentence(irr: float, lo: float, hi: float, what: str) -> str:
    controls = "after allowing for pipe material, age, size, depth and relining"
    if lo < 1 < hi:
        return (f"There is no clear evidence that {what} changes recorded blockages ({irr - 1:+.0%} per tree, "
                f"95% CI {lo - 1:+.0%} to {hi - 1:+.0%}), {controls}.")
    direction = "more" if irr > 1 else "fewer"
    return (f"Each extra {what.replace('a tree', 'tree')} is associated with {abs(irr - 1):.0%} {direction} recorded "
            f"blockages (95% CI {abs(lo - 1):.0%}–{abs(hi - 1):.0%}), {controls}.")


def tree_effect(glm: GlmResult) -> dict:
    t = glm.table.set_index("term")
    a, b = t.loc["trees_5m"], t.loc["aggressive_trees_10m"]
    return {
        "irr_per_tree_5m": a.irr, "ci": [a.ci_low, a.ci_high], "p": a.p,
        "irr_aggressive_10m": b.irr, "ci_aggr": [b.ci_low, b.ci_high], "p_aggr": b.p,
        "sentence": _effect_sentence(a.irr, a.ci_low, a.ci_high, "a tree within 5 m of a pipe"),
    }


def _gbm_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES_GBM].copy()
    X["material"] = pd.Categorical(_clean_material(X["material"]))
    for c in ["age_missing", "depth_missing", "grade_missing"]:
        X[c] = X[c].astype(int)
    return X


def _top_decile_capture(rate: np.ndarray, blockages: np.ndarray, length: np.ndarray, share: float = 0.10) -> float:
    order = np.argsort(-rate, kind="stable")
    cum_len = np.cumsum(length[order])
    k = int(np.searchsorted(cum_len, share * cum_len[-1])) + 1
    return float(blockages[order][:k].sum() / max(1, blockages.sum()))


def _offset(df: pd.DataFrame, rate_per_m: float) -> np.ndarray:
    """log(expected blockages at the overall rate). Starting the boosting there (not at log(length)) keeps
    LightGBM's capped Poisson steps from having to travel ~7 log units, which left predictions ~1000x too high."""
    return np.log(df["length_m"].to_numpy() * rate_per_m)


def cv_gbm(df: pd.DataFrame, groups: pd.Series, seed: int = 7, n_splits: int = 5) -> dict:
    y = df["blockages"].to_numpy()
    length = df["length_m"].to_numpy()
    X = _gbm_X(df)
    oof = {"gbm": np.zeros(len(df)), "glm": np.zeros(len(df)), "baseline": np.zeros(len(df))}
    for train, test in GroupKFold(n_splits=n_splits).split(X, y, groups):
        rate = y[train].sum() / length[train].sum()
        m = lgb.LGBMRegressor(**GBM_PARAMS, random_state=seed)
        m.fit(X.iloc[train], y[train], init_score=_offset(df.iloc[train], rate))
        oof["gbm"][test] = np.exp(m.predict(X.iloc[test], raw_score=True) + _offset(df.iloc[test], rate))
        fitted = fit_glm(df.iloc[train])
        d_test = _glm_frame(df.iloc[test])
        known = d_test["material"].isin(set(fitted.model.model.data.frame["material"]))
        glm_pred = np.zeros(len(test))  # groups the GLM couldn't model had no blockages in training
        if known.any():
            glm_pred[known.to_numpy()] = fitted.model.predict(d_test[known], offset=d_test.loc[known, "log_len"])
        oof["glm"][test] = glm_pred
        rates = baseline_rates(df.iloc[train]).set_index("material")["per_km"]
        overall = y[train].sum() / (length[train].sum() / 1000)
        oof["baseline"][test] = df["material"].iloc[test].map(rates).fillna(overall).to_numpy() * length[test] / 1000
    rate = {k: v / length for k, v in oof.items()}
    return {
        "oof_pred": oof["gbm"],
        "top_decile_capture": _top_decile_capture(rate["gbm"], y, length),
        "glm_top_decile_capture": _top_decile_capture(rate["glm"], y, length),
        "baseline_top_decile_capture": _top_decile_capture(rate["baseline"], y, length),
        "poisson_deviance": {k: float(mean_poisson_deviance(y, np.clip(v, 1e-9, None))) for k, v in oof.items()},
        "auc_any_blockage": float(roc_auc_score(y > 0, rate["gbm"])),
    }


def fit_gbm_and_explain(df: pd.DataFrame, seed: int = 7):
    import shap

    X = _gbm_X(df)
    offset = _offset(df, df["blockages"].sum() / df["length_m"].sum())
    model = lgb.LGBMRegressor(**GBM_PARAMS, random_state=seed)
    model.fit(X, df["blockages"].to_numpy(), init_score=offset)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X)
    pred = np.exp(model.predict(X, raw_score=True) + offset)
    return model, values, explainer.expected_value, X, pred


FEATURE_PHRASES = {
    "material": lambda v: f"{v} pipe",
    "age_years": lambda v: f"{v:.0f} years old",
    "age_missing": lambda v: "install date unknown",
    "diameter_mm": lambda v: f"{v:.0f} mm diameter",
    "diameter_missing": lambda v: "diameter unknown",
    "depth_m": lambda v: f"{v:.1f} m deep",
    "depth_missing": lambda v: "depth unknown",
    "grade": lambda v: f"{v:.1f}% slope",
    "grade_missing": lambda v: "slope unknown",
    "trees_5m": lambda v: f"{int(v)} tree{'s' if int(v) != 1 else ''} within 5 m",
    "trees_10m": lambda v: f"{int(v)} trees within 10 m",
    "aggressive_trees_10m": lambda v: f"{int(v)} root-aggressive tree{'s' if int(v) != 1 else ''} within 10 m",
    "crown_sum_10m": lambda v: f"{v:.0f} m of tree canopy within 10 m",
    "trees_per_100m_10m": lambda v: f"{v:.1f} trees per 100 m of pipe",
}


def reasons(shap_row: dict, feature_values: dict, top: int = 2) -> str:
    positive = {k: v for k, v in shap_row.items() if v > 0}
    if not positive:
        return "No single factor stands out"
    total = sum(positive.values())
    parts = []
    for k, v in sorted(positive.items(), key=lambda kv: -kv[1])[:top]:
        phrase = FEATURE_PHRASES.get(k, lambda x: f"{k} = {x}")(feature_values[k])
        parts.append(f"{phrase} ({round(100 * v / total)}%)")
    return ", ".join(parts)


def risk_band(pct: float) -> str:
    if pct >= 95:
        return "Very high"
    if pct >= 80:
        return "High"
    if pct >= 50:
        return "Medium"
    return "Low"

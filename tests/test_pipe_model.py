import numpy as np
import pandas as pd
import pytest

from projects.pipe_blockages.model import (FEATURES_GBM, FEATURES_GLM, RISK_BANDS, baseline_rates, cv_gbm, fit_glm,
                                           reasons, risk_band, tree_effect)


def simulate(n=20_000, seed=1, irr_tree=1.15, irr_ew=2.0, alpha=0.5):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "id": np.arange(n),
        "material": rng.choice(["Plastic", "Earthenware", "Concrete"], n, p=[0.5, 0.2, 0.3]),
        "diameter_mm": rng.choice([150.0, 225.0, 300.0], n),
        "age_years": rng.uniform(5, 90, n),
        "depth_m": rng.uniform(0.8, 4.0, n),
        "grade": rng.uniform(0.002, 0.05, n),
        "relined": rng.random(n) < 0.08,
        "trees_5m": rng.poisson(1.0, n),
        "length_m": rng.uniform(20, 150, n),
        "cell": rng.integers(0, 60, n).astype(str),
    })
    for c in ["age_missing", "depth_missing", "grade_missing", "diameter_missing"]:
        df[c] = False
    df["trees_10m"] = df.trees_5m + rng.poisson(1.0, n)
    df["aggressive_trees_10m"] = rng.binomial(df.trees_10m, 0.3)
    df["crown_sum_10m"] = df.trees_10m * rng.uniform(2, 8, n)
    df["trees_per_100m_10m"] = 100 * df.trees_10m / df.length_m
    mu = (df.length_m / 1000) * 3.0 * np.where(df.material == "Earthenware", irr_ew, 1.0) \
        * np.where(df.material == "Concrete", 1.4, 1.0) * irr_tree ** df.trees_5m
    df["blockages"] = rng.negative_binomial(1 / alpha, 1 / (1 + alpha * mu))
    return df


SIM = simulate()


def test_glm_recovers_planted_tree_effect():
    glm = fit_glm(SIM)
    t = glm.table.set_index("term")
    assert t.loc["trees_5m", "ci_low"] < 1.15 < t.loc["trees_5m", "ci_high"]
    assert t.loc["material: Earthenware", "ci_low"] < 2.0 < t.loc["material: Earthenware", "ci_high"]
    eff = tree_effect(glm)
    assert eff["ci"][0] < eff["irr_per_tree_5m"] < eff["ci"][1]
    assert "more recorded blockages" in eff["sentence"]


def test_tree_effect_sentence_when_no_evidence():
    glm = fit_glm(simulate(seed=3, irr_tree=1.0))
    eff = tree_effect(glm)
    if eff["ci"][0] < 1 < eff["ci"][1]:
        assert "no clear evidence" in eff["sentence"]


def test_baseline_rates_per_km_with_ci():
    df = pd.DataFrame({"material": ["A", "A", "B"], "blockages": [2, 2, 1], "length_m": [1000.0, 1000.0, 1000.0]})
    r = baseline_rates(df).set_index("material")
    assert r.loc["A", "per_km"] == pytest.approx(2.0) and r.loc["B", "per_km"] == pytest.approx(1.0)
    assert r.loc["A", "ci_low"] < 2.0 < r.loc["A", "ci_high"]


def test_cv_gbm_beats_baseline_on_signal():
    cv = cv_gbm(SIM, SIM["cell"], seed=7)
    assert cv["top_decile_capture"] > cv["baseline_top_decile_capture"]
    assert cv["top_decile_capture"] > 0.10
    assert set(cv["poisson_deviance"]) == {"gbm", "glm", "baseline"}
    assert len(cv["oof_pred"]) == len(SIM)


def test_reasons_names_top_drivers():
    values = {"material": "Earthenware", "trees_10m": 6, "age_years": 70.0, "depth_m": 1.2}
    shap_row = {"material": 0.9, "trees_10m": 0.6, "age_years": 0.3, "depth_m": -0.4}
    text = reasons(shap_row, values, top=2)
    assert text.startswith("Earthenware pipe (50%)") and "6 trees within 10 m (33%)" in text


def test_reasons_when_nothing_raises_risk():
    assert reasons({"material": -0.2}, {"material": "Plastic"}) == "No single factor stands out"


def test_risk_band_never_says_safe():
    bands = {risk_band(p) for p in np.linspace(0, 100, 101)}
    assert bands <= set(RISK_BANDS) and "safe" not in " ".join(bands).lower()
    assert risk_band(99) == "Very high" and risk_band(85) == "High" and risk_band(60) == "Medium" and risk_band(10) == "Low"


def test_gbm_features_exclude_relined():
    assert "relined" in FEATURES_GLM and "relined" not in FEATURES_GBM


def test_cv_gbm_is_calibrated_at_real_world_rates():
    # ~1 blockage per km (the real rate) — predictions must add up to roughly the observed total
    sim = simulate(seed=5)
    sim["blockages"] = np.random.default_rng(5).poisson(sim.length_m / 1000 * 1.0 * 1.15 ** sim.trees_5m)
    cv = cv_gbm(sim, sim["cell"])
    ratio = cv["oof_pred"].sum() / sim.blockages.sum()
    assert 0.8 < ratio < 1.25, ratio
    assert cv["poisson_deviance"]["gbm"] < 2 * cv["poisson_deviance"]["baseline"]


def test_glm_handles_groups_with_no_events():
    sim = simulate(seed=6, n=8000)
    extra = sim.head(60).copy()
    extra["material"], extra["blockages"], extra["age_missing"] = "Other", 0, True
    glm = fit_glm(pd.concat([sim, extra], ignore_index=True))
    t = glm.table
    assert np.isfinite(t[["irr", "ci_low", "ci_high"]].to_numpy()).all()
    assert "age_missing" not in set(t.term) and not any(t.term.str.contains("Other"))
    assert glm.dropped  # says what was left out and why

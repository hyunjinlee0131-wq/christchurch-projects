"""Wastewater pipe blockages and tree roots: results first, then search, then the why."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))  # so `lib` imports when this page is run directly

import pandas as pd
import pydeck as pdk
import streamlit as st

from lib.data import load_metrics, load_pipes, search_street
from lib.feedback import feedback_enabled, send_feedback
from lib.text import pct, plural

st.set_page_config(page_title="Sewer pipe blockages · Christchurch Projects", page_icon="🚰", layout="wide")

MAX_ROWS = 500
DRIVER_LABELS = {"diameter (per 100 mm)": "Each extra 100 mm wide", "age (per 10 years)": "Each extra 10 years old",
                 "slope (per 1%)": "Each extra 1% of slope", "depth (per m)": "Each extra metre deep",
                 "trees_5m": "Each tree within 5 m", "aggressive_trees_10m": "Each root-aggressive tree within 10 m"}
BAND_COLOURS = {"Very high": [179, 38, 30], "High": [230, 126, 34], "Medium": [241, 196, 15], "Low": [160, 170, 166]}
COLUMNS = {"street": "Street", "material": "Material", "age_years": "Age (yrs)", "diameter_mm": "Diameter (mm)",
           "blockages": "Recorded blockages", "risk_band": "Risk", "reason": "Main reasons"}

st.title("Which sewer pipes block, and do trees cause it?")
pipes, m = load_pipes(), load_metrics("pipe_blockages")
if pipes is None or m is None:
    st.info("The pipe results are not available right now. Please try again later.")
    st.stop()

# ---- Results first (no input needed) ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Sewer pipes analysed", f"{m['n_pipes']:,}", help=f"{m['km']:,.0f} km of in-service council gravity pipes")
c2.metric("Recorded blockages", f"{m['total_blockages']:,}", help="All time, undated, on " + plural(m["n_blocked"], "pipe"))
eff = m["tree_effect"]
c3.metric("Effect of a tree within 5 m", eff["metric"],
          help=f"95% CI {eff['ci'][0] - 1:+.0%} to {eff['ci'][1] - 1:+.0%}" + ("" if eff["clear"] else ": no clear evidence"))
c4.metric("Blockages in riskiest 10% of pipe length", pct(m["cv"]["top_decile_capture"]),
          help=f"Measured on areas the model never saw; vs {pct(m['cv']['baseline_top_decile_capture'])} ranking by material alone")

st.markdown(f"**Short answer:** {m['headline']} {m.get('answer', '')}")

if feedback_enabled():
    f1, f2, f3 = st.columns([1, 1, 6])
    if f1.button("👍 Useful", key="fb_up"):
        f3.write("Thanks!" if send_feedback("pipe_blockages", "answer", 1) else "Couldn't send. Please try again later.")
    if f2.button("👎 Not useful", key="fb_down"):
        f3.write("Thanks!" if send_feedback("pipe_blockages", "answer", -1) else "Couldn't send. Please try again later.")

# ---- Map ----
st.subheader("Where the risk is")
show_all = st.toggle("Show all pipes (slower)", value=False)
view = pipes if show_all else pipes[pipes["risk_band"].isin(["Very high", "High"])]
layer_df = pd.DataFrame({
    "path": view["path"].map(lambda p: [list(xy) for xy in p]),
    "colour": view["risk_band"].map(BAND_COLOURS),
    "street": view["street"].replace("", "(unnamed)"), "material": view["material"],
    "age": view["age_years"].map(lambda a: "unknown" if pd.isna(a) else f"{a:.0f} years"),
    "blockages": view["blockages"], "band": view["risk_band"], "reason": view["reason"],
})
st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer("PathLayer", layer_df, get_path="path", get_color="colour", width_min_pixels=2,
                      get_width=4, pickable=True)],
    initial_view_state=pdk.ViewState(latitude=-43.53, longitude=172.63, zoom=10.5),
    map_style="light",
    tooltip={"html": "<b>{street}</b><br/>{material}, {age}<br/>Recorded blockages: {blockages}<br/>"
                     "Risk: <b>{band}</b><br/>{reason}"},
), height=480)
st.caption("Red = Very high (top 5%), orange = High (top 20%). Risk is a priority for inspection, not a forecast. "
           "No pipe is guaranteed blockage-free.")

# ---- Search ----
st.subheader("Search your street")
q = st.text_input("Street name", key="street", placeholder="e.g. Main Road")
if q.strip():
    hits = search_street(pipes, q)
    if hits.empty:
        st.info(f"No pipes found on a street matching “{q.strip()}”. About 9% of pipes have no street within 40 m "
                "and can't be found by name; use the map.")
    else:
        shown = hits.sort_values("risk_pct", ascending=False).head(MAX_ROWS)
        more = f" (showing the riskiest {MAX_ROWS}; type more of the name to narrow it)" if len(hits) > MAX_ROWS else ""
        st.write(f"{plural(len(hits), 'pipe')} on streets matching “{q.strip()}”, riskiest first{more}:")
        st.dataframe(shown[list(COLUMNS)].rename(columns=COLUMNS),
                     hide_index=True, use_container_width=True)

# ---- What to inspect first ----
st.subheader("Top 20 pipes to inspect first")
st.caption("Highest-risk pipes with no recorded blockage yet: the best candidates for proactive CCTV inspection.")
first = pipes[pipes["blockages"] == 0].sort_values("risk_pct", ascending=False).head(20)
st.dataframe(first[list(COLUMNS)].rename(columns=COLUMNS), hide_index=True, use_container_width=True)

# ---- Why ----
st.subheader("Why")
left, right = st.columns(2)
rates = pd.DataFrame(m["rates_by_material"]).set_index("material")["per_km"].sort_values()
left.markdown("**Recorded blockages per km, by material**")
left.bar_chart(rates, horizontal=True, color="#1f6f5c")
left.caption("Before allowing for age and size. Old, small asbestos-cement, concrete and earthenware pipes are the "
             "ones to look at first.")
drivers = pd.DataFrame(m["drivers"])
drivers = drivers[~drivers["term"].str.endswith("_missing") & (drivers["term"] != "relined")]
drivers["term"] = drivers["term"].map(lambda t: DRIVER_LABELS.get(t, t.replace("material: ", "") + " (vs plastic)"))
drivers["effect"] = drivers["irr"] - 1
right.markdown("**Effect of each factor, all else equal** (change in recorded blockages)")
right.bar_chart(drivers.set_index("term")["effect"].sort_values(), horizontal=True, color="#1f6f5c")
right.caption("Bars right of zero go with more blockages, left with fewer. "
              + ("Trees within 5 m: no clear effect." if not eff["clear"] else f"Trees within 5 m: {eff['short']}."))

with st.expander("How this was worked out"):
    st.markdown(f"""
- **Data:** Christchurch City Council open data (CC BY 4.0), pulled {m['data_pulled_at'][:10]}: wastewater pipes,
  recorded blockage counts, street and park trees, street names.
- **Pipes:** {m['n_pipes']:,} in-service, council-owned gravity sewer pipes. Pressure and vacuum pipes fail differently and are left out.
- **Blockages** are all-time, undated counts, so there are no trends. Results are associations, not proof of cause.
- **Models:** a negative-binomial model (for the effect sizes and the tree question) and a gradient-boosted model
  (for each pipe's risk and its reasons, via SHAP). The headline accuracy figures are measured on areas the models
  never saw (1 km grid cells held out). The risk shown for each pipe on this page comes from a model fitted to all
  pipes, so treat it as a priority list, not a forecast. Out of sample, the "Very high" 5% of pipes held
  {pct(m['very_high_out_of_sample']['share'])} of recorded blockages.
- **Age:** blockage counts are all-time, so older pipes have also simply had longer to block.
- **Trees:** only trees the council records individually. Private garden trees, often blamed for roots in older
  sewers, are not in the data.
- **Relining** is done *because* pipes block, so it's never used to rank risk.
- Full write-up: `projects/pipe_blockages/SUMMARY.md` on [GitHub](https://github.com/hyunjinlee0131-wq/christchurch-projects).
""")
st.caption("Christchurch Projects: an independent project, not affiliated with Christchurch City Council.")

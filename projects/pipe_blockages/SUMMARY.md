# Executive summary: wastewater pipe blockages and tree roots

*Data: Christchurch City Council open data, pulled 2026-11-02. 32,438 in-service council gravity sewer pipes (1,646 km);
1,860 recorded blockages on 1,320 pipes. Counts are all-time and undated. Findings are associations, not proof of cause.*

## Situation
The council keeps a count of recorded blockages for every sewer pipe, plus detailed asset records: material, size,
age, depth and slope. It also maps about 183,000 street and park trees. Blockages cause overflows and call-outs, and
roots are widely blamed.

## Complication
Blockages are rare (about 1.1 per km of pipe, all time) and spread thinly across 1,646 km of pipe, so inspecting
everything isn't practical. The obvious suspect, street trees, can't be checked by eye because tree-lined streets also
differ in pipe age, material and size.

## Question
1. Which pipes should be inspected first?
2. Do nearby trees make pipes block more (project 21)?

## Answer

**1. Pipe age and size matter most, then material.** After allowing for everything else:

| Driver | Effect on recorded blockages | 95% CI |
|---|---|---|
| Diameter | **−65% per extra 100 mm** (bigger pipes rarely block) | −70% to −59% |
| Age | **+15% per extra 10 years** | +11% to +20% |
| Asbestos cement vs plastic | ×1.68 | 1.30–2.16 |
| Concrete vs plastic | ×1.50 | 1.19–1.88 |
| Earthenware vs plastic | ×1.22 (raw rate 2.8× plastic, mostly explained by its age and small size) | 0.89–1.68 |

**A risk ranking helps.** Ranked by the model, the riskiest 10% of pipe length (165 km) holds **31%** of recorded
blockages. Ranking by material alone captures 17%, so the model nearly doubles the "hit rate" of an inspection
programme. This was validated on areas held out by 1 km grid cell, so it isn't flattered by neighbouring pipes.
It falls short of the 40% target set at the start; see Limitations.

**2. There is no clear evidence that council-recorded trees cause blockages.**
- **Per tree within 5 m:** −2% per tree (95% CI −6% to +2%), after allowing for material, age, size, depth and relining.
- **Root-aggressive genera** (willow, poplar, gum, oak, ash, maple, elm, plane, birch, liquidambar) within 10 m are
  associated with **4% fewer** recorded blockages per tree (CI 1–6% fewer).

That doesn't mean roots don't block sewers. It means the council's *street and park* trees don't explain where
blockages happen. The likely culprits are **private garden trees over older laterals**, which aren't in open data, and
**where street trees are planted** (newer, wider streets with newer pipes).

## Recommended actions
1. **Inspect the "Very high" band first:** 1,638 pipes, 50 km, holding 33% of recorded blockages. That includes
   **1,311 Very high pipes with no recorded blockage yet**, the best candidates for proactive CCTV.
2. **Prioritise small (100–150 mm), old (60+ years) asbestos-cement, concrete and earthenware pipes.** These are
   the pipes the model consistently flags.
3. **Don't target root cutting by council street-tree proximity alone;** the data doesn't support it. If roots are the
   concern, the evidence needed is **private-property tree and lateral data** or CCTV defect codes.
4. **Fix data gaps that distort the picture:**
   - pipes with an unknown slope show 3× the blockages, so the gap is linked to problem pipes;
   - renewed "plastic" pipes keep their original install date (80+ year-old "plastic" blocks at 9.5 per km);
   - grades recorded as "1 in 1" or similar.

## Business value
For a fixed inspection budget covering 10% of the network, targeting by this model finds roughly **1.8× as many
blockage-prone pipes** as targeting by material, and avoids spending on root cutting where the data shows no link.

## Limitations
- **Undated, cumulative counts:** there are no trends, and blockages before a pipe was relined are mixed with later ones.
- **Observational data:** relining is done *because* pipes block, so it's used only as a control and never in the risk
  score.
- **Tree coverage:** only trees the council records individually; private trees are invisible here.
- **The root-aggressive genus list** is a common rule-of-thumb list from arborist and water-utility guidance, not
  checked against a specific study.
- **Heavy over-dispersion** (negative-binomial α ≈ 10): a few pipes block repeatedly, so per-pipe predictions are
  uncertain. Treat risk bands as priorities, not forecasts.
- **Model ranking** (AUC 0.71) is useful but far from perfect; it misses the 40% target.

## Next steps
- Add CCTV defect codes, lateral records and blockage dates if the council can share them. Dates alone would allow
  "blockages after relining" analysis.
- Re-test the tree question with private-tree canopy from LiDAR or aerial imagery.
- Review the Very high list with asset planners and record which pipes were inspected and what was found.

## Readiness
**MVP ready** as a prioritisation aid and an evidence check on the tree question. It's not ready to drive automated
maintenance decisions without the data improvements above.

## How this was produced (baseline A1–A9)
`README.md` (problem), `data_dictionary.md`, `reports/profile_summary.md` (pre/post profiling, GO decision),
`eda.ipynb`, `model.py` (negative-binomial GLM with length offset, LightGBM Poisson with SHAP, 5-fold spatial CV),
`outputs/` (pipes with risk and reasons, metrics, model tables). Feedback is collected in the app; visitor analytics
use Streamlit Cloud's built-in viewer stats, because GA4 isn't practical inside Streamlit.

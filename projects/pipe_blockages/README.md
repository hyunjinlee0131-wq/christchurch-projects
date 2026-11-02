# Wastewater pipe blockages and tree roots (projects 20 + 21)

## Project context (baseline)

- **Project name:** Wastewater pipe blockages and tree roots
- **Target user / persona:** Christchurch City Council three-waters asset planners (primary); residents curious about their street (secondary).
- **One-line value proposition:** "Asset planners enter nothing and get a ranked, explained list of gravity sewer pipes most likely to block, plus the measured effect of nearby trees."
- **Decision this improves:** where to target proactive CCTV inspection, root cutting and relining, instead of waiting for blockages and overflows.
- **Success metrics / KPIs:**
  - **Top-decile capture:** the share of recorded blockages that sit in the 10% of pipe length the model ranks riskiest. Target ≥ 40%, and better than ranking by material alone.
  - **Tree effect:** the incidence-rate ratio per tree within 5 m, with a 95% CI and a plain-language sentence.
  - **Usefulness:** the app's 👍 share.
- **Constraints and assumptions:**
  - Blockage counts are cumulative and undated, so there's no trend analysis.
  - The data is observational: findings are associations, not causes.
  - Relining is often done *because* a pipe blocked, so it's confounded.
  - Tree data covers only trees the council records individually; private garden trees are missing.
- **Data sources:** CCC open data: `WasteWater/WwPipe`, `WasteWater/WwPipeBlockageCount`, `Tree/Tree`, `Road/StreetCentreLine` (CC BY 4.0).

## Problem statement

**Not** "build a blockage model" **but** "find the sewer pipes most likely to block next, and decide whether trees near them should change how we inspect and maintain them."

- **Cost of inaction:** blockages cause wastewater overflows into homes, streets and waterways, emergency call-outs and public-health risk. Reactive clearing costs more than planned root cutting or relining.
- **Population:** in-service, council-owned gravity pipes: 33,116 pipes (2026-11-02), before dropping pipes under 1 m. Pressure, vacuum, vent and overflow pipes fail in different ways and are excluded.
- **Target:** recorded blockages per pipe (all time, undated); pipes not in the blockage layer count as 0.
- **Exposure:** pipe length (a longer pipe has more chances to block).

Files: `data_dictionary.md` · `reports/profile_summary.md` · `eda.ipynb` · `SUMMARY.md` · `outputs/`.

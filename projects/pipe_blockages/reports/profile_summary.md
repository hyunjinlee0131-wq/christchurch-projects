# Data quality summary

Rows before cleaning: **71854** · after: **32438**

| column | missing % (pre) | unique (pre) | missing % (post) | unique (post) |
|---|---|---|---|---|
| WwPipeID | 0.0 | 71854 | — | — |
| Type | 0.0 | 12 | — | — |
| ServiceStatus | 0.0 | 5 | — | — |
| Ownership | 0.0 | 3 | — | — |
| Construction | 2.6 | 33 | — | — |
| NominalDiameter | 0.8 | 69 | — | — |
| CommissionDate | 3.6 | 1945 | — | — |
| Depth | 18.1 | 327 | — | — |
| Grade | 32.5 | 3460 | — | — |
| Treatment | 96.3 | 5 | — | — |
| TreatmentDate | 96.2 | 238 | — | — |
| drvLength | 0.0 | 2231 | — | — |
| id | — | — | 0.0 | 32438 |
| material | — | — | 0.0 | 7 |
| diameter_mm | — | — | 0.0 | 53 |
| age_years | — | — | 0.0 | 1081 |
| depth_m | — | — | 0.0 | 200 |
| grade | — | — | 0.0 | 1796 |
| relined | — | — | 0.0 | 2 |
| length_m | — | — | 0.0 | 1405 |
| trees_5m | — | — | 0.0 | 29 |
| trees_10m | — | — | 0.0 | 48 |
| aggressive_trees_10m | — | — | 0.0 | 32 |
| crown_sum_10m | — | — | 0.0 | 1187 |
| trees_per_100m_10m | — | — | 0.0 | 11752 |
| street | — | — | 0.0 | 3668 |
| cell | — | — | 0.0 | 302 |
| blockages | — | — | 0.0 | 9 |
| diameter_missing | — | — | 0.0 | 2 |
| age_missing | — | — | 0.0 | 2 |
| depth_missing | — | — | 0.0 | 2 |
| grade_missing | — | — | 0.0 | 2 |

## Notes and hypotheses

- Modelled pipes: 32,438; with ≥1 recorded blockage: 1,320; recorded blockages: 1,860.
- Blocked pipe ids outside the population: 137 of 1,457 (9%).
- Missing values are imputed (median; age by material first) with *_missing flags kept as features.
- Transform: keep gravity pipes (71,854 → 46,609)
- Transform: keep in-service pipes (46,609 → 37,035)
- Transform: keep council-owned pipes (37,035 → 33,116)
- Transform: drop pipes under 1 m (33,116 → 32,438)
- Transform: blockage ids unmatched to population (dropped) (1,457 → 1,320)
- H1: earthenware (EW) and concrete pipes have higher blockage rates per km than plastic.
- H2: more trees within 5 m of a pipe raise its blockage rate after allowing for material and age.
- H3: root-aggressive genera (willow, poplar, gum, elm, plane, ash, oak, maple, birch, liquidambar) matter more than tree count alone.
- H4: older and shallower pipes block more.
- H5: relined pipes show lower rates, but relining is often done because a pipe blocked (confounded).

## Decision: **GO** for modelling

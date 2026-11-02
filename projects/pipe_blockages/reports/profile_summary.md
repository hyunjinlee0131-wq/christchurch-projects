# Data quality summary

Rows before cleaning: **71854**

| column | missing % (pre) | unique (pre) |
|---|---|---|
| WwPipeID | 0.0 | 71854 |
| Type | 0.0 | 12 |
| ServiceStatus | 0.0 | 5 |
| Ownership | 0.0 | 3 |
| Construction | 2.6 | 33 |
| NominalDiameter | 0.8 | 69 |
| CommissionDate | 3.6 | 1945 |
| Depth | 18.1 | 327 |
| Grade | 32.5 | 3460 |
| Treatment | 96.3 | 5 |
| TreatmentDate | 96.2 | 238 |
| drvLength | 0.0 | 2231 |

## Notes and hypotheses

- ww_pipe: 71,854 rows
- blockage: 1,457 rows
- tree: 183,158 rows
- street: 12,440 rows
- H1: earthenware (EW) and concrete pipes have higher blockage rates per km than plastic.
- H2: more trees within 5 m of a pipe raise its blockage rate after allowing for material and age.
- H3: root-aggressive genera (willow, poplar, gum, elm, plane, ash, oak, maple, birch, liquidambar) matter more than tree count alone.
- H4: older and shallower pipes block more.
- H5: relined pipes show lower rates, but relining is often done because a pipe blocked (confounded).

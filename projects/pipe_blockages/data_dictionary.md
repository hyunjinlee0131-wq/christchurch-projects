# Data dictionary: pipe blockages

Source: Christchurch City Council open data (CC BY 4.0), fetched with `ccc_data` (only the columns below; `layers.toml`).
"Missing %" is over all 71,854 pipes before filtering (`reports/profile_summary.md`).

## WasteWater / WwPipe (71,854 rows, polyline, EPSG:2193)

| Field | Type | Meaning | Missing % | Used as |
|---|---|---|---|---|
| WwPipeID | int (object id) | Pipe identifier | 0 | key |
| Type | text (12 values) | Gravity, Pressure, Vacuum, … | 0 | filter: Gravity, Gravity Collector |
| ServiceStatus | text (5) | In Service, Abandoned, Removed, … | 0 | filter: In Service |
| Ownership | text (3) | CCC, Private, Selwyn DC | 0 | filter: CCC |
| Construction | text (33 codes) | Pipe material | 2.6 | feature `material` (grouped, below) |
| NominalDiameter | int, mm | Nominal internal diameter | 0.8 | feature `diameter_mm` (+ missing flag) |
| CommissionDate | date (epoch ms) | When the pipe went into service | 3.6 | feature `age_years` (+ missing flag) |
| Depth | float, m | Depth to pipe | 18.1 | feature `depth_m` (+ missing flag) |
| Grade | float | Pipe slope | 32.5 | feature `grade` (+ missing flag) |
| Treatment | text (5) | Relining method (CIPP, wound plastic, sleeve, …) | 96.3 | `relined` flag (GLM control only; confounded) |
| TreatmentDate | date | When relined | 96.2 | not used (too sparse, and post-hoc) |
| drvLength | float, m | Pipe length | 0 | exposure `length_m`; drop < 1 m |

### Material groups (`features.MATERIAL_GROUPS`)

| Group | Codes |
|---|---|
| Earthenware | EW, VC |
| Concrete | RCRR, CONC |
| Asbestos cement | AC |
| Plastic | UPVC, PVC, MPVC, OPVC, PVCLRC, PE, PE100, HDPE, LDPE, MDPE80, MDPE100, PELRC, CORRPE, NovaFlow, ABS, GRP |
| Metal | CI, DI, CLDI, CLS, STEEL, WI, AL |
| Other | BB, BLBRUTE |
| Unknown | missing |

## WasteWater / WwPipeBlockageCount (1,457 rows)

| Field | Type | Meaning | Used as |
|---|---|---|---|
| WwPipeID | int | Pipe identifier | join key |
| NumberOfBlockages | int (1–24) | Recorded blockages on this pipe, all time, undated | **target** (absent → 0) |

## Tree / Tree (183,158 rows, point)

| Field | Type | Meaning | Missing % | Used as |
|---|---|---|---|---|
| Genus | text | Tree genus | low | `aggressive_trees_10m` (root-aggressive genera list) |
| CrownSpread | float, m | Canopy width | 0.2 | `crown_sum_10m` |
| DiameterAtBreastHeight | float | Trunk size | — | profiled only |
| Height | float, m | Tree height | — | profiled only |

## Road / StreetCentreLine (12,440 rows, polyline)

| Field | Type | Meaning | Used as |
|---|---|---|---|
| FullRoadName | text | Street name | `street` (nearest within 40 m), for search in the app |

## Derived features (`features.py`)

`material`, `diameter_mm`, `diameter_missing`, `age_years`, `age_missing`, `depth_m`, `depth_missing`, `grade`,
`grade_missing`, `relined`, `length_m`, `trees_5m`, `trees_10m`, `aggressive_trees_10m`, `crown_sum_10m`,
`trees_per_100m_10m`, `street`, `cell` (1 km grid, cross-validation group), `blockages` (target).

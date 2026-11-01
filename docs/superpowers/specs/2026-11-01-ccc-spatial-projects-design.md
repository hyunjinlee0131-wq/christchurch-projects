# CCC Spatial Projects — Design

Date: 2026-11-01 · Owner: hyunjinlee0131-wq · Status: draft for approval

Marking: **[user]** = decided by the user. **[Claude's call]** = chosen by Claude, open to override. Unmarked = context or fact.

## 1. Intent

Mass-produce small projects built on Christchurch City Council (CCC) open spatial data and gather them on one website **[user]**. Projects are fun, solve a real local problem, or are statistical **[user]**. Every project must be a polished, fully usable product, not a demo **[user]**.

Why: show what CCC's open data can do for real people in Christchurch, and build a portfolio that keeps growing cheaply. Every new project should cost one analysis plus one page, not a new stack.

## 2. Goals, non-goals, anti-goals

**Goals**
- Ship the first 10 projects (section 7) on one site **[user]**.
- Serious projects follow the user's Data Science Baseline in full (section 5). Fun projects (1, 4, 6) relax the rigour and focus on attracting users **[user]**.
- A Christchurch resident with no data background can open any project on a phone and get a useful answer within 10 seconds, without signing up **[Claude's call, from baseline B1]**.
- Shared plumbing, so project #11 is cheap.

**Non-goals**
- No user accounts or logins.
- No data sources beyond CCC open data unless a project explicitly calls for one (project 31 does: OSM street lamps).
- No original data collection. The only user-generated data is park votes and feedback.

**Anti-goals** (failure even if it technically works) **[Claude's call]**
- Results that claim more than the data supports, e.g. calling cumulative blockage counts a trend, or calling property risk "safe".
- Pages that need explaining before they're useful.
- A site that silently goes stale. Every page shows its data date.
- Anything that exposes individuals. Property data is valuation data only; no owner names.

## 3. Constraints

- **Data source:** CCC ArcGIS server `https://gis.ccc.govt.nz/server/rest/services/OpenData/<Service>/FeatureServer/<layer>`, discovered through the Hub catalog at `https://opendata-christchurchcity.hub.arcgis.com` (483 datasets; full list in `datasets.md`).
- **Server quirk 1:** the server fails Python 3.13's strict X.509 check ("Basic Constraints of CA cert not marked critical"). The fix is to clear only `ssl.VERIFY_X509_STRICT`; normal verification stays on.
- **Server quirk 2:** Hub catalog URLs can be stale. "Walking Track" no longer exists, and "River Urban Impact" moved to `WaterCharacteristic/FeatureServer/22`. The downloader resolves layers by **service + layer name** from the live service listing, never from catalog URLs.
- **Large layers:** Tree (183k records), Building (237k), Rating Unit / Unit Value (188k each), Coastal Inundation (105k polygons). Downloads must paginate (server max record count) and be cached once for all projects.
- **Free hosting only:** GitHub Pages and Streamlit Community Cloud (repo must be public), plus a Supabase free tier for votes **[Claude's call]**.
- **Accounts:** GitHub `hyunjinlee0131-wq` (gh CLI logged in). The user still needs to create: a Supabase project, a GA4 property, a Google Form for feedback, and a Streamlit Cloud login linked to GitHub. The builder leaves clearly named placeholders and a `SETUP.md` checklist.
- **Machine:** Windows 10; Python 3.13 runs through the `py` launcher (bare `python` is the Store stub); Node is installed.
- **Licence:** CCC data is CC BY 4.0 (to be confirmed in the dataset metadata). Every page carries attribution.

## 4. Architecture (hybrid — **[user]** chose hybrid; specifics **[Claude's call]**)

```
repo (public, GitHub: hyunjinlee0131-wq/christchurch-projects)
├── ccc_data/            shared Python package: fetch, cache, log, helpers
├── projects/<slug>/     one folder per project (notebooks, pipeline, outputs, summary)
├── app/                 Streamlit multipage app — one page per serious project
├── site/                Astro static site — home, fun projects, cards linking to app
├── .github/workflows/   scheduled data refresh + site deploy
├── datasets.md, intent.md, SETUP.md
```

- **Static site (Astro + MapLibre GL, GitHub Pages):** the home page is a gallery of project cards with live headline numbers (e.g. "#1 park: X"). It hosts fun projects 1, 4 and 6 fully, with data baked in at build time as GeoJSON/PMTiles. Each serious project gets a landing card that links to its Streamlit page. Shareable URLs per item (e.g. `/parks/<park-slug>`) with Open Graph preview images.
- **Streamlit app (Community Cloud):** one multipage app for projects 17, 20, 31, 32, 34, 39 and 42. Results show on the first screen, with a "Run with sample data / example address" default. Maps use pydeck or folium (builder's choice). The app reads **precomputed** small outputs (parquet/GeoJSON) committed to the repo and never downloads raw layers at runtime.
- **Pipeline:** each project has `projects/<slug>/pipeline.py`, which runs raw → clean → analysis → `outputs/`. Raw cache lives in `data/raw/` (gitignored); outputs are committed.
- **Refresh [Claude's call]:** a monthly GitHub Action reruns all pipelines, commits changed outputs and redeploys the site. Every output records `data_pulled_at`, which every page displays.
- **Shared look:** one colour/typography token set used by both Astro and the Streamlit theme (`.streamlit/config.toml`), so the two halves feel like one site.
- **Feedback on every result (baseline B5):** 👍/👎 buttons, plus a Google Form link (placeholder). 👍/👎 is stored in the same Supabase database (table `feedback`: project, item_id, value, created_at). GA4 runs on both halves, with events for key actions: search, vote, filter, share, feedback.
- **Address lookup (used by 17, 39 and optionally others):** geocode against CCC `Street Address` (local, offline) with fuzzy matching. No external geocoder.

## 5. How the baseline applies

**Serious projects (17, 20, 31, 32, 34, 39, 42): full Part A, steps 1–9.** Each delivers, in `projects/<slug>/`:
1. `README.md` with the filled PROJECT CONTEXT block (persona, value prop, decision, KPIs, constraints, sources) and the problem statement.
2. The environment comes from one shared, pinned `requirements.txt` at the repo root **[Claude's call: one env for all; per-project only if a project needs an extra library]**. Baseline stack plus geopandas, shapely, pyproj, pyogrio, shap.
3. `data_dictionary.md`, generated from layer field metadata plus notes, along with the ingestion step and fetch metadata (size, record count, pull date).
4. Pre-profiling: ydata-profiling HTML (not committed if large; a summary markdown is) plus a data quality summary and hypotheses.
5. Cleaning steps in `pipeline.py`, with a transformation log.
6. Post-profiling: a pre/post comparison and an explicit go/no-go note.
7. `eda.ipynb` with annotated visuals.
8. Modelling only where the project lists it; baseline model first; interpretable; SHAP for explanations.
9. `SUMMARY.md` in SCQA form, with recommended actions and readiness status. Its key finding is also shown in plain language on the project's page.

**Fun projects (1, 4, 6): light rigour.** A fetch-and-clean script, sanity checks and a short methodology note on the page. The effort goes into attraction instead: shareable results, a strong headline, mobile-first interaction, and OG images per item **[user: "may not follow" the baseline; focus on attraction]**.

**Product principles (Part B) apply to all 10:** results first, one persona, visual and explained output, a feedback loop. Each project also gets a distribution note in `projects/<slug>/LAUNCH.md` with a story-driven post draft and target communities (r/chch, local Facebook groups, LinkedIn, relevant volunteer networks). Posting is done by the user.

## 6. Quality bar ("high-level, fully usable") **[user intent; checklist is Claude's call]**

Every project, before it counts as done:
- Usable on a phone (360 px wide) and a desktop; no horizontal scroll.
- First meaningful result shown without input (a sensible default or sample).
- Loading, empty and error states handled; no raw tracebacks shown to users.
- Plain-language result first, a "How this was calculated" section second, and limitations stated.
- Data date and CCC attribution visible.
- Accessibility basics: keyboard reachable, alt text, colour-blind-safe palettes, contrast passes.
- Static pages load within about 3 s on 4G. The Streamlit cold start is accepted, and the static landing card hides it by showing the headline result before the user clicks through.
- One runnable check per pipeline: asserts on output shape, ranges and key invariants.

## 7. The projects

Record counts were checked live on 2026-11-01. "Track" replaces the removed "Walking Track" layer.

### 1. Best Park in Christchurch — fun · static site · **ranking site with user voting [user]**
- **Persona:** families and dog owners choosing a park for the weekend.
- **Value prop:** pick what you care about and get the best parks near you, ranked, plus what Christchurch actually loves.
- **Data:** Park (1,396 polygons), Playground (416), Play Equipment (8,933), Seat (4,273), Picnic Table (1,032), Sport Field (1,089), Drinking Fountain (272), Facility (128), Barbecue (40), Shower (35), Dog Exercise Area (9), Tree (183,106).
- **Data score:** count amenities inside each park polygon (plus a small buffer, builder sets it, around 20 m), and compute tree density per hectare. Normalise each factor (percentile), combine with default weights, and score 0–100. Exclude parks that are not really parks (road reserves, tiny verges, utility land) using size and type rules decided during cleaning; document the rule.
- **Personal ranking:** sliders/toggles reweight the factors live in the browser ("I have a dog", "toddlers", "BBQ"). Filter by distance from the user's location (browser geolocation, opt-in) or a chosen suburb.
- **Voting [user]:** visitors vote for parks they love. My call on the mechanics: one 👍 per park per browser (stored with a random browser ID in localStorage), unlimited parks, no downvotes. Votes go to Supabase table `park_votes` (park_id, voter_id, created_at; unique on park_id+voter_id). Row-level security allows insert only, with no update or delete. Counts are read through a view. A per-IP rate limit runs through a Supabase edge function or database policy (builder's choice). Accepted limit: this can't stop a determined cheater.
- **Ranking site [user: "make a ranking site at the end"]:** the site is the ranking. Its main view is the leaderboard (Data Score rank), with a People's Choice column/tab from votes. A "Data vs People" section highlights the biggest disagreements, e.g. "underrated gems". My call: data score and votes are shown side by side, not blended into one number.
- **Per-park page** (`/parks/<slug>`): score breakdown, amenity list, mini-map, vote button, share button with an OG image like "Hagley Park is #3 in Christchurch".

### 4. The Bench Map — fun · static site
- **Persona:** older walkers, people with limited mobility, and parents with young kids. Secondary: the parks team.
- **Value prop:** see how far you'd walk before the next seat.
- **Data:** Seat (4,273), Track (6,896), Walking & Mountain Bike Route (433).
- **Method:** snap seats within X m (builder sets, around 15 m) to track lines, then compute the gaps between consecutive seats along each track. Output gap segments with their lengths.
- **Experience:** a map colouring tracks by distance-to-next-seat. A "Longest walks without a seat" leaderboard as the fun hook. A slider "I need a rest every ___ m" highlights which tracks work for you.

### 6. Public Art Treasure Hunt — fun · static site
- **Persona:** tourists, families and locals looking for a free outing.
- **Value prop:** choose a start point and a time budget, and get a walking route through as many artworks as possible.
- **Data:** Public Place Art (337), Public Place Art Site (174), Street Centre Line (12,440).
- **Method:** a walking graph from street centre lines, plus prebuilt curated trails (e.g. Central City 1 h, Riverside). Custom routes use a fast heuristic solver for orienteering (max artworks within a distance). The builder decides whether it runs in the browser or as precomputed options; it must feel instant.
- **Experience:** art cards (photo, artist and title where attributes exist), a "collected" checklist saved in localStorage, and a share card "I found 14/337 artworks".

### 17. Sea Level Rise Exposure — serious · Streamlit
- **Persona:** homeowners and buyers in coastal suburbs; community board members.
- **Value prop:** enter an address and see whether and when coastal inundation reaches it under each sea-level scenario, plus how your suburb compares.
- **Decision:** buy/insure/adapt for individuals; prioritising adaptation planning for boards.
- **Data:** Coastal Inundation Hazard (105,134 polygons; fields include Scenario, Timeframe, ExceedenceProbability, Depth), Coastal Erosion Hazard (5,322), Coastal Hazard Modelled Extent (12), Building (237,094), Rating Unit (188,003), Street Centre Line (12,440), Street Address.
- **Analysis:** overlay buildings, rating units and road length with each scenario. Exposure curves (exposed count against sea-level rise), aggregated by suburb or ward.
- **KPIs:** time to answer an address query; share of lookups resulting in "learn more"/feedback.
- **Wording rule:** never say "safe"; say "not in modelled extent for this scenario", and link to CCC's official coastal hazards information.

### 20 + 21. Wastewater Pipe Blockages and Tree Roots — serious · Streamlit · modelling
- **Persona:** CCC three-waters asset planners and interested residents.
- **Value prop:** see which wastewater pipes block most, why, and which unblocked pipes look most at risk.
- **Decision:** where to target proactive pipe inspection, cleaning or relining.
- **Data:** Ww Pipe Blockage Count (1,457 pipes; fields WwPipeID, NumberOfBlockages), Ww Pipe (71,850), Ww Pipe Type (71,850), Tree (183,106).
- **Data limit [Claude's assumption; user did not object]:** blockages are cumulative counts per pipe with no dates, so there's no trend analysis; pipes missing from the count layer are treated as zero recorded blockages (to be validated during profiling).
- **Features:** pipe material, diameter, install year/age, length, depth/grade if present, and tree features: count and canopy proxy within buffers (e.g. 5 and 10 m), and species/genus where available.
- **Models:** baseline is blockages per metre by material. Main models are a Poisson / negative binomial GLM (statsmodels) with a length offset for interpretability, plus a gradient-boosted model with SHAP for "why". Sub-question 21 is answered explicitly: the tree effect, controlling for material and age, with effect size and confidence interval.
- **Output:** a map of blockage hotspots, a risk score for every pipe, and plain-language explanations ("high risk, mainly due to earthenware pipe (45%) and 6 trees within 5 m (30%)"). A street search.

### 31. Dark Spots on Walking and Cycling Routes — serious · Streamlit
- **Persona:** people who walk or cycle after dark; community safety groups.
- **Value prop:** see which stretches of cycleways and tracks have no lighting.
- **Data:** Light (4,632), Light Pole (1,935), Cycleway (4,926), Track (6,896), Street Centre Line.
- **Known gap:** the CCC Light layer appears to be park and furniture lighting (fields: Purpose, SiteName, Ownership), not the full street-light network. See open questions.
- **Method:** buffer each light by an effective radius (builder picks it with justification, around 25–30 m), then compute lit/unlit length per route segment. Rank the longest unlit stretches.

### 32. River Health Report Card — serious · Streamlit
- **Persona:** river care volunteer groups and residents near rivers.
- **Value prop:** pick a river and get an A–F report card with what's dragging it down and where.
- **Data:** CREAS Site (1,380), CREAS Point (554), River Urban Impact (2,770), Fish Obstruction (85), River Bank Observation (6,521), River Water Flow (6,632), Wc Water Course (9,550), and the impact layers in `WaterCharacteristic` (bank material, riparian vegetation, sediment depth, silt, substrate, velocity, width/depth diversity, channel meander), each about 86–324 records. CREAS 2005–2009 layers allow a then-vs-now comparison.
- **Method:** a per-site composite index from the impact scores (weights documented; sensitivity tested), aggregated per river and reach. Fish barrier priority list (barrier height × upstream habitat length).
- **Output:** a report card per river, a map of reaches by grade, top 3 issues per river in plain words.

### 34. Weed Invasion Map — serious · Streamlit
- **Persona:** volunteer weed-control groups and park rangers.
- **Value prop:** find the weed hotspots near you, which species they are, and where a working bee would have the most impact.
- **Data:** Notable Weed (2,159), CREAS Site Notable Weed (158), Park (1,396).
- **Method:** hotspot clustering (density or DBSCAN), species frequency, survey-date recency, and accessibility (distance to a park/public access point). A priority score for volunteer action.
- **Output:** a map filterable by species, a hotspot list, species ID cards. Survey date shown on each point, with a caveat about how old the data is.

### 39. Property Value Map — serious · Streamlit · modelling
- **Persona:** homeowners checking their latest valuation; prospective buyers.
- **Value prop:** enter an address and see its capital and land value and how it compares with the street, suburb and city change.
- **Data:** VDH Current Rating Unit Value (187,998), Rating Unit (188,003), Revaluation Valuation Roll (208 rolls; average change per roll), Ward (16), plus hazard and zoning layers as features.
- **Analysis:** a choropleth of value change by roll; outlier detection. Explanatory model: what location factors (hazards, zoning, distance to CBD/parks/coast) explain land value per m², using an interpretable model plus SHAP.
- **Privacy:** valuation data only; no owner fields are fetched or shown.

### 42. Central City Parking Finder — serious · Streamlit
- **Persona:** drivers heading into central Christchurch.
- **Value prop:** pick a destination and how long you're staying, and get the nearest parking that fits, with time limits and whether it's paid.
- **Data:** On-Street Parking Casual (1,939), Vehicle Class Restricted (537), Off-Street Parking (110), Car Park (858), PayMyPark Area (196), RAMM Parking Meter (224).
- **Data limit:** there's no occupancy or demand data. "Supply vs demand" from the original idea becomes **supply and access** analysis (supply by zone, paid vs free share, time-limit mix). Demand is not modelled **[Claude's call]**.
- **Output:** a destination search, ranked options by walking distance, and a supply summary for the central city.

## 8. Build order **[Claude's call]**

1. Repo setup (git init, public GitHub repo), `ccc_data` package (fetch/paginate/cache/log, SSL fix, resolve by name) with its self-check, shared theme, site skeleton, app skeleton, refresh workflow, `SETUP.md`.
2. Project 1 (Best Park, including voting) proves the static-site template.
3. Project 20+21 (Pipes) proves the serious/Streamlit template and the full baseline.
4. The remaining eight, reusing the two templates.
5. Home page polish, cross-links, launch notes.

## 9. Left to the builder

Library picks within the stated stack (map library in Streamlit, routing solver, clustering method), exact buffers and thresholds (with stated justification), scoring weights' starting values, folder internals, CI details, visual design within the shared tokens, and the exact park-exclusion rule.

## 10. Calls settled after the builder check **[Claude's call]**

- **Baseline document:** the full text is in `docs/baseline.md`. Section 5 refers to it.
- **Refresh vs findings:** the monthly Action re-downloads data and reruns pipelines, but **opens a pull request** instead of committing. Model metrics and headline numbers are diffed in the PR description, and a human merges. Findings never change unreviewed.
- **Launch cadence:** each project goes live as soon as it passes the section 6 quality bar. The home page lists only live projects. `LAUNCH.md` posts go out per project.
- **Project 39 privacy:** CCC already publishes per-property rating valuations publicly through its rates search, so showing the same values by address exposes nothing new. No owner fields are fetched. The page links to CCC's official rates lookup.

## 11. User answers (2026-11-01)

- **Project 31 [user]:** bring in non-CCC street-light data (an exception to the CCC-only non-goal). Confirmed: the CCC Light layer is park/sport/decorative lighting only (Purpose: Functional Non Sport 2,797, Decorative 583, Sport Field 693, Sport Area 545). Candidate source: OpenStreetMap `highway=street_lamp` (ODbL, attribution required). It's unverified because Overpass couldn't be reached from this machine (curl exit 35, an SSL connect error). The first build step for project 31 is to measure OSM street-lamp coverage, then combine it with the CCC park lights. If coverage is too patchy, the page must say where data is missing rather than show those stretches as "dark".
- **Site name [user]:** "Christchurch Projects". Address: `https://hyunjinlee0131-wq.github.io/christchurch-projects/` and repo `hyunjinlee0131-wq/christchurch-projects` **[Claude's call]**.

# Scripts

Utility scripts for building, validating, and enriching the camp/afterschool dataset that powers the static site. All scripts are run from the project root (e.g. `python scripts/<name>.py`).

## Build & serve

- **`build_data_js.py`** — Builds `data.js` (consumed by the frontend) by merging `data/organizations.csv` + `data/programs.csv`. Runs `validate_data.py` first and aborts on errors.
- **`validate_data.py`** — Validates the two CSVs for foreign-key integrity, required fields, and enum values. Acts as the gate before `build_data_js.py` writes output.
- **`dev_server.py`** — Local static dev server with lightweight live-reload, used while iterating on the site.

## Data enrichment (CSV-in-place)

These scripts read a CSV, fill in blanks, and write it back. They are idempotent and never overwrite existing values unless explicitly flagged.

- **`backfill_age_grade.py`** — Fills blank `grades_min`/`grades_max` from `age_min`/`age_max` (and vice versa) using `data/age_to_grade.csv`.
- **`enrich_locations.py`** — Geocodes/normalizes program addresses to populate location fields where they look like real street addresses.
- **`enrich_websites.py`** — Populates blank `website` cells in `organizations.csv` using `programs.csv` registration URLs and `potential_vt_organizations_full.csv` website URLs.
- **`fetch_descriptions.py`** — Fetches each program's `registration_url` and extracts a description into the blank `description` field.
- **`infer_activities.py`** — Infers activity tags for programs by keyword-matching the description and program name against the canonical tag list.
- **`infer_counties.py`** — Fills `site_county` for programs (and backfills org city/county) using the Vermont town→county GeoJSON.
- **`infer_org_types.py`** — Infers `org_type` (nonprofit / municipal / school / private / university / faith-based) from keywords in `org_name`.
- **`normalize_times.py`** — Canonicalizes program start/end times into a consistent 12-hour format.
- **`parse_costs.py`** — Parses freeform `cost_raw` strings (e.g. "$200/week", "free", "$50/day") into a numeric `cost_per_week`.

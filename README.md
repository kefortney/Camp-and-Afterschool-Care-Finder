# Camp & Afterschool Care Finder

An open-source tool helping Vermont families find summer camps and afterschool programs for K–12 students. Filter by grade, city, county, activity, cost, and schedule. Browse as a list, calendar, or interactive map.

**Live site:** [https://kefortney.github.io/Camp-and-Afterschool-Care-Finder/](https://kefortney.github.io/Camp-and-Afterschool-Care-Finder/)

## Run locally

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`. For live reload while editing:

```bash
python scripts/dev_server.py
```

## Data pipeline

All program and organization data lives in two CSV files:

| File | Contents |
| --- | --- |
| `data/programs.csv` | 401 programs — 391 summer camps, 10 afterschool |
| `data/organizations.csv` | 148 organizations |

After editing either CSV, rebuild `data.js`:

```bash
python scripts/validate_data.py   # check for errors first
python scripts/build_data_js.py   # generates data.js
```

The validation script exits 1 on errors (blocks the build). Warnings are printed but do not block.

## Utility scripts

| Script | What it does |
| --- | --- |
| `scripts/backfill_age_grade.py` | Fill `grades_min`/`grades_max` from age data (and vice versa) |
| `scripts/enrich_locations.py` | Geocode and standardize `site_address` via Nominatim |
| `scripts/fetch_descriptions.py` | Fetch missing `description` values from `registration_url` |
| `scripts/infer_activities.py` | Infer `activities` tags from `description` and `program_name` |
| `scripts/infer_counties.py` | Fill `site_county` using the GeoJSON town→county map |
| `scripts/infer_org_types.py` | Infer `org_type` from `org_name` keywords |
| `scripts/normalize_times.py` | Standardize `start_time`/`end_time` to 12-hour format |
| `scripts/parse_costs.py` | Parse `cost_raw` into a normalized `cost_per_week` value |
| `scripts/dev_server.py` | Local server with live reload and CSV save endpoint |

## Admin editor

Open `http://localhost:8000/admin.html` while running the dev server to edit programs and organizations through a UI.

**Save All** writes directly to `data/programs.csv` and `data/organizations.csv` on disk (requires `dev_server.py` — falls back to browser localStorage if not running). After saving, rebuild `data.js` to propagate changes:

```bash
python scripts/build_data_js.py
```

**Sharing edits with others:**

1. Run `python scripts/dev_server.py`
2. Edit in the admin → click **Save All** (button confirms "✓ Saved to CSV")
3. Run `python scripts/build_data_js.py`
4. Commit `data/programs.csv`, `data/organizations.csv`, and `data.js` — others pull and rebuild

> When Save All writes to CSV it clears localStorage, so the next page load always reflects the latest committed data rather than stale browser state.

## Data constraints

**`site_city` must match a town name in `data/Vermont_Town_GEOID_RPC_County.geojson`.**
The `infer_counties.py` script uses this file to fill `site_county` automatically. If a town name does not match, the county field will be left blank and the program will be excluded from county-based filters.

Use the `TOWNNAMEMC` property in the GeoJSON as the canonical spelling (e.g. `Burlington`, `South Burlington`, `Saint Albans City`). Common aliases like `St. Albans` are handled by the script, but new aliases must be added to `CITY_ALIASES` in `scripts/infer_counties.py`.

## Contributing

1. Fork the repo and clone it locally
2. Add or edit rows in `data/programs.csv` or `data/organizations.csv`
3. Run `python scripts/validate_data.py` — fix any ERRORs
4. Run `python scripts/build_data_js.py` — regenerates `data.js`
5. Test with `python -m http.server 8000`
6. Submit a pull request

See the [Data docs](https://kefortney.github.io/Camp-and-Afterschool-Care-Finder/data.html) for full field-by-field schema documentation.

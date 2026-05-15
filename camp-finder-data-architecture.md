# Camp Finder — Data Architecture Reference

*Last updated: 2026-05-12. Migration complete — all phases executed.*

---

## Current File Structure

```
data/
  programs.csv              # 401 programs — 391 camps, 10 afterschool
  organizations.csv         # 148 organizations
  age_to_grade.csv          # 13-row lookup table (unchanged)
  archive/
    summer_camp_2026.csv    # Archived — original camp CSV, do not delete
    21cclc_2025_2026.csv    # Archived — original afterschool CSV, do not delete

scripts/
  validate_data.py          # Foreign key + enum validation (exits 1 on errors)
  build_data_js.py          # Joins CSVs → data.js (runs validate first)
  backfill_age_grade.py     # Fill grades_min/max from age_min/max (and vice versa)
  enrich_locations.py       # Geocode site_address via Nominatim
  fetch_descriptions.py     # Pull description from registration_url
  normalize_times.py        # Standardize start_time/end_time to 12-hour format
  dev_server.py             # Local server with live reload + CSV save endpoint

data.js                     # Generated — do not edit directly
```

---

## Data Pipeline

```
Edit CSVs
    ↓
python scripts/validate_data.py      # exits 1 on any ERROR
    ↓
python scripts/build_data_js.py      # generates data.js
    ↓
Reload browser
```

`build_data_js.py` runs `validate_data.py` internally and aborts on errors. Running validate separately first gives clearer error output when iterating.

---

## programs.csv Schema

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `program_id` | string | YES | Kebab-case slug. Never reuse or rename. |
| `org_id` | string (FK) | YES | Must match an `org_id` in `organizations.csv` |
| `program_name` | string | YES | |
| `program_type` | enum | YES | `camp` or `afterschool` |
| `program_year` | integer | YES | e.g. `2026` |
| `description` | text | no | Auto-fetchable via `fetch_descriptions.py` |
| `session_type` | enum | YES | `day`, `residential`, `hybrid`, `drop-in` |
| `schedule_type` | enum | YES | `seasonal`, `weekly`, `daily`, `year-round` |
| `grades_min` | string | YES | `PK`, `K`, `1`–`12` |
| `grades_max` | string | YES | |
| `age_min` | integer | no | Backfilled by `backfill_age_grade.py` |
| `age_max` | integer | no | |
| `start_date` | date | no | `YYYY-MM-DD` |
| `end_date` | date | no | `YYYY-MM-DD` |
| `days_of_week` | string | no | e.g. `Mon–Fri` |
| `start_time` | string | no | `HH:MM AM` — normalized by `normalize_times.py` |
| `end_time` | string | no | `HH:MM PM` |
| `pre_after_care` | string | no | |
| `cost_raw` | string | no | As listed by the provider |
| `cost_per_week` | decimal | no | Normalized; `0` for free programs |
| `cost_notes` | text | no | |
| `meals_provided` | boolean | no | `TRUE` or `FALSE` |
| `transportation_provided` | boolean | no | |
| `transportation_notes` | text | no | |
| `activities` | string | no | Comma-separated canonical tags |
| `site_address` | string | no | Program site if different from org address |
| `site_city` | string | no | |
| `site_county` | enum | no | One of 14 Vermont counties |
| `registration_url` | URL | no | Direct registration link |
| `funding_source` | string | no | e.g. `21st Century Community Learning Centers` |
| `confidence` | enum | YES | `confirmed`, `likely`, `inactive` |
| `verified_date` | date | no | `YYYY-MM-DD` |
| `notes` | text | no | Internal only |

---

## organizations.csv Schema

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `org_id` | string (PK) | YES | Kebab-case slug. Never rename. |
| `org_name` | string | YES | Display name |
| `org_type` | enum | YES | `nonprofit`, `municipal`, `school`, `private`, `university`, `faith-based` |
| `website` | URL | no | |
| `phone` | string | no | `802-555-1234` |
| `email` | string | no | |
| `street_address` | string | no | |
| `city` | string | YES | |
| `county` | enum | YES | One of 14 Vermont counties |
| `state` | string | YES | `VT` |
| `zip` | string | no | |
| `financial_aid_available` | boolean | YES | `TRUE` or `FALSE` |
| `financial_aid_notes` | text | no | |
| `registration_policy` | string | no | |
| `registration_opens` | string | no | |
| `confidence` | enum | YES | `confirmed`, `likely`, `inactive` |
| `verified_date` | date | no | `YYYY-MM-DD` |
| `notes` | text | no | Internal only |

**County values:** `Addison`, `Bennington`, `Caledonia`, `Chittenden`, `Essex`, `Franklin`, `Grand Isle`, `Lamoille`, `Orange`, `Orleans`, `Rutland`, `Washington`, `Windham`, `Windsor`

---

## Canonical Activity Tags

Used in the `activities` column of `programs.csv`. Values outside this list produce a WARN from `validate_data.py`:

`STEM`, `Coding`, `Robotics`, `Science`, `Math`, `Arts`, `Music`, `Theater`, `Dance`, `Sports`, `Outdoor Education`, `Nature`, `Swimming`, `Hiking`, `Horseback Riding`, `Cooking`, `Language`, `Leadership`, `Community Service`, `Special Needs Support`, `Academic Enrichment`, `Maker`, `Film & Media`

---

## org_id Rules

- Kebab-case slug: lowercase, hyphens, no spaces or special characters
- Set once, never renamed — programs reference it as a foreign key
- Common patterns: `bgc-burlington`, `ymca-burlington`, `colchester-sd`
- For YMCA branches: `ymca-[city]`
- For school districts: `[town]-sd`
- On rebrand: update `org_name`, add a `notes` entry. Do NOT change `org_id`.

---

## data.js Structure

Generated by `build_data_js.py`. Exports two global constants:

```javascript
// Auto-generated — do not edit directly
const PROGRAMS = [ /* 401 objects */ ];
const ORGANIZATIONS = [ /* 148 objects */ ];
```

Each program object has org fields merged in (phone, email, website, address) with program-level `site_address`/`site_city`/`site_county` taking precedence over org-level fields.

`app.js` reads these synchronously at page load — no async CSV fetches.

---

## app.js Integration

```javascript
// Synchronous org lookup — no async needed
const orgMap = new Map(
  (typeof ORGANIZATIONS !== 'undefined' ? ORGANIZATIONS : []).map(o => [o.orgId, o])
);

// init() is synchronous — PROGRAMS is already loaded
function init() {
  allPrograms = typeof PROGRAMS !== 'undefined' ? PROGRAMS : [];
  // ...
}
```

`activeCategory` is read from `document.body.dataset.category`:

- `index.html` — `data-category="camp"`
- `afterschool.html` — `data-category="afterschool"`

---

## admin.html Integration

The admin page has two views — **Programs** and **Organizations** — toggled via a toolbar.

- Programs view: reads from `PROGRAMS` on load; edits are held in localStorage (`adminProgramData`)
- Organizations view: reads from `ORGANIZATIONS` on load; edits held in `adminOrgData`
- `org_id` field in the program edit modal is a `<select>` populated from `ORGANIZATIONS` — never a free-text input
- Delete guard: cannot delete an org if any program still references its `org_id`
- Save All: writes both CSVs via `POST /__save_csv` to `scripts/dev_server.py` (local only)

---

## Adding New Programs

1. Add the org to `organizations.csv` first (if not already there)
2. Add program rows to `programs.csv` referencing the org's `org_id`
3. Run `python scripts/validate_data.py` — fix any errors
4. Run `python scripts/build_data_js.py` — regenerates `data.js`
5. Test locally with `python -m http.server 8000`

**Do not add a program without a matching org row.** The validator will block the build.

---

## Archived Files

| File | Reason |
| --- | --- |
| `data/archive/summer_camp_2026.csv` | Original camp CSV — source of truth for migration questions |
| `data/archive/21cclc_2025_2026.csv` | Original afterschool CSV |

Do not delete these. They are the pre-migration record.

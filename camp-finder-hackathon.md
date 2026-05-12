# Camp & Afterschool Care Finder — Dad Guild Hackathon Planning Doc

**Event:** Dad Guild Hackathon — Friday, May 15, 2026, 5:30–11:00 PM  
**Location:** The Guild Hall @ Soda Plant, 266 Pine Street, Burlington, VT  
**Project:** [Camp & Afterschool Care Finder](https://kefortney.github.io/Camp-and-Afterschool-Care-Finder/)  
**Repo:** [github.com/kefortney/Camp-and-Afterschool-Care-Finder](https://github.com/kefortney/Camp-and-Afterschool-Care-Finder)

---

## What We Built and Why

Every spring, parents across Vermont spend hours hunting for summer camps that fit the right age range, the right weeks, and the right budget. That information is scattered across dozens of individual program websites with no central place to search, filter, or compare.

The Camp & Afterschool Care Finder is an open-source web app that solves this. It aggregates camp and afterschool care programs into a single searchable, filterable interface — letting families filter by grade, city, county, activity, schedule week, cost, financial aid availability, and STARS rating. It supports list, calendar, and map views. It is free, community-built, and publicly hosted.

This hackathon is about improving the tool before summer 2026 kicks off. Below are the specific work tracks participants can contribute to.

---

## Work Tracks

### Track 1 — Data Entry: Build Out the Camp List

**What:** The camp database is populated manually by researching individual programs and entering their details. This is intentional: automated scrapers produce dirty, unreliable data for something as variable as camp schedules and pricing. Human researchers get it right.

**Why this matters:** The tool is only as good as its data. An empty or sparse database makes the app useless. Getting more camps in — especially underrepresented ones (rural counties, lower-cost programs, specialty/STEM camps) — is the highest-impact contribution a non-technical participant can make tonight.

**How to contribute:**
- Pick a county or category of programs that isn't well covered yet
- Research camps via their websites, town recreation departments, and school district pages
- Enter new records using the admin interface (open `admin.html` in a local server session) or edit `data/programs.csv` directly
- Flag programs where data is incomplete so others can fill gaps

**Key fields to populate:** `program_name`, `org_id` (must match `organizations.csv`), `site_city`, `site_county`, `grades_min`/`grades_max`, `session_type` (day/residential/hybrid/drop-in), `start_date`/`end_date`, `start_time`/`end_time`, `cost_raw`, `cost_per_week`, `activities`, `registration_url`, and `confidence` (set to `confirmed` if details are verified for 2026, `likely` if carrying forward from prior year).

**No coding required for this track.**

---

### Track 2 — Data Verification: Confirm What We Have Is Accurate

**What:** We have records from prior research and from last year's data. Many of these programs will run again in 2026, but details change — costs go up, dates shift, registration links go stale, programs fold or pause.

**Why this matters:** Stale data erodes trust. A parent who calls a number that's been disconnected or clicks a dead registration link won't come back to the tool.

**How to contribute:**
- Take a batch of existing records and verify each one against the program's current website
- Check: Is the program still running? Are dates/weeks correct for 2026? Has the cost changed? Is the registration link live?
- Mark records as verified with a verification date, or flag them for correction/removal
- Note any programs that appear to have shut down permanently vs. temporarily

**No coding required for this track.**

---

### Track 3 — Data Quality: Confidence Field and Verification Workflow

**Current state:** The `confidence` field is fully implemented in the data model and admin UI. Every program and org row has a `confidence` value: `confirmed`, `likely`, or `inactive`. The app hides `inactive` programs by default.

**What this track is about tonight:**

1. **Backfill verification** — Many records still have `confidence = likely` because their 2026 details haven't been confirmed yet. Work through programs in the admin Organizations or Programs view, visit their websites, and flip `confidence` to `confirmed` once verified. Stamp `verified_date` with today's date.

2. **Badge UX** — Programs with `confidence = likely` are shown in results but have no visual indicator yet. A yellow badge ("2026 details not yet confirmed — check website") would help users understand the data quality. This is an open design+implementation task.

3. **Outreach tracking** — Should we add an `outreach_sent` date column to `organizations.csv` to track when we contacted a program to request 2026 details? Open question for the group.

**Contribution options:** Data verification (no code required), badge implementation in HTML/CSS/JS, outreach workflow design.

---

### Track 4 — Feature: Summer Camp Planner and CSV Export

**What:** Add functionality that lets a parent build a personal summer camp plan — selecting candidate programs, assigning them to weeks, adding notes, and exporting the plan as a CSV for follow-up.

**Why this matters:** Finding a camp is only step one. Parents need to coordinate multiple kids, multiple weeks, and multiple programs — often with gaps to fill and waitlists to manage. A planning layer turns the finder into a real decision-support tool.

**Proposed MVP feature set:**

- **Add to Plan button** on each program card/detail view
- **Plan sidebar or panel** showing selected programs with week assignments
- **Notes field** per selection (e.g., "need to confirm financial aid", "waitlist as of 5/1")
- **Week conflict detection** — flag if two selected programs overlap on the same week for the same child
- **CSV export** with columns: Program Name, Organization, Weeks, Cost, Phone, Email, Website, Notes, Status

**Out of scope for tonight (future):**
- Multi-child support
- Saving plans across sessions (requires backend)
- Sharing plans with a partner

**Contribution options:** JavaScript for the plan state management, HTML/CSS for the UI panel, CSV export logic (`data → Blob → download`), UX flow design.

---

### Track 5 — Backend Architecture: JSON File vs. Hosted Database

**The current setup:** Data lives in two CSV files (`data/programs.csv` and `data/organizations.csv`). A Python pipeline (`validate_data.py` → `build_data_js.py`) generates `data.js`, which exports `PROGRAMS` and `ORGANIZATIONS` as global constants. The app is fully static — no server, hosted on GitHub Pages. Simple, fast, zero cost.

**The question:** Should we migrate to a hosted structured database?

---

#### Staying with JSON/CSV (current approach)

**Pros:**
- Zero infrastructure cost and zero maintenance burden
- Works perfectly with GitHub Pages static hosting
- Version control on data — every change is a commit, fully auditable
- No authentication or API surface to secure
- Contributors can submit data changes via pull request
- Survives indefinitely without anyone paying a server bill

**Cons:**
- No concurrent editing — two people editing the CSV simultaneously will produce merge conflicts
- Admin experience is rough — editing raw CSV or JSON is error-prone
- No query capability — all filtering happens client-side in the browser, which scales poorly past ~2,000 records
- Adding relational structure (e.g., linking a program to multiple session records) is awkward in flat CSV
- No audit trail within the app — who changed what, when

**Best for:** Current scale (likely <500 records), volunteer-run project, no budget for infrastructure.

---

#### Migrating to a Hosted Database

**Options to consider:** Supabase (Postgres, free tier), Airtable (spreadsheet-like, great for non-technical admins), PocketBase (self-hosted, single binary).

**Pros:**
- Real concurrent editing with conflict resolution
- Admin UI becomes dramatically easier — form-based entry, validation, no raw file editing
- Enables relational modeling (program → sessions → weeks as separate tables)
- API-driven — frontend fetches live data, no redeploy needed to publish new records
- Query-side filtering reduces client-side JavaScript complexity
- User roles — different permissions for viewers vs. editors vs. admins
- Audit logs built in

**Cons:**
- Introduces operational dependency — if the database goes down, the app breaks
- Free tiers have limits; eventual cost if the project scales
- Requires someone to own the infrastructure (account, credentials, backups)
- GitHub Pages no longer sufficient for any write operations — need a separate API layer or use Supabase's client SDK directly from the browser
- Data is no longer in version control by default (must set up export/backup discipline)
- Meaningfully higher complexity for contributors to set up locally

**Recommendation for tonight:** Don't migrate the backend at the hackathon — the risk of introducing breaking changes mid-event is too high. Instead, treat this as a design session: agree on the target schema if you were to migrate, document the decision, and leave the actual migration as a post-hackathon milestone. Airtable is worth a serious look as a middle path — it gives non-technical admins a spreadsheet interface while exposing an API the frontend can query.

---

### Track 6 — Admin Page: Use It and Improve It

**Current state:** `admin.html` is a fully functional data management tool. It has two views — **Programs** and **Organizations** — toggled in the toolbar. Program edits use modal forms with dropdowns for `org_id`, `program_type`, `session_type`, `schedule_type`, and `confidence` (no free-text for controlled fields). Organization edits have their own modal. A "Save All" button writes changes back to the CSVs via the local dev server.

**To use the admin page:**

1. Run `python scripts/dev_server.py` (not just `http.server` — you need the save endpoint)
2. Open `http://127.0.0.1:8000/admin.html`
3. Edit programs or orgs, then click "Save All" to write to the CSVs
4. Run `python scripts/build_data_js.py` to regenerate `data.js`

**Known gaps / open improvement tasks:**

- No search or filter in the Programs table — hard to find specific records in 401 rows
- No bulk verification workflow — "Mark all selected as verified" would help during data passes
- No visual indicator for stale records (verified_date blank or > 90 days old)
- The Organizations view shows all 148 orgs but no filter by confidence
- Import from CSV is not yet implemented — adding many programs still requires direct CSV editing

**Contribution options tonight:** Implement table search/filter, add verified_date staleness indicators, implement bulk confidence update, improve mobile layout of the edit modals.

---

## How to Contribute Tonight

| Track | Technical skill needed | Good for |
|---|---|---|
| 1 — Data Entry | None | Everyone |
| 2 — Data Verification | None | Everyone |
| 3 — Recurring Programs Design | Low–Medium | Designers, PMs, JS devs |
| 4 — Planner / CSV Export | Medium | JS developers |
| 5 — Backend Architecture | Medium–High | Architects, devs (design session) |
| 6 — Admin Page | Medium | JS/HTML/CSS developers |

**To get started:** Clone or fork [github.com/kefortney/Camp-and-Afterschool-Care-Finder](https://github.com/kefortney/Camp-and-Afterschool-Care-Finder), run `python3 -m http.server 8000`, and open `http://localhost:8000`.

---

## What Success Looks Like Tonight

By the end of the evening, we want to leave with:

- Meaningfully more camp records in the database — verified, complete, and ready to publish
- A clear decision and design spec for how to handle recurring/unconfirmed programs
- A working prototype or clear spec for the planner/export feature
- A documented decision on the backend architecture path forward
- An improved or fully specced admin page

The tool is already useful. Tonight is about making it genuinely great before summer starts.

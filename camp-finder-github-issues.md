# Camp Finder — GitHub Issues for Hackathon

Each section below is one issue. Copy the title and body separately into GitHub's "New Issue" form.

---

## Issue 1

**Title:** `[Data] Audit and verify all existing 2026 camp records`

**Body:**
Many records in `data/programs.csv` were entered based on prior-year data or early research. Before the tool goes wide, every record needs a human verification pass against the program's current website. The `confidence` and `verified_date` fields are already in the schema — this issue is about doing the verification work.

**Tasks:**
- [ ] Confirm the program is still operating in 2026
- [ ] Verify schedule weeks are correct for this year
- [ ] Confirm cost information is current
- [ ] Check that the registration link is live and correct
- [ ] Set `confidence = confirmed` (or `inactive` if the program is gone)
- [ ] Set `verified_date` to today's date
- [ ] For orgs: verify phone, email, and website are current in `data/organizations.csv`

**Labels:** `data`, `good first issue`, `help wanted`

---

## Issue 2

**Title:** `[Data] Research and add camps for underrepresented counties`

**Body:**
The current dataset skews toward Chittenden County programs. We need broader coverage across Vermont, particularly for rural counties where families have fewer options and the tool adds the most value.

**Tasks:**
- [ ] Identify which counties have fewer than 5 records
- [ ] Research camps and afterschool programs in those counties via town recreation departments, school district pages, and regional nonprofits
- [ ] Enter new records following the existing field schema
- [ ] Prioritize lower-cost and financial-aid-eligible programs, which are often underrepresented

**Labels:** `data`, `help wanted`

---

## Issue 3

**Title:** `[Data] Research and add STEM, arts, and specialty camp categories`

**Body:**
Activity/subject coverage in the dataset is uneven. We need more programs tagged with specific activity categories so filters are useful.

**Tasks:**
- [ ] Identify gaps in the `subject / activity` filter values
- [ ] Research programs in underrepresented categories (STEM, coding, arts, music, theater, sports-specific, nature/outdoor ed)
- [ ] Enter new records with correct activity tags
- [ ] Review existing records to ensure activity tags are accurate and consistent

**Labels:** `data`, `help wanted`

---

## Issue 4

**Title:** `[Feature] Add UI badge for "likely" programs with unconfirmed 2026 details`

**Body:**
The `confidence` field is already implemented in the data model (`confirmed`, `likely`, `inactive`). `inactive` programs are hidden. But `likely` programs currently show in results with no visual distinction from `confirmed` programs — users have no way to know the details may be from a prior year.

**Tasks:**

- [ ] Design a badge/indicator for `likely` programs (yellow warning, tooltip, or muted card style)
- [ ] Implement badge on the program card in list view
- [ ] Implement indicator in the program detail modal
- [ ] Decide: should `likely` programs show by default or require a filter opt-in?
- [ ] Write badge copy (e.g., "2026 details not yet confirmed — check website")
- [ ] Confirm mobile rendering works at 375px width

**Labels:** `feature`, `design`, `data`

---

## Issue 5

**Title:** `[Feature] Summer camp planner with CSV export`

**Body:**
Parents don't just need to find camps — they need to plan a full summer across multiple weeks, potentially for multiple kids. Add a lightweight planning layer that lets users select programs, assign weeks, add notes, and export their plan.

**MVP scope:**
- "Add to Plan" button on each program card and detail view
- Plan panel/sidebar listing selected programs
- Week assignment per selection
- Notes field per selection (e.g., "on waitlist", "need to confirm financial aid")
- Basic conflict detection: flag if two selected programs overlap on the same week
- Export plan as CSV with columns: Program Name, Organization, Weeks, Cost, Phone, Email, Website, Notes, Status

**Out of scope for MVP:**
- Multi-child support
- Persisting plan across browser sessions
- Sharing plan with another user

**Tasks:**
- [ ] Design plan panel UI (sidebar, drawer, or dedicated tab)
- [ ] Implement plan state management in JS
- [ ] Add "Add to Plan" / "Remove from Plan" toggle to program cards
- [ ] Implement week conflict detection logic
- [ ] Implement CSV export (`data → Blob → anchor download`)
- [ ] Confirm which fields to include in the export

**Labels:** `feature`, `enhancement`

---

## Issue 6

**Title:** `[Design] Decide on UX for "likely" program badges`

**Body:**
Tracking issue for the design decision on how to visually communicate that a program's 2026 details are not yet confirmed (see issue #4).

**Options to evaluate:**
1. Inline yellow badge on the program card: "Details unconfirmed"
2. Tooltip on hover explaining the confidence status
3. Modal/alert when user clicks into the detail view
4. Muted/greyed card styling with a note at the top of the detail view

**Considerations:**
- Should not be so alarming that users skip the program entirely
- Should be clear enough that users don't act on stale data without checking
- Should work on mobile

**Tasks:**
- [ ] Sketch or mockup at least two options
- [ ] Get feedback from at least one non-technical user
- [ ] Implement chosen approach

**Labels:** `design`, `ux`

---

## Issue 7

**Title:** `[Admin] Add search, filter, and bulk update to admin page`

**Body:**
The admin page now has full CRUD for both Programs and Organizations, with dropdown-enforced controlled fields (`org_id`, `program_type`, `session_type`, `schedule_type`, `confidence`). The remaining gaps are discovery and bulk workflow features.

**Required functionality:**

- [ ] Table search — text input that filters the Programs or Organizations table by name/org
- [ ] Filter by `confidence` in both Programs and Organizations views (surface `likely` records needing verification)
- [ ] Bulk confidence update — select multiple rows, set all to `confirmed` / `likely` / `inactive`
- [ ] Visual staleness indicator — highlight records with `verified_date` blank or older than 90 days

**Nice to have:**

- [ ] Import — paste or upload a CSV row, parse into the form for review before saving
- [ ] Column sort in the Programs table (by city, date, confidence)

**Labels:** `admin`, `enhancement`, `feature`

---

## Issue 8

**Title:** `[Admin] Expose "Mark as Verified" and staleness surfacing in admin`

**Body:**
The `verified_date` field exists in both `programs.csv` and `organizations.csv`. The admin edit modals expose it as a text input. What's missing is workflow support — a one-click verify button and a way to surface stale records without manually scanning the table.

**Tasks:**

- [ ] Add a "Mark as Verified" button to the program and org edit modals — stamps today's date into `verified_date` without requiring the user to open the date field
- [ ] Highlight rows in the admin table where `verified_date` is blank or older than 90 days
- [ ] Add a "Show unverified only" toggle to the Programs and Organizations views
- [ ] Consider adding a `verified_date` column to the Programs table view (currently hidden)

**Labels:** `admin`, `data`, `enhancement`

---

## Issue 9

**Title:** `[Tech] Evaluate migration from CSV/JSON to hosted database`

**Body:**
The current data backend is a flat CSV loaded via `data.js`. This works well at current scale but has limitations for concurrent editing, relational data modeling, and admin UX.

**This issue is a design/decision spike, not an implementation task.** Do not merge any backend migration without a documented decision here.

**Options to evaluate:**

| Option | Notes |
|---|---|
| Stay with CSV/JSON | Zero cost, git-versioned, simple — but editing workflow is rough and doesn't scale past ~2k records |
| Airtable | Non-technical admin UX, API-accessible, free tier — but data leaves git and depends on Airtable's terms |
| Supabase (Postgres) | Full relational DB, free tier, direct browser SDK — more power but more operational complexity |
| PocketBase | Self-hosted, single binary, includes admin UI — requires someone to own a server |

**Tasks:**
- [ ] Document current pain points that a database would solve
- [ ] Define the record volume and contributor scale we're planning for
- [ ] Evaluate Airtable as a middle path
- [ ] Make a go/no-go decision and document it in this issue
- [ ] If migrating: define target schema before touching any code

**Labels:** `tech`, `architecture`, `discussion`

---

## Issue 10

**Title:** `[Bug] npm ci fails in CI without a lockfile`

**Body:**
If a `package-lock.json` or `yarn.lock` is not committed to the repo, `npm ci` will fail in any CI/CD pipeline. `npm install` should be used as a fallback, or a lockfile should be committed.

**Tasks:**
- [ ] Check whether a lockfile exists in the repo
- [ ] If not: run `npm install` locally and commit the generated `package-lock.json`
- [ ] Update any CI workflow files to use `npm ci` once a lockfile is present

**Labels:** `bug`, `ci`

---

## Issue 11

**Title:** `[Enhancement] Add mobile-responsive improvements to filter panel`

**Body:**
The filter panel has a large number of dropdowns (program model, grade, city, subject, week, county, STARS rating, status, cost, financial aid). On mobile this is likely to be cramped or overflow.

**Tasks:**
- [ ] Test filter panel on a 375px wide viewport (iPhone SE baseline)
- [ ] Identify any overflow, truncation, or tap-target issues
- [ ] Implement collapsible filter panel for mobile (collapsed by default, expand on tap)
- [ ] Ensure all dropdowns have adequate tap target size (minimum 44x44px)
- [ ] Test on iOS Safari and Android Chrome

**Labels:** `enhancement`, `mobile`, `ux`

---

## Issue 12

**Title:** `[Enhancement] Improve empty state when no programs match filters`

**Body:**
Currently when no programs match the active filters, the app shows "No programs found — try adjusting your search or filters." This is a dead end for users who don't know which filter is too restrictive.

**Tasks:**
- [ ] Show which filters are currently active when the empty state appears
- [ ] Add a "Clear all filters" button directly in the empty state (not just at the top of the panel)
- [ ] Consider showing the count of results as filters are applied so users can see when they're about to hit zero

**Labels:** `enhancement`, `ux`

---

## Issue 13

**Title:** `[Data] Establish and document controlled vocabulary for activity/subject tags`

**Body:**
The `subject / activity` field is free-text right now, which means inconsistent tagging (e.g., "STEM", "Science", "Science & Tech" all appearing as separate filter values). We need a canonical tag list.

**Tasks:**
- [ ] Audit all existing activity tags in the dataset
- [ ] Propose a canonical tag list (aim for ~15–25 meaningful categories)
- [ ] Document the tag list in the repo (e.g., `data/README.md` or a `tags.json` reference file)
- [ ] Normalize existing records to use canonical tags
- [ ] Update the admin form to use a dropdown or multi-select for activity tags (no free text)

**Labels:** `data`, `admin`, `enhancement`

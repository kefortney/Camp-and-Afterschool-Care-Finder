# Data Quality Assessment & Improvement Plan
*Audited: 2026-05-12*

---

## Summary: Where We Stand

| Dataset | Rows | Critical issues | High-priority gaps | Automated fixes applied |
| --- | --- | --- | --- | --- |
| `programs.csv` | 401 | 5 types fixed | 8 fields sparse | ✅ 107 rows touched |
| `organizations.csv` | 148 | 2 rows fixed | 6 fields 100% blank | ✅ 2 rows fixed |

---

## Automated Fixes Applied (2026-05-12)

These were fixed by script — no manual review needed:

| Fix | Rows affected |
| --- | --- |
| `ace-colchester` org: city/state/zip columns were shifted right by one | 1 org |
| `south-burlington-sd` org: street_address/city/state/zip columns were shifted right by one | 1 org |
| Vermont Audubon programs with `program_name = '?'` → "Vermont Audubon Summer Day Camp" | 8 programs |
| Corrupted `registration_url` (two URLs concatenated) → trimmed to first URL | 1 program |
| `grades_min = 'k'` → 'K' (lowercase) | 1 program |
| `start_time` values of 12:00 AM / 12:30 AM / 1:00 AM / 2:00 AM / 3:00 AM → PM equivalent | 26 programs |
| Burlington Parks Rec + South Burlington Rec programs with 2025 dates: `confidence = confirmed` → `likely` | ~100 programs |
| Fixed `normalize_times.py` bug that forced all start times to AM regardless of input | script fix |

---

## Remaining Issues by Priority

---

### 🔴 Critical — Fix Before Hackathon

#### 1. Burlington Parks Rec and South Burlington Rec: 2025 dates

**~100 programs** from Burlington Parks & Recreation and South Burlington Recreation have `start_date` and `end_date` in 2025 but `program_year = 2026`. These were migrated from last year's data and never updated. They have been downgraded to `confidence = likely` automatically.

**Action:** Go to [summerbtvparks.com](https://summerbtvparks.com/) and the [South Burlington Rec registration site](https://secure.rec1.com/VT/south-burlington-vt-rec) and pull the 2026 schedule. Update dates, confirm times, and flip confidence to `confirmed`.

**Program names also need updating:** "Hat Trick Hockey 2025", "Cool Camp 2025", "Rise & Shine 2025" etc. should be "... 2026" or whatever name the program uses this year.

---

#### 2. Vermont Audubon: 8 programs still missing grades and cost

All 8 Vermont Audubon weekly programs have placeholder names (now fixed to "Vermont Audubon Summer Day Camp") but still have no `grades_min`, `grades_max`, `cost_raw`, or `cost_per_week`. They also have a 9th row (`vermont-audubon-vermont-audubon-summer-program-2026`) that is a duplicate placeholder with no dates — this should be deleted.

**Action:** Visit [vt.audubon.org/programs/summer-day-camps](https://vt.audubon.org/programs/summer-day-camps). Fill in grades and cost for all 8 weekly sessions. Confirm the individual camp names (they likely have themed names). Delete the 9th duplicate row. Also consider whether each week has a different theme name that should be used instead of the generic placeholder.

---

#### 3. Two programs have end_date before start_date

```
vermont-audubon--2026-8:  start 2026-08-17, end 2026-08-12  ← flipped
bread-butter-farm-knoll-adventures-2026:  start 2026-08-17, end 2026-08-12  ← same
```

**Action:** Verify correct dates from each program's website and fix.

---

### 🟡 High Priority — Major Coverage Gaps

#### 4. `activities` tags: 98% blank for camp programs

Only the 10 afterschool programs have activity tags. The `activities` field drives the subject/activity filter in the app — without it, that filter is useless for camps.

**Missing count:** 391/401 programs (97.5%)

**Canonical tag list** (use exactly these values, comma-separated):
`STEM`, `Coding`, `Robotics`, `Science`, `Math`, `Arts`, `Music`, `Theater`, `Dance`, `Sports`, `Outdoor Education`, `Nature`, `Swimming`, `Hiking`, `Horseback Riding`, `Cooking`, `Language`, `Leadership`, `Community Service`, `Special Needs Support`, `Academic Enrichment`, `Maker`, `Film & Media`

**Action options:**
- A. Manual tagging via admin page (most accurate)
- B. Run `scripts/fetch_descriptions.py` first to get descriptions, then write a keyword inference script using the description text
- C. Hybrid: run keyword inference, then review/correct in admin

A keyword inference script pass using the existing 307 programs that already have descriptions could populate tags for most camps. Flag any program with no matching keywords for manual review.

---

#### 5. `site_county`: 98% blank for camp programs

Only 10 programs (the afterschool ones, all Chittenden County) have `site_county` set. The County filter in the app is effectively non-functional for summer camps.

**Missing count:** 391/401 programs

**Action:** County can be derived from `site_city` for most programs. Write a script that maps city → county using a Vermont city-to-county lookup table. This is mechanical once the lookup table exists. Many programs also have `site_address` which can be geocoded for county.

**Vermont city→county lookup** (partial, for the cities that appear in our data):
- Burlington, South Burlington, Colchester, Winooski, Essex, Essex Junction, Williston, Shelburne, Charlotte, Hinesburg, Richmond → Chittenden
- Stowe → Lamoille
- Montpelier → Washington
- St. Albans → Franklin
- Fairlee → Orange
- Greensboro → Orleans
- Jay → Orleans
- Thetford → Orange
- Bristol → Addison
- Huntington → Chittenden
- Bolton → Chittenden

---

#### 6. `site_city`: 31% blank for camps

125 camp programs have no city. Without a city, programs won't appear on the map and can't be found via the City filter.

**Missing count:** 125/401

**Action:** City can often be looked up from the org record. A script that copies `city` from `organizations.csv` into `site_city` for programs where `site_city` is blank would fill many of these automatically (valid assumption: most programs run in their org's home city unless `site_address` indicates otherwise).

---

#### 7. `org_type`: 100% blank in organizations.csv

All 148 organizations have a blank `org_type`. This field drives potential filtering by organization type and is required by the schema.

**Missing count:** 148/148

**Allowed values:** `nonprofit`, `municipal`, `school`, `private`, `university`, `faith-based`

**Action:** Many org types are inferable from the org name:
- "Boys & Girls Club", "YMCA", "... Community Center" → `nonprofit`
- "... School District", "... Elementary", "... Middle School" → `school`
- "City of Burlington", "... Parks & Recreation", "... Recreation" → `municipal`
- "University of Vermont", "... College" → `university`
- Write a script to auto-classify obvious cases; manually review the rest

---

#### 8. `financial_aid_available`: 100% blank in organizations.csv

All 148 orgs have blank `financial_aid_available`. This field drives the Financial Aid filter.

**Missing count:** 148/148

**Action:** Research-heavy — requires visiting each org's website to find scholarship/subsidy info. Prioritize the 19 `confidence = confirmed` orgs first. Flag orgs that are `municipal` or `school` type as likely `TRUE` (public programs typically have sliding scale).

---

#### 9. `cost_per_week`: 98% blank for camps

Only the 10 free afterschool programs have `cost_per_week = 0`. The cost filter is non-functional for summer camps.

**Missing count:** ~390/401

**Action:** `cost_raw` is present for ~289 camp programs. Write a cost parser that extracts a weekly dollar amount from raw strings like "$300/week", "$45/day | $60/day with late pickup", "160. *Pre-camp care (8AM-9AM): $10/day*". Many are parseable; ambiguous cases need manual entry.

---

### 🟠 Medium Priority — Quality & Completeness

#### 10. `description`: 31% blank

126 programs have no description. This matters for search and for the detail modal.

**Missing count:** 126/401

**Action:** Run `python scripts/fetch_descriptions.py` — it fetches descriptions from `registration_url` for blank rows. Most of the 381 programs that have a `registration_url` can be auto-fetched. After fetching, run a manual pass on anything that came back too short or clearly wrong.

---

#### 11. `grades_min` / `grades_max`: 33% / 28% blank

131 programs missing `grades_min`, 112 missing `grades_max`.

**Action:** First, run `backfill_age_grade.py` — it fills grades from age data (and vice versa). After that, remaining blanks need manual research from program websites.

---

#### 12. `start_date` / `end_date`: 34% blank

136 programs have no dates. These don't appear in the Calendar view.

**Action:** Dates require visiting each program's website — this is manual research work. Prioritize programs that have a `registration_url` (those websites are most likely to have current dates).

---

#### 13. `org_type` inference for organizations (148 blank)

See item 7 above — worth automating the obvious cases.

---

#### 14. Organizations `county`: 39% blank, `city`: 32% blank

57 orgs have no county, 47 have no city.

**Action:** City and county can often be inferred from the org's programs. If an org has programs with `site_city` set, the org's city is likely the same. A script pass that pulls the most-common `site_city` from an org's programs would fill many gaps.

---

#### 15. Organizations `website`, `phone`, `email`: 91% / 88% / 89% blank

Most orgs are missing contact info. This affects the "More from this organization" modal.

**Action:** Manual research — search each org name to find their website. For hackathon participants, working through the 129 `confidence = likely` orgs alphabetically (Google → fill in contact fields → mark verified) is a good non-technical task. One person can verify 10-20 orgs per hour.

---

#### 16. `verified_date`: 100% blank everywhere

No records have been marked as verified. The admin page supports this (edit modal has `verified_date` field) but no "Mark as Verified" button exists yet.

**Action:** This is a UI feature request (see github issues). For now, use the admin edit modal and manually set the date. A bulk "mark as verified today" button is a good hackathon contribution.

---

#### 17. "Lamoille Valley" as a `site_city` value

Red Clover Camp has `site_city = 'Lamoille Valley'` — this is a region name, not a city. The actual town is likely Johnson, VT.

**Action:** Look up Red Clover Camp's actual address and correct both `site_city` and `site_county`.

---

#### 18. Cosmodôme Space Camp (Montreal, Canada)

8 programs for Cosmodôme are in the dataset with `site_city = 'Montreal'`. This is a Canadian camp, not Vermont. Whether to include it is a content decision.

**Action:** Decide: keep (as a "regional option Vermont families consider") or remove. If keeping, add a note to the description and ensure it doesn't appear in the Vermont map/county filters incorrectly.

---

## Recommended Work Order for the Hackathon

| Track | Who | Est. time | Impact |
| --- | --- | --- | --- |
| 1. Update Burlington Parks Rec + S.Burlington Rec to 2026 dates | 1 researcher | 1-2 hrs | High — ~100 programs fixed |
| 2. Fill `site_county` by city→county mapping script | 1 developer | 30 min | High — fixes the county filter |
| 3. Tag `activities` for all camp programs | 2-3 people | 2-3 hrs | High — enables subject filter |
| 4. Fill `org_type` for all orgs (auto + manual) | 1 developer + review | 1 hr | Medium |
| 5. Run `fetch_descriptions.py` to fill missing descriptions | automated | 20 min | Medium |
| 6. Run cost parser on `cost_raw` → `cost_per_week` | 1 developer | 1-2 hrs | Medium — enables cost filter |
| 7. Verify orgs: website, phone, email (non-technical) | 2-3 people | 2-3 hrs | Medium |
| 8. Fill `site_city` from org city for blanks | 1 developer | 30 min | Medium |
| 9. Fix Vermont Audubon programs (grades, cost, names) | 1 researcher | 30 min | Low-medium |
| 10. Fix end_date < start_date (2 programs) | 1 researcher | 15 min | Low |

---

## Scripts to Write

These scripts don't exist yet but would have high leverage:

### `scripts/infer_counties.py`
Map `site_city` → `site_county` using a Vermont city-to-county lookup table. Write results to `programs.csv`. Also fill `county` in `organizations.csv` where blank.

### `scripts/infer_org_types.py`
Classify `org_type` in `organizations.csv` using keyword matching on `org_name`. Auto-set obvious cases (`School District` → `school`, `YMCA` → `nonprofit`, `City of` → `municipal`). Write a review CSV for ambiguous ones.

### `scripts/parse_costs.py`
Extract a numeric weekly cost from `cost_raw` into `cost_per_week`. Handle formats like `$300/week`, `$45/day`, `$300 per week`, `sliding scale` (→ 0). Write a review CSV for unparseable values.

### `scripts/infer_activities.py`
Scan `description` and `program_name` for keywords from the canonical tag list and populate `activities`. Use the existing descriptions to tag 307 programs that already have text.

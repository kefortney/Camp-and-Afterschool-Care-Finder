"""
Validate organizations.csv and programs.csv for foreign key integrity,
required fields, and enum values before building data.js.

Run from project root:
  python scripts/validate_data.py

Exit code 0 = no errors (warnings OK).
Exit code 1 = at least one ERROR (build should be blocked).
"""

import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT        = Path(__file__).parent.parent
ORGS_CSV    = ROOT / "data/organizations.csv"
PROGRAMS_CSV = ROOT / "data/programs.csv"

VALID_ORG_TYPES   = {"nonprofit", "municipal", "school", "private", "university", "faith-based"}
VALID_COUNTIES    = {"Addison", "Bennington", "Caledonia", "Chittenden", "Essex",
                     "Franklin", "Grand Isle", "Lamoille", "Orange", "Orleans",
                     "Rutland", "Washington", "Windham", "Windsor"}
VALID_CONFIDENCE  = {"confirmed", "likely", "inactive"}
VALID_PROG_TYPES  = {"camp", "afterschool"}
VALID_SESSION     = {"day", "residential", "hybrid", "drop-in"}
VALID_SCHEDULE    = {"weekly", "daily", "seasonal", "year-round"}
VALID_GRADES      = {"PK", "K", "1", "2", "3", "4", "5", "6",
                     "7", "8", "9", "10", "11", "12"}
GRADE_ORDER       = ["PK", "K", "1","2","3","4","5","6","7","8","9","10","11","12"]
VALID_BOOLS       = {"TRUE", "FALSE", "true", "false", "True", "False", "1", "0", "yes", "no", ""}
CANONICAL_ACTIVITIES = {
    "STEM", "Coding", "Robotics", "Science", "Math", "Arts", "Music",
    "Theater", "Dance", "Sports", "Outdoor Education", "Nature", "Swimming",
    "Hiking", "Horseback Riding", "Cooking", "Language", "Leadership",
    "Community Service", "Special Needs Support", "Academic Enrichment",
    "Maker", "Film & Media",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")


def is_url(v: str) -> bool:
    if not v:
        return True  # blank is OK
    try:
        r = urlparse(v)
        return r.scheme in ("http", "https") and bool(r.netloc)
    except Exception:
        return False


def grade_index(g: str) -> int:
    try:
        return GRADE_ORDER.index(g)
    except ValueError:
        return -1


errors: list[str] = []
warnings: list[str] = []


def err(msg: str):
    errors.append(f"  ERROR: {msg}")


def warn(msg: str):
    warnings.append(f"  WARN:  {msg}")


def validate_orgs() -> set[str]:
    """Returns set of valid org_ids."""
    valid_ids: set[str] = set()

    if not ORGS_CSV.exists():
        err(f"organizations.csv not found at {ORGS_CSV}")
        return valid_ids

    seen_ids: dict[str, int] = {}
    with open(ORGS_CSV, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            oid = (row.get("org_id") or "").strip()
            name = (row.get("org_name") or "").strip()
            label = f"orgs row {i} ({oid or 'NO_ID'})"

            # Required fields
            if not oid:
                err(f"{label}: org_id is blank")
                continue
            if not name:
                err(f"{label}: org_name is blank")

            # Slug format
            if oid and not SLUG_RE.match(oid):
                err(f"{label}: org_id '{oid}' is not valid kebab-case (no spaces/uppercase)")

            # Duplicate check
            if oid in seen_ids:
                err(f"{label}: duplicate org_id '{oid}' (also at row {seen_ids[oid]})")
            else:
                seen_ids[oid] = i
                valid_ids.add(oid)

            # Enum checks
            org_type = (row.get("org_type") or "").strip()
            if org_type and org_type not in VALID_ORG_TYPES:
                err(f"{label}: org_type '{org_type}' not in {sorted(VALID_ORG_TYPES)}")

            county = (row.get("county") or "").strip()
            if county and county not in VALID_COUNTIES:
                err(f"{label}: county '{county}' not a valid Vermont county")

            confidence = (row.get("confidence") or "").strip()
            if confidence not in VALID_CONFIDENCE:
                err(f"{label}: confidence '{confidence}' not in {sorted(VALID_CONFIDENCE)}")

            # Optional format checks
            website = (row.get("website") or "").strip()
            if not is_url(website):
                warn(f"{label}: website '{website}' does not look like a URL")

            email = (row.get("email") or "").strip()
            if email and "@" not in email:
                warn(f"{label}: email '{email}' does not contain @")

            vdate = (row.get("verified_date") or "").strip()
            if vdate and not DATE_RE.match(vdate):
                warn(f"{label}: verified_date '{vdate}' is not YYYY-MM-DD")

            fin_aid = (row.get("financial_aid_available") or "").strip()
            if fin_aid and fin_aid not in VALID_BOOLS:
                warn(f"{label}: financial_aid_available '{fin_aid}' should be TRUE or FALSE")

    return valid_ids


def validate_programs(valid_org_ids: set[str]):
    if not PROGRAMS_CSV.exists():
        err(f"programs.csv not found at {PROGRAMS_CSV}")
        return

    seen_ids: dict[str, int] = {}
    with open(PROGRAMS_CSV, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            pid     = (row.get("program_id") or "").strip()
            org_id  = (row.get("org_id") or "").strip()
            name    = (row.get("program_name") or "").strip()
            label   = f"programs row {i} ({pid[:40] or 'NO_ID'})"

            # Hard-required fields (must have a value)
            for col in ("program_id", "org_id", "program_name", "program_type",
                        "program_year", "session_type", "schedule_type", "confidence"):
                if not (row.get(col) or "").strip():
                    err(f"{label}: required field '{col}' is blank")
            # Soft-required fields (warn when blank — backfill_age_grade.py can fill these)
            for col in ("grades_min", "grades_max"):
                if not (row.get(col) or "").strip():
                    warn(f"{label}: '{col}' is blank (run backfill_age_grade.py)")

            # Duplicate program_id
            if pid:
                if pid in seen_ids:
                    err(f"{label}: duplicate program_id (also at row {seen_ids[pid]})")
                else:
                    seen_ids[pid] = i

            # Foreign key check
            if org_id and org_id not in valid_org_ids:
                err(f"{label}: org_id '{org_id}' not found in organizations.csv")

            # Enum checks
            for col, valid_set in [
                ("program_type", VALID_PROG_TYPES),
                ("session_type",  VALID_SESSION),
                ("schedule_type", VALID_SCHEDULE),
                ("confidence",    VALID_CONFIDENCE),
            ]:
                v = (row.get(col) or "").strip()
                if v and v not in valid_set:
                    err(f"{label}: {col} '{v}' not in allowed values {sorted(valid_set)}")

            # Grade ordering
            gmin = (row.get("grades_min") or "").strip()
            gmax = (row.get("grades_max") or "").strip()
            if gmin and gmin not in VALID_GRADES:
                warn(f"{label}: grades_min '{gmin}' not a recognized grade")
            if gmax and gmax not in VALID_GRADES:
                warn(f"{label}: grades_max '{gmax}' not a recognized grade")
            if gmin and gmax and gmin in VALID_GRADES and gmax in VALID_GRADES:
                if grade_index(gmin) > grade_index(gmax):
                    warn(f"{label}: grades_min '{gmin}' > grades_max '{gmax}'")

            # Date ordering
            sdate = (row.get("start_date") or "").strip()
            edate = (row.get("end_date") or "").strip()
            if sdate and not DATE_RE.match(sdate):
                warn(f"{label}: start_date '{sdate}' is not YYYY-MM-DD")
            if edate and not DATE_RE.match(edate):
                warn(f"{label}: end_date '{edate}' is not YYYY-MM-DD")
            if sdate and edate and DATE_RE.match(sdate) and DATE_RE.match(edate):
                if sdate > edate:
                    warn(f"{label}: start_date '{sdate}' is after end_date '{edate}'")

            # Cost
            cost = (row.get("cost_per_week") or "").strip()
            if cost:
                try:
                    float(cost)
                except ValueError:
                    warn(f"{label}: cost_per_week '{cost}' is not numeric")

            # Activities tags
            activities = (row.get("activities") or "").strip()
            if activities:
                for tag in [t.strip() for t in activities.split(",") if t.strip()]:
                    if tag not in CANONICAL_ACTIVITIES:
                        warn(f"{label}: activity tag '{tag}' not in canonical list")

            # URL check
            reg_url = (row.get("registration_url") or "").strip()
            if not is_url(reg_url):
                warn(f"{label}: registration_url '{reg_url}' does not look like a URL")

            # Verified date
            vdate = (row.get("verified_date") or "").strip()
            if vdate and not DATE_RE.match(vdate):
                warn(f"{label}: verified_date '{vdate}' is not YYYY-MM-DD")


def main():
    print("Validating organizations.csv...")
    valid_org_ids = validate_orgs()
    print(f"  {len(valid_org_ids)} org IDs loaded")

    print("Validating programs.csv...")
    validate_programs(valid_org_ids)

    print()
    if errors:
        print(f"ERRORS ({len(errors)}) — build is blocked:")
        for e in errors:
            print(e)
    else:
        print("No errors.")

    if warnings:
        # Limit warning output to first 40 so it's readable
        shown = warnings[:40]
        print(f"\nWarnings ({len(warnings)} total{', showing first 40' if len(warnings) > 40 else ''}):")
        for w in shown:
            print(w)
    else:
        print("No warnings.")

    print()
    if errors:
        print("RESULT: FAIL — fix errors before running build_data_js.py")
        sys.exit(1)
    else:
        print("RESULT: PASS — safe to run build_data_js.py")


if __name__ == "__main__":
    main()

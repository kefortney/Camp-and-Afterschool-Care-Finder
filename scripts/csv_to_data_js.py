"""
Convert data/2026 Summer Camp.csv → data.js

Run from the project root:
    python3 scripts/csv_to_data_js.py
"""

import csv
import json
import re
from pathlib import Path

CAMP_PATH = Path("data/2026 Summer Camp.csv")
OUT_PATH = Path("data.js")

GRADE_ORDER = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

# ── helpers ──────────────────────────────────────────────────────────────────

def normalize_grade(raw: str) -> str:
    val = raw.strip().upper()
    if val in ("K", "KINDER", "KINDERGARTEN"):
        return "K"
    if val in GRADE_ORDER:
        return val
    return ""


def grade_from_age(age_str: str, is_start: bool) -> str:
    """Map age → approximate grade."""
    try:
        age = int(age_str.strip())
    except (ValueError, AttributeError):
        return ""
    # start-of-year ages: 5→K, 6→1, …, 17→12
    grade_index = age - 5
    if is_start:
        grade_index = age - 5
    else:
        grade_index = age - 6   # end age is exclusive-ish
    if 0 <= grade_index < len(GRADE_ORDER):
        return GRADE_ORDER[grade_index]
    return ""


def parse_cost(raw: str):
    """
    Return (cost_int, period_str) from a messy cost string.
    period is one of: 'week', 'day', 'month', 'session'.
    Returns (None, None) if no dollar amount found.
    """
    if not raw:
        return None, None

    text = raw.lower()

    # Find all dollar amounts like $300, $1,200, $1200
    amounts = re.findall(r"\$([0-9,]+(?:\.[0-9]{1,2})?)", text)
    if not amounts:
        # Try bare numbers preceded by nothing special
        amounts = re.findall(r"(?<!\d)([0-9]{2,5})(?!\d)", text)
    if not amounts:
        return None, None

    # Pick the first clean amount
    try:
        cost = int(amounts[0].replace(",", "").split(".")[0])
    except ValueError:
        return None, None

    # Determine period
    if "per week" in text or "/week" in text or "week" in text:
        period = "week"
    elif "per day" in text or "/day" in text or "day" in text:
        period = "day"
    elif "per month" in text or "/month" in text or "month" in text:
        period = "month"
    else:
        period = "session"

    return cost, period


def has_scholarship(cost_text: str, notes_text: str) -> bool:
    combined = ((cost_text or "") + " " + (notes_text or "")).lower()
    keywords = ["scholarship", "financial aid", "sliding scale", "subsidy",
                "income-based", "need-based", "assistance", "reduced", "free"]
    return any(kw in combined for kw in keywords)


SUBJECT_KEYWORDS = [
    ("STEM",               ["stem"]),
    ("Science",            ["science", "biology", "chemistry", "physics", "ecology", "botany"]),
    ("Technology",         ["technology", "engineering", "robotics", "maker", "makerspace"]),
    ("Coding",             ["coding", "programming", "python", "javascript", "web dev", "game design", "app"]),
    ("Math",               ["math", "mathematics"]),
    ("Reading",            ["reading", "literacy", "books"]),
    ("Writing",            ["writing", "creative writing", "journalism", "poetry", "fiction"]),
    ("Arts",               ["art", "arts", "craft", "crafts", "painting", "sculpture", "drawing", "ceramics", "visual"]),
    ("Drama",              ["drama", "theater", "theatre", "acting", "improv", "musical"]),
    ("Music",              ["music", "singing", "band", "orchestra", "guitar", "piano", "instruments", "choir"]),
    ("Sports",             ["sport", "sports", "athletic", "athletics"]),
    ("Soccer",             ["soccer", "football"]),
    ("Basketball",         ["basketball"]),
    ("Outdoor Education",  ["outdoor", "wilderness", "nature", "hiking", "kayak", "canoe", "camping",
                             "environmental", "conservation", "garden", "gardening", "farm", "farming",
                             "forest", "archery", "climbing"]),
    ("Dance",              ["dance", "dancing", "ballet", "hip hop"]),
    ("Equestrian",         ["horse", "equestrian", "riding", "pony"]),
    ("Swim",               ["swim", "swimming", "aquatic", "water"]),
    ("Cooking",            ["cook", "cooking", "culinary", "baking", "food"]),
]


def extract_subjects(name: str, description: str) -> list:
    text = ((name or "") + " " + (description or "")).lower()
    found = []
    for label, keywords in SUBJECT_KEYWORDS:
        if any(kw in text for kw in keywords):
            found.append(label)
    return found


def build_fallback_description(org: str, name: str, city: str, subjects: list,
                               sg: str, eg: str, cost: int, period: str) -> str:
    """Generate a plain-English description from available metadata."""
    parts = []

    camp_label = name if name and name != org else "this summer program"
    parts.append(f"{org} offers {camp_label}")

    location = f"in {city}, VT" if city else "in Vermont"
    parts[0] += f" {location}."

    if sg and eg:
        if sg == eg:
            parts.append(f"Open to students in grade {sg}.")
        else:
            parts.append(f"Open to students in grades {sg}–{eg}.")

    if subjects:
        subj_str = ", ".join(subjects[:4])
        parts.append(f"Activities include {subj_str}.")

    if cost and cost > 0:
        parts.append(f"Cost: ${cost:,} per {period}.")

    return " ".join(parts)


def build_hours(start_time: str, end_time: str) -> str:
    s = (start_time or "").strip()
    e = (end_time or "").strip()
    if s and e:
        return f"{s} – {e}"
    if s:
        return f"Starts {s}"
    if e:
        return f"Until {e}"
    return ""


def normalize_date(raw: str) -> str:
    """Normalize M/D/YYYY or M/D/YY to YYYY-MM-DD for consistent JS sorting."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})$", raw)
    if not m:
        return raw
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    return f"{year:04d}-{month:02d}-{day:02d}"


# ── main conversion ───────────────────────────────────────────────────────────

def convert():
    with CAMP_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    programs = []
    uid = 1

    for row in rows:
        org      = (row.get("Organization") or "").strip()
        name     = (row.get("Camp Name") or "").strip() or org
        website  = (row.get("Webpage") or "").strip()
        desc     = (row.get("Camp Description") or "").strip()
        city     = (row.get("City") or "").strip()
        location = (row.get("Location") or "").strip()
        cost_raw = (row.get("Cost") or "").strip()
        notes    = (row.get("Notes") or "").strip()
        reg_text = (row.get("Registration") or "").strip()

        # Skip rows with no meaningful identity
        if not org and not name:
            continue

        # Grades
        sg = normalize_grade(row.get("Start Grade") or "")
        eg = normalize_grade(row.get("End Grade") or "")
        if not sg:
            sg = grade_from_age(row.get("Start Age") or "", is_start=True)
        if not eg:
            eg = grade_from_age(row.get("End Age") or "", is_start=False)

        # Ages
        try:
            age_min = int((row.get("Start Age") or "").strip())
        except ValueError:
            age_min = None
        try:
            age_max = int((row.get("End Age") or "").strip())
        except ValueError:
            age_max = None

        # Cost
        cost_val, cost_period = parse_cost(cost_raw)
        scholarship = has_scholarship(cost_raw, notes)

        # Hours
        hours = build_hours(row.get("Start Time"), row.get("End Time"))

        # Subjects
        subjects = extract_subjects(name, desc)

        # Fallback description if blank
        if not desc:
            desc = build_fallback_description(
                org, name, city, subjects,
                sg, eg, cost_val, cost_period or "session"
            )

        # Dates
        start_date = normalize_date(row.get("Start Date") or "")
        end_date   = normalize_date(row.get("End Date") or "")

        # Type
        pre_after = (row.get("Pre/After Care") or "").strip().lower()
        prog_type = "Both" if pre_after in ("yes", "y", "true") else "Summer Camp"

        entry = {
            "id":                  uid,
            "name":                name,
            "type":                prog_type,
            "organization":        org,
            "address":             location,
            "city":                city,
            "state":               "VT",
            "zip":                 "",
            "phone":               "",
            "email":               "",
            "website":             website,
            "gradesMin":           sg,
            "gradesMax":           eg,
            "ageMin":              age_min,
            "ageMax":              age_max,
            "cost":                cost_val if cost_val is not None else 0,
            "costPeriod":          cost_period or "session",
            "scholarshipAvailable": scholarship,
            "hours":               hours,
            "daysOffered":         "Mon–Fri",
            "sessionType":         "Summer",
            "subjects":            subjects,
            "description":         desc,
            "indoorOutdoor":       "Both",
            "transportation":      False,
            "mealsProvided":       False,
            "acceptingRegistration": True,
            "startDate":             start_date,
            "endDate":               end_date,
        }

        programs.append(entry)
        uid += 1

    # Write data.js
    js_array = json.dumps(programs, indent=2, ensure_ascii=False)
    output = f"const programsData = {js_array};\n"
    OUT_PATH.write_text(output, encoding="utf-8")

    print(f"Written {len(programs)} programs to {OUT_PATH}")

    # Summary
    with_city    = sum(1 for p in programs if p["city"])
    with_grades  = sum(1 for p in programs if p["gradesMin"] and p["gradesMax"])
    with_cost    = sum(1 for p in programs if p["cost"] > 0)
    with_hours   = sum(1 for p in programs if p["hours"])
    with_subjects = sum(1 for p in programs if p["subjects"])
    with_dates    = sum(1 for p in programs if p["startDate"])
    print(f"  city present:    {with_city}/{len(programs)}")
    print(f"  grades present:  {with_grades}/{len(programs)}")
    print(f"  cost > 0:        {with_cost}/{len(programs)}")
    print(f"  hours present:   {with_hours}/{len(programs)}")
    print(f"  subjects found:  {with_subjects}/{len(programs)}")
    print(f"  dates present:   {with_dates}/{len(programs)}")


if __name__ == "__main__":
    convert()

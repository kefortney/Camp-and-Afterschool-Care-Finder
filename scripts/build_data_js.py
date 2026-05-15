"""
Build data.js from data/organizations.csv + data/programs.csv.

Replaces csv_to_data_js.py. Runs validate_data.py first — aborts on errors.

Run from project root:
    python scripts/build_data_js.py

Outputs data.js containing:
    const PROGRAMS = [...];       // all programs with org fields merged in
    const ORGANIZATIONS = [...];  // full org list for the "More from this org" modal
"""

import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).parent.parent
ORGS_CSV     = ROOT / "data/organizations.csv"
PROGRAMS_CSV = ROOT / "data/programs.csv"
OUT_PATH     = ROOT / "data.js"
VALIDATE     = ROOT / "scripts/validate_data.py"

GRADE_ORDER = ["K","1","2","3","4","5","6","7","8","9","10","11","12"]


# ── Normalization helpers (carried from csv_to_data_js.py) ───────────────────

def normalize_grade(raw: str) -> str:
    val = (raw or "").strip().upper()
    if val in ("K", "KINDER", "KINDERGARTEN"):
        return "K"
    if val in GRADE_ORDER:
        return val
    return ""


def grade_from_age(age_str: str, is_start: bool) -> str:
    try:
        age = int((age_str or "").strip())
    except (ValueError, AttributeError):
        return ""
    grade_index = (age - 5) if is_start else (age - 6)
    if 0 <= grade_index < len(GRADE_ORDER):
        return GRADE_ORDER[grade_index]
    return ""


def parse_cost(raw: str):
    """Return (cost_int, period_str) from a messy cost string."""
    if not raw:
        return None, None
    text = raw.lower()
    if any(w in text for w in ("free", "no cost", "no charge", "federally")):
        return 0, "session"
    amounts = re.findall(r"\$([0-9,]+(?:\.[0-9]{1,2})?)", text)
    if not amounts:
        amounts = re.findall(r"(?<!\d)([0-9]{2,5})(?!\d)", text)
    if not amounts:
        return None, None
    try:
        cost = int(amounts[0].replace(",", "").split(".")[0])
    except ValueError:
        return None, None
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
    return any(kw in combined for kw in (
        "scholarship", "financial aid", "sliding scale", "subsidy",
        "income-based", "need-based", "assistance", "reduced",
    ))


def normalize_bool(v: str) -> bool:
    return (v or "").strip().lower() in ("true", "yes", "1")


def normalize_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})$", raw)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}-{day:02d}"
    return raw


def build_hours(start_time: str, end_time: str) -> str:
    s = (start_time or "").strip()
    e = (end_time or "").strip()
    if s and e:
        return f"{s} – {e}"
    return s or e or ""


SUBJECT_KEYWORDS = [
    ("STEM",             ["stem"]),
    ("Science",          ["science","biology","chemistry","physics","ecology","botany",
                          "paleontolog","astrono","space camp","rocket science","geology"]),
    ("Technology",       ["technology","engineering","robotics","maker","makerspace",
                          "3d print","fabricat","electronics"]),
    ("Coding",           ["coding","programming","python","javascript","web dev",
                          "game design","minecraft","computer science","app development","scratch"]),
    ("Math",             ["math","mathematics"]),
    ("Chess",            ["chess"]),
    ("Reading",          ["reading","literacy","books"]),
    ("Writing",          ["writing","creative writing","journalism","poetry","fiction",
                          "storytell","dungeons","d&d","role-playing","narrative"]),
    ("Arts",             ["art","arts","craft","crafts","painting","sculpture","drawing",
                          "ceramics","visual","printmaking","pottery","collage","illustration",
                          "mosaic","photography","filmmaking","animation","textile","fiber arts"]),
    ("Drama",            ["drama","theater","theatre","acting","improv","musical",
                          "stagecraft","playwriting","puppetry"]),
    ("Circus",           ["circus","acrobat","juggling","clown","aerial","trapeze",
                          "smirkus","stilts","tightrope"]),
    ("Music",            ["music","singing","band","orchestra","guitar","piano",
                          "instrument","choir","drum","ukulele","songwrit","violin",
                          "cello","composit"]),
    ("Dance",            ["dance","dancing","ballet","hip hop","hip-hop","tap dance",
                          "contemporary dance","ballroom","salsa","latin dance"]),
    ("Tennis",           ["tennis","pickleball"]),
    ("Martial Arts",     ["martial art","aikido","karate","judo","jiu-jitsu",
                          "taekwondo","kung fu","self-defense","wrestling"]),
    ("Gymnastics",       ["gymnastics","gymnast","tumbling"]),
    ("Yoga",             ["yoga"]),
    ("Skateboarding",    ["skate camp","skateboard","skating camp","skate school","skate park"]),
    ("Soccer",           ["soccer"]),
    ("Basketball",       ["basketball"]),
    ("Volleyball",       ["volleyball"]),
    ("Hockey",           ["hockey"]),
    ("Lacrosse",         ["lacrosse"]),
    ("Baseball",         ["baseball","softball"]),
    ("Sports",           ["sport","sports","athletic","athletics","multi-sport","multisport"]),
    ("Mountain Biking",  ["mountain bike","mountain biking","mtb"]),
    ("Disc Golf",        ["disc golf","disk golf"]),
    ("Ultimate Frisbee", ["ultimate frisbee","ultimate disc","ultimate camp"]),
    ("Sailing",          ["sail","sailing","windsurf","windsurfing","nautical","regatta","boating"]),
    ("Swim",             ["swim","swimming","aquatic","pool","water safety","lifeguard"]),
    ("Outdoor Education",["outdoor","wilderness","nature","hiking","kayak","canoe",
                          "camping","environmental","conservation","garden","gardening",
                          "farm","farming","forest","archery","climbing","trail",
                          "backpack","survival","adventure"]),
    ("Equestrian",       ["horse","equestrian","riding","pony","mounted","stable","equine"]),
    ("Cooking",          ["cook","cooking","culinary","baking","food","chef","nutrition","restaurant"]),
    ("Animals",          ["animal","veterinar","wildlife","creature","humane society",
                          "zoolog","pet care","paw paw"]),
]


def extract_subjects(name: str, description: str, existing_activities: str) -> list:
    # If activities are already set in programs.csv, use those
    if existing_activities and existing_activities.strip():
        return [a.strip() for a in existing_activities.split(",") if a.strip()]
    # Otherwise infer from name + description
    text = ((name or "") + " " + (description or "")).lower()
    found = []
    for label, keywords in SUBJECT_KEYWORDS:
        if any(kw in text for kw in keywords):
            found.append(label)
    return found


def build_fallback_description(org_name, prog_name, city, subjects, sg, eg, cost, period):
    parts = []
    label = prog_name if prog_name and prog_name != org_name else "this summer program"
    parts.append(f"{org_name} offers {label}")
    location = f"in {city}, VT" if city else "in Vermont"
    parts[0] += f" {location}."
    if sg and eg:
        parts.append(f"Open to grades {sg}–{eg}." if sg != eg else f"Open to grade {sg}.")
    if subjects:
        parts.append(f"Activities include {', '.join(subjects[:4])}.")
    if cost and cost > 0:
        parts.append(f"Cost: ${cost:,} per {period}.")
    return " ".join(parts)


# ── Load data ────────────────────────────────────────────────────────────────

def load_orgs() -> dict:
    orgs = {}
    with open(ORGS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = (row.get("org_id") or "").strip()
            if oid:
                orgs[oid] = {k: (v or "").strip() for k, v in row.items()}
    return orgs


def load_programs() -> list:
    with open(PROGRAMS_CSV, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(f)]


# ── Build JS program objects ─────────────────────────────────────────────────

def build_program_obj(prog: dict, org: dict, uid: int) -> dict:
    org_id      = prog.get("org_id", "")
    prog_type   = prog.get("program_type", "camp")
    is_free     = prog.get("cost_per_week") == "0" or prog.get("cost_raw", "").lower() == "free"

    # City and address: program site overrides org
    city    = prog.get("site_city") or org.get("city", "")
    address = prog.get("site_address") or org.get("street_address", "")
    county  = prog.get("site_county") or org.get("county", "")

    # Grades
    sg = normalize_grade(prog.get("grades_min", ""))
    eg = normalize_grade(prog.get("grades_max", ""))
    if not sg:
        sg = grade_from_age(prog.get("age_min", ""), is_start=True)
    if not eg:
        eg = grade_from_age(prog.get("age_max", ""), is_start=False)

    # Ages
    try:
        age_min = int(prog.get("age_min", ""))
    except (ValueError, TypeError):
        age_min = None
    try:
        age_max = int(prog.get("age_max", ""))
    except (ValueError, TypeError):
        age_max = None

    # Cost
    cost_raw = prog.get("cost_raw", "")
    cost_notes = prog.get("cost_notes", "")
    if prog.get("cost_per_week"):
        try:
            cost_val  = int(float(prog["cost_per_week"]))
            cost_period = "week"
        except ValueError:
            cost_val, cost_period = parse_cost(cost_raw)
    else:
        cost_val, cost_period = parse_cost(cost_raw)

    if is_free:
        cost_val   = 0
        cost_period = "session"

    scholarship = (
        normalize_bool(org.get("financial_aid_available", ""))
        or has_scholarship(cost_raw, cost_notes)
    )

    # Subjects
    name = prog.get("program_name", "")
    desc = prog.get("description", "")
    subjects = extract_subjects(name, desc, prog.get("activities", ""))

    # Fallback description
    if not desc:
        desc = build_fallback_description(
            org.get("org_name", org_id), name, city,
            subjects, sg, eg, cost_val, cost_period or "session",
        )

    # Hours
    hours = build_hours(prog.get("start_time", ""), prog.get("end_time", ""))

    # Registration
    reg_url = prog.get("registration_url", "") or org.get("website", "")
    accepting = prog.get("confidence", "confirmed") != "inactive"

    # Type label
    if prog_type == "afterschool":
        type_label = prog.get("funding_source", "") or "Afterschool"
        if "21" in type_label:
            type_label = "21CCLC Afterschool (Free)"
    elif prog.get("pre_after_care", "").lower() in ("yes", "y", "true"):
        type_label = "Both"
    else:
        type_label = "Summer Camp"

    return {
        "id":                   uid,
        "uid":                  f"{prog_type}-{uid}",
        "category":             prog_type,
        "name":                 name,
        "type":                 type_label,
        "isFree":               is_free,
        "organization":         org.get("org_name", org_id),
        "orgId":                org_id,
        "orgName":              org.get("org_name", ""),
        "address":              address,
        "city":                 city,
        "state":                org.get("state", "VT"),
        "zip":                  org.get("zip", ""),
        "county":               county,
        "phone":                org.get("phone", ""),
        "email":                org.get("email", ""),
        "website":              reg_url,
        "gradesMin":            sg,
        "gradesMax":            eg,
        "ageMin":               age_min,
        "ageMax":               age_max,
        "cost":                 cost_val if cost_val is not None else 0,
        "costPeriod":           cost_period or "session",
        "scholarshipAvailable": scholarship,
        "hours":                hours,
        "daysOffered":          prog.get("days_of_week", "Mon–Fri"),
        "sessionType":          prog.get("schedule_type", "weekly").title(),
        "subjects":             subjects,
        "description":          desc,
        "indoorOutdoor":        "Both",
        "transportation":       normalize_bool(prog.get("transportation_provided", "")),
        "mealsProvided":        normalize_bool(prog.get("meals_provided", "")),
        "acceptingRegistration": accepting,
        "startDate":            normalize_date(prog.get("start_date", "")),
        "endDate":              normalize_date(prog.get("end_date", "")),
        "starsLevel":           org.get("stars_rating", ""),
        "referralStatus":       "Active" if accepting else "Inactive",
        "providerProgramType":  type_label,
        "programType":          prog_type,
        "confidence":           prog.get("confidence", "confirmed"),
        "fundingSource":        prog.get("funding_source", ""),
        # Raw CSV pass-throughs for admin round-trip
        "programId":      prog.get("program_id", ""),
        "programYear":    prog.get("program_year", "2026"),
        "registrationUrl": prog.get("registration_url", ""),
        "registrationOpens":      prog.get("registration_opens", ""),
        "registrationOpensEarly": prog.get("registration_opens_early", ""),
        "registrationNotes":      prog.get("registration_notes", ""),
        "startTime":      prog.get("start_time", ""),
        "endTime":        prog.get("end_time", ""),
        "sessionTypeCsv": prog.get("session_type", ""),
        "scheduleTypeCsv": prog.get("schedule_type", "weekly"),
        "preAfterCare":   prog.get("pre_after_care", ""),
        "costRaw":        prog.get("cost_raw", ""),
        "activitiesCsv":  prog.get("activities", ""),
        "transportNotes": prog.get("transportation_notes", ""),
        "verifiedDate":   prog.get("verified_date", ""),
        "programNotes":   prog.get("notes", ""),
    }


def build_org_obj(org: dict) -> dict:
    return {
        "orgId":   org.get("org_id", ""),
        "name":    org.get("org_name", ""),
        "type":    org.get("org_type", ""),
        "website": org.get("website", ""),
        "phone":   org.get("phone", ""),
        "email":   org.get("email", ""),
        "address": org.get("street_address", ""),
        "city":    org.get("city", ""),
        "county":  org.get("county", ""),
        "state":   org.get("state", "VT"),
        "zip":     org.get("zip", ""),
        "financialAidAvailable": org.get("financial_aid_available", "").lower() in ("true","yes","1"),
        "financialAidNotes":     org.get("financial_aid_notes", ""),
        "confidence":            org.get("confidence", "likely"),
        "registrationPolicy": org.get("registration_policy", ""),
        "registrationOpens":  org.get("registration_opens", ""),
        "verifiedDate":       org.get("verified_date", ""),
        "notes":              org.get("notes", ""),
    }


def main():
    # Run validation first — abort on errors
    result = subprocess.run(
        [sys.executable, str(VALIDATE)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Validation failed — fix errors before building data.js:\n")
        print(result.stdout)
        sys.exit(1)

    orgs     = load_orgs()
    programs = load_programs()

    program_objs = []
    uid = 1
    for prog in programs:
        org_id = prog.get("org_id", "")
        org    = orgs.get(org_id, {"org_id": org_id, "org_name": org_id})
        # Skip inactive programs
        if prog.get("confidence") == "inactive":
            continue
        obj = build_program_obj(prog, org, uid)
        program_objs.append(obj)
        uid += 1

    org_objs = [build_org_obj(o) for o in orgs.values()
                if o.get("confidence") != "inactive"]

    # Stats
    camps       = [p for p in program_objs if p["category"] == "camp"]
    afterschool = [p for p in program_objs if p["category"] == "afterschool"]
    now_str     = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    programs_js = json.dumps(program_objs, indent=2, ensure_ascii=False)
    orgs_js     = json.dumps(org_objs, indent=2, ensure_ascii=False)

    output = (
        f"// Auto-generated by scripts/build_data_js.py — do not edit directly\n"
        f"// Generated: {now_str} | Orgs: {len(org_objs)} | Programs: {len(program_objs)}"
        f" | Camps: {len(camps)} | Afterschool: {len(afterschool)}\n\n"
        f"const PROGRAMS = {programs_js};\n\n"
        f"const ORGANIZATIONS = {orgs_js};\n"
    )
    OUT_PATH.write_text(output, encoding="utf-8")

    print(f"data.js written")
    print(f"  Organizations: {len(org_objs)}")
    print(f"  Programs:      {len(program_objs)} ({len(camps)} camps, {len(afterschool)} afterschool)")

    with_city    = sum(1 for p in program_objs if p["city"])
    with_grades  = sum(1 for p in program_objs if p["gradesMin"] and p["gradesMax"])
    with_cost    = sum(1 for p in program_objs if p["cost"] > 0)
    with_dates   = sum(1 for p in program_objs if p["startDate"])
    with_subjects = sum(1 for p in program_objs if p["subjects"])
    print(f"  city present:   {with_city}/{len(program_objs)}")
    print(f"  grades present: {with_grades}/{len(program_objs)}")
    print(f"  cost > 0:       {with_cost}/{len(program_objs)}")
    print(f"  dates present:  {with_dates}/{len(program_objs)}")
    print(f"  subjects found: {with_subjects}/{len(program_objs)}")


if __name__ == "__main__":
    main()

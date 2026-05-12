"""
Parse cost_raw into a normalized cost_per_week value.

Fills blank cost_per_week fields only — never overwrites existing non-zero values.
Many camp costs are variable or ambiguous; this script makes a best-effort parse.
Manual review of the output is expected.

Parsing rules:
  - "free" / "no cost" / "no charge" -> 0
  - "$X/week" or "$X per week"        -> X
  - "$X/day" or "$X per day"          -> X * 5  (assumes 5-day week)
  - "$X/session"                      -> X  (treated as per-week)
  - "$X" bare dollar amount           -> X  (assumed weekly; flag for review)
  - "$X-$Y" range                     -> midpoint
  - "sliding scale" / "contact"       -> blank (leave for manual)

Run from the project root:
    python scripts/parse_costs.py
"""

import csv
import re
from pathlib import Path

PROGRAMS_PATH = Path("data/programs.csv")


def parse_cost(raw: str):
    """Return (cost_per_week: float|None, needs_review: bool)."""
    text = (raw or "").strip().lower()
    if not text:
        return None, False

    # Explicit free
    if re.search(r"\bfree\b|\bno cost\b|\bno charge\b|\$0\b", text):
        return 0.0, False

    # Ambiguous / contact-required
    if re.search(r"sliding scale|contact|call us|see website|varies|variable|tbd|n/a|upon request", text):
        return None, False

    # Extract all dollar amounts in order
    amounts = [float(m.replace(",", "")) for m in re.findall(r"\$?(\d[\d,]*(?:\.\d+)?)", text)]
    if not amounts:
        return None, False

    # Per-day pricing
    if re.search(r"/\s*day\b|per\s+day", text):
        # Use first (lowest) amount, multiply by 5
        cost = min(amounts) * 5
        return round(cost, 2), True  # flag: daily rate conversion is approximate

    # Per-hour pricing — skip, too ambiguous
    if re.search(r"/\s*hour|per\s+hour", text):
        return None, False

    # Per-week / per-session / general
    if re.search(r"/\s*week|per\s+week|weekly", text):
        cost = min(amounts)  # use lower bound of any range
        return round(cost, 2), False

    if re.search(r"/\s*session|per\s+session", text):
        cost = min(amounts)
        return round(cost, 2), True

    # Bare dollar amount — assume weekly, flag for review
    if amounts:
        cost = min(amounts)
        return round(cost, 2), True

    return None, False


def main():
    with PROGRAMS_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filled = 0
    flagged = 0
    skipped_existing = 0
    skipped_no_parse = 0

    for row in rows:
        existing = (row.get("cost_per_week") or "").strip()
        # Skip if already has a non-blank value (including "0" for free programs)
        if existing != "":
            skipped_existing += 1
            continue

        raw = (row.get("cost_raw") or "").strip()
        cost, needs_review = parse_cost(raw)

        if cost is None:
            skipped_no_parse += 1
            continue

        row["cost_per_week"] = str(int(cost)) if cost == int(cost) else str(cost)
        filled += 1
        if needs_review:
            flagged += 1
            existing_notes = (row.get("cost_notes") or "").strip()
            review_note = "cost_per_week auto-parsed — verify"
            if existing_notes:
                row["cost_notes"] = f"{existing_notes}; {review_note}"
            else:
                row["cost_notes"] = review_note

    print(f"cost_per_week parsed:   {filled}")
    print(f"  of which flagged for review: {flagged}")
    print(f"already had value:       {skipped_existing}")
    print(f"unparseable / ambiguous: {skipped_no_parse}")

    with PROGRAMS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Next step: python scripts/build_data_js.py")


if __name__ == "__main__":
    main()

"""
Infer org_type for organizations from org_name keywords.

Fills blank org_type fields only — never overwrites existing values.
Allowed values: nonprofit, municipal, school, private, university, faith-based

Run from the project root:
    python scripts/infer_org_types.py
"""

import csv
import re
from pathlib import Path

ORGS_PATH = Path("data/organizations.csv")

RULES = [
    ("school", [
        r"school district", r"\bsd\b", r"supervisory union", r"\bsu\b",
        r"elementary", r"middle school", r"high school", r"academy",
        r"montessori", r"waldorf", r"charter school",
    ]),
    ("university", [
        r"university", r"college", r"\buvm\b", r"champlain college",
        r"middlebury", r"norwich", r"vermont state",
    ]),
    ("municipal", [
        r"city of ", r"town of ", r"parks? [&and]+ rec", r"recreation dept",
        r"recreation department", r"recreation area", r"rec center",
        r"recreation center", r"department of parks", r"municipal",
        r"public works", r"leisure services",
    ]),
    ("nonprofit", [
        r"boys [&and]+ girls club", r"\bymca\b", r"\bywca\b", r"\bthe y\b",
        r"community center", r"foundation", r"\bassociation\b", r"\bsociety\b",
        r"audubon", r"humane society", r"united way", r"habitat for",
        r"volunteers of america", r"big brothers", r"4-h", r"scouts",
        r"girl scouts", r"boy scouts", r"community farm", r"community land",
        r"community action", r"community health",
    ]),
    ("faith-based", [
        r"church", r"catholic", r"christian", r"baptist", r"methodist",
        r"episcopal", r"jewish", r"jewish community", r"temple", r"synagogue",
        r"diocese", r"parish", r"quaker", r"unitarian", r"lutheran",
        r"presbyterian", r"congregation",
    ]),
]


def infer_type(org_name: str) -> str:
    name_lower = org_name.lower()
    for org_type, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, name_lower):
                return org_type
    return "private"


def main():
    with ORGS_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filled = 0
    skipped = 0

    for row in rows:
        if row.get("org_type", "").strip():
            skipped += 1
            continue
        inferred = infer_type(row["org_name"])
        row["org_type"] = inferred
        filled += 1

    print(f"org_type inferred: {filled}")
    print(f"org_type already set (skipped): {skipped}")

    # Show distribution
    from collections import Counter
    dist = Counter(r["org_type"] for r in rows)
    for k, v in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    with ORGS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Next step: python scripts/build_data_js.py")


if __name__ == "__main__":
    main()

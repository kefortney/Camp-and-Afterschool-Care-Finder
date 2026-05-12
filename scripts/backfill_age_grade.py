"""
Backfill grades_min/grades_max from age_min/age_max (and vice versa) in programs.csv.

Uses data/camp/age_to_grade.csv as the lookup table.
Only fills in blank values; never overwrites existing data.

Run from project root:
  python scripts/backfill_age_grade.py
"""

import csv
from pathlib import Path

PROGRAMS_PATH = Path("data/programs.csv")
AGE_GRADE_PATH = Path("data/camp/age_to_grade.csv")

with AGE_GRADE_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    mapping_rows = list(csv.DictReader(file))

start_age_to_grade = {}
end_age_to_grade = {}
grade_to_start_age = {}
grade_to_end_age = {}

for row in mapping_rows:
    start_age = (row.get("Start Age") or "").strip()
    end_age = (row.get("End Age") or "").strip()
    grade = (row.get("Grade") or "").strip().upper()

    if start_age and grade:
        start_age_to_grade[start_age] = grade
        grade_to_start_age[grade] = start_age
    if end_age and grade:
        end_age_to_grade[end_age] = grade
        grade_to_end_age[grade] = end_age

with PROGRAMS_PATH.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    fieldnames = reader.fieldnames
    rows = list(reader)

changes = {
    "grades_min_from_age_min": 0,
    "grades_max_from_age_max": 0,
    "age_min_from_grades_min": 0,
    "age_max_from_grades_max": 0,
}

for row in rows:
    age_min   = (row.get("age_min") or "").strip()
    age_max   = (row.get("age_max") or "").strip()
    grade_min = (row.get("grades_min") or "").strip()
    grade_max = (row.get("grades_max") or "").strip()

    if not grade_min and age_min in start_age_to_grade:
        row["grades_min"] = start_age_to_grade[age_min]
        grade_min = row["grades_min"]
        changes["grades_min_from_age_min"] += 1

    if not grade_max and age_max in end_age_to_grade:
        row["grades_max"] = end_age_to_grade[age_max]
        grade_max = row["grades_max"]
        changes["grades_max_from_age_max"] += 1

    if not age_min and grade_min.upper() in grade_to_start_age:
        row["age_min"] = grade_to_start_age[grade_min.upper()]
        changes["age_min_from_grades_min"] += 1

    if not age_max and grade_max.upper() in grade_to_end_age:
        row["age_max"] = grade_to_end_age[grade_max.upper()]
        changes["age_max_from_grades_max"] += 1

with PROGRAMS_PATH.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Updated rows with mapping-based backfill:")
for key, value in changes.items():
    print(f"  {key}: {value}")
print("Total fill operations:", sum(changes.values()))
print("Rows processed:", len(rows))
print("Next step: python scripts/build_data_js.py")

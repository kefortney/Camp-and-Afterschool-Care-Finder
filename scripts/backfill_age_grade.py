import csv
from pathlib import Path

camp_path = Path("data/2026 Summer Camp.csv")
map_path = Path("data/Age to Grade.csv")

with map_path.open("r", encoding="utf-8-sig", newline="") as file:
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

with camp_path.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    fieldnames = reader.fieldnames
    rows = list(reader)

changes = {
    "start_grade_from_start_age": 0,
    "end_grade_from_end_age": 0,
    "start_age_from_start_grade": 0,
    "end_age_from_end_grade": 0,
}

for row in rows:
    start_age = (row.get("Start Age") or "").strip()
    end_age = (row.get("End Age") or "").strip()
    start_grade = (row.get("Start Grade") or "").strip()
    end_grade = (row.get("End Grade") or "").strip()

    if not start_grade and start_age in start_age_to_grade:
        row["Start Grade"] = start_age_to_grade[start_age]
        start_grade = row["Start Grade"]
        changes["start_grade_from_start_age"] += 1

    if not end_grade and end_age in end_age_to_grade:
        row["End Grade"] = end_age_to_grade[end_age]
        end_grade = row["End Grade"]
        changes["end_grade_from_end_age"] += 1

    normalized_start_grade = start_grade.upper()
    if not start_age and normalized_start_grade in grade_to_start_age:
        row["Start Age"] = grade_to_start_age[normalized_start_grade]
        start_age = row["Start Age"]
        changes["start_age_from_start_grade"] += 1

    normalized_end_grade = end_grade.upper()
    if not end_age and normalized_end_grade in grade_to_end_age:
        row["End Age"] = grade_to_end_age[normalized_end_grade]
        end_age = row["End Age"]
        changes["end_age_from_end_grade"] += 1

with camp_path.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Updated rows with mapping-based backfill:")
for key, value in changes.items():
    print(f"  {key}: {value}")
print("Total fill operations:", sum(changes.values()))
print("Rows processed:", len(rows))

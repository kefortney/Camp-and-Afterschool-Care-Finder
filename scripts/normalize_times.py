import csv
import re
from pathlib import Path

CAMP_PATH = Path("data/2026 Summer Camp.csv")

TIME_RE = re.compile(r"^\s*(\d{1,3})\s*:\s*(\d{2})\s*([AaPp][Mm])?\s*$")


def coerce_hour(hour: int) -> int:
    if hour >= 100:
        reduced = hour // 100
        if 0 <= reduced <= 23:
            return reduced
    return hour


def to_12_hour(hour24: int):
    if hour24 == 0:
        return 12, "AM"
    if 1 <= hour24 < 12:
        return hour24, "AM"
    if hour24 == 12:
        return 12, "PM"
    if 13 <= hour24 <= 23:
        return hour24 - 12, "PM"
    return None, None


def normalize_start_time(value: str):
    raw = (value or "").strip()
    if not raw:
        return raw

    match = TIME_RE.match(raw)
    if not match:
        return raw

    hour = coerce_hour(int(match.group(1)))
    minute = int(match.group(2))
    if minute > 59:
        return raw

    # Force Start Time to AM as requested.
    if 0 <= hour <= 23:
        hour12, _ = to_12_hour(hour)
    elif 1 <= hour <= 12:
        hour12 = hour
    else:
        return raw

    if hour12 is None:
        return raw

    return f"{hour12:02d}:{minute:02d} AM"


def normalize_end_time(value: str):
    raw = (value or "").strip()
    if not raw:
        return raw

    match = TIME_RE.match(raw)
    if not match:
        return raw

    hour = coerce_hour(int(match.group(1)))
    minute = int(match.group(2))
    meridiem = match.group(3)

    if minute > 59:
        return raw

    if meridiem:
        meridiem = meridiem.upper()
        if hour == 0:
            hour12 = 12
        elif 1 <= hour <= 12:
            hour12 = hour
        elif 13 <= hour <= 23:
            hour12, meridiem = to_12_hour(hour)
        else:
            return raw
        return f"{hour12:02d}:{minute:02d} {meridiem}"

    # No AM/PM provided: infer and normalize.
    if 0 <= hour <= 23:
        if 0 <= hour <= 23 and hour >= 13:
            hour12, inferred = to_12_hour(hour)
            return f"{hour12:02d}:{minute:02d} {inferred}"
        if hour == 0:
            return f"12:{minute:02d} AM"
        if hour == 12:
            return f"12:{minute:02d} PM"
        # Day-camp end times are typically afternoon if AM/PM missing.
        return f"{hour:02d}:{minute:02d} PM"

    if 1 <= hour <= 12:
        if hour == 12:
            return f"12:{minute:02d} PM"
        return f"{hour:02d}:{minute:02d} PM"

    return raw


def main():
    with CAMP_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    start_changed = 0
    end_changed = 0

    for row in rows:
        old_start = (row.get("Start Time") or "")
        old_end = (row.get("End Time") or "")

        new_start = normalize_start_time(old_start)
        new_end = normalize_end_time(old_end)

        if new_start != old_start:
            row["Start Time"] = new_start
            start_changed += 1
        if new_end != old_end:
            row["End Time"] = new_end
            end_changed += 1

    with CAMP_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Start Time updated:", start_changed)
    print("End Time updated:", end_changed)
    print("Rows processed:", len(rows))


if __name__ == "__main__":
    main()

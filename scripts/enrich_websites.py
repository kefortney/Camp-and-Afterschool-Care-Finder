#!/usr/bin/env python3
"""Enrich `website` in data/organizations.csv from two source-of-truth CSVs.

Sources, in priority order (first non-empty wins per org_id):
  1. data/programs.csv — `registration_url` of programs whose `org_id` matches.
     When several programs share an org_id, the most common URL wins (ties broken by
     first occurrence).
  2. data/potential_vt_organizations_full.csv — `website` matched by `org_id`, with a
     normalized-name fallback for rows that don't carry an org_id.

Only rows with a non-empty source URL contribute. By default we ONLY fill blank `website`
cells in organizations.csv; pass --overwrite to replace existing values. Use --dry-run to
preview without writing.

Run from project root:
    python scripts/enrich_websites.py [--overwrite] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POTENTIAL_CSV = PROJECT_ROOT / "data" / "potential_vt_organizations_full.csv"
PROGRAMS_CSV = PROJECT_ROOT / "data" / "programs.csv"
ORGS_CSV = PROJECT_ROOT / "data" / "organizations.csv"


def normalize(name: str) -> str:
    return " ".join(name.strip().lower().split())


def load_programs() -> dict[str, str]:
    """Return {org_id: registration_url} from data/programs.csv.

    Multiple programs can share an org_id with differing URLs; we pick the most common
    URL per org (ties broken by first occurrence), which is the most representative
    "registration" link for that organization.
    """
    by_org_id: dict[str, Counter] = defaultdict(Counter)
    with PROGRAMS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            org_id = (row.get("org_id") or "").strip()
            url = (row.get("registration_url") or "").strip()
            if org_id and url:
                by_org_id[org_id][url] += 1
    return {org_id: counter.most_common(1)[0][0] for org_id, counter in by_org_id.items()}


def load_potential() -> tuple[dict[str, str], dict[str, str], list[tuple[str, str, str]]]:
    """Return (by_org_id, by_name, collisions).

    `collisions` records cases where two potential rows point at the same org_id with
    different website values — first non-empty wins, but we surface them for review.
    """
    by_org_id: dict[str, str] = {}
    by_name: dict[str, str] = {}
    collisions: list[tuple[str, str, str]] = []

    with POTENTIAL_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            website = (row.get("website") or "").strip()
            if not website:
                continue
            org_id = (row.get("org_id") or "").strip()
            name = (row.get("organization_name") or "").strip()

            if org_id:
                existing = by_org_id.get(org_id)
                if existing is None:
                    by_org_id[org_id] = website
                elif existing != website:
                    collisions.append((org_id, existing, website))

            if name:
                key = normalize(name)
                by_name.setdefault(key, website)

    return by_org_id, by_name, collisions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing website values (default: only fill blank cells).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed changes without writing organizations.csv.",
    )
    args = parser.parse_args()

    programs_by_org_id = load_programs()
    potential_by_org_id, potential_by_name, collisions = load_potential()

    with ORGS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise SystemExit("organizations.csv appears to be empty (no header).")
        rows = list(reader)

    filled = 0
    overwritten = 0
    skipped_already_filled = 0
    unmatched: list[str] = []

    for row in rows:
        existing = (row.get("website") or "").strip()
        org_id = (row.get("org_id") or "").strip()
        name = (row.get("org_name") or "").strip()

        website = None
        match_via = ""
        if org_id and org_id in programs_by_org_id:
            website = programs_by_org_id[org_id]
            match_via = "programs"
        elif org_id and org_id in potential_by_org_id:
            website = potential_by_org_id[org_id]
            match_via = "potential:org_id"
        elif name:
            website = potential_by_name.get(normalize(name))
            if website:
                match_via = "potential:name"

        if not website:
            unmatched.append(org_id or name or "<unknown>")
            continue

        if existing and not args.overwrite:
            skipped_already_filled += 1
            continue

        if existing and existing != website:
            print(f"  ~ [{match_via}] {org_id or name}: {existing}  ->  {website}")
            row["website"] = website
            overwritten += 1
        elif not existing:
            print(f"  + [{match_via}] {org_id or name}: {website}")
            row["website"] = website
            filled += 1

    if collisions:
        print()
        print("Collisions in potential CSV (multiple websites for same org_id; first wins):")
        for org_id, kept, other in collisions:
            print(f"  ! {org_id}: kept {kept}, dropped {other}")

    if not args.dry_run:
        with ORGS_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print()
    print(f"Filled blanks:        {filled}")
    print(f"Overwritten:          {overwritten}")
    print(f"Skipped (had value):  {skipped_already_filled}")
    print(f"No match in source:   {len(unmatched)}")
    if args.dry_run:
        print("(dry-run — organizations.csv was not modified)")


if __name__ == "__main__":
    main()

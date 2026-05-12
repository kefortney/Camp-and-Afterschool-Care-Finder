"""
Infer site_county for programs and fill missing org city/county.

Steps:
  1. Load town→county map from data/Vermont_Town_GEOID_RPC_County.geojson
  2. For programs with blank site_city, copy city from their org record
  3. For all programs, fill site_county from town→county map using site_city
  4. For orgs with blank city or county, backfill from their programs' site data

Run from the project root:
    python scripts/infer_counties.py

IMPORTANT: site_city values must match town names in the GeoJSON exactly.
See data/Vermont_Town_GEOID_RPC_County.geojson for the canonical list.
"""

import csv
import json
from pathlib import Path
from collections import Counter

PROGRAMS_PATH = Path("data/programs.csv")
ORGS_PATH = Path("data/organizations.csv")
GEOJSON_PATH = Path("data/Vermont_Town_GEOID_RPC_County.geojson")

# Additional aliases for common alternate spellings not in the GeoJSON
CITY_ALIASES = {
    "St. Albans": "Saint Albans City",
    "Saint Albans": "Saint Albans City",
    "Barre": "Barre City",
    "Hyde Park": "Hyde Park",  # Lamoille County
}


def load_town_county_map():
    with GEOJSON_PATH.open(encoding="utf-8") as f:
        gj = json.load(f)
    mapping = {}
    for feat in gj["features"]:
        props = feat["properties"]
        town = (props.get("TOWNNAMEMC") or props.get("Municipal_Name") or "").strip()
        county = (props.get("County") or "").strip()
        if town and county:
            mapping[town] = county
    # Add aliases
    for alias, canonical in CITY_ALIASES.items():
        if canonical in mapping:
            mapping[alias] = mapping[canonical]
    return mapping


def main():
    town_county = load_town_county_map()

    # Load orgs
    with ORGS_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        o_fieldnames = reader.fieldnames
        o_rows = list(reader)
    org_by_id = {r["org_id"]: r for r in o_rows}

    # Load programs
    with PROGRAMS_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        p_fieldnames = reader.fieldnames
        p_rows = list(reader)

    city_filled = 0
    county_filled = 0
    city_no_match = set()

    for row in p_rows:
        # Step 2: fill blank site_city from org city
        if not row["site_city"].strip():
            org = org_by_id.get(row["org_id"])
            if org and org.get("city", "").strip():
                row["site_city"] = org["city"].strip()
                city_filled += 1

        # Step 3: fill site_county from town→county map
        city = row["site_city"].strip()
        if city and not row["site_county"].strip():
            county = town_county.get(city)
            if county:
                row["site_county"] = county
                county_filled += 1
            else:
                city_no_match.add(city)

    print(f"site_city filled from org:   {city_filled}")
    print(f"site_county filled from map: {county_filled}")
    if city_no_match:
        print(f"Cities with no county match: {sorted(city_no_match)}")

    with PROGRAMS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=p_fieldnames)
        writer.writeheader()
        writer.writerows(p_rows)

    # Step 4: backfill org city/county from their programs
    org_cities = {}
    org_counties = {}
    for row in p_rows:
        oid = row["org_id"]
        city = row["site_city"].strip()
        county = row["site_county"].strip()
        if city:
            org_cities.setdefault(oid, Counter())[city] += 1
        if county:
            org_counties.setdefault(oid, Counter())[county] += 1

    org_city_filled = 0
    org_county_filled = 0
    for row in o_rows:
        oid = row["org_id"]
        if not row["city"].strip() and oid in org_cities:
            row["city"] = org_cities[oid].most_common(1)[0][0]
            org_city_filled += 1
        if not row["county"].strip() and oid in org_counties:
            row["county"] = org_counties[oid].most_common(1)[0][0]
            org_county_filled += 1

    print(f"Org city filled from programs:   {org_city_filled}")
    print(f"Org county filled from programs: {org_county_filled}")

    with ORGS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=o_fieldnames)
        writer.writeheader()
        writer.writerows(o_rows)

    print("Next step: python scripts/build_data_js.py")


if __name__ == "__main__":
    main()

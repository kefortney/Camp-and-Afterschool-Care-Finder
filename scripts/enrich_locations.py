import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

CAMP_PATH = Path("data/2026 Summer Camp.csv")

USER_AGENT = "CampFinderAddressEnricher/1.0 (local use)"
REQUEST_DELAY_SECONDS = 0.7

STREET_HINT_RE = re.compile(
    r"\b(st|street|rd|road|ave|avenue|ln|lane|dr|drive|ct|court|blvd|way|pkwy|parkway|pl|place|cir|circle|ter|terrace|hwy|highway|route|rt)\b",
    re.I,
)


def looks_street_address(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return bool(re.search(r"\d", text)) and bool(STREET_HINT_RE.search(text))


def location_has_city_or_state(location: str, city: str) -> bool:
    text = (location or "").lower()
    city_l = (city or "").strip().lower()
    if city_l and city_l in text:
        return True
    return " vt" in text or "vermont" in text


def normalize_city(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def fetch_nominatim(query: str):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 3,
            "countrycodes": "us",
        }
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def build_full_address(item):
    address = item.get("address", {})
    house_number = (address.get("house_number") or "").strip()
    road = (address.get("road") or "").strip()
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("municipality")
        or ""
    ).strip()
    state = (address.get("state") or "").strip()
    postcode = (address.get("postcode") or "").strip()

    if not city:
        return None
    if state.lower() != "vermont":
        return None

    line1 = f"{house_number} {road}".strip()
    if not line1:
        return None
    line2 = f"{city}, VT"
    if postcode:
        line2 += f" {postcode}"
    return f"{line1}, {line2}"


def city_matches(item, expected_city: str) -> bool:
    if not expected_city:
        return True
    address = item.get("address", {})
    found_city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("municipality")
        or ""
    )
    if found_city and normalize_city(found_city) == normalize_city(expected_city):
        return True
    display_name = (item.get("display_name") or "").lower()
    return normalize_city(expected_city) in display_name


def choose_result(results, expected_city: str):
    fallback = None
    for item in results:
        addr = item.get("address", {})
        if (addr.get("country_code") or "").lower() != "us":
            continue
        if not city_matches(item, expected_city):
            continue

        state = (addr.get("state") or "").strip().lower()
        if state != "vermont":
            continue

        full_address = build_full_address(item)
        if full_address:
            return full_address
        if not fallback:
            display = (item.get("display_name") or "").strip()
            if display:
                fallback = display
    return fallback


def enrich_row(row):
    location = (row.get("Location") or "").strip()
    city = (row.get("City") or "").strip()
    org = (row.get("Organization") or "").strip()

    if looks_street_address(location):
        return None

    queries = []

    if location and city:
        queries.append(f"{location}, {city}, Vermont")
    if org and city:
        queries.append(f"{org}, {city}, Vermont")
    if location and org and city:
        queries.append(f"{org} {location}, {city}, Vermont")

    seen = set()
    deduped_queries = []
    for query in queries:
        key = query.lower()
        if key not in seen:
            deduped_queries.append(query)
            seen.add(key)

    for query in deduped_queries:
        try:
            results = fetch_nominatim(query)
        except Exception:
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        full_address = choose_result(results, city)
        time.sleep(REQUEST_DELAY_SECONDS)
        if full_address:
            return full_address

    return None


def main():
    with CAMP_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    checked = 0
    updated = 0
    standardized_existing = 0

    for row in rows:
        location = (row.get("Location") or "").strip()
        city = (row.get("City") or "").strip()
        org = (row.get("Organization") or "").strip()

        if looks_street_address(location):
            if city and not location_has_city_or_state(location, city):
                row["Location"] = f"{location}, {city}, VT"
                standardized_existing += 1
            continue
        if not city or (not location and not org):
            continue

        checked += 1
        full_address = enrich_row(row)
        if full_address:
            row["Location"] = full_address
            updated += 1

    with CAMP_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Rows considered:", checked)
    print("Locations updated:", updated)
    print("Street rows standardized:", standardized_existing)
    print("Rows total:", len(rows))


if __name__ == "__main__":
    main()

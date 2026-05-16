"""
Verify each organization's website actually contains camp-related content.

Reads data/organizations.csv. For every row with a `website` value, fetches
the page and looks for camp / afterschool / youth-program keywords. Rows that
verify get their `confidence` upgraded from `likely` to `confirmed`. Rows that
fail verification keep their existing `confidence` (we never downgrade rows
that were already marked `confirmed` manually with phone/email/address data).

Progress is saved every 10 rows so a Ctrl-C doesn't lose work.

Run from the project root:
    python3 scripts/verify_camp_websites.py
"""

import csv
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ORGS_PATH = Path("data/organizations.csv")

USER_AGENT = "CampFinderVerifier/1.0 (local research tool)"
REQUEST_DELAY = 2.0  # seconds between requests, per user instruction
TIMEOUT = 20  # seconds per request
SAVE_EVERY = 10

# Match whole words so e.g. "camping" matches but "scamp" or "decamp" don't get
# false-positive credit from a regex like r"camp". Word boundaries handle that.
CAMP_KEYWORDS = [
    r"\bcamp\b",
    r"\bcamps\b",
    r"\bsummer camp\b",
    r"\bday camp\b",
    r"\bafter[- ]?school\b",
    r"\byouth program",
    r"\bkids program",
    r"\bchildren'?s program",
    r"\byouth camp",
    r"\bsummer program",
    r"\bsleepaway\b",
    r"\bovernight camp\b",
]
CAMP_RE = re.compile("|".join(CAMP_KEYWORDS), re.IGNORECASE)


class TextExtractor(HTMLParser):
    """Strip tags + skip script/style; collect visible text."""

    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        # Also capture meta description content, since some sites bury the
        # word "camp" in meta rather than visible text.
        if tag == "meta":
            attr = dict(attrs)
            if attr.get("name", "").lower() == "description" or \
               attr.get("property", "").lower() == "og:description":
                content = attr.get("content", "")
                if content:
                    self.parts.append(content)
        if tag == "title":
            # title text comes through handle_data; nothing to do here
            pass

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


def fetch_page_text(url: str) -> tuple[str, str]:
    """Fetch a URL and return (visible_text, error). On success error is ''."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower() and "xml" not in content_type.lower():
                return "", f"non-html content-type: {content_type}"
            raw = resp.read(500_000)  # cap at ~500 KB
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return "", f"{type(e).__name__}: {e}"

    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        html = raw.decode("latin-1", errors="replace")

    parser = TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        # parser errors still leave us with whatever we collected so far
        pass

    return parser.text(), ""


def is_camp_related(text: str) -> bool:
    return bool(CAMP_RE.search(text))


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    with ORGS_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise SystemExit("organizations.csv appears to be empty.")
        rows = list(reader)

    targets = [
        i for i, r in enumerate(rows)
        if (r.get("website") or "").strip()
    ]

    with_no_website = len(rows) - len(targets)
    print(f"Rows total:              {len(rows)}")
    print(f"Rows with website:       {len(targets)}")
    print(f"Rows without website:    {with_no_website}  (left untouched)")
    print(f"Delay between fetches:   {REQUEST_DELAY}s")
    print()

    upgraded = 0          # likely -> confirmed
    kept_confirmed = 0    # already confirmed, verified again
    stayed_likely = 0     # likely, did not verify
    fetch_errors = 0      # could not fetch at all
    already_confirmed_failed = 0  # confirmed row whose site didn't match (left as confirmed)

    for n, idx in enumerate(targets, 1):
        row = rows[idx]
        url = (row.get("website") or "").strip().split()[0]
        org = (row.get("org_name") or row.get("org_id") or "")[:48]
        current = (row.get("confidence") or "").strip()

        prefix = f"[{n:3d}/{len(targets)}] {org:<48}  {url[:60]:<60}"
        print(prefix, end="  ", flush=True)

        text, err = fetch_page_text(url)

        if err:
            fetch_errors += 1
            if current == "likely":
                stayed_likely += 1
            print(f"FETCH ERROR: {err}")
        else:
            matched = is_camp_related(text)
            if matched:
                if current != "confirmed":
                    rows[idx]["confidence"] = "confirmed"
                    upgraded += 1
                    print("camp-related -> CONFIRMED")
                else:
                    kept_confirmed += 1
                    print("camp-related (already confirmed)")
            else:
                if current == "confirmed":
                    already_confirmed_failed += 1
                    print("no camp keywords (kept confirmed — manually verified)")
                else:
                    stayed_likely += 1
                    print("no camp keywords (stays likely)")

        # Save progress periodically
        if n % SAVE_EVERY == 0:
            _write_csv(ORGS_PATH, fieldnames, rows)
            print(f"  -- progress saved ({upgraded} upgraded so far) --")

        # 2-second delay between requests; skip after final row
        if n < len(targets):
            time.sleep(REQUEST_DELAY)

    _write_csv(ORGS_PATH, fieldnames, rows)

    print()
    print(f"Upgraded likely -> confirmed:     {upgraded}")
    print(f"Already confirmed, re-verified:   {kept_confirmed}")
    print(f"Stayed likely (no match / error): {stayed_likely}")
    print(f"Confirmed rows w/ no match (left as confirmed): {already_confirmed_failed}")
    print(f"Fetch errors total:               {fetch_errors}")


if __name__ == "__main__":
    main()

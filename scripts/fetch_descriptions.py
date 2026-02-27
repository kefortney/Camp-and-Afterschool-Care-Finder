"""
Fetch missing Camp Description values from each camp's website.

Reads data/2026 Summer Camp.csv, fills in blank Camp Description fields
by fetching the webpage and extracting the best available description text,
then writes the updated CSV back in place.

Run from the project root:
    python3 scripts/fetch_descriptions.py

Only rows with a Webpage URL and a blank Camp Description are processed.
Existing descriptions are never overwritten.
"""

import csv
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

CAMP_PATH = Path("data/2026 Summer Camp.csv")

USER_AGENT = "CampFinderDescriptionFetcher/1.0 (local research tool)"
REQUEST_DELAY = 0.8   # seconds between requests
TIMEOUT       = 15    # seconds per request
MIN_DESC_LEN  = 40    # ignore descriptions shorter than this
MAX_DESC_LEN  = 500   # truncate descriptions longer than this


# ── HTML parser ───────────────────────────────────────────────────────────────

class MetaDescParser(HTMLParser):
    """Extracts meta description / og:description and first body paragraphs."""

    def __init__(self):
        super().__init__()
        self.og_desc    = ""
        self.meta_desc  = ""
        self._in_body   = False
        self._in_p      = False
        self._p_texts   = []
        self._cur_p     = []
        self._skip_tags = set()
        self._depth     = 0
        self._skip_depth = None

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)

        if tag == "body":
            self._in_body = True

        # Skip script/style content
        if tag in ("script", "style", "noscript", "nav", "footer", "header"):
            if self._skip_depth is None:
                self._skip_depth = self._depth
            self._skip_tags.add(tag)

        self._depth += 1

        if self._skip_depth is not None:
            return

        # <meta name="description" …>
        if tag == "meta":
            name    = attr_dict.get("name", "").lower()
            prop    = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "").strip()
            if not content:
                return
            if prop == "og:description" and not self.og_desc:
                self.og_desc = content
            elif name == "description" and not self.meta_desc:
                self.meta_desc = content

        if self._in_body and tag == "p":
            self._in_p = True
            self._cur_p = []

    def handle_endtag(self, tag):
        self._depth -= 1

        if self._skip_depth is not None and self._depth < self._skip_depth:
            self._skip_depth = None

        if tag in ("script", "style", "noscript", "nav", "footer", "header"):
            self._skip_tags.discard(tag)

        if self._in_p and tag == "p":
            text = " ".join(self._cur_p).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) >= MIN_DESC_LEN:
                self._p_texts.append(text)
            self._in_p = False
            self._cur_p = []

    def handle_data(self, data):
        if self._skip_depth is not None:
            return
        if self._in_p:
            self._cur_p.append(data.strip())

    def best_description(self) -> str:
        for candidate in [self.og_desc, self.meta_desc] + self._p_texts:
            text = candidate.strip()
            if len(text) >= MIN_DESC_LEN:
                # Trim to max length at a sentence boundary if possible
                if len(text) > MAX_DESC_LEN:
                    truncated = text[:MAX_DESC_LEN]
                    last_period = truncated.rfind(".")
                    if last_period > MIN_DESC_LEN:
                        truncated = truncated[:last_period + 1]
                    text = truncated.strip()
                return text
        return ""


# ── fetcher ───────────────────────────────────────────────────────────────────

def fetch_description(url: str) -> str:
    """Fetch a URL and return the best description string, or '' on failure."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            # Only process HTML responses
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                return ""
            raw = resp.read(200_000)  # cap at ~200 KB
    except (urllib.error.URLError, OSError, ValueError):
        return ""

    # Decode — try UTF-8 then latin-1 fallback
    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        html = raw.decode("latin-1", errors="replace")

    parser = MetaDescParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    return parser.best_description()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    with CAMP_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Identify rows that need a description
    targets = [
        i for i, r in enumerate(rows)
        if not (r.get("Camp Description") or "").strip()
        and (r.get("Webpage") or "").strip()
    ]

    print(f"Rows total:          {len(rows)}")
    print(f"Already have desc:   {sum(1 for r in rows if (r.get('Camp Description') or '').strip())}")
    print(f"Will attempt to fetch: {len(targets)}")
    print()

    updated = 0
    failed  = 0

    for n, idx in enumerate(targets, 1):
        row = rows[idx]
        url = (row.get("Webpage") or "").strip().split()[0]  # take first URL if multiple
        org = (row.get("Organization") or "").strip()

        print(f"[{n}/{len(targets)}] {org[:50]:<50}  {url[:60]}", end="  ", flush=True)

        desc = fetch_description(url)
        time.sleep(REQUEST_DELAY)

        if desc:
            rows[idx]["Camp Description"] = desc
            updated += 1
            print(f"✓  ({len(desc)} chars)")
        else:
            failed += 1
            print("✗  (no description found)")

        # Save progress every 25 rows so a Ctrl-C doesn't lose everything
        if n % 25 == 0:
            _write_csv(CAMP_PATH, fieldnames, rows)
            print(f"  ── progress saved ({updated} updated so far) ──")

    # Final save
    _write_csv(CAMP_PATH, fieldnames, rows)

    print()
    print(f"Done.  Updated: {updated}  |  No description found: {failed}")
    print(f"Re-run   python3 scripts/csv_to_data_js.py   to rebuild data.js")


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()

"""
Infer activity tags for programs from description and program_name keywords.

Fills blank activities fields only — never overwrites existing values.
Uses the canonical tag list from validate_data.py.

Run from the project root:
    python scripts/infer_activities.py
"""

import csv
import re
from pathlib import Path

PROGRAMS_PATH = Path("data/programs.csv")

# Canonical tag -> keyword patterns (matched against description + program_name, case-insensitive)
TAG_PATTERNS = {
    "STEM": [
        r"\bstem\b", r"science[,\s]+technology", r"technology[,\s]+engineering",
    ],
    "Coding": [
        r"\bcoding\b", r"\bcode\b", r"\bprogramming\b", r"computer science",
        r"\bsoftware\b", r"web dev", r"scratch\b", r"\bpython\b", r"\bjava\b",
        r"minecraft", r"roblox",
    ],
    "Robotics": [
        r"\brobot", r"lego mindstorms", r"\bvex\b", r"first robotics",
    ],
    "Science": [
        r"\bscience\b", r"\bbiology\b", r"\bchemistry\b", r"\bphysics\b",
        r"\becology\b", r"\bastronomy\b", r"\bgeology\b", r"lab\b",
        r"experiment", r"specimen", r"dissect",
    ],
    "Math": [
        r"\bmath\b", r"\bmathematics\b", r"\balgebra\b", r"\bgeometry\b",
        r"numeracy", r"chess",
    ],
    "Arts": [
        r"\bart\b", r"\barts\b", r"\bcrafts?\b", r"\bdrawing\b", r"\bpainting\b",
        r"\bpottery\b", r"\bceramics\b", r"visual art", r"\bsculpture\b",
        r"\bprintmaking\b", r"\bsketch", r"mixed media", r"\bwatercolor\b",
        r"\bsewing\b", r"\btextile\b",
    ],
    "Music": [
        r"\bmusic\b", r"\bband\b", r"\borchestra\b", r"\bchoir\b", r"\bchorus\b",
        r"\bguitar\b", r"\bpiano\b", r"\bviolin\b", r"\bdrums?\b",
        r"\bsinging\b", r"\bsong\b", r"\blyrics\b", r"\bcomposition\b",
    ],
    "Theater": [
        r"\btheater\b", r"\btheatre\b", r"\bdrama\b", r"\bacting\b",
        r"\bimprov\b", r"\bcomedy\b", r"\bstage\b", r"\bmusical\b",
        r"\bperformance\b", r"\bplay\b", r"\bskit\b", r"\bstand-?up\b",
    ],
    "Dance": [
        r"\bdance\b", r"\bdancing\b", r"\bballet\b", r"hip hop", r"jazz dance",
        r"\bchoreograph", r"\btap\b",
    ],
    "Sports": [
        r"\bsport\b", r"\bbasketball\b", r"\bsoccer\b", r"\bfootball\b",
        r"\bbaseball\b", r"\bsoftball\b", r"\bvolleyball\b", r"\blacrosse\b",
        r"\bhockey\b", r"\btennis\b", r"\bgolf\b", r"\bwrestl", r"\bgymnastics\b",
        r"\bcheerleading\b", r"\btrack\b", r"\bfield\b", r"\brugby\b",
        r"\bfitness\b", r"\bathletic\b", r"\bflag football\b", r"\bdisc golf\b",
        r"\bfrisbee\b", r"\bskate\b", r"\bskating\b", r"\bski\b",
    ],
    "Outdoor Education": [
        r"\boutdoor\b", r"\bwilderness\b", r"\badventure\b", r"\bexpedition\b",
        r"\bsurvival\b", r"forest school", r"\bcamping\b", r"\bbackpack",
        r"rock climb", r"rappel", r"zip ?line",
    ],
    "Nature": [
        r"\bnature\b", r"\bwildlife\b", r"\bconservation\b", r"\benvironment",
        r"\bbirds?\b", r"\bbotany\b", r"\bgarden\b", r"\bforest\b",
        r"\bfarm\b", r"\bagriculture\b", r"\banimals?\b", r"\bsustainab",
    ],
    "Swimming": [
        r"\bswim", r"\bpool\b", r"\baquatic\b", r"\bwaterfront\b",
        r"\bwater sports\b", r"\bdiving\b",
    ],
    "Hiking": [
        r"\bhiking\b", r"\bhike\b", r"\btrail\b", r"\bmountain\b",
        r"\bbackpack", r"\btrekking\b",
    ],
    "Horseback Riding": [
        r"\bhorse\b", r"\bequestrian\b", r"\briding\b", r"\bequine\b",
        r"\bstable\b", r"\bpony\b",
    ],
    "Cooking": [
        r"\bcooking\b", r"\bculinary\b", r"\bbaking\b", r"\bfood\b",
        r"\bchef\b", r"\bkitchen\b", r"\brecipe\b", r"\bbread\b",
    ],
    "Language": [
        r"\blanguage\b", r"\bspanish\b", r"\bfrench\b", r"sign language",
        r"\besl\b", r"foreign language", r"\bmandarin\b", r"\bimmersion\b",
    ],
    "Leadership": [
        r"\bleadership\b", r"\bleader\b", r"\bmentor\b", r"\bempowerment\b",
        r"\bteamwork\b", r"\bteam building\b",
    ],
    "Community Service": [
        r"community service", r"\bvolunteer\b", r"service learning",
        r"service project", r"give back",
    ],
    "Special Needs Support": [
        r"special needs", r"\bautism\b", r"\biep\b", r"\bdisabilit",
        r"\binclusive\b", r"\baccessib", r"\badaptive\b",
    ],
    "Academic Enrichment": [
        r"\btutoring\b", r"\bacademic\b", r"\bhomework\b", r"\breading\b",
        r"\bliteracy\b", r"\bwriting\b", r"\bsat\b", r"test prep",
        r"\bstudy\b", r"\bscholarship\b", r"enrichment",
    ],
    "Maker": [
        r"\bmaker\b", r"\bmakerspace\b", r"\bengineering\b", r"\bfabricat",
        r"3d print", r"\bwoodwork", r"\belectronics\b", r"\bcircuits?\b",
        r"\binvention\b", r"\bprototype\b", r"design and build",
    ],
    "Film & Media": [
        r"\bfilm\b", r"\bvideo\b", r"\bmedia\b", r"\bphotography\b",
        r"\bphoto\b", r"\banimation\b", r"\bfilmmaking\b", r"\bjournalism\b",
        r"\bpodcast\b", r"\bbroadcast\b", r"\byoutube\b",
    ],
}

# Compile all patterns
COMPILED = {
    tag: [re.compile(p, re.IGNORECASE) for p in patterns]
    for tag, patterns in TAG_PATTERNS.items()
}


def infer_tags(text: str) -> list:
    found = []
    for tag, patterns in COMPILED.items():
        for pat in patterns:
            if pat.search(text):
                found.append(tag)
                break
    return found


def main():
    with PROGRAMS_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filled = 0
    skipped_existing = 0
    skipped_no_text = 0

    for row in rows:
        if (row.get("activities") or "").strip():
            skipped_existing += 1
            continue

        # Build text corpus from name + description
        text = " ".join([
            row.get("program_name", ""),
            row.get("description", ""),
        ])

        tags = infer_tags(text)

        if tags:
            row["activities"] = ", ".join(tags)
            filled += 1
        else:
            skipped_no_text += 1

    print(f"activities inferred:   {filled}")
    print(f"already had activities: {skipped_existing}")
    print(f"no tags found:          {skipped_no_text}")

    with PROGRAMS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Next step: python scripts/build_data_js.py")


if __name__ == "__main__":
    main()

# Camp-and-Afterschool-Care-Finder

Local web view for `data/camp/summer_camp_2026.csv` is available in `index.html`.

## Run locally

From the project root:

```bash
python3 -m http.server 8000
```

Then open:

`http://localhost:8000`

## Live reload while editing

From the project root:

```bash
python scripts/dev_server.py
```

Then open:

`http://127.0.0.1:8000`

When files like `.html`, `.css`, `.js`, `.json`, or `.csv` change, the page reloads automatically.

## Features

- Click any column header to sort ascending/descending.
- Use the top search box to search across all columns.
- Use per-column filter inputs under each header to narrow results.

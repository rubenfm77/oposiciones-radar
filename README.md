# Oposiciones Radar

A tool for tracking Spanish public sector job openings (*oposiciones*) across the
three layers of Spanish administration — national (BOE), regional (Generalitat de
Catalunya), and local (Catalan municipalities) — filtered to a specific candidate
profile instead of requiring manual daily checks across a dozen disconnected sites.

🔗 **Live demo:** https://oposiciones-radar-dtecwtbkjjvlkvunvdepwn.streamlit.app/

## Why this exists

Public sector job postings in Spain are scattered across sources with no shared
format: a national open-data API (BOE), a regional government portal with no API,
and hundreds of municipalities each running their own website. Most people track
this manually, checking a handful of bookmarks every so often and hoping not to
miss a filing deadline. This app centralizes that check into one place, being
explicit about which sources are actually automated versus which are curated
shortcuts to the right manual search — rather than pretending a shaky scraper
covers ground it doesn't.

## What it does

**BOE (national)** — fully automated via the official open-data API. Pulls the
daily bulletin, filters to the "Oposiciones y concursos" section, and keyword-matches
titles against a configurable list of target corps. Also surfaces the full
unfiltered list per date range, since Spanish administrative titles aren't phrased
consistently enough for keyword matching alone to guarantee completeness.

**Generalitat de Catalunya (regional)** — links directly to the official
"Treballar a la Generalitat" hub, which lists open calls by corps and department.
The DOGC's own search engine is built for legal text retrieval, not job postings,
so it's not a good fit here even though it's the more obvious first guess.

**Ajuntaments (local)** — direct links for Barcelona and Terrassa, plus the CIDO
tool (built by Diputació de Barcelona but indexing selection processes across all
of Catalonia, including the Girona area via XALOC) for keyword and geographic-proximity
search across municipalities without needing a bespoke scraper per town.

## Tech stack

- Python, Streamlit
- BOE Open Data API (`boe.es/datosabiertos`) — no API key required
- Defensive JSON parsing: BOE's per-announcement structure isn't fully documented,
  so fields are normalized and malformed entries are skipped individually rather
  than crashing the page

## Local development
```bash
pip install streamlit requests --break-system-packages
streamlit run app.py
```

## Design tradeoffs worth knowing about

- Keyword matching is substring-based on announcement titles, not semantic — the
  unfiltered list exists precisely because that filter can miss relevant results
  phrased differently than expected.
- Large national convocatorias (GACE, CSTI...) are typically published once or
  twice a year, so a short date range legitimately returning few or no results
  isn't necessarily a bug.
- No background/scheduled checking yet — data is pulled on demand when the page
  is open, not pushed via alerts.
- Full scraping of all 300+ Barcelona-province and 200+ Girona-province
  municipalities was deliberately scoped out: no shared API or HTML structure
  exists across them, and building one-off scrapers per town doesn't hold up
  over time.

## Possible next steps

- Persist "already seen" results to avoid re-reviewing the same announcement.
- Scheduled checks (e.g. GitHub Actions) with email/Telegram alerts on new matches.

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

## Telegram alerts (BOE only)

A separate headless script (`boe_telegram_alert.py`) runs on a schedule via GitHub
Actions and sends a Telegram message for each **new** BOE match — no need to keep
the Streamlit app open. It tracks what's already been notified in `seen_ids.json`,
committed back to the repo after each run, so you're only pinged once per announcement.

**One-time setup:**
1. Create a bot: message `@BotFather` on Telegram → `/newbot` → follow the prompts →
   copy the token it gives you.
2. Get your chat ID: send your new bot any message, then open
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and read the
   `chat.id` field from the JSON response.
3. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository
   secret**, add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. That's it — `.github/workflows/boe_alert.yml` runs it automatically on weekdays.
   It can also be triggered manually from the **Actions** tab (`workflow_dispatch`) to test.

Scope note: only the BOE is covered here, since it's the only source with a
reliable API to poll unattended. The Generalitat and Ajuntaments tabs still rely
on visiting the linked portals directly — there's nothing stable enough to poll
automatically for those without a real API.



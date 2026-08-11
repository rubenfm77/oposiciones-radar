# Oposiciones Radar

Tracks Spanish public sector job openings (*oposiciones*) relevant to a specific
candidate profile, across the three administrative layers: national (BOE), regional
(Generalitat de Catalunya), and local (Barcelona-area municipalities).

🔗 **Live App:** https://oposiciones-radar-dtecwtbkjjvlkvunvdepwn.streamlit.app/

## What it actually does

| Source | Status | How |
|---|---|---|
| **BOE** (national) | ✅ Fully automated | Official open-data API, filtered to section "II.B — Oposiciones y concursos", keyword-matched against your target corps (GACE, CSTI, Seguridad Social, Gestión Procesal, Administradores Civiles...). Also shows the full unfiltered list so you can sanity-check the keyword matching yourself. |
| **Generalitat de Catalunya** | 🔗 Direct link | Links to the official "Treballar a la Generalitat > Oposicions" portal, which centralizes all open calls by corps/department — more useful than the DOGC's own legal-text search engine, which is built for regulations, not job postings. |
| **Ajuntaments** | 🔗 Direct links | Barcelona and Terrassa specifically, plus the Diputació de Barcelona's CIDO tool as a province-wide aggregator (real keyword search supported in the URL). Covering all 300+ Barcelona-province municipalities reliably isn't realistic — no shared API or format exists across them. |

## Run locally
```bash
pip install streamlit requests --break-system-packages
streamlit run app.py
```

## Deploy (Streamlit Cloud, same flow as the other projects)
1. Push this folder to a GitHub repo (e.g. `oposiciones-radar`).
2. Add a `requirements.txt`:
   ```
   streamlit
   requests
   ```
3. Connect the repo at https://share.streamlit.io and deploy — same pattern as
   `cycling-performance-ml` or `credit-risk-scoring-ml`.

## Known limitations (by design, not oversight)
- BOE parsing is defensive (try/except at multiple levels) since the exact JSON
  structure per announcement isn't fully documented — a malformed entry is skipped
  rather than crashing the whole page.
- Keyword matching is substring-based on the announcement title. The BOE doesn't
  always phrase a given corps the same way twice, so the app also exposes the
  full unfiltered list per date range — treat the keyword filter as a shortcut,
  not a guarantee of completeness.
- Large, relevant convocatorias (GACE, CSTI, etc.) are typically published once or
  twice a year, not weekly — seeing few or zero matches in a short date window is
  often expected, not a bug.
- No scheduled/background checking yet — you open the app and pull data on demand.

## Possible next steps
- Persist "already seen" results (local CSV, or `window.storage` if migrated to an
  artifact) to avoid re-reviewing the same announcement.
- Email/Telegram alerts on new matches — would require running the BOE-fetching
  logic headless on a schedule (e.g. GitHub Actions) instead of inside the
  Streamlit UI, which only runs when someone has the page open.
- Revisit whether a lightweight scraper for a handful of specific municipalities
  (beyond Barcelona/Terrassa) is worth the maintenance cost.

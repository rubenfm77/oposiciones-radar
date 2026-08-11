# Oposiciones Radar

🔗 **Live App:** https://oposiciones-radar-dtecwtbkjjvlkvunvdepwn.streamlit.app/

## Run locally
```bash
pip install streamlit requests --break-system-packages
streamlit run app.py
```

## Deploy (Streamlit Cloud, same as your other projects)
1. Push this folder to a new GitHub repo (e.g. `oposiciones-radar`).
2. Add a `requirements.txt` with:
   ```
   streamlit
   requests
   ```
3. Connect the repo at https://share.streamlit.io and deploy — same flow as
   `cycling-performance-ml` or `credit-risk-scoring-ml`.

## Honest scope of each tab
- **BOE**: fully automated via the official BOE open-data API. No API key needed.
  Parsing is defensive (try/except) in case the JSON structure shifts slightly, but
  if you ever see 0 results in a range where you expected some, it's worth checking.
- **DOGC**: no open public API like the BOE, so instead of a fragile scraper this tab
  gives you pre-filtered search links using your keywords.
- **Ajuntaments**: only Barcelona and Terrassa are wired up as direct links, plus the
  CIDO search tool from Diputació de Barcelona as a province-wide aggregator.

## Possible next steps
- Store seen results in `window.storage` (if migrated to an artifact) or a local CSV,
  to mark which ones you've already reviewed.
- Add email/Telegram alerts when a new match appears (would require running the
  script headless on a schedule, e.g. via GitHub Actions, instead of the Streamlit UI).

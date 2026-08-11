# Radar de Oposiciones

## Correrla en local
```bash
pip install streamlit requests --break-system-packages
streamlit run app.py
```

## Desplegarla (como tus otros proyectos, en Streamlit Cloud)
1. Sube esta carpeta a un repo nuevo en GitHub (ej. `oposiciones-radar`).
2. Añade un `requirements.txt` con:
   ```
   streamlit
   requests
   ```
3. Conecta el repo en https://share.streamlit.io y despliega — igual que hiciste con
   `cycling-performance-ml` o `credit-risk-scoring-ml`.

## Importante — honestidad sobre lo que cubre cada pestaña
- **BOE**: 100% automatizado, vía la API oficial de datos abiertos del BOE. No necesita
  API key. Si un día la estructura del JSON cambia ligeramente, el parsing está hecho
  a la defensiva (try/except) para no romper la app, pero puede que algún resultado no
  se capture — revísalo si un día ves 0 resultados en un rango donde esperabas alguno.
- **DOGC**: no tiene API pública abierta como el BOE, así que en vez de un scraper
  frágil te doy enlaces de búsqueda ya filtrados con tus palabras clave.
- **Ajuntaments**: solo Barcelona y Terrassa automatizados como enlace directo, más el
  buscador CIDO de la Diputació de Barcelona como agregador de toda la provincia.

## Próximos pasos posibles (si quieres ampliarla más adelante)
- Guardar resultados vistos en `window.storage` (si migras a versión artifact) o en un
  CSV local, para marcar cuáles ya has revisado.
- Añadir un envío de email/Telegram cuando aparezca una coincidencia nueva (requeriría
  desplegarla con un cron, por ejemplo GitHub Actions ejecutando el script en modo
  headless en vez de la interfaz Streamlit).

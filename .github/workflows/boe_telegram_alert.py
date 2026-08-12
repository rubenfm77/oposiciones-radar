"""
BOE Telegram Alert — standalone script (no Streamlit) meant to run on a schedule
=================================================================================

What it does:
  1. Fetches today's BOE sumario via the official open-data API.
  2. Filters section "II.B — Oposiciones y concursos" and matches your keywords.
  3. Compares against `seen_ids.json` (committed in the repo) to find only NEW matches.
  4. Sends a Telegram message per new match, and updates `seen_ids.json`.

Why this is separate from app.py:
  Streamlit apps only run code while someone has the page open — they can't check
  the BOE for you overnight. This script is meant to run headless on a schedule
  (see .github/workflows/boe_alert.yml) so it works even if you never open the app.

One-time setup:
  1. Create a Telegram bot: message @BotFather on Telegram, send /newbot, follow the
     prompts. You'll get a token that looks like "123456789:AAExxxxxxxxxxxxxxxxxxx".
  2. Get your chat_id: message your new bot anything, then open in a browser
     https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
     and look for "chat":{"id": 123456789, ...} in the JSON response.
  3. In your GitHub repo: Settings > Secrets and variables > Actions > New repository
     secret. Add two secrets: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
  4. Push this script + the workflow file. GitHub Actions runs it on the schedule
     defined there (default: once a day) for free.

Run manually to test:
    export TELEGRAM_BOT_TOKEN="123456789:AAExxxx..."
    export TELEGRAM_CHAT_ID="123456789"
    python boe_telegram_alert.py
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

SEEN_FILE = Path(__file__).parent / "seen_ids.json"

KEYWORDS = [
    "cuerpo de gestión de la administración",
    "sistemas y tecnologías de la información",
    "escala de gestión de la seguridad social",
    "cuerpo general administrativo de la seguridad social",
    "gestión procesal",
    "tramitación procesal",
    "administradores civiles",
]

BOE_SUMARIO_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}"
DAYS_TO_CHECK = 3  # revisamos hoy + 2 días atrás, por si el script falla un día puntual


# ---------------------------------------------------------------------------
# Helpers compartidos con app.py (duplicados aquí para que este script sea
# 100% independiente y no dependa de tener Streamlit instalado en el runner)
# ---------------------------------------------------------------------------
def _safe_str(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        for key in ("#text", "texto", "url", "@url"):
            if key in x and isinstance(x[key], str):
                return x[key].strip()
        return ""
    if isinstance(x, list) and x:
        return _safe_str(x[0])
    return str(x).strip()


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def fetch_boe_sumario(fecha_str: str):
    url = BOE_SUMARIO_URL.format(fecha=fecha_str)
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [WARN] error al consultar {fecha_str}: {e}", file=sys.stderr)
        return None


def extract_items_from_departamento(depto: dict):
    items = []
    for epigrafe in _as_list(depto.get("epigrafe")):
        items.extend(_as_list(epigrafe.get("item")))
    items.extend(_as_list(depto.get("item")))
    return items


def extract_oposiciones_del_dia(sumario_json: dict, fecha_str: str):
    resultados = []
    if not sumario_json:
        return resultados
    try:
        diario = sumario_json.get("data", {}).get("sumario", {}).get("diario")
        for d in _as_list(diario):
            for seccion in _as_list(d.get("seccion")):
                nombre_seccion = (seccion.get("nombre") or seccion.get("@nombre") or "").lower()
                if "oposici" not in nombre_seccion:
                    continue
                for depto in _as_list(seccion.get("departamento")):
                    nombre_depto = depto.get("nombre") or depto.get("@nombre") or "Sin departamento"
                    for it in extract_items_from_departamento(depto):
                        item_id = _safe_str(it.get("identificador")) or _safe_str(it.get("titulo"))
                        resultados.append({
                            "id": item_id,
                            "departamento": _safe_str(nombre_depto),
                            "titulo": _safe_str(it.get("titulo")) or "(sin título)",
                            "url_html": _safe_str(it.get("url_html")),
                            "fecha": fecha_str,
                        })
    except Exception as e:
        print(f"  [WARN] estructura inesperada en {fecha_str}: {e}", file=sys.stderr)
    return resultados


def filtra_por_keywords(items, keywords):
    kws = [k.lower().strip() for k in keywords if k.strip()]
    return [it for it in items if any(k in it["titulo"].lower() for k in kws)]


# ---------------------------------------------------------------------------
# Persistencia de "ya avisados"
# ---------------------------------------------------------------------------
def load_seen_ids() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_seen_ids(seen_ids: set):
    # Nos quedamos con los últimos 2000 para que el fichero no crezca sin límite
    trimmed = list(seen_ids)[-2000:]
    SEEN_FILE.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def send_telegram_message(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        print(f"  [ERROR] Telegram devolvió {r.status_code}: {r.text}", file=sys.stderr)
    return r.status_code == 200


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[ERROR] Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID como variables de entorno.")
        sys.exit(1)

    seen_ids = load_seen_ids()
    print(f"IDs ya vistos en ejecuciones anteriores: {len(seen_ids)}")

    todos = []
    hoy = date.today()
    for i in range(DAYS_TO_CHECK):
        fecha = hoy - timedelta(days=i)
        fecha_str = fecha.strftime("%Y%m%d")
        data = fetch_boe_sumario(fecha_str)
        items = extract_oposiciones_del_dia(data, fecha_str)
        todos.extend(items)
        print(f"  {fecha_str}: {len(items)} anuncios de oposiciones/concursos")

    filtrados = filtra_por_keywords(todos, KEYWORDS)

    # Deduplicado por id, por si el mismo anuncio aparece más de una vez en el sumario
    # (p. ej. representado tanto dentro de un epígrafe como directamente bajo el
    # departamento) — sin esto, un mismo anuncio podría enviarse dos veces en una
    # sola ejecución aunque seen_ids.json funcione perfectamente entre ejecuciones.
    vistos_en_esta_ejecucion = set()
    filtrados_unicos = []
    for it in filtrados:
        clave = it["id"] or it["titulo"]
        if clave in vistos_en_esta_ejecucion:
            continue
        vistos_en_esta_ejecucion.add(clave)
        filtrados_unicos.append(it)
    filtrados = filtrados_unicos

    nuevos = [it for it in filtrados if it["id"] and it["id"] not in seen_ids]

    print(f"Coincidencias totales: {len(filtrados)} · Nuevas (no notificadas antes): {len(nuevos)}")

    if not nuevos:
        print("Nada nuevo que notificar. Fin.")
        return

    for it in nuevos:
        mensaje = (
            f"📋 <b>Nueva oposición en el BOE</b>\n\n"
            f"{it['titulo']}\n\n"
            f"🏢 {it['departamento']}\n"
            f"📅 {it['fecha']}\n"
        )
        if it["url_html"]:
            mensaje += f"\n{it['url_html']}"

        ok = send_telegram_message(token, chat_id, mensaje)
        print(f"  {'✅ enviado' if ok else '❌ fallo al enviar'}: {it['titulo'][:60]}...")
        if ok:
            seen_ids.add(it["id"])

    save_seen_ids(seen_ids)
    print("seen_ids.json actualizado.")


if __name__ == "__main__":
    main()

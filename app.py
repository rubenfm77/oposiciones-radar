"""
Radar de Oposiciones — GACE, CSTI, Seguridad Social, Gestión Procesal, Generalitat, Ajuntaments
=================================================================================================

Qué hace de verdad (automatizado):
  - Consulta la API OFICIAL de datos abiertos del BOE (https://boe.es/datosabiertos) día a día,
    filtra la sección "II.B. Oposiciones y concursos" y busca tus palabras clave.

Qué hace "a medias" (sin API oficial fiable, así que se generan enlaces de búsqueda ya filtrados
en vez de fingir un scraping robusto que se rompería a la primera):
  - DOGC (Generalitat de Catalunya): no publica una API REST abierta como el BOE. En vez de un
    scraper frágil, la app te genera el enlace directo de búsqueda ya con tus palabras clave.
  - Ajuntament de Barcelona / Ajuntament de Terrassa: enlaces directos a sus portales de
    processos selectius. Cubrir los 300+ municipios de la provincia de Barcelona con un scraper
    fiable es un proyecto en sí mismo (cada ayuntamiento tiene su propia web, sin estándar común);
    aquí se cubren los dos que te interesan a ti y se deja preparado el patrón para añadir más.

Cómo correrla:
    pip install streamlit requests --break-system-packages
    streamlit run app.py
"""

import streamlit as st
import requests
from datetime import date, timedelta
from urllib.parse import quote_plus

st.set_page_config(page_title="Radar de Oposiciones", page_icon="📋", layout="wide")

# ---------------------------------------------------------------------------
# Configuración de palabras clave por defecto (editable desde la barra lateral)
# ---------------------------------------------------------------------------
KEYWORDS_DEFAULT = [
    "gestión de la administración civil",
    "sistemas y tecnologías de la información",
    "seguridad social",
    "gestión procesal",
    "tramitación procesal",
    "administradores civiles",
]

BOE_SUMARIO_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}"
BOE_SECCION_OPOS = "oposici"  # se busca en minúsculas dentro del nombre de sección (cubre "Oposiciones")


# ---------------------------------------------------------------------------
# BOE — parte automatizada de verdad, vía API oficial
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_boe_sumario(fecha_str: str):
    """Descarga el sumario del BOE de un día concreto (formato AAAAMMDD)."""
    url = BOE_SUMARIO_URL.format(fecha=fecha_str)
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if r.status_code == 404:
            return None  # no hay BOE ese día (festivo/domingo)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return "ERROR"


def _safe_str(x):
    """Convierte a string limpio cualquier valor que venga del JSON del BOE. A veces un campo
    que esperamos como texto plano llega como dict/lista si esa entrada tiene una estructura
    distinta (p.ej. varios PDFs en vez de uno) — aquí lo normalizamos para que nunca rompa
    un link_button, que exige un string no vacío."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        # A veces la URL viene anidada, p.ej. {"#text": "https://..."} o similar
        for key in ("#text", "texto", "url", "@url"):
            if key in x and isinstance(x[key], str):
                return x[key].strip()
        return ""
    if isinstance(x, list) and x:
        return _safe_str(x[0])
    return str(x).strip()


def _as_list(x):
    """La API del BOE a veces devuelve un dict cuando solo hay 1 elemento, y una lista si hay
    varios. Esta función normaliza siempre a lista para no romper el parsing."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def extract_items_from_departamento(depto: dict):
    """Extrae los anuncios/items de un departamento, tenga o no epígrafes intermedios."""
    items = []
    for epigrafe in _as_list(depto.get("epigrafe")):
        items.extend(_as_list(epigrafe.get("item")))
    items.extend(_as_list(depto.get("item")))
    return items


def extract_oposiciones_del_dia(sumario_json: dict):
    """Recorre el JSON del sumario y devuelve solo los anuncios de la sección
    'II.B Oposiciones y concursos', con departamento, título y enlaces."""
    resultados = []
    if not sumario_json or sumario_json == "ERROR":
        return resultados
    try:
        diario = sumario_json.get("data", {}).get("sumario", {}).get("diario")
        for d in _as_list(diario):
            for seccion in _as_list(d.get("seccion")):
                nombre_seccion = (seccion.get("nombre") or seccion.get("@nombre") or "").lower()
                if BOE_SECCION_OPOS not in nombre_seccion:
                    continue
                for depto in _as_list(seccion.get("departamento")):
                    nombre_depto = depto.get("nombre") or depto.get("@nombre") or "Sin departamento"
                    for it in extract_items_from_departamento(depto):
                        resultados.append({
                            "departamento": _safe_str(nombre_depto),
                            "titulo": _safe_str(it.get("titulo")) or "(sin título)",
                            "url_html": _safe_str(it.get("url_html")),
                            "url_pdf": _safe_str(it.get("url_pdf")),
                        })
    except Exception:
        # Estructura inesperada: no rompemos la app, devolvemos lo que tengamos
        pass
    return resultados


def filtra_por_keywords(items, keywords):
    if not keywords:
        return items
    kws = [k.lower().strip() for k in keywords if k.strip()]
    return [it for it in items if any(k in it["titulo"].lower() for k in kws)]


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📋 Radar de Oposiciones")
st.caption("BOE automatizado vía API oficial · DOGC y Ajuntaments con enlaces pre-filtrados")

with st.sidebar:
    st.header("⚙️ Configuración")
    keywords = st.text_area(
        "Palabras clave (una por línea)",
        value="\n".join(KEYWORDS_DEFAULT),
        height=160,
    ).splitlines()

    st.divider()
    dias_atras = st.slider("Días hacia atrás a revisar en el BOE", 1, 30, 7)
    st.caption("El BOE no publica sábados, domingos ni festivos — la app los salta sola.")

tab_boe, tab_dogc, tab_ajuntaments = st.tabs(["🇪🇸 BOE (AGE)", "📰 Generalitat (Oposicions)", "🏛️ Ajuntaments"])

# --- TAB BOE ---
with tab_boe:
    st.subheader("Convocatorias en el BOE (Sección II.B — Oposiciones y concursos)")
    if st.button("🔍 Buscar ahora en el BOE", type="primary"):
        hoy = date.today()
        todos = []
        errores = 0
        progreso = st.progress(0, text="Consultando el BOE día a día...")

        fechas = [hoy - timedelta(days=i) for i in range(dias_atras)]
        for idx, fecha in enumerate(fechas):
            fecha_str = fecha.strftime("%Y%m%d")
            data = fetch_boe_sumario(fecha_str)
            if data == "ERROR":
                errores += 1
            else:
                items = extract_oposiciones_del_dia(data)
                for it in items:
                    it["fecha"] = fecha.strftime("%d/%m/%Y")
                todos.extend(items)
            progreso.progress((idx + 1) / len(fechas), text=f"Revisando {fecha.strftime('%d/%m/%Y')}...")

        progreso.empty()
        filtrados = filtra_por_keywords(todos, keywords)

        st.success(f"Revisados {len(fechas)} días · {len(todos)} anuncios de oposiciones/concursos totales "
                    f"· {len(filtrados)} coinciden con tus palabras clave")
        if errores:
            st.warning(f"{errores} día(s) no se pudieron consultar (error de red o fin de semana/festivo).")

        if filtrados:
            for it in filtrados:
                try:
                    with st.container(border=True):
                        st.markdown(f"**{it['titulo']}**")
                        st.caption(f"📅 {it['fecha']} · 🏢 {it['departamento']}")
                        cols = st.columns(2)
                        url_html = it.get("url_html", "")
                        url_pdf = it.get("url_pdf", "")
                        if isinstance(url_html, str) and url_html.startswith("http"):
                            cols[0].link_button("Ver en BOE (HTML)", url_html)
                        if isinstance(url_pdf, str) and url_pdf.startswith("http"):
                            cols[1].link_button("Ver PDF", url_pdf)
                except Exception:
                    # Si un ítem concreto viene con una estructura rara, lo saltamos
                    # en vez de tumbar toda la app.
                    st.caption(f"⚠️ No se pudo mostrar un resultado ({it.get('titulo', '')[:60]}...)")
                    continue
        else:
            st.info("No hay coincidencias con tus palabras clave en el rango de fechas elegido. "
                    "Prueba a ampliar los días o revisar las palabras clave.")
    else:
        st.info("Pulsa el botón para consultar el BOE. La primera vez puede tardar unos segundos "
                "por día consultado (se cachea 1h para no repetir peticiones).")

# --- TAB DOGC / GENERALITAT ---
with tab_dogc:
    st.subheader("Oposicions de la Generalitat de Catalunya")
    st.info(
        "Mejor que buscar en el DOGC (que es un buscador de normativa legal, no de convocatorias): "
        "la Generalitat tiene un portal propio que centraliza todas las oposiciones activas por "
        "departamento, cuerpo y escala."
    )
    st.link_button("🔎 Abrir «Treballar a la Generalitat» — Oposicions (portal oficial)",
                    "https://web.gencat.cat/ca/generalitat/treballar-generalitat/oposicions",
                    use_container_width=True)
    st.caption(
        "Dentro de ese portal hay una sección de 'Previsió de convocatòries' con lo que está "
        "planificado a corto plazo, y el listado de convocatorias abiertas actualmente por cuerpo "
        "(útil para localizar directamente Cos Superior, Cos de Gestió, etc.)."
    )
    st.divider()
    st.caption(
        "Si además quieres rastrear el DOGC en sí (normativa, no solo convocatorias), el buscador "
        "avanzado oficial de todo su contenido desde 1977 está en el Portal Jurídic de Catalunya:"
    )
    st.link_button("📖 Portal Jurídic de Catalunya (buscador de normativa DOGC)",
                    "https://portaljuridic.gencat.cat/ca/inici/",
                    use_container_width=True)

# --- TAB AJUNTAMENTS ---
with tab_ajuntaments:
    st.subheader("Ajuntaments clave")
    st.warning(
        "Cubrir los 300+ ayuntamientos de la provincia de Barcelona con scraping fiable no es "
        "realista (cada uno tiene web distinta, sin estándar común). Aquí tienes acceso directo "
        "a los procesos selectivos de los que te interesan a ti, y el patrón para añadir más si "
        "algún día quieres ampliarlo."
    )
    st.link_button(
        "🏙️ Ajuntament de Barcelona — Processos selectius",
        "https://seuelectronica.ajuntament.barcelona.cat/processosselectius/",
        use_container_width=True,
    )
    st.link_button(
        "🏘️ Ajuntament de Terrassa — Oferta pública d'ocupació",
        "https://aoberta.terrassa.cat/ocupacio/",
        use_container_width=True,
    )

    st.divider()
    st.markdown("**Diputació de Barcelona — CIDO**, agregador de processos selectius de tots els "
                "municipis de la província (aquest sí que admet cerca per paraula clau en la URL):")
    for kw in [k for k in keywords if k.strip()]:
        url_cido = f"https://cido.diba.cat/oposicions?filtreParaulaClau%5Bkeyword%5D={quote_plus(kw)}"
        st.link_button(f"🔎 Buscar «{kw}» en el CIDO", url_cido, use_container_width=True)
    st.caption(
        "El CIDO de la Diputació de Barcelona es lo más parecido a un agregador de oposiciones "
        "municipales de toda la provincia — no es una API, pero es el mejor punto único de consulta "
        "que existe para no tener que mirar ayuntamiento por ayuntamiento."
    )

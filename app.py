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
    processos selectius. Además, el CIDO (Diputació de Barcelona) indexa procesos de TODA
    Catalunya, incluida la zona de Girona vía XALOC — no hace falta scrapear cada municipio
    uno a uno para tener cobertura razonable de ambas provincias.

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
    "gestión",
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
    dias_atras = st.slider("Días hacia atrás a revisar en el BOE", 1, 90, 30)
    st.caption("El BOE no publica sábados, domingos ni festivos — la app los salta sola. "
               "Las grandes convocatorias (GACE, CSTI...) suelen salir 1-2 veces al año, así que "
               "conviene mirar un rango amplio, no solo la última semana.")

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

        st.caption(
            "⚠️ Las palabras clave son frases exactas — si el BOE redacta el título de forma distinta "
            "a como lo escribiste (p. ej. 'Cuerpo General' en vez de tu frase completa), no aparecerá "
            "aquí abajo aunque sí sea relevante. Por eso te dejo también la lista SIN filtrar para que "
            "la revises tú mismo si quieres estar 100% seguro de no perderte nada."
        )

        st.markdown("### 🎯 Coincidencias con tus palabras clave")
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
                    "Prueba a ampliar los días, o revisa la lista completa sin filtrar de abajo.")

        with st.expander(f"📋 Ver TODOS los anuncios de oposiciones/concursos del rango ({len(todos)}), sin filtrar"):
            for it in todos:
                st.markdown(f"- **{it['titulo']}** · {it.get('fecha', '')} · _{it['departamento']}_")
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
    st.subheader("Ajuntaments — Barcelona i Girona")
    st.warning(
        "Cubrir cada ayuntamiento de forma individual con scraping fiable no es realista (webs "
        "distintas, sin estándar común). Pero el CIDO no es solo de la provincia de Barcelona: "
        "indexa procesos selectivos de TODA Catalunya, incluida la red de municipios de Girona a "
        "través de XALOC (el servicio equivalente de la Diputació de Girona)."
    )

    col_bcn, col_girona = st.columns(2)

    with col_bcn:
        st.markdown("#### 🏙️ Zona Barcelona")
        st.link_button(
            "Ajuntament de Barcelona — Processos selectius",
            "https://seuelectronica.ajuntament.barcelona.cat/processosselectius/",
            use_container_width=True,
        )
        st.link_button(
            "Ajuntament de Terrassa — Oferta pública d'ocupació",
            "https://aoberta.terrassa.cat/ocupacio/",
            use_container_width=True,
        )

    with col_girona:
        st.markdown("#### 🏔️ Zona Girona")
        st.link_button(
            "Diputació de Girona — Tauler electrònic (oferta d'ocupació pròpia)",
            "https://seu.ddgi.cat/web/nivell/326/s-1/oferta-d-ocupacio",
            use_container_width=True,
        )
        st.caption(
            "Los ayuntamientos pequeños de la provincia de Girona suelen gestionar su selección de "
            "personal a través de XALOC (Xarxa Local de Municipis Gironins), cuyas convocatorias "
            "también aparecen indexadas en el CIDO — usa los enlaces filtrados de abajo."
        )

    st.divider()
    st.markdown("**CIDO — buscador de procesos selectivos de toda Catalunya** "
                "(Diputació de Barcelona, pero indexa también Girona/XALOC):")
    for kw in [k for k in keywords if k.strip()]:
        url_cido = f"https://cido.diba.cat/oposicions?filtreParaulaClau%5Bkeyword%5D={quote_plus(kw)}"
        st.link_button(f"🔎 Buscar «{kw}» en el CIDO (toda Catalunya)", url_cido, use_container_width=True)

    st.caption(
        "Tip: dentro del CIDO puedes además filtrar por proximidad geográfica (población + radio en "
        "km) o por institución concreta (p.ej. 'Ajuntaments de Girona' o 'XALOC') una vez abierto el "
        "buscador, para acotar aún más sin tener que revisar ayuntamiento por ayuntamiento."
    )
    st.caption(
        "El CIDO de la Diputació de Barcelona es lo más parecido a un agregador de oposiciones "
        "municipales de toda la provincia — no es una API, pero es el mejor punto único de consulta "
        "que existe para no tener que mirar ayuntamiento por ayuntamiento."
    )

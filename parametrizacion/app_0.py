import streamlit as st
import pandas as pd
import numpy as np
import math
import io
from docx import Document
from docx.shared import Pt
from typing import List, Tuple, Dict, Union, Any

# ── Configuración ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Visualizador Tablas de Correlaciones",
    layout="wide",
    page_icon="📊",
)

st.markdown("""
<style>
html, body, [data-testid="stApp"] { background-color: #f5f6f8; }

/* ── Expander base nativo (Reemplaza al JavaScript anterior) ── */
div[data-testid="stExpander"] {
    border: 1px solid #b3d4ec;
    border-radius: 10px;
    background-color: #ffffff;
    box-shadow: 0 2px 5px rgba(0,0,0,0.04);
}
div[data-testid="stExpander"] > details > summary {
    background-color: #f0f7fd !important;
    color: #0d3a5c !important;
    border-radius: 10px; 
    padding: 12px 18px;
    font-size: 1.05rem; 
    font-weight: 600; 
    border: none;
    transition: filter 0.2s;
}
div[data-testid="stExpander"] > details > summary:hover {
    filter: brightness(0.95);
}
div[data-testid="stExpander"] > details[open] > summary { 
    border-radius: 10px 10px 0 0; 
    border-bottom: 1px solid #b3d4ec;
}

/* ── Tablas ── */
.custom-table {
    border-collapse: collapse; width: 100%;
    font-size: 0.88rem; margin-top: 6px;
}
.custom-table thead tr th {
    background-color: #daeeff !important; color: #0d3a5c !important;
    font-weight: 700; padding: 8px 12px;
    border: 1px solid #a8cce8; text-align: center;
}
.custom-table tbody tr td {
    padding: 6px 12px; border: 1px solid #d9e8f5; text-align: center;
}
.custom-table tbody tr:nth-child(even) { background-color: #eaf4fc; }

.table-subtitle {
    color: #0d3a5c; font-size: 0.93rem; font-weight: 700;
    margin: 14px 0 4px 2px; padding: 4px 10px;
    border-left: 3px solid #1a6ea8; background-color: #e4f0fa;
    border-radius: 0 6px 6px 0;
}
.param-section-label {
    font-size: 0.78rem; font-weight: 700; color: #0d3a5c;
    background: #daeeff; border: 1px solid #a8cce8;
    padding: 4px 6px; text-align: center;
    margin-bottom: 1px;
}

/* ── Banners de categoria ── */
.cat-banner {
    display: flex; align-items: center; gap: 14px;
    padding: 11px 20px; border-radius: 10px;
    margin: 22px 0 8px 0; font-size: 1.05rem;
    font-weight: 700; letter-spacing: 0.04em;
}
.cat-resistencia {
    background: linear-gradient(90deg, #d4edda, #eaf7ee);
    border-left: 6px solid #2d8c4e; color: #1a5c32;
}
.cat-elasticidad {
    background: linear-gradient(90deg, #cce5ff, #e8f4fd);
    border-left: 6px solid #1a6ea8; color: #0d3a5c;
}

/* ── Cabecera principal ── */
.app-header {
    background: linear-gradient(135deg, #0d3a5c 0%, #1a6ea8 60%, #2196b8 100%);
    border-radius: 14px; padding: 26px 32px 22px;
    margin-bottom: 10px;
}
.app-header h1 {
    color: #ffffff; margin: 0 0 6px; font-size: 1.85rem;
    font-weight: 800; letter-spacing: 0.01em;
}
.app-header p { color: #b8daf2; margin: 0; font-size: 0.92rem; line-height: 1.5; }
.legend-row { display: flex; gap: 20px; margin-top: 14px; flex-wrap: wrap; }
.legend-item {
    display: flex; align-items: center; gap: 7px;
    font-size: 0.82rem; font-weight: 600; color: #e0f0ff;
}
.legend-dot { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)

# ── Titulo principal con leyenda de colores ────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>📊 Tablas de Correlaciones Geotécnicas</h1>
    <p>Correlaciones empíricas para la estimación de parámetros del suelo a partir del ensayo SPT y propiedades índice.<br>
    Modifica los valores de entrada para recalcular los resultados automáticamente en tiempo real.</p>
    <div class="legend-row">
        <div class="legend-item">
            <div class="legend-dot" style="background:#2d8c4e;"></div>Parámetros resistentes
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background:#5ba8d6;"></div>Parámetros elásticos
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Utilidades ────────────────────────────────────────────────────────────────

def _r(v: Union[float, int, str, None], d: int = 2) -> str:
    """Formatea número: entero si es entero, sino redondea a d decimales. Protegido contra NaN."""
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    try:
        f = float(v)
        if abs(f - round(f)) < 1e-9 and abs(f) < 1e9:
            return str(int(round(f)))
        return str(round(f, d))
    except (ValueError, TypeError):
        return str(v)

def render_table(df: pd.DataFrame, key_df: str = None) -> None:
    """Renderiza la tabla en HTML y opcionalmente la guarda en session_state para exportarla."""
    if key_df:
        st.session_state[f"df_{key_df}"] = df
        
    st.markdown(
        df.to_html(index=False, border=0, classes="custom-table"),
        unsafe_allow_html=True,
    )

def subtitulo(texto: str) -> None:
    st.markdown(f'<p class="table-subtitle">{texto}</p>', unsafe_allow_html=True)

def params_inputs(params: List[Tuple], sheet_key: str) -> Dict[str, float]:
    """
    Muestra tabla de parámetros con number_input.
    Espera tuplas de 4 o 5 elementos: (símbolo, descripción, valor_default, unidad, [valor_mínimo])
    """
    h0, h1, h2, h3 = st.columns([1, 3.5, 1.5, 0.9])
    for col, lbl in zip((h0, h1, h2, h3), ("Símbolo", "Descripción", "Valor", "Unidad")):
        col.markdown(f"<div class='param-section-label'>{lbl}</div>", unsafe_allow_html=True)

    vals = {}
    for item in params:
        sym = item[0]
        desc = item[1]
        default = float(item[2])
        unit = item[3]
        min_v = float(item[4]) if len(item) > 4 else None

        c0, c1, c2, c3 = st.columns([1, 3.5, 1.5, 0.9])
        c0.markdown(f"**{sym}**")
        c1.write(desc)
        c3.write(unit)
        
        safe_default = max(default, min_v) if min_v is not None else default

        val = c2.number_input(
            label=sym,
            value=safe_default,
            min_value=min_v,
            key=f"{sheet_key}_{sym}",
            label_visibility="collapsed",
        )
        vals[sym] = val
    return vals

# ── Generador de Informe Word ─────────────────────────────────────────────────
def generar_informe_word() -> io.BytesIO:
    doc = Document()
    
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)

    doc.add_heading('Anexo de Cálculo: Correlaciones Geotécnicas', 0)
    doc.add_paragraph('Documento generado automáticamente a partir de los datos introducidos en la herramienta de estimación empírica.')

    mapa_dfs = {
        "Cu — Resistencia al corte sin drenaje": "cu",
        "RCS → CTE — Resistencia a compresión simple": "rcs",
        "φ → Ángulo de rozamiento efectivo": "fr",
        "φr → Ángulo de rozamiento residual arcilla": "fr_residual",
        "E → Módulo de elasticidad arenas": "e_arenas",
        "E → Módulo de elasticidad arcillas": "e_arcillas",
        "E → Módulo de elasticidad CTE": "e_cte",
        "Kv — Módulo de balasto vertical": "kv",
        "ν — Coeficiente de Poisson": "poisson"
    }

    incluido_algo = False

    for cat in CATEGORIAS:
        for nombre, fn in cat["hojas"]:
            key_checkbox = f"export_{nombre}"
            if st.session_state.get(key_checkbox, False):
                incluido_algo = True
                doc.add_heading(nombre, level=1)
                
                key_df = mapa_dfs.get(nombre)
                if key_df and f"df_{key_df}" in st.session_state:
                    df = st.session_state[f"df_{key_df}"]
                    table = doc.add_table(rows=1, cols=len(df.columns))
                    table.style = 'Table Grid'
                    
                    hdr_cells = table.rows[0].cells
                    for i, column in enumerate(df.columns):
                        hdr_cells[i].text = str(column)
                    
                    for index, row in df.iterrows():
                        row_cells = doc.add_row().cells
                        for i, val in enumerate(row):
                            row_cells[i].text = str(val)
                    
                    doc.add_paragraph()

    if not incluido_algo:
        doc.add_paragraph('No se seleccionó ninguna tabla para exportar.')

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════════════════════════
#  HOJAS DE CÁLCULO
# ══════════════════════════════════════════════════════════════════════════════

def sheet_cu():
    p = params_inputs([
        ("Nspt", "Golpeo ensayo SPT",              47.0, "golpeos", 10.0),
        ("s'",   "Tensión efectiva cota muestra",  25.0, "kPa",      0.0),
        ("IP",   "Índice de Plasticidad",          19.0, "%",        0.0),
        ("LL",   "Límite líquido",                 38.0, "%",        0.0),
    ], "cu")
    N, s, IP, LL = p["Nspt"], p["s'"], p["IP"], p["LL"]

    def aplic(cond): return "Aplica" if cond else "No aplica"

    def cu_14():
        try:
            return _r((0.11 + 0.0037 * math.log10(IP)) * s, 4) if IP > 0 else "—"
        except ValueError:
            return "—"
    
    st.info("ATENCIÓN SE USAN CUATRO GRUPOS DE PARÁMETROS")

    rows = [
        (1,  "Terzaghi y Peck",         "Arcillas",                                 _r(0.067*N*98.1),           "Nspt",   ""),
        (2,  "DM-7",                    "Arcilla de baja plasticidad",              _r(0.038*N*98.1),           "Nspt",   ""),
        (3,  "DM-7",                    "Arcilla de media plasticidad",             _r(0.074*N*98.1),           "Nspt",   ""),
        (4,  "DM-7 y Sangletat",        "Arcilla de alta plasticidad",              _r(0.125*N*98.1),           "Nspt",   ""),
        (5,  "Sanglerat",               "Arcilla limosa",                           _r(0.1*N*98.1),             "Nspt",   ""),
        (6,  "Sanglerat",               "Arcilla limo arenosa",                     _r(0.067*N*98.4),           "Nspt",   ""),
        (7,  "Sanglerat 1",             "Arcillas",                                 _r(98.1*N/10),              "Nspt",   ""),
        (8,  "Sanglerat 2",             "Arcillas",                                 _r(N*98.1/15.6),            "Nspt",   ""),
        (9,  "Sowers",                  "Arcillas baja plasticidad y limos arc.",   _r(0.5*191.57*N/15),        "Nspt",   ""),
        (10, "Shioi-Fukui",             "Arcillas de media plasticidad",            _r(0.025*N*98.1),           "Nspt",   ""),
        (11, "Shioi-Fukui",             "Arcillas de alta plasticidad",             _r(0.05*N*98.1),            "Nspt",   ""),
        (12, "Bjerrum & Simons 1960",   "Arcillas IP>50",                           _r(0.45*s*math.sqrt(max(IP,0)/100), 4), "IP, s'", aplic(IP >= 50)),
        (13, "Terzaghi y Peck",         "Arcilla NC  IP>10",                        _r((0.11+0.0037*IP)*s, 4),  "IP, s'", aplic(IP > 10)),
        (14, "Skempton 1954",           "Arcillas NC, IP<60",                       cu_14(),                    "IP, s'", aplic(IP < 60)),
        (15, "Lambe & Whitman, 1969",   "Todo tipo de arcillas",                    _r((0.14+0.003*IP)*s, 4),   "IP, s'", ""),
        (16, "Karlson & Viberg 1697",   "Arcillas LL>40",                           _r(0.5*LL*s/100, 4),        "LL, s'", aplic(LL > 40)),
        (17, "Mesri 1975",              "Arcillas blandas",                         _r(0.22*s, 4),              "s'",     ""),
        (18, "Larsson, 1980",           "Arcillas inorgánicas",                     _r(0.33*s, 4),              "s'",     ""),
    ]

    st.write("")
    subtitulo("Tabla de estimación de valores Cu")
    df_cu = pd.DataFrame(rows, columns=["ID", "Autor", "Aplicación", "Cu (kPa)", "Parámetros", "Criterio"])
    render_table(df_cu, key_df="cu")

def sheet_rcs():
    p = params_inputs([
        ("Nspt", "Golpeo ensayo SPT", 47.0, "golpeos", 10.0),
    ], "rcs")
    N = p["Nspt"]

    def r8():  return _r(8*N)                                  if N <= 10            else "No aplica"
    def r9():  return _r((150-80)*(N-10)/(25-10)+80)           if 10 < N <= 25       else "No aplica"
    def r10(): return _r((300-150)*(N-25)/(50-25)+150)         if 25 < N <= 50       else "No aplica"
    def r11(): return _r((500-300)*(N-50)/(100-50)+300)        if 50 < N <= 100      else "No aplica"

    st.info("REFERENCIA TABLA D,23 VALORES ORIENTATIVOS DE RESISTENCIA A COMPRESION DE SUELOS COHESIVOS")
    st.write("")
    subtitulo("Tabla de estimación de valores de Resistencia a Compresión Simple")
    df_rcs = pd.DataFrame([
        (1, "Suelos muy flojos o muy blandos", "N < 10",          r8(),  "Nspt"),
        (2, "Suelos flojos o blandos",          "N entre 10 a 25", r9(),  "Nspt"),
        (3, "Suelos medios",                    "N entre 25 a 50", r10(), "Nspt"),
        (4, "Suelos compactos o duros",         "N = 50 o Rechazo",r11(), "Nspt"),
    ], columns=["ID", "Autor", "Aplicación", "qu (kPa)", "Parámetros"])
    render_table(df_rcs, key_df="rcs")

def sheet_fr():
    p = params_inputs([
        ("Nspt", "Golpeo ensayo SPT",     40.0, "golpeos", 10.0),
        ("IP",   "Índice de Plasticidad", 36.5, "%",        0.0),
    ], "fr")
    N, IP = p["Nspt"], p["IP"]

    sqN = math.sqrt(max(N, 0))
    try:
        lnval = math.log(0.166 * N) if N > 0 else float("nan")
    except ValueError:
        lnval = float("nan")
        
    st.info("SE USAN VARIOS TIPOS DE PARÁMETROS")

    rows = [
        (1,  "Jiménez Salas y Justo Alpañes", "Suelos arcillosos y limosos C03<12%",          _r(34.9 - 0.339*IP),               "IP"),
        (2,  "Jiménez Salas y Justo Alpañes", "Suelos compactados al 95% PN",                 _r(36.3 - 0.567*IP),               "IP"),
        (3,  "Peck",                               "Arenas",                                         _r(27.1 + 0.3*N - 0.00054*N**2),   "Nspt"),
        (4,  "Muromachi, 1974",                    "Arenas",                                         _r(20 + 3.5*sqN),                  "Nspt"),
        (5,  "Terzaghi & Peck 1948",               "Arenas",                                         _r(28.5 + 0.25*N),                 "Nspt"),
        (6,  "Kishida, 1969",                      "Arenas",                                         _r(15 + math.sqrt(20*max(N,0))),   "Nspt"),
        (7,  "Japan National Railway, 1999",        "Arenas",                                         _r(27 + 0.3*N),                    "Nspt"),
        (8,  "Japan Road Bureau, 1986",             "Arenas",                                         _r(15 + math.sqrt(9.375*max(N,0))),"Nspt"),
        (9,  "Hatanaka & Uchida, 1996",             "Arenas",                                         _r(math.sqrt(20*max(N,0)) + 20),   "Nspt"),
        (10, "Montenegro & Gonzalez",               "Arenas",                                         _r(12.79 + math.sqrt(25.86*max(N,0))), "Nspt"),
        (11, "Shioi-Fukuni 1982",                   "Arenas finas y limos",                           _r(15 + math.sqrt(15*max(N,0))),   "Nspt"),
        (12, "Shioi-Fukuni 1982",                   "Arenas medias gruesas",                          _r(0.3*N + 27),                    "Nspt"),
        (13, "Owasaki & Iwasaki",                   "Arenas medias a gruesas y finas con grava",      _r(15 + math.sqrt(20*max(N,0))),   "Nspt"),
        (14, "Sowers",                              "Arenas en general",                              _r(28 + 0.28*N),                   "Nspt"),
        (15, "Schmertmann 1978",                    "Arenas arcillosas",
             _r(24 + 5.77*lnval) if not math.isnan(lnval) else "—",                                                                     "Nspt"),
    ]

    st.write("")
    subtitulo("Tabla de estimación de valores del ángulo de rozamiento efectivo")
    df_fr = pd.DataFrame(rows, columns=["ID", "Autor", "Aplicación", "f (°)", "Parámetros"])
    render_table(df_fr, key_df="fr")
    
def sheet_fr_residual():
    p = params_inputs([
        ("T42", "% que pasa por el Tamiz 0,42 mm (ASTM)", 80.0, "%", 0.0),
        ("CA",  "% Contenido de arcilla",                  65.0, "%", 0.0),
        ("LL",  "Límite líquido",                          35.0, "%", 0.0),
        ("LP",  "Límite Plástico",                         15.0, "%", 0.0),
    ], "frr")
    T42, CA, LL, LP = p["T42"], p["CA"], p["LL"], p["LP"]

    CA_star = (CA * 100 / T42) if T42 != 0 else 0.0
    CALIP   = CA_star**2 * LL * LP * 0.00001

    st.write("")
    subtitulo("Cálculos intermedios")
    render_table(pd.DataFrame([
        ("CA*",   "Contenido de arcilla respecto al % que pasa Tamiz 0,42 mm", _r(CA_star, 4), "%"),
        ("CALIP", "Parámetro de cálculo",                                       _r(CALIP, 4),   "--"),
    ], columns=["Símbolo", "Descripción", "Valor", "Unidad"]))

    x = CALIP
    def p_f17(x): return 1.067e-8*x**5 - 3.113e-6*x**4 + 3.041e-4*x**3 - 0.0075572*x**2 - 0.4549668*x  + 28.70807
    def p_h17(x): return 1.667e-8*x**5 - 4.564e-6*x**4 + 4.221e-4*x**3 - 0.0104326*x**2 - 0.546262 *x  + 34.9509123
    def p_f19(x): return 1.449e-8*x**5 - 3.993e-6*x**4 + 3.564e-4*x**3 - 0.0068035*x**2 - 0.5482355*x  + 28.0581335
    def p_h19(x): return 1.267e-8*x**5 - 3.237e-6*x**4 + 2.396e-4*x**3 + 0.0018737*x**2 - 0.8809821*x  + 35.0004382

    f17 = p_f17(x) if x < 90 else 7.0
    h17 = p_h17(x) if x < 90 else 8.0
    f18 = (f17 + h17) * 0.5
    f19 = p_f19(x) if x < 95 else 7.0
    h19 = p_h19(x) if x < 90 else 8.0
    f20 = (f19 + h19) * 0.5

    st.write("")
    st.info(
        "**Nota sobre la metodología de cálculo:**\n"
        "Los polinomios de 5º grado aplicados en esta sección para la obtención "
        "de **φ'** y **φ' promedio** corresponden a ajustes empíricos basados en "
        "el parámetro de cálculo **CALIP** (Contenido de Arcilla x Límite Líquido "
        "x Índice Plástico). Estos modelos son aproximaciones analíticas derivadas "
        "de ensayos de corte directo residual y corte torsional."
    )
    
    subtitulo("Resultados — Ángulos de rozamiento residual")
    df_fr_res = pd.DataFrame([
        ("Corte directo residual",           "f'",          _r(f17,4), "a", _r(h17,4), "°"),
        ("Corte directo residual (promedio)", "f' promedio", _r(f18,4), "--","--",       "°"),
        ("Corte torsional",                  "f'",          _r(f19,4), "a", _r(h19,4), "°"),
        ("Corte torsional (promedio)",        "f' promedio", _r(f20,4), "--","--",       "°"),
    ], columns=["Propiedad", "Símbolo", "Valor mínimo", "Rango", "Valor máximo", "Unidad"])
    render_table(df_fr_res, key_df="fr_residual")

def sheet_e_arenas():
    p = params_inputs([
        ("Nspt", "Golpeo ensayo SPT", 40.0, "golpeos", 10.0),
    ], "ea")
    N = p["Nspt"]

    st.info("RECOMENDABLE USAR EL Nspt X 0,60")

    rows = [
        (1,  "Webb, 1974",            "Arenas arcillosas",               _r(3.3*(N+15)*98.1/1000),  "Nspt"),
        (2,  "Webb, 1974",            "Casos intermedios",               _r(4*(N+12)*98.1/1000),    "Nspt"),
        (3,  "Denver, 1982",          "Arenas",                          _r(7*math.sqrt(max(N,0))), "Nspt"),
        (5,  "Meigh y Nixon, 1961",   "Limos y limos arenosos",          _r(5*N*98.1/1000),         "Nspt"),
        (6,  "Meigh y Nixon, 1691",   "Arenas finas",                    _r(8*N*98.1/1000),         "Nspt"),
        (7,  "Wrench y Nowatzki, 1986","Gravas",                         _r(2.22*max(N,0)**0.886) if N > 0 else "—", "Nspt"),
        (8,  "Bowles, 1996",          "Arenas normalmente consolidadas", _r(5*(N+15)*98.1/1000),    "Nspt"),
        (9,  "Bowles, 1996",          "Gravas N≤15",                     _r(6*(N+6)*98.1/1000),     "Nspt"),
        (10, "Bowles, 1996",          "Gravas N>15",                     _r((6*(N+6)+20)*98.1/1000),"Nspt"),
        (11, "Begueman 1974",         "Gravas y arenas N≤15",            _r(12*(N+6)*98.1/1000),    "Nspt"),
        (12, "Begueman 1974",         "Gravas y arenas N>15",            _r((40+12*(N+6))*98.1/1000),"Nspt"),
        (13, "Schertmann 1970",       "Arenas",                          _r(8*N*98.1/1000),         "Nspt"),
        (14, "D'Polonia y otros",     "Arenas normalmente consolidadas", _r((215+10.6*N)*98.1/1000),"Nspt"),
        (15, "D'Polonia y otros",     "Arenas preconsolidadas",          _r((540+13.5*N)*98.1/1000),"Nspt"),
    ]

    st.write("")
    subtitulo("Tabla de estimación de valores del módulo de elasticidad para arenas")
    df_e_arenas = pd.DataFrame(rows, columns=["ID", "Autor", "Aplicación", "E (MPa)", "Parámetros"])
    render_table(df_e_arenas, key_df="e_arenas")
    
def sheet_e_arcillas():
    p = params_inputs([
        ("IP",   "Índice de plasticidad", 12.0, "%", 0.0),
        ("Nspt", "Golpeo ensayo SPT",     22.0, "golpeos", 10.0),
        ("Cu",   "Cohesión sin drenaje",   0.0, "kPa", 0.0),
    ], "earc")
    IP, N, Cu = p["IP"], p["Nspt"], p["Cu"]

    st.info("ATENCIÓN SE USAN VARIAS PROCEDENCIAS DE PARÁMETROS, Cu y el conjunto (Nspt,IP)")

    rows = [
        (1,  "Stroud, 1974 límite superior",  "Arcillas",               _r(N*(-0.0081*IP**3+1.732*IP**2-127*IP+3703)/1000), "Nspt, IP"),
        (2,  "Stroud, 1974 límite inferior",  "Arcillas",               _r(N*(-0.0031*IP**3+0.8591*IP**2-72.041*IP+2410)/1000),"Nspt, IP"),
        (3,  "Stroud y Buttler",              "Arcillas media plast.",  _r(5*N*98.1/1000),    "Nspt"),
        (4,  "Stroud y Buttler",              "Arcillas baja plast.",   _r(6*N*98.1/1000),    "Nspt, IP"),
        (5,  "CTE-DB-SE-C, Tabla F.2",        "IP<30, OCR<3",           _r(800*Cu/1000),       "Cu"),
        (6,  "CTE-DB-SE-C, Tabla F.2",        "IP<30, 3<OCR<5",        _r(600*Cu/1000),       "Cu"),
        (7,  "CTE-DB-SE-C, Tabla F.2",        "IP<30, OCR>5",           _r(300*Cu/1000),       "Cu"),
        (8,  "CTE-DB-SE-C, Tabla F.2",        "30<IP<50, OCR<3",        _r(350*Cu/1000),       "Cu"),
        (9,  "CTE-DB-SE-C, Tabla F.2",        "30<IP<50, 3<OCR<5",     _r(250*Cu/1000),       "Cu"),
        (10, "CTE-DB-SE-C, Tabla F.2",        "30<IP<50, OCR>5",        _r(130*Cu/1000),       "Cu"),
        (11, "CTE-DB-SE-C, Tabla F.2",        "IP>50, OCR<3",           _r(150*Cu/1000),       "Cu"),
        (12, "CTE-DB-SE-C, Tabla F.2",        "IP>50, 3<OCR<5",        _r(100*Cu/1000),       "Cu"),
        (13, "CTE-DB-SE-C, Tabla F.2",        "IP>50, OCR>5",           _r(50*Cu/1000),        "Cu"),
    ]

    st.write("")
    subtitulo("Tabla de estimación de valores de E para arcillas")
    df_e_arcillas = pd.DataFrame(rows, columns=["ID", "Autor", "Aplicación", "E (MPa)", "Parámetros"])
    render_table(df_e_arcillas, key_df="e_arcillas")

def sheet_e_cte():
    p = params_inputs([
        ("Nspt", "Golpeo ensayo SPT", 41.0, "golpeos", 10.0),
    ], "ecte")
    N = p["Nspt"]

    def r8():  return _r(0.8*N)                          if N <= 10       else "No aplica"
    def r9():  return _r((40-8)*(N-10)/(25-10)+8)        if 10 < N <= 25  else "No aplica"
    def r10(): return _r((100-40)*(N-25)/(50-25)+40)     if 25 < N <= 50  else "No aplica"
    def r11(): return _r((500-100)*(N-50)/(100-50)+100)  if 50 < N <= 100 else "No aplica"

    st.info("REFERENCIA TABLA D,23 VALORES ORIENTATIVOS DE MÓDULO DE ELASTICIDAD DE SUELOS")
    st.write("")
    subtitulo("Tabla de estimación de valores de E según CTE")
    df_e_cte = pd.DataFrame([
        (1, "Suelos muy flojos o muy blandos", "N < 10",           r8(),  "Nspt"),
        (2, "Suelos flojos o blandos",          "N entre 10 a 25", r9(),  "Nspt"),
        (3, "Suelos medios",                    "N entre 25 a 50", r10(), "Nspt"),
        (4, "Suelos compactos o duros",         "N = 50 o Rechazo",r11(), "Nspt"),
    ], columns=["ID", "Autor", "Aplicación", "E (MPa)", "Parámetros"])
    render_table(df_e_cte, key_df="e_cte")

def sheet_kv():
    subtitulo("Parámetros de cálculo KsB")
    p = params_inputs([
        ("B",   "Ancho de la cimentación",           2.0,  "m", 0.0),
        ("L",   "Longitud de la cimentación",        2.0,  "m", 0.0),
        ("K30", "Coef. balasto placa 30×30 cm",     25.0,  "MN/m³", 0.0),
    ], "kv")
    B, L, K30 = p["B"], p["L"], p["K30"]

    KsB_coh  = K30 * 0.3 / B                          if B != 0 else 0.0
    KsB_gran = K30 * ((B + 0.3) / (2 * B))**2         if B != 0 else 0.0
    KsBL_coh  = KsB_coh  * (1 + B / (2 * L))          if L != 0 else 0.0
    KsBL_gran = KsB_gran * (1 + B / (2 * L))          if L != 0 else 0.0

    st.write("")
    subtitulo("Valores orientativos k30 según tipo de suelo (Fuente: CTE-DB-C)")
    render_table(pd.DataFrame([
        ("Arcilla blanda",           15,     30),
        ("Arcilla media",            30,     60),
        ("Arcilla dura",             60,    200),
        ("Limo",                     15,     45),
        ("Arena floja",              10,     30),
        ("Arena media",              30,     90),
        ("Arena compacta",           90,    200),
        ("Grava arenosa floja",      70,    120),
        ("Grava arenosa compacta",  120,    300),
        ("Margas arcillosas",       200,    400),
        ("Rocas algo alteradas",    300,   5000),
        ("Rocas sanas",           ">5000",  ">5000"),
    ], columns=["Tipo de suelo", "k30 mín (MN/m³)", "k30 máx (MN/m³)"]))

    st.write("")
    subtitulo("Resultados — Módulo de balasto KsB")
    
    # Agrupamos resultados para el Word
    df_kv_res = pd.DataFrame([
        ("Cuadrada",     "Suelo Cohesivo",  "KsB",  _r(KsB_coh,  4), "MN/m³", "K30 · 0,30 / B"),
        ("Cuadrada",     "Suelo Granular",  "KsB",  _r(KsB_gran, 4), "MN/m³", "K30 · [(B+0,30)/(2B)]²"),
        ("Rectangular", "Suelo Cohesivo",  "KsBL", _r(KsBL_coh, 4), "MN/m³", "KsB · (1 + B/2L)"),
        ("Rectangular", "Suelo Granular",  "KsBL", _r(KsBL_gran,4), "MN/m³", "KsB · (1 + B/2L)"),
    ], columns=["Tipo cimentación", "Tipo suelo", "Parámetro", "Valor", "Unidad", "Fórmula"])
    
    render_table(df_kv_res, key_df="kv")


def sheet_poisson():
    subtitulo("Tabla de estimación de valores del coeficiente de Poisson")
    df_poisson = pd.DataFrame([
        (1, "CTE DB SE-C Tabla D.24", "Arcillas normalmente consolidadas",  0.40),
        (2, "CTE DB SE-C Tabla D.24", "Arcillas medias",                    0.30),
        (3, "CTE DB SE-C Tabla D.24", "Arcillas duras preconsolidadas",     0.15),
        (4, "CTE DB SE-C Tabla D.24", "Arenas y suelos granulares",         0.30),
    ], columns=["ID", "Fuente", "Aplicación", "ν"])
    render_table(df_poisson, key_df="poisson")

# ══════════════════════════════════════════════════════════════════════════════
#  LAYOUT PRINCIPAL 
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIAS = [
    {
        "nombre": "Parámetros Resistentes",
        "icono": "",
        "clase": "resistencia",
        "hojas": [
            ("Cu — Resistencia al corte sin drenaje",        sheet_cu),
            ("RCS → CTE — Resistencia a compresión simple",  sheet_rcs),
            ("φ → Ángulo de rozamiento efectivo",            sheet_fr),
            ("φr → Ángulo de rozamiento residual arcilla",   sheet_fr_residual),
        ],
    },
    {
        "nombre": "Parámetros Elásticos",
        "icono": "",
        "clase": "elasticidad",
        "hojas": [
            ("E → Módulo de elasticidad arenas",             sheet_e_arenas),
            ("E → Módulo de elasticidad arcillas",           sheet_e_arcillas),
            ("E → Módulo de elasticidad CTE",                sheet_e_cte),
            ("Kv — Módulo de balasto vertical",              sheet_kv),
            ("ν — Coeficiente de Poisson",                   sheet_poisson),
        ],
    },
]

total_hojas = sum(len(c["hojas"]) for c in CATEGORIAS)
total_interac = sum(1 for c in CATEGORIAS for n, _ in c["hojas"] if "Poisson" not in n)

c1, c2 = st.columns(2)
c1.metric("Hojas de correlaciones", total_hojas)
c2.metric("Con parámetros interactivos", total_interac)

st.divider()
st.subheader("Explorar por tabla")
st.caption(
    "Modifica los valores de la columna **Valor** para recalcular "
    "los resultados automáticamente en tiempo real."
)
st.write("")

# Motor de renderizado con casillas de exportación
for cat in CATEGORIAS:
    st.markdown(
        f'<div class="cat-banner cat-{cat["clase"]}">'
        f'{cat["icono"]}&nbsp;&nbsp;{cat["nombre"]}'
        f'</div>',
        unsafe_allow_html=True,
    )
    for nombre, fn in cat["hojas"]:
        with st.expander(f"  {nombre}"):
            fn()
            st.write("")
            st.checkbox(
                "📄 Incluir esta tabla en el informe (.docx)", 
                key=f"export_{nombre}"
            )
        st.write("")

st.divider()
st.caption("© 2026 · Tablas de correlaciones geotécnicas — _Visualización con Streamlit_")

# ── Sidebar con botón de descarga del informe Word ────────────────────────────
with st.sidebar:
    st.header("📄 Exportación")
    st.write("Selecciona las tablas que desees incluir usando las casillas de verificación de cada apartado.")
    st.write("---")
    
    informe_docx = generar_informe_word()
    
    st.download_button(
        label="Descargar Informe (.docx)",
        data=informe_docx,
        file_name="Anexo_Correlaciones_Geotecnicas.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary"
    )

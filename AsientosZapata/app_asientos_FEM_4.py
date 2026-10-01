import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL

# IMPORTACIÓN DESDE EL BACKEND (Sin la ecuación elástica)
from funciones_asientos import (
    OPENSEES_DISPONIBLE, ErrorMEF, holl_centro, calcular_steinbrenner,
    calcular_opensees_3d, sigma_v0, z_influencia_ec7, dimensiones_malla_3d
)

# ══════════════════════════════════════════════════════════════════════════
# INFORME WORD ESTÉTICO
# ══════════════════════════════════════════════════════════════════════════
def _fig_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    buf.seek(0)
    return buf

def tabla_comparativa(df_st, df_mef, con_cotas=False):
    """Comparativa por estrato. Si la tabla MEF no existe o no casa con la de
    Steinbrenner, la columna MEF se deja vacía en lugar de provocar un error."""
    cols = ["Capa"] + (["z Techo [m]", "z Base [m]"] if con_cotas else [])
    out = df_st[cols].copy()
    out["Δs Steinbrenner [mm]"] = df_st["Δs [mm]"].values
    if df_mef is not None and len(df_mef) == len(df_st):
        out["Δs OpenSees 3D [mm]"] = df_mef["Δs [mm]"].values
    else:
        out["Δs OpenSees 3D [mm]"] = "—"
    return out

def _add_styled_table(doc, df, title):
    if title:
        h = doc.add_heading(title, level=2)
        if h.runs:
            h.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    
    df = df.astype(str)
    table = doc.add_table(rows=1+len(df), cols=len(df.columns))
    table.style = 'Light Shading Accent 1' 
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    hdr_cells = table.rows[0].cells
    for i, column in enumerate(df.columns):
        hdr_cells[i].text = column
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for paragraph in hdr_cells[i].paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(8) 
                run.font.color.rgb = RGBColor(23, 54, 93) 
    
    for i, row in enumerate(df.itertuples(index=False)):
        row_cells = table.rows[i+1].cells
        for j, value in enumerate(row):
            row_cells[j].text = str(value)
            row_cells[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for paragraph in row_cells[j].paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(8)
    doc.add_paragraph()

def _body(doc, text, italic=False, gray=False, size=10, bold=False):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text)
    r.font.size = Pt(size); r.font.italic = italic; r.font.bold = bold
    if gray:
        r.font.color.rgb = RGBColor(89, 89, 89)
    return par

def _bullets(doc, items):
    for it in items:
        par = doc.add_paragraph(style='List Bullet')
        r = par.add_run(it); r.font.size = Pt(10)

def _h2(doc, text):
    h = doc.add_heading(text, level=2)
    if h.runs:
        h.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    return h

def _nota(doc, text):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text)
    r.font.size = Pt(10); r.font.bold = True
    r.font.color.rgb = RGBColor(192, 0, 0)
    return par

def generar_word(B, L, p, NF, z_max, zi, df_terreno, df_st, tot_st, 
                 df_mef, tot_mef, fig_bulbo_bytes, meta=None, s_adm=25.0):
    fecha = datetime.now().strftime("%d/%m/%Y — %H:%M")
    meta = meta or {}
    obra         = meta.get("obra") or "[Denominación de la obra]"
    peticionario = meta.get("peticionario") or "[Peticionario]"
    referencia   = meta.get("referencia") or "GEO-XXXX-ASN-01"
    autor        = meta.get("autor") or "Dpto. Geotecnia "
    revision     = meta.get("revision") or "00 — Emisión inicial"

    # --- Magnitudes derivadas para el informe ---
    s_st, s_mef = tot_st * 1000.0, tot_mef * 1000.0
    dif_mef_st = abs(s_mef - s_st) / max(abs(s_st), 1e-9) * 100.0
    s_gob = s_mef                      
    LIM_ELS = float(s_adm)             
    cumple_els = s_gob <= LIM_ELS
    ratio_els = s_gob / LIM_ELS

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2.5)
        sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)
        fp = sec.footer.paragraphs[0]
        fp.text = f"Memoria de Cálculo de Asientos · {referencia} · Generado el {fecha}"
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp.runs[0].font.size = Pt(8); fp.runs[0].font.color.rgb = RGBColor(128, 128, 128)

    style = doc.styles['Normal']; style.font.name = 'Calibri'; style.font.size = Pt(10)
    h1f = doc.styles['Heading 1'].font
    h1f.name = 'Calibri Light'; h1f.size = Pt(14); h1f.color.rgb = RGBColor(23, 54, 93); h1f.bold = True

    # ───────────────────────── PORTADA ─────────────────────────
    doc.add_paragraph(); doc.add_paragraph()
    pt = doc.add_paragraph(); pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = pt.add_run('MEMORIA DE CÁLCULO DE ASIENTOS')
    rt.bold = True; rt.font.size = Pt(24); rt.font.color.rgb = RGBColor(23, 54, 93)
    ps = doc.add_paragraph(); ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = ps.add_run('Cimentación superficial · Método Analítico y MEF 3D')
    rs.font.size = Pt(13); rs.font.color.rgb = RGBColor(89, 89, 89)
    doc.add_paragraph(); doc.add_paragraph()

    tid = doc.add_table(rows=6, cols=2); tid.style = 'Light Shading Accent 1'
    id_data = [('Obra / Proyecto', obra), ('Peticionario', peticionario),
               ('Referencia', referencia), ('Redactado por', autor),
               ('Fecha', fecha), ('Revisión', revision)]
    for i, (k, v) in enumerate(id_data):
        cs = tid.rows[i].cells
        cs[0].text = k; cs[1].text = str(v)
        cs[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cs[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if cs[0].paragraphs[0].runs:
            cs[0].paragraphs[0].runs[0].font.bold = True
    doc.add_page_break()

    # ───────────────── 1. OBJETO Y ALCANCE ─────────────────
    doc.add_heading('1. Objeto y alcance', level=1)
    _h2(doc, '1.1 Objeto')
    _body(doc, "El presente documento recoge el cálculo del asiento de una cimentación superficial rectangular "
               "sometida a carga vertical uniforme, mediante dos formulaciones independientes: el método analítico "
               "de Steinbrenner y un modelo tridimensional de elementos finitos (OpenSeesPy).")
    _h2(doc, '1.2 Alcance: asiento elástico / inmediato')
    _body(doc, "Ambos métodos parten de la teoría de la elasticidad lineal. En consecuencia, el resultado "
               "corresponde al ASIENTO ELÁSTICO (inmediato), producido en el momento de aplicación de la carga.")
    doc.add_page_break()

    # ───────────────── 2. NORMATIVA ─────────────────
    doc.add_heading('2. Normativa y referencias', level=1)
    _bullets(doc, [
        "CTE DB-SE-C «Seguridad estructural – Cimientos». Estados Límite de Servicio (asientos admisibles).",
        "UNE-EN 1997-1 (Eurocódigo 7), apartado 6.6.2: criterio de profundidad de influencia (Δσz ≤ 0,20·σ′v0).",
        "Holl (1940): incrementos de tensión bajo la esquina de un rectángulo cargado; tensiones bajo el centro por superposición de cuatro cuadrantes.",
        "Steinbrenner / Bowles: solución elástica aproximada del asiento de un estrato de espesor finito, basada en el campo de desplazamientos del semiespacio homogéneo.",
        "OpenSeesPy: biblioteca de elementos finitos; hexaedro de 8 nodos con formulación B-bar (bbarBrick).",
    ])
    doc.add_page_break()

    # ───────────────── 3. DATOS DE PARTIDA ─────────────────
    doc.add_heading('3. Datos de partida', level=1)
    _h2(doc, '3.1 Geometría, acciones y profundidades')
    t3 = doc.add_table(rows=6, cols=2); t3.style = 'Light Shading Accent 1'
    d3 = [('Dimensiones en planta (B × L)', f'{B:.2f} m × {L:.2f} m'),
          ('Presión neta de trabajo (p)', f'{p:.1f} kPa'),
          ('Nivel freático (NF)', f'{NF:.1f} m'),
          ('Profundidad de influencia (z_i, EC7)', f'{zi:.2f} m'),
          ('Profundidad de corte evaluada (z_max)', f'{z_max:.1f} m'),
          ('Criterio tensional', 'Centro de la zapata')]
    for i, (k, v) in enumerate(d3):
        cs = t3.rows[i].cells; cs[0].text = k; cs[1].text = v
        cs[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER; cs[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if cs[0].paragraphs[0].runs: cs[0].paragraphs[0].runs[0].font.bold = True
    _body(doc, "La presión p es la presión NETA de trabajo (descontada la sobrecarga de tierras retirada). "
               "Los asientos se evalúan en combinación de servicio (ELS), no con acciones mayoradas.", gray=True, size=9)
    doc.add_paragraph()
    _add_styled_table(doc, df_terreno, '3.2 Estratigrafía del perfil geotécnico')
    doc.add_page_break()

    # ───────────────── 4. HIPÓTESIS Y MODELO ─────────────────
    doc.add_heading('4. Hipótesis y modelo de cálculo', level=1)
    _h2(doc, '4.1 Base común: elasticidad lineal')
    _body(doc, "Ambos métodos asumen un terreno elástico lineal, isótropo, caracterizado por (E, ν) en cada estrato.")
    _h2(doc, '4.2 Hipótesis de cada método')
    _bullets(doc, [
        "Steinbrenner: solución aproximada. El asiento de cada estrato se obtiene con los factores φ₁ y φ₂ suponiendo la distribución de tensiones del semiespacio homogéneo; no recoge la redistribución de tensiones debida al contraste de rigidez entre estratos ni la presencia de la base rígida.",
        "MEF 3D (OpenSees): resolución del continuo tridimensional discreto con hexaedros bbarBrick, cuarto de dominio por doble simetría y base rígida en z_max. Sí recoge la interacción entre estratos.",
        "Ambos métodos proporcionan el asiento del centro de una cimentación flexible, sin corrección por rigidez ni por empotramiento.",
    ])
    doc.add_page_break()

    # ───────────────── 5. PROFUNDIDAD DE INFLUENCIA ─────────────────
    doc.add_heading('5. Profundidad de influencia (EC7)', level=1)
    _body(doc, "La profundidad de cálculo se acota mediante el criterio del Eurocódigo 7: se considera despreciable "
               "la contribución al asiento por debajo de la cota z_i en la que el incremento de tensión vertical cae "
               "por debajo del 20 % de la tensión efectiva geoestática:")
    _body(doc, "Δσz(z_i) ≤ 0,20 · σ′v0(z_i)", bold=True)
    _body(doc, f"Para el caso analizado resulta z_i = {zi:.2f} m, adoptándose una profundidad de corte z_max = {z_max:.1f} m.")
    doc.add_page_break()

    # ───────────────── 6. MÉTODO 1 — STEINBRENNER ─────────────────
    doc.add_heading('6. Método 1 — Steinbrenner', level=1)
    _body(doc, "El asiento de cada estrato se obtiene como diferencia entre los desplazamientos del semiespacio "
               "homogéneo (w) en su techo y en su base, ambos evaluados con el módulo E y el coeficiente ν del propio "
               "estrato. Los valores w_techo y w_base son auxiliares; solo su diferencia Δs tiene significado físico.")
    _add_styled_table(doc, df_st, '6.1 Cálculos intermedios y asiento por estrato')
    tot1 = doc.add_paragraph(); tot1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot1.add_run(f'Asiento total Steinbrenner: {s_st:.3f} mm'); r.bold = True; r.font.color.rgb = RGBColor(23, 54, 93)
    doc.add_page_break()

    # ───────────────── 7. MÉTODO 2 — MEF 3D ─────────────────
    doc.add_heading('7. Método 2 — MEF 3D (OpenSees)', level=1)
    _h2(doc, '7.1 Descripción del modelo')
    _body(doc, "El terreno se discretiza como un medio continuo tridimensional con hexaedros de 8 nodos de formulación "
               "B-bar (bbarBrick), adecuada para coeficientes de Poisson próximos a 0,5. Se modela un cuarto del dominio "
               "aprovechando la doble simetría del problema.")
    _h2(doc, '7.2 Condiciones de contorno y base rígida')
    _body(doc, "En los planos de simetría (x=0, y=0) y en las fronteras laterales de campo lejano se impide el "
               "desplazamiento normal dejando libre el vertical. En z_max se empotran los tres grados de libertad.")
    _h2(doc, '7.3 Reparto de cargas')
    _body(doc, "La presión se reparte en fuerzas nodales mediante áreas tributarias, equivalentes a las fuerzas "
               "consistentes para hexaedros lineales. El asiento se lee en el eje vertical que pasa por el centro de la "
               "zapata.")
    _add_styled_table(doc, df_mef, '7.4 Asiento por estrato (eje central)')
    tot3 = doc.add_paragraph(); tot3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot3.add_run(f'Asiento total MEF 3D: {s_mef:.3f} mm'); r.bold = True; r.font.color.rgb = RGBColor(192, 0, 0)
    doc.add_page_break()

    # ───────────────── 8. RESULTADOS Y COMPARATIVA ─────────────────
    doc.add_heading('8. Resultados y comparativa', level=1)
    _h2(doc, '8.1 Asientos totales por método')
    tr = doc.add_table(rows=1, cols=2); tr.style = 'Light Shading Accent 1'; tr.alignment = WD_TABLE_ALIGNMENT.CENTER
    cc = tr.rows[0].cells
    for c in cc: c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for cell, (nom, val, col) in zip(cc, [('Steinbrenner', s_st, RGBColor(23, 54, 93)),
                                          ('OpenSees 3D', s_mef, RGBColor(192, 0, 0))]):
        pp = cell.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ra = pp.add_run(nom + '\n'); ra.font.size = Pt(11); ra.bold = True; ra.font.color.rgb = RGBColor(89, 89, 89)
        rb = pp.add_run(f'{val:.3f} mm'); rb.font.size = Pt(16); rb.bold = True; rb.font.color.rgb = col
    doc.add_paragraph()
    
    _h2(doc, '8.2 Comparativa por estrato')
    _add_styled_table(doc, tabla_comparativa(df_st, df_mef), '')
    
    _h2(doc, '8.3 Interpretación')
    _body(doc, f"La diferencia entre el asiento MEF 3D ({s_mef:.2f} mm) y el de Steinbrenner ({s_st:.2f} mm) es del "
               f"{dif_mef_st:.1f} % respecto a este último.")
    _body(doc, "En perfiles estratificados es esperable cierta diferencia entre ambos métodos y no constituye por sí "
               "misma un error: Steinbrenner supone la distribución de tensiones del semiespacio homogéneo, mientras "
               "que el MEF recoge la concentración o el reparto de tensiones debido al contraste de rigidez entre "
               "estratos y el efecto de la base rígida. Diferencias elevadas en perfiles casi homogéneos aconsejan "
               "revisar la malla y la extensión lateral del dominio.")
    doc.add_page_break()

    # ───────────────── 9. VALIDACIÓN DEL MEF ─────────────────
    doc.add_heading('9. Validación del MEF', level=1)
    _body(doc, "El código de cálculo dispone de pruebas automáticas que verifican: (a) las funciones de Steinbrenner "
               "frente a la integración numérica de la solución de Boussinesq; (b) que el asiento total de cada método "
               "coincide con la suma de los asientos por estrato; y (c) la concordancia del MEF 3D con Steinbrenner en "
               "un estrato homogéneo de referencia, dentro de la tolerancia fijada en dichas pruebas.")
    _body(doc, f"Parámetros del modelo MEF de este cálculo: tamaño de malla {meta.get('mesh', '—')} m, extensión "
               f"lateral ×{meta.get('factor_dominio', '—')} (B/2, L/2), base rígida en z_max = {z_max:.2f} m.",
          gray=True, size=9)
    doc.add_page_break()

    # ───────────────── 10. COMPROBACIÓN ELS ─────────────────
    doc.add_heading('10. Comprobación en Estado Límite de Servicio', level=1)
    _body(doc, "Se compara el asiento total obtenido con el asiento general admisible adoptado. "
               f"El valor adoptado para esta comprobación es de {LIM_ELS:.0f} mm.")
    te = doc.add_table(rows=2, cols=4); te.style = 'Light Shading Accent 1'; te.alignment = WD_TABLE_ALIGNMENT.CENTER
    els_rows = [('Comprobación', 'Obtenido', 'Admisible', 'Veredicto'),
                ('Asiento total (MEF 3D)', f'{s_gob:.2f} mm', f'{LIM_ELS:.0f} mm', 'CUMPLE' if cumple_els else 'REVISAR')]
    for i, rowv in enumerate(els_rows):
        cs = te.rows[i].cells
        for j, v in enumerate(rowv):
            cs[j].text = v; cs[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for par in cs[j].paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for rr in par.runs:
                    rr.font.size = Pt(9)
                    if i == 0: rr.font.bold = True; rr.font.color.rgb = RGBColor(23, 54, 93)
    doc.add_paragraph()
    _body(doc, f"El asiento absoluto obtenido ({s_gob:.2f} mm) supone un aprovechamiento del {ratio_els*100:.0f} % del "
               f"asiento admisible adoptado ({LIM_ELS:.0f} mm).", gray=True, size=9)
    doc.add_page_break()

    # ───────────────── 11. ZONA DE INFLUENCIA DE LA CARGA ─────────────────
    doc.add_heading('11. Zona de influencia de la carga de cimentación', level=1)
    pf = doc.add_paragraph(); pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.add_run().add_picture(fig_bulbo_bytes, width=Cm(13))
    nota = doc.add_paragraph(f'Evolución de tensiones bajo el centro de la zapata (p={p:.1f} kPa, B={B:.2f} m, '
                             f'L={L:.2f} m). Criterio EC7: 0,20·σ′v0. Tensiones horizontales de Holl para ν = 0,5.')
    nota.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nota.runs[0].font.size = Pt(9); nota.runs[0].font.italic = True; nota.runs[0].font.color.rgb = RGBColor(128, 128, 128)

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN E INTERFAZ STREAMLIT
# ══════════════════════════════════════════════════════════════════════════
def reset_calculo():
    st.session_state.calculo_realizado = False
    if st.session_state.get("informe_generado", False):
        st.session_state.informe_stale = True 
    st.session_state.informe_generado = False
    st.session_state.word_buf = None

if 'calculo_realizado' not in st.session_state:
    st.session_state.calculo_realizado = False
if 'informe_generado' not in st.session_state:
    st.session_state.informe_generado = False
if 'informe_stale' not in st.session_state:
    st.session_state.informe_stale = False
if 'word_buf' not in st.session_state:
    st.session_state.word_buf = None

if 'df_terreno' not in st.session_state:
    st.session_state.df_terreno = pd.DataFrame({
        "Descripción":           ["Arcilla 1",  "Arcilla 2",  "Arcilla 3"],
        "Espesor (m)":           [1.5,         3.0,        5.0],
        "E (kPa)":               [10000.0,     15000.0,     40000.0],
        "nu":                    [0.30,         0.45,       0.25],
        "Peso Esp. (kN/m³)":     [18.0,         19.0,       21.0],
        "Peso Esp. Sat (kN/m³)": [20.0,         20.0,       22.0],
    })

st.set_page_config(page_title="Cálculo Asientos V13 · MEF 3D", layout="wide", page_icon="🏗️")
st.sidebar.title("Navegación")
modo = st.sidebar.radio("Vista:", ["🧮 Panel de Cálculo", "📋 Modelo Steinbrenner", "🌐 Modelo OpenSees", "📉 Bulbo de Presiones", "📐 Asientos Admisibles", "📖 Fundamento Teórico"])

st.sidebar.markdown("---")
st.sidebar.header("📥 Datos de Entrada")
B  = st.sidebar.number_input("Ancho (B) [m]", min_value=0.1, value=2.0, step=0.1, on_change=reset_calculo)
L  = st.sidebar.number_input("Longitud (L) [m]", min_value=0.1, value=3.0, step=0.1, on_change=reset_calculo)
p  = st.sidebar.number_input("Presión neta (p) [kPa]", min_value=1.0, value=150.0, step=10.0, on_change=reset_calculo)
NF = st.sidebar.number_input("Nivel Freático [m]", min_value=0.0, value=100.0, step=0.5, on_change=reset_calculo)

if L < B: B, L = L, B; st.sidebar.warning("⚠️ L<B: valores intercambiados.")
# Evitamos problemas con filas vacías en la UI
df_clean_ui = st.session_state.df_terreno.dropna(subset=["Espesor (m)"])
espesor_total = max(float(pd.to_numeric(df_clean_ui["Espesor (m)"]).sum()), 0.1)
zi = z_influencia_ec7(p, B, L, st.session_state.df_terreno, NF)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Profundidad de Cálculo")
z_max_user = st.sidebar.number_input("Profundidad de corte (z_max) [m]", min_value=0.1, max_value=espesor_total, value=float(min(round(zi, 1), espesor_total)), step=0.1, on_change=reset_calculo)

st.sidebar.markdown("---")
st.sidebar.subheader("✅ Comprobación de Servicio (ELS)")
asiento_adm = st.sidebar.number_input(
    "Asiento admisible [mm]", min_value=1.0, value=25.0, step=1.0, on_change=reset_calculo,
    help="Asiento total máximo admisible. Consulta la pestaña «📐 Asientos Admisibles» para referencias.")

# ── CONTROLES OPENSEES 3D ──
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parámetros OpenSees MEF 3D")
if not OPENSEES_DISPONIBLE: st.sidebar.warning("⚠️ Módulo OpenSeesPy no detectado.")
factor_dominio = st.sidebar.slider("Extensión del dominio (×B/2, ×L/2)", min_value=3.0, max_value=8.0, value=5.0, step=1.0, on_change=reset_calculo)
mesh_3d = st.sidebar.number_input("Tamaño malla MEF 3D [m]", min_value=0.25, max_value=1.0, value=0.5, step=0.05, on_change=reset_calculo)

if factor_dominio < 4:
    st.sidebar.warning("Con factor < 4 las fronteras laterales rigidizan el modelo y subestiman el asiento.")

nodos_totales, elementos_totales = dimensiones_malla_3d(
    B, L, st.session_state.df_terreno, z_max_user, mesh_3d, factor_dominio)

if nodos_totales < 15000:
    st.sidebar.success(f"🟢 **Malla ligera:** {nodos_totales:,} nodos · {elementos_totales:,} elem.")
elif nodos_totales < 50000:
    st.sidebar.warning(f"🟡 **Malla densa:** {nodos_totales:,} nodos. El 3D es más pesado que el 2D.")
else:
    st.sidebar.error(f"🔴 **Malla pesada:** {nodos_totales:,} nodos. Puede tardar bastante.")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 Calcular", type="primary", width="stretch"):
    tot_st, df_st = calcular_steinbrenner(p, B, L, st.session_state.df_terreno, z_max_user)
    try:
        with st.spinner("Resolviendo el modelo MEF 3D…"):
            tot_mef, df_mef = calcular_opensees_3d(p, B, L, st.session_state.df_terreno, z_max_user,
                                                   mesh_3d, factor_dominio)
        st.session_state.mef_ok, st.session_state.mef_error = True, None
    except ErrorMEF as e:
        tot_mef, df_mef = None, None
        st.session_state.mef_ok, st.session_state.mef_error = False, str(e)

    st.session_state.tot_st, st.session_state.df_st = tot_st, df_st
    st.session_state.tot_mef, st.session_state.df_mef = tot_mef, df_mef
    st.session_state.calc_params = {"mesh": mesh_3d, "factor_dominio": factor_dominio}
    st.session_state.calculo_realizado = True

    if st.session_state.get("informe_generado", False):
        st.session_state.informe_stale = True
    st.session_state.informe_generado = False
    st.session_state.word_buf = None

st.sidebar.markdown("---")
st.sidebar.subheader("🗎 Documentación")

with st.sidebar.expander("🗂️ Identificación del informe"):
    meta_obra = st.text_input("Obra / Proyecto", value="")
    meta_peti = st.text_input("Peticionario", value="")
    meta_ref  = st.text_input("Referencia", value="GEO-XXXX-ASN-01")
    meta_autor = st.text_input("Autor", value="Dpto. Geotecnia")
meta_informe = {"obra": meta_obra, "peticionario": meta_peti, "referencia": meta_ref, "autor": meta_autor}

if st.session_state.get("informe_stale", False):
    st.sidebar.warning("⚠️ Los datos han cambiado. **Recalcula** y vuelve a **generar el informe**.")

if not st.session_state.calculo_realizado:
    if not st.session_state.get("informe_stale", False):
        st.sidebar.info("Ejecuta el cálculo para poder generar el informe.")
elif not st.session_state.get("mef_ok", False):
    st.sidebar.error("El cálculo MEF no se ha ejecutado: no se puede generar el informe ni emitir la comprobación ELS.")
else:
    if st.sidebar.button("📝 Generar informe", width="stretch"):
        with st.spinner("Generando memoria de cálculo…"):
            z_vals = np.linspace(0.05, espesor_total, 200)
            sz_v, sx_v, sy_v, sv0_v = [], [], [], []
            for z in z_vals:
                sz, sx, sy = holl_centro(p, B, L, z)
                sz_v.append(sz); sx_v.append(sx); sy_v.append(sy)
                sv0_v.append(sigma_v0(z, st.session_state.df_terreno, NF) * 0.20)
            fig_b, ax_b = plt.subplots(figsize=(5, 7))
            ax_b.plot(sz_v, z_vals, label=r"Vertical $\Delta\sigma_z$", color='red', lw=2)
            ax_b.plot(sx_v, z_vals, label=r"Horiz. Trans. $\Delta\sigma_x$ ($\nu$=0,5)", color='blue', ls='--')
            ax_b.plot(sy_v, z_vals, label=r"Horiz. Long. $\Delta\sigma_y$ ($\nu$=0,5)", color='purple', ls='-.')
            ax_b.plot(sv0_v, z_vals, label=r"$0.20\,\sigma'_{v0}$ (EC7)", color='green', lw=2)
            ax_b.legend(fontsize=8, loc='lower right')
            ax_b.set_ylim(espesor_total, 0); ax_b.set_xlim(left=0)
            ax_b.set_xlabel("Tensión (kPa)"); ax_b.set_ylabel("Profundidad z (m)")
            ax_b.set_title("Bulbo de presiones")
            ax_b.grid(True, linestyle=':', alpha=0.4)
            ax_b.spines[['top', 'right']].set_visible(False)
            plt.tight_layout()
            fig_bulbo_bytes = _fig_bytes(fig_b); plt.close(fig_b)

            st.session_state.word_buf = generar_word(
                B, L, p, NF, z_max_user, zi, st.session_state.df_terreno,
                st.session_state.df_st, st.session_state.tot_st,
                st.session_state.df_mef, st.session_state.tot_mef, fig_bulbo_bytes,
                meta={**meta_informe, **st.session_state.get("calc_params", {})}, s_adm=asiento_adm)
        st.session_state.informe_generado = True
        st.session_state.informe_stale = False
        st.sidebar.success("✅ Informe generado.")

if st.session_state.get("informe_generado", False) and st.session_state.get("word_buf") is not None:
    st.sidebar.download_button("⬇️ Descargar informe Word",
                               data=st.session_state.word_buf,
                               file_name="informe_comparativo.docx",
                               width="stretch")

# ══════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
st.title("🏗️ Cálculo de Asientos de cimentaciones rectangulares")
st.markdown("**Herramienta académica sin testear**")

if modo == "🧮 Panel de Cálculo":
    st.header("1. Estratigrafía del Terreno")
    df_edit = st.data_editor(st.session_state.df_terreno, num_rows="dynamic", width="stretch")
    if not df_edit.equals(st.session_state.df_terreno):
        st.session_state.df_terreno = df_edit
        if st.session_state.get("informe_generado", False):
            st.session_state.informe_stale = True
        st.session_state.calculo_realizado = False
        st.session_state.informe_generado = False
        st.session_state.word_buf = None
        st.rerun()

    st.markdown("---")
    st.header("2. Resultados y Comparativa")
    if not st.session_state.calculo_realizado: st.info("👈 Pulsa Calcular.")
    else:
        mef_ok = st.session_state.get("mef_ok", False)
        c1, c2, c3 = st.columns(3)
        c1.metric("🔵 Steinbrenner", f"{st.session_state.tot_st*1000:.3f} mm")
        if mef_ok:
            c2.metric("🔴 OpenSees 3D", f"{st.session_state.tot_mef*1000:.3f} mm")
            dif = abs(st.session_state.tot_st - st.session_state.tot_mef)*1000
            pct = abs(st.session_state.tot_st - st.session_state.tot_mef)/max(abs(st.session_state.tot_st), 1e-9)*100
            c3.metric("📊 Dif (ST vs MEF)", f"{dif:.3f} mm", f"{pct:.1f}%")

            s_gob_mm = st.session_state.tot_mef * 1000
            aprov = s_gob_mm / asiento_adm * 100 if asiento_adm > 0 else 0
            if s_gob_mm <= asiento_adm:
                st.success(f"✅ **CUMPLE** — Asiento gobernante (MEF 3D) {s_gob_mm:.2f} mm ≤ admisible "
                           f"{asiento_adm:.0f} mm  ·  aprovechamiento {aprov:.0f} %.")
            else:
                st.error(f"⚠️ **REVISAR** — Asiento gobernante (MEF 3D) {s_gob_mm:.2f} mm > admisible "
                         f"{asiento_adm:.0f} mm  ·  aprovechamiento {aprov:.0f} %.")
        else:
            c2.metric("🔴 OpenSees 3D", "—")
            c3.metric("📊 Dif (ST vs MEF)", "—")
            st.error(f"⛔ **ELS NO EVALUADO** — {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')} "
                     "El asiento de Steinbrenner se muestra solo a título informativo.")

        st.dataframe(tabla_comparativa(st.session_state.df_st, st.session_state.df_mef, con_cotas=True),
                     width="stretch", hide_index=True)

elif modo == "📐 Asientos Admisibles":
    st.header("📐 Asientos Generales Admisibles")
    st.markdown("Tabla de referencia para fijar el **asiento admisible** en la barra lateral, según el tipo de "
                "edificio y la naturaleza del terreno. El valor elegido se emplea en la comprobación ELS y en el informe.")

    df_adm = pd.DataFrame({
        "Características del edificio": [
            "Obras de carácter monumental",
            "Edificios con estructura de H.A. de gran rigidez",
            "Edificios con estructura de H.A. de pequeña rigidez · Estructuras metálicas hiperestáticas · Edificios con muros de fábrica",
            "Estructuras metálicas isostáticas · Estructuras de madera · Estructuras provisionales",
        ],
        "Terreno sin cohesión [mm]": ["12", "35", "50", ">50 (con comprobación)"],
        "Terreno cohesivos [mm]": ["25", "50", "75", ">75 (con comprobación)"],
    })
    st.dataframe(df_adm, width="stretch", hide_index=True)

    st.info(f"**Asiento admisible fijado actualmente:** {asiento_adm:.0f} mm  "
            f"(se edita en la barra lateral, apartado «Comprobación de Servicio»).")

    st.markdown("**Notas:**")
    st.markdown(
        "- *Sin cohesión* = terrenos granulares (arenas, gravas); *cohesivos* = terrenos cohesivos (arcillas, limos). "
        "Los límites admisibles son mayores en terrenos coherentes.\n"
        "- La última fila (*«con comprobación»*) no es un límite cerrado: indica que se admiten asientos mayores "
        "siempre que se justifique que la estructura los tolera.\n"
        "- En perfiles multicapa mixtos, la elección del tipo de terreno y de edificio es criterio del proyectista: "
        "la aplicación no lo infiere automáticamente.")
    st.caption("Fuente: tabla de asientos generales admisibles (Jiménez Salas), de uso habitual en la práctica geotécnica.")



elif modo == "📋 Modelo Steinbrenner":
    st.header("📋 Detalle Método Steinbrenner")
    st.markdown(r"Cálculo capa a capa integrando las funciones de influencia $\phi_1$ y $\phi_2$.")
    
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Calcula primero en el panel izquierdo.")
    else:
        df_st = st.session_state.df_st
        st.markdown("##### 🔼 Valores en el Techo")
        st.caption("w = desplazamiento del semiespacio homogéneo con el E y ν del propio estrato. "
                   "Es un valor auxiliar: solo la diferencia Δs = w_techo − w_base es un asiento.")
        st.dataframe(df_st[["Capa","z Techo [m]","m_techo","φ1_techo","φ2_techo","w_techo [mm]"]],
                     width="stretch", hide_index=True)
        st.markdown("##### 🔽 Valores en la Base")
        st.dataframe(df_st[["Capa","z Base [m]","m_base","φ1_base","φ2_base","w_base [mm]"]],
                     width="stretch", hide_index=True)
        st.markdown("##### 📊 Asiento por estrato")
        st.dataframe(df_st[["Capa","Δs [mm]"]], width="stretch", hide_index=True)
        st.metric("🔵 Asiento Total Steinbrenner",
                  f"{st.session_state.tot_st*1000:.3f} mm")

elif modo == "🌐 Modelo OpenSees":
    st.header("🌐 Modelo de Elementos Finitos (OpenSees 3D)")
    st.markdown("Medio continuo tridimensional discretizado por el Método de los Elementos Finitos.")

    st.subheader("1. Concepto y Datos de Entrada")
    st.markdown("* **Materiales:** `ElasticIsotropic` ($E$, $\\nu$).\n"
                "* **Geometría:** hexaedros de 8 nodos con formulación B-bar (`bbarBrick`) en un cuarto del dominio.\n"
                "* **Carga:** presión repartida en fuerzas nodales por áreas tributarias (equivalentes a las consistentes).")

    st.subheader("2. Condiciones de Contorno")
    col1, col2 = st.columns(2)
    with col1:
        st.info("📏 Simetría y campo lejano")
        st.markdown(r"Desplazamiento normal impedido, vertical libre.")
    with col2:
        st.info("⬇️ Base")
        st.markdown(r"En $z_{max}$ se empotran los tres grados de libertad.")

    st.markdown("---")
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo.")
    elif not st.session_state.get("mef_ok", False):
        st.error(f"⛔ {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')}")
    else:
        df_mef = st.session_state.df_mef
        st.markdown("##### 📍 Asiento por estrato (eje central)")
        st.dataframe(df_mef[["Capa", "Δs [mm]"]], width="stretch", hide_index=True)
        st.metric("🔴 Asiento Total OpenSees 3D", f"{st.session_state.tot_mef*1000:.3f} mm")

elif modo == "📉 Bulbo de Presiones":
    st.header("Bulbo de Presiones y Zona de Influencia")
    st.markdown(r"Tensiones de Holl bajo el centro ($\times 4$ superposición $B/2 \times L/2$). "
                r"Las tensiones horizontales corresponden a $\nu = 0{,}5$.")
    col1, col2 = st.columns([1, 3])
    with col1:
        z_gr = st.slider("Profundidad máxima [m]:", 1.0, espesor_total, min(espesor_total, 15.0), 0.5)
        st.metric("📐 z_i (EC7)", f"{zi:.2f} m")
    with col2:
        z_vals = np.linspace(0.05, z_gr, 200)
        sz_v, sx_v, sy_v, sv0_v, umb20_v = [], [], [], [], []
        for z in z_vals:
            sz, sx, sy = holl_centro(p, B, L, z)
            sv = sigma_v0(z, df_clean_ui, NF)
            sz_v.append(sz); sx_v.append(sx); sy_v.append(sy)
            sv0_v.append(sv); umb20_v.append(0.20*sv)

        fig, ax = plt.subplots(figsize=(9, 7))
        ax.plot(sz_v,   z_vals, label=r"Vertical $\Delta\sigma_z$",           color='red',         lw=2)
        ax.plot(sx_v,   z_vals, label=r"Horiz. Trans. $\Delta\sigma_x$ ($\nu$=0,5)", color='blue',   ls='--')
        ax.plot(sy_v,   z_vals, label=r"Horiz. Long. $\Delta\sigma_y$ ($\nu$=0,5)",  color='purple', ls='-.')
        ax.plot(sv0_v,  z_vals, label=r"$\sigma'_{v0}$ (tensión efect.)",     color='saddlebrown', ls=':', lw=1.5)
        ax.plot(umb20_v,z_vals, label=r"$0.20\,\sigma'_{v0}$ (criterio EC7)", color='green',       lw=2)
        if zi <= z_gr:
            ax.axhline(y=zi, color='orange', ls='--', lw=1.5, label=f'z_i = {zi:.2f} m')
        if NF < z_gr and NF < 100.0:
            ax.axhline(y=NF, color='deepskyblue', ls='-.', lw=1.2)
        ax.set_ylim(z_gr, 0); ax.set_xlim(left=0)
        ax.set_xlabel("Tensión (kPa)"); ax.set_ylabel("Profundidad z (m)")
        ax.legend(loc='lower right'); ax.grid(True, ls=':')
        st.pyplot(fig); plt.close(fig)

elif modo == "📖 Fundamento Teórico":
    st.header("Fundamento Teórico")

    st.subheader("🔵 Método 1 — Steinbrenner")
    st.markdown("Desplazamiento vertical a profundidad z bajo la esquina de un rectángulo cargado, en un "
                "semiespacio elástico homogéneo, expresado con los factores geométricos φ₁ y φ₂:")
    st.latex(r"w(z) = \frac{p \cdot B}{E}\left[(1-\nu^2)\phi_1 - (1-\nu-2\nu^2)\phi_2\right]")
    st.latex(r"\phi_1 = \frac{1}{\pi}\left[\ln\frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} + n\ln\frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}}\right]")
    st.latex(r"\phi_2 = \frac{m}{2\pi}\arctan\frac{n}{m\sqrt{1+m^2+n^2}}")
    st.markdown(r"Bajo el centro se aplica a cuatro cuadrantes $B/2 \times L/2$ (por eso $m = 2z/B$), con "
                r"$n = L/B$. El asiento de cada estrato, evaluando $w$ con el $E$ y $\nu$ del propio estrato:")
    st.latex(r"\Delta s_i = 4\,\left[w(z_{techo}) - w(z_{base})\right]")
    st.info("Steinbrenner es una solución aproximada: supone la distribución de tensiones del semiespacio "
            "homogéneo y no recoge la redistribución por contraste de rigidez entre estratos ni la base rígida. "
            "El MEF 3D sí las recoge, por lo que en perfiles estratificados es normal que ambos difieran.")

    st.markdown("---")
    st.subheader("📐 Criterio de Profundidad de Influencia (EC7)")
    st.latex(r"\Delta\sigma_z(z_i) \leq 0.20\,\sigma'_{v0}(z_i)")

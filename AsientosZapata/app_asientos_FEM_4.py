import io
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
import streamlit as st
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

import funciones_asientos as fa
from funciones_asientos import (
    OPENSEES_DISPONIBLE, ErrorMEF, holl_centro, sigma_v0
)

AZUL, ROJO, GRIS = RGBColor(33, 100, 175), RGBColor(192, 0, 0), RGBColor(89, 89, 89)


<<<<<<< HEAD
from funciones_asientos import (
    OPENSEES_DISPONIBLE, MEFError, NU_MAX, MAX_NODOS_MEF, TIPOS_SUELO,
    TENSION_CONSISTENTE, TENSION_HOLL, CRITERIOS_GOBERNANTE,
    holl_centro, calcular_steinbrenner, calcular_ec68, calcular_opensees_3d,
    sigma_v0, z_influencia_ec7, validar_estratigrafia, estimar_malla_3d,
    asiento_gobernante, estratos_cohesivos,
)


# ══════════════════════════════════════════════════════════════════════════
# INFORME WORD ESTÉTICO
# ══════════════════════════════════════════════════════════════════════════
=======
# ══════════════════════════════════════════════════════════════════════════
# POSTPROCESO
# ══════════════════════════════════════════════════════════════════════════
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


def tabla_puntos(puntos_st, res_mef):
    filas = []
    for nombre, s_st in puntos_st.items():
        filas.append({"Punto": nombre,
                      "Steinbrenner [mm]": round(s_st, 2),
                      "OpenSees 3D [mm]": round(res_mef.puntos[nombre], 2) if res_mef else "—"})
    return pd.DataFrame(filas)


# ══════════════════════════════════════════════════════════════════════════
# FIGURAS
# ══════════════════════════════════════════════════════════════════════════
def fig_bulbo(p, B, L, df, NF, D, z_hasta, zi=None, figsize=(9, 7)):
    z_vals = np.linspace(0.05, z_hasta, 200)
    sz_v, sx_v, sy_v, sv0_v = [], [], [], []
    for z in z_vals:
        sz, sx, sy = holl_centro(p, B, L, z)
        sz_v.append(sz); sx_v.append(sx); sy_v.append(sy)
        sv0_v.append(sigma_v0(D + z, df, NF))
    sv0_v = np.array(sv0_v)
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(sz_v, z_vals, label=r"Vertical $\Delta\sigma_z$", color='red', lw=2)
    ax.plot(sx_v, z_vals, label=r"Horiz. Trans. $\Delta\sigma_x$ ($\nu$=0,5)", color='blue', ls='--')
    ax.plot(sy_v, z_vals, label=r"Horiz. Long. $\Delta\sigma_y$ ($\nu$=0,5)", color='purple', ls='-.')
    ax.plot(sv0_v, z_vals, label=r"$\sigma'_{v0}$ (tensión efect.)", color='saddlebrown', ls=':', lw=1.5)
    ax.plot(0.20 * sv0_v, z_vals, label=r"$0.20\,\sigma'_{v0}$ (criterio EC7)", color='green', lw=2)
    if zi is not None and zi <= z_hasta:
        ax.axhline(y=zi, color='orange', ls='--', lw=1.5, label=f'z_i = {zi:.2f} m')
    if D < NF < D + z_hasta and NF < 100.0:
        ax.axhline(y=NF - D, color='deepskyblue', ls='-.', lw=1.2, label='Nivel freático')
    ax.set_ylim(z_hasta, 0); ax.set_xlim(left=0)
    ax.set_xlabel("Tensión (kPa)"); ax.set_ylabel("Profundidad bajo la cota de apoyo z (m)")
    ax.legend(loc='lower right', fontsize=8); ax.grid(True, ls=':')
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def fig_perfiles(ci, perf_st, res_mef):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, eje, medio in [(axes[0], "x", ci["B"] / 2), (axes[1], "y", ci["L"] / 2)]:
        c_st, s_st = perf_st[eje]
        ax.axvspan(0, medio, color='0.9', label='Zapata')
        ax.plot(c_st, s_st, color='tab:blue', lw=2, label='Steinbrenner')
        if res_mef is not None:
            pm = res_mef.perfil_x if eje == "x" else res_mef.perfil_y
            ax.plot(pm.iloc[:, 0], pm["s [mm]"], color='tab:red', lw=1.5, ls='--', marker='.', ms=4,
                    label='OpenSees 3D')
        ax.set_xlabel(f"{eje} [m] (desde el centro)")
        ax.set_title("Eje transversal (según B)" if eje == "x" else "Eje longitudinal (según L)", fontsize=10)
        ax.grid(True, ls=':'); ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_ylabel("Asiento a la cota de apoyo [mm]")
    axes[0].invert_yaxis()
    axes[1].legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    return fig


def fig_malla(ci, mp):
    malla = fa.construir_malla_3d(ci["B"], ci["L"], ci["df"], ci["z_max"], mp["tamaño_malla"],
                                  mp["factor_dominio"], mp["factor_prof"], ci["D"], mp["graduada"],
                                  mp["ratio"], mp["tamaño_max"])
    fig, ax = plt.subplots(figsize=(9, 5))
    x, z = malla.x, malla.z
    for i in range(len(x) - 1):
        for k in range(len(z) - 1):
            if malla.activo[i, 0, k]:
                col = plt.cm.Pastel1((malla.mat_elem[k] - 1) % 9)
                ax.add_patch(Rectangle((x[i], z[k + 1]), x[i + 1] - x[i], z[k] - z[k + 1],
                                       facecolor=col, edgecolor='0.35', lw=0.4))
    ax.plot([0, ci["B"] / 2], [-ci["D"], -ci["D"]], color='red', lw=3, label='Zapata (B/2)')
    ax.set_xlim(0, x[-1]); ax.set_ylim(z[-1], 0); ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel("x [m]"); ax.set_ylabel("Cota [m]")
    ax.set_title(f"Sección y = 0 de la malla · {malla.n_nodos:,} nodos · {malla.n_elementos:,} elementos",
                 fontsize=10)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    return fig


>>>>>>> refs/remotes/origin/main
def _fig_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


# ══════════════════════════════════════════════════════════════════════════
# INFORME WORD
# ══════════════════════════════════════════════════════════════════════════
def _add_styled_table(doc, df, title):
    if title:
        _h2(doc, title)
    df = df.astype(str)
    table = doc.add_table(rows=1 + len(df), cols=len(df.columns))
    table.style = 'Light Shading Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, column in enumerate(df.columns):
        cell = table.rows[0].cells[i]
        cell.text = column
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for par in cell.paragraphs:
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in par.runs:
                run.font.bold = True; run.font.size = Pt(8); run.font.color.rgb = AZUL
    for i, row in enumerate(df.itertuples(index=False)):
        for j, value in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = str(value)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for par in cell.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in par.runs:
                    run.font.size = Pt(8)
    doc.add_paragraph()


def _tabla_kv(doc, pares):
    t = doc.add_table(rows=len(pares), cols=2)
    t.style = 'Light Shading Accent 1'
    for i, (k, v) in enumerate(pares):
        cs = t.rows[i].cells
        cs[0].text = k; cs[1].text = str(v)
        for c in cs:
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if cs[0].paragraphs[0].runs:
            cs[0].paragraphs[0].runs[0].font.bold = True
    doc.add_paragraph()


def _body(doc, text, italic=False, gray=False, size=10, bold=False):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text)
    r.font.size = Pt(size); r.font.italic = italic; r.font.bold = bold
    if gray:
        r.font.color.rgb = GRIS
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


<<<<<<< HEAD

def _fmt_mm(v, dec=3):
    return f"{v*1000:.{dec}f} mm" if (v is not None and np.isfinite(v)) else "—"


def tabla_comparativa(c):
    return pd.DataFrame({
        "Capa": c["df_st"]["Capa"],
        "z Techo [m]": c["df_st"]["z Techo [m]"],
        "z Base [m]": c["df_st"]["z Base [m]"],
        "Δs Steinbrenner [mm]": c["df_st"]["Δs [mm]"],
        "Δs Ec. Elástica [mm]": c["df_ec"]["Δs [mm]"].values,
        "Δs OpenSees 3D [mm]": c["df_mef"]["Δs [mm]"].values,
    })


def figura_bulbo(c, z_top, figsize=(5, 7)):
    """Tensiones bajo el centro frente a 0,20·σ′v0."""
    z_vals = np.linspace(0.05, z_top, 200)
    sz_v, sx_v, sy_v = holl_centro(c["p"], c["B"], c["L"], z_vals)
    sv_v = sigma_v0(z_vals, c["df"], c["NF"], c["D"], c["gamma_D"], c["gamma_sat_D"])
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(sz_v, z_vals, label=r"Vertical $\Delta\sigma_z$", color='red', lw=2)
    ax.plot(sx_v, z_vals, label=r"Horiz. trans. $\Delta\sigma_x$ (Holl, $\nu$=0,5)", color='blue', ls='--', lw=1)
    ax.plot(sy_v, z_vals, label=r"Horiz. long. $\Delta\sigma_y$ (Holl, $\nu$=0,5)", color='purple', ls='-.', lw=1)
    ax.plot(sv_v, z_vals, label=r"$\sigma'_{v0}$", color='saddlebrown', ls=':', lw=1.5)
    ax.plot(0.20*sv_v, z_vals, label=r"$0.20\,\sigma'_{v0}$ (criterio EC7)", color='green', lw=2)
    if c["zi"] <= z_top:
        ax.axhline(y=c["zi"], color='orange', ls='--', lw=1.5, label=f'z_i EC7 = {c["zi"]:.2f} m')
    nf_loc = c["NF"] - c["D"]
    if 0 < nf_loc < z_top:
        ax.axhline(y=nf_loc, color='deepskyblue', ls='-.', lw=1.2, label=f'NF ({nf_loc:.2f} m bajo la base)')
    ax.set_ylim(z_top, 0); ax.set_xlim(left=0)
    ax.set_xlabel("Tensión (kPa)"); ax.set_ylabel("Profundidad bajo la base z (m)")
    ax.set_title("Bulbo de presiones — centro de la cimentación")
    ax.legend(fontsize=8, loc='lower right')
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.spines[['top', 'right']].set_visible(False)
    plt.tight_layout()
    return fig


def generar_word(c, fig_bulbo_bytes, meta=None):
    """Memoria de cálculo a partir de la instantánea `c` del cálculo realizado."""
=======
def _figura(doc, buf, pie, ancho=15):
    pf = doc.add_paragraph(); pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.add_run().add_picture(buf, width=Cm(ancho))
    nota = doc.add_paragraph(pie); nota.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nota.runs[0].font.size = Pt(9); nota.runs[0].font.italic = True; nota.runs[0].font.color.rgb = GRIS


def _veredicto(doc, filas):
    te = doc.add_table(rows=len(filas), cols=len(filas[0]))
    te.style = 'Light Shading Accent 1'; te.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, rowv in enumerate(filas):
        for j, v in enumerate(rowv):
            c = te.rows[i].cells[j]
            c.text = str(v); c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for par in c.paragraphs:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for rr in par.runs:
                    rr.font.size = Pt(9)
                    if i == 0:
                        rr.font.bold = True; rr.font.color.rgb = AZUL
    doc.add_paragraph()


def generar_word(ctx):
    ci, res_st, res_mef = ctx["ci"], ctx["res_st"], ctx["res_mef"]
    meta, mp = ctx["meta"], res_mef.parametros
    B, L, p, D, NF, z_max, zi = ci["B"], ci["L"], ci["p"], ci["D"], ci["NF"], ci["z_max"], ci["zi"]
    rigida = ci["rigida"]
    tipo = "rígida" if rigida else "flexible"
>>>>>>> refs/remotes/origin/main
    fecha = datetime.now().strftime("%d/%m/%Y — %H:%M")
    obra = meta.get("obra") or "[Denominación de la obra]"
    peticionario = meta.get("peticionario") or "[Peticionario]"
<<<<<<< HEAD
    referencia   = meta.get("referencia") or "GEO-XXXX-ASN-01"
    autor        = meta.get("autor") or "Dpto. Geotecnia"
    revision     = meta.get("revision") or "00 — Emisión inicial"

    B, L, p, NF, D = c["B"], c["L"], c["p"], c["NF"], c["D"]
    z_max, zi = c["z_max"], c["zi"]
    s_st, s_ec, s_mef = c["tot_st"]*1000, c["tot_ec"]*1000, c["tot_mef"]*1000
    mef_ok = np.isfinite(s_mef)
    vals = [v for v in (s_st, s_ec, s_mef) if np.isfinite(v)]
    media = sum(vals) / len(vals)
    dispersion = (max(vals) - min(vals)) / max(media, 1e-9) * 100.0
    s_gob, origen = asiento_gobernante(c["tot_st"], c["tot_ec"], c["tot_mef"],
                                       c["criterio"], c["factor_rigidez"])
    LIM_ELS = float(c["s_adm"])
    cumple_els = s_gob <= LIM_ELS
    consistente = c["modo_tension"] == TENSION_CONSISTENTE
    info = c["mef_info"]
=======
    referencia = meta.get("referencia") or "GEO-XXXX-ASN-01"
    autor = meta.get("autor") or "Dpto. Geotecnia"
    revision = meta.get("revision") or "00 — Emisión inicial"

    s_st, s_mef = res_st.total * 1000.0, res_mef.total * 1000.0
    dif_mef_st = abs(s_mef - s_st) / max(abs(s_st), 1e-9) * 100.0
    s_control = max(s_st, s_mef)
    metodo_control = "Steinbrenner" if s_st >= s_mef else "OpenSees 3D"
    lim_els = float(ctx["s_adm"])
    dentro_umbral = s_control <= lim_els
>>>>>>> refs/remotes/origin/main

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2.5)
        sec.left_margin = Cm(3.0); sec.right_margin = Cm(3.0)
        fp = sec.footer.paragraphs[0]
        fp.text = f"Memoria de Cálculo de Asientos · {referencia} · Generado el {fecha}"
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp.runs[0].font.size = Pt(8); fp.runs[0].font.color.rgb = RGBColor(128, 128, 128)
    style = doc.styles['Normal']; style.font.name = 'Open Sans'; style.font.size = Pt(9)
    h1f = doc.styles['Heading 1'].font
    h1f.name = 'Open Sans Condensed'; h1f.size = Pt(12); h1f.color.rgb = AZUL; h1f.bold = True

    # ── PORTADA
    doc.add_paragraph(); doc.add_paragraph()
    pt = doc.add_paragraph(); pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = pt.add_run('MEMORIA DE CÁLCULO DE ASIENTOS'); rt.bold = True; rt.font.size = Pt(24); rt.font.color.rgb = AZUL
    ps = doc.add_paragraph(); ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = ps.add_run(f'Cimentación superficial {tipo} · Método analítico y MEF 3D')
    rs.font.size = Pt(13); rs.font.color.rgb = GRIS
    doc.add_paragraph(); doc.add_paragraph()
    _tabla_kv(doc, [('Obra / Proyecto', obra), ('Peticionario', peticionario), ('Referencia', referencia),
                    ('Redactado por', autor), ('Fecha', fecha), ('Revisión', revision)])
    doc.add_page_break()

    # ── 1. OBJETO
    doc.add_heading('1. Objeto y alcance', level=1)
    _h2(doc, '1.1 Objeto')
<<<<<<< HEAD
    _body(doc, "El presente documento recoge el cálculo del asiento en el centro de una cimentación superficial "
               "rectangular sometida a carga vertical uniforme, mediante tres formulaciones: el método analítico "
               "de Steinbrenner, la integración numérica de la deformación vertical elástica y un modelo "
               "tridimensional de elementos finitos (OpenSeesPy).")
    _h2(doc, '1.2 Alcance: asiento elástico / inmediato')
    _body(doc, "Los tres métodos parten de la teoría de la elasticidad lineal. En consecuencia, el resultado "
               "corresponde al ASIENTO ELÁSTICO, obtenido con los módulos introducidos. Si estos son no drenados, "
               "el asiento es inmediato y no incluye la consolidación; si son drenados (E′), representa el asiento "
               "diferido en condiciones drenadas. El valor calculado corresponde al centro de un área flexible.")
=======
    _body(doc, f"El presente documento recoge el cálculo del asiento de una cimentación superficial rectangular "
               f"{tipo} sometida a carga vertical centrada, mediante dos formulaciones independientes: el método "
               f"de Steinbrenner y un modelo tridimensional de elementos finitos (OpenSeesPy). Se evalúa además la "
               f"distribución de asientos en la cota de apoyo.")
    _h2(doc, '1.2 Alcance: asiento elástico / inmediato')
    _body(doc, "Ambos métodos parten de la teoría de la elasticidad lineal. El resultado corresponde al ASIENTO "
               "ELÁSTICO (inmediato). No incluye la consolidación primaria ni la secundaria.")
>>>>>>> refs/remotes/origin/main
    doc.add_page_break()

    # ── 2. NORMATIVA
    doc.add_heading('2. Normativa y referencias', level=1)
    _bullets(doc, [
<<<<<<< HEAD
        "CTE DB-SE-C «Seguridad estructural – Cimientos». Estados Límite de Servicio (asientos admisibles).",
        "UNE-EN 1997-1 (Eurocódigo 7), apartado 6.6.2: criterio de profundidad de influencia (Δσz ≤ 0,20·σ′v0).",
        "Steinbrenner (1934) / Bowles: desplazamiento vertical del semiespacio elástico bajo la esquina de un "
        "rectángulo; asiento de cada estrato como diferencia entre techo y base (aproximación de estrato finito).",
        "Holl (1940): tensiones bajo carga rectangular uniforme; las expresiones de σx y σy corresponden a ν = 0,5.",
        "Boussinesq: suma de tensiones normales θ = (1+ν)·P·z/(π·R³), válida para ν arbitrario.",
        "OpenSeesPy: biblioteca de elementos finitos; hexaedro de 8 nodos con formulación B-bar (bbarBrick).",
=======
        "CTE DB-SE-C «Seguridad estructural – Cimientos»: estados límite de servicio.",
        "UNE-EN 1997-1 (Eurocódigo 7), apartado 6.6.2: criterio de profundidad de influencia (Δσz ≤ 0,20·σ′v0).",
        "Holl (1940): incrementos de tensión bajo la esquina de un rectángulo cargado.",
        "Steinbrenner / Bowles: solución elástica aproximada del asiento de un estrato de espesor finito.",
        "Grasshoff: punto característico para el asiento de cimentaciones rígidas.",
        "Mayne y Poulos (1999): factor de corrección por empotramiento I_E.",
        "OpenSeesPy: elementos finitos; hexaedro de 8 nodos con formulación B-bar (bbarBrick).",
>>>>>>> refs/remotes/origin/main
    ])
    doc.add_page_break()

    # ── 3. DATOS
    doc.add_heading('3. Datos de partida', level=1)
    _h2(doc, '3.1 Geometría, acciones y profundidades')
<<<<<<< HEAD
    d3 = [('Dimensiones en planta (B × L)', f'{B:.2f} m × {L:.2f} m'),
          ('Presión neta de trabajo (p)', f'{p:.1f} kPa'),
          ('Profundidad de cimentación (D)', f'{D:.2f} m'),
          ('Terreno sobre la base (γ / γsat)', f'{c["gamma_D"]:.1f} / {c["gamma_sat_D"]:.1f} kN/m³'),
          ('Nivel freático (NF, desde superficie)', f'{NF:.1f} m' if NF < 100 else 'No detectado'),
          ('Profundidad de influencia (z_i, EC7)', f'{zi:.2f} m bajo la base'
                                                   + ('' if c["zi_ok"] else ' (criterio no alcanzado)')),
          ('Profundidad de corte evaluada (z_max)', f'{z_max:.2f} m bajo la base'),
          ('Punto de cálculo', 'Centro de la zapata (superposición ×4 de cuadrantes)')]
    t3 = doc.add_table(rows=len(d3), cols=2); t3.style = 'Light Shading Accent 1'
    for i, (k, v) in enumerate(d3):
        cs = t3.rows[i].cells; cs[0].text = k; cs[1].text = v
        cs[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER; cs[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if cs[0].paragraphs[0].runs: cs[0].paragraphs[0].runs[0].font.bold = True
    _body(doc, "La presión p es la presión NETA de trabajo (descontada la sobrecarga de tierras retirada). "
               "Las profundidades z se miden desde la base de la zapata; D y NF, desde la superficie del terreno. "
               "Los asientos se evalúan en combinación de servicio (ELS), no con acciones mayoradas.", gray=True, size=9)
    doc.add_paragraph()
    _add_styled_table(doc, c["df"], '3.2 Estratigrafía del perfil geotécnico')
    _body(doc, f"Los módulos E deben ser coherentes con la condición de análisis adoptada. Si proceden de "
               f"ensayo edométrico (E_oed), conviene convertirlos al módulo de Young mediante "
               f"E = E_oed·(1+ν)(1−2ν)/(1−ν). El coeficiente de Poisson se limita a ν ≤ {NU_MAX} en todos los "
               f"métodos.", gray=True, size=9)
=======
    _tabla_kv(doc, [
        ('Dimensiones en planta (B × L)', f'{B:.2f} m × {L:.2f} m'),
        ('Tipo de cimentación', 'Rígida' if rigida else 'Flexible'),
        ('Profundidad de apoyo (D, desde superficie)', f'{D:.2f} m'),
        ('Presión neta de trabajo (p)', f'{p:.1f} kPa'),
        ('Nivel freático (desde superficie)', f'{NF:.1f} m' if NF < 100 else 'No afecta'),
        ('Profundidad de influencia (z_i, EC7, bajo apoyo)', f'{zi:.2f} m'),
        ('Profundidad de corte (z_max, bajo apoyo)', f'{z_max:.2f} m'),
    ])
    _body(doc, "La presión p es la presión NETA de trabajo (descontada la sobrecarga de tierras retirada). Los asientos "
               "se evalúan en combinación de servicio (ELS). Las profundidades z se miden desde la cota de apoyo.",
          gray=True, size=9)
    _add_styled_table(doc, ci.get("df_entrada", ci["df"]), '3.2 Estratigrafía del perfil geotécnico (desde la superficie)')
    if ci.get("nu_ajustado"):
        _body(doc, "Convención numérica: los valores introducidos como ν = 0,500 se han evaluado como ν = 0,499 "
                   "en ambos métodos para evitar la singularidad de la matriz constitutiva.", gray=True, size=9)
>>>>>>> refs/remotes/origin/main
    doc.add_page_break()

    # ── 4. HIPÓTESIS
    doc.add_heading('4. Hipótesis y modelo de cálculo', level=1)
    _h2(doc, '4.1 Base común: elasticidad lineal')
<<<<<<< HEAD
    _body(doc, "Los tres métodos asumen un terreno elástico lineal, isótropo, caracterizado por (E, ν) en cada "
               "estrato. El asiento resulta de integrar la deformación vertical en profundidad hasta z_max.")
    _h2(doc, '4.2 Hipótesis de cada método')
    _bullets(doc, [
        "Steinbrenner: solución cerrada del desplazamiento del semiespacio con los factores φ₁ y φ₂; asiento por "
        "estrato como diferencia entre techo y base, con el (E, ν) del estrato.",
        "Ecuación elástica: integración numérica (Gauss, 3 puntos por subcapa) de "
        "Δεz = [Δσz − ν(Δσx+Δσy)]/E, con "
        + ("la suma de tensiones horizontales exacta para el ν de cada estrato." if consistente
           else "las tensiones horizontales clásicas de Holl (ν = 0,5)."),
        f"MEF 3D (OpenSees): continuo tridimensional con hexaedros bbarBrick, cuarto de dominio por doble "
        f"simetría y base rígida a {c['factor_prof']:.2f}·z_max.",
=======
    _body(doc, "Ambos métodos asumen un terreno elástico lineal, isótropo, caracterizado por (E, ν) en cada estrato, "
               "sin reproducir consolidación primaria, fluencia ni dependencia de la rigidez con el nivel tensional.")
    _h2(doc, '4.2 Hipótesis de cada método')
    _bullets(doc, [
        "Steinbrenner: solución aproximada que supone la distribución de tensiones del semiespacio homogéneo; no "
        "recoge la redistribución de tensiones por contraste de rigidez entre estratos ni la base rígida."
        + (" El asiento de la zapata rígida se evalúa con el punto clásico (0,37·B; 0,37·L), aproximación asociada "
           "a ν = 0 cuya posición no es universal." if rigida else
           " Se evalúa el asiento del centro de la zapata flexible."),
        "MEF 3D (OpenSees): continuo tridimensional con hexaedros bbarBrick y cuarto de dominio por doble simetría. "
        f"La base fija se sitúa a {mp['factor_prof']:.2f}·z_max bajo el apoyo."
        + (" Zapata rígida y lisa: los nodos cargados comparten el desplazamiento vertical." if rigida else
           " Zapata flexible: presión uniforme.")
        + (f" Para D = {D:.2f} m se representa la geometría excavada y el terreno lateral, sin contacto lateral "
           "suelo-zapata, estado geostático ni fases constructivas."
           if D > 0 else ""),
>>>>>>> refs/remotes/origin/main
    ])
    doc.add_page_break()

    # ── 5. PROFUNDIDAD DE INFLUENCIA
    doc.add_heading('5. Profundidad de influencia (EC7)', level=1)
<<<<<<< HEAD
    _body(doc, "La profundidad de cálculo se acota mediante el criterio del Eurocódigo 7: se considera despreciable "
               "la contribución al asiento por debajo de la cota z_i en la que el incremento de tensión vertical cae "
               "por debajo del 20 % de la tensión efectiva geoestática:")
    _body(doc, "Δσz(z_i) ≤ 0,20 · σ′v0(z_i)", bold=True)
    _body(doc, f"La tensión efectiva σ′v0 incluye el terreno situado por encima de la base (D = {D:.2f} m) y se "
               f"calcula con el peso específico natural sobre el nivel freático y el peso sumergido (γsat − γw) "
               f"por debajo. Resulta z_i = {zi:.2f} m bajo la base, adoptándose z_max = {z_max:.2f} m.")
    if not c["zi_ok"]:
        _nota(doc, "El criterio del 20 % no se alcanza dentro de la estratigrafía definida: z_i se ha limitado al "
                   "espesor total del perfil. Conviene prolongar la estratigrafía.")
=======
    _body(doc, "La profundidad de cálculo se acota con el criterio del Eurocódigo 7: se considera despreciable la "
               "contribución al asiento por debajo de la cota z_i en la que el incremento de tensión vertical bajo el "
               "centro cae por debajo del 20 % de la tensión efectiva geostática. σ′v0 incluye las tierras situadas "
               "por encima de la cota de apoyo.")
    _body(doc, "Δσz(z_i) ≤ 0,20 · σ′v0(D + z_i)", bold=True)
    _body(doc, f"Para el caso analizado resulta z_i = {zi:.2f} m bajo la cota de apoyo, adoptándose z_max = {z_max:.2f} m.")
>>>>>>> refs/remotes/origin/main
    doc.add_page_break()

    # ── 6. STEINBRENNER
    doc.add_heading('6. Método 1 — Steinbrenner', level=1)
<<<<<<< HEAD
    _body(doc, "Solución cerrada del asiento con los factores geométricos φ₁ y φ₂ = (m/2π)·arctan[n/(m√(1+m²+n²))]. "
               "El asiento de cada estrato se obtiene como diferencia entre el valor en su techo y en su base.")
    _add_styled_table(doc, c["df_st"], '6.1 Cálculos intermedios y asiento por estrato')
=======
    xs, ys = res_st.punto
    _body(doc, "El asiento de cada estrato se obtiene como diferencia entre los desplazamientos del semiespacio "
               "homogéneo (w) en su techo y en su base, evaluados con el E y ν del propio estrato. Los valores w son "
               "auxiliares; solo su diferencia Δs tiene significado físico.")
    _body(doc, f"Punto de evaluación: x = {xs:.2f} m, y = {ys:.2f} m "
               + ("(punto característico de la zapata rígida)." if rigida else "(centro de la zapata flexible)."))
    if res_st.I_E < 1.0:
        _body(doc, f"Se aplica el factor de empotramiento de Mayne y Poulos (1999), I_E = {res_st.I_E:.3f}, incluido en "
                   f"Δs. Asiento sin corrección: {res_st.total_sin_correccion*1000:.2f} mm.")
    _add_styled_table(doc, res_st.tabla, '6.1 Cálculos intermedios y asiento por estrato')
>>>>>>> refs/remotes/origin/main
    tot1 = doc.add_paragraph(); tot1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot1.add_run(f'Asiento Steinbrenner: {s_st:.3f} mm'); r.bold = True; r.font.color.rgb = AZUL
    doc.add_page_break()

<<<<<<< HEAD
    # ───────────────── 7. MÉTODO 2 — EC. ELÁSTICA ─────────────────
    doc.add_heading('7. Método 2 — Integración de la ecuación elástica', level=1)
    if consistente:
        _body(doc, "Integración numérica de la deformación vertical en subcapas (cuadratura de Gauss de 3 puntos). "
                   "Δσz procede de Holl y la suma Δσx+Δσy se obtiene de forma exacta para el ν de cada estrato "
                   "(θ − σz). Al compartir teoría con Steinbrenner, su coincidencia verifica la integración, no la "
                   "hipótesis elástica.")
    else:
        _body(doc, "Integración numérica de la deformación vertical en subcapas (cuadratura de Gauss de 3 puntos) con "
                   "las tensiones clásicas de Holl. Sus tensiones horizontales corresponden a ν = 0,5, por lo que el "
                   "asiento resulta inferior al de Steinbrenner cuando ν < 0,5.")
    _add_styled_table(doc, c["df_ec"], f'7.1 Tensiones medias y asiento por estrato (dz = {c["dz_sub"]} m)')
    tot2 = doc.add_paragraph(); tot2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot2.add_run(f'Asiento total Ec. Elástica: {s_ec:.3f} mm'); r.bold = True; r.font.color.rgb = RGBColor(33, 115, 70)
    doc.add_page_break()

    # ───────────────── 8. MÉTODO 3 — MEF 3D ─────────────────
    doc.add_heading('8. Método 3 — MEF 3D (OpenSees)', level=1)
    _h2(doc, '8.1 Descripción del modelo')
    _body(doc, f"El terreno se discretiza como un medio continuo tridimensional con hexaedros de 8 nodos con "
               f"formulación B-bar (bbarBrick), que evita el bloqueo volumétrico con ν elevado, y material "
               f"ElasticIsotropic por estrato. Se modela un cuarto del dominio por doble simetría, con una extensión "
               f"lateral de {c['factor_dominio']:.0f}·B/2 × {c['factor_dominio']:.0f}·L/2. La malla es uniforme "
               f"(tamaño {c['mesh']:.2f} m) bajo la zapata"
               + (f" y crece en progresión geométrica de razón {c['ratio']:.2f} hacia el contorno." if c['ratio'] > 1
                  else " y en el resto del dominio."))
    _h2(doc, '8.2 Condiciones de contorno y base rígida')
    _body(doc, f"En los planos de simetría y en las fronteras laterales se impide el desplazamiento normal dejando "
               f"libre el vertical. La base rígida (tres grados de libertad empotrados) se sitúa a "
               f"{c['factor_prof']*z_max:.2f} m bajo la base de la zapata ({c['factor_prof']:.2f}·z_max).")
    if mef_ok and c["factor_prof"] > 1.0:
        _body(doc, f"El asiento de comparación es s(0) − s(z_max) = {s_mef:.3f} mm, coherente con los métodos "
                   f"analíticos. El asiento total en superficie, que incluye la deformación entre z_max y la base "
                   f"rígida, es de {info['s_superficie_mm']:.3f} mm.")
        if info["extension"]:
            _nota(doc, "El perfil definido no alcanza la base rígida: el último estrato se ha prolongado con sus "
                       "mismas propiedades hasta ella.")
    if mef_ok:
        _h2(doc, '8.3 Reparto de cargas y tamaño del modelo')
        _body(doc, f"La presión se reparte en fuerzas nodales mediante áreas tributarias. Resultante aplicada: "
                   f"{info['resultante_kN']:.3f} kN frente a p·B·L/4 = {info['resultante_teorica_kN']:.3f} kN. "
                   f"Modelo: {info['n_nodos']:,} nodos y {info['n_elementos']:,} elementos; solver {info['solver']}.")
        _add_styled_table(doc, c["df_mef"], '8.4 Asiento por estrato (eje central)')
        tot3 = doc.add_paragraph(); tot3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = tot3.add_run(f'Asiento MEF 3D (0 – z_max): {s_mef:.3f} mm'); r.bold = True; r.font.color.rgb = RGBColor(192, 0, 0)
    else:
        _nota(doc, f"El cálculo MEF no ha podido completarse: {c['mef_error'].rstrip('.')}. La comprobación de servicio se "
                   f"realiza con los métodos analíticos.")
    doc.add_page_break()

    # ───────────────── 9. RESULTADOS Y COMPARATIVA ─────────────────
    doc.add_heading('9. Resultados y comparativa', level=1)
    _h2(doc, '9.1 Asientos por método (0 – z_max)')
    tr = doc.add_table(rows=1, cols=3); tr.style = 'Light Shading Accent 1'; tr.alignment = WD_TABLE_ALIGNMENT.CENTER
    cc = tr.rows[0].cells
    for cell_, (nom, val, col) in zip(cc, [('Steinbrenner', s_st, RGBColor(23, 54, 93)),
                                            ('Ec. Elástica', s_ec, RGBColor(33, 115, 70)),
                                            ('OpenSees 3D', s_mef, RGBColor(192, 0, 0))]):
        cell_.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        pp = cell_.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ra = pp.add_run(nom + '\n'); ra.font.size = Pt(11); ra.bold = True; ra.font.color.rgb = RGBColor(89, 89, 89)
        rb = pp.add_run(f'{val:.3f} mm' if np.isfinite(val) else 'No disponible')
        rb.font.size = Pt(16); rb.bold = True; rb.font.color.rgb = col
    doc.add_paragraph()
    _h2(doc, '9.2 Comparativa por estrato')
    _add_styled_table(doc, tabla_comparativa(c).drop(columns=["z Techo [m]", "z Base [m]"]), '')
    _h2(doc, '9.3 Interpretación')
    texto = f"La dispersión entre los métodos disponibles es del {dispersion:.1f} %. "
    if consistente:
        texto += ("Steinbrenner y la integración elástica resuelven el mismo problema (semiespacio elástico con el "
                  "(E, ν) de cada estrato), por lo que deben coincidir: su acuerdo verifica la implementación, no "
                  "la validez de la hipótesis. ")
    else:
        texto += ("La integración con tensiones de Holl queda por debajo de Steinbrenner porque sus tensiones "
                  "horizontales corresponden a ν = 0,5. ")
    if mef_ok:
        dif = (s_mef - s_st) / max(abs(s_st), 1e-9) * 100.0
        texto += (f"El MEF 3D difiere de Steinbrenner un {dif:+.1f} %. La diferencia es esperable: el MEF resuelve "
                  f"un estrato sobre base rígida, con dominio lateral finito y con la interacción real entre "
                  f"estratos de distinta rigidez, mientras que Steinbrenner integra el campo del semiespacio.")
    _body(doc, texto)
    doc.add_page_break()

    # ───────────────── 10. VERIFICACIÓN ─────────────────
    doc.add_heading('10. Verificación del programa', level=1)
    _body(doc, "El motor de cálculo dispone de una batería de pruebas automatizadas que contrasta: los factores de "
               "Steinbrenner con la integración numérica de la solución de Boussinesq; las tensiones de Holl con la "
               "integración directa de Boussinesq; la igualdad entre Steinbrenner y la integración elástica "
               "consistente; el equilibrio de cargas del MEF; la independencia del resultado respecto a la "
               "graduación de la malla, y la detección de fallos del solver.")
    doc.add_page_break()

    # ───────────────── 11. COMPROBACIÓN ELS ─────────────────
    doc.add_heading('11. Comprobación en Estado Límite de Servicio', level=1)
    _body(doc, "Se compara el asiento de comprobación con el asiento general admisible adoptado en función del tipo "
               "de edificio y de la naturaleza del terreno (tabla de asientos generales admisibles). "
               f"Asiento de comprobación: {origen}.")
    te = doc.add_table(rows=2, cols=4); te.style = 'Light Shading Accent 1'; te.alignment = WD_TABLE_ALIGNMENT.CENTER
    els_rows = [('Comprobación', 'Obtenido', 'Admisible', 'Veredicto'),
                ('Asiento total', f'{s_gob:.2f} mm', f'{LIM_ELS:.0f} mm', 'CUMPLE' if cumple_els else 'REVISAR')]
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
    _body(doc, f"El asiento obtenido ({s_gob:.2f} mm) supone un aprovechamiento del {s_gob/LIM_ELS*100:.0f} % del "
               f"asiento admisible adoptado ({LIM_ELS:.0f} mm).", gray=True, size=9)
    if c["cohesivos"]:
        _nota(doc, "Estratos cohesivos dentro de z_max (" + ", ".join(c["cohesivos"]) + "): el asiento calculado es "
                   "elástico. Si los módulos no son drenados, falta sumar el asiento de consolidación antes de "
                   "comparar con el asiento total admisible.")
=======
    # ── 7. MEF
    doc.add_heading('7. Método 2 — MEF 3D (OpenSees)', level=1)
    _h2(doc, '7.1 Descripción del modelo')
    _body(doc, "Hexaedros de 8 nodos con formulación B-bar (bbarBrick), adecuada para ν próximos a 0,5. Cuarto de "
               "dominio por doble simetría. En los planos de simetría y en las fronteras laterales se impide el "
               f"desplazamiento normal; la base se fija a {res_mef.profundidad_dominio:.2f} m bajo la cota de apoyo, "
               f"mientras el asiento se integra hasta z_max = {z_max:.2f} m.")
    _bullets(doc, [
        f"Malla {'graduada' if mp['graduada'] else 'uniforme'}: tamaño bajo la zapata {mp['tamaño_malla']:.2f} m"
        + (f", crecimiento ×{mp['ratio']:.2f} por elemento hasta {mp['tamaño_max']:.2f} m" if mp['graduada'] else "")
        + ".",
        f"Extensión lateral: ×{mp['factor_dominio']:.0f} (B/2, L/2) → {res_mef.extension_x:.2f} m × "
        f"{res_mef.extension_y:.2f} m en el cuarto modelado.",
        f"Tamaño del modelo: {res_mef.n_nodos:,} nodos y {res_mef.n_elementos:,} elementos "
        f"(resuelto en {res_mef.tiempo:.1f} s).",
        f"Equilibrio vertical del cuarto de dominio: carga {res_mef.carga_aplicada:.3f} kN, reacción "
        f"{res_mef.reaccion_vertical:.3f} kN, error relativo {res_mef.error_equilibrio:.2e}.",
        "Carga: " + ("zapata rígida y lisa (nodos cargados con igual desplazamiento vertical, equalDOF)." if rigida
                     else "presión uniforme repartida en fuerzas nodales por áreas tributarias."),
    ] + ([f"Profundidad de apoyo: se representa el hueco excavado y el terreno lateral hasta D = {D:.2f} m. "
          f"No se modelan contacto lateral, tensiones geostáticas ni secuencia de excavación."] if D > 0 else []))
    conv = ctx.get("convergencia")
    if conv:
        _body(doc, f"Estudio de sensibilidad: modelo de referencia con tamaño {conv['tamaño_malla']:.3f} m y factor "
                   f"lateral {conv['factor_dominio']:.1f}; asiento {conv['asiento_ref_mm']:.3f} mm y diferencia "
                   f"{conv['diferencia_pct']:.2f} % respecto al modelo principal.",
              bold=conv["diferencia_pct"] > 5.0)
    else:
        _body(doc, "No se ha ejecutado el estudio opcional de sensibilidad de malla y extensión lateral.",
              gray=True, size=9)
    _figura(doc, _fig_bytes(fig_malla(ci, mp)), "Sección y = 0 de la malla de elementos finitos.", 15)
    _add_styled_table(doc, res_mef.tabla, '7.2 Asiento por estrato (eje central)')
    tot3 = doc.add_paragraph(); tot3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot3.add_run(f'Asiento MEF 3D: {s_mef:.3f} mm'); r.bold = True; r.font.color.rgb = ROJO
    doc.add_page_break()

    # ── 8. COMPARATIVA
    doc.add_heading('8. Resultados y comparativa', level=1)
    _veredicto(doc, [('Steinbrenner', 'OpenSees 3D', 'Diferencia'),
                     (f'{s_st:.2f} mm', f'{s_mef:.2f} mm', f'{dif_mef_st:.1f} %')])
    _add_styled_table(doc, tabla_comparativa(res_st.tabla, res_mef.tabla), '8.1 Comparativa por estrato')
    _h2(doc, '8.2 Interpretación')
    _body(doc, "En perfiles estratificados es esperable cierta diferencia entre ambos métodos y no constituye por sí "
               "misma un error: Steinbrenner supone la distribución de tensiones del semiespacio homogéneo, mientras "
               "que el MEF recoge la redistribución de tensiones por contraste de rigidez entre estratos y la base "
               "rígida. Diferencias elevadas en perfiles casi homogéneos aconsejan revisar la malla y la extensión "
               "lateral del dominio.")
    doc.add_page_break()

    # ── 9. CONTROLES
    doc.add_heading('9. Controles numéricos', level=1)
    _body(doc, "La ejecución verifica la conservación de la carga mediante áreas tributarias, el equilibrio vertical "
               "entre carga y reacciones, la cobertura del perfil geotécnico hasta la base del dominio y el cumplimiento "
               "del criterio de profundidad de influencia. Estos controles no sustituyen un estudio de sensibilidad "
               "frente al tamaño de malla y a la extensión de las fronteras para resultados de proyecto.")
    doc.add_page_break()

    # ── 10. COMPARACIÓN DEL ASIENTO ELÁSTICO
    doc.add_heading('10. Comparación del asiento elástico con el umbral adoptado', level=1)
    _body(doc, f"Se adopta como valor de control la envolvente de los dos métodos ({metodo_control}) y se compara con "
               f"el umbral indicado por el usuario ({lim_els:.0f} mm). La comparación es parcial: no constituye por sí "
               "sola una comprobación completa del asiento total si existen consolidación o fluencia.")
    _veredicto(doc, [('Comprobación', 'Obtenido', 'Admisible', 'Veredicto'),
                     (f'Asiento elástico de control ({metodo_control})', f'{s_control:.2f} mm', f'{lim_els:.0f} mm',
                      'DENTRO DEL UMBRAL' if dentro_umbral else 'REVISAR')])
    _body(doc, f"Relación respecto al umbral: {s_control / lim_els * 100:.0f} %.", gray=True, size=9)
>>>>>>> refs/remotes/origin/main
    doc.add_page_break()

    # ── 11. DISTRIBUCIÓN DE ASIENTOS
    doc.add_heading('11. Distribución de asientos', level=1)
    _add_styled_table(doc, tabla_puntos(ctx["puntos_st"], res_mef), '11.1 Asientos en puntos notables (cota de apoyo)')
    _figura(doc, _fig_bytes(fig_perfiles(ci, ctx["perf_st"], res_mef)),
            "Perfiles de asiento a la cota de apoyo según los ejes de la zapata.", 16)
    doc.add_page_break()

    # ── 12. BULBO
    doc.add_heading('12. Zona de influencia de la carga de cimentación', level=1)
    z_h = max(fa.espesor_total(ci["df"]) - D, 0.5)
    _figura(doc, _fig_bytes(fig_bulbo(p, B, L, ci["df"], NF, D, z_h, zi, figsize=(5, 7))),
            f"Tensiones bajo el centro de la zapata (p = {p:.1f} kPa, B = {B:.2f} m, L = {L:.2f} m). "
            f"Criterio EC7: 0,20·σ′v0. Tensiones horizontales de Holl para ν = 0,5.", 13)

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════════════
# ESTADO DE LA SESIÓN
# ══════════════════════════════════════════════════════════════════════════
def reset_calculo():
    st.session_state.calculo_realizado = False
<<<<<<< HEAD
    if st.session_state.get("informe_generado", False):
        st.session_state.informe_stale = True
    st.session_state.informe_generado = False
    st.session_state.word_buf = None


@st.cache_data(show_spinner=False)
def _zi_cacheado(p, B, L, df, NF, D, gamma_D, gamma_sat_D):
    return z_influencia_ec7(p, B, L, df, NF, D, gamma_D, gamma_sat_D)


for _k, _v in [("calculo_realizado", False), ("informe_generado", False),
               ("informe_stale", False), ("word_buf", None), ("calc", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if 'df_terreno' not in st.session_state:
    st.session_state.df_terreno = pd.DataFrame({
        "Descripción":           ["Arcilla 1", "Arcilla 2", "Grava"],
        "Tipo":                  ["Cohesivo", "Cohesivo", "Granular"],
        "Espesor (m)":           [1.5, 3.0, 5.0],
        "E (kPa)":               [10000.0, 15000.0, 40000.0],
        "nu":                    [0.30, 0.45, 0.25],
        "Peso Esp. (kN/m³)":     [18.0, 19.0, 21.0],
        "Peso Esp. Sat (kN/m³)": [20.0, 20.0, 22.0],
    })

st.set_page_config(page_title="Cálculo de Asientos · MEF 3D", layout="wide", page_icon="🏗️")
st.sidebar.title("Navegación")
modo = st.sidebar.radio("Vista:", ["🧮 Panel de Cálculo", "📋 Modelo Steinbrenner", "📋 Modelo Elástico",
                                   "🌐 Modelo OpenSees", "📉 Bulbo de Presiones", "📐 Asientos Admisibles",
                                   "📖 Fundamento Teórico"])

# ── DATOS DE ENTRADA ──
st.sidebar.markdown("---")
st.sidebar.header("📥 Datos de Entrada")
B  = st.sidebar.number_input("Ancho (B) [m]", min_value=0.1, value=2.0, step=0.1, on_change=reset_calculo)
L  = st.sidebar.number_input("Longitud (L) [m]", min_value=0.1, value=3.0, step=0.1, on_change=reset_calculo)
p  = st.sidebar.number_input("Presión neta (p) [kPa]", min_value=1.0, value=150.0, step=10.0, on_change=reset_calculo)
D  = st.sidebar.number_input("Profundidad de cimentación (D) [m]", min_value=0.0, value=0.0, step=0.1,
                             on_change=reset_calculo, help="Desde la superficie del terreno hasta la base de la zapata.")
NF = st.sidebar.number_input("Nivel freático, desde superficie [m]", min_value=0.0, value=100.0, step=0.5,
                             on_change=reset_calculo, help="Un valor ≥ 100 m equivale a «sin nivel freático».")
with st.sidebar.expander("Terreno por encima de la base (0 ≤ prof. ≤ D)"):
    gamma_D = st.number_input("γ [kN/m³]", min_value=10.0, value=18.0, step=0.5, on_change=reset_calculo)
    gamma_sat_D = st.number_input("γsat [kN/m³]", min_value=10.0, value=20.0, step=0.5, on_change=reset_calculo)

if L < B:
    B, L = L, B
    st.sidebar.warning("⚠️ L<B: valores intercambiados.")

df_val, errores, avisos = validar_estratigrafia(st.session_state.df_terreno)
datos_ok = not errores
if datos_ok:
    espesor_total = max(float(df_val["Espesor (m)"].sum()), 0.1)
    zi, zi_ok = _zi_cacheado(p, B, L, df_val, NF, D, gamma_D, gamma_sat_D)
else:
    espesor_total, zi, zi_ok = 0.1, 0.1, False
    st.sidebar.error("❌ La estratigrafía tiene errores (ver panel de cálculo).")

# ── PROFUNDIDAD DE CÁLCULO ──
st.sidebar.markdown("---")
st.sidebar.subheader("📐 Profundidad de Cálculo")
if datos_ok and not zi_ok:
    st.sidebar.warning("El criterio EC7 no se alcanza dentro del perfil: z_i se limita al espesor total. "
                       "Conviene prolongar la estratigrafía.")
z_auto = float(max(0.1, min(round(zi, 2), espesor_total)))
usar_zi = st.sidebar.checkbox("Usar z_i (EC7) como profundidad de corte", value=True, key="z_max_auto",
                              on_change=reset_calculo)
if usar_zi:
    z_max_user = z_auto
    st.sidebar.markdown(f"**z_max = z_i = {z_max_user:.2f} m** bajo la base")
else:
    if "z_max_manual" not in st.session_state:
        st.session_state.z_max_manual = z_auto
    st.session_state.z_max_manual = float(min(max(st.session_state.z_max_manual, 0.1), espesor_total))
    z_max_user = st.sidebar.number_input("Profundidad de corte (z_max) [m]", min_value=0.1,
                                         max_value=espesor_total, step=0.1, key="z_max_manual",
                                         on_change=reset_calculo)
    st.sidebar.caption(f"Referencia EC7: z_i = {zi:.2f} m")

# ── ELS ──
st.sidebar.markdown("---")
st.sidebar.subheader("✅ Comprobación de Servicio (ELS)")
asiento_adm = st.sidebar.number_input(
    "Asiento admisible [mm]", min_value=1.0, value=25.0, step=1.0, on_change=reset_calculo,
    help="Consulta la pestaña «📐 Asientos Admisibles» para elegirlo según edificio y terreno.")
criterio = st.sidebar.selectbox("Asiento de comprobación", CRITERIOS_GOBERNANTE, index=0, on_change=reset_calculo,
                                help="Si se elige el MEF y no puede resolverse, se usa el máximo de los analíticos.")
factor_rigidez = st.sidebar.number_input(
    "Factor de rigidez de la zapata (s_rígida / s_centro)", min_value=0.5, max_value=1.0, value=1.0, step=0.01,
    on_change=reset_calculo,
    help="1,0 = centro de zapata flexible (lado seguro). Para zapata rígida la bibliografía propone valores "
         "del orden de 0,8–0,93 según la fuente; justifica el valor adoptado.")

# ── MÉTODO 2 ──
st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Ecuación Elástica")
dz_sub = st.sidebar.select_slider("Tamaño de subcapa (dz) [m]", options=[2.0, 1.0, 0.5, 0.25, 0.10, 0.05],
                                  value=0.25, on_change=reset_calculo)
_modo_lbl = st.sidebar.radio("Tensiones horizontales",
                             ["Consistentes con ν (exactas)", "Holl clásicas (ν = 0,5)"],
                             on_change=reset_calculo,
                             help="Las expresiones de Holl para σx, σy suponen ν = 0,5 e infravaloran el asiento "
                                  "cuando ν es menor.")
modo_tension = TENSION_CONSISTENTE if _modo_lbl.startswith("Consistentes") else TENSION_HOLL

# ── MEF 3D ──
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parámetros OpenSees MEF 3D")
if not OPENSEES_DISPONIBLE:
    st.sidebar.warning("⚠️ OpenSeesPy no detectado: la comprobación usará los métodos analíticos.")
factor_dominio = st.sidebar.slider("Extensión del dominio (×B/2, ×L/2)", min_value=3.0, max_value=8.0,
                                   value=5.0, step=1.0, on_change=reset_calculo)
mesh_3d = st.sidebar.number_input("Tamaño de malla bajo la zapata [m]", min_value=0.1, max_value=1.0, value=0.5,
                                  step=0.05, on_change=reset_calculo)
ratio_malla = st.sidebar.select_slider("Crecimiento de la malla hacia el contorno",
                                       options=[1.0, 1.1, 1.2, 1.3, 1.5], value=1.2, on_change=reset_calculo,
                                       help="1,0 = malla uniforme. Valores > 1 engrosan la malla fuera de la zapata.")
factor_prof = st.sidebar.slider("Base rígida del MEF (× z_max)", min_value=1.0, max_value=2.0, value=1.0,
                                step=0.25, on_change=reset_calculo,
                                help="1,0 = base rígida en z_max (comparable con los analíticos). Con valores > 1 "
                                     "se informa además el asiento total en superficie.")
if factor_dominio < 4:
    st.sidebar.warning("Con factor < 4 las fronteras laterales rigidizan el modelo y subestiman el asiento (≥5 recomendado).")

if datos_ok:
    nodos_totales, elementos_totales = estimar_malla_3d(B, L, df_val, z_max_user, mesh_3d,
                                                       factor_dominio, factor_prof, ratio_malla)
    if nodos_totales > MAX_NODOS_MEF:
        st.sidebar.error(f"🔴 **Malla excesiva:** {nodos_totales:,} nodos (límite {MAX_NODOS_MEF:,}). "
                         "El MEF no se ejecutará.")
    elif nodos_totales > 10000:
        st.sidebar.warning(f"🟡 **Malla densa:** {nodos_totales:,} nodos · {elementos_totales:,} elem. "
                           "Puede tardar del orden de un minuto.")
    else:
        st.sidebar.success(f"🟢 **Malla ligera:** {nodos_totales:,} nodos · {elementos_totales:,} elem.")

# ── CÁLCULO ──
st.sidebar.markdown("---")
if st.sidebar.button("🚀 Calcular", type="primary", width="stretch", disabled=not datos_ok):
    with st.spinner("Calculando…"):
        tot_st, df_st = calcular_steinbrenner(p, B, L, df_val, z_max_user)
        tot_ec, df_ec = calcular_ec68(p, B, L, df_val, z_max_user, dz_sub, modo_tension)
        try:
            tot_mef, df_mef, mef_info = calcular_opensees_3d(p, B, L, df_val, z_max_user, mesh_3d,
                                                             factor_dominio, factor_prof, ratio_malla)
            mef_error = None
        except MEFError as exc:
            tot_mef, mef_info, mef_error = float("nan"), None, str(exc)
            df_mef = pd.DataFrame({"Capa": df_st["Capa"], "Δs [mm]": np.nan})
    st.session_state.calc = dict(
        B=B, L=L, p=p, D=D, NF=NF, gamma_D=gamma_D, gamma_sat_D=gamma_sat_D, df=df_val,
        zi=zi, zi_ok=zi_ok, z_max=z_max_user, s_adm=asiento_adm, criterio=criterio,
        factor_rigidez=factor_rigidez, dz_sub=dz_sub, modo_tension=modo_tension,
        factor_dominio=factor_dominio, mesh=mesh_3d, ratio=ratio_malla, factor_prof=factor_prof,
        tot_st=tot_st, df_st=df_st, tot_ec=tot_ec, df_ec=df_ec,
        tot_mef=tot_mef, df_mef=df_mef, mef_info=mef_info, mef_error=mef_error,
        cohesivos=estratos_cohesivos(df_val, z_max_user),
    )
    st.session_state.calculo_realizado = True
=======
    marcar_informe_obsoleto()


def marcar_informe_obsoleto():
>>>>>>> refs/remotes/origin/main
    if st.session_state.get("informe_generado", False):
        st.session_state.informe_stale = True
    st.session_state.informe_generado = False
    st.session_state.word_buf = None

<<<<<<< HEAD
calc = st.session_state.calc if st.session_state.calculo_realizado else None

# ── DOCUMENTACIÓN ──
st.sidebar.markdown("---")
st.sidebar.subheader("🗎 Documentación")
with st.sidebar.expander("🗂️ Identificación del informe"):
    meta_obra = st.text_input("Obra / Proyecto", value="")
    meta_peti = st.text_input("Peticionario", value="")
    meta_ref  = st.text_input("Referencia", value="GEO-XXXX-ASN-01")
    meta_autor = st.text_input("Autor", value="Dpto. Geotecnia")
meta_informe = {"obra": meta_obra, "peticionario": meta_peti, "referencia": meta_ref, "autor": meta_autor}
=======

for k, v in {"calculo_realizado": False, "informe_generado": False, "informe_stale": False,
             "word_buf": None, "mef_ok": False}.items():
    st.session_state.setdefault(k, v)

if 'df_terreno' not in st.session_state:
    st.session_state.df_terreno = pd.DataFrame({
        "Descripción":           ["Arcilla 1", "Arcilla 2", "Arcilla 3"],
        "Espesor (m)":           [1.5, 3.0, 5.0],
        "E (kPa)":               [10000.0, 15000.0, 40000.0],
        "nu":                    [0.30, 0.45, 0.25],
        "Peso Esp. (kN/m³)":     [18.0, 19.0, 21.0],
        "Peso Esp. Sat (kN/m³)": [20.0, 20.0, 22.0],
    })

# ══════════════════════════════════════════════════════════════════════════
# BARRA LATERAL
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Cálculo Asientos · MEF 3D", layout="wide", page_icon="🏗️")
st.sidebar.title("Navegación")
modo = st.sidebar.radio("Vista:", ["🧮 Panel de Cálculo", "📋 Modelo Steinbrenner", "🌐 Modelo OpenSees",
                                   "📏 Distribución de asientos", "📉 Bulbo de Presiones",
                                   "📐 Asientos Admisibles", "📖 Fundamento Teórico"])

st.sidebar.markdown("---")
st.sidebar.header("📥 Datos de Entrada")
B = st.sidebar.number_input("Ancho (B) [m]", min_value=0.1, value=2.0, step=0.1, on_change=reset_calculo)
L = st.sidebar.number_input("Longitud (L) [m]", min_value=0.1, value=3.0, step=0.1, on_change=reset_calculo)
p = st.sidebar.number_input("Presión neta (p) [kPa]", min_value=1.0, value=150.0, step=10.0, on_change=reset_calculo)
D = st.sidebar.number_input("Profundidad de apoyo (D) [m]", min_value=0.0, value=0.0, step=0.1, on_change=reset_calculo,
                            help="Cota de apoyo medida desde la superficie del terreno.")
NF = st.sidebar.number_input("Nivel freático desde superficie [m]", min_value=0.0, value=100.0, step=0.5,
                             on_change=reset_calculo, help="Un valor ≥ 100 m equivale a nivel freático sin influencia.")
if L < B:
    B, L = L, B
    st.sidebar.warning("⚠️ L<B: valores intercambiados.")
tipo_zapata = st.sidebar.radio("Tipo de zapata", ["Flexible", "Rígida"], horizontal=True, on_change=reset_calculo,
                               help="Flexible: asiento del centro. Rígida: asiento uniforme (punto característico "
                                    "en Steinbrenner; nodos con igual desplazamiento en el MEF).")
rigida = tipo_zapata == "Rígida"
if rigida:
    st.sidebar.caption("El punto 0,37B-0,37L de Steinbrenner es una aproximación; "
                       "su posición real depende de ν, L/B y del espesor compresible.")
empotramiento = st.sidebar.checkbox("Corrección por empotramiento en Steinbrenner (Mayne y Poulos)", value=False,
                                    disabled=D <= 0, on_change=reset_calculo,
                                    help="En Steinbrenner se aplica el factor I_E de forma opcional. El MEF solo "
                                         "representa la geometría excavada, sin contacto lateral ni fases constructivas.")

df_ui = st.session_state.df_terreno
errores_datos = fa.validar_estratigrafia(df_ui)
esp_total = fa.espesor_total(df_ui) if not errores_datos else 0.0
esp_bajo = esp_total - D
if not errores_datos and esp_bajo < 0.1:
    errores_datos.append("La profundidad de apoyo D alcanza o supera el espesor total de la estratigrafía.")
datos_validos = not errores_datos

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Profundidad de Cálculo")
if datos_validos:
    res_zi = fa.evaluar_z_influencia_ec7(p, B, L, df_ui, NF, D)
    zi = res_zi.profundidad
    z_max_user = st.sidebar.number_input("Profundidad de corte bajo apoyo (z_max) [m]", min_value=0.1,
                                         max_value=float(esp_bajo), value=float(min(max(zi, 0.1), esp_bajo)),
                                         step=0.1, on_change=reset_calculo)
    if res_zi.criterio_cumplido:
        st.sidebar.caption(f"z_i = {zi:.2f} m · Δσz/σ'v0 = {res_zi.ratio:.3f}")
    else:
        st.sidebar.error(
            f"El perfil termina a {zi:.2f} m bajo el apoyo sin alcanzar Δσz/σ'v0 ≤ 0,20 "
            f"(valor en el fondo: {res_zi.ratio:.3f}). Amplía la estratigrafía."
        )
else:
    res_zi, zi, z_max_user = None, 0.0, 0.1
    st.sidebar.error("Corrige la estratigrafía en el Panel de Cálculo.")

st.sidebar.markdown("---")
st.sidebar.subheader("📏 Umbral de asiento")
asiento_adm = st.sidebar.number_input(
    "Umbral admisible [mm]", min_value=1.0, value=25.0, step=1.0, on_change=marcar_informe_obsoleto,
    help="Umbral de comparación. El programa calcula asiento elástico, no consolidación ni fluencia.")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parámetros OpenSees MEF 3D")
if not OPENSEES_DISPONIBLE:
    st.sidebar.warning("⚠️ Módulo OpenSeesPy no detectado.")
graduada = st.sidebar.checkbox("Malla graduada", value=True, on_change=reset_calculo,
                               help="Malla fina bajo la zapata que crece hacia los contornos.")
factor_dominio = st.sidebar.slider("Extensión del dominio (×B/2, ×L/2)", min_value=3.0,
                                   max_value=12.0 if graduada else 8.0, value=8.0 if graduada else 5.0, step=1.0,
                                   on_change=reset_calculo)
mesh_3d = st.sidebar.number_input("Tamaño de malla bajo la zapata [m]", min_value=0.1, max_value=1.0,
                                  value=0.25 if graduada else 0.5, step=0.05, on_change=reset_calculo)
factor_prof = st.sidebar.number_input(
    "Profundidad del dominio / z_max", min_value=1.2, max_value=4.0, value=2.0, step=0.1,
    on_change=reset_calculo,
    help="La base fija del MEF se sitúa por debajo de la profundidad usada para integrar el asiento."
)
verificar_convergencia = st.sidebar.checkbox(
    "Ejecutar estudio de sensibilidad MEF", value=False, on_change=reset_calculo,
    help="Resuelve un segundo modelo con malla más fina y dominio lateral mayor. Incrementa el tiempo de cálculo."
)
ratio, tam_max = 1.3, 2.0
if graduada:
    ratio = st.sidebar.slider("Razón de crecimiento", 1.1, 1.6, 1.3, 0.05, on_change=reset_calculo)
    tam_max = st.sidebar.number_input("Tamaño máximo de elemento [m]", min_value=0.5, max_value=5.0, value=2.0,
                                      step=0.25, on_change=reset_calculo)
if factor_dominio < 4:
    st.sidebar.warning("Con factor < 4 las fronteras laterales rigidizan el modelo y subestiman el asiento.")
profundidad_eval_ok = datos_validos and res_zi.criterio_cumplido and z_max_user >= zi - 1e-9
cobertura_mef_ok = datos_validos and factor_prof * z_max_user <= esp_bajo + 1e-9
if datos_validos and not profundidad_eval_ok and res_zi.criterio_cumplido:
    st.sidebar.error("z_max no puede ser menor que z_i para la comprobación mostrada.")
if datos_validos and not cobertura_mef_ok:
    st.sidebar.error(
        f"El dominio MEF requiere {factor_prof*z_max_user:.2f} m bajo el apoyo y el perfil dispone de "
        f"{esp_bajo:.2f} m. Amplía la estratigrafía o reduce el factor de profundidad."
    )
calculo_habilitado = datos_validos and profundidad_eval_ok and cobertura_mef_ok
params_mef = dict(tamaño_malla=mesh_3d, factor_dominio=factor_dominio, factor_prof=factor_prof, D=D, rigida=rigida,
                  graduada=graduada, ratio=ratio, tamaño_max=tam_max)

if calculo_habilitado:
    nodos_totales, elementos_totales = fa.dimensiones_malla_3d(
        B, L, df_ui, z_max_user, mesh_3d, factor_dominio, factor_prof, D, graduada, ratio, tam_max)
    if nodos_totales < 15000:
        st.sidebar.success(f"🟢 **Malla ligera:** {nodos_totales:,} nodos · {elementos_totales:,} elem.")
    elif nodos_totales < 50000:
        st.sidebar.warning(f"🟡 **Malla densa:** {nodos_totales:,} nodos. Puede tardar algo.")
    else:
        st.sidebar.error(f"🔴 **Malla pesada:** {nodos_totales:,} nodos. Puede tardar bastante.")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 Calcular", type="primary", width="stretch", disabled=not calculo_habilitado):
    df_calculo = fa.normalizar_estratigrafia(df_ui.dropna(how="all").reset_index(drop=True))
    ci = {"B": B, "L": L, "p": p, "D": D, "NF": NF, "z_max": z_max_user, "zi": zi, "rigida": rigida,
          "df": df_calculo, "df_entrada": df_ui.dropna(how="all").reset_index(drop=True).copy(),
          "nu_ajustado": bool((pd.to_numeric(df_ui["nu"], errors="coerce") >= 0.5).any()),
          "zi_ratio": res_zi.ratio}
    res_st = fa.calcular_steinbrenner_zapata(p, B, L, ci["df"], z_max_user, D, rigida, empotramiento)
    try:
        with st.spinner("Resolviendo el modelo MEF 3D…"):
            res_mef = fa.calcular_opensees_3d(p, B, L, ci["df"], z_max_user, **params_mef)
        convergencia = None
        if verificar_convergencia:
            params_ref = params_mef.copy()
            params_ref["tamaño_malla"] = max(0.1, 0.75 * mesh_3d)
            params_ref["factor_dominio"] = min(12.0, factor_dominio + 2.0)
            with st.spinner("Resolviendo el modelo de sensibilidad MEF…"):
                res_ref = fa.calcular_opensees_3d(p, B, L, ci["df"], z_max_user, **params_ref)
            diferencia = abs(res_ref.total - res_mef.total) / max(abs(res_ref.total), 1e-12) * 100.0
            convergencia = {"asiento_ref_mm": res_ref.total * 1000.0, "diferencia_pct": diferencia,
                            "tamaño_malla": params_ref["tamaño_malla"],
                            "factor_dominio": params_ref["factor_dominio"]}
        st.session_state.mef_ok, st.session_state.mef_error = True, None
    except ErrorMEF as e:
        res_mef, convergencia = None, None
        st.session_state.mef_ok, st.session_state.mef_error = False, str(e)
    except Exception as e:
        res_mef, convergencia = None, None
        st.session_state.mef_ok = False
        st.session_state.mef_error = f"Fallo no controlado de OpenSees: {type(e).__name__}: {e}"

    if res_mef is not None:
        coords = {"x": res_mef.perfil_x["x [m]"].values, "y": res_mef.perfil_y["y [m]"].values}
    else:
        coords = {"x": np.linspace(0, factor_dominio * B / 2, 41), "y": np.linspace(0, factor_dominio * L / 2, 41)}
    perf_st = {e: (c, fa.perfil_steinbrenner(p, B, L, ci["df"], z_max_user, D, c, e, res_st))
               for e, c in coords.items()}
    st.session_state.update(ci=ci, res_st=res_st, res_mef=res_mef, perf_st=perf_st,
                            puntos_st=fa.asientos_puntos_steinbrenner(p, B, L, ci["df"], z_max_user, D, res_st),
                            convergencia=convergencia, calculo_realizado=True)
    marcar_informe_obsoleto()

st.sidebar.markdown("---")
st.sidebar.subheader("🗎 Documentación")
with st.sidebar.expander("🗂️ Identificación del informe"):
    meta_informe = {"obra": st.text_input("Obra / Proyecto", value=""),
                    "peticionario": st.text_input("Peticionario", value=""),
                    "referencia": st.text_input("Referencia", value="GEO-XXXX-ASN-01"),
                    "autor": st.text_input("Autor", value="Dpto. Geotecnia")}
>>>>>>> refs/remotes/origin/main

if st.session_state.get("informe_stale", False):
    st.sidebar.warning("⚠️ Los datos han cambiado. **Recalcula** y vuelve a **generar el informe**.")

<<<<<<< HEAD
if calc is None:
    if not st.session_state.get("informe_stale", False):
        st.sidebar.info("Ejecuta el cálculo para poder generar el informe.")
else:
    if st.sidebar.button("📝 Generar informe", width="stretch"):
        with st.spinner("Generando memoria de cálculo…"):
            fig_b = figura_bulbo(calc, float(calc["df"]["Espesor (m)"].sum()))
            fig_bulbo_bytes = _fig_bytes(fig_b); plt.close(fig_b)
            st.session_state.word_buf = generar_word(calc, fig_bulbo_bytes, meta=meta_informe)
        st.session_state.informe_generado = True
        st.session_state.informe_stale = False
        st.sidebar.success("✅ Informe generado.")

if st.session_state.get("informe_generado", False) and st.session_state.get("word_buf") is not None:
    st.sidebar.download_button("⬇️ Descargar informe Word", data=st.session_state.word_buf,
                               file_name="informe_comparativo.docx", width="stretch")
=======
calc_ok = st.session_state.calculo_realizado

if not calc_ok:
    if not st.session_state.get("informe_stale", False):
        st.sidebar.info("Ejecuta el cálculo para poder generar el informe.")
elif not st.session_state.mef_ok:
    st.sidebar.error("El cálculo MEF no se ha ejecutado: no se puede generar el informe ni emitir la comprobación ELS.")
elif st.sidebar.button("📝 Generar informe", width="stretch"):
    with st.spinner("Generando memoria de cálculo…"):
        st.session_state.word_buf = generar_word({
            "ci": st.session_state.ci, "res_st": st.session_state.res_st, "res_mef": st.session_state.res_mef,
            "perf_st": st.session_state.perf_st, "puntos_st": st.session_state.puntos_st,
            "convergencia": st.session_state.get("convergencia"),
            "meta": meta_informe, "s_adm": asiento_adm})
    st.session_state.informe_generado = True
    st.session_state.informe_stale = False
    st.sidebar.success("✅ Informe generado.")

if st.session_state.get("informe_generado", False) and st.session_state.get("word_buf") is not None:
    st.sidebar.download_button("⬇️ Descargar informe Word", data=st.session_state.word_buf,
                               file_name="informe_asientos.docx", width="stretch")
>>>>>>> refs/remotes/origin/main

# ══════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
st.title("🏗️ Cálculo de Asientos de cimentaciones rectangulares")
<<<<<<< HEAD
st.markdown("**Herramienta académica** · los resultados deben ser revisados por un técnico competente")
st.markdown("Según directiva ITQ404")

if modo == "🧮 Panel de Cálculo":
    st.header("1. Estratigrafía del Terreno")
    st.caption("Profundidades medidas desde la base de la zapata. «Tipo» se usa para los avisos de ELS.")
    df_edit = st.data_editor(
        st.session_state.df_terreno, num_rows="dynamic", width="stretch",
        column_config={"Tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_SUELO)})
=======
st.markdown("**Herramienta académica**")

res_st = st.session_state.get("res_st") if calc_ok else None
res_mef = st.session_state.get("res_mef") if calc_ok else None
mef_ok = calc_ok and st.session_state.mef_ok

if modo == "🧮 Panel de Cálculo":
    st.header("1. Estratigrafía del Terreno (desde la superficie)")
    df_edit = st.data_editor(st.session_state.df_terreno, num_rows="dynamic", width="stretch")
>>>>>>> refs/remotes/origin/main
    if not df_edit.equals(st.session_state.df_terreno):
        st.session_state.df_terreno = df_edit
        reset_calculo()
        st.rerun()
<<<<<<< HEAD
    for e in errores:
        st.error(e)
    for a in avisos:
        st.warning(a)

    st.markdown("---")
    st.header("2. Resultados y Comparativa")
    if calc is None:
        st.info("👈 Pulsa Calcular.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔵 Steinbrenner", _fmt_mm(calc["tot_st"]))
        c2.metric("🟢 Ec. Elástica", _fmt_mm(calc["tot_ec"]))
        c3.metric("🔴 OpenSees 3D", _fmt_mm(calc["tot_mef"]))
        if np.isfinite(calc["tot_mef"]):
            dif = (calc["tot_mef"] - calc["tot_st"]) * 1000
            pct = dif / max(abs(calc["tot_st"]) * 1000, 1e-9) * 100
            c4.metric("📊 MEF − Steinbrenner", f"{dif:+.3f} mm", f"{pct:+.1f} %", delta_color="off")
        else:
            st.error(f"❌ MEF 3D no disponible: {calc['mef_error']}")

        s_gob, origen = asiento_gobernante(calc["tot_st"], calc["tot_ec"], calc["tot_mef"],
                                           calc["criterio"], calc["factor_rigidez"])
        aprov = s_gob / calc["s_adm"] * 100
        msg = (f"Asiento de comprobación ({origen}) {s_gob:.2f} mm "
               f"{'≤' if s_gob <= calc['s_adm'] else '>'} admisible {calc['s_adm']:.0f} mm · "
               f"aprovechamiento {aprov:.0f} %.")
        if s_gob <= calc["s_adm"]:
            st.success("✅ **CUMPLE** — " + msg)
        else:
            st.error("⚠️ **REVISAR** — " + msg)
        if calc["cohesivos"]:
            st.warning("⚠️ Hay estratos cohesivos dentro de z_max (" + ", ".join(calc["cohesivos"]) + "). "
                       "El asiento calculado es elástico: si los módulos no son drenados, falta la consolidación "
                       "antes de compararlo con el asiento total admisible.")
        st.dataframe(tabla_comparativa(calc), width="stretch", hide_index=True)

# ══════════════════════════════════════════════════
# VISTA: ASIENTOS ADMISIBLES
# ══════════════════════════════════════════════════
elif modo == "📐 Asientos Admisibles":
    st.header("📐 Asientos Generales Admisibles")
    st.markdown("Tabla de referencia para fijar el **asiento admisible** en la barra lateral, según el tipo de "
                "edificio y la naturaleza del terreno. El valor elegido se emplea en la comprobación ELS y en el informe.")
    df_adm = pd.DataFrame({
=======
    for err in errores_datos:
        st.error(err)
    if "nu" in df_ui and (pd.to_numeric(df_ui["nu"], errors="coerce") >= 0.5).any():
        st.info("Los valores introducidos como ν = 0,500 se calculan como ν = 0,499 en Steinbrenner y OpenSees.")

    st.markdown("---")
    st.header("2. Resultados y Comparativa")
    if not calc_ok:
        st.info("👈 Pulsa Calcular.")
    else:
        ci = st.session_state.ci
        etiqueta_st = "punto característico" if ci["rigida"] else "centro"
        c1, c2, c3 = st.columns(3)
        c1.metric(f"🔵 Steinbrenner ({etiqueta_st})", f"{res_st.total*1000:.3f} mm")
        if res_st.I_E < 1:
            c1.caption(f"Incluye I_E = {res_st.I_E:.3f} (sin corrección: {res_st.total_sin_correccion*1000:.2f} mm)")
        if ci["rigida"]:
            c1.caption("Aproximación de Grasshoff: el punto fijo 0,37B-0,37L no es universal.")
        if mef_ok:
            c2.metric(f"🔴 OpenSees 3D ({'rígida' if ci['rigida'] else 'centro'})", f"{res_mef.total*1000:.3f} mm")
            dif = abs(res_st.total - res_mef.total) * 1000
            pct = dif / max(abs(res_st.total) * 1000, 1e-9) * 100
            c3.metric("📊 Dif (ST vs MEF)", f"{dif:.3f} mm", f"{pct:.1f}%")

            s_control_mm = max(res_st.total, res_mef.total) * 1000
            metodo_control = "Steinbrenner" if res_st.total >= res_mef.total else "OpenSees 3D"
            relacion = s_control_mm / asiento_adm * 100
            if s_control_mm <= asiento_adm:
                st.success(f"✅ **Asiento elástico dentro del umbral** — envolvente ({metodo_control}) "
                           f"{s_control_mm:.2f} mm ≤ {asiento_adm:.0f} mm · relación {relacion:.0f} %.")
            else:
                st.error(f"⚠️ **Asiento elástico: REVISAR** — envolvente ({metodo_control}) "
                         f"{s_control_mm:.2f} mm > {asiento_adm:.0f} mm · relación {relacion:.0f} %.")
            st.warning("Comparación parcial: no incluye asiento por consolidación primaria ni fluencia.")
        else:
            c2.metric("🔴 OpenSees 3D", "—")
            c3.metric("📊 Dif (ST vs MEF)", "—")
            st.error(f"⛔ **Comparación no completada** — {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')} "
                     "El asiento de Steinbrenner se muestra solo a título informativo.")

        st.dataframe(tabla_comparativa(res_st.tabla, res_mef.tabla if mef_ok else None, con_cotas=True),
                     width="stretch", hide_index=True)

elif modo == "📐 Asientos Admisibles":
    st.header("📐 Asientos Generales Admisibles")
    st.markdown("Tabla de referencia para fijar el **umbral admisible** en la barra lateral, según el tipo de "
                "edificio y la naturaleza del terreno.")
    st.dataframe(pd.DataFrame({
>>>>>>> refs/remotes/origin/main
        "Características del edificio": [
            "Obras de carácter monumental",
            "Edificios con estructura de H.A. de gran rigidez",
            "Edificios con estructura de H.A. de pequeña rigidez · Estructuras metálicas hiperestáticas · "
            "Edificios con muros de fábrica",
            "Estructuras metálicas isostáticas · Estructuras de madera · Estructuras provisionales",
        ],
        "Terreno sin cohesión [mm]": ["12", "35", "50", ">50 (con comprobación)"],
<<<<<<< HEAD
        "Terreno coherente [mm]": ["25", "50", "75", ">75 (con comprobación)"],
    })
    st.dataframe(df_adm, width="stretch", hide_index=True)
    st.info(f"**Asiento admisible fijado actualmente:** {asiento_adm:.0f} mm  "
            f"(se edita en la barra lateral, apartado «Comprobación de Servicio»).")
    st.markdown("**Notas:**")
    st.markdown(
        "- *Sin cohesión* = terrenos granulares (arenas, gravas); *coherentes* = terrenos cohesivos (arcillas, limos). "
        "Los límites admisibles son mayores en terrenos coherentes.\n"
        "- Son asientos **totales**: en terrenos cohesivos el asiento elástico calculado aquí no incluye la "
        "consolidación, salvo que se hayan empleado módulos drenados.\n"
        "- La última fila (*«con comprobación»*) no es un límite cerrado: indica que se admiten asientos mayores "
        "siempre que se justifique que la estructura los tolera.\n"
        "- En perfiles multicapa mixtos, la elección del tipo de terreno y de edificio es criterio del proyectista.")
    st.caption("Fuente: tabla de asientos generales admisibles (Jiménez Salas), de uso habitual en la práctica geotécnica.")

# ══════════════════════════════════════════════════
# VISTA: DETALLE STEINBRENNER
# ══════════════════════════════════════════════════
elif modo == "📋 Modelo Steinbrenner":
    st.header("📋 Detalle Método Steinbrenner")
    st.markdown(r"Cálculo capa a capa con las funciones de influencia $\phi_1$ y $\phi_2$ "
                r"(4 cuadrantes de $B/2 \times L/2$).")
    if calc is None:
        st.warning("⚠️ Calcula primero en el panel izquierdo.")
    else:
        df_st = calc["df_st"]
        st.markdown("##### 🔼 Valores en el Techo")
        st.dataframe(df_st[["Capa", "z Techo [m]", "m_techo", "φ1_techo", "φ2_techo", "s_techo [mm]"]],
                     width="stretch", hide_index=True)
        st.markdown("##### 🔽 Valores en la Base")
        st.dataframe(df_st[["Capa", "z Base [m]", "m_base", "φ1_base", "φ2_base", "s_base [mm]"]],
                     width="stretch", hide_index=True)
        st.markdown("##### 📊 Asiento por estrato")
        st.dataframe(df_st[["Capa", "Δs [mm]"]], width="stretch", hide_index=True)
        st.metric("🔵 Asiento Total Steinbrenner", _fmt_mm(calc["tot_st"]))

# ══════════════════════════════════════════════════
# VISTA: DETALLE EC ELÁSTICO
# ══════════════════════════════════════════════════
elif modo == "📋 Modelo Elástico":
    st.header("📋 Detalle Método Ecuación Elástica")
    st.latex(r"s = \sum_i \int_{z_{t,i}}^{z_{b,i}} \frac{\Delta\sigma_z - \nu_i(\Delta\sigma_x+\Delta\sigma_y)}{E_i}\,dz")
    if calc is None:
        st.warning("⚠️ Calcula primero.")
    else:
        df_ec = calc["df_ec"]
        tipo = ("suma horizontal exacta para el ν de cada estrato" if calc["modo_tension"] == TENSION_CONSISTENTE
                else "tensiones horizontales de Holl (ν = 0,5)")
        st.caption(f"Subcapas de **{calc['dz_sub']} m**, cuadratura de Gauss de 3 puntos, {tipo}. "
                   "Los valores medios son promedios ponderados en el espesor del estrato.")
        st.markdown("##### ⚡ Tensiones medias por capa")
        st.dataframe(df_ec[["Capa", "Sub-capas", "Δσz med [kPa]", "Δ(σx+σy) med [kPa]"]],
                     width="stretch", hide_index=True)
        st.markdown("##### 📐 Deformación unitaria media y asiento")
        st.dataframe(df_ec[["Capa", "h_ef [m]", "Sub-capas", "Δεz med [-]", "Δs [mm]"]],
                     width="stretch", hide_index=True)
        st.metric("🟢 Asiento Total Ec. Elástica", _fmt_mm(calc["tot_ec"]))

# ══════════════════════════════════════════════════
# VISTA: MODELO OPENSEES
# ══════════════════════════════════════════════════
elif modo == "🌐 Modelo OpenSees":
    st.header("🌐 Modelo de Elementos Finitos (OpenSees 3D)")
    st.markdown("El terreno se resuelve como un **medio continuo tridimensional** discretizado por el Método de los "
                "Elementos Finitos: el asiento de la zapata rectangular sale directamente del cálculo.")
    st.subheader("1. Concepto y Datos de Entrada")
    st.markdown("* **Materiales:** a cada estrato se le asigna un modelo `ElasticIsotropic` ($E$, $\\nu$).\n"
                "* **Elementos:** hexaedros de 8 nodos con formulación B-bar (`bbarBrick`), que evita el bloqueo "
                "volumétrico con $\\nu$ elevado, en un **cuarto del dominio** por doble simetría.\n"
                "* **Malla:** uniforme bajo la zapata, con el borde cargado siempre en un nodo, y en progresión "
                "geométrica hacia el contorno si el crecimiento es > 1.\n"
                "* **Carga:** presión repartida en fuerzas nodales por **áreas tributarias**, con resultante exacta "
                "$p\\cdot B\\cdot L/4$.")
    st.subheader("2. Condiciones de Contorno")
    col1, col2 = st.columns(2)
    with col1:
        st.info("📏 Simetría y campo lejano")
        st.markdown(r"Planos de simetría ($x=0$, $y=0$) y fronteras laterales: desplazamiento normal impedido, "
                    r"vertical libre.")
    with col2:
        st.info("⬇️ Base")
        st.markdown(rf"Base rígida (3 GDL empotrados) a **{factor_prof:.2f}·z_max**. El asiento de comparación es "
                    r"siempre $s(0)-s(z_{max})$, coherente con los métodos analíticos.")
    if factor_prof > 1.0:
        st.info("Con la base por debajo de z_max se informa además el asiento total en superficie. Si el perfil no "
                "llega a la base rígida, el último estrato se prolonga con sus mismas propiedades.")
    st.markdown("---")
    if calc is None:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo para visualizar la extracción de asientos.")
    elif calc["mef_info"] is None:
        st.error(f"❌ El MEF no ha podido resolverse: {calc['mef_error']}")
    else:
        info = calc["mef_info"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nodos", f"{info['n_nodos']:,}")
        m2.metric("Elementos", f"{info['n_elementos']:,}")
        m3.metric("Tiempo", f"{info['t_calculo_s']:.1f} s")
        m4.metric("Resultante", f"{info['resultante_kN']:.2f} kN",
                  f"teórica {info['resultante_teorica_kN']:.2f} kN", delta_color="off")
        st.caption(f"Solver lineal: {info['solver']}")
        st.markdown("##### 📍 Asiento por estrato (eje central)")
        st.dataframe(calc["df_mef"][["Capa", "Δs [mm]"]], width="stretch", hide_index=True)
        st.metric("🔴 Asiento OpenSees 3D (0 – z_max)", _fmt_mm(calc["tot_mef"]))
        if calc["factor_prof"] > 1.0:
            st.metric("Asiento total en superficie (hasta la base rígida)", f"{info['s_superficie_mm']:.3f} mm")
            if info["extension"]:
                st.warning("El perfil no alcanza la base rígida: el último estrato se ha prolongado.")
=======
        "Terreno cohesivos [mm]": ["25", "50", "75", ">75 (con comprobación)"],
    }), width="stretch", hide_index=True)
    st.info(f"**Umbral admisible fijado actualmente:** {asiento_adm:.0f} mm.")
    st.markdown("- *Sin cohesión* = terrenos granulares; *cohesivos* = arcillas y limos.\n"
                "- La última fila no es un límite cerrado: se admiten asientos mayores si se justifica que la "
                "estructura los tolera.\n"
                "- En perfiles mixtos, la elección es criterio del proyectista.")
    st.caption("Fuente: tabla de asientos generales admisibles (Jiménez Salas).")

elif modo == "📋 Modelo Steinbrenner":
    st.header("📋 Detalle Método Steinbrenner")
    if not calc_ok:
        st.warning("⚠️ Calcula primero en el panel izquierdo.")
    else:
        xs, ys = res_st.punto
        st.markdown(f"Punto de evaluación: **x = {xs:.2f} m, y = {ys:.2f} m** "
                    + ("(punto característico, zapata rígida)." if res_st.rigida else "(centro, zapata flexible)."))
        if res_st.rigida:
            st.warning("El punto fijo (0,37B; 0,37L) es la aproximación clásica asociada a ν = 0. "
                       "Para otros ν, relaciones L/B o espesores compresibles, su posición varía; "
                       "contrasta el resultado rígido con el MEF y un estudio de sensibilidad.")
        if res_st.I_E < 1:
            st.info(f"Factor de empotramiento I_E = {res_st.I_E:.3f} incluido en Δs.")
        st.caption("w = desplazamiento del semiespacio homogéneo con el E y ν del propio estrato. Es un valor "
                   "auxiliar: solo la diferencia Δs = w_techo − w_base es un asiento.")
        tab = res_st.tabla
        cols_t = [c for c in ["Capa", "z Techo [m]", "m_techo", "φ1_techo", "φ2_techo", "w_techo [mm]"] if c in tab]
        cols_b = [c for c in ["Capa", "z Base [m]", "m_base", "φ1_base", "φ2_base", "w_base [mm]"] if c in tab]
        st.markdown("##### 🔼 Valores en el Techo")
        st.dataframe(tab[cols_t], width="stretch", hide_index=True)
        st.markdown("##### 🔽 Valores en la Base")
        st.dataframe(tab[cols_b], width="stretch", hide_index=True)
        st.markdown("##### 📊 Asiento por estrato")
        st.dataframe(tab[["Capa", "Δs [mm]"]], width="stretch", hide_index=True)
        st.metric("🔵 Asiento Steinbrenner", f"{res_st.total*1000:.3f} mm")

elif modo == "🌐 Modelo OpenSees":
    st.header("🌐 Modelo de Elementos Finitos (OpenSees 3D)")
    st.markdown("* **Materiales:** `ElasticIsotropic` ($E$, $\\nu$).\n"
                "* **Elementos:** hexaedros de 8 nodos con formulación B-bar (`bbarBrick`) en un cuarto del dominio.\n"
                "* **Malla:** uniforme o graduada (fina bajo la zapata, creciente hacia los contornos).\n"
                "* **Zapata flexible:** presión uniforme por áreas tributarias. **Rígida:** nodos cargados con igual "
                "desplazamiento vertical (`equalDOF`, zapata rígida y lisa).\n"
                "* **Profundidad de apoyo:** si D > 0 se representa la excavación y el terreno lateral, sin contacto "
                "lateral ni fases constructivas.\n"
                "* **Contornos:** deslizaderas en simetría y fronteras laterales; la base fija se sitúa por debajo de "
                "la profundidad usada para integrar el asiento.")
    st.markdown("---")
    if not calc_ok:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo.")
    elif not mef_ok:
        st.error(f"⛔ {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')}")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nodos", f"{res_mef.n_nodos:,}")
        c2.metric("Elementos", f"{res_mef.n_elementos:,}")
        c3.metric("Base bajo apoyo", f"{res_mef.profundidad_dominio:.2f} m")
        c4.metric("Error de equilibrio", f"{res_mef.error_equilibrio:.1e}")
        st.caption(f"Tiempo de cálculo: {res_mef.tiempo:.1f} s · carga del cuarto: "
                   f"{res_mef.carga_aplicada:.2f} kN · reacción: {res_mef.reaccion_vertical:.2f} kN.")
        conv = st.session_state.get("convergencia")
        if conv:
            mensaje = (f"Sensibilidad: {conv['asiento_ref_mm']:.3f} mm con h={conv['tamaño_malla']:.3f} m y "
                       f"factor lateral {conv['factor_dominio']:.1f}; diferencia {conv['diferencia_pct']:.2f} %.")
            (st.success if conv["diferencia_pct"] <= 5.0 else st.warning)(mensaje)
        else:
            st.info("No se ha ejecutado el estudio opcional de sensibilidad de malla y dominio.")
        fig = fig_malla(st.session_state.ci, res_mef.parametros)
        st.pyplot(fig); plt.close(fig)
        st.markdown("##### 📍 Asiento por estrato (eje central)")
        st.dataframe(res_mef.tabla, width="stretch", hide_index=True)
        st.metric("🔴 Asiento OpenSees 3D", f"{res_mef.total*1000:.3f} mm")

elif modo == "📏 Distribución de asientos":
    st.header("📏 Distribución de asientos")
    if not calc_ok:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo.")
    else:
        ci = st.session_state.ci
        fig = fig_perfiles(ci, st.session_state.perf_st, res_mef if mef_ok else None)
        st.pyplot(fig); plt.close(fig)
        st.caption("Asientos a la cota de apoyo. Fuera de la zapata, Steinbrenner usa la solución flexible y, al "
                   "suponer el semiespacio homogéneo truncado, puede diferir del resultado del MEF.")
        st.markdown("##### Asientos en puntos notables")
        st.dataframe(tabla_puntos(st.session_state.puntos_st, res_mef if mef_ok else None),
                     width="stretch", hide_index=True)
>>>>>>> refs/remotes/origin/main

elif modo == "📉 Bulbo de Presiones":
    st.header("Bulbo de Presiones y Zona de Influencia")
<<<<<<< HEAD
    st.markdown(r"Tensiones bajo el centro ($\times 4$ superposición $B/2 \times L/2$). "
                r"El criterio EC7 es: $\Delta\sigma_z \leq 0.20\,\sigma'_{v0}$.")
    if not datos_ok:
        st.warning("Corrige la estratigrafía para ver el bulbo.")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            z_gr = st.slider("Profundidad máxima [m]:", 0.1, max(espesor_total, 0.2), min(max(espesor_total, 0.2), 15.0), 0.1)
            st.markdown(f"**p:** {p} kPa · **B:** {B} m · **L:** {L} m · **D:** {D} m")
            if NF < 100.0: st.markdown(f"**NF:** {NF:.1f} m desde superficie")
            st.metric("📐 z_i (EC7)", f"{zi:.2f} m")
            st.markdown("---")
            st.info("Δσz es común a los dos métodos analíticos. Las curvas de Δσx y Δσy son las de Holl (ν = 0,5); "
                    "el método elástico consistente usa la suma exacta para el ν de cada estrato.")
        with col2:
            ctx = dict(p=p, B=B, L=L, df=df_val, NF=NF, D=D, gamma_D=gamma_D, gamma_sat_D=gamma_sat_D, zi=zi)
            fig = figura_bulbo(ctx, z_gr, figsize=(9, 7))
            st.pyplot(fig); plt.close(fig)

# ══════════════════════════════════════════════════
# VISTA: FUNDAMENTO TEÓRICO
# ══════════════════════════════════════════════════
elif modo == "📖 Fundamento Teórico":
    st.header("Fundamento Teórico — Comparativa de Formulaciones")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🔵 Método 1 — Steinbrenner")
        st.markdown(r"Desplazamiento vertical del semiespacio bajo la esquina de un rectángulo $B' \times L'$; "
                    r"para el centro se superponen 4 cuadrantes con $B'=B/2$, $L'=L/2$:")
        st.latex(r"s(z) = 4\,\frac{p\,B'}{E}\left[(1-\nu^2)\,\phi_1 - (1-\nu-2\nu^2)\,\phi_2\right]")
        st.latex(r"\phi_1 = \frac{1}{\pi}\left[\ln\frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} + n\ln\frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}}\right]")
        st.latex(r"\phi_2 = \frac{m}{2\pi}\arctan\frac{n}{m\sqrt{1+m^2+n^2}}")
        st.markdown(r"Con $n = L'/B' = L/B$ y $m = z/B' = 2z/B$. El asiento de cada estrato:")
        st.latex(r"\Delta s_i = s(z_{techo}) - s(z_{base})")
    with col_b:
        st.subheader("🟢 Método 2 — Ecuación Elástica")
        st.markdown("Integración numérica de la deformación vertical en subcapas (Gauss, 3 puntos por subcapa):")
        st.latex(r"\Delta\varepsilon_z = \frac{\Delta\sigma_z - \nu(\Delta\sigma_x+\Delta\sigma_y)}{E}")
        st.markdown(r"La suma de tensiones horizontales exacta para $\nu$ arbitrario se obtiene de la tensión "
                    r"media de Boussinesq integrada sobre el rectángulo:")
        st.latex(r"\Delta\sigma_x+\Delta\sigma_y = (1+\nu)\,\frac{p}{\pi}\arctan\frac{BL}{zR_3} - \Delta\sigma_z"
                 r"\quad\text{(por esquina)}")
        st.info("Con esta suma, el método 2 coincide con Steinbrenner: sirve de verificación numérica. "
                "Con las tensiones clásicas de Holl (ν = 0,5) el asiento queda por debajo cuando ν < 0,5.")
    st.markdown("---")
    st.subheader("🔁 Tensiones de Holl bajo la esquina")
    st.markdown(r"Superposición ×4 con $B/2 \times L/2$ para obtener el **centro** de la zapata. "
                r"$\sigma_z$ es válida para cualquier $\nu$; $\sigma_x$ y $\sigma_y$ corresponden a $\nu = 0{,}5$.")
    st.latex(r"\sigma_z = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} + BL\left(\frac{1}{R_1^2}+\frac{1}{R_2^2}\right)\frac{z}{R_3}\right]")
    st.latex(r"\sigma_x = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} - \frac{BLz}{R_1^2 R_3}\right]")
    st.latex(r"\sigma_y = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} - \frac{BLz}{R_2^2 R_3}\right]")
    st.latex(r"R_1=\sqrt{L^2+z^2}\quad R_2=\sqrt{B^2+z^2}\quad R_3=\sqrt{L^2+B^2+z^2}")
    st.markdown("---")
    st.subheader("📐 Criterio de Profundidad de Influencia (UNE-EN 1997-1, 6.6.2)")
    st.latex(r"\Delta\sigma_z(z_i) \leq 0.20\,\sigma'_{v0}(z_i)")
    st.markdown(r"Con $\sigma'_{v0}$ = tensión efectiva geoestática, incluido el terreno sobre la base (D) y "
                r"considerando el nivel freático: $\gamma_i$ sobre NF y $\gamma_{sat,i} - \gamma_w$ bajo NF.")
=======
    st.markdown(r"Tensiones de Holl bajo el centro ($\times 4$ superposición $B/2 \times L/2$). "
                r"Las tensiones horizontales corresponden a $\nu = 0{,}5$. Profundidades bajo la cota de apoyo.")
    if not datos_validos:
        st.warning("Corrige la estratigrafía en el Panel de Cálculo.")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            z_gr = st.slider("Profundidad máxima [m]:", 0.5, float(max(esp_bajo, 0.5)),
                             float(min(max(esp_bajo, 0.5), 15.0)), 0.5)
            st.metric("📐 z_i (EC7)", f"{zi:.2f} m")
        with col2:
            fig = fig_bulbo(p, B, L, df_ui, NF, D, z_gr, zi)
            st.pyplot(fig); plt.close(fig)

elif modo == "📖 Fundamento Teórico":
    st.header("Fundamento Teórico")
    st.subheader("🔵 Método 1 — Steinbrenner")
    st.markdown("Desplazamiento vertical a profundidad z bajo la esquina de un rectángulo cargado, en un "
                "semiespacio elástico homogéneo:")
    st.latex(r"w(z) = \frac{p \cdot B}{E}\left[(1-\nu^2)\phi_1 - (1-\nu-2\nu^2)\phi_2\right]")
    st.latex(r"\phi_1 = \frac{1}{\pi}\left[\ln\frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} + "
             r"n\ln\frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}}\right]")
    st.latex(r"\phi_2 = \frac{m}{2\pi}\arctan\frac{n}{m\sqrt{1+m^2+n^2}}")
    st.markdown(r"Con $m = z/B$ y $n = L/B$ del rectángulo de esquina. Para un punto cualquiera $(x, y)$ se "
                r"superponen con signo los cuatro rectángulos con vértice en su vertical. El asiento de cada estrato "
                r"se evalúa con el $E$ y $\nu$ del propio estrato:")
    st.latex(r"\Delta s_i = w(x, y, z_{techo}) - w(x, y, z_{base})")
    st.info("Steinbrenner es una solución aproximada: supone la distribución de tensiones del semiespacio "
            "homogéneo y no recoge la redistribución por contraste de rigidez entre estratos ni la base rígida.")

    st.subheader("🧱 Zapata rígida — punto característico")
    st.markdown(r"El asiento de una zapata rígida coincide aproximadamente con el de la zapata flexible en el "
                r"punto característico clásico $(\pm 0{,}37\,B;\ \pm 0{,}37\,L)$ desde el centro (Grasshoff). "
                r"Estas coordenadas fijas corresponden al caso ideal con $\nu=0$; en general la posición depende "
                r"de $\nu$, $L/B$ y del espesor compresible. En el MEF la rigidez se impone directamente igualando "
                r"el desplazamiento vertical de los nodos cargados.")

    st.subheader("⬇️ Empotramiento — Mayne y Poulos (1999)")
    st.latex(r"I_E = 1 - \frac{1}{3{,}5\,e^{(1{,}22\nu - 0{,}4)}\left(\frac{B_e}{D} + 1{,}6\right)}"
             r"\qquad B_e = \sqrt{\frac{4BL}{\pi}}")
    st.markdown("Factor opcional aplicado al asiento de Steinbrenner. El MEF modela el terreno lateral y no lo "
                "aplica; su geometría excavada no reproduce contacto lateral ni fases constructivas.")

    st.markdown("---")
    st.subheader("📐 Criterio de Profundidad de Influencia (EC7)")
    st.latex(r"\Delta\sigma_z(z_i) \leq 0.20\,\sigma'_{v0}(D + z_i)")
>>>>>>> refs/remotes/origin/main

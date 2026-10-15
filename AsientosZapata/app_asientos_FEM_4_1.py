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
    OPENSEES_DISPONIBLE, ErrorMEF, LIMITES_DISTORSION_CTE, holl_centro, sigma_v0
)

AZUL, ROJO, GRIS = RGBColor(23, 54, 93), RGBColor(192, 0, 0), RGBColor(89, 89, 89)


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


def evaluar_distorsion(ci, res_st, res_mef, cfg):
    """Distorsión angular entre el centro de la zapata y un elemento vecino."""
    eje, d = cfg["eje"], cfg["distancia"]
    medio = ci["B"] / 2.0 if eje == "x" else ci["L"] / 2.0
    lim = 1.0 / LIMITES_DISTORSION_CTE[cfg["estructura"]]
    out = {"lim": lim, "den": LIMITES_DISTORSION_CTE[cfg["estructura"]], "valido": d > medio + 1e-9,
           "metodos": {}, "gobierna": None}
    if not out["valido"]:
        return out

    x, y = (d, 0.0) if eje == "x" else (0.0, d)
    s_ind = fa.asiento_steinbrenner_punto(ci["p"], ci["B"], ci["L"], ci["df"], ci["z_max"], ci["D"], x, y) * 1000
    ds, beta = fa.distorsion_angular(res_st.total * 1000, s_ind, cfg["s_vecino"], d)
    out["metodos"]["Steinbrenner"] = {"s_propio": res_st.total * 1000, "s_inducido": s_ind, "ds": ds, "beta": beta}
    out["gobierna"] = "Steinbrenner"

    if res_mef is not None:
        perfil = res_mef.perfil_x if eje == "x" else res_mef.perfil_y
        ext = res_mef.extension_x if eje == "x" else res_mef.extension_y
        out["fiable_mef"] = d <= 0.6 * ext
        if out["fiable_mef"]:
            s_ind_m = float(np.interp(d, perfil.iloc[:, 0].values, perfil["s [mm]"].values))
            ds_m, beta_m = fa.distorsion_angular(res_mef.total * 1000, s_ind_m, cfg["s_vecino"], d)
            out["metodos"]["OpenSees 3D"] = {"s_propio": res_mef.total * 1000, "s_inducido": s_ind_m,
                                             "ds": ds_m, "beta": beta_m}
            out["gobierna"] = "OpenSees 3D"
    gob = out["metodos"][out["gobierna"]]
    out["cumple"] = gob["beta"] <= lim
    return out


def tabla_distorsion(ev):
    filas = []
    for metodo, r in ev["metodos"].items():
        filas.append({"Método": metodo,
                      "s zapata [mm]": round(r["s_propio"], 2),
                      "s inducido en vecino [mm]": round(r["s_inducido"], 2),
                      "Δs [mm]": round(r["ds"], 2),
                      "β": f"1/{1/r['beta']:.0f}" if r["beta"] > 0 else "0",
                      "Límite CTE": f"1/{ev['den']}",
                      "Veredicto": "CUMPLE" if r["beta"] <= ev["lim"] else "NO CUMPLE"})
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


def fig_perfiles(ci, perf_st, res_mef, cfg=None):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, eje, medio in [(axes[0], "x", ci["B"] / 2), (axes[1], "y", ci["L"] / 2)]:
        c_st, s_st = perf_st[eje]
        ax.axvspan(0, medio, color='0.9', label='Zapata')
        ax.plot(c_st, s_st, color='tab:blue', lw=2, label='Steinbrenner')
        if res_mef is not None:
            pm = res_mef.perfil_x if eje == "x" else res_mef.perfil_y
            ax.plot(pm.iloc[:, 0], pm["s [mm]"], color='tab:red', lw=1.5, ls='--', marker='.', ms=4,
                    label='OpenSees 3D')
        if cfg is not None and cfg["eje"] == eje:
            ax.axvline(cfg["distancia"], color='green', ls=':', lw=1.5, label='Elemento vecino')
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
    meta, mp, ev, cfg = ctx["meta"], res_mef.parametros, ctx["dist"], ctx["cfg_dist"]
    B, L, p, D, NF, z_max, zi = ci["B"], ci["L"], ci["p"], ci["D"], ci["NF"], ci["z_max"], ci["zi"]
    rigida = ci["rigida"]
    tipo = "rígida" if rigida else "flexible"
    fecha = datetime.now().strftime("%d/%m/%Y — %H:%M")
    obra = meta.get("obra") or "[Denominación de la obra]"
    peticionario = meta.get("peticionario") or "[Peticionario]"
    referencia = meta.get("referencia") or "GEO-XXXX-ASN-01"
    autor = meta.get("autor") or "Dpto. Geotecnia"
    revision = meta.get("revision") or "00 — Emisión inicial"

    s_st, s_mef = res_st.total * 1000.0, res_mef.total * 1000.0
    dif_mef_st = abs(s_mef - s_st) / max(abs(s_st), 1e-9) * 100.0
    lim_els = float(ctx["s_adm"])
    cumple_els = s_mef <= lim_els

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
    h1f.name = 'Calibri Light'; h1f.size = Pt(14); h1f.color.rgb = AZUL; h1f.bold = True

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
    _body(doc, f"El presente documento recoge el cálculo del asiento de una cimentación superficial rectangular "
               f"{tipo} sometida a carga vertical centrada, mediante dos formulaciones independientes: el método "
               f"de Steinbrenner y un modelo tridimensional de elementos finitos (OpenSeesPy). Se evalúan además la "
               f"distribución de asientos y la distorsión angular respecto a un elemento vecino.")
    _h2(doc, '1.2 Alcance: asiento elástico / inmediato')
    _body(doc, "Ambos métodos parten de la teoría de la elasticidad lineal. El resultado corresponde al ASIENTO "
               "ELÁSTICO (inmediato). No incluye la consolidación primaria ni la secundaria.")
    doc.add_page_break()

    # ── 2. NORMATIVA
    doc.add_heading('2. Normativa y referencias', level=1)
    _bullets(doc, [
        "CTE DB-SE-C «Seguridad estructural – Cimientos»: estados límite de servicio; valores límite de "
        "distorsión angular (tabla 2.2).",
        "UNE-EN 1997-1 (Eurocódigo 7), apartado 6.6.2: criterio de profundidad de influencia (Δσz ≤ 0,20·σ′v0).",
        "Holl (1940): incrementos de tensión bajo la esquina de un rectángulo cargado.",
        "Steinbrenner / Bowles: solución elástica aproximada del asiento de un estrato de espesor finito.",
        "Grasshoff: punto característico para el asiento de cimentaciones rígidas.",
        "Mayne y Poulos (1999): factor de corrección por empotramiento I_E.",
        "OpenSeesPy: elementos finitos; hexaedro de 8 nodos con formulación B-bar (bbarBrick).",
    ])
    doc.add_page_break()

    # ── 3. DATOS
    doc.add_heading('3. Datos de partida', level=1)
    _h2(doc, '3.1 Geometría, acciones y profundidades')
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
    _add_styled_table(doc, ci["df"], '3.2 Estratigrafía del perfil geotécnico (desde la superficie)')
    doc.add_page_break()

    # ── 4. HIPÓTESIS
    doc.add_heading('4. Hipótesis y modelo de cálculo', level=1)
    _h2(doc, '4.1 Base común: elasticidad lineal')
    _body(doc, "Ambos métodos asumen un terreno elástico lineal, isótropo, caracterizado por (E, ν) en cada estrato, "
               "con base rígida en z_max.")
    _h2(doc, '4.2 Hipótesis de cada método')
    _bullets(doc, [
        "Steinbrenner: solución aproximada que supone la distribución de tensiones del semiespacio homogéneo; no "
        "recoge la redistribución de tensiones por contraste de rigidez entre estratos ni la base rígida."
        + (" El asiento de la zapata rígida se evalúa en el punto característico (0,37·B; 0,37·L)." if rigida else
           " Se evalúa el asiento del centro de la zapata flexible."),
        "MEF 3D (OpenSees): continuo tridimensional con hexaedros bbarBrick, cuarto de dominio por doble simetría y "
        "base rígida en z_max."
        + (" Zapata rígida y lisa: los nodos cargados comparten el desplazamiento vertical." if rigida else
           " Zapata flexible: presión uniforme.")
        + (f" Se modela el terreno lateral por encima de la cota de apoyo (D = {D:.2f} m) con la excavación vaciada."
           if D > 0 else ""),
    ])
    doc.add_page_break()

    # ── 5. PROFUNDIDAD DE INFLUENCIA
    doc.add_heading('5. Profundidad de influencia (EC7)', level=1)
    _body(doc, "La profundidad de cálculo se acota con el criterio del Eurocódigo 7: se considera despreciable la "
               "contribución al asiento por debajo de la cota z_i en la que el incremento de tensión vertical bajo el "
               "centro cae por debajo del 20 % de la tensión efectiva geostática. σ′v0 incluye las tierras situadas "
               "por encima de la cota de apoyo.")
    _body(doc, "Δσz(z_i) ≤ 0,20 · σ′v0(D + z_i)", bold=True)
    _body(doc, f"Para el caso analizado resulta z_i = {zi:.2f} m bajo la cota de apoyo, adoptándose z_max = {z_max:.2f} m.")
    doc.add_page_break()

    # ── 6. STEINBRENNER
    doc.add_heading('6. Método 1 — Steinbrenner', level=1)
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
    tot1 = doc.add_paragraph(); tot1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = tot1.add_run(f'Asiento Steinbrenner: {s_st:.3f} mm'); r.bold = True; r.font.color.rgb = AZUL
    doc.add_page_break()

    # ── 7. MEF
    doc.add_heading('7. Método 2 — MEF 3D (OpenSees)', level=1)
    _h2(doc, '7.1 Descripción del modelo')
    _body(doc, "Hexaedros de 8 nodos con formulación B-bar (bbarBrick), adecuada para ν próximos a 0,5. Cuarto de "
               "dominio por doble simetría. En los planos de simetría y en las fronteras laterales se impide el "
               "desplazamiento normal; en la base (z_max bajo la cota de apoyo) se empotran los tres grados de libertad.")
    _bullets(doc, [
        f"Malla {'graduada' if mp['graduada'] else 'uniforme'}: tamaño bajo la zapata {mp['tamaño_malla']:.2f} m"
        + (f", crecimiento ×{mp['ratio']:.2f} por elemento hasta {mp['tamaño_max']:.2f} m" if mp['graduada'] else "")
        + ".",
        f"Extensión lateral: ×{mp['factor_dominio']:.0f} (B/2, L/2) → {res_mef.extension_x:.2f} m × "
        f"{res_mef.extension_y:.2f} m en el cuarto modelado.",
        f"Tamaño del modelo: {res_mef.n_nodos:,} nodos y {res_mef.n_elementos:,} elementos "
        f"(resuelto en {res_mef.tiempo:.1f} s).",
        "Carga: " + ("zapata rígida y lisa (nodos cargados con igual desplazamiento vertical, equalDOF)." if rigida
                     else "presión uniforme repartida en fuerzas nodales por áreas tributarias."),
    ] + ([f"Empotramiento: terreno lateral modelado entre la superficie y la cota de apoyo (D = {D:.2f} m), con la "
          f"excavación ocupada por la zapata vaciada."] if D > 0 else []))
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

    # ── 9. VALIDACIÓN
    doc.add_heading('9. Validación', level=1)
    _body(doc, "El código de cálculo dispone de pruebas automáticas que verifican: (a) las funciones de Steinbrenner, "
               "bajo la esquina y en puntos exteriores, frente a la integración numérica de la solución de Boussinesq; "
               "(b) que el asiento total de cada método coincide con la suma de los asientos por estrato; (c) la "
               "concordancia del MEF 3D con Steinbrenner en un estrato homogéneo, para zapata flexible (centro) y "
               "rígida (punto característico); (d) la reducción del asiento por empotramiento en el MEF frente al "
               "factor de Mayne y Poulos; y (e) la convergencia de la malla graduada frente a una malla de referencia.")
    doc.add_page_break()

    # ── 10. ELS ASIENTO TOTAL
    doc.add_heading('10. Comprobación de asiento total (ELS)', level=1)
    _body(doc, f"Se compara el asiento obtenido con el MEF 3D con el asiento admisible adoptado ({lim_els:.0f} mm).")
    _veredicto(doc, [('Comprobación', 'Obtenido', 'Admisible', 'Veredicto'),
                     ('Asiento total (MEF 3D)', f'{s_mef:.2f} mm', f'{lim_els:.0f} mm',
                      'CUMPLE' if cumple_els else 'REVISAR')])
    _body(doc, f"Aprovechamiento: {s_mef / lim_els * 100:.0f} % del asiento admisible.", gray=True, size=9)
    doc.add_page_break()

    # ── 11. DISTRIBUCIÓN Y DISTORSIÓN
    doc.add_heading('11. Distribución de asientos y distorsión angular', level=1)
    _add_styled_table(doc, tabla_puntos(ctx["puntos_st"], res_mef), '11.1 Asientos en puntos notables (cota de apoyo)')
    _figura(doc, _fig_bytes(fig_perfiles(ci, ctx["perf_st"], res_mef, cfg)),
            "Perfiles de asiento a la cota de apoyo según los ejes de la zapata.", 16)
    _h2(doc, '11.2 Distorsión angular respecto al elemento vecino')
    eje_txt = "transversal (según B)" if cfg["eje"] == "x" else "longitudinal (según L)"
    _body(doc, f"Elemento vecino en dirección {eje_txt}, a {cfg['distancia']:.2f} m entre ejes, con un asiento propio "
               f"de {cfg['s_vecino']:.1f} mm. Tipo de estructura: {cfg['estructura']} (límite 1/{ev['den']}, CTE "
               f"DB-SE-C tabla 2.2). Se incluye el asiento que esta zapata induce en el vecino, pero no el que el "
               f"vecino induce sobre esta zapata.")
    if not ev["valido"]:
        _body(doc, "La distancia indicada queda dentro de la propia zapata: comprobación no realizada.", bold=True)
    else:
        _add_styled_table(doc, tabla_distorsion(ev), '')
        if ev.get("fiable_mef") is False:
            _body(doc, "El elemento vecino queda fuera de la zona fiable del dominio MEF (60 % de la extensión "
                       "lateral): la comprobación se realiza con Steinbrenner.", gray=True, size=9)
        _body(doc, f"Veredicto ({ev['gobierna']}): {'CUMPLE' if ev['cumple'] else 'NO CUMPLE'}.", bold=True)
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
    marcar_informe_obsoleto()


def marcar_informe_obsoleto():
    if st.session_state.get("informe_generado", False):
        st.session_state.informe_stale = True
    st.session_state.informe_generado = False
    st.session_state.word_buf = None


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
                                   "📏 Distribución y distorsión", "📉 Bulbo de Presiones",
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
empotramiento = st.sidebar.checkbox("Corrección por empotramiento en Steinbrenner (Mayne y Poulos)", value=False,
                                    disabled=D <= 0, on_change=reset_calculo,
                                    help="El MEF modela el empotramiento directamente; en Steinbrenner se aplica el "
                                         "factor I_E de forma opcional.")

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
    zi = fa.z_influencia_ec7(p, B, L, df_ui, NF, D)
    z_max_user = st.sidebar.number_input("Profundidad de corte bajo apoyo (z_max) [m]", min_value=0.1,
                                         max_value=float(esp_bajo), value=float(min(max(zi, 0.1), esp_bajo)),
                                         step=0.1, on_change=reset_calculo)
    st.sidebar.caption(f"z_i (EC7) = {zi:.2f} m bajo la cota de apoyo")
else:
    zi, z_max_user = 0.0, 0.1
    st.sidebar.error("Corrige la estratigrafía en el Panel de Cálculo.")

st.sidebar.markdown("---")
st.sidebar.subheader("✅ Comprobación de Servicio (ELS)")
asiento_adm = st.sidebar.number_input(
    "Asiento admisible [mm]", min_value=1.0, value=25.0, step=1.0, on_change=marcar_informe_obsoleto,
    help="Asiento total máximo admisible. Consulta la pestaña «📐 Asientos Admisibles» para referencias.")
with st.sidebar.expander("📏 Distorsión angular (CTE)"):
    estructura = st.selectbox("Tipo de estructura", list(LIMITES_DISTORSION_CTE.keys()), index=1,
                              on_change=marcar_informe_obsoleto)
    eje_txt = st.radio("Dirección del elemento vecino", ["Transversal (x, según B)", "Longitudinal (y, según L)"],
                       on_change=marcar_informe_obsoleto)
    distancia = st.number_input("Distancia entre ejes [m]", min_value=0.1, value=4.0, step=0.5,
                                on_change=marcar_informe_obsoleto)
    s_vecino = st.number_input("Asiento propio del vecino [mm]", min_value=0.0, value=0.0, step=1.0,
                               on_change=marcar_informe_obsoleto,
                               help="Asiento del elemento vecino debido a su propia carga.")
cfg_dist = {"estructura": estructura, "eje": "x" if eje_txt.startswith("Transversal") else "y",
            "distancia": distancia, "s_vecino": s_vecino}

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
ratio, tam_max = 1.3, 2.0
if graduada:
    ratio = st.sidebar.slider("Razón de crecimiento", 1.1, 1.6, 1.3, 0.05, on_change=reset_calculo)
    tam_max = st.sidebar.number_input("Tamaño máximo de elemento [m]", min_value=0.5, max_value=5.0, value=2.0,
                                      step=0.25, on_change=reset_calculo)
if factor_dominio < 4:
    st.sidebar.warning("Con factor < 4 las fronteras laterales rigidizan el modelo y subestiman el asiento.")
params_mef = dict(tamaño_malla=mesh_3d, factor_dominio=factor_dominio, factor_prof=1.0, D=D, rigida=rigida,
                  graduada=graduada, ratio=ratio, tamaño_max=tam_max)

if datos_validos:
    nodos_totales, elementos_totales = fa.dimensiones_malla_3d(
        B, L, df_ui, z_max_user, mesh_3d, factor_dominio, 1.0, D, graduada, ratio, tam_max)
    if nodos_totales < 15000:
        st.sidebar.success(f"🟢 **Malla ligera:** {nodos_totales:,} nodos · {elementos_totales:,} elem.")
    elif nodos_totales < 50000:
        st.sidebar.warning(f"🟡 **Malla densa:** {nodos_totales:,} nodos. Puede tardar algo.")
    else:
        st.sidebar.error(f"🔴 **Malla pesada:** {nodos_totales:,} nodos. Puede tardar bastante.")

st.sidebar.markdown("---")
if st.sidebar.button("🚀 Calcular", type="primary", width="stretch", disabled=not datos_validos):
    ci = {"B": B, "L": L, "p": p, "D": D, "NF": NF, "z_max": z_max_user, "zi": zi, "rigida": rigida,
          "df": df_ui.dropna(how="all").reset_index(drop=True).copy()}
    res_st = fa.calcular_steinbrenner_zapata(p, B, L, ci["df"], z_max_user, D, rigida, empotramiento)
    try:
        with st.spinner("Resolviendo el modelo MEF 3D…"):
            res_mef = fa.calcular_opensees_3d(p, B, L, ci["df"], z_max_user, **params_mef)
        st.session_state.mef_ok, st.session_state.mef_error = True, None
    except ErrorMEF as e:
        res_mef = None
        st.session_state.mef_ok, st.session_state.mef_error = False, str(e)

    if res_mef is not None:
        coords = {"x": res_mef.perfil_x["x [m]"].values, "y": res_mef.perfil_y["y [m]"].values}
    else:
        coords = {"x": np.linspace(0, factor_dominio * B / 2, 41), "y": np.linspace(0, factor_dominio * L / 2, 41)}
    perf_st = {e: (c, fa.perfil_steinbrenner(p, B, L, ci["df"], z_max_user, D, c, e, res_st))
               for e, c in coords.items()}
    st.session_state.update(ci=ci, res_st=res_st, res_mef=res_mef, perf_st=perf_st,
                            puntos_st=fa.asientos_puntos_steinbrenner(p, B, L, ci["df"], z_max_user, D, res_st),
                            calculo_realizado=True)
    marcar_informe_obsoleto()

st.sidebar.markdown("---")
st.sidebar.subheader("🗎 Documentación")
with st.sidebar.expander("🗂️ Identificación del informe"):
    meta_informe = {"obra": st.text_input("Obra / Proyecto", value=""),
                    "peticionario": st.text_input("Peticionario", value=""),
                    "referencia": st.text_input("Referencia", value="GEO-XXXX-ASN-01"),
                    "autor": st.text_input("Autor", value="Dpto. Geotecnia")}

if st.session_state.get("informe_stale", False):
    st.sidebar.warning("⚠️ Los datos han cambiado. **Recalcula** y vuelve a **generar el informe**.")

calc_ok = st.session_state.calculo_realizado
if calc_ok:
    ev_dist = evaluar_distorsion(st.session_state.ci, st.session_state.res_st, st.session_state.res_mef, cfg_dist)

if not calc_ok:
    if not st.session_state.get("informe_stale", False):
        st.sidebar.info("Ejecuta el cálculo para poder generar el informe.")
elif not st.session_state.mef_ok:
    st.sidebar.error("El cálculo MEF no se ha ejecutado: no se puede generar el informe ni emitir la comprobación ELS.")
elif st.sidebar.button("📝 Generar informe", width="stretch"):
    with st.spinner("Generando memoria de cálculo…"):
        st.session_state.word_buf = generar_word({
            "ci": st.session_state.ci, "res_st": st.session_state.res_st, "res_mef": st.session_state.res_mef,
            "perf_st": st.session_state.perf_st, "puntos_st": st.session_state.puntos_st, "dist": ev_dist,
            "cfg_dist": cfg_dist, "meta": meta_informe, "s_adm": asiento_adm})
    st.session_state.informe_generado = True
    st.session_state.informe_stale = False
    st.sidebar.success("✅ Informe generado.")

if st.session_state.get("informe_generado", False) and st.session_state.get("word_buf") is not None:
    st.sidebar.download_button("⬇️ Descargar informe Word", data=st.session_state.word_buf,
                               file_name="informe_asientos.docx", width="stretch")

# ══════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
st.title("🏗️ Cálculo de Asientos de cimentaciones rectangulares")
st.markdown("**Herramienta académica**")

res_st = st.session_state.get("res_st") if calc_ok else None
res_mef = st.session_state.get("res_mef") if calc_ok else None
mef_ok = calc_ok and st.session_state.mef_ok

if modo == "🧮 Panel de Cálculo":
    st.header("1. Estratigrafía del Terreno (desde la superficie)")
    df_edit = st.data_editor(st.session_state.df_terreno, num_rows="dynamic", width="stretch")
    if not df_edit.equals(st.session_state.df_terreno):
        st.session_state.df_terreno = df_edit
        reset_calculo()
        st.rerun()
    for err in errores_datos:
        st.error(err)

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
        if mef_ok:
            c2.metric(f"🔴 OpenSees 3D ({'rígida' if ci['rigida'] else 'centro'})", f"{res_mef.total*1000:.3f} mm")
            dif = abs(res_st.total - res_mef.total) * 1000
            pct = dif / max(abs(res_st.total) * 1000, 1e-9) * 100
            c3.metric("📊 Dif (ST vs MEF)", f"{dif:.3f} mm", f"{pct:.1f}%")

            s_gob_mm = res_mef.total * 1000
            aprov = s_gob_mm / asiento_adm * 100
            if s_gob_mm <= asiento_adm:
                st.success(f"✅ **Asiento total: CUMPLE** — MEF 3D {s_gob_mm:.2f} mm ≤ admisible "
                           f"{asiento_adm:.0f} mm · aprovechamiento {aprov:.0f} %.")
            else:
                st.error(f"⚠️ **Asiento total: REVISAR** — MEF 3D {s_gob_mm:.2f} mm > admisible "
                         f"{asiento_adm:.0f} mm · aprovechamiento {aprov:.0f} %.")
        else:
            c2.metric("🔴 OpenSees 3D", "—")
            c3.metric("📊 Dif (ST vs MEF)", "—")
            st.error(f"⛔ **ELS NO EVALUADO** — {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')} "
                     "El asiento de Steinbrenner se muestra solo a título informativo.")

        if ev_dist["valido"]:
            g = ev_dist["metodos"][ev_dist["gobierna"]]
            txt = (f"**Distorsión angular ({ev_dist['gobierna']}):** β = 1/{1/g['beta']:.0f} frente a límite "
                   f"1/{ev_dist['den']}" if g["beta"] > 0 else "**Distorsión angular:** β = 0")
            (st.success if ev_dist["cumple"] else st.error)(("✅ " if ev_dist["cumple"] else "⚠️ ") + txt +
                                                             " · detalle en «📏 Distribución y distorsión».")
        else:
            st.warning("La distancia al elemento vecino queda dentro de la zapata: distorsión no evaluada.")

        st.dataframe(tabla_comparativa(res_st.tabla, res_mef.tabla if mef_ok else None, con_cotas=True),
                     width="stretch", hide_index=True)

elif modo == "📐 Asientos Admisibles":
    st.header("📐 Asientos Generales Admisibles")
    st.markdown("Tabla de referencia para fijar el **asiento admisible** en la barra lateral, según el tipo de "
                "edificio y la naturaleza del terreno.")
    st.dataframe(pd.DataFrame({
        "Características del edificio": [
            "Obras de carácter monumental",
            "Edificios con estructura de H.A. de gran rigidez",
            "Edificios con estructura de H.A. de pequeña rigidez · Estructuras metálicas hiperestáticas · "
            "Edificios con muros de fábrica",
            "Estructuras metálicas isostáticas · Estructuras de madera · Estructuras provisionales",
        ],
        "Terreno sin cohesión [mm]": ["12", "35", "50", ">50 (con comprobación)"],
        "Terreno cohesivos [mm]": ["25", "50", "75", ">75 (con comprobación)"],
    }), width="stretch", hide_index=True)
    st.info(f"**Asiento admisible fijado actualmente:** {asiento_adm:.0f} mm.")
    st.markdown("- *Sin cohesión* = terrenos granulares; *cohesivos* = arcillas y limos.\n"
                "- La última fila no es un límite cerrado: se admiten asientos mayores si se justifica que la "
                "estructura los tolera.\n"
                "- En perfiles mixtos, la elección es criterio del proyectista.")
    st.caption("Fuente: tabla de asientos generales admisibles (Jiménez Salas).")
    st.subheader("Distorsión angular — CTE DB-SE-C, tabla 2.2")
    st.dataframe(pd.DataFrame({"Tipo de estructura": list(LIMITES_DISTORSION_CTE.keys()),
                               "Límite": [f"1/{d}" for d in LIMITES_DISTORSION_CTE.values()]}),
                 width="stretch", hide_index=True)

elif modo == "📋 Modelo Steinbrenner":
    st.header("📋 Detalle Método Steinbrenner")
    if not calc_ok:
        st.warning("⚠️ Calcula primero en el panel izquierdo.")
    else:
        xs, ys = res_st.punto
        st.markdown(f"Punto de evaluación: **x = {xs:.2f} m, y = {ys:.2f} m** "
                    + ("(punto característico, zapata rígida)." if res_st.rigida else "(centro, zapata flexible)."))
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
                "* **Empotramiento:** si D > 0 se modela el terreno lateral y se vacía la excavación.\n"
                "* **Contornos:** deslizaderas en simetría y fronteras laterales; base empotrada en z_max bajo apoyo.")
    st.markdown("---")
    if not calc_ok:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo.")
    elif not mef_ok:
        st.error(f"⛔ {st.session_state.get('mef_error', 'El cálculo MEF no se ha ejecutado.')}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Nodos", f"{res_mef.n_nodos:,}")
        c2.metric("Elementos", f"{res_mef.n_elementos:,}")
        c3.metric("Tiempo de cálculo", f"{res_mef.tiempo:.1f} s")
        fig = fig_malla(st.session_state.ci, res_mef.parametros)
        st.pyplot(fig); plt.close(fig)
        st.markdown("##### 📍 Asiento por estrato (eje central)")
        st.dataframe(res_mef.tabla, width="stretch", hide_index=True)
        st.metric("🔴 Asiento OpenSees 3D", f"{res_mef.total*1000:.3f} mm")

elif modo == "📏 Distribución y distorsión":
    st.header("📏 Distribución de asientos y distorsión angular")
    if not calc_ok:
        st.warning("⚠️ Ejecuta el cálculo en el panel izquierdo.")
    else:
        ci = st.session_state.ci
        fig = fig_perfiles(ci, st.session_state.perf_st, res_mef if mef_ok else None, cfg_dist)
        st.pyplot(fig); plt.close(fig)
        st.caption("Asientos a la cota de apoyo. Fuera de la zapata, Steinbrenner usa la solución flexible y, al "
                   "suponer el semiespacio homogéneo truncado, tiende a quedarse corto frente al MEF; por eso la "
                   "distorsión se evalúa con el MEF siempre que el vecino quede dentro de su zona fiable.")
        st.markdown("##### Asientos en puntos notables")
        st.dataframe(tabla_puntos(st.session_state.puntos_st, res_mef if mef_ok else None),
                     width="stretch", hide_index=True)
        st.markdown("##### Distorsión angular respecto al elemento vecino")
        st.markdown(f"Vecino a **{cfg_dist['distancia']:.2f} m** entre ejes ({eje_txt.lower()}), asiento propio "
                    f"**{cfg_dist['s_vecino']:.1f} mm**. Límite CTE: **1/{ev_dist['den']}** ({estructura.lower()}). "
                    "Se configura en la barra lateral, apartado «📏 Distorsión angular».")
        if not ev_dist["valido"]:
            st.warning("La distancia indicada queda dentro de la propia zapata.")
        else:
            st.dataframe(tabla_distorsion(ev_dist), width="stretch", hide_index=True)
            if ev_dist.get("fiable_mef") is False:
                st.info("El vecino queda fuera del 60 % de la extensión del dominio MEF: gobierna Steinbrenner. "
                        "Amplía el dominio para evaluarlo con el MEF.")
            (st.success if ev_dist["cumple"] else st.error)(
                f"Veredicto ({ev_dist['gobierna']}): {'CUMPLE' if ev_dist['cumple'] else 'NO CUMPLE'}")
        st.caption("Se incluye el asiento que esta zapata induce en el vecino, pero no el que el vecino induce "
                   "sobre esta zapata.")

elif modo == "📉 Bulbo de Presiones":
    st.header("Bulbo de Presiones y Zona de Influencia")
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
                r"punto característico $(\pm 0{,}37\,B;\ \pm 0{,}37\,L)$ desde el centro (Grasshoff). En el MEF la "
                r"rigidez se impone directamente igualando el desplazamiento vertical de los nodos cargados.")

    st.subheader("⬇️ Empotramiento — Mayne y Poulos (1999)")
    st.latex(r"I_E = 1 - \frac{1}{3{,}5\,e^{(1{,}22\nu - 0{,}4)}\left(\frac{B_e}{D} + 1{,}6\right)}"
             r"\qquad B_e = \sqrt{\frac{4BL}{\pi}}")
    st.markdown("Factor opcional aplicado al asiento de Steinbrenner. El MEF modela el terreno lateral y no lo "
                "necesita.")

    st.subheader("📏 Distorsión angular — CTE DB-SE-C")
    st.latex(r"\beta = \frac{\left|\,s_{zapata} - (s_{vecino} + s_{inducido})\,\right|}{d}")
    st.markdown("Se compara con los valores límite de la tabla 2.2 del DB-SE-C.")

    st.markdown("---")
    st.subheader("📐 Criterio de Profundidad de Influencia (EC7)")
    st.latex(r"\Delta\sigma_z(z_i) \leq 0.20\,\sigma'_{v0}(D + z_i)")

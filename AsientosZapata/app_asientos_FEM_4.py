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
    meta, mp = ctx["meta"], res_mef.parametros
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
    s_control = max(s_st, s_mef)
    metodo_control = "Steinbrenner" if s_st >= s_mef else "OpenSees 3D"
    lim_els = float(ctx["s_adm"])
    dentro_umbral = s_control <= lim_els

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
    _body(doc, f"El presente documento recoge el cálculo del asiento de una cimentación superficial rectangular "
               f"{tipo} sometida a carga vertical centrada, mediante dos formulaciones independientes: el método "
               f"de Steinbrenner y un modelo tridimensional de elementos finitos (OpenSeesPy). Se evalúa además la "
               f"distribución de asientos en la cota de apoyo.")
    _h2(doc, '1.2 Alcance: asiento elástico / inmediato')
    _body(doc, "Ambos métodos parten de la teoría de la elasticidad lineal. El resultado corresponde al ASIENTO "
               "ELÁSTICO (inmediato). No incluye la consolidación primaria ni la secundaria.")
    doc.add_page_break()

    # ── 2. NORMATIVA
    doc.add_heading('2. Normativa y referencias', level=1)
    _bullets(doc, [
        "CTE DB-SE-C «Seguridad estructural – Cimientos»: estados límite de servicio.",
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
    _add_styled_table(doc, ci.get("df_entrada", ci["df"]), '3.2 Estratigrafía del perfil geotécnico (desde la superficie)')
    if ci.get("nu_ajustado"):
        _body(doc, "Convención numérica: los valores introducidos como ν = 0,500 se han evaluado como ν = 0,499 "
                   "en ambos métodos para evitar la singularidad de la matriz constitutiva.", gray=True, size=9)
    doc.add_page_break()

    # ── 4. HIPÓTESIS
    doc.add_heading('4. Hipótesis y modelo de cálculo', level=1)
    _h2(doc, '4.1 Base común: elasticidad lineal')
    _body(doc, "Ambos métodos asumen un terreno elástico lineal, isótropo, caracterizado por (E, ν) en cada estrato, "
               "sin reproducir consolidación primaria, fluencia ni dependencia de la rigidez con el nivel tensional.")
    _h2(doc, '4.2 Hipótesis de cada método')
    _bullets(doc, [
        "Steinbrenner: solución aproximada que supone la distribución de tensiones del semiespacio homogéneo; no "
        "recoge la redistribución de tensiones por contraste de rigidez entre estratos ni la base rígida."
        + (" El asiento de la zapata rígida se evalúa en el punto característico (0,37·B; 0,37·L)." if rigida else
           " Se evalúa el asiento del centro de la zapata flexible."),
        "MEF 3D (OpenSees): continuo tridimensional con hexaedros bbarBrick y cuarto de dominio por doble simetría. "
        f"La base fija se sitúa a {mp['factor_prof']:.2f}·z_max bajo el apoyo."
        + (" Zapata rígida y lisa: los nodos cargados comparten el desplazamiento vertical." if rigida else
           " Zapata flexible: presión uniforme.")
        + (f" Para D = {D:.2f} m se representa la geometría excavada y el terreno lateral, sin contacto lateral "
           "suelo-zapata, estado geostático ni fases constructivas."
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

if st.session_state.get("informe_stale", False):
    st.sidebar.warning("⚠️ Los datos han cambiado. **Recalcula** y vuelve a **generar el informe**.")

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
                "aplica; su geometría excavada no reproduce contacto lateral ni fases constructivas.")

    st.markdown("---")
    st.subheader("📐 Criterio de Profundidad de Influencia (EC7)")
    st.latex(r"\Delta\sigma_z(z_i) \leq 0.20\,\sigma'_{v0}(D + z_i)")

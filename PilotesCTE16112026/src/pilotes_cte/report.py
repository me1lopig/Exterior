"""Memoria Word trazable, sin dependencias de Streamlit ni de Kaleido."""
from __future__ import annotations

from datetime import date
import io
from typing import Sequence

from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from matplotlib.figure import Figure

from .core import Configuracion, Estrato, Resultado, perfil_tensiones, NORMA


def _tabla(doc: Document, cabeceras: list[str], filas: list[list[str]], tam=8) -> None:
    t=doc.add_table(rows=1,cols=len(cabeceras))
    t.style="Light Shading Accent 1"
    t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for cel,h in zip(t.rows[0].cells,cabeceras):
        cel.text=str(h)
    for fila in filas:
        celdas=t.add_row().cells
        for cel,val in zip(celdas,fila):
            cel.text=str(val)
    for fila in t.rows:
        for cel in fila.cells:
            for p in cel.paragraphs:
                for run in p.runs: run.font.size=Pt(tam)


def _imagen_tensiones(estratos:list[Estrato],cfg:Configuracion)->io.BytesIO:
    zs,sv,u,se=perfil_tensiones(estratos,cfg.nivel_freatico,paso=.25)
    fig=Figure(figsize=(8.3,4.6),dpi=125)
    ax=fig.subplots()
    ax.plot(sv,zs,label="σv total")
    ax.plot(u,zs,label="u")
    ax.plot(se,zs,label="σ'v efectiva")
    y=0.
    for e in estratos:
        ax.axhline(y,linewidth=.5,color="gray",alpha=.7)
        y+=e.espesor
    ax.axhline(y,linewidth=.5,color="gray",alpha=.7)
    if cfg.nivel_freatico is not None:
        ax.axhline(cfg.nivel_freatico,linestyle="--",linewidth=1,color="blue",label="Nivel freático")
    ax.set_ylim(y,0)
    ax.set_xlabel("Tensión / presión (kPa)")
    ax.set_ylabel("Profundidad (m)")
    ax.grid(alpha=.25)
    ax.legend(loc="best",fontsize=8)
    fig.tight_layout()
    out=io.BytesIO();fig.savefig(out,format="png");out.seek(0)
    return out


def _imagen_resistencias(resultados:list[Resultado])->io.BytesIO:
    fig=Figure(figsize=(8.3,4.2),dpi=125)
    ax=fig.subplots()
    ds=sorted({round(r.diametro,5) for r in resultados})
    for d in ds[:12]:
        sub=sorted((r for r in resultados if round(r.diametro,5)==d),key=lambda r:r.longitud)
        ax.plot([r.longitud for r in sub],[r.r_cabeza_orientativa for r in sub],marker="o",label=f"D eq {d:.2f} m")
    ax.set_xlabel("Longitud del pilote (m)")
    ax.set_ylabel("Capacidad de cabeza orientativa (kN)")
    ax.grid(alpha=.25)
    ax.legend(fontsize=7,ncol=3)
    fig.tight_layout()
    out=io.BytesIO();fig.savefig(out,format="png");out.seek(0)
    return out


def _formatear_detalle(rows:list[dict],decimales=2):
    if not rows:return [],[]
    cab=list(rows[0].keys())
    filas=[]
    for row in rows:
        vals=[]
        for c in cab:
            v=row.get(c,"")
            vals.append(f"{v:.{decimales}f}" if isinstance(v,float) else str(v))
        filas.append(vals)
    return cab,filas


def generar_informe(estratos:list[Estrato],cfg:Configuracion,situacion:str,
                    motivo_gamma:str,geo_desc:str,resultados:list[Resultado],
                    auditoria:Resultado,errores:list[dict],metadatos:dict|None=None)->bytes:
    if not resultados:
        raise ValueError("No hay resultados calculables para memoria Word.")
    info=metadatos or {}
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Cm(1.9);sec.bottom_margin=Cm(1.8)
    sec.left_margin=Cm(2);sec.right_margin=Cm(2)
    title=doc.add_heading("ANEJO DE CÁLCULO · PILOTES",0)
    title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    sub=doc.add_paragraph("Estimación analítica preliminar de resistencia axial según CTE DB-SE-C")
    sub.alignment=WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Versión PilotesCTE v3.0 — PROTOTIPO EN REVISIÓN",style="Subtitle")
    doc.add_paragraph(f"Fecha de emisión: {date.today():%d/%m/%Y}")
    doc.add_paragraph(f"Proyecto: {info.get('proyecto','No indicado')}")
    doc.add_paragraph(f"Sondeo / perfil: {info.get('sondeo','Perfil definido en aplicación')}")
    doc.add_paragraph(f"Fuente normativa: {NORMA}")
    doc.add_paragraph("No constituye por sí misma verificación ELU, comprobación estructural íntegra ni validación del proyecto.")

    doc.add_heading("1. Hipótesis y condiciones",1)
    entrada=[
        ("Ejecución",cfg.ejecucion),("Material",cfg.material),("Sección",geo_desc),
        ("Situación",situacion),("Nivel freático", "No reconocido en sondeo" if cfg.nivel_freatico is None else f"{cfg.nivel_freatico:.2f} m"),
        ("Fuste nulo",f"{cfg.fuste_nulo:.2f} m"),
        ("γR",f"{cfg.gamma_r:.2f}"),("Justificación γR",motivo_gamma),
        ("Tope axial simplificado",f"{cfg.sigma_tope_mpa:.2f} MPa"),
        ("Rozamiento negativo", "Activado" if cfg.rozamiento_negativo else "Desactivado")
    ]
    if cfg.rozamiento_negativo:
        entrada.extend([("Intervalo RN",f"{cfg.rn_desde:.2f}–{cfg.rn_hasta:.2f} m"),
                        ("Factor de acción RN",f"{cfg.factor_rn:.2f} (aportado por usuario)")])
    _tabla(doc,["Parámetro","Valor"],[[a,b] for a,b in entrada])

    doc.add_heading("2. Estratigrafía y parámetros geotécnicos",1)
    _tabla(doc,["UG","Espesor\nm","γ seco","γ sat","Tipo","Condición","cu kPa","φ °","Clase β"],
           [[e.nombre,f"{e.espesor:.2f}",f"{e.gamma_seco:.2f}",f"{e.gamma_sat:.2f}",e.tipo,
             e.condicion,f"{e.cu:.1f}",f"{e.phi:.1f}",e.clase_rn] for e in estratos],7)

    doc.add_heading("3. Metodología y alcance",1)
    for p in [
        "Rck = Rpk + Rfk; Rpk = qp·Ap; Rfk = ∫τf·p dz (CTE 5.8–5.10).",
        "F.30: qp = fp·σ'v(punta)·Nq (máximo 20 MPa). Parámetro φ equivalente ponderado por espesor en 6D/3D.",
        "F.32: qp = 9·cu equivalente. Para punta fina sin drenaje, cu ponderado en 2D/2D.",
        "Terreno mixto dentro de la ventana: cota conservadora por el otro tipo de suelo; hipótesis de ingeniería no textualmente prescrita por el CTE. Revisar en proyecto.",
        "5.11: qp ≤ 6·(1+H/D)²·cu del estrato fino inferior; se aplica el mínimo de los límites de capas inferiores reconocidas.",
        "F.31: τf = min(σ'v·Kf·f·tgφ, 120 kPa en granular / 100 kPa en fino drenado). F.33: τf = 100cu/(100+cu).",
        "El fuste se integra por tramos de σ'v y por cambios de estrato, NF y zonas de fricción; no se extrapola por debajo del sondeo.",
        "5.2.2 (5.4): RN opcional = ∫β·σ'v·p dz en el intervalo definido; se elimina allí el fuste resistente para evitar doble cómputo. La zona de asiento relativo debe justificarse externamente.",
        "Rcd = Rck/γR (CTE 5.7). Capacidad de cabeza orientativa = max(0, min(Rcd, Rtope) − Fneg,d), sin realizar Ed≤Rd completo.",
        "Geometría: H, punta=min(bh,1,5b²), fuste 2(b+h); tubular hincado, punta superficie circunscrita exterior, estructura corona metálica.",
    ]:
        doc.add_paragraph(p,style="List Bullet")

    doc.add_heading("4. Tensiones verticales y nivel freático",1)
    zs,sv,u,se=perfil_tensiones(estratos,cfg.nivel_freatico,paso=.2)
    doc.add_picture(_imagen_tensiones(estratos,cfg),width=Cm(16))
    valores=[];prof_total=sum(e.espesor for e in estratos)
    zshow={0.,prof_total}
    acum=0
    for e in estratos: acum+=e.espesor;zshow.add(acum)
    if cfg.nivel_freatico is not None:zshow.add(cfg.nivel_freatico)
    for z in sorted(zshow):
        from .core import tensiones
        v=tensiones(z,estratos,cfg.nivel_freatico)
        valores.append([f"{z:.2f}",*[f"{x:.2f}" for x in v]])
    _tabla(doc,["z (m)","σv (kPa)","u (kPa)","σ'v (kPa)"],valores)

    doc.add_heading("5. Matriz de resistencias y estados N/D",1)
    doc.add_paragraph(f"Combinaciones calculables: {len(resultados)}; rechazadas N/D: {len(errores)}.")
    ds=sorted({round(r.diametro,5) for r in resultados} | {round(e["D_eq (m)"],5) for e in errores})
    ls=sorted({round(r.longitud,5) for r in resultados} | {round(e["L (m)"],5) for e in errores})
    lookup={(round(r.longitud,5),round(r.diametro,5)):r for r in resultados}
    for inicio in range(0,len(ds),6):
        dc=ds[inicio:inicio+6]
        if len(ds)>6:doc.add_paragraph(f"Submatriz {inicio//6+1}: D equivalentes {dc[0]:.2f}–{dc[-1]:.2f} m")
        _tabla(doc,["L / D eq"]+[f"{d:.2f} m" for d in dc],
               [[f"{l:.2f}"]+[f"{lookup[(l,d)].r_cabeza_orientativa:.0f}" if (l,d) in lookup else "N/D" for d in dc] for l in ls])
    doc.add_paragraph("Valores en kN: capacidad de carga de cabeza ORIENTATIVA con descuento de RN si procede. "
                      "La matriz íntegra y los errores están disponibles en la aplicación.")
    if resultados:
        doc.add_picture(_imagen_resistencias(resultados),width=Cm(16))

    doc.add_heading("6. Auditoría detallada de una combinación",1)
    r=auditoria
    _tabla(doc,["Magnitud","Resultado"],[
        ["Longitud",f"{r.longitud:.2f} m"],["Diámetro equivalente",f"{r.diametro:.3f} m"],
        ["Área punta",f"{r.seccion.area_punta:.4f} m²"],["Área estructural",f"{r.seccion.area_estructural:.4f} m²"],
        ["Perímetro fuste",f"{r.seccion.perimetro_fuste:.4f} m"],
        ["qp antes de 5.11",f"{r.q_p_sin_limite:.1f} kPa"],
        ["Límite 5.11", "No aplicable (sin capas inferiores finas)" if r.q_limite_511 is None else f"{r.q_limite_511:.1f} kPa"],
        ["qp adoptado",f"{r.q_p:.1f} kPa"],
        ["Rpk",f"{r.r_pk:.2f} kN"],["Rfk",f"{r.r_fk:.2f} kN"],
        ["Rck",f"{r.r_ck:.2f} kN"],["Rcd",f"{r.r_cd:.2f} kN"],
        ["Tope axial simplificado",f"{r.r_estructural:.2f} kN"],
        ["Fneg,k",f"{r.rn_k:.2f} kN"],["Fneg,d",f"{r.rn_d:.2f} kN"],
        ["Carga cabeza orientativa",f"{r.r_cabeza_orientativa:.2f} kN"],
        ["Control",r.control],
    ])
    for titulo,datos in (("6.1. Punta y parámetros equivalentes",r.detalles_punta),
                         ("6.2. Fuste por tramo",r.detalles_fuste),
                         ("6.3. Rozamiento negativo por tramo",r.detalles_rn)):
        doc.add_heading(titulo,2)
        if datos:
            cab,filas=_formatear_detalle(datos)
            _tabla(doc,cab,filas,7)
        else:
            doc.add_paragraph("Sin contribuciones en esta categoría.")
    if r.observaciones:
        doc.add_heading("Advertencias del cálculo auditado",2)
        for obs in r.observaciones: doc.add_paragraph(obs,style="List Bullet")
    if errores:
        doc.add_heading("7. Combinaciones no disponibles",1)
        for e in errores[:30]:
            doc.add_paragraph(f"D={e['D_eq (m)']:.3f} m, L={e['L (m)']:.2f} m: {e['Causa']}")
        if len(errores)>30:doc.add_paragraph(f"Y otras {len(errores)-30} combinaciones; consultar la aplicación.")
    doc.add_page_break()
    doc.add_heading("8. Comprobaciones pendientes y limitaciones",1)
    for x in (
        "No se calcula apoyo en roca: opción deshabilitada; se mantienen exclusivamente suelos finos/granulares.",
        "No se calculan automáticamente ambos escenarios de corto/largo plazo; la condición elegida por estrato debe justificarse.",
        "No se verifica Ed≤Rd con combinaciones de acciones de proyecto, asientos, grupo, arrancamiento ni cargas horizontales.",
        "Tope estructural axial usado como comparación simplificada, no sustituye proyecto de la sección ni pandeo, corrosión, flexocompresión o uniones.",
        "El nivel freático es una hipótesis hidrostática simple; no incluye flujo, artesianismo ni variación temporal.",
        "La localización de la zona de rozamiento negativo y el plano neutro no se determinan automáticamente.",
        "La detección de capas blandas se limita a la estratigrafía proporcionada. No se prolonga artificialmente el terreno.",
        "Prototipo computacional; resultados sujetos a revisión por especialista y contraste con el estudio geotécnico.",
    ):doc.add_paragraph(x,style="List Bullet")
    output=io.BytesIO();doc.save(output)
    return output.getvalue()

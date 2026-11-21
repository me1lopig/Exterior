"""Vista geotécnica de sección e isobaras Boussinesq (Plotly)."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from calculos.bulbo_2d import ISOBARAS, malla_influencia
from modelos.datos import CapaSuelo

COLORES_ISOBARAS = ("#3974a3", "#23856e", "#8f9041", "#bf813b", "#c26c48", "#a84d45")
COLORES_ESTRATOS = ("#e8c8a7", "#ead7af", "#d6d8c0", "#e3c5ba", "#bfcfcb")


def figura_seccion_bulbo(b: float, l: float | None, d: float,
                         nivel_freatico_m: float, capas: tuple[CapaSuelo, ...],
                         presion_neta_kpa: float, *, corrida: bool = False,
                         zmax_m: float | None = None,
                         zcte_m: float | None = None,
                         profundidad_perfil_m: float | None = None,
                         mostrar_2b: bool = False) -> go.Figure:
    """Sección perpendicular a L, con z medido desde rasante en la vista.

    Los estratos recibidos se definen desde la BASE (z=0 de capas); no se
    inventa la estratigrafía por encima de la cimentación.
    """
    if not np.isfinite(d) or d < 0 or not np.isfinite(nivel_freatico_m) or nivel_freatico_m < 0:
        raise ValueError("Profundidad de base o nivel freático inválida.")
    if not np.isfinite(presion_neta_kpa) or presion_neta_kpa <= 0:
        raise ValueError("La presión neta de referencia debe ser positiva.")
    x, z, factor = malla_influencia(b,l,corrida=corrida,zmax_m=zmax_m)
    ymax = d + z[-1]
    xlim = max(abs(x[0]),abs(x[-1]))
    fig = go.Figure()
    # Estratigrafía visual, no modifica la solución homogénea de Boussinesq.
    fig.add_shape(type="rect", x0=x[0], x1=x[-1], y0=0, y1=d,
                  line_width=0, fillcolor="#f2e9d9", layer="below")
    if d:
        fig.add_annotation(x=x[0]+.04*xlim, y=d/2, text="Terreno sobre la base (sin estratigrafía)",
                           showarrow=False, xanchor="left", font={"size":10,"color":"#6a6358"})
    ultimo = d
    for i,c in enumerate(capas):
        superior, inferior = d+c.z_superior_m, min(ymax,d+c.z_inferior_m)
        if inferior <= superior:
            continue
        fig.add_shape(type="rect", x0=x[0], x1=x[-1], y0=superior, y1=inferior,
                      line_width=0, fillcolor=COLORES_ESTRATOS[i%len(COLORES_ESTRATOS)],
                      layer="below", opacity=.63)
        fig.add_annotation(x=x[0]+.04*xlim, y=(superior+inferior)/2,
                           text=c.nombre.replace("<","").replace(">",""), showarrow=False,
                           xanchor="left", font={"size":10,"color":"#655446"})
        ultimo = max(ultimo,inferior)
    if ultimo < ymax:
        fig.add_shape(type="rect", x0=x[0],x1=x[-1],y0=ultimo,y1=ymax,
                      line_width=0,fillcolor="#ececec",layer="below")
        fig.add_annotation(x=x[0]+.04*xlim,y=(ultimo+ymax)/2,
                           text="Terreno sin caracterizar",showarrow=False,xanchor="left",
                           font={"size":10,"color":"#656565"})
    # Una traza por isobara para valores porcentuales no equiespaciados.
    for nivel,color in zip(ISOBARAS,COLORES_ISOBARAS):
        fig.add_trace(go.Contour(
            x=x,y=d+z,z=factor,
            autocontour=False,
            contours={"start":nivel,"end":nivel,"size":.0001,
                      "coloring":"lines","showlabels":True,
                      "labelfont":{"size":10,"color":color}},
            line={"color":color,"width":2},
            showscale=False,showlegend=True,
            name=f"{nivel:.0%} ({nivel*presion_neta_kpa:.1f} kPa)",
            hovertemplate=f"Isobara {nivel:.0%}: {nivel*presion_neta_kpa:.2f} kPa"
                          "<br>x=%{x:.2f} m<br>Profundidad=%{y:.2f} m<extra></extra>",
        ))
    # INC-03A: referencias de profundidad BAJO LA BASE, sin alterar las isobaras.
    # Z_CTE es el cruce calculado bajo el eje, NO el contorno de la isobara 10 %.
    referencias = (
        (zcte_m, "#c94f59", "dash", f"Z_CTE = {zcte_m:.2f} m" if zcte_m is not None else "",
         x[-1]-.05*xlim, "right", 14),
        (2*b if mostrar_2b else None, "#8067aa", "dot", f"2B = {2*b:.2f} m",
         x[0]+.05*xlim, "left", -14),
        (profundidad_perfil_m, "#495568", "dashdot",
         f"Fin del perfil = {profundidad_perfil_m:.2f} m" if profundidad_perfil_m is not None else "",
         x[-1]-.05*xlim, "right", -14),
    )
    for profundidad, color, trazo, etiqueta, posicion_x, ancla, desplazamiento in referencias:
        if profundidad is None:
            continue
        if not np.isfinite(profundidad) or profundidad < 0:
            raise ValueError("Profundidad de referencia no válida.")
        cota = d + profundidad
        if cota > ymax:
            continue
        fig.add_shape(type="line", x0=x[0],x1=x[-1],y0=cota,y1=cota,
                      line={"color":color,"width":2.5 if trazo=="dash" else 1.5,"dash":trazo})
        fig.add_annotation(x=posicion_x,y=cota,text=etiqueta,showarrow=False,
                           yshift=desplazamiento,xanchor=ancla,
                           font={"size":11,"color":color},
                           bgcolor="rgba(255,255,255,0.80)")
    # Nivel freático y zapata por encima de las curvas.
    if nivel_freatico_m <= ymax:
        fig.add_shape(type="line", x0=x[0],x1=x[-1],y0=nivel_freatico_m,
                      y1=nivel_freatico_m,line={"color":"#2088c0","width":2,"dash":"dash"})
        fig.add_annotation(x=x[-1]-.05*xlim,y=nivel_freatico_m,
                           text="Nivel freático",yshift=12,showarrow=False,
                           xanchor="right",font={"size":11,"color":"#116c9a"})
    alto = max(.10*b,.12)
    fig.add_shape(type="rect",x0=-b/2,x1=b/2,y0=max(0,d-alto),y1=d,
                  fillcolor="#929ea0",line={"color":"#435359","width":2})
    fig.add_annotation(x=0,y=max(0,d-alto),text="q neta ↓",showarrow=True,
                       ay=-30,ax=0,arrowcolor="#b44d42",font={"color":"#a64438"})
    tipo = "corrida ideal (L → ∞)" if corrida else ("cuadrada" if abs(float(l)-b)<1e-10*b else "rectangular")
    fig.update_layout(
        title=f"Sección y bulbo 2D · zapata {tipo} · B={b:.2f} m" +
              ("" if corrida else f" · L={float(l):.2f} m"),
        template="plotly_white",height=620,hovermode="closest",
        margin={"l":55,"r":35,"t":75,"b":85},
        legend={"orientation":"h","y":-0.16,"x":0,"font":{"size":10}},
        xaxis={"title":"Distancia horizontal al eje de B (m)","range":[x[0],x[-1]]},
        yaxis={"title":"Profundidad desde rasante (m)","range":[ymax,0],"autorange":False},
    )
    return fig

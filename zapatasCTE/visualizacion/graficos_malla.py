"""Mapas BxL con valores impresos y selección, sin interpolación de geometrías."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utiles.tablas_malla import CAMPOS_MAPA

# Paleta solicitada: azul claro -> azul marino. Las regiones fuera de B<=L
# conservan fondo gris claro, y no se interpolan.
AZULES = [
    [0.00, "#d7e6f1"], [0.25, "#adcae1"],
    [0.50, "#82a8d2"], [0.75, "#587fc5"], [1.00, "#344b9d"],
]
COLOR_FONDO = "#f3f4f6"
COLORES_LIMITACION = {"Hundimiento": 0.0, "No válido": 0.5, "Asientos": 1.0}


def mapa_calor(df: pd.DataFrame, etiqueta: str) -> go.Figure:
    """Mapa B x L: valor de cada solución escrito en el interior de la celda.

    La ficha se controla por la selección Plotly o por su desplegable asociado.
    Los valores mostrados son los mismos que en tabla_malla, sin interpolación.
    """
    col = CAMPOS_MAPA[etiqueta]
    bs = sorted(df["B (m)"].unique())
    ls = sorted(df["L (m)"].unique())
    filas = {(float(r["B (m)"]), float(r["L (m)"])): r for _, r in df.iterrows()}
    categorico = col == "Limitación"
    valores = []
    for b in bs:
        fila = []
        for l in ls:
            dato = filas.get((float(b), float(l)))
            value = None if dato is None else dato[col]
            if categorico:
                fila.append(None if value is None else COLORES_LIMITACION.get(value, .5))
            else:
                fila.append(None if value is None or pd.isna(value) else float(value))
        valores.append(fila)
    reales = [float(x) for fila in valores for x in fila if x is not None and np.isfinite(x)]
    zmin, zmax = (min(reales), max(reales)) if reales else (0., 1.)
    if abs(zmax-zmin) < 1e-12:
        zmin -= max(abs(zmin)*0.1, 0.01)
        zmax += max(abs(zmax)*0.1, 0.01)
    if categorico:
        zmin, zmax = 0, 1
        escala = [[0, "#3378ad"], [.49, "#3378ad"],
                  [.50, "#929fac"], [.51, "#929fac"],
                  [.52, "#df8d48"], [1, "#df8d48"]]
    else:
        escala = AZULES
    fig=go.Figure()
    fig.add_trace(go.Heatmap(
        x=ls,y=bs,z=valores,zmin=zmin,zmax=zmax,colorscale=escala,
        xgap=3,ygap=3,showscale=not categorico,
        colorbar={"title": "MPa" if "(MPa)" in col else "MN/m³", "thickness": 13, "len": 0.8},
        hovertemplate="B=%{y:.2f} m<br>L=%{x:.2f} m<br>Valor=%{z:.4f}<extra></extra>",
        hoverongaps=False,
    ))
    # Valores siempre visibles. Con más filas se adapta la altura del gráfico.
    # El contraste del texto se controla por la posición en la escala cromática.
    fontsize = 11 if max(len(bs),len(ls)) <= 14 else 9
    for i,b in enumerate(bs):
        for j,l in enumerate(ls):
            value=valores[i][j]
            if value is None:
                texto="–"
                color="#c5cad0"
            elif categorico:
                categoria=filas[(float(b),float(l))]["Limitación"]
                texto={"Hundimiento":"H", "Asientos":"A", "No válido":"!"}.get(categoria,"?")
                color="#ffffff"
            else:
                texto=f"{value:.3f}" if "(MPa)" in col else f"{value:.2f}"
                intensidad=(value-zmin)/(zmax-zmin)
                color="#ffffff" if intensidad >= 0.58 else "#123a57"
            fig.add_annotation(x=float(l),y=float(b),text=texto,showarrow=False,
                               font={"size":fontsize,"color":color},opacity=1)
    if categorico:
        for nombre, color in [("H = Hundimiento","#3378ad"),
                              ("A = Asientos","#df8d48"),
                              ("! = No válido","#929fac")]:
            fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",name=nombre,
                marker={"symbol":"square","size":12,"color":color}))
    # Marcador invisible para que Plotly/Streamlit registre selección por puntos.
    xx, yy, hover_extra = [], [], []
    for (b,l),r in filas.items():
        xx.append(l); yy.append(b)
        def fmt(k, unit=""):
            n=r[k]
            return "—" if pd.isna(n) else f"{float(n):.3f}{unit}"
        hover_extra.append(
            f"B={b:.2f} m · L={l:.2f} m<br>"
            f"Hundimiento neto: {fmt('q hund. neta (MPa)')} MPa<br>"
            f"Asientos neto: {fmt('q asientos neta (MPa)')} MPa<br>"
            f"Servicio neto: {fmt('q servicio neta (MPa)')} MPa<br>"
            f"ks,BL: {fmt('ks,BL (MN/m³)')} MN/m³<br>"
            f"Ksp30: {fmt('Ksp30 (MN/m³)')} MN/m³<br>"
            f"Gobierna: {r['Limitación']}"
        )
    if xx:
        # Coordenadas y eventos con la misma referencia que la traza Heatmap.
        fig.add_trace(go.Scatter(x=xx,y=yy,mode="markers",showlegend=False,
            marker={"symbol":"square","size":max(8,min(42,round(580/max(len(ls),len(bs),1)))),
                    "color":"rgba(255,255,255,0.002)","line":{"width":0}},
            text=hover_extra,hovertemplate="%{text}<extra></extra>",name="Seleccionar"))
    fig.update_layout(
        title={"text":etiqueta,"x":0.02,"font":{"size":16}},
        height=max(470, int(44*len(bs)+125)),
        template="plotly_white", dragmode="select", clickmode="event+select",
        margin={"l":50,"r":40,"t":60,"b":60},
        legend={"orientation":"h","y":1.04},
        xaxis={"title":"Longitud L (m)","tickmode":"array","tickvals":ls,
               "tickangle":0,"gridcolor":"#ffffff","type":"linear"},
        yaxis={"title":"Ancho B (m)","tickmode":"array","tickvals":bs,
               "autorange":"reversed","gridcolor":"#ffffff","type":"linear"},
        plot_bgcolor=COLOR_FONDO,paper_bgcolor="#ffffff",
    )
    return fig


def curvas_seccion(df: pd.DataFrame, b: float) -> go.Figure:
    datos = df[np.isclose(df["B (m)"], b)].sort_values("L (m)")
    fig=go.Figure()
    for campo,nombre,color in [
        ("q hund. neta (MPa)","Hundimiento neto","#286b9b"),
        ("q asientos neta (MPa)","Asientos neto","#d18c35"),
        ("q servicio neta (MPa)","Servicio neto","#db4757"),
    ]:
        fig.add_trace(go.Scatter(x=datos["L (m)"],y=datos[campo],mode="lines+markers",
                                 name=nombre,line={"color":color,"width":3 if "servicio" in campo else 2}))
    fig.update_layout(
        title=f"Presiones netas para B = {b:.2f} m",template="plotly_white",height=390,
        margin={"l":25,"r":15,"t":55,"b":35},legend={"orientation":"h","y":1.12},
        xaxis_title="Longitud L (m)",yaxis_title="Presión neta (MPa)",hovermode="x unified",
    )
    return fig


def grafico_geom(b: float, l: float) -> go.Figure:
    fig=go.Figure()
    fig.add_shape(type="rect",x0=-l/2,x1=l/2,y0=-b/2,y1=b/2,
                  line={"color":"#2878b5","width":3},fillcolor="rgba(40,120,181,0.17)")
    fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",marker={"size":10,"color":"#cf5965"},
                             hovertemplate="Centro de cimentación<extra></extra>",showlegend=False))
    fig.add_annotation(x=0,y=b/2,text=f"L = {l:.2f} m",showarrow=False,yshift=15)
    fig.add_annotation(x=l/2,y=0,text=f"B = {b:.2f} m",showarrow=False,xshift=45,textangle=90)
    fig.update_xaxes(visible=False,range=[-l*.68,l*.68],scaleanchor="y",scaleratio=1)
    fig.update_yaxes(visible=False,range=[-max(b,1)*.72,max(b,1)*.72])
    fig.update_layout(height=250,template="plotly_white",margin={"l":10,"r":10,"t":24,"b":0})
    return fig

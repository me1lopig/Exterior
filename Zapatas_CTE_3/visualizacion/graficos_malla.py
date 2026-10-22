"""Mapas B×L y perfiles comparativos. No se interpolan celdas no calculadas."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utiles.tablas_malla import CAMPOS_MAPA

COLOR_FONDO = "#f7f9fc"


def mapa_calor(df: pd.DataFrame, etiqueta: str) -> go.Figure:
    """Mapa de celdas BxL con superposición de marcadores para selección Plotly.

    Las celdas B>L no existen en el DataFrame y quedan vacías (gris).
    """
    col=CAMPOS_MAPA[etiqueta]
    bs=sorted(df["B (m)"].unique())
    ls=sorted(df["L (m)"].unique())
    dic={(float(r["B (m)"]),float(r["L (m)"])):r for _,r in df.iterrows()}
    es_categoria=col=="Limitación"
    colores={"Hundimiento":0.0,"Asientos":1.0,"No válido":0.5}
    mapa=[]; textos=[]
    for b in bs:
        fila=[]; txt=[]
        for l in ls:
            row=dic.get((float(b),float(l)))
            val=None if row is None else row[col]
            if es_categoria:
                fila.append(None if val is None else colores.get(val,0.5))
                txt.append("Fuera B<=L" if val is None else str(val))
            else:
                fila.append(None if val is None or pd.isna(val) else float(val))
                txt.append("Sin valor" if val is None or pd.isna(val) else f"{float(val):.4f}")
        mapa.append(fila); textos.append(txt)
    fig=go.Figure()
    if es_categoria:
        escala=[[0,"#2772ae"],[.49,"#2772ae"],[.50,"#929fac"],[.51,"#929fac"],[.52,"#df8d48"],[1,"#df8d48"]]
        fig.add_trace(go.Heatmap(x=ls,y=bs,z=mapa,zmin=0,zmax=1,colorscale=escala,
                                 xgap=2,ygap=2,showscale=False,text=textos,
                                 hovertemplate="B=%{y:.2f} m<br>L=%{x:.2f} m<br>%{text}<extra></extra>"))
        for nombre,color in [("Hundimiento","#2772ae"),("Asientos","#df8d48"),("No válido","#929fac")]:
            fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",name=nombre,
                    marker={"symbol":"square","size":12,"color":color}))
    else:
        fig.add_trace(go.Heatmap(x=ls,y=bs,z=mapa,colorscale="Viridis",xgap=2,ygap=2,
            colorbar={"title":"MPa" if "(MPa)" in col else "MN/m³"},text=textos,
            hovertemplate="B=%{y:.2f} m<br>L=%{x:.2f} m<br>%{text}<extra></extra>"))
    # Los controles de selección de Streamlit reciben eventos de la traza Scatter.
    # El selector textual de la ficha siempre ofrece un mecanismo alternativo.
    coordenadas=[(float(r["L (m)"]),float(r["B (m)"])) for _,r in df.iterrows()
                 if es_categoria or not pd.isna(r[col])]
    if coordenadas:
        xx,yy=zip(*coordenadas)
        fig.add_trace(go.Scatter(x=xx,y=yy,mode="markers",showlegend=False,
            marker={"symbol":"square","size":max(7,min(42,round(680/max(len(ls),len(bs),1)))),
                    "color":"rgba(255,255,255,0.005)","line":{"width":0}},
            hovertemplate="B=%{y:.2f} m<br>L=%{x:.2f} m<extra></extra>",name="Seleccionar"))
    fig.update_layout(
        title={"text":etiqueta,"x":0.02,"font":{"size":16}},
        height=510,template="plotly_white",dragmode="select",clickmode="event+select",
        margin={"l":30,"r":30,"t":60,"b":45},
        legend={"orientation":"h","y":1.06},
        xaxis={"title":"Longitud L (m)","gridcolor":"#e5e9f0","tickmode":"array","tickvals":ls},
        yaxis={"title":"Ancho B (m)","gridcolor":"#e5e9f0","tickmode":"array","tickvals":bs},
        plot_bgcolor="#e9edf1",paper_bgcolor="#ffffff",
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

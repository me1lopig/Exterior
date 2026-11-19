"""Gráficos y mapa de calor para corridas y estudios exploratorios."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utiles.tablas_malla import CAMPOS_MAPA
from visualizacion.graficos_malla import AZULES, COLOR_FONDO, COLORES_LIMITACION


def mapa_calor_corridas(tabla: pd.DataFrame, etiqueta: str) -> go.Figure:
    """Mapa unidimensional: una columna y una fila por ancho B.

    Reutiliza las mismas variables/colores que el mapa BxL.
    Las longitudes internas 100/1000 m no se confunden con L infinito.
    """
    campo = CAMPOS_MAPA[etiqueta]
    if tabla.empty or not {"B (m)",campo}.issubset(tabla.columns):
        raise ValueError("Tabla de corridas vacía o sin el campo solicitado.")
    datos = tabla.sort_values("B (m)")
    bs = datos["B (m)"].astype(float).tolist()
    categorico = campo == "Limitación"
    bruto = datos[campo].tolist()
    z = [
        COLORES_LIMITACION.get(v, .5) if categorico
        else float(v) if pd.notna(v) else float("nan") for v in bruto
    ]
    finitos = [v for v in z if np.isfinite(v)]
    minimo,maximo = (min(finitos),max(finitos)) if finitos else (0.,1.)
    if categorico:
        minimo,maximo=0.,1.
        escala=[[0,"#3378ad"],[.49,"#3378ad"],[.5,"#929fac"],
                [.51,"#929fac"],[.52,"#df8d48"],[1,"#df8d48"]]
    else:
        escala=AZULES
        if abs(maximo-minimo)<1e-12:
            minimo-=max(0.01,abs(minimo)*.1)
            maximo+=max(0.01,abs(maximo)*.1)
    figura=go.Figure(go.Heatmap(
        x=["Corrida aprox."],y=bs,z=[[v] for v in z],
        zmin=minimo,zmax=maximo,colorscale=escala,
        showscale=not categorico,xgap=4,ygap=3,
        colorbar={"title":"MPa" if "(MPa)" in campo else "MN/m³",
                  "thickness":14,"len":.8},
        hovertemplate="B=%{y:.2f} m<br>Valor=%{z:.4f}<extra></extra>",
        hoverongaps=False,
    ))
    for b,v,orig in zip(bs,z,bruto):
        texto=("—" if not np.isfinite(v) else
               {"Hundimiento":"H","Asientos":"A","No válido":"!"}.get(orig,"?") if categorico else
               f"{v:.3f}" if "(MPa)" in campo else f"{v:.2f}")
        figura.add_annotation(x="Corrida aprox.",y=b,text=texto,
            font={"size":12,"color":"#ffffff" if categorico else "#17324b"},
            showarrow=False)
    # Una traza con un punto por fila permite la selección desde Streamlit.
    figura.add_trace(go.Scatter(
        x=["Corrida aprox."]*len(bs),y=bs,mode="markers",
        name="Seleccionar B",showlegend=False,
        marker={"symbol":"square","size":20,
                "color":"rgba(255,255,255,0.002)","line":{"width":0}},
        customdata=bs,hovertemplate="B=%{y:.2f} m<extra></extra>",
    ))
    figura.update_layout(
        title={"text":etiqueta,"font":{"size":16}},
        template="plotly_white",height=max(375,52*len(bs)+145),
        clickmode="event+select",dragmode="select",
        xaxis={"title":"Geometría aproximada (L_as=100 m; L_h=1000 m)",
               "type":"category"},
        yaxis={"title":"Anchura B (m)","tickmode":"array","tickvals":bs,
               "autorange":"reversed"},
        margin={"l":48,"r":25,"t":58,"b":70},
        plot_bgcolor=COLOR_FONDO,
    )
    return figura


def grafico_balasto(tabla: pd.DataFrame, *, corrida: bool = False,
                    b: float | None = None) -> go.Figure:
    """Compara balasto calculado y equivalente en la MISMA geometría."""
    if tabla.empty:
        raise ValueError("No hay resultados de balasto.")
    if corrida:
        d=tabla.sort_values("B (m)")
        x="B (m)"
    else:
        if b is None:
            raise ValueError("Se exige ancho B para secciones rectangulares.")
        d=tabla[np.isclose(tabla["B (m)"],b)].sort_values("L (m)")
        x="L (m)"
    if d.empty:
        raise ValueError("La sección de balasto solicitada no existe.")
    fig=go.Figure()
    for columna,nombre,color in (
        ("ks,BL (MN/m³)","ks,BL","#286b9b"),
        ("Ksp30 (MN/m³)","Ksp30","#d18c35"),
    ):
        fig.add_trace(go.Scatter(
            x=d[x],y=d[columna],mode="lines+markers",
            name=nombre,line={"color":color,"width":2.5},
            hovertemplate="%{x:.2f} m: %{y:.3f} MN/m³<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        template="plotly_white",height=390,hovermode="x unified",
        xaxis_title="Anchura B (m)" if corrida else "Longitud L (m)",
        yaxis_title="Coeficiente de balasto (MN/m³)",
        title="Evolución de los coeficientes de balasto",
        legend={"orientation":"h","y":1.13},
    )
    return fig


def grafico_convergencia(tabla: pd.DataFrame) -> go.Figure:
    """Evolución de límites netos con L/B finito, sin presuponer L infinito."""
    if tabla.empty:
        raise ValueError("Falta el estudio de convergencia.")
    fig=go.Figure()
    for columna,nombre,color in (
        ("q hund. neta (MPa)","Hundimiento","#286b9b"),
        ("q asientos neta (MPa)","Asientos","#d18c35"),
        ("q servicio neta (MPa)","Servicio","#db4757"),
    ):
        fig.add_trace(go.Scatter(
            x=tabla["L/B"],y=tabla[columna],mode="lines+markers",
            name=nombre,line={"color":color,"width":3 if nombre=="Servicio" else 2},
        ))
    fig.update_layout(
        template="plotly_white",height=430,hovermode="x unified",
        title="Convergencia numérica de geometrías finitas",
        xaxis_title="Relación L/B (escala logarítmica)",
        xaxis_type="log",yaxis_title="Presión neta (MPa)",
        legend={"orientation":"h","y":1.13},
    )
    return fig


def grafico_comparativa(tabla: pd.DataFrame) -> go.Figure:
    """Comparación etiquetada: sin presión de servicio inventada para infinito."""
    fig=go.Figure()
    for columna,nombre,color in (
        ("q hund. neta (MPa)","Hundimiento","#286b9b"),
        ("q asientos neta (MPa)","Asientos","#d18c35"),
        ("q servicio neta (MPa)","Servicio","#db4757"),
    ):
        fig.add_trace(go.Bar(x=tabla["Hipótesis"],y=tabla[columna],
            name=nombre,marker_color=color))
    fig.update_layout(
        template="plotly_white",barmode="group",height=440,
        yaxis_title="Presión neta (MPa)",xaxis_title="Hipótesis comparada",
        legend={"orientation":"h","y":1.14},
    )
    return fig


def grafico_sensibilidad(tabla: pd.DataFrame) -> go.Figure:
    fig=go.Figure()
    for col,nombre,color in (
        ("q hund. bruta (MPa)","Hundimiento bruto","#286b9b"),
        ("q hund. neta (MPa)","Hundimiento neto","#d18c35"),
    ):
        fig.add_trace(go.Scatter(x=tabla["NF bajo rasante (m)"],
            y=tabla[col],mode="lines+markers",name=nombre,
            line={"color":color}))
    fig.add_trace(go.Scatter(
        x=tabla["NF bajo rasante (m)"],y=tabla["gamma_k (kN/m³)"],
        mode="lines",name="γk",yaxis="y2",
        line={"color":"#21866c","dash":"dash","width":3}))
    fig.update_layout(
        template="plotly_white",height=430,hovermode="x unified",
        title="Sensibilidad de hundimiento y γk al nivel freático",
        xaxis_title="Nivel freático bajo rasante (m)",
        yaxis_title="Presión de hundimiento (MPa)",
        yaxis2={"title":"γk (kN/m³)","overlaying":"y","side":"right",
                "showgrid":False},
        legend={"orientation":"h","y":1.17},
    )
    return fig

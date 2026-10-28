"""Figuras de perfil para seleccion individual en Streamlit."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from calculos.diagnostico_asientos import PerfilBulbo


def figura_bulbo(perfil: PerfilBulbo) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=perfil.delta_sigma_kpa, y=perfil.z_m, name="Incremento Boussinesq",
                    mode="lines", line=dict(color="#3562b3", width=3))
    fig.add_scatter(x=perfil.umbral_cte_kpa, y=perfil.z_m, name="Umbral CTE: min(10% q, 5% sigma'v0)",
                    mode="lines", line=dict(color="#db8250", dash="dash"))
    fig.add_hline(y=perfil.profundidad_modelo_m, line_dash="dot", line_color="#8592a3",
                  annotation_text="Fin del perfil de E")
    if perfil.profundidad_influencia_m is not None:
        fig.add_hline(y=perfil.profundidad_influencia_m, line_dash="dash",
                      line_color="#29755c", annotation_text="Prof. activa estimada")
    fig.update_yaxes(autorange="reversed", title="z bajo la base (m)")
    fig.update_xaxes(title="Incremento de tension (kPa)", rangemode="tozero")
    fig.update_layout(template="plotly_white", title="Bulbo de tensiones en eje central",
                      legend=dict(orientation="h", y=-0.25), height=400,
                      margin=dict(l=20, r=20, t=55, b=85))
    return fig


def figura_asiento_acumulado(tabla: pd.DataFrame) -> go.Figure:
    z = [0.0] + tabla["z inf. (m)"].to_list()
    u = [0.0] + tabla["Asiento acumulado (mm)"].to_list()
    fig=go.Figure()
    fig.add_scatter(x=u, y=z, mode="lines+markers", line_shape="hv",
                    name="Acumulado por estratos", line=dict(color="#385db2", width=3),
                    marker=dict(size=8), customdata=["inicio"]+tabla["Unidad"].to_list(),
                    hovertemplate="z=%{y:.2f} m<br>Acumulado=%{x:.3f} mm<br>%{customdata}<extra></extra>")
    fig.update_yaxes(autorange="reversed", title="z bajo la base (m)")
    fig.update_xaxes(title="Asiento acumulado por capas (mm)", rangemode="tozero")
    fig.update_layout(template="plotly_white", title="Suma progresiva de contribuciones",
                      height=400, margin=dict(l=20,r=20,t=55,b=30))
    return fig


def figura_contribuciones(tabla: pd.DataFrame) -> go.Figure:
    fig=go.Figure(go.Bar(x=tabla["Contribucion (%)"],y=tabla["Unidad"],orientation="h",
                         marker_color="#6589ca",text=[f"{x:.1f}%" for x in tabla["Contribucion (%)"]],
                         textposition="outside"))
    fig.update_layout(template="plotly_white",title="Contribucion por estratos",
                      xaxis_title="Porcentaje del asiento calculado (%)",yaxis_title="Estrato",
                      height=max(300,55*len(tabla)+100),margin=dict(l=15,r=45,t=55,b=25))
    fig.update_yaxes(autorange="reversed")
    return fig

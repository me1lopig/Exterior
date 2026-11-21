"""Figuras de perfil para seleccion individual en Streamlit."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from calculos.diagnostico_asientos import PerfilBulbo


def figura_bulbo(perfil: PerfilBulbo, *, b_m: float | None = None) -> go.Figure:
    """INC-03C: curvas independientes que determinan Z_CTE bajo el eje."""
    fig = go.Figure()
    q10_kpa = float(perfil.delta_sigma_kpa[0]) * 0.10  # z[0] = 0: Delta sigma = q
    fig.add_scatter(x=perfil.delta_sigma_kpa, y=perfil.z_m, name="Δσz Boussinesq",
                    mode="lines", line=dict(color="#3562b3", width=3))
    fig.add_scatter(x=[q10_kpa]*len(perfil.z_m), y=perfil.z_m,
                    name="10 % de q neta",mode="lines",
                    line=dict(color="#ce7d32", width=2, dash="dot"))
    fig.add_scatter(x=0.05*perfil.sigma_efectiva_inicial_kpa, y=perfil.z_m,
                    name="5 % de σ'v0",mode="lines",
                    line=dict(color="#9263a6", width=2, dash="dash"))
    fig.add_scatter(x=perfil.umbral_cte_kpa, y=perfil.z_m,
                    name="Umbral CTE = mínimo de ambos",mode="lines",
                    line=dict(color="#c94f59", width=2, dash="dashdot"))
    fig.add_hline(y=perfil.profundidad_modelo_m, line_dash="dashdot",
                  line_color="#495568",annotation_text="Fin del perfil")
    if b_m is not None:
        fig.add_hline(y=2*b_m, line_dash="dot",line_color="#8067aa",
                      annotation_text="2B (orientativo)")
    if perfil.profundidad_influencia_m is not None:
        fig.add_hline(y=perfil.profundidad_influencia_m, line_dash="dash",
                      line_color="#c94f59", annotation_text="Z_CTE")
    fig.update_yaxes(autorange="reversed", title="z bajo la base (m)")
    fig.update_xaxes(title="Incremento / umbrales de tensión (kPa)", rangemode="tozero")
    fig.update_layout(template="plotly_white", title="Determinación de Z_CTE bajo el eje central",
                      legend=dict(orientation="h", y=-0.29), height=480,
                      margin=dict(l=20, r=20, t=55, b=125))
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

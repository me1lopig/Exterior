"""Representacion grafica de perfiles geotecnicos."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def perfil_resultados(df: pd.DataFrame, titulo: str) -> go.Figure:
    datos = df.dropna(subset=["profundidad_m", "valor_grafico"]).copy()
    if datos.empty:
        figura = go.Figure()
        figura.add_annotation(text="Sin resultados numericos para representar", showarrow=False)
        return figura
    figura = px.line(
        datos.sort_values("profundidad_m"),
        x="valor_grafico",
        y="profundidad_m",
        color="metodo",
        markers=True,
        line_group="grupo",
        hover_data=["grupo", "punto", "unidad", "advertencias"],
        title=titulo,
    )
    figura.update_yaxes(autorange="reversed", title="Profundidad (m)")
    figura.update_xaxes(title="Valor")
    figura.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title_text="Metodo",
        margin=dict(l=30, r=20, t=55, b=35),
        font=dict(color="#10263f"),
    )
    figura.update_xaxes(showgrid=True, gridcolor="#edf0f3")
    figura.update_yaxes(showgrid=True, gridcolor="#edf0f3")
    return figura


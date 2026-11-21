"""Gráficos Plotly de la aplicación."""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go

from modelos.datos import ResultadoAncho


def grafico_presiones(resultados: Sequence[ResultadoAncho], geometria: str) -> go.Figure:
    es_cuadrada = geometria == "Cuadrada"
    anchos = [r.ancho_m for r in resultados]
    hundimiento = [
        r.hundimiento_cuadrada_mpa if es_cuadrada else r.hundimiento_corrida_mpa
        for r in resultados
    ]
    asientos = [
        r.asiento_cuadrada_mpa if es_cuadrada else r.asiento_corrida_mpa
        for r in resultados
    ]
    servicio = [
        r.servicio_cuadrada_mpa if es_cuadrada else r.servicio_corrida_mpa
        for r in resultados
    ]
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(x=anchos, y=hundimiento, name="Hundimiento", mode="lines+markers")
    )
    figura.add_trace(
        go.Scatter(x=anchos, y=asientos, name="Asientos", mode="lines+markers")
    )
    figura.add_trace(
        go.Scatter(
            x=anchos,
            y=servicio,
            name="Admisible de servicio",
            mode="lines+markers",
            line={"color": "#e65358", "width": 3},
            marker={"size": 8},
        )
    )
    figura.update_layout(
        template="plotly_white",
        height=430,
        margin={"l": 20, "r": 20, "t": 35, "b": 20},
        legend={"orientation": "h", "y": 1.12, "x": 0},
        xaxis_title="Ancho equivalente B* (m)",
        yaxis_title="Presión (MPa)",
        hovermode="x unified",
        font={"family": "Inter, Arial, sans-serif", "color": "#10243a"},
    )
    figura.update_xaxes(showgrid=False)
    figura.update_yaxes(gridcolor="#e8edf2", rangemode="tozero")
    return figura

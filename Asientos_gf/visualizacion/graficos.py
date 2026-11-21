"""Figuras Plotly con una paleta coherente y legible."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from calculos.asientos import CalculationResult


NAVY = "#0b263e"
RED = "#e45455"
GREEN = "#238b57"
GRID = "#dfe4ea"


def _layout(figure: go.Figure, height: int = 420) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=45, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", color=NAVY, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    figure.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    figure.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return figure


def stress_profile_figure(result: CalculationResult) -> go.Figure:
    frame = pd.DataFrame(result.slices)
    center = frame[frame["punto"] == result.points[0].name]
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=center["sigma_v0_efectiva_kpa"], y=center["z_m"], name="sigma'v0", line=dict(color=NAVY, width=2)
    ))
    figure.add_trace(go.Scatter(
        x=center["delta_sigma_z_kpa"], y=center["z_m"], name="Delta sigma z", line=dict(color=RED, width=2)
    ))
    figure.update_yaxes(autorange="reversed", title="Profundidad desde el terreno (m)")
    figure.update_xaxes(title="Tension (kPa)")
    figure.update_layout(title="Perfil de tensiones en el punto de control")
    return _layout(figure)


def settlement_components_figure(result: CalculationResult) -> go.Figure:
    records = []
    for point in result.points:
        records.extend([
            {"Punto": point.name, "Componente": "Inmediato", "Asiento (mm)": point.immediate_mm},
            {"Punto": point.name, "Componente": "Primario", "Asiento (mm)": point.primary_final_mm},
            {"Punto": point.name, "Componente": "Secundario", "Asiento (mm)": point.secondary_service_mm},
        ])
    frame = pd.DataFrame(records)
    figure = px.bar(
        frame,
        x="Punto",
        y="Asiento (mm)",
        color="Componente",
        barmode="relative",
        color_discrete_map={"Inmediato": NAVY, "Primario": RED, "Secundario": GREEN},
        title="Componentes del asiento",
    )
    return _layout(figure)


def time_figure(result: CalculationResult) -> go.Figure:
    figure = go.Figure(go.Scatter(
        x=result.time_years,
        y=result.time_settlement_mm,
        line=dict(color=RED, width=3),
        name="Centro",
        hovertemplate="%{x:.3g} anos<br>%{y:.2f} mm<extra></extra>",
    ))
    figure.update_xaxes(type="log", title="Tiempo (anos)")
    figure.update_yaxes(title="Asiento acumulado (mm)")
    figure.update_layout(title="Evolucion temporal hasta la vida de servicio")
    return _layout(figure)


def contact_pressure_figure(result: CalculationResult) -> go.Figure:
    field = result.pressure_field
    figure = go.Figure(go.Scatter(
        x=field.x_m,
        y=field.y_m,
        mode="markers",
        marker=dict(
            color=field.gross_pressure_kpa,
            colorscale="RdYlBu_r",
            size=9,
            colorbar=dict(title="q bruta<br>(kPa)"),
            line=dict(width=0),
        ),
        hovertemplate="x=%{x:.2f} m<br>y=%{y:.2f} m<br>q=%{marker.color:.2f} kPa<extra></extra>",
    ))
    figure.update_yaxes(scaleanchor="x", scaleratio=1, title="y (m)")
    figure.update_xaxes(title="x (m)")
    figure.update_layout(title="Distribucion de presion bruta de contacto", showlegend=False)
    return _layout(figure)

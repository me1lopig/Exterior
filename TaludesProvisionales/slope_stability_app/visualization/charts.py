"""Construccion de figuras Plotly sin estado global."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from slope_stability_app.calculations.geometry import ground_elevation
from slope_stability_app.calculations.search import CriticalResult
from slope_stability_app.models import SlopeGeometry, SoilProfile


INK = "#17202A"
MUTED = "#667085"
ACCENT = "#D97706"
WATER = "#2878B5"
GRID = "#E7E9ED"


def _base_layout(fig: go.Figure, height: int = 500) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=38, r=24, t=42, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", color=INK, size=12),
        hoverlabel=dict(bgcolor="white", font_color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)


def section_figure(
    geometry: SlopeGeometry,
    profile: SoilProfile,
    critical: CriticalResult | None = None,
) -> go.Figure:
    x = np.linspace(geometry.x_min, geometry.x_max, 500)
    ground = ground_elevation(x, geometry)
    bottom = -0.8 * geometry.height
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ground,
            fill="tonexty",
            fillcolor="rgba(155, 134, 98, 0.20)",
            line=dict(color=INK, width=2.3),
            name="Terreno",
            hovertemplate="x=%{x:.2f} m<br>z=%{y:.2f} m<extra></extra>",
        )
    )
    if profile.has_two_soils:
        fig.add_hline(
            y=profile.interface_elevation,
            line=dict(color="#8B5E3C", width=2, dash="dash"),
            annotation_text="Contacto de suelos",
            annotation_position="bottom left",
        )
    water_surface = np.minimum(ground, geometry.water_elevation)
    mask = water_surface > bottom
    fig.add_trace(
        go.Scatter(
            x=x[mask],
            y=water_surface[mask],
            line=dict(color=WATER, width=2, dash="dot"),
            name="Nivel freatico",
            hovertemplate="NF z=%{y:.2f} m<extra></extra>",
        )
    )
    if critical is not None:
        circle = critical.evaluation.circle
        xs = np.linspace(circle.entry_x, circle.exit_x, 350)
        base = circle.base_elevation(xs)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=base,
                line=dict(color=ACCENT, width=3),
                name=f"{critical.method}: FS={critical.factor_of_safety:.3f}",
                hovertemplate="Superficie critica<br>x=%{x:.2f} m<br>z=%{y:.2f} m<extra></extra>",
            )
        )
        for item in critical.evaluation.slices:
            fig.add_shape(
                type="line",
                x0=item.x_mid,
                x1=item.x_mid,
                y0=item.base_elevation,
                y1=item.top_elevation,
                line=dict(color="rgba(23,32,42,0.18)", width=1),
            )
        fig.add_trace(
            go.Scatter(
                x=[circle.center_x],
                y=[circle.center_y],
                mode="markers",
                marker=dict(symbol="cross", color=ACCENT, size=10),
                name="Centro",
                hovertemplate="Centro (%{x:.2f}, %{y:.2f}) m<extra></extra>",
            )
        )
    _base_layout(fig, 520)
    fig.update_xaxes(title="Distancia x (m)")
    fig.update_yaxes(title="Cota z (m)", scaleanchor="x", scaleratio=1)
    return fig


def sensitivity_figure(data: pd.DataFrame) -> go.Figure:
    n_angles = data["Pendiente (deg)"].nunique()
    n_waters = data["Nivel freatico (m)"].nunique()
    if n_angles > 1 and n_waters > 1:
        pivot = data.pivot(index="Nivel freatico (m)", columns="Pendiente (deg)", values="FS Bishop")
        fig = go.Figure(
            go.Heatmap(
                x=pivot.columns,
                y=pivot.index,
                z=pivot.values,
                colorscale=[[0, "#B42318"], [0.45, "#F6C453"], [1, "#287271"]],
                colorbar=dict(title="FS Bishop"),
                hovertemplate="Pendiente=%{x:.1f} deg<br>NF=%{y:.2f} m<br>FS=%{z:.3f}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Pendiente (deg)")
        fig.update_yaxes(title="Cota del nivel freatico (m)", autorange="reversed")
    else:
        variable = "Pendiente (deg)" if n_angles > 1 else "Nivel freatico (m)"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data[variable], y=data["FS Fellenius"], mode="lines+markers", name="Fellenius"))
        fig.add_trace(go.Scatter(x=data[variable], y=data["FS Bishop"], mode="lines+markers", name="Bishop simplificado", line=dict(color=ACCENT)))
        fig.update_xaxes(title=variable)
        fig.update_yaxes(title="Factor de seguridad")
    _base_layout(fig, 430)
    return fig

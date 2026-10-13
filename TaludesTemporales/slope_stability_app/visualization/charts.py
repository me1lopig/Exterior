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
SOIL_COLORS = (
    "rgba(224, 210, 180, 0.72)",
    "rgba(184, 202, 186, 0.66)",
    "rgba(199, 190, 211, 0.64)",
    "rgba(218, 190, 174, 0.64)",
    "rgba(177, 198, 211, 0.64)",
    "rgba(211, 201, 169, 0.64)",
)


def _filled_band(
    fig: go.Figure,
    x: np.ndarray,
    top: np.ndarray,
    bottom: np.ndarray,
    name: str,
    color: str,
) -> None:
    """Añade un estrato como polígono cerrado sin alterar el contorno del terreno."""
    fig.add_trace(
        go.Scatter(
            x=np.concatenate((x, x[::-1])),
            y=np.concatenate((top, bottom[::-1])),
            mode="lines",
            line=dict(width=0),
            fill="toself",
            fillcolor=color,
            name=name,
            hoverinfo="skip",
        )
    )


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
    bottom = geometry.model_base_elevation
    fig = go.Figure()

    cumulative = 0.0
    for index, layer in enumerate(profile.layers):
        layer_top = geometry.height - cumulative
        cumulative += layer.thickness
        layer_bottom = max(geometry.height - cumulative, bottom)
        if layer_top <= bottom + 1e-9:
            break
        layer_mask = ground >= layer_bottom - 1e-9
        _filled_band(
            fig,
            x[layer_mask],
            np.minimum(ground[layer_mask], layer_top),
            np.full(np.count_nonzero(layer_mask), layer_bottom),
            f"Capa {index + 1}: {layer.soil.name}",
            SOIL_COLORS[index % len(SOIL_COLORS)],
        )
        if cumulative < geometry.model_depth - 1e-9:
            contact = geometry.height - cumulative
            contact_mask = ground >= contact - 1e-9
            fig.add_trace(
                go.Scatter(
                    x=x[contact_mask],
                    y=np.full(np.count_nonzero(contact_mask), contact),
                    line=dict(color="#7A6652", width=1.5, dash="dot"),
                    name="Contactos entre capas",
                    showlegend=index == 0,
                    hovertemplate=f"Contacto {index + 1}<br>z=%{{y:.2f}} m<extra></extra>",
                )
            )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ground,
            line=dict(color=INK, width=2.3),
            name="Terreno",
            hovertemplate="x=%{x:.2f} m<br>z=%{y:.2f} m<extra></extra>",
        )
    )

    # El NF horizontal termina donde aflora en el terreno; no sigue la cara del talud.
    water_mask = ground >= geometry.water_elevation - 1e-9
    fig.add_trace(
        go.Scatter(
            x=x[water_mask],
            y=np.full(np.count_nonzero(water_mask), geometry.water_elevation),
            line=dict(color=WATER, width=2, dash="dash"),
            name=f"NF d={geometry.water_depth:.2f} m",
            hovertemplate="NF z=%{y:.2f} m<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[geometry.x_min, geometry.x_max],
            y=[bottom, bottom],
            line=dict(color=MUTED, width=1, dash="dash"),
            name=f"Limite del modelo d={geometry.model_depth:.2f} m",
            hovertemplate="Limite inferior z=%{y:.2f} m<extra></extra>",
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
    n_waters = data["Profundidad NF (m)"].nunique()
    if n_angles > 1 and n_waters > 1:
        pivot = data.pivot(index="Profundidad NF (m)", columns="Pendiente (deg)", values="FS Bishop")
        fig = go.Figure(
            go.Heatmap(
                x=pivot.columns,
                y=pivot.index,
                z=pivot.values,
                colorscale=[[0, "#B42318"], [0.45, "#F6C453"], [1, "#287271"]],
                colorbar=dict(title="FS Bishop"),
                hovertemplate="Pendiente=%{x:.1f} deg<br>Prof. NF=%{y:.2f} m<br>FS=%{z:.3f}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Pendiente (deg)")
        fig.update_yaxes(title="Profundidad NF desde coronacion (m)", autorange="reversed")
    else:
        variable = "Pendiente (deg)" if n_angles > 1 else "Profundidad NF (m)"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data[variable], y=data["FS Fellenius"], mode="lines+markers", name="Fellenius"))
        fig.add_trace(go.Scatter(x=data[variable], y=data["FS Bishop"], mode="lines+markers", name="Bishop simplificado", line=dict(color=ACCENT)))
        fig.update_xaxes(title=variable)
        fig.update_yaxes(title="Factor de seguridad")
    _base_layout(fig, 430)
    return fig

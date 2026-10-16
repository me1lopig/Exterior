from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLORS = {
    "ink": "#0B2239",
    "coral": "#E55353",
    "green": "#12905A",
    "blue": "#2164AF",
    "gray": "#778292",
}


def _layout(fig, title: str):
    fig.update_layout(
        title=title,
        font={"family": "Arial", "color": COLORS["ink"]},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
        legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#E7EBEF", zeroline=False)
    fig.update_yaxes(gridcolor="#E7EBEF", zeroline=False)
    return fig


def optimization_figure(results: pd.DataFrame):
    if results.empty:
        return go.Figure()
    if results["L_m"].nunique() > 1:
        value_column = (
            "Q_limite_estructura_kn"
            if "Q_limite_estructura_kn" in results
            else "util_h_max"
        )
        pivot = results.pivot(index="L_m", columns="B_m", values=value_column)
        fig = px.imshow(
            pivot,
            aspect="auto",
            color_continuous_scale=["#E8F0F8", COLORS["blue"]],
            text_auto=".0f",
            labels={"x": "B (m)", "y": "L (m)", "color": "Carga admisible (kN)"},
        )
        fig.update_traces(textfont={"size": 12})
    else:
        y_columns = (
            ["Q_limite_estructura_kn"]
            if "Q_limite_estructura_kn" in results
            else ["util_h_max"]
        )
        fig = px.line(
            results.sort_values("B_m"),
            x="B_m",
            y=y_columns,
            markers=True,
            labels={
                "value": "Carga admisible (kN)",
                "B_m": "B (m)",
                "variable": "Resultado",
            },
            color_discrete_sequence=[COLORS["coral"], COLORS["blue"]],
        )
        fig.update_traces(
            mode="lines+markers+text",
            texttemplate="%{y:.0f}",
            textposition="top center",
        )
    return _layout(fig, "Carga admisible para la malla de dimensiones")


def terms_figure(terms: dict[str, float]):
    frame = pd.DataFrame(
        {"termino": list(terms.keys()), "kPa": list(terms.values())}
    )
    fig = px.bar(
        frame,
        x="termino",
        y="kPa",
        color="kPa",
        color_continuous_scale=["#DCE6F1", COLORS["blue"]],
    )
    fig.update_coloraxes(showscale=False)
    return _layout(fig, "Contribuciones a la resistencia caracteristica")


def settlement_depth_figure(unit_result: dict[str, object]):
    settlement = pd.DataFrame(unit_result["settlement_profile"])
    stress = pd.DataFrame(unit_result["stress_profile"])
    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        horizontal_spacing=0.10,
        subplot_titles=("Acortamiento acumulado", "Incremento de tension"),
    )
    fig.add_trace(
        go.Scatter(
            x=settlement["settlement_mm"],
            y=settlement["depth_below_base_m"],
            mode="lines+markers",
            line={"color": COLORS["coral"]},
            name="s acumulado",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=stress["delta_sigma_kpa"],
            y=stress["depth_below_base_m"],
            mode="lines",
            line={"color": COLORS["blue"]},
            name="Delta sigma z",
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(title_text="Profundidad bajo la base (m)", autorange="reversed", row=1, col=1)
    fig.update_xaxes(title_text="Asiento (mm)", row=1, col=1)
    fig.update_xaxes(title_text="Delta sigma z (kPa)", row=1, col=2)
    return _layout(fig, "Respuesta vertical para una presion neta unitaria")

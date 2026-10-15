from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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
            labels={"x": "B (m)", "y": "L (m)", "color": "Carga admisible (kN)"},
        )
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
    return _layout(fig, "Carga admisible para la malla de dimensiones")


def sensitivity_figure(data: pd.DataFrame):
    if data.empty:
        return go.Figure()
    fig = px.line(
        data,
        x="factor",
        y="utilizacion",
        color="variable",
        markers=True,
        labels={"factor": "Factor sobre valor base", "utilizacion": "Utilizacion"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color=COLORS["ink"])
    return _layout(fig, "Sensibilidad de la resistencia de hundimiento")


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

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from calculos.asientos import ResultadoCalculo
from modelos.datos import Cimentacion


AZUL = "#12304A"
AZUL_CLARO = "#2164AF"
ROJO = "#E45454"
VERDE = "#17835C"
GRIS = "#778497"


def _estilo_base(fig: go.Figure, titulo_x: str, titulo_y: str) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=25, r=20, t=35, b=25),
        font=dict(family="Open Sans, Arial", color=AZUL, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        hovermode="y unified",
    )
    fig.update_xaxes(title=titulo_x, showgrid=True, gridcolor="#E8ECF1", zeroline=False)
    fig.update_yaxes(title=titulo_y, showgrid=True, gridcolor="#E8ECF1", autorange="reversed")
    return fig


def figura_tensiones(resultado: ResultadoCalculo) -> go.Figure:
    df = resultado.perfiles[resultado.perfiles["Punto"] == "Centro"]
    fig = go.Figure()
    series = [
        ("σv0 total", "sigma_v0_total_kPa", GRIS, "solid"),
        ("σ'v0 efectiva", "sigma_v0_ef_kPa", VERDE, "solid"),
        ("Δσz zapata", "delta_sigma_z_kPa", ROJO, "solid"),
        ("σ'v0 + Δσz", "sigma_ef_final_kPa", AZUL_CLARO, "dash"),
    ]
    for nombre, columna, color, dash in series:
        fig.add_trace(
            go.Scatter(
                x=df[columna], y=df["z_bajo_base_m"], mode="lines",
                name=nombre, line=dict(color=color, width=2.4, dash=dash),
            )
        )
    return _estilo_base(fig, "Tensión vertical (kPa)", "Profundidad bajo la base (m)")


def figura_asientos(resultado: ResultadoCalculo) -> go.Figure:
    fig = go.Figure()
    colores = [AZUL_CLARO, ROJO, VERDE, "#8A5CA8", "#D18C1D", GRIS]
    for color, (nombre, df) in zip(colores, resultado.perfiles.groupby("Punto", sort=False)):
        fig.add_trace(
            go.Scatter(
                x=df["desplazamiento_mm"], y=df["z_bajo_base_m"], mode="lines",
                name=nombre, line=dict(color=color, width=2.2),
            )
        )
    return _estilo_base(fig, "Desplazamiento vertical w (mm)", "Profundidad bajo la base (m)")


def figura_deformacion(resultado: ResultadoCalculo) -> go.Figure:
    df = resultado.perfiles[resultado.perfiles["Punto"] == "Centro"]
    fig = go.Figure(
        go.Scatter(
            x=df["epsilon_z"] * 1000.0,
            y=df["z_bajo_base_m"],
            mode="lines",
            line=dict(color=ROJO, width=2.4),
            name="εz",
        )
    )
    return _estilo_base(fig, "Deformación vertical εz (‰)", "Profundidad bajo la base (m)")


def figura_bulbo(
    malla: dict,
    cimentacion: Cimentacion,
    estratos: pd.DataFrame,
) -> go.Figure:
    eje = str(malla["eje"][0])
    ancho = cimentacion.b_m if eje == "B" else cimentacion.l_m
    porcentaje = 100.0 * malla["delta_sigma_kPa"] / cimentacion.q_neta_kpa
    fig = go.Figure(
        go.Contour(
            x=malla["x_m"], y=malla["z_m"], z=porcentaje,
            contours=dict(start=5, end=80, size=5, coloring="heatmap", showlabels=True),
            colorscale=[[0.0, "#FFFFFF"], [0.25, "#DDEAF6"], [0.55, "#76A8CF"], [0.8, "#F2AA6B"], [1.0, "#D94F4F"]],
            colorbar=dict(title="Δσz/q (%)"),
            hovertemplate="x=%{x:.2f} m<br>z=%{y:.2f} m<br>Δσ/q=%{z:.1f}%<extra></extra>",
        )
    )
    fig.add_shape(type="rect", x0=-ancho / 2, x1=ancho / 2, y0=-0.12, y1=0.0,
                  line=dict(color=AZUL, width=2), fillcolor="#D9DEE5")
    for limite in estratos["z_inf_m"].to_numpy(dtype=float) - cimentacion.df_m:
        if 0 < limite < float(malla["z_m"][-1]):
            fig.add_hline(y=limite, line_width=1, line_dash="dot", line_color="#687487")
    fig.update_layout(
        template="plotly_white", margin=dict(l=25, r=20, t=35, b=25),
        font=dict(family="Open Sans, Arial", color=AZUL, size=12),
    )
    fig.update_xaxes(title=f"Distancia en dirección {eje} (m)", zeroline=False)
    fig.update_yaxes(title="Profundidad bajo la base (m)", autorange="reversed", scaleanchor="x", scaleratio=1)
    return fig


def figura_aporte_estratos(resultado: ResultadoCalculo) -> go.Figure:
    df = resultado.resumen_estratos
    fig = go.Figure(
        go.Bar(
            x=df["asiento_mm"], y=df["Estrato"], orientation="h",
            marker_color=AZUL_CLARO,
            text=df["asiento_mm"].map(lambda v: f"{v:.2f} mm"), textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_white", margin=dict(l=25, r=35, t=25, b=25),
        font=dict(family="Open Sans, Arial", color=AZUL, size=12), showlegend=False,
    )
    fig.update_xaxes(title="Aporte al asiento bajo el centro (mm)", gridcolor="#E8ECF1")
    fig.update_yaxes(title="", autorange="reversed")
    return fig


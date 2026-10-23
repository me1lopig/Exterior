"""Construccion del perfil interactivo con Plotly."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from perfil_geologico.calculos.contactos import interpolar_contacto
from perfil_geologico.calculos.dpsh import separar_tramos_contiguos
from perfil_geologico.modelos.dominio import Contacto, Proyecto


def _rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(160,160,160,{alpha})"
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def crear_figura_perfil(
    proyecto: Proyecto,
    sondeos: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
    contactos: list[Contacto],
    dpsh: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame,
    zonas: list[dict] | None = None,
    escala_dpsh: float = 0.12,
    mostrar_rellenos: bool = True,
    mostrar_dpsh: bool = True,
) -> go.Figure:
    """Crea la vista tecnica principal del perfil."""
    figura = go.Figure()
    if sondeos.empty:
        figura.update_layout(template="plotly_white")
        return figura

    unidades_orden = unidades.sort_values("orden")
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    orden = dict(zip(unidades["unidad_id"].astype(str), unidades["orden"].astype(float)))
    sondeos_orden = sondeos.sort_values("s_m")
    terreno = sondeos_orden.groupby("s_m", as_index=False)["cota_boca_m"].mean()
    s_terreno = terreno["s_m"].to_numpy(float)
    z_terreno = terreno["cota_boca_m"].to_numpy(float)
    xmin, xmax = float(s_terreno.min()), float(s_terreno.max())
    ancho = max(xmax - xmin, 1.0)
    estaciones = np.linspace(xmin, xmax, 501)
    z_sup = np.interp(estaciones, s_terreno, z_terreno)

    contactos_orden = sorted(contactos, key=lambda c: orden.get(c.unidad_inferior, 1e9))
    zonas = zonas or []
    if mostrar_rellenos and zonas:
        tramas = {
            "sin_trama": "", "horizontal": "-", "vertical": "|", "diagonal_45": "/",
            "diagonal_135": "\\", "cruzada": "x", "puntos": ".", "grava": "o", "roca": "+",
        }
        unidades_mostradas: set[str] = set()
        for zona in sorted(zonas, key=lambda item: float(item.get("area_m2", 0.0)), reverse=True):
            coordenadas = zona.get("coordenadas", [])
            if len(coordenadas) < 3:
                continue
            unidad = str(zona.get("unidad_id", ""))
            x = [p[0] for p in coordenadas] + [coordenadas[0][0]]
            y = [p[1] for p in coordenadas] + [coordenadas[0][1]]
            figura.add_trace(
                go.Scatter(
                    x=x, y=y, mode="lines", fill="toself",
                    line={"color": "rgba(70,80,90,0.45)", "width": 0.7},
                    fillcolor=_rgba(str(zona.get("color", "#D9DDE2")), 0.58),
                    fillpattern={"shape": tramas.get(str(zona.get("trama", "sin_trama")), "")},
                    name=nombres.get(unidad, unidad or "Sin asignar"),
                    legendgroup=f"unidad-{unidad}", showlegend=unidad not in unidades_mostradas,
                    customdata=[[zona.get("etiqueta", ""), unidad]] * len(x),
                    hovertemplate="%{customdata[0]}<br>unidad=%{customdata[1]}<extra></extra>",
                )
            )
            unidades_mostradas.add(unidad)
    elif mostrar_rellenos:
        for contacto in contactos_orden:
            z_inf = interpolar_contacto(contacto, estaciones)
            mascara = np.isfinite(z_sup) & np.isfinite(z_inf)
            if mascara.any():
                x = estaciones[mascara]
                pol_x = np.concatenate([x, x[::-1]])
                pol_y = np.concatenate([z_sup[mascara], z_inf[mascara][::-1]])
                unidad = contacto.unidad_superior
                figura.add_trace(
                    go.Scatter(
                        x=pol_x,
                        y=pol_y,
                        mode="lines",
                        line={"width": 0},
                        fill="toself",
                        fillcolor=_rgba(colores.get(unidad, "#A0A0A0"), 0.58),
                        name=nombres.get(unidad, unidad),
                        legendgroup=f"unidad-{unidad}",
                        hoverinfo="skip",
                    )
                )
                z_sup = np.where(mascara, z_inf, z_sup)
        if contactos_orden:
            ultima = contactos_orden[-1].unidad_inferior
            fondo = min(
                float((sondeos["cota_boca_m"] - sondeos["profundidad_m"]).min()),
                float(np.nanmin(z_sup)) - 2.0,
            )
            mascara = np.isfinite(z_sup)
            x = estaciones[mascara]
            pol_x = np.concatenate([x, x[::-1]])
            pol_y = np.concatenate([z_sup[mascara], np.full_like(x, fondo)[::-1]])
            figura.add_trace(
                go.Scatter(
                    x=pol_x, y=pol_y, mode="lines", line={"width": 0}, fill="toself",
                    fillcolor=_rgba(colores.get(ultima, "#8B9098"), 0.58),
                    name=nombres.get(ultima, ultima), legendgroup=f"unidad-{ultima}", hoverinfo="skip",
                )
            )

    figura.add_trace(
        go.Scatter(
            x=s_terreno,
            y=z_terreno,
            mode="lines+markers",
            line={"color": "#0A2239", "width": 2.2},
            marker={"size": 5, "color": "#0A2239"},
            name="Terreno / bocas",
            hovertemplate="s=%{x:.2f} m<br>cota=%{y:.2f} m<extra></extra>",
        )
    )

    ancho_sondeo = max(ancho * 0.007, 0.55)
    for sondeo in sondeos_orden.itertuples(index=False):
        grupo = intervalos[intervalos["sondeo_id"] == sondeo.sondeo_id].sort_values("desde_m")
        for tramo in grupo.itertuples(index=False):
            techo = float(sondeo.cota_boca_m) - float(tramo.desde_m)
            muro = float(sondeo.cota_boca_m) - float(tramo.hasta_m)
            unidad = str(tramo.unidad_id)
            figura.add_shape(
                type="rect",
                x0=float(sondeo.s_m) - ancho_sondeo,
                x1=float(sondeo.s_m) + ancho_sondeo,
                y0=muro,
                y1=techo,
                line={"color": "white", "width": 0.6},
                fillcolor=colores.get(unidad, "#C7CBD1"),
                layer="above",
            )
        figura.add_annotation(
            x=float(sondeo.s_m), y=float(sondeo.cota_boca_m) + 0.65,
            text=str(sondeo.sondeo_id), showarrow=False, yanchor="bottom",
            font={"size": 11, "color": "#0A2239"},
        )

    for contacto in contactos_orden:
        if len(contacto.vertices) < 2:
            continue
        estilos = ["solid" if punto.origen == "observado" else "dot" for punto in contacto.vertices]
        dash = "solid" if all(estilo == "solid" for estilo in estilos) else "dash"
        figura.add_trace(
            go.Scatter(
                x=[punto.s_m for punto in contacto.vertices],
                y=[punto.z_m for punto in contacto.vertices],
                mode="lines+markers",
                line={"color": contacto.color, "width": 2.0, "dash": dash},
                marker={
                    "size": 7,
                    "color": ["#0A2239" if p.origen == "observado" else "white" for p in contacto.vertices],
                    "line": {"color": contacto.color, "width": 1.5},
                },
                name=contacto.nombre,
                customdata=[[p.origen, p.referencia] for p in contacto.vertices],
                hovertemplate="s=%{x:.2f} m<br>cota=%{y:.2f} m<br>%{customdata[0]} %{customdata[1]}<extra></extra>",
            )
        )

    if mostrar_dpsh and not dpsh.empty:
        for ensayo in dpsh.sort_values("s_m").itertuples(index=False):
            grupo = lecturas_dpsh[lecturas_dpsh["ensayo_id"] == ensayo.ensayo_id]
            for indice, tramo in enumerate(separar_tramos_contiguos(grupo)):
                x = float(ensayo.s_m) + tramo["n20"].to_numpy(float) * escala_dpsh
                z = float(ensayo.cota_inicio_m) - tramo["profundidad_m"].to_numpy(float)
                figura.add_trace(
                    go.Scatter(
                        x=x,
                        y=z,
                        mode="lines+markers",
                        line={"color": "#E45658", "width": 1.7, "shape": "linear"},
                        marker={"size": 4, "color": "#E45658"},
                        name=str(ensayo.ensayo_id),
                        legendgroup=str(ensayo.ensayo_id),
                        showlegend=indice == 0,
                        customdata=np.column_stack(
                            [tramo["profundidad_m"].to_numpy(float), tramo["n20"].to_numpy(float)]
                        ),
                        hovertemplate="prof.=%{customdata[0]:.2f} m<br>N20=%{customdata[1]:.0f}<extra></extra>",
                    )
                )
            profundidad = float(grupo["profundidad_m"].max()) if len(grupo) else float(ensayo.profundidad_m)
            figura.add_shape(
                type="line", x0=float(ensayo.s_m), x1=float(ensayo.s_m),
                y0=float(ensayo.cota_inicio_m), y1=float(ensayo.cota_inicio_m) - profundidad,
                line={"color": "rgba(228,86,88,0.45)", "width": 1, "dash": "dot"},
            )
            figura.add_annotation(
                x=float(ensayo.s_m), y=float(ensayo.cota_inicio_m) + 0.65,
                text=str(ensayo.ensayo_id), showarrow=False, yanchor="bottom",
                font={"size": 10, "color": "#B6383B"},
            )

    figura.update_layout(
        template="plotly_white",
        height=620,
        margin={"l": 55, "r": 25, "t": 25, "b": 55},
        paper_bgcolor="white",
        plot_bgcolor="#FAFBFC",
        font={"family": "Arial, sans-serif", "color": "#243447", "size": 12},
        hovermode="closest",
        dragmode="pan",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0.0, "font": {"size": 10}},
        xaxis={
            "title": "Distancia sobre el perfil, s (m)",
            "gridcolor": "#E1E5EA",
            "zeroline": False,
            "range": [xmin - ancho * 0.04, xmax + ancho * 0.12],
        },
        yaxis={
            "title": "Cota (m)",
            "gridcolor": "#E1E5EA",
            "zeroline": False,
        },
        modebar={"bgcolor": "rgba(255,255,255,0.85)"},
    )
    return figura

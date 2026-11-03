"""Construccion del perfil interactivo con Plotly."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from perfil_geologico.calculos.contactos import interpolar_contacto
from perfil_geologico.calculos.dpsh import separar_tramos_contiguos, distribucion_curvas
from perfil_geologico.modelos.dominio import Contacto, Proyecto
from perfil_geologico.calculos.presentacion import preparar_guitarra


def _rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(160,160,160,{alpha})"
    try:
        r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"rgba(160,160,160,{alpha})"
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
    rango_pk: tuple[float, float] | None = None,
    paso_guitarra: float | None = None,
    terreno_puntos: pd.DataFrame | None = None,
    spt: pd.DataFrame | None = None,
    muestras: pd.DataFrame | None = None,
    laboratorio: pd.DataFrame | None = None,
) -> go.Figure:
    """Crea la vista tecnica principal del perfil."""
    figura = go.Figure()
    if sondeos.empty and (terreno_puntos is None or terreno_puntos.empty):
        figura.update_layout(template='plotly_white')
        return figura
    capas = proyecto.capas
    mostrar_rellenos = mostrar_rellenos and capas.get('rellenos', True)
    mostrar_dpsh = mostrar_dpsh and capas.get('penetracion', True)

    unidades_orden = unidades.sort_values("orden")
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    orden = dict(zip(unidades["unidad_id"].astype(str), unidades["orden"].astype(float)))
    sondeos_orden = sondeos.sort_values("s_m")
    fuente = terreno_puntos if terreno_puntos is not None and not terreno_puntos.empty else sondeos_orden
    terreno = fuente.groupby("s_m", as_index=False)["cota_boca_m"].mean()
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
            huecos = [h for h in zona.get("huecos", []) if len(h) >= 3]
            if huecos:
                def trazar_anillo(anillo):
                    return "M " + " L ".join(f"{float(a):.8f},{float(b):.8f}" for a, b in anillo) + " Z"
                figura.add_shape(
                    type="path",
                    path=" ".join([trazar_anillo(coordenadas), *(trazar_anillo(h) for h in huecos)]),
                    fillrule="evenodd", fillcolor=_rgba(str(zona.get("color", "#D9DDE2")), 0.58),
                    line={"color": "rgba(70,80,90,0.45)", "width": 0.7}, layer="below",
                )
                figura.add_trace(go.Scatter(
                    x=[zona.get("centro_s_m")], y=[zona.get("centro_z_m")],
                    mode="markers", marker={"opacity": 0, "size": 1},
                    name=nombres.get(unidad, unidad or "Sin asignar"),
                    legendgroup=f"unidad-{unidad}", showlegend=unidad not in unidades_mostradas,
                    hovertemplate=f"{zona.get('etiqueta','')}<br>unidad={unidad}<extra></extra>",
                ))
                unidades_mostradas.add(unidad)
                continue
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
    # Sin poligonos validados no se inventan unidades por orden de contactos.

    if capas.get("terreno", True):
        figura.add_trace(
        go.Scatter(
            x=s_terreno,
            y=z_terreno,
            mode="lines",
            line={"color": "#0A2239", "width": 2.2},
            name="Terreno (puntos PERFIL1)",
            hovertemplate="s=%{x:.2f} m<br>cota=%{y:.2f} m<extra></extra>",
        )
    )

    ancho_sondeo = max(ancho * 0.007, 0.55)
    for sondeo in sondeos_orden.itertuples(index=False) if capas.get("sondeos",True) else []:
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
        figura.add_shape(
            type="line", x0=float(sondeo.s_m) - ancho_sondeo,
            x1=float(sondeo.s_m) + ancho_sondeo,
            y0=float(sondeo.cota_boca_m), y1=float(sondeo.cota_boca_m),
            line={"color": "#0A2239", "width": 2},
        )
        figura.add_annotation(
            x=float(sondeo.s_m), y=float(sondeo.cota_boca_m) + 0.65,
            text=str(sondeo.sondeo_id), showarrow=False, yanchor="bottom",
            font={"size": proyecto.texto_general_pt, "color": "#0A2239"},
        )

    for contacto in contactos_orden if capas.get("contactos",True) else []:
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
        escala_efectiva, sentidos = distribucion_curvas(dpsh, lecturas_dpsh, escala_dpsh,
                                                       sondeos, rango_pk or (xmin,xmax))
        for ensayo in dpsh.sort_values("s_m").itertuples(index=False):
            grupo = lecturas_dpsh[lecturas_dpsh["ensayo_id"] == ensayo.ensayo_id]
            for indice, tramo in enumerate(separar_tramos_contiguos(grupo)):
                x = float(ensayo.s_m) + sentidos.get(str(ensayo.ensayo_id),1) * tramo["n20"].to_numpy(float) * escala_efectiva
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
            figura.add_trace(go.Scatter(
                x=[float(ensayo.s_m)], y=[float(ensayo.cota_inicio_m)],
                mode="markers", marker={"size": 8, "color": "white",
                                         "line": {"color": "#E45658", "width": 2}},
                showlegend=False, name="Inicio penetrómetro",
                hovertemplate="Inicio de penetrómetro · PK %{x:.2f} m · cota %{y:.2f} m<extra></extra>",
            ))
            figura.add_annotation(
                x=float(ensayo.s_m), y=float(ensayo.cota_inicio_m) + 0.65,
                text=str(ensayo.ensayo_id), showarrow=False, yanchor="bottom",
                font={"size": proyecto.texto_ensayos_pt, "color": "#B6383B"},
            )

    # Capas de ensayos puntuales: profundidad y cota originales de los registros.
    if spt is not None and len(spt) and capas.get('spt', True):
        sp = spt.sort_values(['pk_m', 'profundidad_m'])
        figura.add_trace(go.Scatter(
            x=sp['pk_m'], y=sp['cota_m'], mode='markers+text',
            text=['SPT '+str(v) for v in sp['secuencia']],
            textposition='middle right',
            textfont={'size':proyecto.texto_ensayos_pt,'color':'#365E9C'},
            marker={'symbol':'line-ew','size':13,'line':{'color':'#365E9C','width':2}},
            name='SPT (golpes)',
            customdata=np.column_stack([sp['sondeo_id'],sp['profundidad_m'],sp['n_central'].fillna(-1)]),
            hovertemplate='%{customdata[0]} · prof. %{customdata[1]:.2f} m<br>%{text}<extra></extra>',
        ))
    if muestras is not None and len(muestras) and capas.get('muestras',False):
        grupos=muestras.copy()
        grupos['pk'] = grupos['reconocimiento'].map(
            {str(r.sondeo_id):float(r.s_m) for r in sondeos.itertuples(index=False)}).fillna(np.nan)
        grupos['z'] = grupos['reconocimiento'].map(
            {str(r.sondeo_id):float(r.cota_boca_m) for r in sondeos.itertuples(index=False)})-grupos['profundidad_m']
        grupos=grupos.dropna(subset=['pk','z'])
        figura.add_trace(go.Scatter(
            x=grupos['pk'],y=grupos['z'],mode='markers+text',
            text=[str(t)+' · '+str(u) for t,u in zip(grupos['tipo'],grupos['unidad_geotecnica'])],
            textposition='middle left',textfont={'size':proyecto.texto_ensayos_pt,'color':'#855F2E'},
            marker={'symbol':'square','size':7,'color':'#855F2E'}, name='Muestras'))
    if laboratorio is not None and len(laboratorio) and capas.get('laboratorio',False):
        labs=laboratorio.loc[laboratorio['tipo'].ne('SPT')].copy()
        ubi={str(r.sondeo_id):(float(r.s_m),float(r.cota_boca_m)) for r in sondeos.itertuples(index=False)}
        for r in labs.itertuples(index=False):
            if r.reconocimiento not in ubi: continue
            pk,cota=ubi[r.reconocimiento]
            campos=[str(r.unidad_geotecnica)]
            if str(r.uscs).strip(): campos.append('USCS '+str(r.uscs))
            if pd.notna(r.ip_pct): campos.append(f'IP={float(r.ip_pct):g}%')
            if pd.notna(r.rcs_kpa): campos.append(f'RCS={float(r.rcs_kpa):g} kPa')
            figura.add_annotation(x=pk,y=cota-float(r.profundidad_m),text=' | '.join(campos),
               showarrow=False,xanchor='left',xshift=15,yshift=-max(12,proyecto.texto_ensayos_pt+3),
               font={'size':proyecto.texto_ensayos_pt,'color':'#6A5B4B'})

    # La guitarra comparte exactamente los PK del dibujo (x2 coincide con x).
    if rango_pk is not None:
        inicio, fin = float(rango_pk[0]), float(rango_pk[1])
    else:
        inicio, fin = xmin, xmax
    guitarra = preparar_guitarra(sondeos, dpsh, (inicio, fin),
                                 float(paso_guitarra or getattr(proyecto, 'guitarra_paso_m', 50.0)),
                                 terreno_puntos=terreno_puntos)
    if capas.get("guitarra",True):
        for y in (0.0, 1.0, 2.0, 3.0, 4.0):
            figura.add_trace(go.Scatter(
                x=[inicio, fin], y=[y, y], mode='lines', xaxis='x2', yaxis='y2',
                line={'color':'#7B8793', 'width':0.8}, hoverinfo='skip', showlegend=False))
        for marca in guitarra['marcas']:
            pk = marca['pk_m']
            figura.add_trace(go.Scatter(
                x=[pk, pk], y=[0,4], mode='lines', xaxis='x2', yaxis='y2',
                line={'color':'#CFD6DE', 'width':0.8}, hoverinfo='skip', showlegend=False))
            figura.add_trace(go.Scatter(
                x=[pk], y=[3.5], text=[f'{pk:.1f}' if abs(pk-round(pk))>1e-4 else f'{pk:.0f}'], mode='text', xaxis='x2', yaxis='y2',
                textfont={'size':proyecto.texto_guitarra_pt,'color':'#283849'}, hoverinfo='skip',showlegend=False))
            cota = marca['terreno_m']
            figura.add_trace(go.Scatter(
                x=[pk], y=[2.5], text=[f'{cota:.2f}' if cota is not None else '—'],
                mode='text', xaxis='x2', yaxis='y2',
                textfont={'size':proyecto.texto_guitarra_pt,'color':'#283849'}, hoverinfo='skip',showlegend=False))
        for rec in guitarra['reconocimientos']:
            altura = 1.5 if rec['tipo'] == 'Sondeo' else 0.5
            figura.add_trace(go.Scatter(
                x=[rec['pk_m']], y=[altura], mode='text', text=[rec['nombre']],
                xaxis='x2', yaxis='y2', textfont={'size':proyecto.texto_guitarra_pt,'color':'#0A5E80' if rec['tipo']=='Sondeo' else '#B6383B'},
                hovertemplate=f"{rec['tipo']} {rec['nombre']} - PK {rec['pk_m']:.2f} m<extra></extra>",showlegend=False))
        for altura, nombre in ((3.5,'PK (m)'),(2.5,'Cota (m)'),(1.5,'Sondeos'),(0.5,'Penetrómetros')):
            figura.add_annotation(xref='paper',yref='y2',x=0,y=altura,
                                  xanchor='right',xshift=-7,showarrow=False,
                                  text=nombre,font={'size':proyecto.texto_guitarra_pt,'color':'#344960'})
    figura.update_layout(
        template="plotly_white",
        height=780,
        margin={"l": 55, "r": 25, "t": 25, "b": 55},
        paper_bgcolor="white",
        plot_bgcolor="#FAFBFC",
        font={"family": "Arial, sans-serif", "color": "#243447", "size": 12},
        hovermode="closest",
        dragmode="pan",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0.0, "font": {"size": 10}},
        xaxis={
            "title": "",
            "gridcolor": "#E1E5EA",
            "zeroline": False,
            "domain": [0, 1],
            "range": [inicio, fin],
        },
        yaxis={
            "title": "Cota (m)",
            "domain": [0.29, 1],
            "scaleanchor": "x",
            "scaleratio": float(proyecto.exageracion_vertical),
            "gridcolor": "#E1E5EA",
            "zeroline": False,
        },
        xaxis2={"visible":capas.get("guitarra",True),"anchor":"y2", "domain":[0,1], "matches":"x", "range":[inicio,fin],
                "title":"Distancia sobre el perfil / PK (m)","showgrid":False,"zeroline":False},
        yaxis2={"visible":capas.get("guitarra",True),"anchor":"x2", "domain":[0,0.22], "range":[-0.05,4.05],
                "showticklabels":False,"showgrid":False,"zeroline":False,"fixedrange":True},
        modebar={"bgcolor": "rgba(255,255,255,0.85)"},
    )
    return figura

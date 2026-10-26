"""Exportaciones tecnicas sin dependencias de CAD propietarias."""

from __future__ import annotations

from io import BytesIO, StringIO

import numpy as np
import pandas as pd

from perfil_geologico.calculos.contactos import interpolar_contacto
from perfil_geologico.modelos.dominio import Contacto, Proyecto


def contactos_a_csv(contactos: list[Contacto]) -> bytes:
    filas = []
    for contacto in contactos:
        for orden, punto in enumerate(contacto.vertices, start=1):
            filas.append(
                {
                    "contacto_id": contacto.contacto_id,
                    "nombre": contacto.nombre,
                    "orden": orden,
                    "s_m": punto.s_m,
                    "z_m": punto.z_m,
                    "origen": punto.origen,
                    "referencia": punto.referencia,
                    "interfaz_id": punto.interfaz_id,
                }
            )
    return pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig")


def contactos_a_dxf(contactos: list[Contacto], zonas: list[dict] | None = None) -> bytes:
    """Genera un DXF ASCII R12 con contactos y contornos de zonas."""
    salida = StringIO()
    salida.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
    for contacto in contactos:
        if len(contacto.vertices) < 2:
            continue
        capa = contacto.contacto_id.upper()[:31]
        cerrado = (len(contacto.vertices) >= 4 and
                   abs(contacto.vertices[0].s_m - contacto.vertices[-1].s_m) < 1e-8 and
                   abs(contacto.vertices[0].z_m - contacto.vertices[-1].z_m) < 1e-8)
        salida.write(f"0\nPOLYLINE\n8\n{capa}\n66\n1\n70\n{1 if cerrado else 0}\n")
        for punto in contacto.vertices:
            salida.write(f"0\nVERTEX\n8\n{capa}\n10\n{punto.s_m:.6f}\n20\n{punto.z_m:.6f}\n30\n0.0\n")
        salida.write("0\nSEQEND\n")
    for zona in zonas or []:
        capa = f"ZONA_{zona.get('unidad_id') or 'SIN_ASIGNAR'}".upper()[:31]
        for coordenadas in [zona.get("coordenadas", []), *zona.get("huecos", [])]:
            if len(coordenadas) < 3:
                continue
            salida.write(f"0\nPOLYLINE\n8\n{capa}\n66\n1\n70\n1\n")
            for x, y in coordenadas:
                salida.write(f"0\nVERTEX\n8\n{capa}\n10\n{float(x):.6f}\n20\n{float(y):.6f}\n30\n0.0\n")
            salida.write("0\nSEQEND\n")
    salida.write("0\nENDSEC\n0\nEOF\n")
    return salida.getvalue().encode("ascii", errors="replace")


def figura_perfil_pdf(
    proyecto: Proyecto,
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
    contactos: list[Contacto],
    dpsh_proyectados: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame,
    escala_dpsh: float,
    zonas: list[dict] | None = None,
) -> bytes:
    """Crea un plano PDF estable con Matplotlib."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path

    fig, ax = plt.subplots(figsize=(16.5, 8.5), constrained_layout=True)
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    orden_unidades = dict(zip(unidades["unidad_id"].astype(str), unidades["orden"].astype(float)))
    sondeos_orden = sondeos_proyectados.sort_values("s_m")
    terreno = sondeos_orden.groupby("s_m", as_index=False)["cota_boca_m"].mean()
    estaciones = np.linspace(float(terreno["s_m"].min()), float(terreno["s_m"].max()), 501)
    superficie = np.interp(estaciones, terreno["s_m"], terreno["cota_boca_m"])
    fondo = float((sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()) - 2.0
    contactos_orden = sorted(contactos, key=lambda c: orden_unidades.get(c.unidad_inferior, 1e9))
    zonas = zonas or []
    if zonas:
        tramas = {
            "sin_trama": None, "horizontal": "---", "vertical": "|||", "diagonal_45": "///",
            "diagonal_135": "\\\\\\", "cruzada": "xxx", "puntos": "...", "grava": "OO", "roca": "++",
        }
        unidades_mostradas: set[str] = set()
        for zona in sorted(zonas, key=lambda item: float(item.get("area_m2", 0.0)), reverse=True):
            coordenadas = zona.get("coordenadas", [])
            if len(coordenadas) < 3:
                continue
            unidad = str(zona.get("unidad_id", ""))
            etiqueta = nombres.get(unidad, unidad or "Sin asignar")
            vertices_path = []
            codigos_path = []
            for indice_anillo, anillo in enumerate([coordenadas, *zona.get("huecos", [])]):
                if len(anillo) < 3:
                    continue
                vertices_anillo = [tuple(p) for p in anillo]
                area_orientada = sum(
                    a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(vertices_anillo, vertices_anillo[1:] + vertices_anillo[:1])
                )
                # El relleno no-cero de Matplotlib exige orientar los huecos
                # al contrario de su contorno exterior.
                if (indice_anillo == 0 and area_orientada < 0) or (indice_anillo > 0 and area_orientada > 0):
                    vertices_anillo.reverse()
                vertices_path.extend(vertices_anillo + [vertices_anillo[0]])
                codigos_path.extend([Path.MOVETO] + [Path.LINETO] * (len(vertices_anillo) - 1) + [Path.CLOSEPOLY])
            parche = PathPatch(
                Path(vertices_path, codigos_path), facecolor=zona.get("color", "#D9DDE2"),
                alpha=0.48, edgecolor="#667281", linewidth=0.4,
                hatch=tramas.get(zona.get("trama", "sin_trama")),
                label=etiqueta if unidad not in unidades_mostradas else None, zorder=1,
            )
            # Evita rellenar huecos interiores (regla par-impar).
            if hasattr(parche, 'set_fillrule'):
                parche.set_fillrule('evenodd')
            ax.add_patch(parche)
            unidades_mostradas.add(unidad)
    else:
        for contacto in contactos_orden:
            base = interpolar_contacto(contacto, estaciones)
            mascara = np.isfinite(superficie) & np.isfinite(base)
            ax.fill_between(
                estaciones, superficie, base, where=mascara,
                facecolor=colores.get(contacto.unidad_superior, "#cccccc"), alpha=0.42,
                linewidth=0, label=nombres.get(contacto.unidad_superior, contacto.unidad_superior), zorder=1,
            )
            superficie = np.where(mascara, base, superficie)
        if contactos_orden:
            ultima = contactos_orden[-1].unidad_inferior
            fondo = min(
                float((sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()),
                float(np.nanmin(superficie)) - 2.0,
            )
            ax.fill_between(
                estaciones, superficie, fondo, where=np.isfinite(superficie),
                facecolor=colores.get(ultima, "#cccccc"), alpha=0.42, linewidth=0,
                label=nombres.get(ultima, ultima), zorder=1,
            )
    for sondeo in sondeos_proyectados.itertuples(index=False):
        grupo = intervalos[intervalos["sondeo_id"] == sondeo.sondeo_id]
        for tramo in grupo.itertuples(index=False):
            techo = sondeo.cota_boca_m - tramo.desde_m
            muro = sondeo.cota_boca_m - tramo.hasta_m
            ax.add_patch(Rectangle((sondeo.s_m - 1.25, muro), 2.5, techo - muro,
                                   facecolor=colores.get(str(tramo.unidad_id), "#cccccc"),
                                   edgecolor="white", linewidth=0.4, zorder=4))
        ax.text(sondeo.s_m, sondeo.cota_boca_m + 0.8, sondeo.sondeo_id,
                ha="center", va="bottom", fontsize=8, fontweight="bold")
    for contacto in contactos_orden:
        ax.plot([p.s_m for p in contacto.vertices], [p.z_m for p in contacto.vertices],
                color=contacto.color, linewidth=1.6, marker="o", markersize=2.5,
                zorder=3)
    for ensayo in dpsh_proyectados.itertuples(index=False):
        grupo = lecturas_dpsh[lecturas_dpsh["ensayo_id"] == ensayo.ensayo_id].sort_values("profundidad_m")
        from perfil_geologico.calculos.dpsh import separar_tramos_contiguos
        profundidad = float(grupo["profundidad_m"].max()) if len(grupo) else float(ensayo.profundidad_m)
        for tramo in separar_tramos_contiguos(grupo):
            x = ensayo.s_m + tramo["n20"].to_numpy(float) * escala_dpsh
            z = ensayo.cota_inicio_m - tramo["profundidad_m"].to_numpy(float)
            ax.plot(x, z, color="#E45658", linewidth=1.2, marker="o", markersize=1.8, zorder=5)
        ax.plot(
            [ensayo.s_m, ensayo.s_m],
            [ensayo.cota_inicio_m, ensayo.cota_inicio_m - profundidad],
            color="#E45658", linewidth=0.5, alpha=0.4, linestyle=":", zorder=2,
        )
        ax.text(ensayo.s_m, ensayo.cota_inicio_m + 0.8, ensayo.ensayo_id,
                ha="center", va="bottom", fontsize=8, color="#B6383B")
    fig.suptitle(proyecto.nombre, x=0.045, ha="left", fontsize=15, fontweight="bold", color="#0A2239")
    ax.set_xlabel("Distancia sobre el perfil, s (m)")
    ax.set_ylabel("Cota (m)")
    ax.grid(True, color="#DDE2E8", linewidth=0.5)
    ax.set_facecolor("#FAFBFC")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="lower left", ncol=3, fontsize=7, frameon=False)
    x_min = float(sondeos_proyectados["s_m"].min())
    x_max = float(sondeos_proyectados["s_m"].max())
    y_min = min(float((sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()), fondo) - 0.6
    y_max = float(sondeos_proyectados["cota_boca_m"].max()) + 2.0
    ax.set_xlim(x_min - 0.04 * (x_max - x_min), x_max + 0.12 * (x_max - x_min))
    ax.set_ylim(y_min, y_max)
    rango_x = max(np.diff(ax.get_xlim())[0], 1e-9)
    rango_y = max(np.diff(ax.get_ylim())[0], 1e-9)
    aspecto_caja = max(1e-4, rango_y * proyecto.exageracion_vertical / rango_x)
    ax.set_box_aspect(float(aspecto_caja))
    salida = BytesIO()
    fig.savefig(salida, format="pdf", dpi=200, metadata={"Title": proyecto.nombre})
    plt.close(fig)
    return salida.getvalue()

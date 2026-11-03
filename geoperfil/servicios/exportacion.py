"""Exportaciones tecnicas sin dependencias de CAD propietarias."""

from __future__ import annotations

from io import BytesIO, StringIO

import numpy as np
import pandas as pd

from perfil_geologico.calculos.contactos import interpolar_contacto
from perfil_geologico.modelos.dominio import Contacto, Proyecto
from perfil_geologico.calculos.presentacion import preparar_guitarra
from perfil_geologico.calculos.dpsh import separar_tramos_contiguos, distribucion_curvas


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


def contactos_a_dxf(
    contactos: list[Contacto], zonas: list[dict] | None = None, *,
    proyecto: Proyecto | None = None, sondeos: pd.DataFrame | None = None,
    dpsh: pd.DataFrame | None = None, lecturas_dpsh: pd.DataFrame | None = None,
    intervalos: pd.DataFrame | None = None, unidades: pd.DataFrame | None = None,
    rango_pk: tuple[float,float] | None = None, escala_dpsh: float = 0.12,
    terreno_puntos: pd.DataFrame | None = None,
    spt: pd.DataFrame | None = None,
    muestras: pd.DataFrame | None = None,
    laboratorio: pd.DataFrame | None = None,
) -> bytes:
    """DXF R2010 con entidades editables, HATCH y guitarra en coordenadas PK/cota."""
    # Compatibilidad con la exportacion geometrica de versiones anteriores.
    if proyecto is None and sondeos is None:
        salida=StringIO()
        salida.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
        for contacto in contactos:
            if len(contacto.vertices)<2:
                continue
            capa=contacto.contacto_id.upper()[:31]
            puntos=[(p.s_m,p.z_m) for p in contacto.vertices]
            cerrado=(len(puntos)>=4 and abs(puntos[0][0]-puntos[-1][0])<1e-8
                      and abs(puntos[0][1]-puntos[-1][1])<1e-8)
            salida.write(f"0\nPOLYLINE\n8\n{capa}\n66\n1\n70\n{1 if cerrado else 0}\n")
            for x,y in puntos:
                salida.write(f"0\nVERTEX\n8\n{capa}\n10\n{x:.6f}\n20\n{y:.6f}\n30\n0.0\n")
            salida.write("0\nSEQEND\n")
        for zona in zonas or []:
            capa=f"ZONA_{zona.get('unidad_id') or 'SIN_ASIGNAR'}".upper()[:31]
            for anillo in [zona.get('coordenadas',[]),*zona.get('huecos',[])]:
                if len(anillo)<3:
                    continue
                salida.write(f"0\nPOLYLINE\n8\n{capa}\n66\n1\n70\n1\n")
                for x,y in anillo:
                    salida.write(f"0\nVERTEX\n8\n{capa}\n10\n{float(x):.6f}\n20\n{float(y):.6f}\n30\n0.0\n")
                salida.write("0\nSEQEND\n")
        salida.write("0\nENDSEC\n0\nEOF\n")
        return salida.getvalue().encode('ascii',errors='replace')
    import ezdxf
    doc = ezdxf.new('R2010', setup=True)
    model = doc.modelspace()
    capas = ('TERRENO','SONDEOS','CONTACTOS','LENTEJONES','UNIDADES',
             'TRAMAS','DPSH','GUITARRA','TEXTOS','SPT','MUESTRAS','LABORATORIO')
    for capa in capas:
        if not doc.layers.has_entry(capa):
            doc.layers.new(name=capa)
    def linea(puntos, capa, cerrado=False):
        if len(puntos) < 2:
            return
        model.add_lwpolyline([(float(x),float(y)) for x,y in puntos], close=cerrado,
                             dxfattribs={'layer':capa})
    def texto(valor, x, y, tam=1.3, capa='TEXTOS'):
        model.add_text(str(valor),dxfattribs={'layer':capa,'height':tam,'insert':(float(x),float(y))})
    for contacto in contactos if proyecto.capas.get('contactos', True) else []:
        if len(contacto.vertices)<2:
            continue
        vertices=[(p.s_m,p.z_m) for p in contacto.vertices]
        cerrado = len(vertices)>=3 and abs(vertices[0][0]-vertices[-1][0])<1e-7 and abs(vertices[0][1]-vertices[-1][1])<1e-7
        linea(vertices, 'LENTEJONES' if cerrado else 'CONTACTOS', cerrado=cerrado)
    patrones={'horizontal':'ANSI31','vertical':'ANSI31','diagonal_45':'ANSI31',
              'diagonal_135':'ANSI31','cruzada':'ANSI32','puntos':'DOTS',
              'grava':'AR-SAND','roca':'ANSI37'}
    for zona in (zonas or []) if proyecto.capas.get('rellenos',True) else []:
        exterior=zona.get('coordenadas',[])
        if len(exterior)<3:
            continue
        huecos=[h for h in zona.get('huecos',[]) if len(h)>=3]
        linea(exterior,'UNIDADES',cerrado=True)
        for hueco in huecos:
            linea(hueco,'UNIDADES',cerrado=True)
        if not zona.get('unidad_id'):
            continue   # No se rellena una zona no clasificada.
        hatch=model.add_hatch(color=8,dxfattribs={'layer':'TRAMAS'})
        color_hex=str(zona.get('color','#B7BEC8')).lstrip('#')
        if len(color_hex)==6:
            try:
                from ezdxf.colors import rgb2int
                hatch.dxf.true_color=rgb2int(tuple(int(color_hex[i:i+2],16) for i in (0,2,4)))
            except ValueError:
                pass
        patron=str(zona.get('trama','sin_trama'))
        if patron in patrones:
            angulo={'vertical':90,'horizontal':0,'diagonal_45':45,'diagonal_135':135}.get(patron,0)
            try:
                hatch.set_pattern_fill(patrones[patron],scale=1.5,angle=angulo)
            except ValueError:
                hatch.set_pattern_fill('ANSI31',scale=1.5)
        else:
            hatch.set_solid_fill(color=8)
        hatch.paths.add_polyline_path([(float(x),float(y)) for x,y in exterior], is_closed=True, flags=1)
        for hueco in huecos:
            hatch.paths.add_polyline_path([(float(x),float(y)) for x,y in hueco], is_closed=True, flags=0)
    if sondeos is not None and not sondeos.empty:
        fuente=terreno_puntos if terreno_puntos is not None and not terreno_puntos.empty else sondeos
        terreno = fuente.groupby('s_m',as_index=False)['cota_boca_m'].mean().sort_values('s_m')
        if proyecto.capas.get('terreno',True):
            linea(terreno[['s_m','cota_boca_m']].to_numpy(float).tolist(),'TERRENO')
        for fila in sondeos.itertuples(index=False) if proyecto.capas.get('sondeos',True) else []:
            linea([(fila.s_m,fila.cota_boca_m),(fila.s_m,fila.cota_boca_m-fila.profundidad_m)],'SONDEOS')
            model.add_circle((float(fila.s_m),float(fila.cota_boca_m)),
                             radius=0.10,dxfattribs={'layer':'SONDEOS'})
            texto(fila.sondeo_id, fila.s_m, fila.cota_boca_m+1.0)
        if dpsh is not None and not dpsh.empty and proyecto.capas.get('penetracion',True):
            escala_efectiva, sentidos = distribucion_curvas(dpsh,lecturas_dpsh,escala_dpsh,sondeos,rango_pk or
                    (float(terreno['s_m'].min()),float(terreno['s_m'].max())))
            for ensayo in dpsh.itertuples(index=False):
                profundidad=float(ensayo.profundidad_m)
                linea([(ensayo.s_m,ensayo.cota_inicio_m),
                       (ensayo.s_m,ensayo.cota_inicio_m-profundidad)],'DPSH')
                model.add_circle((float(ensayo.s_m),float(ensayo.cota_inicio_m)),
                                 radius=0.10,dxfattribs={'layer':'DPSH'})
                if lecturas_dpsh is not None and not lecturas_dpsh.empty:
                    lecturas = lecturas_dpsh[lecturas_dpsh['ensayo_id']==ensayo.ensayo_id]
                    for tramo in separar_tramos_contiguos(lecturas):
                        linea([(ensayo.s_m+sentidos.get(str(ensayo.ensayo_id),1)*float(v)*escala_efectiva, ensayo.cota_inicio_m-float(depth))
                               for depth,v in zip(tramo['profundidad_m'],tramo['n20'])], 'DPSH')
                texto(ensayo.ensayo_id, ensayo.s_m, ensayo.cota_inicio_m+1.0)
        if rango_pk is None:
            rango_pk=(float(terreno['s_m'].min()),float(terreno['s_m'].max()))
        guitarra=preparar_guitarra(sondeos,dpsh if dpsh is not None else pd.DataFrame(),
                   rango_pk,float(getattr(proyecto,'guitarra_paso_m',50.0)),terreno_puntos=terreno_puntos)
        inicio,fin=guitarra['limites']
        # La guitarra se sitúa bajo el último reconocimiento: Y son cotas CAD locales.
        base=float((sondeos['cota_boca_m']-sondeos['profundidad_m']).min())-10.0
        alto=max(1.5, (float(sondeos['cota_boca_m'].max())-float(sondeos['cota_boca_m'].min()))*0.06)
        for h in range(5) if proyecto.capas.get('guitarra',True) else []:
            y=base-h*alto
            linea([(inicio,y),(fin,y)],'GUITARRA')
        for marca in guitarra['marcas'] if proyecto.capas.get('guitarra',True) else []:
            pk=float(marca['pk_m'])
            linea([(pk,base),(pk,base-4*alto)],'GUITARRA')
            texto(f'{pk:g}',pk,base-.7*alto,max(0.7,alto*.30),'GUITARRA')
            z=marca['terreno_m']
            texto(f'{z:.2f}' if z is not None else '-',pk,base-1.7*alto,max(0.7,alto*.30),'GUITARRA')
        for rec in guitarra['reconocimientos'] if proyecto.capas.get('guitarra',True) else []:
            altura = 2.7 if rec['tipo'] == 'Sondeo' else 3.7
            texto(rec['nombre'],rec['pk_m'],base-altura*alto,max(0.7,alto*.30),'GUITARRA')
        for n,etiqueta in enumerate(('PK (m)','Cota (m)','Sondeos','Penetrómetros')) if proyecto.capas.get('guitarra',True) else []:
            texto(etiqueta,inicio-max((fin-inicio)*.10,5),base-(n+.7)*alto,max(.7,alto*.35),'GUITARRA')
    # Las anotaciones de ensayo son texto CAD real, en capas independientes.
    if sondeos is not None and not sondeos.empty:
        ubicaciones={str(x.sondeo_id):(float(x.s_m),float(x.cota_boca_m)) for x in sondeos.itertuples(index=False)}
        alto=max(0.55,min(2.5,float(proyecto.texto_ensayos_pt)*0.11))
        if spt is not None and len(spt) and proyecto.capas.get('spt',True):
            for r in spt.itertuples(index=False):
                if r.sondeo_id in ubicaciones:
                    x,z=ubicaciones[r.sondeo_id]
                    texto('SPT '+str(r.secuencia),x+0.7,z-float(r.profundidad_m),alto,'SPT')
        if muestras is not None and len(muestras) and proyecto.capas.get('muestras',False):
            for r in muestras.itertuples(index=False):
                if r.reconocimiento in ubicaciones:
                    x,z=ubicaciones[r.reconocimiento]
                    texto(str(r.tipo)+' '+str(r.unidad_geotecnica),x-0.7,z-float(r.profundidad_m),alto,'MUESTRAS')
        if laboratorio is not None and len(laboratorio) and proyecto.capas.get('laboratorio',False):
            for r in laboratorio.itertuples(index=False):
                if r.tipo=='SPT' or r.reconocimiento not in ubicaciones: continue
                x,z=ubicaciones[r.reconocimiento]
                contenido=str(r.unidad_geotecnica)
                if r.uscs: contenido+=' | USCS '+str(r.uscs)
                if pd.notna(r.ip_pct): contenido+=f' | IP={float(r.ip_pct):g}%'
                if pd.notna(r.rcs_kpa): contenido+=f' | RCS={float(r.rcs_kpa):g} kPa'
                texto(contenido,x+0.7,z-float(r.profundidad_m)-alto,alto,'LABORATORIO')
    out=StringIO()
    doc.write(out)
    return out.getvalue().encode('utf-8')


def _figura_perfil_documento(
    proyecto: Proyecto,
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
    contactos: list[Contacto],
    dpsh_proyectados: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame,
    escala_dpsh: float,
    zonas: list[dict] | None = None,
    rango_pk: tuple[float, float] | None = None,
    formato: str = 'pdf',
    terreno_puntos: pd.DataFrame | None = None,
    spt: pd.DataFrame | None = None,
    muestras: pd.DataFrame | None = None,
    laboratorio: pd.DataFrame | None = None,
) -> bytes:
    """Composicion unica Matplotlib para PDF, PNG y SVG."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path

    fig = plt.figure(figsize=(17.0, 8.7))
    gs = fig.add_gridspec(2,1,left=.085,right=.97,bottom=.10,top=.915,hspace=.16,
                          height_ratios=[4.4,1.25])
    ax = fig.add_subplot(gs[0])
    ax_g = fig.add_subplot(gs[1],sharex=ax)
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    orden_unidades = dict(zip(unidades["unidad_id"].astype(str), unidades["orden"].astype(float)))
    sondeos_orden = sondeos_proyectados.sort_values("s_m")
    fuente_terreno = terreno_puntos if terreno_puntos is not None and not terreno_puntos.empty else sondeos_orden
    terreno = fuente_terreno.groupby("s_m", as_index=False)["cota_boca_m"].mean().sort_values("s_m")
    estaciones = np.linspace(float(terreno["s_m"].min()), float(terreno["s_m"].max()), 501)
    superficie = np.interp(estaciones, terreno["s_m"], terreno["cota_boca_m"])
    fondo = float((sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()) - 2.0
    contactos_orden = sorted(contactos, key=lambda c: orden_unidades.get(c.unidad_inferior, 1e9))
    zonas = zonas or []
    if zonas and proyecto.capas.get('rellenos',True):
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
    # El terreno observado debe dibujarse incluso si no hay zonas interpretadas.
    if proyecto.capas.get('terreno',True):
        ax.plot(terreno['s_m'].to_numpy(float),terreno['cota_boca_m'].to_numpy(float),
            color='#0A2239',linewidth=1.7,
            zorder=5,label='Terreno (PERFIL1)')
    ancho_sondeo = max(float(terreno['s_m'].max()-terreno['s_m'].min()) * .007, .55)
    for sondeo in sondeos_proyectados.itertuples(index=False) if proyecto.capas.get('sondeos',True) else []:
        grupo = intervalos[intervalos["sondeo_id"] == sondeo.sondeo_id]
        for tramo in grupo.itertuples(index=False):
            techo = sondeo.cota_boca_m - tramo.desde_m
            muro = sondeo.cota_boca_m - tramo.hasta_m
            ax.add_patch(Rectangle((sondeo.s_m - ancho_sondeo, muro), 2 * ancho_sondeo, techo - muro,
                                   facecolor=colores.get(str(tramo.unidad_id), "#cccccc"),
                                   edgecolor="white", linewidth=0.4, zorder=4))
        ax.plot([sondeo.s_m - ancho_sondeo, sondeo.s_m + ancho_sondeo],
                [sondeo.cota_boca_m, sondeo.cota_boca_m],
                color='#0A2239', linewidth=1.3, zorder=6)
        ax.text(sondeo.s_m, sondeo.cota_boca_m + 0.8, sondeo.sondeo_id,
                ha="center", va="bottom", fontsize=proyecto.texto_general_pt, fontweight="bold")
    for contacto in contactos_orden if proyecto.capas.get('contactos',True) else []:
        ax.plot([p.s_m for p in contacto.vertices], [p.z_m for p in contacto.vertices],
                color=contacto.color, linewidth=1.6, marker="o", markersize=2.5,
                zorder=3)
    escala_efectiva, sentidos = distribucion_curvas(dpsh_proyectados,lecturas_dpsh,escala_dpsh,
        sondeos_proyectados,rango_pk or (float(terreno['s_m'].min()),float(terreno['s_m'].max())))
    for ensayo in dpsh_proyectados.itertuples(index=False) if proyecto.capas.get('penetracion',True) else []:
        grupo = lecturas_dpsh[lecturas_dpsh["ensayo_id"] == ensayo.ensayo_id].sort_values("profundidad_m")
        profundidad = float(grupo["profundidad_m"].max()) if len(grupo) else float(ensayo.profundidad_m)
        for tramo in separar_tramos_contiguos(grupo):
            x = ensayo.s_m + sentidos.get(str(ensayo.ensayo_id),1)*tramo["n20"].to_numpy(float) * escala_efectiva
            z = ensayo.cota_inicio_m - tramo["profundidad_m"].to_numpy(float)
            ax.plot(x, z, color="#E45658", linewidth=1.2, marker="o", markersize=1.8, zorder=5)
        ax.plot(
            [ensayo.s_m, ensayo.s_m],
            [ensayo.cota_inicio_m, ensayo.cota_inicio_m - profundidad],
            color="#E45658", linewidth=0.5, alpha=0.4, linestyle=":", zorder=2,
        )
        ax.plot([ensayo.s_m], [ensayo.cota_inicio_m], marker='o', markersize=4,
                markerfacecolor='white', markeredgecolor='#E45658', zorder=7)
        ax.text(ensayo.s_m, ensayo.cota_inicio_m + 0.8, ensayo.ensayo_id,
                ha="center", va="bottom", fontsize=proyecto.texto_ensayos_pt, color="#B6383B")
    ubicaciones={str(r.sondeo_id):(float(r.s_m),float(r.cota_boca_m)) for r in sondeos_proyectados.itertuples(index=False)}
    if spt is not None and len(spt) and proyecto.capas.get('spt',True):
        for r in spt.itertuples(index=False):
            if r.sondeo_id not in ubicaciones: continue
            x,z=ubicaciones[r.sondeo_id]; y=z-float(r.profundidad_m)
            ax.plot([x],[y],marker='_',color='#365E9C',markersize=8,zorder=7)
            ax.annotate('SPT '+str(r.secuencia),(x,y),xytext=(7,0),textcoords='offset points',
                        va='center',fontsize=proyecto.texto_ensayos_pt,color='#365E9C',zorder=9)
    if muestras is not None and len(muestras) and proyecto.capas.get('muestras',False):
        for r in muestras.itertuples(index=False):
            if r.reconocimiento not in ubicaciones: continue
            x,z=ubicaciones[r.reconocimiento]
            ax.annotate(str(r.tipo)+' '+str(r.unidad_geotecnica),(x,z-float(r.profundidad_m)),
                        xytext=(-5,0),textcoords='offset points',ha='right',va='center',
                        fontsize=proyecto.texto_ensayos_pt,color='#855F2E',zorder=9)
    if laboratorio is not None and len(laboratorio) and proyecto.capas.get('laboratorio',False):
        for r in laboratorio.itertuples(index=False):
            if r.tipo=='SPT' or r.reconocimiento not in ubicaciones: continue
            x,z=ubicaciones[r.reconocimiento]
            contenido=str(r.unidad_geotecnica)
            if r.uscs: contenido+=' | USCS '+str(r.uscs)
            if pd.notna(r.ip_pct): contenido+=f' | IP={float(r.ip_pct):g}%'
            if pd.notna(r.rcs_kpa): contenido+=f' | RCS={float(r.rcs_kpa):g} kPa'
            ax.annotate(contenido,(x,z-float(r.profundidad_m)),
                        xytext=(5,-12),textcoords='offset points',ha='left',va='center',
                        fontsize=proyecto.texto_ensayos_pt,color='#6A5B4B',zorder=9)
    fig.suptitle(proyecto.nombre, x=0.045, ha="left", fontsize=15, fontweight="bold", color="#0A2239")
    ax.set_xlabel("")
    ax.set_ylabel("Cota (m)")
    ax.grid(True, color="#DDE2E8", linewidth=0.5)
    ax.set_facecolor("#FAFBFC")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="lower left", ncol=3, fontsize=7, frameon=False)
    if rango_pk is None:
        x_min = float(sondeos_proyectados['s_m'].min())
        x_max = float(sondeos_proyectados['s_m'].max())
    else:
        x_min, x_max = map(float,rango_pk)
    y_min = min(float((sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()),
                float(terreno["cota_boca_m"].min()), fondo,
                float((dpsh_proyectados["cota_inicio_m"] - dpsh_proyectados["profundidad_m"]).min())
                    if not dpsh_proyectados.empty else fondo) - 0.6
    y_max = max(float(sondeos_proyectados["cota_boca_m"].max()),
                float(terreno["cota_boca_m"].max()),
                float(dpsh_proyectados["cota_inicio_m"].max()) if not dpsh_proyectados.empty else -np.inf) + 2.0
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    # Guitarra de perfil: PK, cota de terreno y reconocimientos en abscisas reales.
    guitarra = preparar_guitarra(sondeos_proyectados,dpsh_proyectados,(x_min,x_max),
                                 float(getattr(proyecto,'guitarra_paso_m',50.0)), terreno_puntos=terreno_puntos)
    ax_g.set_xlim(x_min,x_max)
    ax_g.set_ylim(0,4)
    ax_g.set_yticks([])
    ax_g.tick_params(axis='x', bottom=False,labelbottom=False)
    for y in (0,1,2,3,4) if proyecto.capas.get('guitarra',True) else []:
        ax_g.hlines(y,x_min,x_max,color='#8C9BA8',linewidth=.75)
    for m in guitarra['marcas'] if proyecto.capas.get('guitarra',True) else []:
        pk=m['pk_m']
        ax_g.vlines(pk,0,4,color='#CBD4DF',linewidth=.75)
        ax_g.text(pk,3.5,f'{pk:.1f}' if abs(pk-round(pk))>1e-4 else f'{pk:.0f}',ha='center',va='center',fontsize=8)
        cot=m['terreno_m']
        ax_g.text(pk,2.5,f'{cot:.2f}' if cot is not None else '—',ha='center',va='center',fontsize=8)
    for item in guitarra['reconocimientos'] if proyecto.capas.get('guitarra',True) else []:
        altura = 1.5 if item['tipo'] == 'Sondeo' else 0.5
        ax_g.text(item['pk_m'],altura,item['nombre'],ha='center',va='center',
                  fontsize=proyecto.texto_guitarra_pt,rotation=25,
                  color='#B6383B' if item['tipo']=='DPSH' else '#0A5E80')
    from matplotlib.transforms import blended_transform_factory
    left_axes=blended_transform_factory(ax_g.transAxes,ax_g.transData)
    for y,texto in ((3.5,'PK (m)'),(2.5,'Cota (m)'),(1.5,'Sondeos'),(.5,'Penetrómetros')) if proyecto.capas.get('guitarra',True) else []:
        ax_g.text(-.008,y,texto,transform=left_axes,ha='right',va='center',fontsize=8,clip_on=False)
    ax_g.set_xlabel('Distancia sobre el perfil / PK (m)',fontsize=9)
    ax.tick_params(axis='x', bottom=False, labelbottom=False)
    rango_x = max(np.diff(ax.get_xlim())[0], 1e-9)
    rango_y = max(np.diff(ax.get_ylim())[0], 1e-9)
    aspecto_caja = max(1e-4, rango_y * proyecto.exageracion_vertical / rango_x)
    # En perfiles muy cortos y profundos la exageracion fisica solicitada
    # produciria un lienzo de pocos milimetros de ancho en A3 horizontal.
    # Limitamos SOLO la composicion de la imagen, dejando intactas cotas/PK.
    aspecto_impreso = max(0.22, min(0.63, float(aspecto_caja)))
    if abs(aspecto_impreso-aspecto_caja)>1e-4:
        fig.text(.97,.94,'Vista ajustada para lectura · verificar escala fisica al imprimir',
                 ha='right',va='top',fontsize=8,color='#687487')
    ax.set_box_aspect(aspecto_impreso)
    # Tras fijar aspecto vertical, la guitarra debe ocupar exactamente el mismo ancho.
    fig.canvas.draw()
    superior = ax.get_position()
    inferior = ax_g.get_position()
    ax_g.set_position([superior.x0,inferior.y0,superior.width,inferior.height])
    salida = BytesIO()
    if formato not in ('pdf','png','svg'):
        raise ValueError('Formato de imagen no admitido.')
    parametros={'format':formato,'dpi':220}
    if formato=='pdf':
        parametros['metadata']={'Title':proyecto.nombre}
    fig.savefig(salida,**parametros)
    plt.close(fig)
    return salida.getvalue()


def figura_perfil_pdf(
    proyecto: Proyecto, sondeos_proyectados: pd.DataFrame, intervalos: pd.DataFrame,
    unidades: pd.DataFrame, contactos: list[Contacto], dpsh_proyectados: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame, escala_dpsh: float, zonas: list[dict] | None = None,
    rango_pk: tuple[float,float] | None = None,
    terreno_puntos: pd.DataFrame | None = None, spt: pd.DataFrame | None = None,
    muestras: pd.DataFrame | None = None, laboratorio: pd.DataFrame | None = None,
) -> bytes:
    return _figura_perfil_documento(proyecto,sondeos_proyectados,intervalos,unidades,
                                   contactos,dpsh_proyectados,lecturas_dpsh,escala_dpsh,
                                   zonas=zonas,rango_pk=rango_pk,formato='pdf',
                                   terreno_puntos=terreno_puntos,spt=spt,muestras=muestras,laboratorio=laboratorio)


def figura_perfil_imagen(
    proyecto: Proyecto, sondeos_proyectados: pd.DataFrame, intervalos: pd.DataFrame,
    unidades: pd.DataFrame, contactos: list[Contacto], dpsh_proyectados: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame, escala_dpsh: float, zonas: list[dict] | None = None,
    rango_pk: tuple[float,float] | None = None, formato: str = 'png',
    terreno_puntos: pd.DataFrame | None = None, spt: pd.DataFrame | None = None,
    muestras: pd.DataFrame | None = None, laboratorio: pd.DataFrame | None = None,
) -> bytes:
    if formato not in ('png','svg'):
        raise ValueError('La salida de imagen debe ser PNG o SVG.')
    return _figura_perfil_documento(proyecto,sondeos_proyectados,intervalos,unidades,
                                   contactos,dpsh_proyectados,lecturas_dpsh,escala_dpsh,
                                   zonas=zonas,rango_pk=rango_pk,formato=formato,
                                   terreno_puntos=terreno_puntos,spt=spt,muestras=muestras,laboratorio=laboratorio)

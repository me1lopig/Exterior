"""Entrada reducida de adherencias limite. Guia DGC 2005, 3.3.2.4."""
from math import isfinite
from calculos.axial import Estrato
from calculos.avanzado import validar_inyeccion
from modelos.espesores import intervalos_desde_espesores

FR_DURACION={1.45:6.,1.65:12.}  # representantes internos de las dos categorias

def numero_no_negativo(v, etiqueta):
    try:
        x=float(v)
    except (ValueError,TypeError):
        raise ValueError(etiqueta+' debe ser numerica.') from None
    if not isfinite(x) or x<0:
        raise ValueError(etiqueta+' debe ser finita y no negativa.')
    return x

def coeficiente_comun(filas):
    if not filas:
        raise ValueError('Introduzca al menos una unidad.')
    valores=[numero_no_negativo(f.get('fr'),'Fr') for f in filas]
    if any(x not in FR_DURACION for x in valores):
        raise ValueError('Fr debe ser 1,45 o 1,65 (tabla 3.2).')
    if len(set(valores))!=1:
        raise ValueError('Fr debe ser igual en todos los tramos del mismo micropilote: depende de la duracion, no del estrato.')
    return valores[0]

def necesita_iu(f, profundidad):
    return bool(f['activo'] and f['inyeccion']!='IU' and
                f['inicio_m']<min(5.,profundidad))

def preparar_estratos(filas, profundidad, iu_extra=None, presiones=None):
    """Construye Estrato con adherencias sin minorar; el motor divide por Fr una vez.
    iu_extra y presiones: mapas por indice de fila, no por nombre.
    presiones=None: aplicabilidad numerica no evaluada; requiere confirmacion externa en UI.
    """
    iu_extra={} if iu_extra is None else iu_extra
    profundidad=numero_no_negativo(profundidad,'Profundidad')
    filas=intervalos_desde_espesores(filas)
    fr=coeficiente_comun(filas)
    estratos=[]; detalle=[]
    for i,f in enumerate(filas):
        nombre=str(f.get('nombre','')).strip()
        if not nombre or nombre.lower() in ('nan','none','<na>'):
            raise ValueError(f'Fila {i+1}: indique la unidad.')
        tipo=f.get('inyeccion')
        activo=f.get('activo')
        if tipo not in ('IU','IR','IRS') or type(activo) is not bool:
            raise ValueError(f'Fila {i+1}: seleccione inyeccion y estado de fuste.')
        lim=numero_no_negativo(f.get('adlim_kPa'),f'Fila {i+1}: adherencia limite') if activo else 0.
        iu=lim if tipo=='IU' else 0.
        if necesita_iu(f,profundidad):
            iu=numero_no_negativo(iu_extra.get(i),f'Fila {i+1}: adherencia IU necesaria en primeros 5 m')
        pi=plim=None
        if activo and f['inicio_m']<profundidad and presiones is not None:
            try:
                pi,plim=presiones[i]
            except KeyError:
                raise ValueError(f'Fila {i+1}: faltan presiones para el control avanzado.') from None
            pi=numero_no_negativo(pi,'Presion de inyeccion')
            plim=numero_no_negativo(plim,'Presion limite')
            validar_inyeccion(tipo,pi,plim)
        estratos.append(Estrato(f['inicio_m'],f['fin_m'],iu,lim,activo))
        detalle.append({**f,'fr':fr,'adlim_kPa':lim,'admisible_kPa':lim/fr,
                        'iu_kPa':iu if tipo=='IU' or necesita_iu(f,profundidad) else None,
                        'pi_kPa':pi,'plim_kPa':plim})
    return estratos,detalle,fr

def resumen_aplicado(detalle,profundidad):
    """Vista de solo lectura: separa el tramo de calculo en z=5 m."""
    filas=[]
    for f in detalle:
        a,b=f['inicio_m'],min(f['fin_m'],profundidad)
        if b<=a: continue
        limites=[a]+([5.] if a<5.<b else [])+[b]
        for x,y in zip(limites,limites[1:]):
            tipo='IU' if x<5 else f['inyeccion']
            lim=(f['iu_kPa'] if x<5 else f['adlim_kPa']) if f['activo'] else 0.
            filas.append({'nombre':f['nombre'],'espesor_m':y-x,'inyeccion':tipo,
                          'adlim_kPa':lim,'fr':f['fr'],'admisible_kPa':lim/f['fr'],'activo':f['activo']})
    return filas

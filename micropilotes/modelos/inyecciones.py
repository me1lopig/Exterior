"""Entrada multiprocedimiento. MPa en interfaz; kPa en motor. No estima adherencias."""
from math import isfinite
from calculos.axial import Estrato
from calculos.avanzado import validar_inyeccion
from modelos.espesores import intervalos_desde_espesores
from modelos.adherencias import FR_DURACION, numero_no_negativo, coeficiente_comun

TIPOS=('IU','IR','IRS')
MODOS=('Mixto',)+TIPOS
COLS=['nombre','espesor_m','IU_MPa','IR_MPa','IRS_MPa','inyeccion','activo']
LEGACY={'nombre','espesor_m','inyeccion','adlim_kPa','fr','activo'}

def opcional(v):
    if v is None or (isinstance(v,str) and not v.strip()): return None
    try: n=float(v)
    except (ValueError,TypeError): raise ValueError('Adherencia no numérica.') from None
    if n!=n: return None  # celda vacía de pandas
    if not isfinite(n) or n<0: raise ValueError('Adherencia negativa o no finita.')
    return n

def migrar(filas,widgets=None):
    """No completa valores ausentes. Recupera IU adicional de JSON antiguo si existe."""
    widgets=widgets or {}
    filas=intervalos_desde_espesores(filas)
    salida=[]
    for i,f in enumerate(filas):
        tipo=f.get('inyeccion')
        if tipo not in TIPOS: raise ValueError('Seleccione IU, IR o IRS.')
        r={k:f.get(k) for k in COLS}
        for m in TIPOS:
            k=m+'_MPa'
            v=opcional(f.get(k))
            if v is None and m==tipo:
                raw=opcional(f.get('adlim_kPa'))
                if raw is None: raw=opcional(f.get('iu_kPa' if tipo=='IU' else 'seleccion_kPa'))
                if raw is not None: v=raw/1000
            if v is None and m=='IU':
                raw=opcional(f.get('iu_kPa'))
                if raw is None:
                    key=f"iu_{i}_{f['nombre']}_{tipo}_{f['inicio_m']}_{f['fin_m']}"
                    raw=opcional(widgets.get(key))
                if raw is not None: v=raw/1000
            r[k]=v
        if type(r['activo']) is not bool:
            raise ValueError('Fuste activo debe ser booleano.')
        salida.append(r)
    return salida

def preparar(filas,profundidad,fr,modo,presiones=None):
    """Presiones por (índice, procedimiento ejecutado). IU superficial es valor resistente,
    no implica que se ejecute una inyección IU diferente de la seleccionada.
    Solo exige adherencias de tramos activos efectivamente atravesados."""
    if modo not in MODOS or fr not in FR_DURACION:
        raise ValueError('Escenario o Fr no válido.')
    if not isfinite(profundidad) or profundidad<=0: raise ValueError('Profundidad inválida.')
    filas=intervalos_desde_espesores(filas)
    if profundidad>filas[-1]['fin_m']+1e-8: raise ValueError('La profundidad supera el perfil reconocido.')
    estratos=[]; detalle=[]
    for i,f in enumerate(filas):
        nombre=str(f.get('nombre','')).strip()
        if not nombre or nombre.lower() in ('nan','none','<na>'): raise ValueError(f'Fila {i+1}: indique la unidad.')
        mixto=f.get('inyeccion'); activo=f.get('activo')
        if mixto not in TIPOS or type(activo) is not bool: raise ValueError(f'Fila {i+1}: revise inyección y fuste activo.')
        tipo=mixto if modo=='Mixto' else modo
        valores={m:opcional(f.get(m+'_MPa')) for m in TIPOS}
        a=f['inicio_m']; b=min(f['fin_m'],profundidad)
        iu=valores['IU']; sel=valores[tipo]
        if activo and b>a:
            if a<5 and iu is None: raise ValueError(f'Fila {i+1}: falta IU para el tramo superficial.')
            if b>5 and sel is None: raise ValueError(f'Fila {i+1}: falta adherencia {tipo}.')
        pi=plim=None
        if activo and b>a and presiones is not None:
            try: pi,plim=presiones[i,tipo]
            except KeyError: raise ValueError(f'Fila {i+1}: faltan presiones {tipo}.') from None
            pi=numero_no_negativo(pi,'Presión de inyección')
            plim=numero_no_negativo(plim,'Presión límite')
            validar_inyeccion(tipo,pi,plim)
        # Ceros internos únicamente para partes inactivas o no utilizadas; datos ausentes
        # permanecen None en la entrada y nunca se presentan como adherencia medida.
        iu_k=0. if not activo else (iu or 0.)*1000
        sel_k=0. if not activo else (sel or 0.)*1000
        estratos.append(Estrato(a,f['fin_m'],iu_k,sel_k,activo))
        detalle.append({**f,'inyeccion_mixta':mixto,'inyeccion':tipo,'fr':fr,
            'adlim_kPa':(sel*1000 if sel is not None else None) if activo else 0.,
            'admisible_kPa':(sel*1000/fr if sel is not None else None) if activo else 0.,
            'iu_kPa':(iu*1000 if iu is not None else None) if activo else 0.,
            'pi_kPa':pi,'plim_kPa':plim})
    return estratos,detalle

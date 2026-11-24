"""Presentacion de resultados geotecnicos, sin alterar el motor resistente."""
from math import cos, radians, isfinite

def tabla_calculada(filas, resumen, angulo):
    """Proyecta el resumen aplicado a cotas verticales y longitud axial.
    filas: intervalos originales preparados y contiguos desde z=0.
    resumen: salida de resumen_aplicado, ordenada desde z=0 y recortada.
    """
    if not isfinite(angulo) or not 0 <= angulo < 90:
        raise ValueError('Inclinacion invalida.')
    c=cos(radians(angulo))
    z=0.
    j=0
    salida=[]
    for t in resumen:
        h=t['espesor_m']
        if not isfinite(h) or h<=0:
            raise ValueError('Espesor efectivo invalido.')
        while j<len(filas) and z>=filas[j]['fin_m']-1e-9:
            j+=1
        if j==len(filas) or z+h>filas[j]['fin_m']+1e-8:
            raise ValueError('Intervalos de presentacion inconsistentes.')
        f=filas[j]
        nota='IU por limite de 5 m' if f['activo'] and f['inyeccion']!='IU' and t['inyeccion']=='IU' else ''
        salida.append(dict(nombre=t['nombre'],inicio_m=z,fin_efectivo_m=z+h,
                           longitud_axial_m=h/c,admisible_kPa=t['admisible_kPa'],
                           criterio=nota))
        z+=h
    return salida

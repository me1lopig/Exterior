"""Tablas DGC 2005, 2.1, 2.3, 2.4, 3.4-3.7. No extrapolar tablas."""
from math import isfinite
VIDAS=(5,25,50,75,100)
CORROSION={
    'Suelo natural sin alterar':(0,.30,.60,.90,1.20),
    'Suelo contaminado o industrial':(.15,.75,1.50,2.25,3.00),
    'Suelo natural agresivo':(.20,1.,1.75,2.50,3.25),
    'Relleno no agresivo sin compactar':(.18,.70,1.20,1.70,2.20),
    'Relleno agresivo sin compactar':(.50,2.,3.25,4.50,5.75),
}
RECUBRIMIENTO={'Lechada':{'Compresion':20.,'Traccion':25.},
               'Mortero':{'Compresion':30.,'Traccion':35.}}
# Extremo superior conservador por defecto, no interpolacion inferida.
COACCION={'Sin reduccion de pandeo (justificada)':(0.,0.),
          'Fangos/turbas, su 15–25 kPa':(12.,18.),
          'Arcillas/limos blandos, su 15–25 kPa':(8.,12.),
          'Granular medio, 0.35<Id<0.65 y sobre NF o Cu>=2':(7.,8.),
          'Cohesivo medio, su 25–50 kPa':(7.,8.),
          'Zona libre o terreno inestable':None}

def perdida(terreno,vida):
    if terreno not in CORROSION or vida not in VIDAS:
        raise ValueError('Categoria o vida util no tabulada.')
    return CORROSION[terreno][VIDAS.index(vida)]

def cr_libre(h_m,dr_mm):
    if not all(isfinite(v) for v in (h_m,dr_mm)) or not (h_m>0 and dr_mm>0):
        raise ValueError('Zona libre: H y DR deben ser positivos.')
    return h_m*1000/dr_mm

def recubrimiento(dp,de,material,modo,empalme=None):
    """Chequeo nominal. Empalme desconocido no implica conformidad."""
    r=RECUBRIMIENTO[material][modo]
    if not all(isfinite(v) and v>0 for v in (dp,de)):
        raise ValueError('Diametros invalidos.')
    if empalme is not None and (not isfinite(empalme) or empalme<=0):
        raise ValueError('Diametro de empalme invalido.')
    holgura=(dp-de)/2
    holgura_union=None if empalme is None else (dp-empalme)/2
    return dict(r_min_mm=r,holgura_mm=holgura,holgura_union_mm=holgura_union,
                cuerpo_compatible=holgura>=r,
                union_compatible=None if holgura_union is None else holgura_union>=r)

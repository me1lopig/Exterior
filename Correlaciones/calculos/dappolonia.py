"""Modulo de compresibilidad M segun el metodo de D'Appolonia (1970).

La correlacion se usa con N bruto MEDIO desde la base de cimentacion
hasta una profundidad B adicional. NO se emplean N60 ni (N1)60.
M es parametro del metodo de asiento s = q B mu0 mu1 / M; no se
presenta como modulo de Young E ni modulo edometrico universal.

Referencia reproducible de ecuaciones: Paikowsky (U. Massachusetts Lowell),
Foundation Settlement Analysis Methods (cap. 2, ecs. 2.43-2.44).
Ver asimismo FHWA-HRT-15-080, seccion D'Appolonia.
"""
from __future__ import annotations
from calculos.spt import positivo
from calculos.granulares import registro
from modelos.esquemas import ResultadoCorrelacion

# 1 short ton-force / square foot = 95.7605179607 kPa
TSF_A_MPA = 0.0957605179607
REFERENCIA = (
    'D\'Appolonia, D\'Appolonia y Brissette (1970), cierre del articulo de 1968, '
    'recogido por Paikowsky, Foundation Settlement Analysis Methods, ecs. 2.43-2.44 '
    '(https://faculty.uml.edu/spaikowsky/14.533%20Adv%20Found%20Eng/Documents/Chapter2Version1.1_updated%205-29-2007.pdf); '
    'FHWA-HRT-15-080 (https://www.fhwa.dot.gov/publications/research/infrastructure/structures/bridge/15080/004.cfm)'
)
ESTADOS = ('No definido', 'Normalmente cargada', 'Precargada / OC')
MATERIALES = ('Arena limpia NC', 'Arena limpia OC', 'Grava/arena gravosa')


def calcular_m_dappolonia(n_medio_bruto: float, b_zapata_m: float,
                         estado: str, familia: str) -> list[ResultadoCorrelacion]:
    """Dos ramas, con valor solo para la clase historica indicada.

    Rechaza datos matematicamente invalidos y marca como no aplicable
    la condicion geotecnica inadecuada. El limite N<=60 es operativo.
    """
    n = positivo('N medio bruto', n_medio_bruto, permitir_cero=True)
    b = positivo('Ancho B de zapata', b_zapata_m)
    if estado not in ESTADOS:
        raise ValueError('Estado de carga no reconocido para D\'Appolonia')
    if familia not in ('Arena con finos', *MATERIALES):
        raise ValueError('Material no reconocido para D\'Appolonia')
    limpio = familia in MATERIALES
    coherente = ((familia == 'Arena limpia NC' and estado != 'Precargada / OC') or
                 (familia == 'Arena limpia OC' and estado != 'Normalmente cargada') or
                 familia == 'Grava/arena gravosa')
    filas = []
    for etiqueta, a, pendiente, esperado in (
        ('Normalmente cargada', 196., 7.9, 'Normalmente cargada'),
        ('Precargada / OC', 416., 10.9, 'Precargada / OC'),
    ):
        apto = limpio and coherente and estado == esperado and 0 < n <= 60
        m_tsf = a + pendiente * n
        filas.append(registro(
            f'D\'Appolonia et al. (1970) - M {etiqueta}',
            'Modulo M de compresibilidad para metodo de asentamientos (NO modulo de Young)',
            rf'M=({a:g}+{pendiente:g}\,\bar N_{{bruto}})\,0.09576051796',
            m_tsf*TSF_A_MPA if apto else None, 'MPa',
            'N bruto medio en espesor B bajo zapata [-], B [m], estado de carga',
            REFERENCIA,
            'N bruto MEDIO, sin correccion de energia ni confinamiento, tomado entre la '
            'base de la zapata y B metros por debajo; seleccionar NC o precargada; '
            '0<N<=60 es limite operativo, no dominio publicado.',
            apto=apto, secundaria=True,
            nota=('El valor corresponde al modulo M usado en s=q B mu0 mu1/M; '
                  'no debe interpretarse directamente como E. '
                  f'B definido por el usuario: {b:g} m.')))
    return filas

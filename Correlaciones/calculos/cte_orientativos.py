"""Intervalos ORIENTATIVOS CTE DB SE-C, no valores de proyecto."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite

CTE = 'CTE DB SE-C, edicion 20/12/2019 (https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf)'

@dataclass(frozen=True)
class Intervalo:
    fuente: str
    clasificacion: str
    minimo: float | None
    maximo: float | None
    unidad: str
    nota: str

    def fila(self):
        return {
            'Fuente': self.fuente, 'Clasificacion': self.clasificacion,
            'Minimo': self.minimo, 'Maximo': self.maximo,
            'Unidad': self.unidad, 'Nota': self.nota,
        }

CONSISTENCIA_CU = {
    'Muy blanda': (0,25), 'Blanda':(25,50),'Media':(50,100),
    'Firme':(100,200),'Muy firme':(200,400),'Dura':(400,None),
}
PHI_D27 = {'Grava': (34,45), 'Arena':(30,36), 'Limo':(25,32), 'Arcilla':(16,28)}


def cu_por_consistencia(consistencia: str) -> Intervalo:
    if consistencia not in CONSISTENCIA_CU:
        raise ValueError('Consistencia no reconocida')
    q0,q1=CONSISTENCIA_CU[consistencia]
    return Intervalo('CTE tabla D.3 (qu) -> cu = qu/2',consistencia,
        q0/2.,None if q1 is None else q1/2.,'kPa',
        'Conversion condicionada a arcilla saturada y compresion simple no drenada con phi_u=0; CTE tabula qu, no cu.')


def cu_por_nspt_cte(n: float) -> Intervalo:
    n=float(n)
    if not isfinite(n) or n < 0:
        raise ValueError('NSPT debe ser finito y no negativo')
    if n < 10: et='NSPT < 10'; q0,q1=0.,80.
    elif n <=25: et='10 <= NSPT <= 25'; q0,q1=80.,150.
    elif n <=50: et='25 < NSPT <= 50'; q0,q1=150.,300.
    else: et='50 < NSPT hasta rechazo'; q0,q1=300.,500.
    return Intervalo('CTE tabla D.23 (qu) -> cu = qu/2', et, q0/2,q1/2,'kPa',
        'Tabla D.23 mixta: no calibrada especificamente para cu de arcillas. Conversion solo si material/cohesion y ensayo cumplen qu=2cu.')


def phi_por_tipo_cte(tipo:str) -> Intervalo:
    if tipo not in PHI_D27:
        raise ValueError('Tipo de suelo no presente en D.27')
    a,b=PHI_D27[tipo]
    return Intervalo('CTE DB SE-C tabla D.27',tipo,float(a),float(b),'grados',
        'Intervalo orientativo de angulo de rozamiento interno por clasificacion; no es una correlacion SPT.')


def eu_desde_gmax(ip_pct: float, gmax_mpa: float):
    """CTE F.1: Eu = fp Gmax, para arcillas OC, ensayos cross-hole/down-hole."""
    from modelos.esquemas import EstadoRevision, ResultadoCorrelacion
    ip=float(ip_pct); gmax=float(gmax_mpa)
    if not isfinite(ip) or ip < 0 or not isfinite(gmax) or gmax <= 0:
        raise ValueError('IP>=0 y Gmax>0, ambos finitos')
    if 15 < ip < 30: f=1.2
    elif 30 < ip < 50: f=1.6
    elif ip > 50: f=1.9
    else: f=None
    return ResultadoCorrelacion(
        autor='CTE DB SE-C, tabla F.1', aplicacion='Arcilla sobreconsolidada; Gmax de cross-hole/down-hole',
        formula=r'E_u=f_P G_{max}',valor=f*gmax if f is not None else None,
        unidad='MPa',parametros='IP [%]; Gmax [MPa] medido; arcilla OC',
        aplicable=f is not None, estado=EstadoRevision.VERIFICADA_CTE,
        criterio=f'fP={f:g}' if f is not None else 'IP fuera de columna definida (incluye limites 15,30,50)',
        nota='Modulo sin drenaje segun tabla F.1; no es aplicable a arcillas normalmente consolidadas.',
        referencia=f'{CTE}, tabla F.1')

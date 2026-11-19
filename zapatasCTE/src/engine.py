"""Motor geotecnico independiente para ZapatasCTE 4.2 (reconstruccion funcional).

Aproximacion para predimensionamiento: cargas verticales centradas, asiento inmediato
Steinbrenner por capas, hundimiento CTE DB-SE-C 4.8 y Anejo F, balasto Anejo E.5.
No constituye una verificacion profesional completa de cimentaciones.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import atan, atan2, asinh, exp, hypot, isfinite, pi, radians, sin, sqrt, tan
from typing import Optional
import numpy as np
import pandas as pd
from .balasto_cte import calcular_detalle_balasto

GAMMA_AGUA = 9.81
VERSION = '4.2.0-reconstruida'


def numero(x, nombre: str, *, minval=None, maxval=None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float, np.number)) or not isfinite(float(x)):
        raise ValueError(f'{nombre} debe ser un numero finito.')
    y = float(x)
    if minval is not None and y < minval:
        raise ValueError(f'{nombre} no puede ser inferior a {minval}.')
    if maxval is not None and y > maxval:
        raise ValueError(f'{nombre} no puede superar {maxval}.')
    return y


@dataclass(frozen=True)
class Estrato:
    nombre: str
    z0: float
    z1: float
    E_mpa: float
    nu: float

    def validar(self):
        numero(self.z0, 'z0', minval=0)
        numero(self.z1, 'z1', minval=0)
        numero(self.E_mpa, 'E', minval=1e-9)
        numero(self.nu, 'nu', minval=0, maxval=0.499999)
        if self.z1 <= self.z0:
            raise ValueError(f'{self.nombre}: el fondo de la capa debe superar su techo.')


@dataclass(frozen=True)
class Parametros:
    D_m: float = 0.5
    nf_m: float = 6.6
    gamma_ap_kn_m3: float = 18
    gamma_sub_kn_m3: float = 9
    drenaje: str = 'Drenada'
    phi_deg: float = 30
    cohesion_kpa: float = 0
    gamma_R: float = 3
    incluir_q0: bool = True
    gamma_q0_kn_m3: float = 18
    altura_q0_m: float = 0.5
    factor_profundidad: bool = False
    beta_deg: float = 0
    flujo_ascendente: bool = False
    gradiente: float = 0
    cu_gradiente: bool = False
    cu_z0_m: float = 0
    cu0_kpa: float = 50
    cu_z1_m: float = 10
    cu1_kpa: float = 150
    asiento_adm_cm: float = 5
    metodo_asiento: str = 'superposicion'
    tipo_balasto: str = 'Cohesivo'
    criterio_balasto: str = 'literal_cte'
    descarga_manual_kpa: Optional[float] = None

    def validar(self):
        for name in ('D_m','nf_m','gamma_ap_kn_m3','gamma_sub_kn_m3','gamma_R',
                     'gamma_q0_kn_m3','altura_q0_m','cohesion_kpa','gradiente',
                     'cu_z0_m','cu_z1_m','cu0_kpa','cu1_kpa','asiento_adm_cm'):
            numero(getattr(self, name), name, minval=0)
        numero(self.phi_deg, 'phi', minval=0, maxval=89)
        numero(self.beta_deg, 'beta', minval=0, maxval=89)
        if self.gamma_R <= 0 or self.asiento_adm_cm <= 0 or self.gamma_ap_kn_m3 <= 0 or self.gamma_sub_kn_m3 <= 0:
            raise ValueError('Peso especifico, gammaR y asiento admisible deben ser positivos.')
        if self.gamma_sub_kn_m3 > self.gamma_ap_kn_m3 + 5:
            raise ValueError("Compruebe gamma sumergido: demasiado alto respecto a gamma aparente.")
        if self.drenaje not in ('Drenada','No drenada'):
            raise ValueError('Condicion drenada/no drenada desconocida.')
        if self.drenaje == 'No drenada' and self.phi_deg != 0:
            raise ValueError('En condicion no drenada se debe introducir phi=0.')
        if self.metodo_asiento not in ('superposicion','excel'):
            raise ValueError('Metodo de asiento desconocido.')
        if self.tipo_balasto not in ('Cohesivo','Granular'):
            raise ValueError('Seleccionar Cohesivo o Granular.')
        if self.criterio_balasto not in ('literal_cte','continuo'):
            raise ValueError('Criterio de balasto desconocido.')
        if self.factor_profundidad and (self.D_m < 2 or self.beta_deg > 0):
            raise ValueError('Factores de profundidad: exigen D>=2 m y ausencia de talud.')
        if self.flujo_ascendente and self.gamma_sub_kn_m3 - 9.81*self.gradiente <= 0:
            raise ValueError('El peso efectivo corregido por flujo debe ser positivo.')
        if self.cu_gradiente and (self.cu_z1_m <= self.cu_z0_m or self.cu1_kpa < self.cu0_kpa):
            raise ValueError('El perfil cu(z) requiere z1>z0 y cu1>=cu0.')
        if self.descarga_manual_kpa is not None:
            numero(self.descarga_manual_kpa, 'descarga manual', minval=0)


def validar_estratos(capas: tuple[Estrato,...]):
    if not capas:
        raise ValueError('Defina al menos un estrato elastico.')
    for c in capas:
        c.validar()
    orden = sorted(capas, key=lambda c: c.z0)
    if abs(orden[0].z0) > 1e-8:
        raise ValueError('El perfil comienza en z=0 bajo la base de la cimentacion.')
    for c1,c2 in zip(orden, orden[1:]):
        if abs(c2.z0 - c1.z1) > 1e-7:
            raise ValueError('Estratos con huecos o solapes: las capas deben ser contiguas.')
    return tuple(orden)


def dimensiones(bmin,bmax,db,lmin,lmax,dl):
    vs=[numero(v,k,minval=0.000001) for v,k in zip((bmin,bmax,db,lmin,lmax,dl),('Bmin','Bmax','dB','Lmin','Lmax','dL'))]
    b0,b1,db,l0,l1,dl=vs
    if b1<b0 or l1<l0:
        raise ValueError('Rango maximo inferior al minimo.')
    ns=(int((b1-b0)/db+1e-8)+1,int((l1-l0)/dl+1e-8)+1)
    if max(ns)>300 or ns[0]*ns[1]>20000:
        raise ValueError('Malla demasiado grande: reduzca los rangos o aumente incrementos.')
    return [(round(b0+i*db,9),round(l0+j*dl,9)) for i in range(ns[0]) for j in range(ns[1])
            if b0+i*db <= l0+j*dl+1e-8]


def tension_preexistente_kpa(z_rasante: float, p: Parametros, efectiva=False):
    z=max(z_rasante,0)
    seco=min(z,p.nf_m)
    saturado=max(0,z-p.nf_m)
    return seco*p.gamma_ap_kn_m3 + saturado*(p.gamma_sub_kn_m3 if efectiva else p.gamma_sub_kn_m3+GAMMA_AGUA)


def descarga_pre_kpa(p: Parametros):
    return p.descarga_manual_kpa if p.descarga_manual_kpa is not None else tension_preexistente_kpa(p.D_m,p,False)


def factores_capacidad(phi_deg):
    phi=radians(phi_deg)
    nq=tan(pi/4+phi/2)**2*exp(pi*tan(phi))
    nc=pi+2 if abs(phi_deg)<1e-12 else (nq-1)/tan(phi)
    ng=1.5*(nq-1)*tan(phi)
    return nc,nq,ng


def calculo_hundimiento(b: float,l: float,p: Parametros) -> dict:
    """Resistencia de calculo bruta para carga vertical centrada, MPa."""
    p.validar()
    if not (0<b<=l):
        raise ValueError('La zapata debe cumplir 0<B<=L.')
    sin_drenaje=p.drenaje=='No drenada'
    phi=0 if sin_drenaje else p.phi_deg
    nc,nq,ng=factores_capacidad(phi)
    if sin_drenaje:
        nc,nq,ng=5.14,1.,0.
    ang=radians(phi)
    frac=b/l
    sc=1+0.2*frac
    sq=1+1.5*tan(ang)*frac
    sg=1-0.3*frac
    dc=dq=1.
    if p.factor_profundidad:
        dc=1+0.34*atan(p.D_m/b)
        dq=1 if phi<1e-9 else 1+2*nq/nc*(1-sin(ang))**2*atan(min(p.D_m,2*b)/b)
    q0=p.gamma_q0_kn_m3*p.altura_q0_m if p.incluir_q0 else 0.
    if p.cu_gradiente and sin_drenaje:
        grad=(p.cu1_kpa-p.cu0_kpa)/(p.cu_z1_m-p.cu_z0_m)
        c=grad*(p.D_m+b/4-p.cu_z0_m)+p.cu0_kpa
        c0=p.cu0_kpa-grad*p.cu_z0_m
        if c0<=0:
            raise ValueError('cu extrapolado a superficie no positivo.')
        c=min(c,2*c0)
    else:
        c=p.cohesion_kpa
    fraccion=max(0,min(p.nf_m-p.D_m,b))/b
    gamma=p.gamma_sub_kn_m3+fraccion*(p.gamma_ap_kn_m3-p.gamma_sub_kn_m3)
    if p.flujo_ascendente:
        gamma=p.gamma_sub_kn_m3-9.81*p.gradiente
    beta=radians(p.beta_deg)
    if sin_drenaje:
        tc=tq=tg=1.
    else:
        tc=exp(-2*beta*tan(ang))
        tq=tg=1-sin(2*beta)
    qh=c*nc*dc*sc*tc+q0*nq*dq*sq*tq+0.5*b*gamma*ng*sg*tg
    if sin_drenaje and beta>0:
        qh-=2*beta*c
    return {'qh_bruta_mpa':qh/(p.gamma_R*1000),'q0_kpa':q0,'sc':sc,'sq':sq,'sgamma':sg,
            'dc':dc,'dq':dq,'Nc':nc,'Nq':nq,'Ngamma':ng,'c_representativa_kpa':c,
            'gamma_representativa_kn_m3':gamma}


def esquina_m(q_mpa: float,b: float,l: float,z: float,c: Estrato):
    m=z/b
    n=l/b
    tau=hypot(hypot(1.,n),m)
    f1=(2*asinh(n/sqrt(1+m*m))+2*n*asinh(1/hypot(n,m)))/pi
    f2=0 if z==0 else m/pi*atan2(n,tau*m)
    return q_mpa*b/(2*c.E_mpa)*((1-c.nu*c.nu)*f1-(1-c.nu-2*c.nu*c.nu)*f2)


def contribuciones_asiento(b,l,capas,metodo,q_mpa):
    if metodo=='superposicion':
        mult,x,y=4,b/2,l/2
    elif metodo=='excel':
        mult,x,y=2,b,l
    else:
        raise ValueError('Metodo desconocido.')
    rows=[];ac=0.
    for c in capas:
        s=1000*mult*(esquina_m(q_mpa,x,y,c.z0,c)-esquina_m(q_mpa,x,y,c.z1,c))
        if not isfinite(s):
            raise ValueError('Asiento no finito.')
        ac+=s
        rows.append({'Unidad':c.nombre,'z sup. (m)':c.z0,'z inf. (m)':c.z1,'E (MPa)':c.E_mpa,
                     'nu':c.nu,'Asiento (mm)':s,'Asiento acumulado (mm)':ac})
    for r in rows:
        r['Contribucion (%)']=100*r['Asiento (mm)']/ac if ac>0 else 0
    return rows


def calcular_geometria(b: float,l: float,p: Parametros,capas: tuple[Estrato,...]):
    capas=validar_estratos(capas)
    h=calculo_hundimiento(b,l,p)
    desglose=contribuciones_asiento(b,l,capas,p.metodo_asiento,1.)
    flex_mm=desglose[-1]['Asiento acumulado (mm)']
    if not isfinite(flex_mm) or flex_mm<=0:
        raise ValueError('La flexibilidad de asientos debe ser positiva.')
    qa=p.asiento_adm_cm*10/flex_mm
    sigma=descarga_pre_kpa(p)/1000
    qh_net=h['qh_bruta_mpa']-sigma
    qs_net=min(qh_net,qa) if qh_net>0 else None
    lim=('Asientos' if qa<qh_net else 'Hundimiento') if qs_net is not None else 'No valido'
    ks=1000/flex_mm  # MPa / mm -> MN/m3 (q=1 MPa, s=mm/1000)
    det=calcular_detalle_balasto(ks,b,l,p.tipo_balasto,criterio=p.criterio_balasto)
    avisos=[]
    fondo=capas[-1].z1
    if fondo<2*b:
        avisos.append('Profundidad modelada inferior a 2B; estudiar posible influencia de capas profundas.')
    if len(capas)>1:
        avisos.append('Ksp30 de perfil estratificado es equivalencia teorica, NO ensayo de placa.')
    if qs_net is None:
        avisos.append('Margen neto de hundimiento no positivo: geometria no valida para servicio.')
    return dict(B_m=b,L_m=l,area_m2=b*l,relacion_l_b=l/b,
       q_hund_bruta_mpa=h['qh_bruta_mpa'],q_hund_neta_mpa=qh_net,
       q_asiento_neta_mpa=qa,q_asiento_bruta_mpa=qa+sigma,
       q_serv_neta_mpa=qs_net,q_serv_bruta_mpa=qs_net+sigma if qs_net is not None else None,
       q0_kpa=h['q0_kpa'],sigma_pre_base_kpa=sigma*1000,
       ks_bl_mn_m3=ks,ks_b_equiv_mn_m3=det.ks_b_mn_m3,ksp30_mn_m3=det.ksp30_mn_m3,
       factor_forma_balasto=det.factor_forma,factor_escala_balasto=det.factor_escala,
       criterio_balasto=det.criterio,tipo_balasto=det.material,referencia_balasto=det.ecuaciones,
       limitacion=lim,sc=h['sc'],sq=h['sq'],sgamma=h['sgamma'],
       profundidad_estudiada_m=fondo,avisos=tuple(avisos)+det.advertencias,
       flexibilidad_mm_mpa=flex_mm)



def calcular_corrida_historica(b: float, p: Parametros, capas: tuple[Estrato,...]):
    """Comparativa de zapata corrida historica, NO una zapata finita real.

    Conserva la convencion documentada de la hoja SUELOS:
    longitud equivalente asientos = 100 m; hundimiento = 1000 m.
    """
    r=calcular_geometria(b,100.,p,capas)
    hund=calculo_hundimiento(b,1000.,p)
    qh=hund['qh_bruta_mpa']
    sigma=r['sigma_pre_base_kpa']/1000
    qh_neta=qh-sigma
    valido=qh_neta>0
    qa=r['q_asiento_neta_mpa']
    neto=min(qa,qh_neta) if valido else None
    salida=dict(r)
    salida.update(q_hund_bruta_mpa=qh,q_hund_neta_mpa=qh_neta,
        q_serv_neta_mpa=neto,q_serv_bruta_mpa=neto+sigma if valido else None,
        limitacion=('Asientos' if qa<qh_neta else 'Hundimiento') if valido else 'No valido',
        sc=hund['sc'],sq=hund['sq'],sgamma=hund['sgamma'])
    salida['avisos']=tuple(r['avisos'])+('Corrida aproximada: L_asientos=100m y L_hundimiento=1000m.',)
    return salida


def ejecutar_malla(geometrias, p: Parametros, capas):
    p.validar();capas=validar_estratos(tuple(capas))
    if not geometrias:
        raise ValueError('Ninguna geometria cumple B<=L.')
    if len(geometrias)>20000:
        raise ValueError('Demasiadas geometrías.')
    return [calcular_geometria(b,l,p,capas) for b,l in geometrias]


MAPA = {
 'Presión admisible de servicio (neta)': 'q_serv_neta_mpa',
 'Presión admisible de servicio (bruta)': 'q_serv_bruta_mpa',
 'Presión admisible por hundimiento (neta)': 'q_hund_neta_mpa',
 'Presión admisible por hundimiento (bruta)': 'q_hund_bruta_mpa',
 'Presión admisible por asientos (neta)': 'q_asiento_neta_mpa',
 'Presión admisible por asientos (bruta)': 'q_asiento_bruta_mpa',
 'Coeficiente de balasto ks,BL': 'ks_bl_mn_m3',
 'Balasto equivalente Ksp30': 'ksp30_mn_m3',
 'Estado límite gobernante': 'limitacion',
}

COLUMNAS = {
 'B_m':'B (m)','L_m':'L (m)','area_m2':'Area (m2)','relacion_l_b':'L/B',
 'q0_kpa':'q0 contorno (kPa)','sigma_pre_base_kpa':'sigma pre-excavacion (kPa)',
 'q_hund_bruta_mpa':'q hund. bruta (MPa)','q_hund_neta_mpa':'q hund. neta (MPa)',
 'q_asiento_neta_mpa':'q asientos neta (MPa)','q_asiento_bruta_mpa':'q asientos bruta (MPa)',
 'q_serv_neta_mpa':'q servicio neta (MPa)','q_serv_bruta_mpa':'q servicio bruta (MPa)',
 'ks_bl_mn_m3':'ks,BL (MN/m3)','ksp30_mn_m3':'Ksp30 (MN/m3)','limitacion':'Limitacion',
 'tipo_balasto':'Tipo de suelo','criterio_balasto':'Criterio conversion',
 'sc':'sc','sq':'sq','sgamma':'sgamma','profundidad_estudiada_m':'Fin perfil (m)',
 'factor_forma_balasto':'Factor forma balasto','factor_escala_balasto':'Factor escala balasto',
 'referencia_balasto':'Referencia balasto','avisos':'Avisos',
}


def tabla_resultados(rows):
    df=pd.DataFrame(rows)
    return df.rename(columns=COLUMNAS)


def factor_boussinesq_centro(b,l,z):
    if z<0 or b<=0 or l<b:
        raise ValueError('Geometria o profundidad invalida.')
    if z==0:
        return 1.0
    a,c=b/2,l/2
    r=hypot(hypot(a,c),z)
    return max(0.,min(1.,2/pi*(atan2(a*c,z*r)+a*c*z/r*(1/(a*a+z*z)+1/(c*c+z*z)))))


def bulbo_tensiones(b,l,p,capas,q_neta_mpa,paso=0.1,zmax=None):
    max_cap=max(c.z1 for c in capas)
    prof=max_cap if zmax is None else zmax
    numero(prof,'profundidad',minval=0.1)
    numero(paso,'paso',minval=0.001)
    z=np.linspace(0,prof,min(1501,max(2,int(prof/paso)+1)))
    ds=np.asarray([1000*q_neta_mpa*factor_boussinesq_centro(b,l,float(zi)) for zi in z])
    eff=np.asarray([tension_preexistente_kpa(p.D_m+float(zi),p,efectiva=True) for zi in z])
    umbral=np.minimum(.10*1000*q_neta_mpa,.05*eff)
    indices=np.where(ds<=umbral)[0]
    profundidad=float(z[indices[0]]) if len(indices) else None
    return pd.DataFrame({'z bajo base (m)':z,'Delta sigma vertical (kPa)':ds,
                         'sigma efectiva inicial (kPa)':eff,'umbral CTE (kPa)':umbral}),profundidad

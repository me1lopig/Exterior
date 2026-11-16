"""Motor de cálculo independiente de Streamlit.

PilotesCTE v3.0 · CTE DB-SE-C, 20-12-2019 (edición PDF oficial consultada).
El resultado es una estimación analítica preliminar; no sustituye el proyecto.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional

GAMMA_W = 9.81  # kN/m³
NORMA = "CTE DB-SE-C, 20-12-2019; 2.1, 5.2.2, 5.3.4.1, F.2.1"
CLASES_RN = {"Arcilla/limo blando": 0.25, "Arena floja": 0.10, "Arena densa": 0.80}


class ErrorDatos(ValueError):
    """Dato no válido o hipótesis fuera de alcance."""


@dataclass(frozen=True)
class Estrato:
    nombre: str
    espesor: float
    gamma_seco: float
    gamma_sat: float
    tipo: str  # Fino / Granular
    condicion: str  # Corto Plazo / Largo Plazo (modelo vigente, NO ambos escenarios)
    cu: float
    phi: float
    clase_rn: str = "No definida"


@dataclass(frozen=True)
class Geometria:
    tipo: str = "Circular macizo"  # Circular macizo / Tubular acero / Perfil H acero
    diametro: float = 0.6  # exterior, para macizo/tubular
    espesor_pared: float = 0.02  # tubular
    ancho_ala: float = 0.3  # perfil H
    canto: float = 0.3
    espesor_ala: float = 0.018
    espesor_alma: float = 0.012


@dataclass(frozen=True)
class Seccion:
    area_punta: float
    area_estructural: float
    perimetro_fuste: float
    d_equivalente: float
    descripcion: str


@dataclass(frozen=True)
class Configuracion:
    ejecucion: str = "Perforados"  # Perforados / Hincados
    material: str = "Hormigón armado"
    gamma_r: float = 3.0
    sigma_tope_mpa: float = 5.0
    nivel_freatico: Optional[float] = 3.0
    fuste_nulo: float = 1.5
    rozamiento_negativo: bool = False
    rn_desde: float = 0.0
    rn_hasta: float = 0.0
    factor_rn: float = 1.0  # Factor de la acción seleccionado por el usuario (NO gamma_R)


@dataclass
class Resultado:
    diametro: float
    longitud: float
    seccion: Seccion
    q_p_sin_limite: float
    q_p: float
    q_limite_511: Optional[float]
    r_pk: float
    r_fk: float
    r_ck: float
    r_cd: float
    r_estructural: float
    rn_k: float
    rn_d: float
    r_cabeza_orientativa: float
    control: str
    detalles_punta: list[dict] = field(default_factory=list)
    detalles_fuste: list[dict] = field(default_factory=list)
    detalles_rn: list[dict] = field(default_factory=list)
    observaciones: list[str] = field(default_factory=list)


def _finito(valor: float, nombre: str) -> float:
    try:
        x = float(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorDatos(f"{nombre}: debe ser un número.") from exc
    if not math.isfinite(x):
        raise ErrorDatos(f"{nombre}: no se admiten NaN ni infinitos.")
    return x


def comprobar_estratos(estratos: list[Estrato]) -> float:
    if not estratos:
        raise ErrorDatos("Debe definirse al menos un estrato.")
    if len(estratos) > 100:
        raise ErrorDatos("El perfil admite un máximo de 100 estratos.")
    nombres = set()
    total = 0.0
    for i, e in enumerate(estratos, start=1):
        pref = f"Estrato {i} ({e.nombre or 'sin nombre'})"
        if not str(e.nombre).strip():
            raise ErrorDatos(f"{pref}: el identificador es obligatorio.")
        if e.nombre in nombres:
            raise ErrorDatos(f"{pref}: el identificador de estrato está duplicado.")
        nombres.add(e.nombre)
        for name, value in (("espesor", e.espesor), ("γ seco", e.gamma_seco),
                            ("γ saturado", e.gamma_sat), ("cu", e.cu), ("φ", e.phi)):
            _finito(value, f"{pref}, {name}")
        if e.espesor <= 0 or e.espesor > 10000:
            raise ErrorDatos(f"{pref}: el espesor debe estar en (0, 10000] m.")
        if e.gamma_seco <= 0 or e.gamma_sat <= GAMMA_W:
            raise ErrorDatos(f"{pref}: se requiere γ seco > 0 y γ saturado > 9,81 kN/m³.")
        if e.gamma_seco > 1000 or e.gamma_sat > 1000:
            raise ErrorDatos(f"{pref}: pesos específicos fuera del rango físico admitido (≤1000 kN/m³).")
        if e.gamma_sat < e.gamma_seco:
            raise ErrorDatos(f"{pref}: γ saturado no puede ser inferior a γ seco.")
        if e.cu < 0 or e.cu > 1e6 or not (0 <= e.phi < 89):
            raise ErrorDatos(f"{pref}: se exige 0 ≤ cu ≤ 10⁶ kPa y 0° ≤ φ < 89°.")
        if e.tipo not in ("Fino", "Granular"):
            raise ErrorDatos(f"{pref}: tipo de suelo inválido; roca no implementada.")
        if e.condicion not in ("Corto Plazo", "Largo Plazo"):
            raise ErrorDatos(f"{pref}: condición de cálculo no reconocida.")
        if e.tipo == "Granular" and e.condicion != "Largo Plazo":
            raise ErrorDatos(f"{pref}: el modelo granular F.30/F.31 se calcula en condición drenada.")
        if e.tipo == "Fino" and e.cu <= 0:
            raise ErrorDatos(f"{pref}: indique cu > 0 para F.32/5.11, también si se analiza a largo plazo.")
        if e.condicion == "Largo Plazo" and e.phi <= 0:
            raise ErrorDatos(f"{pref}: se necesita φ > 0° para F.30/F.31 drenadas.")
        if e.clase_rn not in ("No definida", *CLASES_RN):
            raise ErrorDatos(f"{pref}: clase de rozamiento negativo no reconocida.")
        if e.tipo == "Fino" and e.clase_rn in ("Arena floja", "Arena densa"):
            raise ErrorDatos(f"{pref}: clase β de arena incompatible con suelo fino.")
        if e.tipo == "Granular" and e.clase_rn == "Arcilla/limo blando":
            raise ErrorDatos(f"{pref}: clase β de fino incompatible con suelo granular.")
        total += e.espesor
    if not math.isfinite(total):
        raise ErrorDatos("La profundidad total no es finita.")
    return total


def comprobar_nf(zw: Optional[float], profundidad: float) -> None:
    if zw is None:
        return
    zw = _finito(zw, "Profundidad del nivel freático")
    if zw < 0 or zw > profundidad + 1e-9:
        raise ErrorDatos(
            f"Nivel freático a {zw:g} m fuera del terreno reconocido (0–{profundidad:g} m). "
            "Corrija la profundidad o seleccione 'Sin nivel freático'."
        )


def crear_seccion(geo: Geometria) -> Seccion:
    if geo.tipo == "Circular macizo":
        d = _finito(geo.diametro, "Diámetro")
        if d <= 0 or d > 100:
            raise ErrorDatos("El diámetro debe estar en (0, 100] m.")
        a = math.pi * d*d/4
        return Seccion(a, a, math.pi*d, d, f"Circular macizo D={d:.3f} m")
    if geo.tipo == "Tubular acero":
        d = _finito(geo.diametro, "Diámetro exterior")
        t = _finito(geo.espesor_pared, "Espesor del tubo")
        if d <= 0 or d > 100 or t <= 0 or 2*t >= d:
            raise ErrorDatos("Tubular: 0 < 2·t < D ≤ 100 m.")
        a_ext = math.pi*d*d/4
        a_steel = math.pi*(d*d-(d-2*t)**2)/4
        # CTE 5.3.4.1.2.3: para pilotes huecos HINCADOS, área total del contorno externo.
        return Seccion(a_ext, a_steel, math.pi*d, d,
                       f"Tubular hincado D={d:.3f} m, t={t:.3f} m (punta: área exterior; fuste: exterior)")
    if geo.tipo == "Perfil H acero":
        b = _finito(geo.ancho_ala, "Ancho de ala")
        h = _finito(geo.canto, "Canto")
        tf = _finito(geo.espesor_ala, "Espesor de ala")
        tw = _finito(geo.espesor_alma, "Espesor de alma")
        if min(b,h,tf,tw) <= 0 or max(b,h,tf,tw)>100 or 2*tf >= h or tw >= b:
            raise ErrorDatos("Perfil H: 0 < b,h,tf,tw ≤100 m, 2tf < h y tw < b.")
        a_steel = 2*b*tf + (h-2*tf)*tw
        # CTE 5.3.4.1.2.2: menor área del rectángulo circunscrito o 1.5 b².
        a_punta = min(b*h, 1.5*b*b)
        # CTE 5.1.2.2.2: perímetro recomendado 2(b+h).
        p = 2*(b+h)
        d_eq = math.sqrt(4*a_punta/math.pi)
        return Seccion(a_punta,a_steel,p,d_eq,
                       f"Perfil H b={b:.3f}, h={h:.3f}, tf={tf:.3f}, tw={tw:.3f} m")
    raise ErrorDatos("Geometría desconocida.")


def seleccionar_gamma(estratos: list[Estrato], situacion: str,
                      manual: Optional[float] = None, justificacion: str = "") -> tuple[float, str]:
    """Tabla 2.1: 3.0 a largo plazo, posibilidad de 2.0 analítico corto, 2.0 extraordinaria."""
    comprobar_estratos(estratos)
    if situacion not in ("Persistente/transitoria", "Extraordinaria"):
        raise ErrorDatos("Situación de dimensionado desconocida.")
    if situacion == "Extraordinaria":
        base, motivo = 2.0, "Tabla 2.1: hundimiento, situación extraordinaria (método analítico)"
    elif all(e.condicion == "Corto Plazo" for e in estratos):
        base, motivo = 2.0, "Tabla 2.1, nota (1): posibilidad de γR=2,0 para fórmulas analíticas a corto plazo"
    else:
        base, motivo = 3.0, "Tabla 2.1: γR=3,0 para métodos analíticos a largo plazo o perfil mixto"
    if manual is None:
        return base, motivo
    r = _finito(manual, "γR manual")
    if r < 1:
        raise ErrorDatos("γR manual debe ser ≥ 1,0.")
    if not justificacion.strip() or len(justificacion.strip()) < 12:
        raise ErrorDatos("Justifique el cambio de γR (mínimo 12 caracteres).")
    return r, f"Valor manual γR={r:g}. Valor de referencia: {base:g}. Justificación: {justificacion.strip()}"


def comprobar_config(cfg: Configuracion, estratos: list[Estrato], geom: Seccion, L: float) -> None:
    zmax = comprobar_estratos(estratos)
    comprobar_nf(cfg.nivel_freatico,zmax)
    if cfg.ejecucion not in ("Perforados", "Hincados"):
        raise ErrorDatos("Método de ejecución desconocido.")
    if geom.area_punta <= 0 or geom.perimetro_fuste <= 0 or geom.area_estructural <= 0:
        raise ErrorDatos("Área/perímetro geométrico no válido.")
    if cfg.material == "Metálicos" and cfg.ejecucion != "Hincados":
        raise ErrorDatos("La geometría metálica se admite aquí para pilotes hincados.")
    for name,val in (("γR",cfg.gamma_r),("σ tope",cfg.sigma_tope_mpa),
                     ("fuste nulo",cfg.fuste_nulo),("longitud",L),("factor de acción RN",cfg.factor_rn)):
        _finito(val,name)
    if (not 1 <= cfg.gamma_r <= 1e6 or not 0 < cfg.sigma_tope_mpa <= 1e6
            or cfg.fuste_nulo < 0 or L<=0 or not 0 < cfg.factor_rn <= 1e6):
        raise ErrorDatos("γR≥1, tope>0, L>0, fuste nulo≥0 y factor RN>0 obligatorios; se rechazan magnitudes extremas.")
    if L > zmax+1e-9:
        raise ErrorDatos(f"L={L:.2f} m excede el perfil conocido ({zmax:.2f} m).")
    if L+3*geom.d_equivalente > zmax+1e-9:
        raise ErrorDatos(f"Bulbo L+3D={L+3*geom.d_equivalente:.2f} m supera el sondeo ({zmax:.2f} m).")
    if cfg.rozamiento_negativo:
        a = _finito(cfg.rn_desde,"RN desde")
        b = _finito(cfg.rn_hasta,"RN hasta")
        if not (0 <= a < b <= zmax):
            raise ErrorDatos("RN: rango de profundidades debe cumplir 0≤desde<hasta≤fondo sondeo.")
        if a >= L:
            raise ErrorDatos("RN: el tramo definido debe interceptar el fuste del pilote.")
        z=0.0
        for e in estratos:
            if max(a,z) < min(b,L,z+e.espesor)-1e-10 and e.clase_rn == "No definida":
                raise ErrorDatos(f"RN: debe definir la clase β del estrato {e.nombre} dentro del tramo.")
            z += e.espesor


def capas_con_cotas(estratos: list[Estrato]):
    z=0.0
    for e in estratos:
        yield z,z+e.espesor,e
        z += e.espesor


def estrato_en(z: float, estratos: list[Estrato]) -> Estrato:
    # Punta exactamente en límite: estrato inferior; no extrapolar bajo fondo.
    max_z=sum(e.espesor for e in estratos)
    if not (0 <= z <= max_z+1e-9):
        raise ErrorDatos(f"Profundidad {z:.3f} m fuera del reconocimiento.")
    for top,bottom,e in capas_con_cotas(estratos):
        if z < bottom-1e-9 or abs(z-top)<1e-9:
            return e
    return estratos[-1]


def tensiones(z: float, estratos: list[Estrato], zw: Optional[float]) -> tuple[float,float,float]:
    zmax = sum(e.espesor for e in estratos)
    if not math.isfinite(z) or z < -1e-9 or z > zmax+1e-9:
        raise ErrorDatos(f"Tensiones: z={z:g} m fuera del sondeo (0–{zmax:g} m).")
    comprobar_nf(zw,zmax)
    z = max(0.0,min(z,zmax))
    sv=0.0
    for top,bottom,e in capas_con_cotas(estratos):
        a=top
        b=min(z,bottom)
        if b<=a:
            break
        if zw is None:
            sv+=e.gamma_seco*(b-a)
        else:
            dry=max(0.0,min(b,zw)-a)
            sat=(b-a)-dry
            sv+=e.gamma_seco*dry+e.gamma_sat*sat
    u=0.0 if zw is None else max(0.0,z-zw)*GAMMA_W
    return sv,u,sv-u


def perfil_tensiones(estratos: list[Estrato], zw: Optional[float], paso: float=0.2):
    zmax=comprobar_estratos(estratos)
    comprobar_nf(zw,zmax)
    pasos=max(1,math.ceil(zmax/paso))
    puntos={zmax*i/pasos for i in range(pasos+1)}
    for a,b,_ in capas_con_cotas(estratos):
        puntos.add(a); puntos.add(b)
    if zw is not None:
        puntos.add(zw)
    zs=sorted(puntos)
    valores=[tensiones(z,estratos,zw) for z in zs]
    return zs,[r[0] for r in valores],[r[1] for r in valores],[r[2] for r in valores]


def _superposicion(a:float,b:float,c:float,d:float)->float:
    return max(0.0,min(b,d)-max(a,c))


def _nq(phi: float) -> float:
    p=math.radians(phi)
    return ((1+math.sin(p))/(1-math.sin(p)))*math.exp(math.pi*math.tan(p))


def punta(estratos: list[Estrato], seccion:Seccion, L:float, cfg:Configuracion):
    """Devuelve qp inicial, qp final, tope 5.11 y detalle/auditoría.

    Criterio explícito en perfiles mixtos: rama de estrato en punta y tope conservador
    por el otro material dentro del entorno. No se proclama fórmula normativa exacta
    para transiciones de material: queda avisado para revisión geotécnica.
    """
    D=seccion.d_equivalente
    tip=estrato_en(L,estratos)
    sv,u,sve=tensiones(L,estratos,cfg.nivel_freatico)
    detalle=[]; avisos=[]
    if tip.tipo=="Fino" and tip.condicion=="Corto Plazo":
        a=max(0,L-2*D); b=L+2*D
        aporte=0.0; h_fina=0.0; otros=[]
        for top,bot,e in capas_con_cotas(estratos):
            h=_superposicion(a,b,top,bot)
            if h<=0: continue
            if e.tipo=="Fino" and e.condicion=="Corto Plazo":
                aporte+=h*e.cu; h_fina+=h
                detalle.append({"Estrato":e.nombre,"Entorno":"2D/2D","Peso (m)":h,
                                "Parámetro":"cu","Valor":e.cu})
            else:
                otros.append(e)
                detalle.append({"Estrato":e.nombre,"Entorno":"2D/2D","Peso (m)":h,
                                "Parámetro":"φ (mezcla)","Valor":e.phi})
        if h_fina<=0:
            raise ErrorDatos("Falta cu evaluable en el entorno 2D/2D.")
        cu_eq=aporte/h_fina
        qp=9*cu_eq
        detalle.append({"Estrato":"Equivalente","Entorno":"F.32","Peso (m)":h_fina,
                        "Parámetro":"cu equivalente","Valor":cu_eq})
        if otros:
            q_dren=min(min(cfg_to_fp(cfg)*max(0,sve)*_nq(e.phi),20000) for e in otros)
            qp=min(qp,q_dren)
            avisos.append("Transición de suelo en 2D/2D: tope conservador por unidad distinta; revisar modelo de heterogeneidad.")
    else:
        a=max(0,L-6*D);b=L+3*D
        suma_phi=0.0; h_dren=0.0; capas_cortas=[]
        for top,bot,e in capas_con_cotas(estratos):
            h=_superposicion(a,b,top,bot)
            if h<=0: continue
            if e.condicion=="Largo Plazo":
                suma_phi+=e.phi*h;h_dren+=h
                detalle.append({"Estrato":e.nombre,"Entorno":"6D/3D","Peso (m)":h,
                                "Parámetro":"φ","Valor":e.phi})
            else:
                capas_cortas.append(e)
                detalle.append({"Estrato":e.nombre,"Entorno":"6D/3D","Peso (m)":h,
                                "Parámetro":"cu (mezcla)","Valor":e.cu})
        if h_dren<=0:
            raise ErrorDatos("No hay ángulo de rozamiento en 6D/3D para la punta drenada.")
        phi_eq=suma_phi/h_dren
        qp=min(cfg_to_fp(cfg)*max(0.0,sve)*_nq(phi_eq),20000.0)
        detalle.append({"Estrato":"Equivalente","Entorno":"F.30","Peso (m)":h_dren,
                        "Parámetro":"φ equivalente","Valor":phi_eq})
        if capas_cortas:
            qp=min(qp,min(9*e.cu for e in capas_cortas))
            avisos.append("Transición de suelo en 6D/3D: resistencia acotada por unidad fina no drenada; criterio conservador no explicitado por el CTE.")
    qp_sin=qp
    limites=[]
    # 5.11 se aplica a niveles finos por DEBAJO de punta (no al mismo estrato portante).
    for top,bot,e in capas_con_cotas(estratos):
        if e.tipo=="Fino" and top>=L-1e-9:
            h=max(0.0,top-L)
            limite=6*(1+h/D)**2*e.cu
            limites.append((limite,e.nombre,h,e.cu))
    q_lim=min([c[0] for c in limites], default=None)
    if q_lim is not None:
        qp=min(qp,q_lim)
        for lim,name,h,cu in limites:
            detalle.append({"Estrato":name,"Entorno":"5.11 inferior","Peso (m)":h,
                            "Parámetro":"qp límite (kPa)","Valor":lim})
        if qp < qp_sin-1e-8:
            avisos.append("Aplicada la limitación de punta por capa cohesiva blanda inferior, CTE 5.11.")
    return qp_sin,max(0.0,qp),q_lim,detalle,avisos


def cfg_to_fp(cfg:Configuracion)->float:
    return 3.0 if cfg.ejecucion=="Hincados" else 2.5


def _area_tau_drenada(z0,z1,sigma0,sigma1,k,cap):
    """Integral exacta de min(k*sigma(z), cap) para sigma lineal en un tramo."""
    t0=max(0.,sigma0*k);t1=max(0.,sigma1*k)
    h=z1-z0
    if max(t0,t1)<=cap:
        return (t0+t1)*h/2
    if min(t0,t1)>=cap:
        return cap*h
    r=(cap-t0)/(t1-t0)
    if t0 < cap:
        return h*(r*(t0+cap)/2 + (1-r)*cap)
    return h*(r*cap + (1-r)*(cap+t1)/2)


def fuste_y_negativo(estratos:list[Estrato],sec:Seccion,L:float,cfg:Configuracion):
    zmax=sum(e.espesor for e in estratos)
    cortes={0.0,L,min(L,cfg.fuste_nulo)}
    for top,bottom,_ in capas_con_cotas(estratos):
        for z in (top,bottom):
            if 0 < z < L: cortes.add(z)
    if cfg.nivel_freatico is not None and 0 < cfg.nivel_freatico < L:
        cortes.add(cfg.nivel_freatico)
    if cfg.rozamiento_negativo:
        for z in (cfg.rn_desde,cfg.rn_hasta):
            if 0<z<L: cortes.add(z)
    zs=sorted(cortes)
    kf=1.0 if cfg.ejecucion=="Hincados" else 0.75
    if cfg.material=="Metálicos": f=0.8
    elif cfg.ejecucion=="Hincados" and cfg.material.startswith("Hormigón"): f=0.9
    else: f=1.0
    rf=rn=0.0; det_f=[];det_n=[]
    for a,b in zip(zs[:-1],zs[1:]):
        if b-a < 1e-10:continue
        e=estrato_en((a+b)/2,estratos)
        _,_,sv0=tensiones(a,estratos,cfg.nivel_freatico)
        _,_,sv1=tensiones(b,estratos,cfg.nivel_freatico)
        negativa=cfg.rozamiento_negativo and cfg.rn_desde <= (a+b)/2 < cfg.rn_hasta
        if negativa:
            beta=CLASES_RN[e.clase_rn]
            tau=beta*(sv0+sv1)/2
            fuerza=tau*sec.perimetro_fuste*(b-a)
            rn+=fuerza
            det_n.append({"Estrato":e.nombre,"Desde (m)":a,"Hasta (m)":b,
                          "β":beta,"σ' media (kPa)":(sv0+sv1)/2,
                          "τneg (kPa)":tau,"Fneg (kN)":fuerza})
            # Jamás contar este tramo también como fuste resistente.
            continue
        if a < cfg.fuste_nulo-1e-9: continue
        if e.tipo=="Fino" and e.condicion=="Corto Plazo":
            tau=100*e.cu/(100+e.cu)
            if cfg.material=="Metálicos":tau*=0.8
            area_tau=tau*(b-a)
            cap=100.0
        else:
            cap=100.0 if e.tipo=="Fino" else 120.0
            k=kf*f*math.tan(math.radians(e.phi))
            area_tau=_area_tau_drenada(a,b,sv0,sv1,k,cap)
            tau=area_tau/(b-a)
        fuerza=area_tau*sec.perimetro_fuste
        rf+=fuerza
        det_f.append({"Estrato":e.nombre,"Desde (m)":a,"Hasta (m)":b,
                      "τ media (kPa)":tau,"Tope (kPa)":cap,"Rf (kN)":fuerza})
    return rf,rn,det_f,det_n


def calcular_pilote(estratos:list[Estrato],geom:Geometria,L:float,cfg:Configuracion)->Resultado:
    sec=crear_seccion(geom)
    comprobar_config(cfg,estratos,sec,L)
    q_base,q,limit,dp,notas=punta(estratos,sec,L,cfg)
    rf,rn,df,dn=fuste_y_negativo(estratos,sec,L,cfg)
    rp=q*sec.area_punta
    rc=rp+rf
    rd=rc/cfg.gamma_r
    re=sec.area_estructural*cfg.sigma_tope_mpa*1000
    rnd=rn*cfg.factor_rn
    rd_neto=max(0.0,rd-rnd)
    # Estimación conservadora de capacidad de cabeza; no equivale a comprobación ELU completa.
    r_cabeza=min(rd_neto,max(0.0,re-rnd))
    control="Geotécnico" if rd_neto<=max(0.0,re-rnd) else "Tope simplificado"
    if cfg.rozamiento_negativo:
        notas.append("RN: valor de acción Fneg,d añadido a la demanda; margen de carga de cabeza ORIENTATIVO, sin verificación Ed≤Rd.")
    if geom.tipo=="Perfil H acero":
        notas.append("Geometría H: área de punta=min(bh,1,5b²) y perímetro=2(b+h) según DB-SE-C.")
    return Resultado(sec.d_equivalente,L,sec,q_base,q,limit,rp,rf,rc,rd,re,
                     rn,rnd,r_cabeza,control,dp,df,dn,notas)


def matriz_calculo(estratos:list[Estrato], cfg:Configuracion,
                   geometrias:list[Geometria], longitudes:list[float]):
    """Resultados y errores por (D_equiv, L); combinaciones no calculables quedan N/D."""
    resultados=[]; errores=[]
    comprobar_estratos(estratos)
    for geo in geometrias:
        sec=crear_seccion(geo)
        for l in longitudes:
            try:
                r=calcular_pilote(estratos,geo,float(l),cfg)
                resultados.append(r)
            except ErrorDatos as exc:
                errores.append({"D_eq (m)":sec.d_equivalente,"L (m)":float(l),"Causa":str(exc)})
    return resultados,errores

"""Correlaciones documentadas para phi' y modulo E de suelos granulares.

No confundir N de campo, N60 y (N1)60. El modulo es secante aproximado,
no un parametro medido. Referencias en cada ficha.
"""
from __future__ import annotations
import math
from modelos.esquemas import EstadoRevision, ResultadoCorrelacion
from calculos.spt import SalidaSPT, positivo

FHWA_GEC5 = 'FHWA Geotechnical Site Characterization, NHI-16-072, sec. 7.6.9 (https://www.fhwa.dot.gov/engineering/geotech/pubs/nhi16072.pdf)'
FHWA_GEC12 = 'FHWA Driven Pile Foundations, NHI-16-009 vol. 1, ec. 5-14/5-15 (https://www.fhwa.dot.gov/engineering/geotech/pubs/gec12/nhi16009_v1.pdf)'
FHWA_PAV = 'FHWA Geotechnical Aspects of Pavements, cap. 4, Kulhawy y Mayne (1990) (https://www.fhwa.dot.gov/engineering/geotech/pubs/05037/04b.cfm)'
HATANAKA = 'Hatanaka y Uchida (1996), Soils and Foundations 36(4), pp. 1-9 (https://doi.org/10.3208/sandf.36.4_1); adaptacion FHWA para (N1)60'
BEGEMANN = 'Begemann (1974), reproducido en anejo geotecnico publico de Euskadi (https://www.euskadi.eus/contenidos/informacion/subestacion_elec_gernika/es_def/adjuntos/TTE-IS-24001-PWS-SBS-ANX-0005.pdf); pendiente localizar original'
BOWLES = 'Bowles (1988), recopilacion tecnica en estudio Settlements of shallow foundations on granular soil, tabla 4.2 (https://paperzz.com/doc/6951188/settlement-of-shallow-foundations-on-granular-soils); conv. N historico no confirmado'
WOLFF = 'Peck-Hanson-Thornburn (1974), ajuste de Wolff (1989); https://groundhog.readthedocs.io/en/main/site_investigation/spt_correlations.html'
SHIOI = 'Shioi y Fukui (1982), Application of N-value to design of foundations in Japan, ESOPT II, pp. 159-164; variantes reproducidas en ZSoil, The Hardening Soil Model, tabla 3.10 (https://www.zsoil.com/zsoil_manual/Rep-HS-model.pdf)'


def registro(autor: str, aplicacion: str, formula: str, valor: float | None, unidad: str,
             parametros: str, referencia: str, condiciones: str, *, apto: bool = True, nota: str = '', secundaria: bool = False) -> ResultadoCorrelacion:
    if valor is not None and (not math.isfinite(valor) or valor < 0):
        raise ValueError(f"Resultado no fisico: {autor}")
    return ResultadoCorrelacion(autor=autor, aplicacion=aplicacion, formula=formula,
        valor=valor if apto else None, unidad=unidad, parametros=parametros,
        aplicable=apto, estado=EstadoRevision.SECUNDARIA if secundaria else EstadoRevision.VERIFICADA_BIBLIOGRAFIA,
        criterio=condiciones, nota=nota, referencia=referencia)


def calcular_phi_verificado(spt: SalidaSPT, sigma_v_ef_kpa: float | None,
                             tipo_suelo: str) -> list[ResultadoCorrelacion]:
    """Cuatro relaciones: dos FHWA, ajuste Wolff y dos variantes Shioi-Fukui.

    El N70 de Shioi se obtiene solo de N60, SIN correction de confinamiento.
    """
    n60 = positivo('N60', spt.n60, permitir_cero=True)
    arena_h = tipo_suelo == 'Arena limpia fina/media'
    arena_k = tipo_suelo in ('Arena limpia fina/media', 'Arena limpia gruesa')
    filas = []
    n1 = spt.n1_60
    apta_h = arena_h and n1 is not None and 3.5 <= n1 <= 30.
    filas.append(registro('Hatanaka y Uchida (1996), adaptacion FHWA',
        'Arenas limpias; angulo de rozamiento pico',
        r"\phi'=20+\sqrt{15.4\,(N_1)_{60}}", (20+math.sqrt(15.4*n1)) if apta_h else None,
        'grados', '(N1)60 normalizado [-]', HATANAKA,
        '3.5 <= (N1)60 <= 30; arena limpia fina/media; N normalizado a 60% energia', apto=apta_h,
        nota='La fuente original usaba N1 con eficiencia de martillo distinta; se usa la adaptacion explicita FHWA.'))
    apta_k = arena_k and sigma_v_ef_kpa is not None and sigma_v_ef_kpa > 0 and n60 > 0
    # FHWA ec. 5-14: phi' = arctan([N60/(12.2+20.3*sigma_v/pa)]**0.34) en grados
    ang = math.degrees(math.atan((n60/(12.2+20.3*sigma_v_ef_kpa/100.))**0.34)) if apta_k else None
    filas.append(registro('Schmertmann (1975) / Kulhawy y Mayne (1990), FHWA',
        'Arenas limpias; aproximacion tensodependiente',
        r"\phi'=\arctan\!\left(\left[\frac{N_{60}}{12.2+20.3(\sigma'_{v0}/p_a)}\right]^{0.34}\right)",
        ang, 'grados', 'N60 [-], sigma_v0 efectiva [kPa], pa=100 kPa', FHWA_GEC12,
        'Arena limpia, tension efectiva positiva, N60 > 0; aplicacion orientativa', apto=apta_k,
        nota='La potencia 0.34 se aplica al cociente antes del arctan; salida en grados.'))
    # Wolff-Peck: la documentacion Groundhog usa (N1)60 con rango sugerido 0-60.
    apta_w = arena_k and n1 is not None and 0 <= n1 <= 60
    filas.append(registro('Peck et al. (1974) / ajuste Wolff (1989)',
        'Arenas limpias; angulo de rozamiento efectivo estimado con SPT normalizado',
        r"\phi'=27.1+0.3\,(N_1)_{60}-0.00054\,[(N_1)_{60}]^2",
        (27.1+0.3*n1-0.00054*n1*n1) if apta_w else None,
        'grados', '(N1)60 [-] corregido por energia y confinamiento', WOLFF,
        '0 <= (N1)60 <= 60; rango recomendado por Groundhog, suelo granular arenoso',
        apto=apta_w,
        nota='Ajuste de Wolff a correlacion grafica de Peck-Hanson-Thornburn; no usar N60 en su lugar.'))
    # Shioi-Fukui se publico para N70. Solo se transforma energia desde N60.
    n70 = n60 * 60.0/70.0
    apta_s_b = tipo_suelo in ('Arena limpia fina/media','Arena limpia gruesa','Arena con finos') and 0 < n70 <= 50
    apta_s_r = tipo_suelo in ('Arena limpia fina/media','Arena limpia gruesa','Arena con finos','Grava/arena gravosa') and 0 < n70 <= 60
    filas.append(registro('Shioi y Fukui (1982) - carreteras/puentes',
        'Material granular; variante japonesa de puentes y carreteras',
        r"\phi'=15+\sqrt{18\,N_{70}}",
        (15+math.sqrt(18*n70)) if apta_s_b else None,
        'grados', 'N70 = N60 x (60/70); SIN confinamiento', SHIOI,
        '0<N70<=50: limite operativo conservador (equivale a phi<=45); '
        'solamente arenas y arenas con finos',apto=apta_s_b, secundaria=True,
        nota='N70 se corrige por energia 70%; no utilizar (N1)60. '
             'Formula contrastada en manual especializado ZSoil, no en texto completo original.'))
    filas.append(registro('Shioi y Fukui (1982) - ferrocarriles',
        'Material granular; variante japonesa ferroviaria',
        r"\phi'=27+0.36\,N_{70}",
        (27+0.36*n70) if apta_s_r else None,
        'grados', 'N70 = N60 x (60/70); SIN confinamiento', SHIOI,
        '0<N70<=60: limite operativo conservador, no limite bibliografico; granular',
        apto=apta_s_r, secundaria=True,
        nota='Otras recopilaciones ofrecen pendientes diferentes; se implementa la '
             'variante 0.36/N70 de ZSoil y se identifica su origen.'))
    return filas


def calcular_e_arenas_verificado(spt: SalidaSPT, familia: str, *, n_begemann: float | None = None) -> list[ResultadoCorrelacion]:
    """Tres relaciones FHWA para N60 y dos ramas de Begemann para N de campo.

    Begemann utiliza N del estudio historico, no se etiqueta N60 sin evidencia.
    """
    n60 = positivo('N60', spt.n60, permitir_cero=True)
    if n_begemann is None:
        n_begemann = spt.n_campo
    nb = positivo('N para Begemann', n_begemann, permitir_cero=True)
    familia_datos = (
        ('Arena con finos',5.,'Arenas con finos'),
        ('Arena limpia NC',10.,'Arenas limpias normalmente consolidadas'),
        ('Arena limpia OC',15.,'Arenas limpias sobreconsolidadas'),
    )
    res=[]
    for etiqueta, coef, descripcion in familia_datos:
        activo = familia == etiqueta and 0 < n60 <= 60
        res.append(registro('Kulhawy y Mayne (1990), FHWA', descripcion,
            rf"E=p_a\,{coef:g}\,N_{{60}}/1000", coef*n60*100/1000 if activo else None,
            'MPa','N60 [-], pa=100 kPa', FHWA_PAV,
            f'Familia {etiqueta}; 0<N60<=60 como limite operativo conservador (no limite normativo)', apto=activo,
            nota='E/pa aproximado, alta dispersion; pa=100 kPa se usa como referencia tecnica.'))
    beg_fam = familia in ('Grava/arena gravosa', 'Arena limpia NC','Arena limpia OC')
    for tramo, valido, kgcm in (
        ('N < 15', nb<15, 12*(nb+6)),
        ('N > 15', nb>15, 40+12*(nb-6)),
    ):
        apto = beg_fam and valido and 0 < nb <= 50
        res.append(registro('Begemann (1974), recopilacion tecnica',f'Arenas y gravas, tramo {tramo}',
            r'E=12\,(N+6)\,0.0980665' if tramo == 'N < 15' else r'E=[40+12\,(N-6)]\,0.0980665',
            kgcm*0.0980665 if apto else None,'MPa','N de campo [-] (segun recopilacion), kgf/cm2 a MPa',BEGEMANN,
            f'{tramo}; suelo granular; 0<N<=50 (restriccion operativa); N=15 indefinido en las dos ramas publicadas',apto=apto,
            nota='Los dos tramos son discontinuos: no interpolar ni suavizar. Fuente tecnica secundaria revisada, no original.',secundaria=True))
    return res

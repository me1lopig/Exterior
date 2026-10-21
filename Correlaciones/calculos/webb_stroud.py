"""Webb (correlaciones E-N) y Stroud-Butler (m_v, M) con trazabilidad.

No confundir el modulo estimado mediante ensayo de placa con un modulo de Young
universal, ni m_v con modulo de Young. Fuentes, unidad y limites visibles.
"""
from __future__ import annotations

import math
from modelos.esquemas import EstadoRevision, ResultadoCorrelacion

WEBB_REVISION = (
    'Webb, D. L. (1970), Settlement of Structures on Deep Alluvial Sandy Sediments in '
    'Durban, South Africa, pp. 181-188 (registro de publicacion: '
    'https://trid.trb.org/View/125002). Ecuaciones y unidades kPa reproducidas '
    'en Wagh y Bambole (2024), tabla de correlaciones 5a-5c '
    '(https://doi.org/10.1515/eng-2024-0046). Fuente original integra '
    'no contrastada para coeficientes exactos.'
)
STROUD_ORIGINAL = (
    'Stroud, M. A. y Butler, F. G. (1975), The Standard Penetration Test and '
    'the Engineering Properties of Glacial Materials, pp. 124-135, '
    'figuras 4-5 y tabla 4. Reproduccion del trabajo original: '
    'https://www.geosolve.co.uk/refs/Stroud%2BButler_1975.pdf'
)

WEBB_MATERIALES = (
    'Arena saturada',
    'Arena arcillosa',
    'Perfil arenoso medio/heterogeneo',
)
STROUD_MATERIALES = (
    'Arcilla glacial / till',
    'Arcilla glacial laminada',
    'Otro material (fuera del alcance)',
)


def _numero(nombre: str, x: float, positivo: bool = False) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{nombre}: indique un numero valido.') from exc
    if not math.isfinite(x) or (x <= 0 if positivo else x < 0):
        raise ValueError(f'{nombre}: debe ser finito y ' + ('mayor que cero.' if positivo else 'no negativo.'))
    return x


def _fila(autor: str, aplicacion: str, formula: str, valor: float | None,
          unidad: str, parametros: str, valido: bool, criterio: str,
          nota: str, referencia: str, *, secundaria: bool = False) -> ResultadoCorrelacion:
    if valor is not None and (not math.isfinite(valor) or valor < 0):
        raise ValueError('Valor calculado no fisico para el metodo especificado.')
    return ResultadoCorrelacion(
        autor=autor, aplicacion=aplicacion, formula=formula,
        valor=valor if valido else None, unidad=unidad, parametros=parametros,
        aplicable=valido,
        estado=(EstadoRevision.SECUNDARIA if secundaria else EstadoRevision.VERIFICADA_BIBLIOGRAFIA),
        criterio=criterio, nota=nota, referencia=referencia,
    )


def calcular_webb(n_bruto: float, material: str) -> list[ResultadoCorrelacion]:
    """E (MPa) por Webb segun Wagh-Bambole 2024, con N sin normalizar.

    Wagh & Bambole reproducen E en kPa: 500(N+15), 330(N+5), 400(N+12).
    Son correlaciones de deformabilidad a partir de placa para estimar asientos.
    El intervalo 0<N<=60 es una restriccion operativa, NO del autor.
    """
    n = _numero('N bruto', n_bruto)
    if material not in WEBB_MATERIALES:
        raise ValueError('El material de Webb no esta entre las tres variantes identificadas.')
    catalogo = (
        ('Arena saturada', 500.0, 15, 'Arenas saturadas bajo el nivel freatico'),
        ('Arena arcillosa', 330.0, 5, 'Arenas arcillosas'),
        ('Perfil arenoso medio/heterogeneo', 400.0, 12, 'Perfil arenoso medio o heterogeneo'),
    )
    filas = []
    for nombre, coef_kpa, offset, descripcion in catalogo:
        valido = (nombre == material and 0 < n <= 60)
        e_mpa = coef_kpa * (n + offset) / 1000 if valido else None
        filas.append(_fila(
            'Webb (1969/1970), reproduccion Wagh-Bambole (2024)',
            descripcion + '; modulo empirico para estimacion de asientos',
            rf'E=({coef_kpa:g}\,(N+{offset}))/1000', e_mpa,
            'MPa', 'N SPT bruto sin correccion [-]; E original en kPa',
            valido, 'Material de la variante y 0 < N <= 60 (limite de consulta NO bibliografico)',
            'Coeficientes SI de revision 2024. Otras recopilaciones dan equivalentes '
            'aproximados en tsf: los redondeos pueden introducir diferencias. '
            'Basado en ensayos con placa de tornillo de escala reducida; no equiparar '
            'automaticamente con un E de proyecto a cualquier deformacion.',
            WEBB_REVISION, secundaria=True,
        ))
    return filas


def calcular_stroud_butler(n_bruto: float, ip_pct: float, f2_kpa: float,
                           material: str, *, f2_confirmado: bool) -> list[ResultadoCorrelacion]:
    """Stroud-Butler 1975: m_v = 1 / (f2 N), M = f2 N.

    N de ensayo SPT historico; f2 en kN/m2 (kPa), calibrado por plasticidad;
    m_v sale en 1/MPa; M en MPa. No se digitaliza la figura 5 ni se interpola
    automaticamente f2(IP), pues la dispersion de los datos es elevada.
    En el estudio m_v corresponde a incremento de 100 kPa sobre sigma' in situ.
    """
    n = _numero('N bruto de Stroud-Butler', n_bruto)
    ip = _numero('IP', ip_pct)
    f2 = _numero('f2', f2_kpa, positivo=True)
    if material not in STROUD_MATERIALES:
        raise ValueError('Material desconocido para Stroud-Butler.')
    valido = (bool(f2_confirmado) and material != 'Otro material (fuera del alcance)'
              and 15 <= ip <= 60 and 0 < n <= 100)
    m_mpa = (f2 * n / 1000) if valido else None
    mv_1mpa = (1000 / (f2 * n)) if valido else None
    criterio = ('Arcillas glaciares o till de caracteristicas compatibles; '
                '15 <= IP <= 60 (alcance aproximado figura 5), 0<N<=100 '
                '(limite operativo); f2 confirmado por usuario; incremento '
                'edometrico de 100 kPa sobre la tension efectiva in situ')
    nota = ('El coeficiente f2 (kPa) se introduce a partir de figura 5, '
            'ensayos o calibracion justificada, NO se infiere del IP por una recta '
            'inventada. Estos resultados son compresibilidad unidimensional; '
            'M y m_v no son un modulo de Young E ni deben convertirse '
            'a E sin otro modelo constitutivo y datos adicionales.')
    return [
        _fila('Stroud y Butler (1975)', 'Modulo edometrico o confinado M',
              r'M=f_2\,N/1000', m_mpa, 'MPa',
              'N SPT bruto [-], IP [%], f2 [kPa]', valido, criterio, nota,
              STROUD_ORIGINAL),
        _fila('Stroud y Butler (1975)', 'Coeficiente de compresibilidad volumetrica m_v',
              r'm_v=1000/(f_2\,N)', mv_1mpa, '1/MPa',
              'N SPT bruto [-], IP [%], f2 [kPa]', valido, criterio, nota,
              STROUD_ORIGINAL),
    ]

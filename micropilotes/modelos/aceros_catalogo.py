"""Datos orientativos de la tabla del catalogo, no valores certificados de producto."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CalidadAcero:
    norma_tabla: str
    limite_elastico_mpa: str
    resistencia_traccion_mpa: Optional[str]
    alargamiento_min_pct: Optional[int]


# Comercial de Sondeos, catalogo espanol, pagina 03 (pagina 6 del PDF).
CALIDADES = {
    'S235': CalidadAcero('EN 10025', '235', '340-470', 26),
    'S275': CalidadAcero('EN 10025', '275', '410-560', 22),
    'S355': CalidadAcero('EN 10025', '355', '490-630', 22),
    'S420': CalidadAcero('Guia DGC tabla 2.1', '420', None, None),
    'S460': CalidadAcero('Guia DGC tabla 2.1', '460', None, None),
    'S550': CalidadAcero('EN 10025', '550', '600-750', 16),
    'J55': CalidadAcero('API 5CT', '379', '517', 24),
    'K55': CalidadAcero('API 5CT', '379', '655', 19),
    'N80': CalidadAcero('API 5CT', '552-758', '689', 18),
}

FY_GUIA={'S235':235.,'S275':275.,'S355':355.,'S420':420.,'S460':460.}
def fy_referencia(calidad):
    return float(CALIDADES[calidad].limite_elastico_mpa.split('-')[0])

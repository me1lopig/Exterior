"""Datos orientativos de la tabla del catalogo, no valores certificados de producto."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CalidadAcero:
    norma_tabla: str
    limite_elastico_mpa: str
    resistencia_traccion_mpa: str
    alargamiento_min_pct: int


# Comercial de Sondeos, catalogo espanol, pagina 03 (pagina 6 del PDF).
CALIDADES = {
    'S235': CalidadAcero('EN 10025', '235', '340-470', 26),
    'S275': CalidadAcero('EN 10025', '275', '410-560', 22),
    'S355': CalidadAcero('EN 10025', '355', '490-630', 22),
    'S550': CalidadAcero('EN 10025', '550', '600-750', 16),
    'J55': CalidadAcero('API 5CT', '379', '517', 24),
    'K55': CalidadAcero('API 5CT', '379', '655', 19),
    'N80': CalidadAcero('API 5CT', '552-758', '689', 18),
}

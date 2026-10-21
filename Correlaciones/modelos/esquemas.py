from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class EstadoRevision(StrEnum):
    VERIFICADA_CTE = "Verificada con CTE"
    TRANSCRITA = "Transcrita del Excel"
    REVISAR = "Requiere revisión"
    VERIFICADA_BIBLIOGRAFIA = "Contrastada con bibliografía"
    SECUNDARIA = "Contrastada con fuente técnica secundaria"
    INTERPOLACION = "Interpolación propia sobre tabla CTE"


@dataclass(frozen=True, slots=True)
class ResultadoCorrelacion:
    autor: str
    aplicacion: str
    formula: str
    valor: float | None
    unidad: str
    parametros: str
    aplicable: bool = True
    estado: EstadoRevision = EstadoRevision.TRANSCRITA
    criterio: str = ""
    nota: str = ""
    referencia: str = "Excel aportado por el usuario"

    def como_fila(self) -> dict[str, Any]:
        fila = asdict(self)
        fila["estado"] = self.estado.value
        return fila


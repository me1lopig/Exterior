from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class EstadoNF(str, Enum):
    REVISAR = "Revisar: cero importado"
    DETECTADO = "Detectado"
    NO_DETECTADO = "No detectado"
    NO_MEDIDO = "No medido"


class Severidad(str, Enum):
    ERROR = "Error"
    AVISO = "Aviso"
    INFO = "Informacion"


@dataclass(frozen=True)
class Incidencia:
    severidad: Severidad
    tabla: str
    fila: int | None
    campo: str
    mensaje: str


@dataclass
class DatosProyecto:
    perfiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    litologia: pd.DataFrame = field(default_factory=pd.DataFrame)
    dpsh: pd.DataFrame = field(default_factory=pd.DataFrame)
    ensayos: pd.DataFrame = field(default_factory=pd.DataFrame)
    ugeo: pd.DataFrame = field(default_factory=pd.DataFrame)
    nivel_freatico: pd.DataFrame = field(default_factory=pd.DataFrame)
    archivos_ignorados: list[str] = field(default_factory=list)

    def tablas(self) -> dict[str, pd.DataFrame]:
        return {
            "Perfiles": self.perfiles,
            "Litologia": self.litologia,
            "DPSH": self.dpsh,
            "Ensayos": self.ensayos,
            "UGEO": self.ugeo,
            "Nivel freatico": self.nivel_freatico,
        }

    def copy(self) -> "DatosProyecto":
        return DatosProyecto(
            perfiles=self.perfiles.copy(deep=True),
            litologia=self.litologia.copy(deep=True),
            dpsh=self.dpsh.copy(deep=True),
            ensayos=self.ensayos.copy(deep=True),
            ugeo=self.ugeo.copy(deep=True),
            nivel_freatico=self.nivel_freatico.copy(deep=True),
            archivos_ignorados=list(self.archivos_ignorados),
        )


"""Estructuras de datos y validacion del dominio geotecnico."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import math

from pydantic import BaseModel, Field, field_validator


class GrupoParametro(StrEnum):
    RESISTENCIA = "Resistencia"
    DEFORMABILIDAD = "Deformabilidad"
    ESTADO = "Estado"
    HIDRAULICA = "Hidraulica"
    INTERACCION = "Interaccion"


class TipoEnsayo(StrEnum):
    SPT = "SPT"
    PRESIOMETRO = "Presiometro Menard"
    DMT = "Dilatometro DMT"
    MOLINETE = "Molinete de campo"
    SISMICA = "Sismica de campo"
    PLACA = "Placa de carga"
    PERMEABILIDAD = "Permeabilidad in situ"


class TipoN(StrEnum):
    N60 = "N60"
    N1_60 = "(N1)60"
    N1_60_CS = "(N1)60,cs"
    N_CTE = "NSPT compatible CTE"


class MetodoInterpolacion(StrEnum):
    LITERAL = "Intervalo literal"
    LINEAL = "Interpolacion lineal"


class EstadoResultado(StrEnum):
    VALIDO = "Valido"
    CONDICIONADO = "Condicionado"
    NO_VALIDO = "No valido"


class Fuente(BaseModel):
    id: str
    titulo: str
    referencia: str
    url: str
    tipo: str


class Correlacion(BaseModel):
    id: str
    nombre: str
    grupo: GrupoParametro
    parametro: str
    ensayo: TipoEnsayo
    fuente_id: str
    unidades_salida: str
    entradas_requeridas: tuple[str, ...]
    entradas_opcionales: tuple[str, ...] = ()
    dominio: str
    permite_interpolacion: bool = False
    permite_extrapolacion: bool = False
    nivel_confianza: str = "Orientativo"
    formula: str
    version_metodo: str = "1.0"


class Resultado(BaseModel):
    correlacion_id: str
    parametro: str
    valor: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    unidad: str
    valido: bool = True
    estado: EstadoResultado = EstadoResultado.VALIDO
    interpolado: bool = False
    categoria: str | None = None
    advertencias: list[str] = Field(default_factory=list)
    metadatos: dict[str, Any] = Field(default_factory=dict)

    @field_validator("valor", "minimo", "maximo")
    @classmethod
    def validar_numeros_finitos(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Los resultados numericos deben ser finitos.")
        return value


class GrupoDatos(BaseModel):
    id: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    ensayo: TipoEnsayo
    observaciones: str = ""

    @field_validator("id", "nombre")
    @classmethod
    def limpiar_texto(cls, value: str) -> str:
        return value.strip()

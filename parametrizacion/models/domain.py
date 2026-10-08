"""Estructuras de datos compartidas por los calculos y la interfaz."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculationResult:
    """Resultado trazable de una correlacion o tabla geotecnica."""

    method: str
    value: float | str
    unit: str
    formula: str
    input_basis: str
    applicability: str
    reference_id: str
    warning: str = ""


@dataclass(frozen=True)
class Reference:
    """Referencia bibliografica mostrada en la aplicacion."""

    ref_id: str
    citation: str
    url: str
    source_type: str
    scope: str

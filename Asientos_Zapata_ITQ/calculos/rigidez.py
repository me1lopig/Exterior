from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AjusteRigidez:
    """Corrección simplificada del asiento central de una zapata flexible."""

    considerar_rigida: bool = False
    factor: float = 0.80

    def validar(self) -> list[str]:
        if not np.isfinite(self.factor) or not 0.0 < self.factor <= 1.0:
            return ["El factor de rigidez Cr debe cumplir 0 < Cr <= 1."]
        return []

    @property
    def tipo(self) -> str:
        return "Rígida simplificada" if self.considerar_rigida else "Flexible"

    def asiento_adoptado_mm(self, asiento_flexible_centro_mm: float) -> float:
        """Devuelve el asiento central adoptado sin alterar el cálculo flexible base."""
        if not np.isfinite(asiento_flexible_centro_mm):
            raise ValueError("El asiento flexible debe ser finito.")
        return (
            self.factor * asiento_flexible_centro_mm
            if self.considerar_rigida
            else asiento_flexible_centro_mm
        )


def tabla_aportes_con_porcentaje(tabla: pd.DataFrame) -> pd.DataFrame:
    """Añade el porcentaje de cada aporte respecto de la suma de asientos."""
    salida = tabla.copy()
    total = float(salida["asiento_mm"].sum())
    if abs(total) <= 1e-12:
        salida["aporte_pct"] = 0.0
    else:
        salida["aporte_pct"] = 100.0 * salida["asiento_mm"] / total
    return salida

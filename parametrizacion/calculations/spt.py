"""Correcciones del golpeo SPT con factores explicitos.

Convencion: N es el golpeo de campo; ER se introduce en porcentaje. Los factores
CB, CR y CS representan diametro de sondeo, longitud de varillaje y tomamuestras.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SPTCorrection:
    n_field: float
    energy_ratio_percent: float = 60.0
    borehole_factor: float = 1.0
    rod_factor: float = 1.0
    sampler_factor: float = 1.0
    effective_overburden_kpa: float = 100.0
    atmospheric_pressure_kpa: float = 100.0
    cn_cap: float = 1.7

    def __post_init__(self) -> None:
        positive = {
            "ER": self.energy_ratio_percent,
            "CB": self.borehole_factor,
            "CR": self.rod_factor,
            "CS": self.sampler_factor,
            "sigma_v_eff": self.effective_overburden_kpa,
            "pa": self.atmospheric_pressure_kpa,
            "CN max": self.cn_cap,
        }
        if self.n_field < 0:
            raise ValueError("N de campo no puede ser negativo.")
        for name, value in positive.items():
            if value <= 0 or not math.isfinite(value):
                raise ValueError(f"{name} debe ser positivo y finito.")

    @property
    def n60(self) -> float:
        """N60 = N * (ER/60) * CB * CR * CS."""

        return (
            self.n_field
            * self.energy_ratio_percent
            / 60.0
            * self.borehole_factor
            * self.rod_factor
            * self.sampler_factor
        )

    @property
    def cn(self) -> float:
        """Factor de sobrecarga CN = min[sqrt(pa/sigma'v0), CN,max]."""

        return min(
            math.sqrt(self.atmospheric_pressure_kpa / self.effective_overburden_kpa),
            self.cn_cap,
        )

    @property
    def n1_60(self) -> float:
        """Golpeo normalizado por energia y sobrecarga."""

        return self.cn * self.n60

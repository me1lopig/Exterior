from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EffectiveGeometry:
    width_m: float
    length_m: float
    area_m2: float
    eccentricity_b_m: float
    eccentricity_l_m: float
    is_equivalent_rectangle: bool = False
    axes_swapped: bool = False
    note: str = ""


@dataclass(frozen=True)
class CheckResult:
    name: str
    demand: float
    resistance: float
    utilization: float
    passes: bool
    units: str
    basis: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BearingCapacityResult:
    action_name: str
    geometry: EffectiveGeometry
    pressure_gross_kpa: float
    pressure_net_kpa: float
    characteristic_resistance_kpa: float
    design_resistance_kpa: float
    utilization: float
    passes: bool
    terms_kpa: dict[str, float]
    factors: dict[str, float]
    parameters: dict[str, float | str]
    warnings: tuple[str, ...] = field(default_factory=tuple)

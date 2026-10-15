from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math


class DrainageCondition(str, Enum):
    DRAINED = "drenado"
    UNDRAINED = "no_drenado"


class DesignSituation(str, Enum):
    PERSISTENT = "persistente"
    TRANSIENT = "transitoria"
    EXTRAORDINARY = "extraordinaria"


class FoundationType(str, Enum):
    RECTANGULAR = "rectangular"
    STRIP = "corrida"
    CIRCULAR = "circular"


@dataclass(frozen=True)
class SoilProfile:
    drainage: DrainageCondition
    c_effective_kpa: float = 0.0
    phi_effective_deg: float = 30.0
    cu0_kpa: float = 50.0
    cu_gradient_kpa_m: float = 0.0
    cu_profile: tuple[tuple[float, float], ...] = ()
    gamma_apparent_kn_m3: float = 18.0
    gamma_saturated_kn_m3: float = 20.0
    water_table_depth_m: float = 10.0
    upward_gradient: float = 0.0
    gamma_water_kn_m3: float = 9.81
    fines_percent: float | None = None
    coarse_over_20mm_percent: float | None = None
    spt_n_mean: float | None = None
    deformation_modulus_mpa: float | None = None
    poisson_ratio: float = 0.30
    overburden_soil_kpa: float | None = None

    def __post_init__(self) -> None:
        nonnegative = {
            "c'": self.c_effective_kpa,
            "cu0": self.cu0_kpa,
            "gradiente de cu": self.cu_gradient_kpa_m,
            "profundidad del nivel freatico": self.water_table_depth_m,
            "gradiente ascendente": self.upward_gradient,
        }
        for name, value in nonnegative.items():
            if value < 0 or not math.isfinite(value):
                raise ValueError(f"{name} debe ser finito y no negativo")
        if not 0 <= self.phi_effective_deg < 60:
            raise ValueError("phi' debe estar en el intervalo [0, 60) grados")
        if self.gamma_apparent_kn_m3 <= 0:
            raise ValueError("El peso especifico aparente debe ser positivo")
        if self.gamma_saturated_kn_m3 <= self.gamma_water_kn_m3:
            raise ValueError("El peso especifico saturado debe superar al del agua")
        if not 0 <= self.poisson_ratio < 0.5:
            raise ValueError("El coeficiente de Poisson debe estar en [0, 0.5)")
        for name, value in (
            ("porcentaje de finos", self.fines_percent),
            ("porcentaje >20 mm", self.coarse_over_20mm_percent),
        ):
            if value is not None and not 0 <= value <= 100:
                raise ValueError(f"{name} debe estar entre 0 y 100")
        if self.spt_n_mean is not None and self.spt_n_mean <= 0:
            raise ValueError("N_SPT debe ser positivo")
        if self.deformation_modulus_mpa is not None and self.deformation_modulus_mpa <= 0:
            raise ValueError("El modulo de deformacion debe ser positivo")
        if self.overburden_soil_kpa is not None and self.overburden_soil_kpa < 0:
            raise ValueError("La sobrecarga geostatica debe ser no negativa")
        if self.cu_profile:
            previous_depth = -math.inf
            for depth, cu in self.cu_profile:
                if not math.isfinite(depth) or depth < 0 or depth <= previous_depth:
                    raise ValueError(
                        "Las profundidades del perfil cu(z) deben ser finitas, "
                        "no negativas y estrictamente crecientes"
                    )
                if not math.isfinite(cu) or cu < 0:
                    raise ValueError("Los valores cu(z) deben ser finitos y no negativos")
                previous_depth = depth

    @property
    def gamma_submerged_kn_m3(self) -> float:
        return self.gamma_saturated_kn_m3 - self.gamma_water_kn_m3

    def cohesion_kpa(self, width_m: float, base_depth_m: float = 0.0) -> float:
        if self.drainage is DrainageCondition.DRAINED:
            return self.c_effective_kpa
        if self.cu_profile:
            target_depth = base_depth_m + width_m / 4.0
            first_depth, first_cu = self.cu_profile[0]
            last_depth, last_cu = self.cu_profile[-1]
            if target_depth < first_depth or target_depth > last_depth:
                raise ValueError(
                    f"El perfil cu(z) no cubre z=D+B/4={target_depth:.2f} m"
                )
            if math.isclose(target_depth, first_depth):
                return first_cu
            for (z0, cu0), (z1, cu1) in zip(self.cu_profile, self.cu_profile[1:]):
                if z0 <= target_depth <= z1:
                    ratio = (target_depth - z0) / (z1 - z0)
                    return cu0 + ratio * (cu1 - cu0)
            return last_cu
        value = self.cu0_kpa + self.cu_gradient_kpa_m * width_m / 4.0
        return min(value, 2.0 * self.cu0_kpa)


@dataclass(frozen=True)
class Foundation:
    kind: FoundationType
    width_m: float
    length_m: float
    embedment_m: float
    ground_slope_deg: float = 0.0
    surcharge_kpa: float = 0.0
    base_adhesion_kpa: float = 0.0
    include_depth_factors: bool = True
    near_slope: bool = False

    def __post_init__(self) -> None:
        if self.width_m <= 0 or self.length_m <= 0:
            raise ValueError("Las dimensiones de la cimentacion deben ser positivas")
        if self.embedment_m < 0:
            raise ValueError("La profundidad de apoyo no puede ser negativa")
        if not 0 <= self.ground_slope_deg < 45:
            raise ValueError("La inclinacion del terreno debe estar en [0, 45) grados")
        if self.surcharge_kpa < 0 or self.base_adhesion_kpa < 0:
            raise ValueError("La sobrecarga y la adhesion de base no pueden ser negativas")
        if self.kind is FoundationType.RECTANGULAR and self.width_m > self.length_m:
            raise ValueError("En planta rectangular se requiere B <= L")
        if self.kind is FoundationType.STRIP and not math.isclose(self.length_m, 1.0):
            raise ValueError("La zapata corrida se calcula por una franja de L=1 m")
        if self.kind is FoundationType.CIRCULAR and not math.isclose(
            self.width_m, self.length_m
        ):
            raise ValueError("En zapata circular B y L deben coincidir con el diametro")

    @property
    def plan_area_m2(self) -> float:
        if self.kind is FoundationType.CIRCULAR:
            return math.pi * self.width_m**2 / 4.0
        return self.width_m * self.length_m


@dataclass(frozen=True)
class ActionCase:
    name: str
    vertical_kn: float
    horizontal_b_kn: float = 0.0
    horizontal_l_kn: float = 0.0
    moment_b_knm: float = 0.0
    moment_l_knm: float = 0.0
    situation: DesignSituation = DesignSituation.PERSISTENT

    def __post_init__(self) -> None:
        values = (
            self.vertical_kn,
            self.horizontal_b_kn,
            self.horizontal_l_kn,
            self.moment_b_knm,
            self.moment_l_knm,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Las acciones deben ser finitas")
        if self.vertical_kn <= 0:
            raise ValueError("La resultante vertical en la base debe ser positiva")

    @property
    def horizontal_kn(self) -> float:
        return math.hypot(self.horizontal_b_kn, self.horizontal_l_kn)


@dataclass(frozen=True)
class SoilLayer:
    name: str
    top_depth_m: float
    bottom_depth_m: float
    deformation_modulus_mpa: float
    phi_effective_deg: float | None = None
    cu_kpa: float | None = None
    spt_n: float | None = None
    c_effective_kpa: float = 0.0
    gamma_apparent_kn_m3: float = 18.0
    gamma_saturated_kn_m3: float = 20.0
    poisson_ratio: float = 0.30

    def __post_init__(self) -> None:
        if self.top_depth_m < 0 or self.bottom_depth_m <= self.top_depth_m:
            raise ValueError(f"Intervalo invalido en la capa {self.name}")
        if self.deformation_modulus_mpa <= 0:
            raise ValueError(f"Modulo no positivo en la capa {self.name}")
        if self.c_effective_kpa < 0:
            raise ValueError(f"Cohesion efectiva negativa en la capa {self.name}")
        if self.phi_effective_deg is not None and not 0 <= self.phi_effective_deg < 60:
            raise ValueError(f"Angulo de rozamiento no valido en la capa {self.name}")
        if self.gamma_apparent_kn_m3 <= 0:
            raise ValueError(f"Peso especifico no positivo en la capa {self.name}")
        if self.gamma_saturated_kn_m3 <= 9.81:
            raise ValueError(
                f"El peso saturado debe superar al del agua en la capa {self.name}"
            )
        if not 0 <= self.poisson_ratio < 0.5:
            raise ValueError(f"Poisson debe estar en [0, 0.5) en la capa {self.name}")


def bearing_resistance_factor(situation: DesignSituation) -> float:
    if situation is DesignSituation.EXTRAORDINARY:
        return 2.0
    return 3.0


def sliding_resistance_factor(situation: DesignSituation) -> float:
    if situation is DesignSituation.EXTRAORDINARY:
        return 1.1
    return 1.5

"""Estructuras de datos y validacion temprana con unidades explicitas."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, pi
from typing import Literal


SoilType = Literal["granular", "cohesivo"]
Drainage = Literal["simple", "doble"]
Shape = Literal["rectangular", "circular", "banda"]
FoundationType = Literal["zapata", "losa", "pozo"]
LoadMode = Literal["fuerza", "presion"]
PressureBasis = Literal["neta", "bruta"]
Rigidity = Literal["flexible", "rigida"]
ImmediateModel = Literal["edometrico_1d", "elastico_3d"]


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"


@dataclass(frozen=True)
class Layer:
    """Estrato horizontal; tensiones en kPa, longitudes en m y cv en m2/ano."""

    name: str
    soil_type: SoilType
    thickness_m: float
    gamma_unsat_kn_m3: float
    gamma_sat_kn_m3: float
    e_mpa: float
    nu: float = 0.30
    cc: float = 0.0
    cr: float = 0.0
    e0: float = 0.70
    sigma_pc_kpa: float = 0.0
    cv_m2_year: float = 0.0
    c_alpha: float = 0.0
    drainage: Drainage = "doble"

    def validate(self, index: int) -> list[ValidationIssue]:
        prefix = f"estratos[{index}]"
        issues: list[ValidationIssue] = []
        numeric_positive = {
            "thickness_m": self.thickness_m,
            "gamma_unsat_kn_m3": self.gamma_unsat_kn_m3,
            "gamma_sat_kn_m3": self.gamma_sat_kn_m3,
            "e_mpa": self.e_mpa,
        }
        for key, value in numeric_positive.items():
            if not isfinite(value) or value <= 0:
                issues.append(ValidationIssue(f"{prefix}.{key}", "Debe ser finito y mayor que cero."))
        if self.gamma_sat_kn_m3 < self.gamma_unsat_kn_m3:
            issues.append(ValidationIssue(
                f"{prefix}.gamma_sat_kn_m3",
                "El peso especifico saturado es menor que el no saturado.",
                "warning",
            ))
        if not 0 <= self.nu < 0.5:
            issues.append(ValidationIssue(f"{prefix}.nu", "Debe cumplirse 0 <= nu < 0,5."))
        if self.soil_type == "cohesivo":
            for key, value in {"cc": self.cc, "cr": self.cr, "cv_m2_year": self.cv_m2_year}.items():
                if not isfinite(value) or value <= 0:
                    issues.append(ValidationIssue(f"{prefix}.{key}", "Debe ser finito y mayor que cero."))
            if self.cr > self.cc:
                issues.append(ValidationIssue(f"{prefix}.cr", "Cr no debe superar Cc."))
            if not isfinite(self.e0) or self.e0 <= 0:
                issues.append(ValidationIssue(f"{prefix}.e0", "Debe ser finito y mayor que cero."))
            if not isfinite(self.sigma_pc_kpa) or self.sigma_pc_kpa <= 0:
                issues.append(ValidationIssue(f"{prefix}.sigma_pc_kpa", "Debe ser finita y mayor que cero."))
            if not isfinite(self.c_alpha) or self.c_alpha < 0:
                issues.append(ValidationIssue(f"{prefix}.c_alpha", "Debe ser finito y no negativo."))
        return issues


@dataclass(frozen=True)
class Foundation:
    """Geometria y acciones referidas al centro de la base."""

    shape: Shape
    foundation_type: FoundationType = "zapata"
    width_m: float = 2.0
    length_m: float = 3.0
    diameter_m: float = 2.0
    embedment_m: float = 1.0
    load_mode: LoadMode = "presion"
    pressure_basis: PressureBasis = "neta"
    rigidity: Rigidity = "flexible"
    vertical_load_kn: float = 600.0
    pressure_kpa: float = 100.0
    mx_knm: float = 0.0
    my_knm: float = 0.0

    @property
    def area_m2(self) -> float:
        if self.shape == "circular":
            return pi * self.diameter_m**2 / 4.0
        return self.width_m * self.length_m

    @property
    def characteristic_width_m(self) -> float:
        if self.shape == "circular":
            return self.diameter_m
        return self.width_m

    @property
    def applied_vertical_kn(self) -> float:
        if self.load_mode == "presion":
            return self.pressure_kpa * self.area_m2
        return self.vertical_load_kn

    def validate(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        dims = {"embedment_m": self.embedment_m}
        if self.shape == "circular":
            dims["diameter_m"] = self.diameter_m
        else:
            dims.update(width_m=self.width_m, length_m=self.length_m)
        for key, value in dims.items():
            if not isfinite(value) or (key != "embedment_m" and value <= 0) or value < 0:
                issues.append(ValidationIssue(key, "Dimension no valida."))
        for key, value in {
            "vertical_load_kn": self.vertical_load_kn,
            "pressure_kpa": self.pressure_kpa,
            "mx_knm": self.mx_knm,
            "my_knm": self.my_knm,
        }.items():
            if not isfinite(value):
                issues.append(ValidationIssue(key, "Debe ser un numero finito."))
        if self.applied_vertical_kn == 0:
            issues.append(ValidationIssue("carga", "La accion vertical no puede ser nula."))
        if self.shape == "banda" and (abs(self.mx_knm) > 0 or abs(self.my_knm) > 0):
            issues.append(ValidationIssue("momentos", "El modelo de banda no admite momentos.", "warning"))
        if self.foundation_type == "pozo":
            issues.append(ValidationIssue(
                "foundation_type",
                "El pozo requiere transferencia por fuste y base mediante un modelo especifico. "
                "Este motor superficial lo bloquea para evitar un resultado no fisico.",
            ))
        if self.foundation_type == "losa":
            issues.append(ValidationIssue(
                "foundation_type",
                "La losa se evalua como limite flexible o rigido del semiespacio; no se modela la flexion de placa.",
                "warning",
            ))
        return issues


@dataclass(frozen=True)
class AnalysisOptions:
    dz_m: float = 0.20
    influence_ratio: float = 0.10
    max_depth_factor: float = 50.0
    immediate_model: ImmediateModel = "elastico_3d"
    include_primary: bool = True
    include_secondary: bool = True
    service_years: float = 50.0
    settlement_limit_mm: float = 50.0
    gamma_water_kn_m3: float = 9.81
    quadrature_order: int = 12

    def validate(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if not 0.01 <= self.dz_m <= 2.0:
            issues.append(ValidationIssue("dz_m", "Debe estar entre 0,01 y 2,00 m."))
        if not 0 < self.influence_ratio < 1:
            issues.append(ValidationIssue("influence_ratio", "Debe estar entre 0 y 1."))
        if not 5 <= self.max_depth_factor <= 200:
            issues.append(ValidationIssue("max_depth_factor", "Debe estar entre 5 y 200."))
        if not isfinite(self.service_years) or self.service_years <= 0:
            issues.append(ValidationIssue("service_years", "Debe ser mayor que cero."))
        if not isfinite(self.settlement_limit_mm) or self.settlement_limit_mm <= 0:
            issues.append(ValidationIssue("settlement_limit_mm", "Debe ser mayor que cero."))
        if not 4 <= self.quadrature_order <= 32:
            issues.append(ValidationIssue("quadrature_order", "Debe estar entre 4 y 32."))
        return issues


@dataclass
class CalculationMetadata:
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

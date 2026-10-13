"""Estructuras de entrada con validacion temprana y unidades explicitas."""

from __future__ import annotations

from dataclasses import dataclass
from math import radians, tan


@dataclass(frozen=True)
class ProjectData:
    name: str = "Talud temporal"
    location: str = ""
    author: str = ""
    notes: str = ""


@dataclass(frozen=True)
class Soil:
    name: str
    gamma_dry: float
    gamma_sat: float
    cohesion: float
    friction_deg: float

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Cada suelo debe tener un nombre.")
        if self.gamma_dry <= 0 or self.gamma_sat <= 0:
            raise ValueError(f"Los pesos unitarios de {self.name} deben ser positivos.")
        if self.gamma_sat < self.gamma_dry:
            raise ValueError(f"En {self.name}, gamma_sat no puede ser menor que gamma_seco.")
        if self.cohesion < 0:
            raise ValueError(f"La cohesion de {self.name} no puede ser negativa.")
        if not 0 <= self.friction_deg < 50:
            raise ValueError(f"El angulo de rozamiento de {self.name} debe estar entre 0 y 50 grados.")


@dataclass(frozen=True)
class SoilProfile:
    upper: Soil
    lower: Soil | None = None
    interface_elevation: float = 0.0

    @property
    def has_two_soils(self) -> bool:
        return self.lower is not None

    def validate(self, height: float) -> None:
        self.upper.validate()
        if self.lower is not None:
            self.lower.validate()
            if not 0 < self.interface_elevation < height:
                raise ValueError("La cota del contacto debe estar entre el pie y la coronacion.")

    def soil_at(self, elevation: float) -> Soil:
        if self.lower is not None and elevation < self.interface_elevation:
            return self.lower
        return self.upper

    def upper_thickness(self, height: float) -> float:
        """Espesor vertical del estrato superior medido desde coronacion."""
        return height if self.lower is None else height - self.interface_elevation

    def lower_thickness_within_slope(self, height: float) -> float:
        """Espesor del estrato inferior entre el contacto y la cota del pie."""
        return 0.0 if self.lower is None else height - self.upper_thickness(height)


@dataclass(frozen=True)
class SlopeGeometry:
    height: float
    angle_deg: float
    water_elevation: float
    crest_length_factor: float = 1.2
    toe_length_factor: float = 1.0

    def validate(self) -> None:
        if self.height <= 0:
            raise ValueError("La altura debe ser positiva.")
        if not 10 <= self.angle_deg <= 85:
            raise ValueError("La pendiente debe estar entre 10 y 85 grados respecto a la horizontal.")
        if not 0 <= self.water_elevation <= self.height:
            raise ValueError("La cota del nivel freatico debe estar entre 0 y H.")
        if self.crest_length_factor <= 0 or self.toe_length_factor <= 0:
            raise ValueError("Las extensiones de coronacion y pie deben ser positivas.")

    @property
    def run(self) -> float:
        return self.height / tan(radians(self.angle_deg))

    @property
    def x_min(self) -> float:
        return -self.crest_length_factor * self.height

    @property
    def x_max(self) -> float:
        return self.run + self.toe_length_factor * self.height


@dataclass(frozen=True)
class AnalysisConfig:
    slices: int = 30
    search_level: str = "Equilibrada"
    gamma_water: float = 9.81
    bishop_tolerance: float = 1e-5
    bishop_max_iterations: int = 100
    min_depth_ratio: float = 0.08
    target_factor: float = 1.30

    def validate(self) -> None:
        if not 10 <= self.slices <= 100:
            raise ValueError("El numero de dovelas debe estar entre 10 y 100.")
        if self.search_level not in {"Rapida", "Equilibrada", "Detallada"}:
            raise ValueError("Nivel de busqueda no reconocido.")
        if self.gamma_water <= 0:
            raise ValueError("El peso unitario del agua debe ser positivo.")
        if self.bishop_tolerance <= 0 or self.bishop_max_iterations < 10:
            raise ValueError("Parametros iterativos de Bishop no validos.")
        if not 0.5 <= self.target_factor <= 3.0:
            raise ValueError("El factor objetivo debe estar entre 0.5 y 3.0.")


@dataclass(frozen=True)
class SweepConfig:
    vary_angle: bool
    angle_min: float
    angle_max: float
    angle_steps: int
    vary_water: bool
    water_min: float
    water_max: float
    water_steps: int

    def validate(self, height: float) -> None:
        if not self.vary_angle and not self.vary_water:
            raise ValueError("Seleccione al menos una variable para el analisis de sensibilidad.")
        if self.vary_angle:
            if not 10 <= self.angle_min <= self.angle_max <= 85:
                raise ValueError("Los limites de pendiente deben cumplir 10 <= minimo <= maximo <= 85 grados.")
            if not 2 <= self.angle_steps <= 15:
                raise ValueError("Use entre 2 y 15 pasos de pendiente.")
        if self.vary_water:
            if not 0 <= self.water_min <= self.water_max <= height:
                raise ValueError("Los limites del nivel freatico deben estar entre 0 y H.")
            if not 2 <= self.water_steps <= 15:
                raise ValueError("Use entre 2 y 15 pasos de nivel freatico.")

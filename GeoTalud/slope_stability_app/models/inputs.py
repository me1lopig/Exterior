"""Estructuras de entrada con validacion temprana y unidades explicitas."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, radians, tan


def _all_finite(values: tuple[float, ...]) -> bool:
    try:
        return all(isfinite(value) for value in values)
    except TypeError:
        return False


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
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Cada suelo debe tener un nombre.")
        values = (self.gamma_dry, self.gamma_sat, self.cohesion, self.friction_deg)
        if not _all_finite(values):
            raise ValueError(f"Los parametros de {self.name} deben ser numeros finitos.")
        if self.gamma_dry <= 0 or self.gamma_sat <= 0:
            raise ValueError(f"Los pesos unitarios de {self.name} deben ser positivos.")
        if self.gamma_sat < self.gamma_dry:
            raise ValueError(f"En {self.name}, gamma_sat no puede ser menor que gamma_seco.")
        if self.cohesion < 0:
            raise ValueError(f"La cohesion de {self.name} no puede ser negativa.")
        if not 0 <= self.friction_deg < 50:
            raise ValueError(f"El angulo de rozamiento de {self.name} debe estar entre 0 y 50 grados.")


@dataclass(frozen=True)
class SoilLayer:
    soil: Soil
    thickness: float

    def validate(self) -> None:
        self.soil.validate()
        if not _all_finite((self.thickness,)):
            raise ValueError(f"El espesor de {self.soil.name} debe ser un numero finito.")
        if self.thickness <= 0:
            raise ValueError(f"El espesor de {self.soil.name} debe ser mayor que cero.")


@dataclass(frozen=True)
class SoilProfile:
    layers: tuple[SoilLayer, ...]

    def validate(self, model_depth: float) -> None:
        if not _all_finite((model_depth,)) or model_depth <= 0:
            raise ValueError("La profundidad del modelo debe ser positiva y finita.")
        if not self.layers:
            raise ValueError("Debe definir al menos una capa de suelo.")
        for layer in self.layers:
            layer.validate()
        if self.total_thickness + 1e-9 < model_depth:
            missing = model_depth - self.total_thickness
            raise ValueError(
                f"La suma de espesores ({self.total_thickness:.3f} m) no cubre la profundidad "
                f"del modelo ({model_depth:.3f} m); faltan {missing:.3f} m."
            )

    @property
    def total_thickness(self) -> float:
        return float(sum(layer.thickness for layer in self.layers))

    def soil_at(self, elevation: float, crest_elevation: float) -> Soil:
        """Devuelve el suelo a una cota, usando espesores desde coronacion."""
        depth = crest_elevation - elevation
        if depth <= 0:
            return self.layers[0].soil
        cumulative = 0.0
        for layer in self.layers:
            cumulative += layer.thickness
            if depth < cumulative - 1e-10:
                return layer.soil
        if depth <= self.total_thickness + 1e-8:
            return self.layers[-1].soil
        raise ValueError(
            f"La cota z={elevation:.3f} m queda fuera del perfil estratigrafico definido."
        )

    def interface_elevations(self, crest_elevation: float, model_depth: float) -> tuple[float, ...]:
        """Cotas de contactos interiores comprendidos dentro del dominio de calculo."""
        elevations: list[float] = []
        cumulative = 0.0
        for layer in self.layers[:-1]:
            cumulative += layer.thickness
            if cumulative < model_depth - 1e-9:
                elevations.append(crest_elevation - cumulative)
        return tuple(elevations)


@dataclass(frozen=True)
class SlopeGeometry:
    height: float
    angle_deg: float
    water_depth: float
    model_depth: float
    crest_length_factor: float = 1.2
    toe_length_factor: float = 1.0

    def validate(self) -> None:
        values = (
            self.height,
            self.angle_deg,
            self.water_depth,
            self.model_depth,
            self.crest_length_factor,
            self.toe_length_factor,
        )
        if not _all_finite(values):
            raise ValueError("Los parametros geometricos deben ser numeros finitos.")
        if self.height <= 0:
            raise ValueError("La altura debe ser positiva.")
        if not 10 <= self.angle_deg <= 85:
            raise ValueError("La pendiente debe estar entre 10 y 85 grados respecto a la horizontal.")
        if self.model_depth < self.height:
            raise ValueError("La profundidad del modelo debe ser mayor o igual que H.")
        if not 0 <= self.water_depth <= self.model_depth:
            raise ValueError("La profundidad del nivel freatico debe estar entre 0 y la profundidad del modelo.")
        if self.crest_length_factor <= 0 or self.toe_length_factor <= 0:
            raise ValueError("Las extensiones de coronacion y pie deben ser positivas.")

    @property
    def water_elevation(self) -> float:
        """Cota interna del nivel freatico referida al pie z=0."""
        return self.height - self.water_depth

    @property
    def model_base_elevation(self) -> float:
        return self.height - self.model_depth

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
        numeric_values = (
            self.slices,
            self.gamma_water,
            self.bishop_tolerance,
            self.bishop_max_iterations,
            self.min_depth_ratio,
            self.target_factor,
        )
        if not _all_finite(numeric_values):
            raise ValueError("Los parametros de calculo deben ser numeros finitos.")
        if not isinstance(self.slices, int) or isinstance(self.slices, bool):
            raise ValueError("El numero de dovelas debe ser un entero.")
        if not isinstance(self.bishop_max_iterations, int) or isinstance(self.bishop_max_iterations, bool):
            raise ValueError("El maximo de iteraciones de Bishop debe ser un entero.")
        if not 10 <= self.slices <= 100:
            raise ValueError("El numero de dovelas debe estar entre 10 y 100.")
        if self.search_level not in {"Rapida", "Equilibrada", "Detallada"}:
            raise ValueError("Nivel de busqueda no reconocido.")
        if self.gamma_water <= 0:
            raise ValueError("El peso unitario del agua debe ser positivo.")
        if self.bishop_tolerance <= 0 or self.bishop_max_iterations < 10:
            raise ValueError("Parametros iterativos de Bishop no validos.")
        if not 0 < self.min_depth_ratio <= 0.5:
            raise ValueError("La profundidad minima relativa debe estar entre 0 y 0.5.")
        if not 0.5 <= self.target_factor <= 3.0:
            raise ValueError("El factor objetivo debe estar entre 0.5 y 3.0.")


@dataclass(frozen=True)
class SweepConfig:
    vary_angle: bool
    angle_min: float
    angle_max: float
    angle_steps: int
    vary_water: bool
    water_depth_min: float
    water_depth_max: float
    water_steps: int

    def validate(self, model_depth: float) -> None:
        values = (
            self.angle_min,
            self.angle_max,
            self.angle_steps,
            self.water_depth_min,
            self.water_depth_max,
            self.water_steps,
            model_depth,
        )
        if not _all_finite(values):
            raise ValueError("Los limites del barrido deben ser numeros finitos.")
        if not isinstance(self.angle_steps, int) or isinstance(self.angle_steps, bool):
            raise ValueError("Los pasos de pendiente deben ser un entero.")
        if not isinstance(self.water_steps, int) or isinstance(self.water_steps, bool):
            raise ValueError("Los pasos de nivel freatico deben ser un entero.")
        if not self.vary_angle and not self.vary_water:
            raise ValueError("Seleccione al menos una variable para el analisis de sensibilidad.")
        if self.vary_angle:
            if not 10 <= self.angle_min <= self.angle_max <= 85:
                raise ValueError("Los limites de pendiente deben cumplir 10 <= minimo <= maximo <= 85 grados.")
            if self.angle_min == self.angle_max:
                raise ValueError("Para variar la pendiente, sus limites minimo y maximo deben ser distintos.")
            if not 2 <= self.angle_steps <= 15:
                raise ValueError("Use entre 2 y 15 pasos de pendiente.")
        if self.vary_water:
            if not 0 <= self.water_depth_min <= self.water_depth_max <= model_depth:
                raise ValueError("Los limites de profundidad del nivel freatico deben estar dentro del modelo.")
            if self.water_depth_min == self.water_depth_max:
                raise ValueError("Para variar el nivel freatico, sus profundidades minima y maxima deben ser distintas.")
            if not 2 <= self.water_steps <= 15:
                raise ValueError("Use entre 2 y 15 pasos de nivel freatico.")

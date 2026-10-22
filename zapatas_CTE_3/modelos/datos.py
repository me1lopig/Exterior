"""Estructuras de datos y validación temprana."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class DatosProyecto:
    peticionario: str = "CONSEJERÍA DE EDUCACIÓN - JUNTA DE EXTREMADURA"
    trabajo: str = "GIMNASIO EN COLEGIO PÚBLICO PRINCIPE DE ASTURIAS - MONTIJO"
    expediente: str = "6/C555/005"


@dataclass(frozen=True)
class CapaSuelo:
    nombre: str
    z_superior_m: float
    z_inferior_m: float
    modulo_mpa: float
    poisson: float

    def validar(self) -> list[str]:
        errores: list[str] = []
        valores = (self.z_superior_m, self.z_inferior_m, self.modulo_mpa, self.poisson)
        if not all(isfinite(valor) for valor in valores):
            errores.append(f"{self.nombre}: todos los valores deben ser finitos.")
            return errores
        if self.z_superior_m < 0:
            errores.append(f"{self.nombre}: la profundidad superior no puede ser negativa.")
        if self.z_inferior_m <= self.z_superior_m:
            errores.append(f"{self.nombre}: la profundidad inferior debe superar a la superior.")
        if self.modulo_mpa <= 0:
            errores.append(f"{self.nombre}: E debe ser mayor que cero.")
        if not 0 <= self.poisson < 0.5:
            errores.append(f"{self.nombre}: el coeficiente de Poisson debe cumplir 0 <= nu < 0,5.")
        return errores


@dataclass(frozen=True)
class DatosAsientos:
    asiento_admisible_cm: float = 5.0
    longitud_corrida_m: float = 100.0
    capas: tuple[CapaSuelo, ...] = field(default_factory=tuple)
    metodo_centro: str = "excel"
    tipo_material_balasto: str = "Cohesivo"

    def validar(self) -> list[str]:
        errores: list[str] = []
        if not isfinite(self.asiento_admisible_cm) or self.asiento_admisible_cm <= 0:
            errores.append("El asiento admisible debe ser mayor que cero.")
        if not isfinite(self.longitud_corrida_m) or self.longitud_corrida_m <= 0:
            errores.append("La longitud equivalente de la zapata corrida debe ser mayor que cero.")
        if not self.capas:
            errores.append("Debe definirse al menos una capa para el cálculo de asientos.")
        for capa in self.capas:
            errores.extend(capa.validar())
        for anterior, siguiente in zip(self.capas, self.capas[1:]):
            if siguiente.z_superior_m < anterior.z_inferior_m:
                errores.append(
                    f"Las capas {anterior.nombre} y {siguiente.nombre} se solapan en profundidad."
                )
        if self.metodo_centro not in {"excel", "superposicion"}:
            errores.append("El método de asiento central no es válido.")
        if self.tipo_material_balasto not in {"Cohesivo", "Granular"}:
            errores.append("El material para el coeficiente de balasto debe ser Cohesivo o Granular.")
        return errores


@dataclass(frozen=True)
class DatosHundimiento:
    situacion_drenaje: str = "Persistente a largo plazo"
    forma: str = "Rectangular"
    anchos_m: tuple[float, ...] = (1.5, 1.8, 2.0, 2.5, 3.0)
    profundidad_base_m: float = 0.5
    nivel_freatico_m: float = 6.6
    flujo_ascendente: bool = False
    gradiente_vertical: float = 0.4
    inclinacion_talud_deg: float = 0.0
    talud_transitorio_sin_drenaje: bool = False
    phi_deg: float = 30.0
    cohesion_kpa: float = 0.0
    cu_aumenta_con_profundidad: bool = False
    cu_z_inicial_m: float = 0.0
    cu_inicial_kpa: float = 50.0
    cu_z_final_m: float = 10.0
    cu_final_kpa: float = 150.0
    gamma_efectivo_kn_m3: float = 18.0
    gamma_aparente_kn_m3: float = 18.0
    considerar_sobrecarga: bool = True
    gamma_sobrecarga_kn_m3: float = 18.0
    altura_sobrecarga_m: float = 0.5
    considerar_terreno_sobre_base: bool = False
    situacion_seguridad: str = "Situación transitoria"
    longitud_corrida_m: float = 1000.0

    def validar(self) -> list[str]:
        errores: list[str] = []
        if not self.anchos_m or any((not isfinite(b) or b <= 0) for b in self.anchos_m):
            errores.append("Todos los anchos de cimentación deben ser positivos y finitos.")
        if self.profundidad_base_m < 0:
            errores.append("La profundidad de cimentación no puede ser negativa.")
        if self.nivel_freatico_m < 0:
            errores.append("La profundidad del nivel freático no puede ser negativa.")
        if not 0 <= self.phi_deg < 90:
            errores.append("El ángulo de rozamiento debe cumplir 0 <= phi < 90 grados.")
        if self.cohesion_kpa < 0:
            errores.append("La cohesión no puede ser negativa.")
        if not 0 <= self.inclinacion_talud_deg < 90:
            errores.append("La inclinación del terreno debe cumplir 0 <= beta < 90 grados.")
        if self.gamma_efectivo_kn_m3 <= 0 or self.gamma_aparente_kn_m3 <= 0:
            errores.append("Los pesos específicos deben ser mayores que cero.")
        if self.considerar_sobrecarga and (self.gamma_sobrecarga_kn_m3 <= 0 or self.altura_sobrecarga_m < 0):
            errores.append("La sobrecarga debe cumplir gamma > 0 y altura >= 0.")
        if self.longitud_corrida_m <= 0:
            errores.append("La longitud equivalente de la zapata corrida debe ser positiva.")
        if self.cu_aumenta_con_profundidad:
            if self.cu_z_final_m <= self.cu_z_inicial_m:
                errores.append("El perfil cu(z) debe tener z1 mayor que z0.")
            if self.cu_inicial_kpa <= 0 or self.cu_final_kpa <= 0:
                errores.append("Los valores cu(z) deben ser positivos.")
            if self.cu_final_kpa < self.cu_inicial_kpa:
                errores.append("La opción 'cu aumenta' requiere cu1 >= cu0.")
            if self.cu_z_final_m > self.cu_z_inicial_m:
                pendiente = (self.cu_final_kpa - self.cu_inicial_kpa)/(self.cu_z_final_m - self.cu_z_inicial_m)
                cu_superficie = self.cu_inicial_kpa - pendiente * self.cu_z_inicial_m
                if cu_superficie <= 0:
                    errores.append("La recta cu(z) debe extrapolar una resistencia c0 positiva en z=0 m.")
        return errores


@dataclass(frozen=True)
class ResultadoAncho:
    ancho_m: float
    hundimiento_cuadrada_mpa: float
    asiento_cuadrada_mpa: float
    servicio_cuadrada_mpa: float
    limitacion_cuadrada: str
    hundimiento_corrida_mpa: float
    asiento_corrida_mpa: float
    servicio_corrida_mpa: float
    limitacion_corrida: str
    espesor_suficiente: bool
    ksp30_cuadrada_mn_m3: float
    ksp30_corrida_mn_m3: float

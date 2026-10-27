from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpcionesGraficas:
    texto_ejes_m: float = 0.18
    nombre_prospeccion_m: float = 0.42
    texto_estratos_m: float = 0.20
    texto_ensayos_m: float = 0.18
    titulo_m: float = 0.65
    separacion_horizontal_m: float = 0.55
    separacion_vertical_ensayos_m: float = 0.28
    separacion_nombre_m: float = 1.00


PRESETS_GRAFICOS: dict[str, OpcionesGraficas] = {
    "Compacta": OpcionesGraficas(
        texto_ejes_m=0.15,
        nombre_prospeccion_m=0.34,
        texto_estratos_m=0.16,
        texto_ensayos_m=0.15,
        titulo_m=0.55,
        separacion_horizontal_m=0.45,
        separacion_vertical_ensayos_m=0.22,
        separacion_nombre_m=0.80,
    ),
    "Normal": OpcionesGraficas(),
    "Ampliada": OpcionesGraficas(
        texto_ejes_m=0.23,
        nombre_prospeccion_m=0.52,
        texto_estratos_m=0.25,
        texto_ensayos_m=0.23,
        titulo_m=0.80,
        separacion_horizontal_m=0.70,
        separacion_vertical_ensayos_m=0.36,
        separacion_nombre_m=1.25,
    ),
}


def validar_opciones_graficas(options: OpcionesGraficas) -> list[str]:
    errors: list[str] = []
    text_values = {
        "Texto de ejes": options.texto_ejes_m,
        "Nombre de prospeccion": options.nombre_prospeccion_m,
        "Texto de estratos": options.texto_estratos_m,
        "Texto de ensayos": options.texto_ensayos_m,
        "Titulo": options.titulo_m,
    }
    for name, value in text_values.items():
        if value <= 0:
            errors.append(f"{name}: el tamano debe ser positivo.")
        elif value > 5:
            errors.append(f"{name}: el tamano supera el limite de 5 m.")
    spacing_values = {
        "Separacion horizontal": options.separacion_horizontal_m,
        "Separacion vertical de ensayos": options.separacion_vertical_ensayos_m,
        "Separacion del nombre": options.separacion_nombre_m,
    }
    for name, value in spacing_values.items():
        if value < 0:
            errors.append(f"{name}: la separacion no puede ser negativa.")
        elif value > 20:
            errors.append(f"{name}: la separacion supera el limite de 20 m.")
    return errors

"""Estructuras de datos serializables del proyecto geologico 2D."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any


@dataclass(slots=True)
class VerticeContacto:
    """Vertice de un contacto en coordenadas de perfil."""

    s_m: float
    z_m: float
    origen: str = "interpretado"
    referencia: str = ""
    interfaz_id: str = ""


@dataclass(slots=True)
class Contacto:
    """Polilinea que separa dos unidades geologicas."""

    contacto_id: str
    nombre: str
    unidad_superior: str
    unidad_inferior: str
    color: str = "#334155"
    vertices: list[VerticeContacto] = field(default_factory=list)
    visible: bool = True
    bloqueado: bool = False
    evidencia: str = "interpretado"
    incertidumbre_m: float = 0.0

    def ordenar(self) -> None:
        """Valida coordenadas conservando el orden topologico de dibujo.

        El nombre del metodo se mantiene por compatibilidad con proyectos 0.1.
        No se ordena por abscisa porque una lente puede volver sobre si misma.
        """
        if any(not math.isfinite(punto.s_m) or not math.isfinite(punto.z_m) for punto in self.vertices):
            raise ValueError(f"El contacto {self.contacto_id} contiene coordenadas no finitas.")


@dataclass(slots=True)
class Proyecto:
    """Metadatos y estado persistente de un perfil."""

    nombre: str = "Perfil geologico - Caso demostrativo"
    localizacion: str = ""
    autor: str = ""
    sistema_referencia: str = "ETRS89 / UTM"
    corredor_m: float = 50.0
    exageracion_vertical: float = 5.0
    contactos: list[Contacto] = field(default_factory=list)
    zonas: list[dict[str, Any]] = field(default_factory=list)
    hipotesis: list[dict[str, Any]] = field(default_factory=list)
    version_formato: str = "1.2"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Proyecto":
        contactos = []
        for bruto in data.get("contactos", []):
            vertices = [
                VerticeContacto(
                    s_m=float(punto["s_m"]),
                    z_m=float(punto["z_m"]),
                    origen=str(punto.get("origen", "interpretado")),
                    referencia=str(punto.get("referencia", "")),
                    interfaz_id=str(punto.get("interfaz_id", "")),
                )
                for punto in bruto.get("vertices", [])
            ]
            contacto = Contacto(
                contacto_id=bruto["contacto_id"],
                nombre=bruto["nombre"],
                unidad_superior=bruto["unidad_superior"],
                unidad_inferior=bruto["unidad_inferior"],
                color=bruto.get("color", "#334155"),
                vertices=vertices,
                visible=bool(bruto.get("visible", True)),
                bloqueado=bool(bruto.get("bloqueado", False)),
                evidencia=str(bruto.get("evidencia", "interpretado")),
                incertidumbre_m=max(0.0, float(bruto.get("incertidumbre_m", 0.0))),
            )
            contacto.ordenar()
            contactos.append(contacto)
        return cls(
            nombre=data.get("nombre", "Perfil geologico"),
            localizacion=data.get("localizacion", ""),
            autor=data.get("autor", ""),
            sistema_referencia=data.get("sistema_referencia", "ETRS89 / UTM"),
            corredor_m=float(data.get("corredor_m", 50.0)),
            exageracion_vertical=float(data.get("exageracion_vertical", 5.0)),
            contactos=contactos,
            zonas=list(data.get("zonas", [])),
            hipotesis=list(data.get("hipotesis", [])),
            version_formato=str(data.get("version_formato", "1.2")),
        )

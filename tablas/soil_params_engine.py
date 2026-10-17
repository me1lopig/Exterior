"""
soil_params_engine.py
======================
Motor de acceso a la base de datos de parámetros del terreno.

Sin dependencia de Streamlit: puede usarse desde la app, desde notebooks o
desde otras herramientas de cálculo. Carga los YAML de ./data/ (uno por
fuente) y ofrece:

    cargar()                      -> dict {fuente_id: documento}
    lista_fuentes()               -> [meta, ...] ordenadas por id
    get_fuente(fuente_id)         -> documento completo (meta/columnas/filas)
    tabla(fuente_id)              -> DataFrame con valores nativos
    tabla_formateada(fuente_id)   -> DataFrame de texto listo para mostrar

Principio de diseño: cada fuente es independiente. El motor NO compara ni
mezcla valores entre documentos.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache

import yaml
import pandas as pd

DIR_DATOS = Path(__file__).resolve().parent / "data"

# --------------------------------------------------------------------------- #
#  Formato de valores                                                          #
# --------------------------------------------------------------------------- #
_SUPER = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
NA = "—"


def fmt_num(x) -> str:
    """Número con coma decimal (es-ES) y sin ceros sobrantes."""
    if x is None:
        return NA
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, int):
        return str(x)
    return f"{x:g}".replace(".", ",")


def fmt_perm(x) -> str:
    """Permeabilidad en notación a·10ⁿ (m/s). Potencias exactas -> 10ⁿ."""
    if x is None:
        return NA
    if x == 0:
        return "0"
    import math
    exp = math.floor(math.log10(abs(x)))
    mant = x / 10 ** exp
    exp_str = str(exp).translate(_SUPER)
    if abs(mant - 1.0) < 1e-9:
        return f"10{exp_str}"
    return f"{mant:g}".replace(".", ",") + f"·10{exp_str}"


def fmt_perm_fuente(x) -> str:
    """Permeabilidad Grundbau, con la mantisa 1 explícita como en la fuente."""
    if x is None:
        return NA
    if x == 0:
        return "0"
    import math
    exp = math.floor(math.log10(abs(x)))
    mant = x / 10 ** exp
    return f"{mant:g}".replace(".", ",") + f"·10{str(exp).translate(_SUPER)}"


def fmt_num_2dec(x) -> str:
    """Número con dos decimales, formato utilizado en columnas Grundbau."""
    if x is None:
        return NA
    return f"{float(x):.2f}".replace(".", ",")


def fmt_valor(valor, tipo: str) -> str:
    """Formatea un valor nativo (número, [min,max], texto o None) según el
    tipo de columna, para su presentación."""
    if valor is None:
        return NA

    if tipo in {"par", "par_2dec", "par_perm"}:
        formatter = {
            "par": fmt_num,
            "par_2dec": fmt_num_2dec,
            "par_perm": fmt_perm_fuente,
        }[tipo]
        if not isinstance(valor, list):
            return str(valor) if isinstance(valor, str) else formatter(valor)
        if len(valor) != 2:
            raise ValueError(f"Un par de fuente debe tener dos valores: {valor!r}")
        superior, inferior = valor
        if superior is None and inferior is None:
            return NA
        return f"{formatter(superior)} / {formatter(inferior)}"

    if tipo == "perm":
        if isinstance(valor, list):
            lo, hi = valor
            if lo is None:
                return f"< {fmt_perm(hi)}"
            if hi is None:
                return f"> {fmt_perm(lo)}"
            return f"{fmt_perm(lo)} – {fmt_perm(hi)}"
        return fmt_perm(valor)

    if tipo == "rango":
        if isinstance(valor, list):
            lo, hi = valor
            if lo is None:
                return f"< {fmt_num(hi)}"
            if hi is None:
                return f"> {fmt_num(lo)}"
            return f"{fmt_num(lo)} – {fmt_num(hi)}"
        return fmt_num(valor)

    if tipo == "num":
        return fmt_num(valor)

    return str(valor)  # text


def encabezado(columna: dict) -> str:
    """Etiqueta de columna con unidad entre corchetes."""
    et = columna["etiqueta"]
    return f"{et} [{columna['unidad']}]" if columna.get("unidad") else et


# --------------------------------------------------------------------------- #
#  Carga de datos                                                              #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def cargar(dir_datos: str | None = None) -> dict:
    base = Path(dir_datos) if dir_datos else DIR_DATOS
    fuentes = {}
    for ruta in base.glob("*.yaml"):
        if ruta.name.startswith("_"):
            continue
        with open(ruta, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        fuentes[doc["meta"]["fuente_id"]] = doc
    if not fuentes:
        raise FileNotFoundError(f"No se encontraron fuentes YAML en {base}")
    return fuentes


def lista_fuentes() -> list[dict]:
    metas = [doc["meta"] for doc in cargar().values()]
    return sorted(metas, key=lambda m: m["id"])


def get_fuente(fuente_id: str) -> dict:
    return cargar()[fuente_id]


def tabla(fuente_id: str) -> pd.DataFrame:
    """DataFrame con los valores nativos (para cálculo o exportación)."""
    doc = get_fuente(fuente_id)
    campos = [c["campo"] for c in doc["columnas"]]
    filas = [{c: fila.get(c) for c in campos} for fila in doc["filas"]]
    return pd.DataFrame(filas, columns=campos)


def tabla_formateada(fuente_id: str) -> pd.DataFrame:
    """DataFrame de texto listo para mostrar (encabezados con unidad)."""
    doc = get_fuente(fuente_id)
    datos = {}
    for col in doc["columnas"]:
        campo, tipo = col["campo"], col["tipo"]
        datos[encabezado(col)] = [fmt_valor(fila.get(campo), tipo)
                                  for fila in doc["filas"]]
    return pd.DataFrame(datos)


if __name__ == "__main__":
    for m in lista_fuentes():
        print(f"[{m['id']}] {m['fuente_id']:<22} {m['nombre']}")
    print()
    print(tabla_formateada("cte_permeabilidad").to_string(index=False))

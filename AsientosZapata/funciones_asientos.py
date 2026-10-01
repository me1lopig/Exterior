"""Motor de cálculo de asientos elásticos de cimentaciones superficiales rectangulares.

Convenciones
------------
* La estratigrafía (DataFrame) se describe desde la SUPERFICIE del terreno.
* D es la profundidad de apoyo de la cimentación medida desde la superficie.
* El nivel freático NF se mide desde la superficie.
* Las profundidades de cálculo z (Steinbrenner, MEF, z_i, z_max) se miden desde
  la COTA DE APOYO hacia abajo.
* Ejes en planta: x según el ancho B, y según la longitud L, origen en el centro.
* p es la presión NETA de trabajo en servicio.
"""
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════
# IMPORTACIÓN OPENSEES
# ══════════════════════════════════════════════════════════════════════════
try:
    import openseespy.opensees as ops
    OPENSEES_DISPONIBLE = True
except ImportError:
    OPENSEES_DISPONIBLE = False

GAMMA_AGUA = 9.81                       # kN/m³
PASO_Z_INFLUENCIA = 0.05                # m
FRACCION_PUNTO_CARACTERISTICO = 0.37    # punto característico en (±0,37·B, ±0,37·L) desde el centro
COLS_MECANICAS = ["Espesor (m)", "E (kPa)", "nu"]

# CTE DB-SE-C, Tabla 2.2 — Valores límite basados en la distorsión angular (1/denominador)
LIMITES_DISTORSION_CTE = {
    "Estructuras isostáticas y muros de contención": 300,
    "Estructuras reticuladas con tabiquería de separación": 500,
    "Estructuras de paneles prefabricados": 700,
    "Muros de carga sin armar con flexión cóncava hacia arriba": 1000,
    "Muros de carga sin armar con flexión cóncava hacia abajo": 2000,
}


class ErrorMEF(RuntimeError):
    """El cálculo MEF no se ha podido ejecutar (OpenSees no disponible o fallo numérico).

    Se lanza en lugar de devolver 0 mm, para que la interfaz no pueda emitir
    un veredicto ELS a partir de un resultado inexistente.
    """


# ══════════════════════════════════════════════════════════════════════════
# ESTRATIGRAFÍA
# ══════════════════════════════════════════════════════════════════════════
def espesor_total(df):
    df_clean = df.dropna(subset=["Espesor (m)"])
    return float(pd.to_numeric(df_clean["Espesor (m)"]).sum())


def estratos_bajo_apoyo(df, D=0.0):
    """Estratigrafía por debajo de la cota de apoyo D (el estrato cortado se recorta)."""
    df_clean = df.dropna(subset=COLS_MECANICAS)
    filas = []
    z = 0.0
    for _, row in df_clean.iterrows():
        h = float(row["Espesor (m)"])
        zt, zb = z, z + h
        z = zb
        if zb <= D + 1e-9:
            continue
        r = row.copy()
        r["Espesor (m)"] = zb - max(zt, D)
        filas.append(r)
    return pd.DataFrame(filas, columns=df_clean.columns).reset_index(drop=True)


def _estratos_entre(df, z_desde, z_hasta):
    """Estratos (desc, h, E, ν) entre dos profundidades medidas desde la superficie."""
    df_clean = df.dropna(subset=COLS_MECANICAS)
    filas = []
    z = 0.0
    for _, row in df_clean.iterrows():
        h = float(row["Espesor (m)"])
        zt, zb = z, z + h
        z = zb
        a, b = max(zt, z_desde), min(zb, z_hasta)
        if b - a > 1e-9:
            filas.append((str(row["Descripción"]), b - a, float(row["E (kPa)"]), min(float(row["nu"]), 0.499)))
    return filas


def validar_estratigrafia(df):
    """Lista de errores de datos (vacía si la estratigrafía es válida)."""
    errores = []
    df_clean = df.dropna(how="all")
    if df_clean.empty:
        return ["La estratigrafía está vacía."]
    for i, row in df_clean.iterrows():
        nombre = row.get("Descripción")
        etiqueta = f"Fila {i + 1}" + (f" ({nombre})" if isinstance(nombre, str) and nombre.strip() else "")
        for col in COLS_MECANICAS + ["Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"]:
            if pd.isna(row.get(col)):
                errores.append(f"{etiqueta}: falta «{col}».")
        if not pd.isna(row.get("Espesor (m)")) and float(row["Espesor (m)"]) <= 0:
            errores.append(f"{etiqueta}: el espesor debe ser positivo.")
        if not pd.isna(row.get("E (kPa)")) and float(row["E (kPa)"]) <= 0:
            errores.append(f"{etiqueta}: E debe ser positivo.")
        if not pd.isna(row.get("nu")) and not (0.0 <= float(row["nu"]) <= 0.5):
            errores.append(f"{etiqueta}: ν debe estar entre 0 y 0,5.")
    return errores


# ══════════════════════════════════════════════════════════════════════════
# TENSIONES DE HOLL (1940) — Compatibles con arrays de NumPy
# Las tensiones horizontales σx, σy de estas expresiones corresponden a ν = 0,5.
# ══════════════════════════════════════════════════════════════════════════
def holl_esquina(p, B, L, z):
    """Incrementos de tensión bajo la ESQUINA de una carga rectangular B×L. Soporta arrays.

    Límite en superficie (z → 0): bajo la esquina σz = σx = σy = p/4.
    """
    z = np.asarray(z, dtype=float)
    z_safe = np.where(z <= 1e-6, 1e-6, z)

    R1 = np.sqrt(L**2 + z_safe**2)
    R2 = np.sqrt(B**2 + z_safe**2)
    R3 = np.sqrt(L**2 + B**2 + z_safe**2)
    arc = np.arctan((B * L) / (z_safe * R3))

    sz = (p / (2*np.pi)) * (arc + B*L*(1/R1**2 + 1/R2**2)*(z_safe/R3))
    sx = (p / (2*np.pi)) * (arc - (B*L*z_safe)/(R1**2*R3))
    sy = (p / (2*np.pi)) * (arc - (B*L*z_safe)/(R2**2*R3))

    sz = np.where(z <= 1e-6, p/4.0, sz)
    sx = np.where(z <= 1e-6, p/4.0, sx)
    sy = np.where(z <= 1e-6, p/4.0, sy)
    return sz, sx, sy


def holl_centro(p, B, L, z):
    """Tensiones bajo el CENTRO: superposición ×4 de cuadrantes B/2 × L/2."""
    sz, sx, sy = holl_esquina(p, B/2.0, L/2.0, z)
    return 4*sz, 4*sx, 4*sy


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 1 — STEINBRENNER
# ══════════════════════════════════════════════════════════════════════════
def phi1(m, n):
    if m == 0:
        t1 = np.log(np.sqrt(1+n**2)+n)
        t2 = n*np.log((np.sqrt(1+n**2)+1)/n)
    else:
        t1 = np.log((np.sqrt(1+m**2+n**2)+n)/np.sqrt(1+m**2))
        t2 = n*np.log((np.sqrt(1+m**2+n**2)+1)/np.sqrt(n**2+m**2))
    return (1/np.pi)*(t1+t2)


def phi2(m, n):
    if m == 0:
        return 0.0
    return (m/(2*np.pi))*np.arctan(n/(m*np.sqrt(1+m**2+n**2)))


def s_z(p, B, E, nu, z, L):
    """Desplazamiento vertical a profundidad z bajo la ESQUINA de un rectángulo B×L
    en un semiespacio elástico homogéneo (E, ν).

    No es un asiento acumulado: el asiento de un estrato entre z1 y z2 se obtiene
    como s_z(z1) − s_z(z2), evaluando ambos términos con el E y ν de ese estrato.
    """
    n = L/B
    m = z/B
    corchete = (1-nu**2)*phi1(m, n) - (1-nu-2*nu**2)*phi2(m, n)
    return (p*B/E)*corchete


def _w_esquina(p, a, b, E, nu, z):
    if a <= 1e-12 or b <= 1e-12:
        return 0.0
    return s_z(p, a, E, nu, z, b)


def w_punto(p, B, L, E, nu, x, y, z):
    """Desplazamiento vertical en (x, y, z) del semiespacio homogéneo bajo una carga p
    sobre el rectángulo B×L centrado en el origen (B según x, L según y).

    Superposición con signo de cuatro rectángulos con vértice común en la vertical
    del punto; válida para puntos dentro y fuera del área cargada.
    """
    def g(a, b):
        return np.sign(a) * np.sign(b) * _w_esquina(p, abs(a), abs(b), E, nu, z)
    xr, xl = B/2.0 - x, -B/2.0 - x
    yt, yb = L/2.0 - y, -L/2.0 - y
    return g(xr, yt) - g(xl, yt) - g(xr, yb) + g(xl, yb)


def punto_caracteristico(B, L):
    """Punto característico (Grasshoff): el asiento de la zapata flexible en él
    coincide aproximadamente con el asiento de la zapata rígida."""
    return FRACCION_PUNTO_CARACTERISTICO * B, FRACCION_PUNTO_CARACTERISTICO * L


def factor_empotramiento_mayne_poulos(B, L, D, nu):
    """Factor de corrección por empotramiento I_E (Mayne y Poulos, 1999).

    I_E = 1 − 1 / [3,5·exp(1,22·ν − 0,4)·(B_e/D + 1,6)],  B_e = √(4·B·L/π)
    """
    if D <= 1e-9:
        return 1.0
    Be = np.sqrt(4.0 * B * L / np.pi)
    return float(1.0 - 1.0 / (3.5 * np.exp(1.22 * nu - 0.4) * (Be / D + 1.6)))


def calcular_steinbrenner(p, B, L, df, z_max, D=0.0, x=0.0, y=0.0, factor=1.0):
    """Asiento elástico de zapata flexible en el punto (x, y) por Steinbrenner multicapa.

    z_max se mide desde la cota de apoyo D. Las columnas w_techo / w_base son valores
    AUXILIARES (desplazamiento del semiespacio homogéneo con el E y ν del estrato);
    solo su diferencia tiene significado. Δs incluye el factor de corrección `factor`.
    Las columnas m y φ solo se incluyen cuando el punto es el centro.
    """
    df_bajo = estratos_bajo_apoyo(df, D)
    en_centro = abs(x) < 1e-12 and abs(y) < 1e-12
    n_factor = L / B

    total = 0.0
    resultados = []
    z_actual = 0.0
    for _, row in df_bajo.iterrows():
        if z_actual >= z_max - 1e-9:
            break
        h_i = float(row["Espesor (m)"])
        E_i = float(row["E (kPa)"])
        nu_i = float(row["nu"])
        z_techo = z_actual
        z_base = min(z_actual + h_i, z_max)

        w_t = w_punto(p, B, L, E_i, nu_i, x, y, z_techo)
        w_b = w_punto(p, B, L, E_i, nu_i, x, y, z_base)
        ds = factor * (w_t - w_b)
        total += ds

        fila = {"Capa": str(row["Descripción"]),
                "z Techo [m]": round(z_techo, 3),
                "z Base [m]": round(z_base, 3)}
        if en_centro:
            m_t, m_b = z_techo / (B/2), z_base / (B/2)
            fila.update({"m_techo": round(m_t, 4),
                         "φ1_techo": round(phi1(m_t, n_factor), 4),
                         "φ2_techo": round(phi2(m_t, n_factor), 4)})
        fila["w_techo [mm]"] = round(w_t*1000, 3)
        if en_centro:
            fila.update({"m_base": round(m_b, 4),
                         "φ1_base": round(phi1(m_b, n_factor), 4),
                         "φ2_base": round(phi2(m_b, n_factor), 4)})
        fila["w_base [mm]"] = round(w_b*1000, 3)
        fila["Δs [mm]"] = round(ds*1000, 3)
        resultados.append(fila)
        z_actual = z_base

    return total, pd.DataFrame(resultados)


@dataclass
class ResultadoSteinbrenner:
    total: float                    # m
    tabla: pd.DataFrame
    rigida: bool
    punto: tuple                    # (x, y) evaluado
    I_E: float
    total_sin_correccion: float     # m


def calcular_steinbrenner_zapata(p, B, L, df, z_max, D=0.0, rigida=False, empotramiento=False):
    """Steinbrenner para zapata flexible (centro) o rígida (punto característico),
    con corrección opcional por empotramiento (Mayne y Poulos, 1999)."""
    x, y = punto_caracteristico(B, L) if rigida else (0.0, 0.0)
    I_E = 1.0
    if empotramiento and D > 0:
        df_bajo = estratos_bajo_apoyo(df, D)
        nu_ref = float(df_bajo["nu"].iloc[0]) if not df_bajo.empty else 0.3
        I_E = factor_empotramiento_mayne_poulos(B, L, D, nu_ref)
    total0, _ = calcular_steinbrenner(p, B, L, df, z_max, D, x, y, 1.0)
    total, tabla = calcular_steinbrenner(p, B, L, df, z_max, D, x, y, I_E)
    return ResultadoSteinbrenner(total, tabla, rigida, (x, y), I_E, total0)


def asiento_steinbrenner_punto(p, B, L, df, z_max, D, x, y):
    """Asiento (m) de la zapata flexible en un punto cualquiera (x, y) de la cota de apoyo."""
    return calcular_steinbrenner(p, B, L, df, z_max, D, x, y)[0]


def puntos_notables(B, L):
    return {
        "Centro": (0.0, 0.0),
        "Punto medio del lado largo": (B/2.0, 0.0),
        "Punto medio del lado corto": (0.0, L/2.0),
        "Esquina": (B/2.0, L/2.0),
    }


def asientos_puntos_steinbrenner(p, B, L, df, z_max, D, res_st):
    """Asientos (mm) de Steinbrenner en los puntos notables de la zapata."""
    out = {}
    for nombre, (x, y) in puntos_notables(B, L).items():
        if res_st.rigida:
            out[nombre] = res_st.total * 1000.0
        else:
            out[nombre] = asiento_steinbrenner_punto(p, B, L, df, z_max, D, x, y) * res_st.I_E * 1000.0
    return out


def perfil_steinbrenner(p, B, L, df, z_max, D, coords, eje, res_st):
    """Asientos (mm) a la cota de apoyo a lo largo del eje 'x' o 'y' por el centro.
    Bajo una zapata rígida el asiento es uniforme; fuera de ella se usa la solución flexible."""
    medio = B/2.0 if eje == "x" else L/2.0
    vals = []
    for c in coords:
        x, y = (c, 0.0) if eje == "x" else (0.0, c)
        if abs(c) <= medio + 1e-9:
            if res_st.rigida:
                vals.append(res_st.total * 1000.0)
            else:
                vals.append(asiento_steinbrenner_punto(p, B, L, df, z_max, D, x, y) * res_st.I_E * 1000.0)
        else:
            vals.append(asiento_steinbrenner_punto(p, B, L, df, z_max, D, x, y) * 1000.0)
    return np.array(vals)


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 2 — OPENSEES 3D (bbarBrick, cuarto de dominio, base rígida)
# ══════════════════════════════════════════════════════════════════════════
def _grid_1d_3d(longitud, borde, mesh):
    n = max(1, int(round(longitud / mesh)))
    base = np.linspace(0.0, longitud, n + 1)
    coords = np.union1d(base, [0.0, borde, longitud])
    coords = coords[np.concatenate(([True], np.diff(coords) > 1e-9))]
    return coords


def _coords_graduadas(longitud_fina, longitud_total, h0, ratio, h_max):
    """0 → longitud_fina con tamaño uniforme ≤ h0; después crecimiento geométrico
    (razón `ratio`, tope h_max) hasta longitud_total."""
    longitud_fina = min(longitud_fina, longitud_total)
    n = max(1, int(np.ceil(longitud_fina / h0 - 1e-9)))
    c = list(np.linspace(0.0, longitud_fina, n + 1))
    h = longitud_fina / n
    pos = longitud_fina
    while pos < longitud_total - 1e-9:
        h = min(h * ratio, h_max)
        if pos + 1.5 * h >= longitud_total:
            pos = longitud_total
        else:
            pos += h
        c.append(pos)
    return np.array(c)


def _z_coords_3d(espesores, mesh):
    z = [0.0]
    z_act = 0.0
    for h in espesores:
        n_sub = max(1, int(round(h / mesh)))
        for s in range(1, n_sub + 1):
            z.append(z_act - h * s / n_sub)
        z_act -= h
    z = np.array(z, dtype=float)
    z = z[np.concatenate(([True], np.diff(z) < -1e-9))]
    return z


def _profundidades_graduadas(espesores, h0, ratio, h_max, fino):
    """Profundidades (positivas, desde la cota de apoyo) graduadas que respetan las interfaces."""
    interfaces = np.concatenate(([0.0], np.cumsum(espesores)))
    fondo = interfaces[-1]
    base = _coords_graduadas(fino, fondo, h0, ratio, h_max)
    puntos = list(interfaces)
    for i in range(1, len(base) - 1):
        zb = base[i]
        h_loc = 0.5 * (base[i + 1] - base[i - 1])
        if np.min(np.abs(interfaces - zb)) >= 0.35 * h_loc:
            puntos.append(zb)
    return np.unique(np.round(puntos, 9))


def _tributarias_1d_3d(coords, borde_cargado):
    n = len(coords)
    trib = np.zeros(n)
    for i in range(n):
        izq = 0.0 if i == 0 else 0.5 * (coords[i - 1] + coords[i])
        der = coords[i] if i == n - 1 else 0.5 * (coords[i] + coords[i + 1])
        lo = max(izq, 0.0)
        hi = min(der, borde_cargado)
        trib[i] = max(0.0, hi - lo)
    return trib


def _estratos_truncados(df, z_max):
    """Estratos (desc, h, E, ν) desde el techo del DataFrame hasta z_max."""
    df_clean = df.dropna(subset=COLS_MECANICAS)
    filas = []
    z = 0.0
    for _, row in df_clean.iterrows():
        if z >= z_max - 1e-9:
            break
        h = float(row["Espesor (m)"])
        h_ef = min(z + h, z_max) - z
        if h_ef <= 1e-9:
            break
        nu = min(float(row["nu"]), 0.499)
        filas.append((str(row["Descripción"]), h_ef, float(row["E (kPa)"]), nu))
        z += h
    return filas


def _estratos_extendidos_mef(df, z_max, factor_prof):
    df_clean = df.dropna(subset=COLS_MECANICAS)
    filas = []
    z = 0.0
    z_max_mef = z_max * factor_prof
    last_E, last_nu, last_desc = None, None, None
    for _, row in df_clean.iterrows():
        if z >= z_max_mef - 1e-9:
            break
        h = float(row["Espesor (m)"])
        h_ef = min(z + h, z_max_mef) - z
        if h_ef > 1e-9:
            nu = min(float(row["nu"]), 0.499)
            filas.append((str(row["Descripción"]), h_ef, float(row["E (kPa)"]), nu))
        z += h
        last_E, last_nu, last_desc = float(row["E (kPa)"]), min(float(row["nu"]), 0.499), str(row["Descripción"])
    if z < z_max_mef - 1e-9 and last_E is not None:
        filas.append((last_desc + " (Extensión FEM)", z_max_mef - z, last_E, last_nu))
    return filas


@dataclass
class MallaMEF:
    x: np.ndarray            # coordenadas en planta (≥ 0)
    y: np.ndarray
    z: np.ndarray            # cotas absolutas (0 = superficie, negativas hacia abajo)
    k_apoyo: int             # índice de la cota de apoyo en z
    estratos: list           # (desc, h, E, ν) de arriba abajo, desde la superficie
    mat_elem: np.ndarray     # material por capa de elementos (1-based)
    activo: np.ndarray       # (nx-1, ny-1, nz-1) bool: elemento presente
    nodo_usado: np.ndarray   # (nx, ny, nz) bool

    @property
    def n_nodos(self):
        return int(self.nodo_usado.sum())

    @property
    def n_elementos(self):
        return int(self.activo.sum())


def construir_malla_3d(B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=1.0, D=0.0,
                       graduada=True, ratio=1.3, tamaño_max=2.0):
    """Malla MEF de un cuarto de dominio. Única fuente de verdad para el cálculo y para la
    estimación de tamaño de malla de la interfaz.

    Si D > 0 se modela el terreno lateral por encima de la cota de apoyo y se vacía la
    excavación ocupada por la zapata (x < B/2, y < L/2, z > −D).
    """
    df_bajo = estratos_bajo_apoyo(df, D)
    estratos_sup = _estratos_entre(df, 0.0, D) if D > 1e-9 else []
    estratos_inf = _estratos_extendidos_mef(df_bajo, z_max, factor_prof)
    estratos = estratos_sup + estratos_inf
    esp_sup = np.array([h for (_, h, _, _) in estratos_sup], dtype=float)
    esp_inf = np.array([h for (_, h, _, _) in estratos_inf], dtype=float)

    borde_x, borde_y = B / 2.0, L / 2.0
    ext_x, ext_y = borde_x * factor_dominio, borde_y * factor_dominio
    if graduada:
        x = _coords_graduadas(borde_x, ext_x, tamaño_malla, ratio, tamaño_max)
        y = _coords_graduadas(borde_y, ext_y, tamaño_malla, ratio, tamaño_max)
        prof_inf = _profundidades_graduadas(esp_inf, tamaño_malla, ratio, tamaño_max, fino=max(B / 2.0, tamaño_malla))
    else:
        x = _grid_1d_3d(ext_x, borde_x, tamaño_malla)
        y = _grid_1d_3d(ext_y, borde_y, tamaño_malla)
        prof_inf = -_z_coords_3d(esp_inf, tamaño_malla)
    prof_sup = -_z_coords_3d(esp_sup, tamaño_malla) if len(esp_sup) else np.array([0.0])
    z = np.concatenate((-prof_sup, -(D + prof_inf[1:])))
    k_apoyo = len(prof_sup) - 1

    # Material de cada capa de elementos
    cumz = np.concatenate(([0.0], -np.cumsum([h for (_, h, _, _) in estratos])))
    z_med = 0.5 * (z[:-1] + z[1:])
    mat_elem = np.ones(len(z_med), dtype=int)
    for k, zm in enumerate(z_med):
        for m in range(len(estratos)):
            if cumz[m + 1] - 1e-9 <= zm <= cumz[m] + 1e-9:
                mat_elem[k] = m + 1
                break

    # Elementos activos (excavación vaciada) y nodos usados
    xc, yc = 0.5 * (x[:-1] + x[1:]), 0.5 * (y[:-1] + y[1:])
    XC, YC, ZC = np.meshgrid(xc, yc, z_med, indexing="ij")
    activo = ~((XC < borde_x) & (YC < borde_y) & (ZC > -D))
    nodo_usado = np.zeros((len(x), len(y), len(z)), dtype=bool)
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                nodo_usado[di:di + activo.shape[0], dj:dj + activo.shape[1], dk:dk + activo.shape[2]] |= activo
    return MallaMEF(x, y, z, k_apoyo, estratos, mat_elem, activo, nodo_usado)


def dimensiones_malla_3d(B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=1.0, D=0.0,
                         graduada=True, ratio=1.3, tamaño_max=2.0):
    """Devuelve (nº nodos, nº elementos) del modelo que se va a resolver."""
    m = construir_malla_3d(B, L, df, z_max, tamaño_malla, factor_dominio, factor_prof, D,
                           graduada, ratio, tamaño_max)
    return m.n_nodos, m.n_elementos


@dataclass
class ResultadoMEF:
    total: float                       # m, s(apoyo) − s(z_max) en el eje
    tabla: pd.DataFrame                # Δs por estrato bajo la cota de apoyo
    perfil_x: pd.DataFrame             # asientos a la cota de apoyo según x (y = 0)
    perfil_y: pd.DataFrame             # asientos a la cota de apoyo según y (x = 0)
    puntos: dict                       # asientos (mm) en los puntos notables
    rigida: bool
    n_nodos: int
    n_elementos: int
    tiempo: float                      # s
    extension_x: float                 # m
    extension_y: float                 # m
    parametros: dict = field(default_factory=dict)


def calcular_opensees_3d(p, B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=1.0, D=0.0,
                         rigida=False, graduada=True, ratio=1.3, tamaño_max=2.0):
    """Asiento elástico mediante MEF 3D (cuarto de dominio, base rígida rugosa en z_max).

    * Zapata flexible: presión uniforme repartida en fuerzas nodales.
    * Zapata rígida (y lisa): los nodos cargados comparten el desplazamiento vertical (equalDOF).
    * Empotramiento D > 0: terreno lateral modelado y excavación vaciada; la carga se aplica a la
      cota de apoyo.

    El asiento devuelto es s(apoyo) − s(z_max) en el eje, igual a la suma de la tabla por estratos.
    Lanza ErrorMEF si OpenSees no está disponible o el análisis no converge.
    """
    if not OPENSEES_DISPONIBLE:
        raise ErrorMEF("OpenSeesPy no está instalado: el cálculo MEF no se ha ejecutado.")

    t0 = time.perf_counter()
    estratos_reporte = _estratos_truncados(estratos_bajo_apoyo(df, D), z_max)
    if not estratos_reporte:
        raise ErrorMEF("La estratigrafía no contiene estratos válidos bajo la cota de apoyo hasta z_max.")

    malla = construir_malla_3d(B, L, df, z_max, tamaño_malla, factor_dominio, factor_prof, D,
                               graduada, ratio, tamaño_max)
    x_c, y_c, z_c = malla.x, malla.y, malla.z
    nx, ny, nz = len(x_c), len(y_c), len(z_c)
    kb = malla.k_apoyo
    borde_x, borde_y = B / 2.0, L / 2.0

    def nid(i, j, k):
        return int(k * (nx * ny) + j * nx + i + 1)

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 3)
    for pos, (_, _, E_kPa, nu) in enumerate(malla.estratos):
        ops.nDMaterial("ElasticIsotropic", pos + 1, E_kPa, nu)

    usados = np.argwhere(malla.nodo_usado)
    for i, j, k in usados:
        ops.node(nid(i, j, k), float(x_c[i]), float(y_c[j]), float(z_c[k]))

    # Base rígida empotrada; planos de simetría y fronteras lejanas con deslizadera
    for i, j, k in usados:
        t = nid(i, j, k)
        if k == nz - 1:
            ops.fix(t, 1, 1, 1)
        else:
            fx = 1 if (i == 0 or i == nx - 1) else 0
            fy = 1 if (j == 0 or j == ny - 1) else 0
            if fx or fy:
                ops.fix(t, fx, fy, 0)

    el = 1
    for i, j, k in np.argwhere(malla.activo):
        n1 = nid(i, j, k+1);     n2 = nid(i+1, j, k+1)
        n3 = nid(i+1, j+1, k+1); n4 = nid(i, j+1, k+1)
        n5 = nid(i, j, k);       n6 = nid(i+1, j, k)
        n7 = nid(i+1, j+1, k);   n8 = nid(i, j+1, k)
        ops.element("bbarBrick", el, n1, n2, n3, n4, n5, n6, n7, n8, int(malla.mat_elem[k]))
        el += 1

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    trib_x = _tributarias_1d_3d(x_c, borde_x)
    trib_y = _tributarias_1d_3d(y_c, borde_y)
    master = nid(0, 0, kb)
    for j in range(ny):
        for i in range(nx):
            area = trib_x[i] * trib_y[j]
            if area > 0.0:
                ops.load(nid(i, j, kb), 0.0, 0.0, -float(p * area))
                if rigida and nid(i, j, kb) != master:
                    ops.equalDOF(master, nid(i, j, kb), 3)

    ops.system("UmfPack")
    ops.numberer("RCM")
    ops.constraints("Transformation" if rigida else "Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    if ops.analyze(1) != 0:
        ops.wipe()
        raise ErrorMEF("El análisis MEF no ha convergido (fallo numérico en OpenSees).")

    def s_mm(i, j, k):
        return abs(ops.nodeDisp(nid(i, j, k), 3)) * 1000.0

    # Eje central bajo la cota de apoyo
    prof = np.array([-z_c[k] - D for k in range(kb, nz)])
    s_eje = np.array([s_mm(0, 0, k) for k in range(kb, nz)])

    # Perfiles a la cota de apoyo
    perfil_x = pd.DataFrame({"x [m]": x_c, "s [mm]": [s_mm(i, 0, kb) for i in range(nx)]})
    perfil_y = pd.DataFrame({"y [m]": y_c, "s [mm]": [s_mm(0, j, kb) for j in range(ny)]})
    ib = int(np.argmin(np.abs(x_c - borde_x)))
    jb = int(np.argmin(np.abs(y_c - borde_y)))
    puntos = {
        "Centro": s_mm(0, 0, kb),
        "Punto medio del lado largo": s_mm(ib, 0, kb),
        "Punto medio del lado corto": s_mm(0, jb, kb),
        "Esquina": s_mm(ib, jb, kb),
    }
    n_nodos, n_elem = malla.n_nodos, malla.n_elementos
    ops.wipe()

    interfaces = [0.0]
    z = 0.0
    for (_, h, _, _) in estratos_reporte:
        z += h
        interfaces.append(z)
    s_interp = np.interp(interfaces, prof, s_eje)

    filas = [{"Capa": nombre, "Δs [mm]": round(float(s_interp[idx] - s_interp[idx + 1]), 3)}
             for idx, (nombre, _, _, _) in enumerate(estratos_reporte)]
    total_m = float(s_interp[0] - s_interp[-1]) / 1000.0
    parametros = {"tamaño_malla": tamaño_malla, "factor_dominio": factor_dominio, "factor_prof": factor_prof,
                  "graduada": graduada, "ratio": ratio, "tamaño_max": tamaño_max, "D": D}
    return ResultadoMEF(total_m, pd.DataFrame(filas), perfil_x, perfil_y, puntos, rigida, n_nodos, n_elem,
                        time.perf_counter() - t0, float(x_c[-1]), float(y_c[-1]), parametros)


# ══════════════════════════════════════════════════════════════════════════
# DISTORSIÓN ANGULAR (CTE DB-SE-C, 2.4.3)
# ══════════════════════════════════════════════════════════════════════════
def distorsion_angular(s_propio_mm, s_inducido_mm, s_vecino_mm, distancia_m):
    """Asiento diferencial (mm) y distorsión angular β entre el centro de la zapata y un
    elemento vecino situado a `distancia_m` entre ejes.

    El asiento del vecino es su asiento propio más el inducido por esta zapata. No se
    incluye el asiento que el vecino induce sobre esta zapata.
    """
    ds = abs(s_propio_mm - (s_vecino_mm + s_inducido_mm))
    return ds, ds / (distancia_m * 1000.0)


# ══════════════════════════════════════════════════════════════════════════
# TENSIÓN EFECTIVA Y ZONA DE INFLUENCIA
# ══════════════════════════════════════════════════════════════════════════
def sigma_v0(z, df, NF):
    """Tensión vertical efectiva geostática a la profundidad z medida desde la SUPERFICIE."""
    df_clean = df.dropna(subset=["Espesor (m)", "Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"])
    sv = 0.0
    z_act = 0.0
    for _, row in df_clean.iterrows():
        h = float(row["Espesor (m)"])
        g = float(row["Peso Esp. (kN/m³)"])
        gs = float(row["Peso Esp. Sat (kN/m³)"])
        zt = z_act
        zb = z_act + h
        if z <= zt:
            break
        ze = min(z, zb)
        z_sec_b = min(ze, NF)
        if z_sec_b > zt:
            sv += g*(z_sec_b-zt)
        z_sat_t = max(zt, NF)
        if ze > z_sat_t:
            sv += (gs-GAMMA_AGUA)*(ze-z_sat_t)
        z_act = zb
    return sv


def z_influencia_ec7(p, B, L, df, NF, D=0.0):
    """Profundidad bajo la cota de apoyo en la que Δσz (centro) ≤ 0,20·σ′v0 (UNE-EN 1997-1, 6.6.2).

    σ′v0 incluye las tierras situadas por encima de la cota de apoyo.
    """
    df_clean = df.dropna(subset=["Espesor (m)"])
    et = espesor_total(df_clean) - D
    k = 1
    while k * PASO_Z_INFLUENCIA <= et + 1e-9:
        z = round(k * PASO_Z_INFLUENCIA, 2)
        dsz, _, _ = holl_centro(p, B, L, z)
        sv = sigma_v0(D + z, df_clean, NF)
        if sv > 0 and dsz <= 0.20*sv:
            return z
        k += 1
    return round(max(et, 0.0), 2)

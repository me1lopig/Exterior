<<<<<<< HEAD
"""
Motor de cálculo de asientos elásticos de cimentaciones rectangulares.

Convenciones
------------
- z: profundidad medida desde la BASE de la zapata (los estratos empiezan ahí).
- D: profundidad de cimentación, medida desde la superficie del terreno.
- NF: profundidad del nivel freático, medida desde la superficie del terreno.
  (Con D = 0 ambas referencias coinciden, como en versiones anteriores.)
- p: presión NETA de trabajo [kPa]. Unidades: m, kPa, kN/m³.
- Asientos en el CENTRO de un área cargada flexible.
"""
import time
=======
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
>>>>>>> refs/remotes/origin/main

import numpy as np
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════
# IMPORTACIÓN OPENSEES
# ══════════════════════════════════════════════════════════════════════════
try:
    import openseespy.opensees as ops
    OPENSEES_DISPONIBLE = True
<<<<<<< HEAD
except ImportError:  # pragma: no cover - depende del entorno
    ops = None
    OPENSEES_DISPONIBLE = False

GAMMA_AGUA = 9.81        # kN/m³
NU_MAX = 0.499           # tope común de ν para TODOS los métodos
MAX_NODOS_MEF = 20000    # por encima, el solver directo puede agotar la memoria o tardar minutos
SOLVERS_MEF = ("Mumps", "UmfPack")
TIPOS_SUELO = ["Granular", "Cohesivo", "Roca"]

COLS_NUM = ["Espesor (m)", "E (kPa)", "nu", "Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"]


class MEFError(RuntimeError):
    """El modelo de elementos finitos no ha podido resolverse."""


# ══════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE LA ESTRATIGRAFÍA
# ══════════════════════════════════════════════════════════════════════════
def validar_estratigrafia(df):
    """Limpia y valida la tabla de estratos.

    Devuelve (df_limpio, errores, avisos). Con errores no debe calcularse.
    - Elimina filas completamente vacías (típicas del data_editor dinámico).
    - ν ≥ 0,5 se recorta a NU_MAX (aviso); ν fuera de [0, 0,5] es error.
    """
    errores, avisos = [], []
    d = df.copy()
    for col in ["Descripción"] + COLS_NUM:
        if col not in d.columns:
            errores.append(f"Falta la columna «{col}».")
    if errores:
        return d, errores, avisos
    if "Tipo" not in d.columns:
        d["Tipo"] = None

    for col in COLS_NUM:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    desc = d["Descripción"].fillna("").astype(str).str.strip()
    vacia = d[COLS_NUM].isna().all(axis=1) & (desc == "")
    d = d.loc[~vacia].reset_index(drop=True)
    desc = d["Descripción"].fillna("").astype(str).str.strip()

    if d.empty:
        errores.append("La estratigrafía no tiene ningún estrato.")
        return d, errores, avisos

    for i in range(len(d)):
        n = i + 1
        if desc.iloc[i] == "":
            d.at[i, "Descripción"] = f"Estrato {n}"
        nombre = d.at[i, "Descripción"]
        faltan = [c for c in COLS_NUM if pd.isna(d.at[i, c])]
        if faltan:
            errores.append(f"«{nombre}»: faltan valores o no son numéricos ({', '.join(faltan)}).")
            continue
        h, E, nu = d.at[i, "Espesor (m)"], d.at[i, "E (kPa)"], d.at[i, "nu"]
        g, gs = d.at[i, "Peso Esp. (kN/m³)"], d.at[i, "Peso Esp. Sat (kN/m³)"]
        if h <= 0:
            errores.append(f"«{nombre}»: el espesor debe ser > 0.")
        if E <= 0:
            errores.append(f"«{nombre}»: E debe ser > 0.")
        if nu < 0 or nu > 0.5:
            errores.append(f"«{nombre}»: ν debe estar en [0; 0,5].")
        elif nu > NU_MAX:
            d.at[i, "nu"] = NU_MAX
            avisos.append(f"«{nombre}»: ν = {nu:g} se limita a {NU_MAX} en todos los métodos.")
        if g <= 0:
            errores.append(f"«{nombre}»: el peso específico debe ser > 0.")
        if gs <= GAMMA_AGUA:
            errores.append(f"«{nombre}»: γsat debe ser mayor que γw = {GAMMA_AGUA} kN/m³.")
        elif gs < g:
            avisos.append(f"«{nombre}»: γsat < γ natural; revisa los pesos específicos.")
        tipo = d.at[i, "Tipo"]
        if tipo not in TIPOS_SUELO:
            d.at[i, "Tipo"] = "Cohesivo"
            avisos.append(f"«{nombre}»: tipo de terreno no indicado; se asume «Cohesivo» (lado seguro en ELS).")
    return d, errores, avisos


def _capas(df):
    """Lista de tuplas (nombre, h, E, ν, γ, γsat) con ν limitado a NU_MAX."""
    return [(str(r["Descripción"]), float(r["Espesor (m)"]), float(r["E (kPa)"]),
             min(float(r["nu"]), NU_MAX), float(r["Peso Esp. (kN/m³)"]),
             float(r["Peso Esp. Sat (kN/m³)"]))
            for _, r in df.iterrows()]


def _truncar(df, z_max):
    """Estratos recortados a z_max: lista de (nombre, z_techo, z_base, E, ν)."""
    out, z = [], 0.0
    for (nombre, h, E, nu, _, _) in _capas(df):
        if z >= z_max - 1e-9:
            break
        z_b = min(z + h, z_max)
        if z_b - z > 1e-9:
            out.append((nombre, z, z_b, E, nu))
        z += h
    return out


# ══════════════════════════════════════════════════════════════════════════
# TENSIONES BAJO CARGA RECTANGULAR UNIFORME
# ══════════════════════════════════════════════════════════════════════════
def holl_esquina(p, B, L, z):
    """Tensiones de Holl (1940) bajo la ESQUINA de una carga rectangular B×L.

    σz es válida para cualquier ν. Las expresiones de σx y σy corresponden a
    un medio incompresible (ν = 0,5). Soporta arrays; en z → 0 tiende a p/4.
    """
    z = np.asarray(z, dtype=float)
    zs = np.maximum(z, 1e-9)
    R1 = np.sqrt(L**2 + zs**2)
    R2 = np.sqrt(B**2 + zs**2)
    R3 = np.sqrt(L**2 + B**2 + zs**2)
    arc = np.arctan((B * L) / (zs * R3))
    sz = (p / (2*np.pi)) * (arc + B*L*(1/R1**2 + 1/R2**2) * (zs/R3))
    sx = (p / (2*np.pi)) * (arc - (B*L*zs) / (R1**2 * R3))
    sy = (p / (2*np.pi)) * (arc - (B*L*zs) / (R2**2 * R3))
=======
except ImportError:
    OPENSEES_DISPONIBLE = False

GAMMA_AGUA = 9.81                       # kN/m³
PASO_Z_INFLUENCIA = 0.05                # m
FRACCION_PUNTO_CARACTERISTICO = 0.37    # aproximación clásica de Grasshoff; exacta solo en casos particulares
NU_MAX_CALCULO = 0.499                  # evita la singularidad de la elasticidad isotrópica en ν = 0,5
COLS_MECANICAS = ["Espesor (m)", "E (kPa)", "nu"]

class ErrorMEF(RuntimeError):
    """El cálculo MEF no se ha podido ejecutar (OpenSees no disponible o fallo numérico).

    Se lanza en lugar de devolver 0 mm, para que la interfaz no pueda emitir
    un veredicto ELS a partir de un resultado inexistente.
    """


# ══════════════════════════════════════════════════════════════════════════
# ESTRATIGRAFÍA
# ══════════════════════════════════════════════════════════════════════════
def normalizar_nu(nu):
    """Devuelve el ν de cálculo; la entrada ν = 0,5 se evalúa como 0,499."""
    return min(float(nu), NU_MAX_CALCULO)


def normalizar_estratigrafia(df):
    """Copia de la estratigrafía con ν normalizado de forma uniforme."""
    out = df.copy()
    if "nu" in out:
        out["nu"] = pd.to_numeric(out["nu"], errors="coerce").map(
            lambda value: normalizar_nu(value) if pd.notna(value) else value
        )
    return out


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
            filas.append((str(row["Descripción"]), b - a, float(row["E (kPa)"]), normalizar_nu(row["nu"])))
    return filas


def validar_estratigrafia(df):
    """Lista de errores de datos (vacía si la estratigrafía es válida)."""
    errores = []
    df_clean = df.dropna(how="all")
    if df_clean.empty:
        return ["La estratigrafía está vacía."]
    columnas_numericas = COLS_MECANICAS + ["Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"]
    faltantes = [col for col in ["Descripción"] + columnas_numericas if col not in df_clean.columns]
    if faltantes:
        return ["Faltan columnas obligatorias: " + ", ".join(faltantes) + "."]
    for i, row in df_clean.iterrows():
        nombre = row.get("Descripción")
        etiqueta = f"Fila {i + 1}" + (f" ({nombre})" if isinstance(nombre, str) and nombre.strip() else "")
        valores = {}
        for col in columnas_numericas:
            try:
                valor = float(row.get(col))
            except (TypeError, ValueError):
                valor = np.nan
            valores[col] = valor
            if not np.isfinite(valor):
                errores.append(f"{etiqueta}: falta «{col}» o no es un número finito.")
        if np.isfinite(valores["Espesor (m)"]) and valores["Espesor (m)"] <= 0:
            errores.append(f"{etiqueta}: el espesor debe ser positivo.")
        if np.isfinite(valores["E (kPa)"]) and valores["E (kPa)"] <= 0:
            errores.append(f"{etiqueta}: E debe ser positivo.")
        if np.isfinite(valores["nu"]) and not (0.0 <= valores["nu"] <= 0.5):
            errores.append(f"{etiqueta}: ν debe estar entre 0 y 0,5.")
        for col in ["Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"]:
            if np.isfinite(valores[col]) and valores[col] <= 0:
                errores.append(f"{etiqueta}: «{col}» debe ser positivo.")
        gs = valores["Peso Esp. Sat (kN/m³)"]
        if np.isfinite(gs) and gs <= GAMMA_AGUA:
            errores.append(f"{etiqueta}: el peso específico saturado debe superar γw = {GAMMA_AGUA:.2f} kN/m³.")
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
>>>>>>> refs/remotes/origin/main
    return sz, sx, sy


def holl_centro(p, B, L, z):
<<<<<<< HEAD
    """Tensiones de Holl bajo el CENTRO: superposición ×4 de cuadrantes B/2 × L/2."""
=======
    """Tensiones bajo el CENTRO: superposición ×4 de cuadrantes B/2 × L/2."""
>>>>>>> refs/remotes/origin/main
    sz, sx, sy = holl_esquina(p, B/2.0, L/2.0, z)
    return 4*sz, 4*sx, 4*sy


<<<<<<< HEAD
def suma_horizontal_esquina(p, B, L, z, nu):
    """Δσx + Δσy bajo la esquina, EXACTA para ν arbitrario.

    De Boussinesq: θ = σx+σy+σz = (1+ν)·P·z/(π·R³); integrada sobre el
    rectángulo, ∫∫ z/R³ dA = arctan(BL/(z·R3)). Por tanto
    σx + σy = (1+ν)·(p/π)·arctan(BL/(z·R3)) − σz.
    Para ν = 0,5 coincide con la suma de las expresiones de Holl.
    """
    z = np.asarray(z, dtype=float)
    zs = np.maximum(z, 1e-9)
    R3 = np.sqrt(L**2 + B**2 + zs**2)
    arc = np.arctan((B * L) / (zs * R3))
    sz, _, _ = holl_esquina(p, B, L, z)
    return (1.0 + nu) * (p / np.pi) * arc - sz


def suma_horizontal_centro(p, B, L, z, nu):
    """Δσx + Δσy exacta (ν arbitrario) bajo el centro."""
    return 4 * suma_horizontal_esquina(p, B/2.0, L/2.0, z, nu)


=======
>>>>>>> refs/remotes/origin/main
# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 1 — STEINBRENNER
# ══════════════════════════════════════════════════════════════════════════
def phi1(m, n):
    if m == 0:
<<<<<<< HEAD
        t1 = np.log(np.sqrt(1+n**2) + n)
        t2 = n*np.log((np.sqrt(1+n**2) + 1)/n)
    else:
        t1 = np.log((np.sqrt(1+m**2+n**2) + n)/np.sqrt(1+m**2))
        t2 = n*np.log((np.sqrt(1+m**2+n**2) + 1)/np.sqrt(n**2+m**2))
    return (1/np.pi)*(t1 + t2)


def phi2(m, n):
    """Factor φ₂ = (m/2π)·arctan[n/(m·√(1+m²+n²))] (Bowles, I₂)."""
=======
        t1 = np.log(np.sqrt(1+n**2)+n)
        t2 = n*np.log((np.sqrt(1+n**2)+1)/n)
    else:
        t1 = np.log((np.sqrt(1+m**2+n**2)+n)/np.sqrt(1+m**2))
        t2 = n*np.log((np.sqrt(1+m**2+n**2)+1)/np.sqrt(n**2+m**2))
    return (1/np.pi)*(t1+t2)


def phi2(m, n):
>>>>>>> refs/remotes/origin/main
    if m == 0:
        return 0.0
    return (m/(2*np.pi))*np.arctan(n/(m*np.sqrt(1+m**2+n**2)))


def s_z(p, B, E, nu, z, L):
    """Desplazamiento vertical a profundidad z bajo la ESQUINA de un rectángulo B×L
<<<<<<< HEAD
    en el semiespacio elástico (Steinbrenner)."""
=======
    en un semiespacio elástico homogéneo (E, ν).

    No es un asiento acumulado: el asiento de un estrato entre z1 y z2 se obtiene
    como s_z(z1) − s_z(z2), evaluando ambos términos con el E y ν de ese estrato.
    """
    nu = normalizar_nu(nu)
>>>>>>> refs/remotes/origin/main
    n = L/B
    m = z/B
    corchete = (1-nu**2)*phi1(m, n) - (1-nu-2*nu**2)*phi2(m, n)
    return (p*B/E)*corchete


<<<<<<< HEAD
def calcular_steinbrenner(p, B, L, df, z_max):
    total = 0.0
    resultados = []
    n_factor = L / B
    for (nombre, z_techo, z_base, E_i, nu_i) in _truncar(df, z_max):
        m_t = z_techo / (B/2)
        m_b = z_base / (B/2)
        s_t = 4 * s_z(p, B/2, E_i, nu_i, z_techo, L/2)
        s_b = 4 * s_z(p, B/2, E_i, nu_i, z_base, L/2)
        ds = s_t - s_b
        total += ds
        resultados.append({
            "Capa":         nombre,
            "z Techo [m]":  round(z_techo, 3),
            "z Base [m]":   round(z_base, 3),
            "m_techo":      round(m_t, 4),
            "φ1_techo":     round(phi1(m_t, n_factor), 4),
            "φ2_techo":     round(phi2(m_t, n_factor), 4),
            "s_techo [mm]": round(s_t*1000, 3),
            "m_base":       round(m_b, 4),
            "φ1_base":      round(phi1(m_b, n_factor), 4),
            "φ2_base":      round(phi2(m_b, n_factor), 4),
            "s_base [mm]":  round(s_b*1000, 3),
            "Δs [mm]":      round(ds*1000, 3),
        })
    return total, pd.DataFrame(resultados)


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 2 — INTEGRACIÓN ELÁSTICA (Gauss 3 puntos por subcapa)
# ══════════════════════════════════════════════════════════════════════════
_GAUSS_X = np.array([-np.sqrt(3/5), 0.0, np.sqrt(3/5)])
_GAUSS_W = np.array([5/9, 8/9, 5/9])

TENSION_CONSISTENTE = "consistente"
TENSION_HOLL = "holl"


def calcular_ec68(p, B, L, df, z_max, dz_sub=0.25, tension_horizontal=TENSION_CONSISTENTE):
    """Integra Δεz = [Δσz − ν(Δσx+Δσy)]/E en subcapas con cuadratura de Gauss.

    tension_horizontal:
      - "consistente": Δσx+Δσy exacta para el ν de cada estrato (recomendado).
      - "holl": expresiones clásicas de Holl (ν = 0,5); infravalora para ν bajo.
    """
    total = 0.0
    resultados = []
    for (nombre, z_techo, z_base, E_i, nu_i) in _truncar(df, z_max):
        h_ef = z_base - z_techo
        n_sub = max(1, int(np.ceil(h_ef / dz_sub - 1e-9)))
        dz = h_ef / n_sub
        centros = z_techo + (np.arange(n_sub) + 0.5) * dz
        zq = (centros[:, None] + 0.5*dz*_GAUSS_X[None, :]).ravel()
        wq = np.tile(_GAUSS_W * 0.5 * dz, n_sub)

        dsz, dsx, dsy = holl_centro(p, B, L, zq)
        if tension_horizontal == TENSION_HOLL:
            dsxy = dsx + dsy
        else:
            dsxy = suma_horizontal_centro(p, B, L, zq, nu_i)
        dep = (dsz - nu_i*dsxy) / E_i
        ds_capa = float(np.sum(dep * wq))
        total += ds_capa

        resultados.append({
            "Capa":               nombre,
            "z Techo [m]":        round(z_techo, 3),
            "z Base [m]":         round(z_base, 3),
            "h_ef [m]":           round(h_ef, 3),
            "Sub-capas":          n_sub,
            "Δσz med [kPa]":      round(float(np.sum(dsz*wq))/h_ef, 3),
            "Δ(σx+σy) med [kPa]": round(float(np.sum(dsxy*wq))/h_ef, 3),
            "Δεz med [-]":        round(ds_capa/h_ef, 6),
            "Δs [mm]":            round(ds_capa*1000, 3),
        })
    return total, pd.DataFrame(resultados)


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 3 — OPENSEES 3D (bbarBrick, cuarto de dominio, malla graduada)
# ══════════════════════════════════════════════════════════════════════════
def _grid_1d_3d(longitud, borde, mesh, ratio=1.0):
    """Coordenadas 1D: uniformes en [0, borde] con el borde cargado como nodo
    (sin elementos astilla) y, fuera, uniformes (ratio = 1) o en progresión
    geométrica de razón `ratio` hasta `longitud`."""
    n_in = max(1, int(np.ceil(borde / mesh - 1e-9)))
    coords = list(np.linspace(0.0, borde, n_in + 1))
    if longitud <= borde + 1e-9:
        return np.array(coords)
    if ratio <= 1.0 + 1e-9:
        n_out = max(1, int(np.ceil((longitud - borde) / mesh - 1e-9)))
        coords += list(np.linspace(borde, longitud, n_out + 1)[1:])
        return np.array(coords)
    h, x = borde / n_in, borde
    while True:
        h *= ratio
        if longitud - x <= 1.5 * h:
            coords.append(longitud)
            break
        x += h
        coords.append(x)
    return np.array(coords)
=======
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
    """Punto característico clásico de Grasshoff.

    La posición fija (0,37 B; 0,37 L) corresponde al caso ideal con nu = 0.
    En general depende de nu, L/B y del espesor compresible, por lo que el
    resultado de zapata rígida obtenido así debe considerarse aproximado.
    """
    return FRACCION_PUNTO_CARACTERISTICO * B, FRACCION_PUNTO_CARACTERISTICO * L


def factor_empotramiento_mayne_poulos(B, L, D, nu):
    """Factor de corrección por empotramiento I_E (Mayne y Poulos, 1999).

    I_E = 1 − 1 / [3,5·exp(1,22·ν − 0,4)·(B_e/D + 1,6)],  B_e = √(4·B·L/π)
    """
    if D <= 1e-9:
        return 1.0
    nu = normalizar_nu(nu)
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
        nu_i = normalizar_nu(row["nu"])
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
        nu_ref = normalizar_nu(df_bajo["nu"].iloc[0]) if not df_bajo.empty else 0.3
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
>>>>>>> refs/remotes/origin/main


def _z_coords_3d(espesores, mesh):
    z = [0.0]
    z_act = 0.0
    for h in espesores:
<<<<<<< HEAD
        n_sub = max(1, int(np.ceil(h / mesh - 1e-9)))
=======
        n_sub = max(1, int(round(h / mesh)))
>>>>>>> refs/remotes/origin/main
        for s in range(1, n_sub + 1):
            z.append(z_act - h * s / n_sub)
        z_act -= h
    z = np.array(z, dtype=float)
<<<<<<< HEAD
    return z[np.concatenate(([True], np.diff(z) < -1e-9))]
=======
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
>>>>>>> refs/remotes/origin/main


def _tributarias_1d_3d(coords, borde_cargado):
    n = len(coords)
    trib = np.zeros(n)
    for i in range(n):
        izq = 0.0 if i == 0 else 0.5 * (coords[i - 1] + coords[i])
        der = coords[i] if i == n - 1 else 0.5 * (coords[i] + coords[i + 1])
<<<<<<< HEAD
        lo, hi = max(izq, 0.0), min(der, borde_cargado)
=======
        lo = max(izq, 0.0)
        hi = min(der, borde_cargado)
>>>>>>> refs/remotes/origin/main
        trib[i] = max(0.0, hi - lo)
    return trib


<<<<<<< HEAD
def _estratos_mef(df, z_max, factor_prof):
    """Estratos hasta factor_prof·z_max. Devuelve (lista, hay_extension)."""
    filas, z = [], 0.0
    z_fin = z_max * factor_prof
    ultimo = None
    for (nombre, h, E, nu, _, _) in _capas(df):
        if z >= z_fin - 1e-9:
            break
        h_ef = min(z + h, z_fin) - z
        if h_ef > 1e-9:
            filas.append((nombre, h_ef, E, nu))
        z += h
        ultimo = (nombre, E, nu)
    extension = False
    if z < z_fin - 1e-9 and ultimo is not None:
        filas.append((ultimo[0] + " (extensión MEF)", z_fin - z, ultimo[1], ultimo[2]))
        extension = True
    return filas, extension


def estimar_malla_3d(B, L, df, z_max, mesh, factor_dominio=5.0, factor_prof=1.0, ratio=1.0):
    """(nodos, elementos) del modelo que construiría calcular_opensees_3d."""
    estratos, _ = _estratos_mef(df, z_max, factor_prof)
    nx = len(_grid_1d_3d(factor_dominio * B / 2.0, B / 2.0, mesh, ratio))
    ny = len(_grid_1d_3d(factor_dominio * L / 2.0, L / 2.0, mesh, ratio))
    nz = len(_z_coords_3d([h for (_, h, _, _) in estratos], mesh))
    return nx * ny * nz, (nx - 1) * (ny - 1) * (nz - 1)


def calcular_opensees_3d(p, B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0,
                         factor_prof=1.0, ratio=1.0):
    """Asiento en el centro con un modelo 3D de un cuarto de dominio.

    Devuelve (asiento hasta z_max [m], DataFrame por estrato, info).
    El asiento devuelto es s(0) − s(z_max), coherente con la tabla por estratos
    y con los métodos analíticos. Si factor_prof > 1, la base rígida se sitúa
    a factor_prof·z_max y el asiento total en superficie se da en info.
    Lanza MEFError si OpenSees no está disponible o el cálculo falla.
    """
    if not OPENSEES_DISPONIBLE:
        raise MEFError("OpenSeesPy no está instalado en este entorno.")
    if factor_prof < 1.0:
        raise MEFError("factor_prof debe ser ≥ 1.")
    t0 = time.perf_counter()

    estratos_rep = _truncar(df, z_max)
    if not estratos_rep:
        raise MEFError("No hay estratos por encima de z_max.")
    estratos_mef, extension = _estratos_mef(df, z_max, factor_prof)
    espesores = np.array([h for (_, h, _, _) in estratos_mef], dtype=float)

    borde_x, borde_y = B / 2.0, L / 2.0
    x_c = _grid_1d_3d(borde_x * factor_dominio, borde_x, tamaño_malla, ratio)
    y_c = _grid_1d_3d(borde_y * factor_dominio, borde_y, tamaño_malla, ratio)
    z_c = _z_coords_3d(espesores, tamaño_malla)
    nx, ny, nz = len(x_c), len(y_c), len(z_c)
    n_nodos = nx * ny * nz
    if n_nodos > MAX_NODOS_MEF:
        raise MEFError(f"La malla tiene {n_nodos:,} nodos (límite {MAX_NODOS_MEF:,}). "
                       "Aumenta el tamaño de malla, reduce el dominio o usa malla graduada.")

    def nid(i, j, k):
        return k * (nx * ny) + j * nx + i + 1

    try:
        ops.wipe()
        ops.model("basic", "-ndm", 3, "-ndf", 3)
        for pos, (_, _, E_kPa, nu) in enumerate(estratos_mef):
            ops.nDMaterial("ElasticIsotropic", pos + 1, E_kPa, nu)

        for k, z in enumerate(z_c):
            for j, y in enumerate(y_c):
                for i, x in enumerate(x_c):
                    ops.node(nid(i, j, k), float(x), float(y), float(z))

        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    t = nid(i, j, k)
                    if k == nz - 1:
                        ops.fix(t, 1, 1, 1)
                    else:
                        fx = 1 if (i == 0 or i == nx - 1) else 0
                        fy = 1 if (j == 0 or j == ny - 1) else 0
                        if fx or fy:
                            ops.fix(t, fx, fy, 0)

        cumz = np.concatenate(([0.0], -np.cumsum(espesores)))
        el = 1
        for k in range(nz - 1):
            z_media = 0.5 * (z_c[k] + z_c[k + 1])
            mat = 1
            for m in range(len(espesores)):
                if cumz[m + 1] - 1e-9 <= z_media <= cumz[m] + 1e-9:
                    mat = m + 1
                    break
            for j in range(ny - 1):
                for i in range(nx - 1):
                    ops.element("bbarBrick", el,
                                nid(i, j, k+1), nid(i+1, j, k+1), nid(i+1, j+1, k+1), nid(i, j+1, k+1),
                                nid(i, j, k), nid(i+1, j, k), nid(i+1, j+1, k), nid(i, j+1, k), mat)
                    el += 1

        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
        trib_x = _tributarias_1d_3d(x_c, borde_x)
        trib_y = _tributarias_1d_3d(y_c, borde_y)
        resultante = 0.0
        for j in range(ny):
            for i in range(nx):
                area = trib_x[i] * trib_y[j]
                if area > 0.0:
                    ops.load(nid(i, j, 0), 0.0, 0.0, -float(p * area))
                    resultante += p * area

        # Mumps es más rápido, pero no todas las distribuciones de OpenSeesPy lo
        # incluyen: si no está o falla, se reintenta con UmfPack.
        solver_usado = None
        for solver in SOLVERS_MEF:
            try:
                ops.wipeAnalysis()
                ops.reset()
                ops.setTime(0.0)
                ops.system(solver)
                ops.numberer("RCM")
                ops.constraints("Plain")
                ops.integrator("LoadControl", 1.0)
                ops.algorithm("Linear")
                ops.analysis("Static")
                if ops.analyze(1) == 0:
                    solver_usado = solver
                    break
            except Exception:
                continue
        if solver_usado is None:
            raise MEFError("El solver de OpenSees no ha convergido (posible falta de memoria). "
                           "Prueba con una malla más gruesa o graduada.")

        prof = -z_c
        s_mm = np.array([abs(ops.nodeDisp(nid(0, 0, k), 3)) * 1000.0 for k in range(nz)])
    except MEFError:
        raise
    except Exception as exc:  # errores internos de OpenSees
        raise MEFError(f"Error interno de OpenSees: {exc}") from exc
    finally:
        try:
            ops.wipe()
        except Exception:
            pass

    if not np.all(np.isfinite(s_mm)):
        raise MEFError("El MEF ha devuelto desplazamientos no finitos.")

    orden = np.argsort(prof)
    prof, s_mm = prof[orden], s_mm[orden]
    interfaces = [estratos_rep[0][1]] + [zb for (_, _, zb, _, _) in estratos_rep]
    s_int = np.interp(interfaces, prof, s_mm)
    filas = [{"Capa": nombre, "Δs [mm]": round(float(s_int[i] - s_int[i + 1]), 3)}
             for i, (nombre, _, _, _, _) in enumerate(estratos_rep)]

    info = {
        "s_superficie_mm": float(s_mm[0]),
        "s_zmax_mm": float(s_int[-1]),
        "n_nodos": n_nodos,
        "n_elementos": (nx - 1) * (ny - 1) * (nz - 1),
        "factor_prof": factor_prof,
        "extension": extension,
        "resultante_kN": resultante,
        "resultante_teorica_kN": p * B * L / 4.0,
        "t_calculo_s": time.perf_counter() - t0,
        "solver": solver_usado,
    }
    return float(s_int[0] - s_int[-1]) / 1000.0, pd.DataFrame(filas), info
=======
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
        nu = normalizar_nu(row["nu"])
        filas.append((str(row["Descripción"]), h_ef, float(row["E (kPa)"]), nu))
        z += h
    return filas


def _estratos_dominio_mef(df, z_max, factor_prof):
    """Estratos del dominio MEF sin extrapolar propiedades fuera del perfil conocido."""
    df_clean = df.dropna(subset=COLS_MECANICAS)
    filas = []
    z = 0.0
    z_max_mef = z_max * factor_prof
    disponible = espesor_total(df_clean)
    if disponible < z_max_mef - 1e-9:
        raise ValueError(
            f"El dominio MEF requiere {z_max_mef:.2f} m bajo la cota de apoyo, "
            f"pero la estratigrafía solo cubre {disponible:.2f} m."
        )
    for _, row in df_clean.iterrows():
        if z >= z_max_mef - 1e-9:
            break
        h = float(row["Espesor (m)"])
        h_ef = min(z + h, z_max_mef) - z
        if h_ef > 1e-9:
            nu = normalizar_nu(row["nu"])
            filas.append((str(row["Descripción"]), h_ef, float(row["E (kPa)"]), nu))
        z += h
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


def construir_malla_3d(B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=2.0, D=0.0,
                       graduada=True, ratio=1.3, tamaño_max=2.0):
    """Malla MEF de un cuarto de dominio. Única fuente de verdad para el cálculo y para la
    estimación de tamaño de malla de la interfaz.

    Si D > 0 se modela el terreno lateral por encima de la cota de apoyo y se vacía la
    excavación ocupada por la zapata (x < B/2, y < L/2, z > −D).
    """
    df_bajo = estratos_bajo_apoyo(df, D)
    estratos_sup = _estratos_entre(df, 0.0, D) if D > 1e-9 else []
    estratos_inf = _estratos_dominio_mef(df_bajo, z_max, factor_prof)
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


def dimensiones_malla_3d(B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=2.0, D=0.0,
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
    carga_aplicada: float = np.nan     # kN, cuarto de zapata
    reaccion_vertical: float = np.nan  # kN, base del cuarto de dominio
    error_equilibrio: float = np.nan   # error relativo
    profundidad_dominio: float = np.nan  # m bajo la cota de apoyo


def calcular_opensees_3d(p, B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=2.0, D=0.0,
                         rigida=False, graduada=True, ratio=1.3, tamaño_max=2.0):
    """Asiento elástico mediante MEF 3D en un cuarto de dominio.

    * Zapata flexible: presión uniforme repartida en fuerzas nodales.
    * Zapata rígida (y lisa): los nodos cargados comparten el desplazamiento vertical (equalDOF).
    * Si D > 0 se representa la geometría excavada y el terreno lateral, sin modelar contacto
      lateral, estado geostático ni fases de excavación.
    * La base fija se sitúa en factor_prof·z_max; z_max solo delimita el asiento reportado.

    El asiento devuelto es s(apoyo) − s(z_max) en el eje, igual a la suma de la tabla por estratos.
    Lanza ErrorMEF si OpenSees no está disponible o el análisis no converge.
    """
    if not OPENSEES_DISPONIBLE:
        raise ErrorMEF("OpenSeesPy no está instalado: el cálculo MEF no se ha ejecutado.")

    t0 = time.perf_counter()
    estratos_reporte = _estratos_truncados(estratos_bajo_apoyo(df, D), z_max)
    if not estratos_reporte:
        raise ErrorMEF("La estratigrafía no contiene estratos válidos bajo la cota de apoyo hasta z_max.")

    try:
        malla = construir_malla_3d(B, L, df, z_max, tamaño_malla, factor_dominio, factor_prof, D,
                                   graduada, ratio, tamaño_max)
    except ValueError as exc:
        raise ErrorMEF(str(exc)) from exc
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

    carga_aplicada = float(p * trib_x.sum() * trib_y.sum())
    ops.reactions()
    reaccion_vertical = float(sum(ops.nodeReaction(nid(i, j, nz - 1), 3)
                                  for i in range(nx) for j in range(ny)
                                  if malla.nodo_usado[i, j, nz - 1]))
    error_equilibrio = abs(reaccion_vertical - carga_aplicada) / max(abs(carga_aplicada), 1e-12)
    if error_equilibrio > 1e-4:
        ops.wipe()
        raise ErrorMEF(
            f"El modelo no satisface el equilibrio vertical: error relativo {error_equilibrio:.2e}."
        )

    def s_mm(i, j, k):
        return -float(ops.nodeDisp(nid(i, j, k), 3)) * 1000.0

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
    return ResultadoMEF(
        total_m, pd.DataFrame(filas), perfil_x, perfil_y, puntos, rigida, n_nodos, n_elem,
        time.perf_counter() - t0, float(x_c[-1]), float(y_c[-1]), parametros,
        carga_aplicada, reaccion_vertical, error_equilibrio, float(-z_c[-1] - D)
    )
>>>>>>> refs/remotes/origin/main


# ══════════════════════════════════════════════════════════════════════════
# TENSIÓN EFECTIVA Y ZONA DE INFLUENCIA
# ══════════════════════════════════════════════════════════════════════════
<<<<<<< HEAD
def tension_efectiva_base(D, NF, gamma_D=18.0, gamma_sat_D=20.0):
    """σ′v0 al nivel de apoyo (profundidad D) por el terreno situado encima."""
    D = max(float(D), 0.0)
    nf = max(float(NF), 0.0)
    seco = min(D, nf)
    sat = max(0.0, D - nf)
    return gamma_D * seco + (gamma_sat_D - GAMMA_AGUA) * sat


def sigma_v0(z, df, NF, D=0.0, gamma_D=18.0, gamma_sat_D=20.0):
    """Tensión efectiva vertical geoestática a la profundidad z bajo la base.
    Acepta escalares o arrays. NF y D se miden desde la superficie."""
    z_arr = np.asarray(z, dtype=float)
    sv = np.full(z_arr.shape, tension_efectiva_base(D, NF, gamma_D, gamma_sat_D))
    nf_loc = NF - D
    z_act = 0.0
    for (_, h, _, _, g, gs) in _capas(df):
        zt, zb = z_act, z_act + h
        ze = np.clip(z_arr, zt, zb)
        seco = np.clip(np.minimum(ze, nf_loc) - zt, 0.0, None)
        sat = np.clip(ze - np.maximum(zt, nf_loc), 0.0, None)
        sv = sv + g * seco + (gs - GAMMA_AGUA) * sat
        z_act = zb
    return float(sv) if sv.ndim == 0 else sv


def z_influencia_ec7(p, B, L, df, NF, D=0.0, gamma_D=18.0, gamma_sat_D=20.0, paso=0.01):
    """Profundidad en la que Δσz = 0,20·σ′v0 (EN 1997-1, 6.6.2).

    Devuelve (z_i, alcanzado). Si el criterio no se cumple dentro del perfil,
    devuelve (espesor total, False).
    """
    et = float(sum(h for (_, h, _, _, _, _) in _capas(df)))
    if et <= 0:
        return 0.0, False
    z = np.arange(paso, et + 1e-9, paso)
    dsz, _, _ = holl_centro(p, B, L, z)
    sv = sigma_v0(z, df, NF, D, gamma_D, gamma_sat_D)
    f = dsz - 0.20 * sv
    ok = (sv > 0) & (f <= 0)
    if not ok.any():
        return et, False
    i = int(np.argmax(ok))
    if i == 0:
        return float(z[0]), True
    z0, z1, f0, f1 = z[i - 1], z[i], f[i - 1], f[i]
    return float(z0 + f0 * (z1 - z0) / (f0 - f1)), True


# ══════════════════════════════════════════════════════════════════════════
# COMPROBACIÓN ELS
# ══════════════════════════════════════════════════════════════════════════
CRITERIOS_GOBERNANTE = ["MEF 3D", "Máximo de los métodos", "Steinbrenner"]


def asiento_gobernante(tot_st, tot_ec, tot_mef, criterio="MEF 3D", factor_rigidez=1.0):
    """Asiento de comprobación [mm] y descripción de su origen.

    Nunca devuelve 0 por un fallo del MEF: si el criterio es «MEF 3D» y este no
    es válido, se adopta el máximo de los métodos analíticos.
    """
    valores = {"Steinbrenner": tot_st, "Ec. Elástica": tot_ec, "MEF 3D": tot_mef}
    validos = {k: v for k, v in valores.items() if v is not None and np.isfinite(v)}
    if not validos:
        raise ValueError("No hay ningún resultado válido.")
    if criterio == "MEF 3D" and "MEF 3D" in validos:
        base, origen = validos["MEF 3D"], "MEF 3D"
    elif criterio == "Steinbrenner" and "Steinbrenner" in validos:
        base, origen = validos["Steinbrenner"], "Steinbrenner"
    else:
        base = max(validos.values())
        # en caso de empate numérico se nombra el primero (Steinbrenner)
        origen = next(k for k, v in validos.items() if v >= base * (1 - 1e-6))
        origen = f"máximo de los métodos ({origen})"
        if criterio == "MEF 3D":
            origen += " — MEF no disponible"
    s = base * factor_rigidez * 1000.0
    if factor_rigidez != 1.0:
        origen += f" × {factor_rigidez:.2f} (rigidez)"
    return s, origen


def estratos_cohesivos(df, z_max):
    """Nombres de los estratos cohesivos (o sin tipo) situados por encima de z_max."""
    out, z = [], 0.0
    for _, r in df.iterrows():
        if z >= z_max - 1e-9:
            break
        if r.get("Tipo", None) not in ("Granular", "Roca"):
            out.append(str(r["Descripción"]))
        z += float(r["Espesor (m)"])
    return out
=======
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


@dataclass(frozen=True)
class ResultadoInfluencia:
    profundidad: float
    criterio_cumplido: bool
    delta_sigma: float
    sigma_v0: float
    ratio: float


def evaluar_z_influencia_ec7(p, B, L, df, NF, D=0.0):
    """Evalúa la profundidad donde Δσz ≤ 0,20·σ′v0 y si el perfil alcanza el criterio."""
    df_clean = df.dropna(subset=["Espesor (m)"])
    et = espesor_total(df_clean) - D
    k = 1
    while k * PASO_Z_INFLUENCIA <= et + 1e-9:
        z = round(k * PASO_Z_INFLUENCIA, 2)
        dsz, _, _ = holl_centro(p, B, L, z)
        sv = sigma_v0(D + z, df_clean, NF)
        if sv > 0 and dsz <= 0.20*sv:
            return ResultadoInfluencia(z, True, float(dsz), float(sv), float(dsz / sv))
        k += 1
    z = round(max(et, 0.0), 2)
    if z <= 0:
        return ResultadoInfluencia(0.0, False, np.nan, 0.0, np.inf)
    dsz, _, _ = holl_centro(p, B, L, z)
    sv = sigma_v0(D + z, df_clean, NF)
    ratio = float(dsz / sv) if sv > 0 else np.inf
    return ResultadoInfluencia(z, False, float(dsz), float(sv), ratio)


def z_influencia_ec7(p, B, L, df, NF, D=0.0):
    """Compatibilidad: devuelve únicamente la profundidad evaluada."""
    return evaluar_z_influencia_ec7(p, B, L, df, NF, D).profundidad
>>>>>>> refs/remotes/origin/main

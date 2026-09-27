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

import numpy as np
import pandas as pd

# ══════════════════════════════════════════════════════════════════════════
# IMPORTACIÓN OPENSEES
# ══════════════════════════════════════════════════════════════════════════
try:
    import openseespy.opensees as ops
    OPENSEES_DISPONIBLE = True
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
    return sz, sx, sy


def holl_centro(p, B, L, z):
    """Tensiones de Holl bajo el CENTRO: superposición ×4 de cuadrantes B/2 × L/2."""
    sz, sx, sy = holl_esquina(p, B/2.0, L/2.0, z)
    return 4*sz, 4*sx, 4*sy


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


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 1 — STEINBRENNER
# ══════════════════════════════════════════════════════════════════════════
def phi1(m, n):
    if m == 0:
        t1 = np.log(np.sqrt(1+n**2) + n)
        t2 = n*np.log((np.sqrt(1+n**2) + 1)/n)
    else:
        t1 = np.log((np.sqrt(1+m**2+n**2) + n)/np.sqrt(1+m**2))
        t2 = n*np.log((np.sqrt(1+m**2+n**2) + 1)/np.sqrt(n**2+m**2))
    return (1/np.pi)*(t1 + t2)


def phi2(m, n):
    """Factor φ₂ = (m/2π)·arctan[n/(m·√(1+m²+n²))] (Bowles, I₂)."""
    if m == 0:
        return 0.0
    return (m/(2*np.pi))*np.arctan(n/(m*np.sqrt(1+m**2+n**2)))


def s_z(p, B, E, nu, z, L):
    """Desplazamiento vertical a profundidad z bajo la ESQUINA de un rectángulo B×L
    en el semiespacio elástico (Steinbrenner)."""
    n = L/B
    m = z/B
    corchete = (1-nu**2)*phi1(m, n) - (1-nu-2*nu**2)*phi2(m, n)
    return (p*B/E)*corchete


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


def _z_coords_3d(espesores, mesh):
    z = [0.0]
    z_act = 0.0
    for h in espesores:
        n_sub = max(1, int(np.ceil(h / mesh - 1e-9)))
        for s in range(1, n_sub + 1):
            z.append(z_act - h * s / n_sub)
        z_act -= h
    z = np.array(z, dtype=float)
    return z[np.concatenate(([True], np.diff(z) < -1e-9))]


def _tributarias_1d_3d(coords, borde_cargado):
    n = len(coords)
    trib = np.zeros(n)
    for i in range(n):
        izq = 0.0 if i == 0 else 0.5 * (coords[i - 1] + coords[i])
        der = coords[i] if i == n - 1 else 0.5 * (coords[i] + coords[i + 1])
        lo, hi = max(izq, 0.0), min(der, borde_cargado)
        trib[i] = max(0.0, hi - lo)
    return trib


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


# ══════════════════════════════════════════════════════════════════════════
# TENSIÓN EFECTIVA Y ZONA DE INFLUENCIA
# ══════════════════════════════════════════════════════════════════════════
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

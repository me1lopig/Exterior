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

GAMMA_AGUA = 9.81  # kN/m³

# ══════════════════════════════════════════════════════════════════════════
# TENSIONES DE HOLL — BAJO EL CENTRO (Compatibles con arrays de NumPy)
# ══════════════════════════════════════════════════════════════════════════
def holl_esquina(p, B, L, z):
    """Tensiones bajo la ESQUINA de una carga rectangular BxL. Soporta arrays."""
    z_safe = np.where(z <= 1e-6, 1e-6, z)
    
    R1 = np.sqrt(L**2 + z_safe**2)
    R2 = np.sqrt(B**2 + z_safe**2)
    R3 = np.sqrt(L**2 + B**2 + z_safe**2)
    arc = np.arctan((B * L) / (z_safe * R3))
    
    sz = (p / (2*np.pi)) * (arc + B*L*(1/R1**2 + 1/R2**2)*(z_safe/R3))
    sx = (p / (2*np.pi)) * (arc - (B*L*z_safe)/(R1**2*R3))
    sy = (p / (2*np.pi)) * (arc - (B*L*z_safe)/(R2**2*R3))
    
    sz = np.where(z <= 1e-6, p, sz)
    sx = np.where(z <= 1e-6, p/2.0, sx)
    sy = np.where(z <= 1e-6, p/2.0, sy)
    
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
    if m == 0: return 0.0
    return (m/(2*np.pi))*np.arctan(n/(m*np.sqrt(1+m**2+n**2)))

def s_z(p, B, E, nu, z, L):
    """Asiento teórico acumulado desde superficie hasta z (Steinbrenner)."""
    n = L/B
    m = z/B  
    corchete = (1-nu**2)*phi1(m,n) - (1-nu-2*nu**2)*phi2(m,n)
    return (p*B/E)*corchete

def calcular_steinbrenner(p, B, L, df, z_max):
    # 🛡️ FILTRO BACKEND: Ignoramos filas vacías insertadas por la UI
    df_clean = df.dropna(subset=["Espesor (m)", "E (kPa)", "nu"])
    
    total = 0.0
    resultados = []
    z_actual = 0.0
    n_factor = L / B   

    for _, row in df_clean.iterrows():
        if z_actual >= z_max: break
        h_i   = float(row["Espesor (m)"])
        E_i   = float(row["E (kPa)"])
        nu_i  = float(row["nu"])
        nombre= str(row["Descripción"])

        z_techo = z_actual
        z_base  = min(z_actual + h_i, z_max)

        m_t = z_techo / (B/2) 
        m_b = z_base  / (B/2) 
        
        s_t = 4 * s_z(p, B/2, E_i, nu_i, z_techo, L/2)
        s_b = 4 * s_z(p, B/2, E_i, nu_i, z_base,  L/2)
        ds  = s_t - s_b
        total += ds

        resultados.append({
            "Capa":               nombre,
            "z Techo [m]":        round(z_techo, 3),
            "z Base [m]":         round(z_base,  3),
            "m_techo":            round(m_t, 4),
            "φ1_techo":           round(phi1(m_t, n_factor), 4),
            "φ2_techo":           round(phi2(m_t, n_factor), 4),
            "s_techo [mm]":       round(s_t*1000, 3),
            "m_base":             round(m_b, 4),
            "φ1_base":            round(phi1(m_b, n_factor), 4),
            "φ2_base":            round(phi2(m_b, n_factor), 4),
            "s_base [mm]":        round(s_b*1000, 3),
            "Δs [mm]":            round(ds*1000, 3),
        })
        z_actual = z_base

    return total, pd.DataFrame(resultados)


# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 2 — OPENSEES 3D (Refactorizado con bbarBrick y Base extendida)
# ══════════════════════════════════════════════════════════════════════════
def _grid_1d_3d(longitud, borde, mesh):
    n = max(1, int(round(longitud / mesh)))
    base = np.linspace(0.0, longitud, n + 1)
    coords = np.union1d(base, [0.0, borde, longitud])
    coords = coords[np.concatenate(([True], np.diff(coords) > 1e-9))]
    return coords

def _z_coords_3d(espesores, mesh):
    z = [0.0]; z_act = 0.0
    for h in espesores:
        n_sub = max(1, int(round(h / mesh)))
        for s in range(1, n_sub + 1):
            z.append(z_act - h * s / n_sub)
        z_act -= h
    z = np.array(z, dtype=float)
    z = z[np.concatenate(([True], np.diff(z) < -1e-9))]
    return z

def _tributarias_1d_3d(coords, borde_cargado):
    n = len(coords); trib = np.zeros(n)
    for i in range(n):
        izq = 0.0 if i == 0 else 0.5 * (coords[i - 1] + coords[i])
        der = coords[i] if i == n - 1 else 0.5 * (coords[i] + coords[i + 1])
        lo = max(izq, 0.0); hi = min(der, borde_cargado)
        trib[i] = max(0.0, hi - lo)
    return trib

def _estratos_truncados(df, z_max):
    df_clean = df.dropna(subset=["Espesor (m)", "E (kPa)", "nu"])
    filas = []; z = 0.0
    for _, row in df_clean.iterrows():
        if z >= z_max - 1e-9: break
        h = float(row["Espesor (m)"])
        h_ef = min(z + h, z_max) - z
        if h_ef <= 1e-9: break
        nu = min(float(row["nu"]), 0.499)
        filas.append((str(row["Descripción"]), h_ef, float(row["E (kPa)"]), nu))
        z += h
    return filas

def _estratos_extendidos_mef(df, z_max, factor_prof):
    df_clean = df.dropna(subset=["Espesor (m)", "E (kPa)", "nu"])
    filas = []; z = 0.0
    z_max_mef = z_max * factor_prof
    last_E, last_nu, last_desc = None, None, None
    for _, row in df_clean.iterrows():
        if z >= z_max_mef - 1e-9: break
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

def calcular_opensees_3d(p, B, L, df, z_max, tamaño_malla=0.5, factor_dominio=5.0, factor_prof=1.5):
    if not OPENSEES_DISPONIBLE:
        return 0.0, pd.DataFrame([{"Capa": row["Descripción"], "Δs [mm]": 0.0} for _, row in df.iterrows()])

    estratos_reporte = _estratos_truncados(df, z_max)
    if not estratos_reporte: return 0.0, pd.DataFrame([{"Capa": "—", "Δs [mm]": 0.0}])
        
    estratos_mef = _estratos_extendidos_mef(df, z_max, factor_prof)
    espesores_mef = np.array([h for (_, h, _, _) in estratos_mef], dtype=float)

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 3)

    for pos, (_, _, E_kPa, nu) in enumerate(estratos_mef):
        ops.nDMaterial("ElasticIsotropic", pos + 1, E_kPa, nu)

    borde_x, borde_y = B / 2.0, L / 2.0
    x_coords = _grid_1d_3d(borde_x * factor_dominio, borde_x, tamaño_malla)
    y_coords = _grid_1d_3d(borde_y * factor_dominio, borde_y, tamaño_malla)
    z_coords = _z_coords_3d(espesores_mef, tamaño_malla)
    nx, ny, nz = len(x_coords), len(y_coords), len(z_coords)

    def nid(i, j, k): return k * (nx * ny) + j * nx + i + 1

    for k, z in enumerate(z_coords):
        for j, y in enumerate(y_coords):
            for i, x in enumerate(x_coords):
                ops.node(nid(i, j, k), float(x), float(y), float(z))

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                t = nid(i, j, k)
                if k == nz - 1: ops.fix(t, 1, 1, 1)
                else:
                    fx = 1 if (i == 0 or i == nx - 1) else 0      
                    fy = 1 if (j == 0 or j == ny - 1) else 0
                    if fx or fy: ops.fix(t, fx, fy, 0)

    cumz = np.concatenate(([0.0], -np.cumsum(espesores_mef)))
    el = 1
    for k in range(nz - 1):
        z_media = 0.5 * (z_coords[k] + z_coords[k + 1])
        mat = 1
        for m in range(len(espesores_mef)):
            if cumz[m + 1] - 1e-9 <= z_media <= cumz[m] + 1e-9:
                mat = m + 1; break
        for j in range(ny - 1):
            for i in range(nx - 1):
                n1 = nid(i, j, k+1);     n2 = nid(i+1, j, k+1)
                n3 = nid(i+1, j+1, k+1); n4 = nid(i, j+1, k+1)
                n5 = nid(i, j, k);       n6 = nid(i+1, j, k)
                n7 = nid(i+1, j+1, k);   n8 = nid(i, j+1, k)
                ops.element("bbarBrick", el, n1, n2, n3, n4, n5, n6, n7, n8, mat)
                el += 1

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    trib_x = _tributarias_1d_3d(x_coords, borde_x)
    trib_y = _tributarias_1d_3d(y_coords, borde_y)
    for j in range(ny):
        for i in range(nx):
            area = trib_x[i] * trib_y[j]
            if area > 0.0: ops.load(nid(i, j, 0), 0.0, 0.0, -float(p * area))

    ops.system("UmfPack")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    if ops.analyze(1) != 0:
        return 0.0, pd.DataFrame([{"Capa": "Error numérico", "Δs [mm]": 0.0}])

    prof = np.array([-z_coords[k] for k in range(nz)])
    s_mm = np.array([abs(ops.nodeDisp(nid(0, 0, k), 3)) * 1000.0 for k in range(nz)])
    orden = np.argsort(prof); prof, s_mm = prof[orden], s_mm[orden]

    interfaces = [0.0]; z = 0.0
    for (_, h, _, _) in estratos_reporte:
        z += h; interfaces.append(z)
    s_interp = np.interp(interfaces, prof, s_mm)

    filas = [{"Capa": nombre, "Δs [mm]": round(float(s_interp[idx] - s_interp[idx + 1]), 3)}
             for idx, (nombre, _, _, _) in enumerate(estratos_reporte)]
    return float(s_interp[0]) / 1000.0, pd.DataFrame(filas)

# ══════════════════════════════════════════════════════════════════════════
# TENSIÓN EFECTIVA Y ZONA DE INFLUENCIA
# ══════════════════════════════════════════════════════════════════════════
def sigma_v0(z, df, NF):
    # 🛡️ FILTRO BACKEND
    df_clean = df.dropna(subset=["Espesor (m)", "Peso Esp. (kN/m³)", "Peso Esp. Sat (kN/m³)"])
    
    sv = 0.0; z_act = 0.0
    for _, row in df_clean.iterrows():
        h  = float(row["Espesor (m)"])
        g  = float(row["Peso Esp. (kN/m³)"])
        gs = float(row["Peso Esp. Sat (kN/m³)"])
        zt = z_act; zb = z_act + h
        if z <= zt: break
        ze = min(z, zb)
        z_sec_b = min(ze, NF)
        if z_sec_b > zt: sv += g*(z_sec_b-zt)
        z_sat_t = max(zt, NF)
        if ze > z_sat_t: sv += (gs-GAMMA_AGUA)*(ze-z_sat_t)
        z_act = zb
    return sv

def z_influencia_ec7(p, B, L, df, NF):
    # 🛡️ FILTRO BACKEND
    df_clean = df.dropna(subset=["Espesor (m)"])
    et = float(pd.to_numeric(df_clean["Espesor (m)"]).sum())
    
    z = 0.05
    while z <= et:
        dsz, _, _ = holl_centro(p, B, L, z)
        sv = sigma_v0(z, df_clean, NF)
        if sv > 0 and dsz <= 0.20*sv:
            return z
        z += 0.05
    return et

import numpy as np

def validate_tensor(T):
    """Valida y convierte la entrada en un array NumPy 3x3."""
    T = np.asarray(T, dtype=float)
    if T.shape != (3, 3):
        raise ValueError("El tensor debe ser una matriz de 3x3.")
    return T

def get_invariants(T):
    """Calcula los invariantes principales del tensor (I1, I2, I3)."""
    T = validate_tensor(T)
    I1 = np.trace(T)
    I2 = 0.5 * (I1**2 - np.trace(np.dot(T, T)))
    I3 = np.linalg.det(T)
    return I1, I2, I3

def get_principal(T):
    """
    Calcula valores y direcciones principales.
    Retorna los autovalores ordenados de mayor a menor y sus autovectores asociados.
    """
    T = validate_tensor(T)
    # Verificación de simetría (tolerancia numérica)
    is_symmetric = np.allclose(T, T.T, atol=1e-8)
    
    if is_symmetric:
        eigvals, eigvecs = np.linalg.eigh(T)
    else:
        eigvals, eigvecs = np.linalg.eig(T)
        
    # Ordenar autovalores (σ1 >= σ2 >= σ3) y autovectores correspondientes
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]
    return eigvals, eigvecs

def get_decomposition(T):
    """Descompone el tensor en su parte Esférica (volumétrica) y Desviadora."""
    T = validate_tensor(T)
    p = np.trace(T) / 3.0
    T_sph = p * np.eye(3)
    T_dev = T - T_sph
    return T_sph, T_dev, p

def get_deviatoric_invariants(T_dev, eigvals):
    """Calcula los invariantes del desviador (J2, J3) y tensiones equivalentes (Von Mises, Tresca)."""
    J2 = 0.5 * np.trace(np.dot(T_dev, T_dev))
    J3 = np.linalg.det(T_dev)
    von_mises = np.sqrt(3.0 * J2)
    tresca = np.max(eigvals) - np.min(eigvals)
    return J2, J3, von_mises, tresca

def get_plane_components(T, n_vec):
    """
    Calcula las componentes intrínsecas (σn, τ) sobre un plano definido por su vector normal.
    """
    T = validate_tensor(T)
    n_vec = np.asarray(n_vec, dtype=float)
    n_norm = np.linalg.norm(n_vec)
    
    if n_norm < 1e-12:
        raise ValueError("El vector normal no puede ser nulo.")
        
    n_vec = n_vec / n_norm  # Normalización
    
    # Vector tracción t = T * n
    t_vec = T @ n_vec
    # Componente normal σn = t · n
    sigma_n = np.dot(t_vec, n_vec)
    # Vector tangencial τ_vec = t - σn * n
    tau_vec = t_vec - sigma_n * n_vec
    # Magnitud de la tensión tangencial
    tau = np.linalg.norm(tau_vec)
    
    return t_vec, sigma_n, tau_vec, tau

def rotate_tensor(T, R):
    """Rota el tensor mediante una matriz de rotación R. Operación: T' = R * T * R^T"""
    T = validate_tensor(T)
    R = validate_tensor(R)
    return R @ T @ R.T

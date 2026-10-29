from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def influencia_esquina(m: ArrayLike, n: ArrayLike) -> NDArray[np.float64]:
    """Factor de influencia de Boussinesq bajo la esquina de un rectángulo.

    La forma compacta es algebraicamente equivalente a la expresión clásica de
    la imagen de referencia y resulta estable para valores grandes de m y n.
    Admite argumentos con signo para aplicar superposición rectangular.
    """
    m_arr, n_arr = np.broadcast_arrays(
        np.asarray(m, dtype=float), np.asarray(n, dtype=float)
    )
    raiz = np.sqrt(1.0 + m_arr**2 + n_arr**2)
    producto = m_arr * n_arr
    termino_angular = np.arctan2(producto, raiz)
    termino_racional = (producto / raiz) * (
        1.0 / (1.0 + m_arr**2) + 1.0 / (1.0 + n_arr**2)
    )
    return (termino_angular + termino_racional) / (2.0 * np.pi)


def incremento_tension_rectangular(
    x_m: ArrayLike,
    y_m: ArrayLike,
    z_m: ArrayLike,
    b_m: float,
    l_m: float,
    q_kpa: float,
) -> NDArray[np.float64]:
    """Incremento de tensión vertical bajo/cerca de un rectángulo cargado.

    El rectángulo está centrado en (0, 0), con B en el eje x y L en el eje y.
    Se aplica superposición de cuatro primitivas de esquina. La tensión es
    positiva en compresión. En z=0 se devuelve el límite interior geométrico.
    """
    if b_m <= 0 or l_m <= 0 or q_kpa < 0:
        raise ValueError("B y L deben ser positivos y q no puede ser negativa.")
    x, y, z = np.broadcast_arrays(
        np.asarray(x_m, dtype=float),
        np.asarray(y_m, dtype=float),
        np.asarray(z_m, dtype=float),
    )
    if np.any(z < 0):
        raise ValueError("La profundidad z no puede ser negativa.")

    resultado = np.empty_like(z, dtype=float)
    positivo = z > 0.0
    if np.any(positivo):
        zp = z[positivo]
        xp = x[positivo]
        yp = y[positivo]
        x1 = (-b_m / 2.0 - xp) / zp
        x2 = (b_m / 2.0 - xp) / zp
        y1 = (-l_m / 2.0 - yp) / zp
        y2 = (l_m / 2.0 - yp) / zp
        factor = (
            influencia_esquina(x2, y2)
            - influencia_esquina(x1, y2)
            - influencia_esquina(x2, y1)
            + influencia_esquina(x1, y1)
        )
        resultado[positivo] = q_kpa * factor

    if np.any(~positivo):
        xx = np.abs(x[~positivo])
        yy = np.abs(y[~positivo])
        tol = 1e-12 * max(b_m, l_m)
        fx = np.where(xx < b_m / 2.0 - tol, 1.0, np.where(xx <= b_m / 2.0 + tol, 0.5, 0.0))
        fy = np.where(yy < l_m / 2.0 - tol, 1.0, np.where(yy <= l_m / 2.0 + tol, 0.5, 0.0))
        resultado[~positivo] = q_kpa * fx * fy
    return resultado


def incremento_centro(z_m: ArrayLike, b_m: float, l_m: float, q_kpa: float) -> NDArray[np.float64]:
    """Atajo para la vertical que pasa por el centro de la zapata."""
    z = np.asarray(z_m, dtype=float)
    return incremento_tension_rectangular(np.zeros_like(z), np.zeros_like(z), z, b_m, l_m, q_kpa)


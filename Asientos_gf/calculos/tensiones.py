"""Incrementos de tension de Boussinesq y distribuciones de contacto."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, pi, sqrt

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import LinearConstraint, minimize
from scipy.special import roots_legendre

from modelos.datos import Foundation


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PressureField:
    """Cuadratura de una presion de contacto; q en kPa y pesos en m2."""

    x_m: FloatArray
    y_m: FloatArray
    area_weights_m2: FloatArray
    pressure_kpa: FloatArray
    gross_pressure_kpa: FloatArray
    contact_model: str
    warnings: tuple[str, ...] = ()
    rigid_settlement_center_m: float | None = None
    rigid_rotation_x_rad: float | None = None
    rigid_rotation_y_rad: float | None = None
    cell_width_m: FloatArray | None = None
    cell_length_m: FloatArray | None = None
    strip_width_m: float | None = None
    strip_net_pressure_kpa: float | None = None

    @property
    def resultant_kn(self) -> float:
        return float(np.sum(self.pressure_kpa * self.area_weights_m2))

    @property
    def gross_resultant_kn(self) -> float:
        return float(np.sum(self.gross_pressure_kpa * self.area_weights_m2))


def corner_influence_rect(m: float, n: float) -> float:
    """Factor de Boussinesq bajo la esquina de un rectangulo uniforme."""
    m, n = abs(float(m)), abs(float(n))
    if m <= 1e-15 or n <= 1e-15:
        return 0.0
    m2, n2 = m * m, n * n
    a = 1.0 + m2 + n2
    b = m2 * n2
    root = sqrt(a)
    term_1 = (2.0 * m * n * root / (a + b)) * ((a + 1.0) / a)
    term_2 = atan2(2.0 * m * n * root, a - b)
    return (term_1 + term_2) / (4.0 * pi)


def _signed_rect_primitive(x_m: float, y_m: float, z_m: float) -> float:
    if abs(x_m) <= 1e-15 or abs(y_m) <= 1e-15:
        return 0.0
    sign = 1.0 if x_m * y_m > 0 else -1.0
    return sign * corner_influence_rect(abs(x_m) / z_m, abs(y_m) / z_m)


def stress_rect_uniform(
    q_kpa: float,
    width_m: float,
    length_m: float,
    z_m: float | FloatArray,
    x_m: float = 0.0,
    y_m: float = 0.0,
) -> float | FloatArray:
    """Delta sigma_z bajo cualquier punto de un rectangulo uniformemente cargado."""
    z_array = np.asarray(z_m, dtype=float)
    result = np.empty_like(z_array)
    x1, x2 = -width_m / 2.0 - x_m, width_m / 2.0 - x_m
    y1, y2 = -length_m / 2.0 - y_m, length_m / 2.0 - y_m
    flat_z = z_array.ravel()
    flat_result = result.ravel()
    for index, depth in enumerate(flat_z):
        if depth <= 1e-12:
            inside = x1 <= 0 <= x2 and y1 <= 0 <= y2
            flat_result[index] = q_kpa if inside else 0.0
            continue
        influence = (
            _signed_rect_primitive(x2, y2, depth)
            - _signed_rect_primitive(x1, y2, depth)
            - _signed_rect_primitive(x2, y1, depth)
            + _signed_rect_primitive(x1, y1, depth)
        )
        flat_result[index] = q_kpa * influence
    return float(result) if result.ndim == 0 else result


def stress_strip_uniform(q_kpa: float, width_m: float, z_m: float | FloatArray, x_m: float = 0.0) -> float | FloatArray:
    """Solucion bidimensional para una banda indefinida."""
    z = np.asarray(z_m, dtype=float)
    safe_z = np.maximum(z, 1e-15)
    a = -width_m / 2.0 - x_m
    b = width_m / 2.0 - x_m
    angle = np.arctan(b / safe_z) - np.arctan(a / safe_z)
    sine_term = b * safe_z / (b * b + safe_z * safe_z) - a * safe_z / (a * a + safe_z * safe_z)
    result = q_kpa * (angle + sine_term) / pi
    if np.ndim(z_m) == 0:
        return float(result)
    return result


def stress_circle_axis(q_kpa: float, radius_m: float, z_m: float | FloatArray) -> float | FloatArray:
    """Solucion cerrada bajo el eje de un circulo uniformemente cargado."""
    z = np.asarray(z_m, dtype=float)
    safe_z = np.maximum(z, 1e-15)
    result = q_kpa * (1.0 - (1.0 + (radius_m / safe_z) ** 2) ** -1.5)
    if np.ndim(z_m) == 0:
        return float(result)
    return result


def circle_quadrature(radius_m: float, radial_order: int = 12, angular_order: int | None = None) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Cuadratura polar de Gauss para el disco real."""
    angular_order = angular_order or max(24, 2 * radial_order)
    nodes, weights = roots_legendre(radial_order)
    rho = 0.5 * radius_m * (nodes + 1.0)
    wr = 0.5 * radius_m * weights
    theta = (np.arange(angular_order, dtype=float) + 0.5) * 2.0 * pi / angular_order
    rr, tt = np.meshgrid(rho, theta, indexing="ij")
    radial_weights, _ = np.meshgrid(wr, theta, indexing="ij")
    area_weights = radial_weights * rr * (2.0 * pi / angular_order)
    return (rr * np.cos(tt)).ravel(), (rr * np.sin(tt)).ravel(), area_weights.ravel()


def rectangle_quadrature(width_m: float, length_m: float, order: int = 12) -> tuple[FloatArray, FloatArray, FloatArray]:
    nodes, weights = roots_legendre(order)
    x = 0.5 * width_m * nodes
    y = 0.5 * length_m * nodes
    wx = 0.5 * width_m * weights
    wy = 0.5 * length_m * weights
    xx, yy = np.meshgrid(x, y, indexing="ij")
    wxx, wyy = np.meshgrid(wx, wy, indexing="ij")
    return xx.ravel(), yy.ravel(), (wxx * wyy).ravel()


def stress_from_field(
    field: PressureField,
    z_m: float | FloatArray,
    x_m: float = 0.0,
    y_m: float = 0.0,
) -> float | FloatArray:
    """Integra el nucleo de tension vertical de Boussinesq."""
    if field.strip_width_m is not None and field.strip_net_pressure_kpa is not None:
        return stress_strip_uniform(field.strip_net_pressure_kpa, field.strip_width_m, z_m, x_m)
    depths = np.atleast_1d(np.asarray(z_m, dtype=float))
    dx2 = (field.x_m - x_m) ** 2
    dy2 = (field.y_m - y_m) ** 2
    result = np.empty_like(depths)
    loads_kn = field.pressure_kpa * field.area_weights_m2
    for index, depth in enumerate(depths):
        if depth <= 1e-12:
            result[index] = float(np.average(field.pressure_kpa, weights=field.area_weights_m2))
            continue
        if field.cell_width_m is not None and field.cell_length_m is not None:
            value = 0.0
            for px, py, width, length, pressure in zip(
                field.x_m,
                field.y_m,
                field.cell_width_m,
                field.cell_length_m,
                field.pressure_kpa,
            ):
                value += stress_rect_uniform(
                    float(pressure), float(width), float(length), float(depth), x_m - float(px), y_m - float(py)
                )
            result[index] = value
        else:
            radius2 = dx2 + dy2 + depth * depth
            kernel = 3.0 * depth**3 / (2.0 * pi * radius2**2.5)
            result[index] = float(np.sum(loads_kn * kernel))
    return float(result[0]) if np.ndim(z_m) == 0 else result


def vertical_strain_elastic_3d_from_field(
    field: PressureField,
    z_m: float | FloatArray,
    young_kpa: float | FloatArray,
    nu: float | FloatArray,
    x_m: float = 0.0,
    y_m: float = 0.0,
) -> float | FloatArray:
    """Deformacion vertical compresiva derivada del desplazamiento de Boussinesq."""
    depths = np.atleast_1d(np.asarray(z_m, dtype=float))
    young = np.broadcast_to(np.asarray(young_kpa, dtype=float), depths.shape)
    poisson = np.broadcast_to(np.asarray(nu, dtype=float), depths.shape)
    result = np.empty_like(depths)
    radial2 = (field.x_m - x_m) ** 2 + (field.y_m - y_m) ** 2
    loads_kn = field.pressure_kpa * field.area_weights_m2
    for index, (depth, modulus, v) in enumerate(zip(depths, young, poisson)):
        radius2 = radial2 + depth * depth
        kernel = (1.0 + v) / (2.0 * pi * modulus) * (
            3.0 * depth**3 / radius2**2.5 - 2.0 * v * depth / radius2**1.5
        )
        result[index] = float(np.sum(loads_kn * kernel))
    return float(result[0]) if np.ndim(z_m) == 0 else result


def vertical_displacement_elastic_from_field(
    field: PressureField,
    z_m: float,
    young_kpa: float,
    nu: float,
    x_m: float = 0.0,
    y_m: float = 0.0,
) -> float:
    """Desplazamiento vertical de Boussinesq; positivo hacia abajo."""
    if young_kpa <= 0 or not 0 <= nu < 0.5:
        raise ValueError("E y nu no son validos para el desplazamiento elastico.")
    depth = max(float(z_m), 0.0)
    coefficient = (1.0 + nu) / (2.0 * pi * young_kpa)
    if depth <= 1e-14 and field.cell_width_m is not None and field.cell_length_m is not None:
        integral = 0.0
        for px, py, width, length, pressure in zip(
            field.x_m,
            field.y_m,
            field.cell_width_m,
            field.cell_length_m,
            field.pressure_kpa,
        ):
            integral += float(pressure) * _rect_cell_integral_1_over_r(
                float(px) - x_m, float(py) - y_m, float(width) / 2.0, float(length) / 2.0
            )
        return coefficient * 2.0 * (1.0 - nu) * integral
    radial2 = (field.x_m - x_m) ** 2 + (field.y_m - y_m) ** 2
    radius = np.sqrt(radial2 + depth * depth)
    if np.any(radius <= 1e-15):
        raise ValueError("La cuadratura contiene una singularidad de desplazamiento en el punto evaluado.")
    kernel = depth**2 / radius**3 + 2.0 * (1.0 - nu) / radius
    loads_kn = field.pressure_kpa * field.area_weights_m2
    return coefficient * float(np.sum(loads_kn * kernel))


def _cell_grid(foundation: Foundation, target_cells: int = 100) -> tuple[FloatArray, FloatArray, FloatArray, tuple[float, float] | None]:
    if foundation.shape == "circular":
        nr = max(3, int(sqrt(target_cells / 4.0)))
        nt = max(16, 4 * nr)
        radius = foundation.diameter_m / 2.0
        radial_edges = radius * np.sqrt(np.linspace(0.0, 1.0, nr + 1))
        xs: list[float] = []
        ys: list[float] = []
        areas: list[float] = []
        for ir in range(nr):
            r1, r2 = radial_edges[ir], radial_edges[ir + 1]
            centroid_r = (2.0 / 3.0) * (r2**3 - r1**3) / (r2**2 - r1**2)
            cell_area = pi * (r2**2 - r1**2) / nt
            for it in range(nt):
                theta = 2.0 * pi * (it + 0.5) / nt
                xs.append(centroid_r * np.cos(theta))
                ys.append(centroid_r * np.sin(theta))
                areas.append(cell_area)
        return np.asarray(xs), np.asarray(ys), np.asarray(areas), None
    nx = max(4, int(sqrt(target_cells * foundation.width_m / foundation.length_m)))
    ny = max(4, int(np.ceil(target_cells / nx)))
    dx, dy = foundation.width_m / nx, foundation.length_m / ny
    x = np.linspace(-foundation.width_m / 2 + dx / 2, foundation.width_m / 2 - dx / 2, nx)
    y = np.linspace(-foundation.length_m / 2 + dy / 2, foundation.length_m / 2 - dy / 2, ny)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    return xx.ravel(), yy.ravel(), np.full(xx.size, dx * dy), (dx, dy)


def _affine_pressure(foundation: Foundation, x: FloatArray, y: FloatArray, force_kn: float) -> FloatArray:
    area = foundation.area_m2
    if foundation.shape == "circular":
        radius = foundation.diameter_m / 2.0
        inertia_x = inertia_y = pi * radius**4 / 4.0
    else:
        inertia_x = foundation.width_m * foundation.length_m**3 / 12.0
        inertia_y = foundation.length_m * foundation.width_m**3 / 12.0
    return force_kn / area + foundation.mx_knm * y / inertia_x + foundation.my_knm * x / inertia_y


def _solve_nonnegative_equilibrium(
    x: FloatArray,
    y: FloatArray,
    areas: FloatArray,
    target: tuple[float, float, float],
    initial: FloatArray,
) -> FloatArray:
    matrix = np.vstack((areas, areas * y, areas * x))
    constraint = LinearConstraint(matrix, np.asarray(target), np.asarray(target))
    scale = max(float(np.mean(np.abs(initial))), 1.0)
    result = minimize(
        lambda p: 0.5 * float(np.sum(((p - initial) / scale) ** 2)),
        np.maximum(initial, 0.01 * scale),
        jac=lambda p: (p - initial) / scale**2,
        bounds=[(0.0, None)] * initial.size,
        constraints=[constraint],
        method="SLSQP",
        options={"ftol": 1e-10, "maxiter": 1500},
    )
    if not result.success:
        raise ValueError("No existe una distribucion de contacto sin tracciones para las acciones introducidas.")
    return np.asarray(result.x, dtype=float)


def _primitive_1_over_r(x: float, y: float) -> float:
    if abs(x) < 1e-15 and abs(y) < 1e-15:
        return 0.0
    first = x * np.arcsinh(y / abs(x)) if abs(x) > 1e-15 else 0.0
    second = y * np.arcsinh(x / abs(y)) if abs(y) > 1e-15 else 0.0
    return float(first + second)


def _rect_cell_integral_1_over_r(dx: float, dy: float, half_x: float, half_y: float) -> float:
    x1, x2 = dx - half_x, dx + half_x
    y1, y2 = dy - half_y, dy + half_y
    return (
        _primitive_1_over_r(x2, y2)
        - _primitive_1_over_r(x1, y2)
        - _primitive_1_over_r(x2, y1)
        + _primitive_1_over_r(x1, y1)
    )


def _rigid_contact(
    foundation: Foundation,
    gross_force_kn: float,
    representative_e_kpa: float,
    representative_nu: float,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, float, float, float, tuple[str, ...], tuple[float, float] | None]:
    x, y, areas, cell_size = _cell_grid(foundation, 100)
    count = x.size
    coefficient = (1.0 - representative_nu**2) / (pi * representative_e_kpa)
    influence = np.empty((count, count), dtype=float)
    for i in range(count):
        for j in range(count):
            if cell_size is not None:
                integral = _rect_cell_integral_1_over_r(
                    x[j] - x[i], y[j] - y[i], cell_size[0] / 2.0, cell_size[1] / 2.0
                )
            elif i == j:
                equivalent_radius = sqrt(areas[j] / pi)
                integral = 2.0 * pi * equivalent_radius
            else:
                integral = areas[j] / np.hypot(x[j] - x[i], y[j] - y[i])
            influence[i, j] = coefficient * integral

    active = np.ones(count, dtype=bool)
    pressure = np.zeros(count, dtype=float)
    plane = np.zeros(3, dtype=float)
    target = np.asarray([gross_force_kn, foundation.mx_knm, foundation.my_knm], dtype=float)
    for _ in range(count - 3):
        ids = np.flatnonzero(active)
        compatibility = np.column_stack((-np.ones(ids.size), -y[ids], -x[ids]))
        equilibrium = np.vstack((areas[ids], areas[ids] * y[ids], areas[ids] * x[ids]))
        system = np.block([
            [influence[np.ix_(ids, ids)], compatibility],
            [equilibrium, np.zeros((3, 3))],
        ])
        rhs = np.concatenate((np.zeros(ids.size), target))
        try:
            solution = np.linalg.solve(system, rhs)
        except np.linalg.LinAlgError as exc:
            raise ValueError("La matriz de contacto rigido es singular para esta geometria.") from exc
        local_pressure = solution[: ids.size]
        plane = solution[ids.size :]
        if np.min(local_pressure) >= -1e-8:
            pressure[ids] = np.maximum(local_pressure, 0.0)
            break
        active[ids[int(np.argmin(local_pressure))]] = False
    else:
        raise ValueError("No converge el contacto rigido sin tracciones.")
    warnings: list[str] = []
    if np.count_nonzero(~active):
        warnings.append("Se ha resuelto contacto parcial sin tracciones en la base rigida.")
    return x, y, areas, pressure, float(plane[0]), float(plane[1]), float(plane[2]), tuple(warnings), cell_size


def build_pressure_field(
    foundation: Foundation,
    excavation_pressure_kpa: float,
    representative_e_kpa: float,
    representative_nu: float,
    quadrature_order: int = 12,
) -> PressureField:
    """Construye presion bruta de contacto y presion neta que carga el terreno."""
    given_force = foundation.applied_vertical_kn
    gross_force = given_force if foundation.pressure_basis == "bruta" else given_force + excavation_pressure_kpa * foundation.area_m2
    if gross_force <= 0:
        raise ValueError("La resultante bruta de contacto debe ser positiva.")
    warnings: list[str] = []
    if foundation.shape == "banda":
        x = np.asarray([0.0])
        y = np.asarray([0.0])
        area = np.asarray([foundation.area_m2])
        gross = np.asarray([gross_force / foundation.area_m2])
        net = gross - excavation_pressure_kpa
        return PressureField(
            x, y, area, net, gross, "banda uniforme",
            strip_width_m=foundation.width_m,
            strip_net_pressure_kpa=float(net[0]),
        )

    if foundation.rigidity == "rigida":
        x, y, areas, gross, settlement, rotation_x, rotation_y, rigid_warnings, cell_size = _rigid_contact(
            foundation, gross_force, representative_e_kpa, representative_nu
        )
        warnings.extend(rigid_warnings)
        net = gross - excavation_pressure_kpa
        cell_width = np.full(x.size, cell_size[0]) if cell_size is not None else None
        cell_length = np.full(x.size, cell_size[1]) if cell_size is not None else None
        return PressureField(
            x, y, areas, net, gross, "matriz de influencia elastica; contacto sin traccion",
            tuple(warnings), settlement, rotation_x, rotation_y, cell_width, cell_length
        )

    if foundation.shape == "circular":
        x, y, areas = circle_quadrature(foundation.diameter_m / 2.0, quadrature_order)
    else:
        x, y, areas, cell_size = _cell_grid(foundation, max(400, 4 * quadrature_order**2))
    gross = _affine_pressure(foundation, x, y, gross_force)
    if float(np.min(gross)) < -1e-8:
        x, y, areas, cell_size = _cell_grid(foundation, 144)
        initial = _affine_pressure(foundation, x, y, gross_force)
        gross = _solve_nonnegative_equilibrium(
            x, y, areas, (gross_force, foundation.mx_knm, foundation.my_knm), initial
        )
        warnings.append("Se ha resuelto contacto parcial discretizado porque la ley lineal producia tracciones.")
        model = "contacto flexible discretizado sin traccion"
    else:
        model = "presion lineal con contacto completo"
    net = gross - excavation_pressure_kpa
    if foundation.shape == "rectangular":
        cell_width = np.full(x.size, cell_size[0])
        cell_length = np.full(x.size, cell_size[1])
    else:
        cell_width = cell_length = None
    return PressureField(
        x, y, areas, net, gross, model, tuple(warnings),
        cell_width_m=cell_width, cell_length_m=cell_length
    )

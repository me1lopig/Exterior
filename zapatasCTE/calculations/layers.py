from __future__ import annotations

from models.inputs import SoilLayer


def check_layer_coverage(
    layers: list[SoilLayer],
    required_top_m: float,
    required_bottom_m: float,
    label: str,
    tolerance_m: float = 1e-6,
) -> dict[str, object]:
    """Check that the union of layers covers a required depth interval."""
    if required_top_m < 0 or required_bottom_m <= required_top_m:
        raise ValueError("El intervalo de cobertura requerido no es valido")

    ordered = sorted(layers, key=lambda item: (item.top_depth_m, item.bottom_depth_m))
    gaps: list[tuple[float, float]] = []
    overlaps: list[tuple[float, float]] = []
    cursor = required_top_m
    previous_bottom: float | None = None

    for layer in ordered:
        if layer.bottom_depth_m <= required_top_m + tolerance_m:
            continue
        if layer.top_depth_m >= required_bottom_m - tolerance_m:
            break

        top = max(layer.top_depth_m, required_top_m)
        bottom = min(layer.bottom_depth_m, required_bottom_m)
        if bottom <= top + tolerance_m:
            continue

        if previous_bottom is not None and top < previous_bottom - tolerance_m:
            overlaps.append((top, min(previous_bottom, bottom)))
        previous_bottom = max(previous_bottom or bottom, bottom)

        if top > cursor + tolerance_m:
            gaps.append((cursor, top))
            cursor = bottom
        else:
            cursor = max(cursor, bottom)
        if cursor >= required_bottom_m - tolerance_m:
            cursor = required_bottom_m
            break

    if cursor < required_bottom_m - tolerance_m:
        gaps.append((cursor, required_bottom_m))

    covered = not gaps
    warnings: list[str] = []
    if gaps:
        gap_text = ", ".join(f"{top:.2f}-{bottom:.2f} m" for top, bottom in gaps)
        warnings.append(f"{label}: faltan materiales en {gap_text}.")
    if overlaps:
        overlap_text = ", ".join(
            f"{top:.2f}-{bottom:.2f} m" for top, bottom in overlaps
        )
        warnings.append(f"{label}: existen solapes de capas en {overlap_text}.")

    return {
        "label": label,
        "required_top_m": required_top_m,
        "required_bottom_m": required_bottom_m,
        "required_thickness_m": required_bottom_m - required_top_m,
        "covered": covered,
        "gaps": gaps,
        "overlaps": overlaps,
        "warnings": warnings,
    }


def assess_foundation_bulbs(
    layers: list[SoilLayer],
    foundation_base_depth_m: float,
    width_m: float,
    settlement_influence_depth_m: float,
) -> dict[str, object]:
    """Audit material coverage for bearing and settlement pressure bulbs."""
    if width_m <= 0 or settlement_influence_depth_m <= 0:
        raise ValueError("B y la profundidad de influencia deben ser positivas")

    checks = [
        check_layer_coverage(
            layers,
            foundation_base_depth_m,
            foundation_base_depth_m + 1.5 * width_m,
            "Bulbo de hundimiento D a D+1.5B",
        ),
        check_layer_coverage(
            layers,
            foundation_base_depth_m,
            foundation_base_depth_m + settlement_influence_depth_m,
            "Bulbo de asientos D a D+ZI",
        ),
    ]
    warnings = [
        warning
        for check in checks
        for warning in check["warnings"]
    ]
    return {
        "checks": checks,
        "all_covered": all(bool(check["covered"]) for check in checks),
        "warnings": warnings,
    }


def assess_relevant_layers(
    layers: list[SoilLayer], foundation_base_depth_m: float, width_m: float
) -> dict[str, object]:
    """Audit layers within the CTE bearing-capacity representative depth."""
    bottom = foundation_base_depth_m + 1.5 * width_m
    relevant = [
        layer
        for layer in layers
        if layer.bottom_depth_m > foundation_base_depth_m
        and layer.top_depth_m < bottom
    ]
    if not relevant:
        return {
            "relevant": [],
            "warnings": ["No hay capas definidas en la zona D a D+1.5B."],
        }
    min_modulus = min(layer.deformation_modulus_mpa for layer in relevant)
    weakest = [layer.name for layer in relevant if layer.deformation_modulus_mpa == min_modulus]
    warnings: list[str] = []
    if len(relevant) > 1:
        warnings.append(
            "La expresion homogenea de hundimiento requiere parametros caracteristicos "
            "representativos de todas las capas relevantes."
        )
    warnings.append("Capa de menor modulo en la zona de influencia: " + ", ".join(weakest))
    return {"relevant": relevant, "warnings": warnings}

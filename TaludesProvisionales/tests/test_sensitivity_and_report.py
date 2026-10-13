from docx import Document

from slope_stability_app.calculations import run_sensitivity, search_critical_surfaces
from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, Soil, SoilProfile, SweepConfig
from slope_stability_app.services import build_report


def _case():
    geometry = SlopeGeometry(6.0, 42.0, 2.0)
    profile = SoilProfile(Soil("Limo arenoso", 18.0, 20.0, 6.0, 29.0))
    config = AnalysisConfig(slices=18, search_level="Rapida", target_factor=1.25)
    return geometry, profile, config


def test_sensitivity_grid_has_expected_number_of_cases():
    geometry, profile, config = _case()
    sweep = SweepConfig(True, 35.0, 50.0, 3, True, 0.0, 5.0, 2)
    data = run_sensitivity(geometry, profile, config, sweep)
    assert len(data) == 6
    assert data["FS Bishop"].notna().all()
    assert set(data.columns) == {
        "Pendiente (deg)",
        "Nivel freatico (m)",
        "FS Fellenius",
        "FS Bishop",
        "Superficies validas",
    }


def test_report_is_valid_docx(tmp_path):
    geometry, profile, config = _case()
    result = search_critical_surfaces(geometry, profile, config)
    report = build_report(ProjectData("Caso de prueba", "Madrid", "Equipo geotecnico"), geometry, profile, config, result)
    path = tmp_path / "report.docx"
    path.write_bytes(report)
    document = Document(path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Estabilidad de talud temporal" in text
    assert "Resumen de resultados" in text
    assert len(report) > 20_000

# 🌐 Exterior — Programas de visibilidad exterior (Geotecnia)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-See%20LICENSE-lightgrey)](./LICENSE)

## Qué es
Colección de aplicaciones y utilidades en Python (principalmente interfaces Streamlit) para análisis geotécnico exterior: estabilidad de taludes, consolidación 1D, mejora con columnas de grava, asentamientos de zapatas (FEM), dimensionado de pilotes y utilidades de tablas/parametrización. Está orientado a uso académico, investigación y evaluaciones preliminares de diseño.

### Stack
- Lenguaje(s): Python (100%)
- Entorno / runtime: Streamlit (aplicaciones interactivas), scripts y módulos numéricos
- Librerías destacadas: numpy, pandas, plotly / matplotlib, openpyxl, python-docx (y utilidades para exportar informes)

## Organización del repositorio
Estructura anotada (entradas de primer nivel relevantes):

```text
.agent_files/           # plantillas y estilos generados (JSON) para informes
AsientosZapata/         # Aplicaciones FEM para cálculo de asientos de zapatas
ColumnasGrava/          # App Streamlit + motor (método Priebe) + generación de informes
Consolidacion/          # Simulador 1D de consolidación (Terzaghi) + Streamlit
Losas/                  # Módulos FEM/mesher/postprocessing para losas (esqueleto)
MMC_tensores/           # Herramientas para operaciones con tensores (MMC)
PilotesCTE/             # Scripts para dimensionado/análisis de pilotes (CTE)
TaludesTemporales/      # Recursos y app de taludes temporales; incluye documentación AUDIT
ZapatasGCOC/            # App y scripts de zapatas (GCOC) — interfaz e implementación
expansividad/           # App para análisis de expansividad del terreno
slope_stability_app/    # App principal de estabilidad de taludes (GeoSlope) y módulos internos
spt/                    # Interpretación SPT / herramienta SPT
tablas/                 # Generador y librería de tablas/parametrización (engines)
tests/                  # Suite pytest (geometría, validación de entradas, sensibilidad, estabilidad)
LICENSE                 # Licencia del proyecto
README.md               # Este archivo
```

Cómo encaja (resumen)
- Cada carpeta suele ser una aplicación o módulo independiente: entrada de parámetros → motor numérico (cálculo) → visualización (Streamlit / Plotly) → exportación (Excel/Word).
- Los módulos reutilizables (por ejemplo motores de cálculo, generación de informes, tablas de parámetros) están organizados dentro de cada carpeta para mantener cohesión por dominio.

## Resumen de carpetas y programas principales
(qué hace cada programa, archivos clave y notas de ejecución)

- AsientosZapata/
  - app_asientos_FEM_4.py, app_asientos_FEM_4_0.py
    - Aplicaciones que usan un solver FEM para estimar asientos de zapatas. Manejan la interfaz de parámetros, generación de mallado y llamadas al motor numérico.
  - funciones_asientos.py, funciones_asientos_0.py
    - Motor y utilidades FEM: ensamblaje de matrices, condiciones de contorno, resolución y postprocesado de asientos.
  - requirements.txt
    - Dependencias locales (instalar con `pip install -r AsientosZapata/requirements.txt`).

- ColumnasGrava/
  - app.py
    - Interfaz Streamlit que aplica el método de Priebe para columnas de grava: geometría, cálculo de Ac/A, parámetros equivalentes y análisis de sensibilidad.
  - funciones_grava.py
    - Cálculos numéricos (área de columna, relación de sustitución, coeficientes intermedios).
  - informes.py
    - Exportadores a Excel (.xlsx) y Word (.docx) (usa openpyxl / python-docx).
  - README.md (detallado): explica metodología, fórmulas y ejemplos.
  - Ejecución: `streamlit run ColumnasGrava/app.py`

- Consolidacion/
  - consolidacion_streamlit_3.py
    - Simulador 1D basado en la ecuación de Terzaghi. Implementa métodos explícito e implícito (FDM), condiciones de contorno, cálculo de isócronas y exporte de resultados.
  - README.md (completo): teoría, ejemplos de uso y generación de informes.
  - Ejecución: `streamlit run Consolidacion/consolidacion_streamlit_3.py`

- Losas/
  - fem_engine.py, mesher.py, postprocessing.py, app.py (esqueleto)
    - Conjunto orientado al análisis por elementos finitos de losas: generación de mallado, motor FEM (ensamblado) y postprocesado. Algunos ficheros son plantillas o módulos reutilizables.
  - Ejecución: revisar `Losas/requirements.txt` y lanzar la app o integrar el motor en un script.

- MMC_tensores/
  - app.py
    - Interfaz/ejemplo para operaciones tensoriales relevantes en mecánica de medios continuos.
  - tensor_operations.py
    - Funciones para manipulaciones y transformaciones de tensores (contracciones, invariantes, etc.).

- PilotesCTE/
  - PilotesCTE_2.py
    - Script de cálculo y dimensionado de pilotes conforme a criterios de la normativa (CTE). Incluye rutinas de comprobación y salida de resultados.
  - README.md: explicación de uso y ejemplos.

- ZapatasGCOC/
  - app.py, zapatas_GCOC_1.py, README.md
    - Herramientas orientadas al cálculo de zapatas según criterios GCOC: cálculo geométrico, comprobaciones y tablas de resultados.

- TaludesTemporales/
  - README.md y AUDIT.md
    - Documentación extensa, listas de verificación y notas de auditoría. Puede integrar componentes de `slope_stability_app`.

- slope_stability_app/
  - app.py (GeoSlope)
    - Aplicación para estabilidad de taludes por equilibrio límite (Fellenius, Bishop simplificado). Estructura modular:
      - calculations/ — funciones de cálculo
      - models/       — clases de dominio (perfil, capas)
      - services/     — utilidades (IO, export)
      - visualization/— renderizado y gráficas
    - Ejecución: `streamlit run slope_stability_app/app.py`

- spt/
  - app.py, README.md
    - Herramienta SPT: entrada de ensayos, interpretación y tablas de correlación.

- tablas/
  - app.py, build_data.py, soil_params_engine.py
    - Librería y app para construir y servir tablas de parámetros de suelos. `build_data.py` genera las fuentes de datos internas.
  - Ejecución: `streamlit run tablas/app.py` o importar `tablas.soil_params_engine`.

- expansividad/
  - app.py
    - App para analizar riesgos y efectos asociados a suelos expansivos.

- agent_files/
  - estilos_informes_geotecnicos.json
    - Plantilla/estilos en JSON para la generación automatizada de informes (empleada por módulos de informes).

- tests/
  - test_geometry.py, test_input_validation.py, test_sensitivity_and_report.py, test_stability.py
    - Suite pytest que cubre geometría, validación de entradas, sensibilidad de parámetros y estabilidad numérica.

## Cómo ejecutarlo
Ruta mínima desde clonación hasta ejecutar una app

1. Clonar el repositorio:
```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior
```

2. Crear y activar entorno virtual:
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

3. Instalar dependencias por módulo (recomendado — cada app mantiene su requirements):
```bash
pip install -r ColumnasGrava/requirements.txt
pip install -r Consolidacion/requirements.txt
# repetir por cada carpeta que se vaya a usar
```

4. Ejecutar una app Streamlit (ejemplos):
```bash
# GeoSlope (estabilidad de taludes)
streamlit run slope_stability_app/app.py

# Consolidación 1D
streamlit run Consolidacion/consolidacion_streamlit_3.py

# Columnas de grava (Priebe)
streamlit run ColumnasGrava/app.py

# Zapatas (GCOC)
streamlit run ZapatasGCOC/app.py
```

5. Ejecutar tests:
```bash
pytest -q
```

Requisitos
- Python 3.8+ (algunos módulos pueden requerir 3.9+)
- Instalar las dependencias que aparecen en `*/requirements.txt` antes de ejecutar cada app
- Entorno virtual recomendado

## Cómo encajan los módulos
- Las apps comparten un patrón: `app.py` (Streamlit) importa el motor de cálculo y los módulos de export (`informes.py` / `motor_calculo.py`).
- Los resultados se visualizan con Plotly/Matplotlib y pueden exportarse a Excel/Word mediante openpyxl/python-docx.
- `tablas/` actúa como fuente común de parámetros de suelo que otras apps pueden reutilizar.

## Propuestas y siguientes pasos
1. ¿Quieres que cree una rama y abra un PR con esta traducción para revisión antes de dejarlo en `main`?
2. ¿Prefieres que añada un script `setup.sh` o un Makefile para instalar dependencias por módulo automáticamente?
3. ¿Deseas que agregue badges de CI (pytest) y un workflow básico en `.github/workflows`?


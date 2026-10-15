# 🌐 Exterior — Programas de visibilidad exterior (Geotecnia)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-See%20LICENSE-lightgrey)](./LICENSE)

## What this is
Colección de aplicaciones y utilidades en Python (principalmente interfaces Streamlit) para análisis geotécnico exterior: estabilidad de taludes, consolidación 1D, mejora con columnas de grava, asentamientos de zapatas (FEM), dimensionado de pilotes y utilidades de tablas/parametrización. Está orientado a uso académico, investigación y evaluaciones preliminares de diseño.

### Stack
- Language(s): Python (100%)
- Framework / runtime: Streamlit (aplicaciones interactivas), scripts y módulos numéricos
- Notable libraries: numpy, pandas, plotly / matplotlib, openpyxl, python-docx (y utilidades para exportar informes)

## How it's organized
Estructura anotada (entradas de primer nivel relevantes):

```text
.aside: archivos de configuración / LICENSE, README.md (raíz)
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
```

Cómo encaja (resumen)
- Cada carpeta es en general una pequeña aplicación o módulo: entrada de parámetros → motor numérico (cálculo) → visualización (Streamlit / Plotly) → exportación (Excel/Word).
- Los módulos reutilizables (p. ej. motores de cálculo, generación de informes, tablas de parámetros) están organizados dentro de cada carpeta para mantener cohesión por dominio.

## Comentario breve de cada carpeta y programas principales
(qué hace el programa, archivos clave y notas de ejecución)

- AsientosZapata/
  - app_asientos_FEM_4.py, app_asientos_FEM_4_0.py
    - Aplicaciones/ejemplos que usan un solver FEM para estimar asientos de zapatas. Contienen la interfaz (parámetros, elección de mallado) y llamadas al motor numérico.
  - funciones_asientos.py, funciones_asientos_0.py
    - Motor y utilidades FEM: ensamblaje de matrices, condiciones de contorno, resolución y postprocesado de asientos.
  - requirements.txt
    - Dependencias locales (instalar con `pip install -r AsientosZapata/requirements.txt`).

- ColumnasGrava/
  - app.py
    - Interfaz Streamlit que aplica el método de Priebe para columnas de grava: geometría, cálculo de Ac/A, parámetros equivalentes, análisis de sensibilidad.
  - funciones_grava.py
    - Cálculos numéricos (área columna, relaciones de sustitución, coeficientes intermedios).
  - informes.py
    - Exportadores a Excel (.xlsx) y Word (.docx) (usa openpyxl / python-docx).
  - README.md (detallado): explica metodología, fórmulas y ejemplos.
  - usage: `streamlit run ColumnasGrava/app.py`

- Consolidacion/
  - consolidacion_streamlit_3.py
    - Simulador 1D (Terzaghi). Implementa métodos explícito e implícito (FDM), manejo de condiciones de contorno, isócronas y exportes.
  - README.md (muy completo): teoría, ejemplos de uso y generación de informes.
  - usage: `streamlit run Consolidacion/consolidacion_streamlit_3.py`

- Losas/
  - fem_engine.py, mesher.py, postprocessing.py, app.py (esqueleto)
    - Conjunto orientado al análisis por elementos finitos de losas: generación de mallado, motor FEM (ensamblado), y postprocesado. Algunos ficheros actúan como plantilla o módulo reutilizable.
  - usage: revisar `Losas/requirements.txt` y lanzar el app o integrar el motor en un script.

- MMC_tensores/
  - app.py
    - Interfaz/ejemplo para operaciones tensoriales relevantes en mecánica de medios continuos (MMC).
  - tensor_operations.py
    - Funciones para manipulaciones y transformaciones de tensores (contracciones, invariantes, etc.).

- PilotesCTE/
  - PilotesCTE_2.py
    - Script de cálculo y dimensionado de pilotes conforme a criterios/normativa CTE. Incluye rutinas de comprobación y salida de resultados.
  - README.md con explicación de uso y ejemplos.

- ZapatasGCOC/
  - app.py, zapatas_GCOC_1.py, README.md
    - Aplicaciones orientadas al cálculo de zapatas según criterios GCOC: cálculo geométrico, comprobaciones y generación de tablas de resultado.

- TaludesTemporales/
  - README.md y AUDIT.md
    - Documentación extensa y checklist. Incluye app.py pequeño o integraciones con `slope_stability_app` según necesidad.

- slope_stability_app/
  - app.py (GeoSlope — grande, ~28kB)
    - Aplicación para estabilidad de taludes por equilibrio límite (Fellenius, Bishop simplificado). Estructura modular:
      - calculations/ — funciones de cálculo
      - models/ — clases de dominio (perfil, capas)
      - services/ — utilidades (IO, export)
      - visualization/ — renderizado y gráficas
    - usage: `streamlit run slope_stability_app/app.py`

- spt/
  - app.py, README.md
    - Herramienta SPT: entrada de ensayos, interpretación y tablas de correlación.

- tablas/
  - app.py, build_data.py, soil_params_engine.py
    - Biblioteca y app para construir y servir tablas de parámetros de suelos. `build_data.py` contiene scripts para generar las fuentes de datos internas.
  - usage: `streamlit run tablas/app.py` o importar `tablas.soil_params_engine`.

- expansividad/
  - app.py
    - App para analizar riesgos/efectos de suelos expansivos. Contiene lógica de cálculo y GUI.

- agent_files/
  - estilos_informes_geotecnicos.json
    - Plantilla/estilos JSON para generación automatizada de informes (usada por módulos de informes).

- tests/
  - test_geometry.py, test_input_validation.py, test_sensitivity_and_report.py, test_stability.py
    - Suite pytest que cubre geometría, validaciones de entrada, sensibilidad y estabilidad numérica.

## How to run it
(El camino más corto desde clonación a ejecutar una app)

1. Clona el repo:
```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior
```

2. Entorno virtual y dependencias:
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

3. Instala dependencias por módulo (recomendado — cada app mantiene su requirements):
```bash
pip install -r ColumnasGrava/requirements.txt
pip install -r Consolidacion/requirements.txt
# etc. para cada carpeta que vayas a usar
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

Requisitos obvios
- Python 3.8+ (algunos módulos pueden requerir 3.9+)
- Instala dependencias que aparecen en `*/requirements.txt` antes de ejecutar cada app.
- Entorno virtual recomendado.

## How it fits together
- Las apps comparten patrones: `app.py` (Streamlit) importa un motor de cálculo y módulos de export (informes.py / motor_calculo.py).
- Los resultados se muestran con Plotly/Matplotlib y pueden exportarse a Excel/Word mediante openpyxl/python-docx.
- `tablas/` actúa como fuente común de parámetros de suelo que otras apps pueden reutilizar.

## Try asking
1. ¿Quieres que actualice y unifique el README raíz escribiendo la descripción y comentarios (por carpeta) directamente en la rama principal?
2. ¿Prefieres que convierta las instrucciones de instalación en un Makefile / script `setup.sh` para instalar dependencias por módulo automáticamente?
3. ¿Deseas que añada badges de CI (pytest) y comprobaciones de estilo (flake8) y cree un pipeline básico en .github/workflows?

---
Última revisión: descripción generada automáticamente desde el contenido de cada carpeta y archivos principales (app.py, motores y README por módulo). Si quieres, puedo:
- Generar el README.md en la rama principal y crear el commit,
- O generar una rama con el cambio y abrir un PR para revisión.
¿Cómo prefieres que proceda?

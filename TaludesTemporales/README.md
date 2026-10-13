# 🏗️ GeoSlope — Estabilidad de taludes temporales

Aplicación desarrollada en Python con Streamlit para el análisis preliminar de taludes temporales mediante equilibrio límite y superficies de falla circulares.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.49%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![pytest](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)

## 📌 Descripción

GeoSlope permite evaluar la estabilidad de taludes simples con una interfaz gráfica orientada a ingeniería geotécnica. La herramienta integra:

- Cálculo de estabilidad por equilibrio límite con superficies circulares
- Métodos de Fellenius y Bishop simplificado
- Modelado de uno o dos estratos de suelo con ley de Mohr-Coulomb
- Presión de poros hidrostática
- Análisis de sensibilidad y reportes
- Visualización del talud, superficie crítica y dovelas

La aplicación está pensada para un análisis preliminar, útil para revisión rápida de configuraciones geométricas y parámetros geotécnicos.

## ✨ Características principales

- 🧭 Interfaz de usuario con pestañas para proyecto, geometría, suelos, cálculo, sensibilidad, resultados y visualización
- 📐 Validación automática de entradas geométricas y de suelo
- 📊 Generación de gráficos de perfil, superficie crítica y distribución de esfuerzos
- 🧪 Suite de pruebas automatizadas para validación funcional
- 📝 Exportación de resultados y reportes para revisión técnica
- ⚙️ Base modular y extensible para futuras mejoras del núcleo de cálculo

## 🏛️ Estructura del proyecto

```text
TaludesTemporales/
├── app.py                           # Launcher principal de la aplicación
├── requirements.txt                 # Dependencias del proyecto
├── README.md                        # Documentación del módulo
├── AUDIT.md                         # Registro de revisión o auditoría
├── slope_stability_app/
│   ├── __init__.py
│   ├── app.py                      # Lógica principal de la interfaz Streamlit
│   ├── calculations/               # Fórmulas y cálculos de estabilidad
│   ├── models/                     # Modelos de datos y estructuras
│   ├── services/                   # Servicios y lógica de negocio
│   ├── utils/                      # Utilitarios y validaciones
│   └── visualization/              # Visualización de resultados y perfiles
└── tests/
    ├── test_geometry.py
    ├── test_input_validation.py
    ├── test_sensitivity_and_report.py
    └── test_stability.py
```

## 🚀 Requisitos

- Python 3.10 o superior
- pip
- Entorno virtual recomendado

## ⚙️ Instalación y ejecución

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

La aplicación normalmente queda disponible en:

```text
http://localhost:8501
```

## 🧠 Alcance del análisis

El proyecto cubre un alcance funcional específico para taludes simples:

- Sección 2D por metro de longitud
- Longitudes en metros, pesos unitarios en kN/m³, esfuerzos y cohesión en kPa
- Pendiente medida respecto a la horizontal
- Cotas referidas al pie del talud
- Modelado con uno o dos estratos
- Búsqueda discreta de superficies circulares con entrada en la corona y salida en la cara o berma inferior

### Limitaciones conocidas

No se incluyen, entre otros, los siguientes casos:

- 🚫 Sobrecargas
- 🚫 Sismo
- 🚫 Refuerzos
- 🚫 Agua exterior no hidroestática
- 🚫 Succión o filtración compleja
- 🚫 Etapas de excavación
- 🚫 Mecanismos no circulares

## 🧪 Verificación

Para ejecutar la validación automatizada del proyecto:

```bash
pytest -q
```

Las pruebas cubren aspectos clave como:

- Geometría del talud
- Validación de entradas
- Cálculo de estabilidad
- Sensibilidad del análisis
- Generación de reportes
- Casos adversos y rangos de entrada

## 📁 Archivos relevantes

- `app.py`: punto de entrada para lanzar la aplicación
- `slope_stability_app/app.py`: lógica principal de la interfaz y flujo de cálculo
- `tests/`: validaciones automatizadas del comportamiento esperado
- `requirements.txt`: dependencias mínimas del proyecto

## 🛠️ Tecnologías empleadas

- Python
- Streamlit
- NumPy
- Pandas
- Plotly
- Matplotlib
- pytest
- python-docx

## 📘 Uso recomendado

Este proyecto es adecuado para:

- Análisis preliminar de estabilidad
- Evaluación rápida de taludes temporales
- Estudio de sensibilidad paramétrica
- Validación conceptual de geometrías y parámetros de suelo

Para un estudio de diseño final, se recomienda complementar con criterios específicos de la normativa geotécnica aplicable y revisión técnica del ingeniero responsable.

## 👷 Autoría y mantenimiento

Proyecto orientado a ingeniería geotécnica y análisis de estabilidad de taludes. Se recomienda mantener la documentación y pruebas sincronizadas con cada cambio funcional del núcleo de cálculo.


# 🏗️ Asientos de zapata rectangular flexible

Aplicación desarrollada en Python con Streamlit para evaluar asentamientos elásticos en cimentaciones superficiales, considerando una zapata rectangular flexible apoyada sobre terreno estratificado y sometida a carga neta uniforme.

El programa integra la distribución de tensiones de Boussinesq, el módulo de deformación por capas y la comparación con un cálculo independiente basado en la formulación de Steinbrenner. Su objetivo es apoyar la verificación geotécnica de asentamientos bajo la base de cimentación, con visualización gráfica y exportación de resultados.

## 🎯 Objetivo del programa

El software permite:

- Calcular asentamientos verticales bajo puntos de control de una zapata rectangular flexible.
- Modelar suelos estratificados con propiedades variables en profundidad.
- Evaluar la influencia del nivel freático y de la variación de módulo del terreno.
- Analizar la distribución de tensiones y deformaciones bajo la cimentación.
- Comparar dos metodologías de cálculo: integración vertical y Steinbrenner.
- Generar informes DOCX y datos XLSX para documentación técnica.

## ✨ Funcionalidades principales

- Cálculo de asentamientos por integración vertical de Δσz/M.
- Cálculo alternativo según Steinbrenner con E y ν.
- Definición de geometría de cimentación y suelo multicapa.
- Control de profundidad, paso de discretización y validación geométrica.
- Representación del bulbo de influencia y perfiles de tensión.
- Generación de gráficos de resultados y contribución por estrato.
- Exportación de informes y datos en formatos profesionales.

## 📁 Estructura del proyecto

```text
Asientos_Zapata_ITQ/
├── app.py                          # Punto de entrada principal de la interfaz Streamlit
├── requirements.txt                # Dependencias del proyecto
├── README.md                      # Documentación del proyecto
├── calculos/                      # Módulos de cálculo geotécnico
│   ├── __init__.py
│   ├── asientos.py                # Cálculo principal de asentamientos
│   ├── boussinesq.py              # Fórmulas de Boussinesq
│   ├── geostatica.py              # Tensiones geostáticas y nivel freático
│   └── steinbrenner.py            # Cálculo de Steinbrenner
├── modelos/                       # Definiciones de datos y validación del caso
│   ├── __init__.py
│   └── datos.py                   # Estructuras, estratos de ejemplo y validación
├── servicios/                     # Exportación de resultados
│   ├── __init__.py
│   ├── exportacion_docx.py        # Generación de informe DOCX
│   └── exportacion_excel.py       # Generación de hoja XLSX
├── utiles/                        # Utilidades y estilos visuales
│   ├── __init__.py
│   └── estilos.py                 # CSS personalizado de la aplicación
├── visualizacion/                 # Generación de gráficos y visualizaciones
│   ├── __init__.py
│   └── graficos.py                # Figuras con Plotly
├── tests/                         # Pruebas unitarias del programa
│   ├── test_asientos.py
│   ├── test_boussinesq.py
│   ├── test_exportaciones.py
│   ├── test_geostatica.py
│   └── test_steinbrenner.py
└── .venv/                         # Entorno virtual local (si se crea en el equipo)
```

## 🧮 Cometido del programa

La aplicación está orientada a la ingeniería geotécnica y permite realizar una evaluación práctica de asentamientos en cimentaciones superficiales bajo condiciones de carga vertical y terreno estratificado. En concreto, el sistema:

- analiza una zapata rectangular flexible con geometría B × L,
- considera presión neta uniforme sobre la base,
- integra la variación de tensiones con la profundidad,
- modela el comportamiento del terreno mediante módulos deformacionales por capa,
- incorpora efectos del nivel freático y de la estratigrafía,
- compara soluciones mediante dos enfoques de cálculo,
- presenta resultados numéricos y gráficos para toma de decisiones técnicas.

## ⚙️ Requisitos

- Python 3.10 o superior
- Entorno virtual recomendado
- Paquetes indicados en `requirements.txt`

Instalación:

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## ▶️ Ejecución

```bash
streamlit run app.py
```

La aplicación abrirá la interfaz web para definir geometría, estratos del terreno, condiciones de carga y revisar resultados.

## 🧪 Validación

Se incluye una batería de pruebas automatizadas con `pytest` para verificar:

- cálculo de asentamientos,
- distribución de tensiones de Boussinesq,
- condiciones geostáticas,
- formulación de Steinbrenner,
- exportación de resultados.

Ejecución:

```bash
pytest -q
```

## 📌 Convenciones del cálculo

- Longitudes en metros.
- Tensiones en kPa o kN/m².
- Módulos de entrada en MPa y conversión interna a kPa.
- Asientos mostrados en milímetros.
- Profundidad positiva hacia abajo.
- Compresión como valor positivo.

## 🧭 Nota técnica

La solución implementada es una aproximación de ingeniería para terrenos estratificados y no sustituye un análisis geotécnico completo cuando se requiere modelado avanzado de consolidación, plasticidad, anisotropía o interacción suelo-estructura.

## 📎 Licencia y uso

Proyecto orientado a uso técnico y académico dentro del contexto de análisis de cimentaciones superficiales. Se recomienda revisar y validar los resultados frente a exigencias específicas de cada proyecto, normativa local y criterio del ingeniero responsable.

---

Desarrollado para análisis de asientos de zapata flexible en terreno multicapa.

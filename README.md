# 🏗️ Exterior

Suite de aplicaciones geotécnicas y de análisis estructural desarrolladas en Python para apoyo técnico en proyectos de ingeniería civil, perfiles geológicos, cimentaciones y mejora del terreno.

El repositorio reúne varias herramientas orientadas a la modelización, cálculo y documentación técnica, con interfaces construidas en Streamlit y motor de cálculo basado en Python, NumPy, pandas, Plotly y bibliotecas especializadas.

## ✨ Visión general

Exterior está organizado como una colección de módulos y apps temáticas, cada una enfocada en un problema geotécnico concreto:

- GeoPerfil 2D para perfiles geológicos e interpretación de sondeos.
- AsientosZapata para cálculo de asiento de zapatas rectangulares.
- ColumnasGrava para mejora del terreno con columnas de grava.
- Correlaciones para cálculo de propiedades geotécnicas mediante correlaciones.
- Módulos adicionales para cimentaciones, taludes, lazos de carga, consolidación y otros análisis.

## 📁 Estructura principal del repositorio

```text
Exterior/
├── .github/                       # Configuración de GitHub y automatización
├── AsientosZapata/                # Cálculo de asientos elásticos de zapatas
├── ColumnasGrava/                 # Mejora del terreno con columnas de grava
├── Consolidacion/                 # Análisis de consolidación
├── Correlaciones/                 # Correlaciones geotécnicas y regresiones
├── Losas/                        # Diseño y comprobación de losas
├── MMC_tensores/                  # Matriz de rigidez y tensores / análisis geotécnico
├── PilotesCTE/                    # Cimentaciones profundas y pilotes
├── TaludesTemporales/             # Estabilidad de taludes temporales
├── ZapatasGCOC/                  # Zapatas con criterios GCOC
├── agent_files/                   # Archivos auxiliares de agentes / automatización
├── calculos/                     # Utilidades de cálculo matemático y geotécnico
├── componentes/                   # Componentes reutilizables de la interfaz / CAD
├── ejemplos/                     # Casos de ejemplo y plantillas
├── expansividad/                 # Análisis de expansión de suelos
├── geoperfil/                    # Módulo principal de GeoPerfil 2D
├── modelos/                      # Modelos de datos y dominio
├── paginas/                      # Vistas y páginas de la aplicación principal
├── servicios/                    # Importación/exportación, persistencia y servicios
├── slope_stability_app/          # Aplicación de estabilidad de taludes
├── spt/                          # Datos y cálculos relacionados con SPT
├── tablas/                       # Tablas y estructuras auxiliares
├── tests/                        # Pruebas automatizadas
├── utiles/                       # Funciones auxiliares y utilidades varias
├── visualizacion/                # Gráficos, Plotly y visualización de resultados
├── app.py                        # Entrypoint principal del proyecto
├── estilos.css                   # Estilos globales de la interfaz
├── requirements.txt              # Dependencias principales
├── iniciar_linux.sh              # Lanzador para Linux
├── iniciar_windows.bat           # Lanzador para Windows
├── LICENSE                       # Licencia del proyecto
├── README.md                     # Documentación del repositorio
├── __init__.py                   # Paquete raíz
└── ...                           # Módulos específicos por disciplina geotécnica
```

## 🧩 Aplicaciones y módulos clave

### 1) GeoPerfil 2D
Este módulo constituye la herramienta principal del repositorio para interpretación geológica y trazado de perfiles 2D.

Incluye:

- Importación y validación de datos de sondeos
- Representación de perfiles geológicos
- Interfaz de edición y análisis con MiniCAD
- Visualización con Plotly y exportación de resultados
- Gestión de geometrías y zonas interpretadas

Ubicación principal:

- `geoperfil/`
- `app.py`
- `paginas/`
- `calculos/`
- `visualizacion/`

### 2) AsientosZapata
Aplicación orientada al cálculo de asientos inmediatos de zapatas rectangulares usando:

- Método analítico de Steinbrenner
- Modelo 3D por elementos finitos con OpenSeesPy
- Generación automática de memoria y reportes en Word

### 3) ColumnasGrava
Herramienta para evaluar la mejora del terreno mediante columnas de grava, aplicando la metodología de Priebe.

Incluye:

- Cálculo de parámetros equivalentes
- Evaluación de geometría de la malla y relación de sustitución
- Gráficos comparativos de resultados
- Informes en Excel y Word

### 4) Correlaciones
Módulo de correlaciones geotécnicas para derivar parámetros a partir de ensayos de campo y tablas normalizadas.

Se apoya en:

- SPT, DMT, molinete, presiómetro y otros ensayos
- Tratamiento de unidades y dominios
- Interpolación de resultados
- Generación de informes y fichas de proyecto

### 5) Casos específicos del repositorio
Además de las apps principales, el repositorio incluye varias carpetas temáticas para otros análisis geotécnicos:

- `Consolidacion` — consolidación
- `Losas` — losas
- `PilotesCTE` — cimentaciones profundas
- `TaludesTemporales` — estabilidad de taludes
- `ZapatasGCOC` — zapatas y criterios de diseño
- `expansividad` — comportamiento expansivo
- `slope_stability_app` — estabilidad de taludes

## 🛠️ Stack tecnológico

El proyecto usa principalmente:

- Python 3
- Streamlit
- NumPy
- pandas
- Plotly
- Matplotlib
- OpenSeesPy (en módulos específicos)
- python-docx
- openpyxl / Excel automation
- pytest (pruebas y validación)

## 🚀 Cómo ejecutar

1. Crear un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# o .venv\Scripts\activate  # Windows
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación principal:

```bash
streamlit run app.py
```

O bien, si se trabaja desde un módulo concreto, se puede ejecutar la app específica dentro de la carpeta correspondiente.

## 📦 Dependencias generales

El archivo `requirements.txt` del repositorio raíz incluye la base necesaria para la mayoría de las funciones principales, y cada carpeta especializada puede disponer de sus propios requisitos según la herramienta concreta.

## 🧪 Calidad y validación

El proyecto incorpora una estructura orientada a pruebas y validación técnica:

- `tests/` para pruebas automatizadas
- Verificación de cálculos y flujo de datos
- Exportación de informes y resultados
- Validación de modelos geotécnicos y de interfaz

## 📜 Licencia

Este repositorio usa la licencia GNU General Public License v3.0.

## 👷 Propósito del repositorio

Exterior está pensado como una plataforma de cálculo y visualización geotécnica para apoyar:

- interpretación de perfiles geológicos
- diseño de cimentaciones
- evaluación de suelos mejorados
- cálculo de propiedades geotécnicas
- documentación técnica y exportación de resultados

## ✅ Resumen

El proyecto combina varias herramientas geotécnicas en un mismo ecosistema, con enfoque en ingeniería civil, validación técnica y automatización de cálculo. Su organización modular permite ampliar nuevas funcionalidades sin perder la trazabilidad y la estructura del análisis.

---

© 2026 Exterior · Repositorio geotécnico profesionalizado con Python y Streamlit

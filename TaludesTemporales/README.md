# 📐 Taludes Temporales

Aplicación de análisis preliminar de estabilidad de taludes temporales desarrollada en Python con Streamlit. El proyecto está orientado a evaluar la seguridad de taludes simples mediante métodos de equilibrio límite, con enfoque en superficies circulares y análisis de geometría, estratigrafía, nivel freático y sensibilidad paramétrica.

## 🧭 Descripción general

Esta carpeta contiene la implementación completa de una herramienta para:

- Definir geometría del talud y estratigrafía multicapa.
- Evaluar estabilidad mediante métodos clásicos de equilibrio límite.
- Explorar superficies críticas y factores de seguridad.
- Revisar sensibilidad ante variaciones de parámetros geotécnicos.
- Visualizar resultados y perfiles del talud en una interfaz interactiva.

La solución combina lógica de cálculo, validación de entradas, generación de reportes y visualización gráfica en un entorno de trabajo accesible para análisis preliminares.

## 📁 Estructura del proyecto

```text
TaludesTemporales/
├── README.md                  # Documentación del proyecto
├── AUDIT.md                   # Evidencia o auditoría técnica del proyecto
├── app.py                     # Punto de entrada para ejecutar la aplicación
├── requirements.txt           # Dependencias de Python
├── agent_files/               # Archivos auxiliares o generados por agentes
├── tests/                     # Pruebas automatizadas del comportamiento principal
├── slope_stability_app/       # Módulo principal de la aplicación
│   ├── __init__.py
│   ├── app.py                 # Lógica y UI principal de Streamlit
│   ├── calculations/          # Geometría, búsqueda de superficies y estabilidad
│   │   ├── geometry.py
│   │   ├── search.py
│   │   ├── sensitivity.py
│   │   └── stability.py
│   ├── models/                # Modelos de entrada y configuración del problema
│   │   └── inputs.py
│   ├── services/              # Validación y generación de reportes
│   │   ├── validation.py
│   │   └── report.py
│   ├── utils/                 # Utilidades auxiliares
│   └── visualization/         # Funciones y componentes para representación visual
```

## 🏗️ Componentes principales

### 1) Aplicación principal

- `app.py` ejecuta la interfaz de usuario.
- `slope_stability_app/app.py` concentra la lógica de presentación y la experiencia del usuario en Streamlit.
- Permite navegar entre secciones de proyecto, geometría, geotecnia, cálculo, sensibilidad, resultados y visualización.

### 2) Cálculos geotécnicos

En `slope_stability_app/calculations/` se implementan las funciones relacionadas con:

- Geometría del talud y del perfil estratigráfico.
- Búsqueda de superficies potencialmente críticas.
- Cálculo de estabilidad con métodos de equilibrio límite.
- Análisis de sensibilidad frente a parámetros de terreno.

### 3) Modelado de entradas

En `models/inputs.py` se define la estructura de datos para:

- Propiedades del talud.
- Capas de suelo.
- Parámetros resistentes.
- Nivel freático.
- Configuración del análisis.

### 4) Validación y reportes

En `services/` se gestionan:

- Validación de datos y consistencia de entradas.
- Generación de informes de resultados y diagnósticos.
- Control de errores y mensajes útiles para el usuario.

### 5) Visualización

La carpeta `visualization` está enfocada en la representación gráfica del perfil, la superficie crítica y los resultados del análisis para facilitar la interpretación técnica.

## 🧪 Calidad y validación

El proyecto incluye una carpeta `tests/` para verificar:

- Geometría del talud.
- Cálculo de fuerzas y dovelas.
- Convergencia del método.
- Condiciones con nivel freático bajo el pie.
- Perfiles multicapa.
- Entradas adversas y validación de robustez.

Además, el archivo `AUDIT.md` aporta documentación complementaria de revisión y control del proyecto.

## ⚙️ Requisitos y ejecución

1. Crear un entorno virtual:

```bash
python -m venv .venv
```

2. Activarlo:

- Linux/macOS:

```bash
source .venv/bin/activate
```

- Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecutar la aplicación:

```bash
streamlit run app.py
```

La interfaz suele abrirse en:

```text
http://localhost:8501
```

## 🎯 Alcance del análisis

Esta herramienta está diseñada para análisis preliminares de taludes temporales con enfoque práctico y académico. El cálculo se centra en condiciones típicas de estabilidad por equilibrio límite, considerando:

- Geometría 2D de sección unitaria.
- Suelos con capas horizontales.
- Parámetros efectivos de resistencia.
- Presión de poros hidrostatica.
- Búsqueda de superficies circulares críticas.

No reemplaza un estudio geotécnico completo ni contempla todos los mecanismos avanzados de estabilidad, pero sí aporta una base útil para evaluación inicial, comparación de escenarios y toma de decisiones preliminares.

## ✅ Resumen

`TaludesTemporales` es un módulo funcional y bien estructurado para análisis de estabilidad de taludes mediante una aplicación interactiva. Su arquitectura separa claramente:

- entrada de datos,
- cálculos geotécnicos,
- validación,
- visualización,
- y documentación técnica.

Esto facilita mantenimiento, extensión y uso en entornos de análisis preliminar y académico.

---

Desarrollado para análisis y evaluación de estabilidad de taludes temporales en entorno Python/Streamlit.

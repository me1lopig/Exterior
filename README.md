# 🏗️ Exterior — Herramientas geotécnicas con Python y Streamlit

> Colección de aplicaciones para análisis, diseño y verificación geotécnica en cimentaciones y mejora del terreno.

---

## 📌 Descripción general

El repositorio **Exterior** reúne una serie de herramientas de cálculo y análisis geotécnico desarrolladas en **Python** con **Streamlit**, orientadas a la resolución de problemas reales de cimentaciones, asentamientos, consolidación, estructura del terreno y soluciones de mejora.

Cada módulo está pensado para ser una herramienta técnica autónoma, con interfaz visual, cálculos parametrizados y exportación de resultados para uso profesional.

---

## 🧩 Estructura del repositorio

```text
Exterior/
├── .github/                  # Configuración y automatización de GitHub
├── AsientosZapata/           # Asientos en zapatas y análisis de carga
├── ColumnasGrava/            # Mejora de suelos con columnas de grava
├── Consolidacion/            # Consolidación unidimensional
├── PilotesCTE/               # Diseño de pilotes según CTE DB-SE-C
├── ZapatasGCOC/              # Dimensionamiento de zapatas según GCOC
├── expansividad/             # Evaluación de suelos expansivos
├── parametrizacion/          # Parametrización geotécnica
├── spt/                      # Análisis de ensayos SPT
├── zapatasCTE/               # Cálculo de hundimiento según CTE
├── LICENSE                   # Licencia del repositorio
├── README.md                 # Documentación principal
└── ...
```

---

## 🏗️ Módulos disponibles

| Módulo | Enfoque principal | Tecnologías | Estado |
|---|---|---|---|
| **AsientosZapata** | Asientos en cimentaciones superficiales | Streamlit, NumPy, Pandas, Matplotlib | ✅ Activo |
| **ColumnasGrava** | Mejora de suelo con columnas de grava | Streamlit, NumPy, Pandas, Plotly | ✅ Activo |
| **Consolidacion** | Consolidación 1D y asientos temporales | Streamlit, NumPy, Pandas, Plotly | ✅ Activo |
| **PilotesCTE** | Diseño de pilotes según CTE | Streamlit, NumPy, Pandas, Plotly | ✅ Activo |
| **ZapatasGCOC** | Dimensionamiento de zapatas según GCOC | Streamlit, NumPy, Pandas, Plotly | ✅ Activo |
| **expansividad** | Evaluación de suelos expansivos | Python, análisis geotécnico | ✅ Base |
| **parametrizacion** | Parametrización geotécnica | Python, Pandas, NumPy | ✅ Base |
| **spt** | Interpretación de ensayos SPT | Python, análisis de suelos | ✅ Base |
| **zapatasCTE** | Hundimiento de zapatas según CTE | Streamlit, NumPy, Pandas | ✅ Activo |

---

## 🎯 Áreas de aplicación

- Cimentaciones superficiales
- Cimentaciones profundas
- Asientos y deformaciones del terreno
- Consolidación y drenaje
- Mejoras del terreno
- Suelos expansivos y problemáticos
- Verificación de estructuras apoyadas en suelo

---

## 🚀 Cómo empezar

### Requisitos previos

- Python 3.8 o superior
- Entorno virtual recomendado
- Dependencias específicas por módulo

### Instalación general

```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior
```

Luego, entra en la carpeta de cada aplicación y ejecuta su `requirements.txt`:

```bash
cd AsientosZapata
pip install -r requirements.txt
```

Y para arrancar la app:

```bash
streamlit run app.py
```

> En cada módulo la interfaz principal puede llamarse distinto (`app.py`, `app_asientos_FEM_4.py`, `PilotesCTE_2.py`, etc.).

---

## 📚 Principales metodologías incluidas

- Método de Brinch-Hansen adaptado a GCOC
- Cálculo de capacidad portante de zapatas
- Análisis de asentamientos por métodos elásticos y numéricos
- Consolidación unidimensional de Terzaghi
- Diseño de pilotes según normativas españolas
- Homogeneización de terrenos mediante columnas de grava
- Evaluación de suelos expansivos y parámetros de terreno

---

## 🧠 Objetivo del repositorio

Este repositorio sirve como entorno de aprendizaje, prototipado y validación técnica para aplicaciones geotécnicas en Python. Su finalidad es facilitar la automatización de cálculos, la visualización de resultados y la generación de documentación técnica para proyectos reales.

---

## 📜 Licencia

Este repositorio se distribuye bajo la licencia **GNU GPL v3.0**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## 🤝 Contacto

Si quieres colaborar, reportar un problema o proponer mejoras, puedes contactar con el mantenedor del repositorio desde GitHub.

---

## 🏁 Resumen

**Exterior** es una colección técnica y académica de herramientas geotécnicas para análisis, verificación y diseño de cimentaciones y mejora del terreno, desarrolladas con enfoque profesional, visualización clara y exportación de resultados útiles para ingeniería.

# 🏗️ ZapatasGCOC — Dimensionamiento de cimentaciones superficiales

> Herramienta para el diseño y verificación de zapatas según la Guía de Cimentaciones en Obras de Carretera (GCOC).

---

## 📌 Descripción general

**ZapatasGCOC** es un módulo geotécnico para el dimensionamiento y verificación de **zapatas** cimentadas en suelo. Está basado en una adaptación de la formulación de **Brinch-Hansen** y en criterios de la **Guía de Cimentaciones en Obras de Carretera (GCOC)**.

La aplicación permite trabajar con dos escenarios principales:

- Pre-dimensionamiento de zapatas mediante cartas de tensiones admisibles
- Verificación estructural con cargas reales y comprobación de seguridad

---

## 🧩 Funcionalidades principales

- Cálculo de capacidad portante bajo hundimiento
- Verificación de factor de seguridad frente a hundimiento
- Análisis para zapatas rectangulares, corridas y circulares
- Consideración de excentricidad y nivel freático
- Visualización en gráficos interactivos y mapas de calor
- Exportación de resultados para análisis posterior

---

## 📁 Estructura del módulo

```text
ZapatasGCOC/
├── app.py                   # Interfaz principal
├── zapatas_GCOC_1.py       # Motor de cálculo
├── requirements.txt        # Dependencias del módulo
├── README.md               # Documentación del proyecto
└── ...
```

---

## 🚀 Ejecución

### Requisitos

- Python 3.8 o superior
- Dependencias indicadas en `requirements.txt`

### Instalación

```bash
cd ZapatasGCOC
pip install -r requirements.txt
```

### Arranque

```bash
streamlit run app.py
```

---

## 📊 Salidas relevantes

- Tensiones admisibles por geometría
- Verificación de factores de seguridad
- Gráficos interactivos de resistencia y comportamiento
- Tablas de resultados para comparación de alternativas

---

## 🧠 Casos de uso

- Dimensionamiento rápido de zapatas
- Verificación de zapatas existentes
- Estudios preliminares de cimentación superficial
- Comparación de distintas geometrías y condiciones de terreno

---

## 📜 Licencia

Este módulo forma parte del repositorio principal **Exterior** y sigue la licencia del proyecto.

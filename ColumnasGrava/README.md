# 🏗️ ColumnasGrava — Sistema de Cálculo de Mejora de Terrenos

> Herramienta profesional de ingeniería geotécnica para el análisis y diseño de soluciones con columnas de grava

---

## 📌 Descripción general

**ColumnasGrava** es una aplicación desarrollada en Python con **Streamlit** para evaluar la mejora del comportamiento del terreno mediante columnas de grava, siguiendo los principios del método de homogeneización propuesto por **Priebe (1995)**. La herramienta automatiza cálculos geotécnicos complejos y genera resultados técnicos listos para su uso en documentos de proyecto.

El sistema permite:

- Analizar la mejora del terreno según la geometría de la columna
- Evaluar la influencia del tipo de malla y el espaciado
- Determinar parámetros equivalentes del terreno tratado
- Generar informes técnicos en **Excel** y **Word** de forma automática

---

## 🎯 Objetivo del proyecto

El objetivo principal es automatizar el cálculo y la documentación de la mejora de suelos mediante columnas de grava, cubriendo las siguientes necesidades:

- Estimación de la geometría de la inclusión y del área tributaria
- Cálculo de la relación de sustitución Ac/A
- Evaluación de parámetros intermedios del método de Priebe
- Determinación de parámetros equivalentes del terreno mejorado
- Seguimiento de la evolución de fricción, cohesión y módulo elástico
- Generación de informes profesionales para uso técnico y administrativo

---

## 🧩 Arquitectura del proyecto

```text
ColumnasGrava/
├── app.py
├── funciones_grava.py
├── informes.py
├── requirements.txt
├── README.md
└── __pycache__/
```

### 1) `app.py` — Interfaz principal

Archivo central de la aplicación con interfaz gráfica desarrollada en **Streamlit**.

**Responsabilidades principales:**
- Configuración de la página principal
- Entrada de parámetros del terreno y de la grava
- Visualización de tablas y gráficas
- Descarga de resultados en Excel y Word
- Presentación de formulaciones del método Priebe

**Pestañas principales:**
- 📋 **Tablas de datos**
- 📈 **Gráficas**
- 📥 **Descargas**
- 🧮 **Formulaciones usadas**

### 2) `funciones_grava.py` — Motor de cálculo

Módulo matemático encargado de realizar los cálculos de homogeneización del terreno.

**Función principal:**
- `calcular_mejora_excel(...)`

**Proceso interno:**
- Cálculo del área de la columna de grava
- Determinación de áreas tributarias para malla cuadrícula y tresbolillo
- Cálculo de la relación Ac/A
- Evaluación de factores intermedios y coeficientes del método de Priebe
- Generación de la tabla final con parámetros equivalentes

### 3) `informes.py` — Generación de informes

Módulo encargado de exportar la información en formatos técnicos estándar.

**Funciones relevantes:**
- `generar_excel_memoria(...)`
- `generar_word_memoria(...)`

**Salida generada:**
- 📊 Libro Excel con varias hojas de resultados
- 📄 Documento Word con memoria de cálculo y gráficos

### 4) `requirements.txt` — Dependencias

Archivo con las librerías necesarias para ejecutar la aplicación:
- Streamlit
- NumPy
- Pandas
- Plotly
- python-docx
- xlsxwriter
- openpyxl
- kaleido

---

## 📐 Metodología aplicada

La herramienta implementa la lógica del **Método de Priebe (1995)** para estimar la mejora del comportamiento del terreno tras la introducción de columnas de grava.

### Consideraciones del modelo

El análisis considera:
- Propiedades del suelo original
- Propiedades del material granular
- Geometría de la malla
- Coeficiente de Poisson del terreno
- Relación entre el área de columna y el área tributaria

### Fórmulas principales

**Área de la columna**

```text
Ac = π · D² / 4
```

**Área tributaria para malla cuadrícula**

```text
A = s²
```

**Área tributaria para malla tresbolillo**

```text
A = (√3 / 2) · s²
```

**Tasa de sustitución**

```text
r = Ac / A
```

**Parámetros equivalentes**

```text
φ_eq = arctan[m · tan(φc) + (1 - m) · tan(φs)]
c_eq = c_s · (1 - m)
E_eq = E_s · (1 - m) + E_c · m
```

Con este conjunto de ecuaciones, la aplicación estima la mejora del suelo tratado y presenta la evolución de sus parámetros frente a la situación inicial.

---

## 🚀 Requisitos para ejecutar

### Requisitos mínimos
- Python 3.9 o superior
- Entorno virtual recomendado
- Dependencias listadas en `requirements.txt`

### Instalación

```bash
pip install -r requirements.txt
```

### Ejecución

```bash
streamlit run app.py
```

---

## 📊 Resultados esperados

La aplicación genera:

- Tablas con geometría y relaciones de sustitución
- Cálculos intermedios del método Priebe
- Parámetros equivalentes de fricción, cohesión y módulo elástico
- Gráficos comparativos por diámetro de columna
- Archivos Excel y Word para documentación técnica

---

## 🧠 Casos de uso

Este proyecto es útil para:

- Análisis preliminares de mejora de suelos
- Diseño de columnas de grava en obras geotécnicas
- Estudio de sensibilidad vinculada al diámetro y espaciado
- Comparación de diferentes alternativas de diseño
- Generación de memoria de cálculo y documentación técnica

---

## 🏁 Conclusión

**ColumnasGrava** reúne la lógica geotécnica del método de Priebe, la potencia del análisis numérico en Python y la facilidad de uso de Streamlit para convertir un cálculo técnico complejo en una herramienta accesible, visual y exportable.

La carpeta está organizada para servir como base de cálculo, análisis y documentación técnica para proyectos de mejora de suelo mediante columnas de grava.

---

## 🔗 Información general

- Proyecto: **Exterior / ColumnasGrava**
- Lenguaje principal: **Python**
- Interfaz: **Streamlit**
- Objetivo: **Diseño y análisis de columnas de grava**

---

## 📝 Nota

Este README está orientado a un uso profesional, técnico y de presentación para repositorios de ingeniería y proyectos de análisis geotécnico.

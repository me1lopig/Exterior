# 🏗️ ZapatasCTE — Cálculo de hundimiento según CTE DB SE-C

> Herramienta para el análisis de capacidad portante y hundimiento en cimentaciones superficiales según el Código Técnico de la Edificación.

---

## 📌 Descripción general

**ZapatasCTE** es una aplicación geotécnica para el cálculo de **capacidad portante** y verificación frente a **hundimiento** en zapatas según el **CTE DB SE-C**. El módulo integra criterios de resistencia y seguridad con la geometría de la fundación y las propiedades del terreno.

Se puede utilizar para análisis de cimentaciones superficiales con distintos tipos de zapata y condiciones de terreno.

---

## 🧩 Funcionalidades principales

- Análisis de capacidad portante bajo hundimiento
- Cálculo de presión admisible
- Soporte para zapatas rectangulares, corridas y circulares
- Distinción entre suelos drenados y no drenados
- Consideración de taludes, inclinación de carga y nivel freático
- Barrido geométrico para comparar alternativas
- Visualización de resultados en tablas y gráficos

---

## 📁 Estructura del módulo

```text
zapatasCTE/
├── app.py                  # Interfaz de usuario
├── motor_calculo.py        # Motor de cálculo geotécnico
├── requirements.txt        # Dependencias del módulo
├── README.md               # Documentación del proyecto
└── ...
```

---

## 🚀 Ejecución

### Requisitos

- Python 3.8 o superior
- Dependencias en `requirements.txt`

### Instalación

```bash
cd zapatasCTE
pip install -r requirements.txt
```

### Arranque

```bash
streamlit run app.py
```

---

## 📊 Resultados esperados

- Capacidad de hundimiento
- Presión admisible
- Verificación del terreno frente a cargas aplicadas
- Comparación de geometrías y configuraciones
- Informe técnico para uso de proyecto

---

## 🧠 Casos de uso

- Verificación de zapatas según normativa
- Diseño preliminar de cimentaciones superficiales
- Comparación de alternativas geométricas
- Estudios de diseño y análisis geotécnico

---

## 📜 Licencia

Este módulo forma parte del repositorio principal **Exterior** y sigue la licencia del proyecto.

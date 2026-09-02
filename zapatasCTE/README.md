# 🏗️ **Zapatas CTE - Cálculo de Hundimiento (DB SE-C)**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.24%2B-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 **Descripción**

**ZapatasCTE** es una herramienta de **cálculo analítico de capacidad portante y hundimiento** para cimentaciones superficiales, desarrollada según los criterios del **Código Técnico de la Edificación (CTE DB SE-C)**. 

La aplicación permite evaluar el **estado límite último (ELU) por hundimiento** en zapatas de hormigón (rectangulares, corridas o circulares), considerando:
- Propiedades geotécnicas del terreno (cohesión, ángulo de rozamiento, peso específico, nivel freático).
- Geometría de la cimentación y condiciones de contorno (talud, profundidad de apoyo).
- Acciones aplicadas (axil, cortante, momentos).
- Factores de corrección por **forma, profundidad, inclinación de la carga y talud**.

---

## ✨ **Características**

| Funcionalidad | Descripción |
|--------------|-------------|
| **Análisis geotécnico** | Cálculo de capacidad portante (`q_h`) y presión admisible (`q_adm`) según CTE DB SE-C. |
| **Tipos de zapata** | Soporte para zapatas **rectangulares**, **corridas** y **circulares**. |
| **Barrido geométrico** | Generación automática de matrices de resultados para rangos de dimensiones. |
| **Visualización** | Gráficos interactivos (Matplotlib) y tablas de resultados (Pandas). |
| **Informes** | Exportación de memorias justificativas en **PDF** y **Word** (próximamente). |
| **Interfaz intuitiva** | UI web basada en **Streamlit** sin necesidad de frontend. |

---

## 📦 **Estructura del Proyecto**

```
zapatasCTE/
├── app.py                  # Interfaz de usuario (Streamlit)
├── motor_calculo.py        # Motor de cálculo geotécnico (CTE DB SE-C)
├── requirements.txt        # Dependencias Python
└── README.md               # Documentación
```

---

## 🛠 **Requisitos**

- **Python** ≥ 3.8
- **Sistema operativo**: Windows, Linux o macOS
- **Dependencias**: Ver [requirements.txt](requirements.txt)

---

## 🚀 **Instalación**

### 1. Clonar el repositorio
```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior/zapatasCTE
```

### 2. Crear entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# O en Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## 🎯 **Uso**

### Ejecutar la aplicación
```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador por defecto (normalmente en `http://localhost:8501`).

---

### 📝 **Parámetros de Entrada**

#### **1. Terreno y Agua**
| Parámetro | Descripción | Valor por defecto | Unidad |
|-----------|-------------|-------------------|--------|
| `Análisis Drenado` | Activa/desactiva análisis drenado | ✅ Sí | - |
| `Cohesión (c₀)` | Cohesión del terreno | 10.0 | kPa |
| `Gradiente (m)` | Gradiente de cohesión | 0.0 | kPa/m |
| `Áng. Rozamiento (φ')` | Ángulo de rozamiento interno | 30.0 | ° |
| `γ aparente` | Peso específico aparente | 18.0 | kN/m³ |
| `γ saturado` | Peso específico saturado | 20.0 | kN/m³ |
| `Profundidad N.F.` | Profundidad del nivel freático | 5.0 | m |
| `Gradiente ascendente (i_v)` | Gradiente hidráulico | 0.0 | - |
| `Anular resistencia terreno superior` | Ignora coeficiente de profundidad (`d_i = 1`) | ❌ No | - |

#### **2. Cimentación**
| Parámetro | Descripción | Valor por defecto | Unidad |
|-----------|-------------|-------------------|--------|
| `Tipo de Zapata` | Rectangular, corrida o circular | Rectangular | - |
| `Cota de apoyo (D)` | Profundidad de apoyo | 1.0 | m |
| `Sobrecarga (q_ext)` | Sobrecarga permanente | 0.0 | kPa |
| `Inclinación talud (β)` | Inclinación del talud | 0.0 | ° |
| `Cohesión base-terreno (c)` | Adhesión base-terreno | 0.0 | kPa |

#### **3. Acciones**
| Parámetro | Descripción | Valor por defecto | Unidad |
|-----------|-------------|-------------------|--------|
| `Axil (V)` | Carga vertical | 1000.0 | kN |
| `Cortante (H)` | Carga horizontal | 0.0 | kN |
| `Momento (M_B)` | Momento en dirección B | 0.0 | mkN |
| `Momento (M_L)` | Momento en dirección L (solo rectangular/circular) | 0.0 | mkN |

---

### 📊 **Barrido Geométrico**
- Define rangos para las dimensiones principales (`B_min`, `B_max`, `paso`).
- Para zapatas rectangulares, también se configuran `L_min` y `L_max`.
- La aplicación genera una **matriz de resultados** con todas las combinaciones válidas.

---

### 📈 **Resultados**

#### **1. Pestaña "Resultados"**
- Tabla con:
  - Dimensiones (`B`, `L`, `B*` [dimensión efectiva]).
  - Área efectiva.
  - Presión de trabajo (`q_trabajo`).
  - Capacidad de hundimiento (`q_h`).
  - Presión admisible (`q_adm`).
  - **Cumple**: ✅ (verde) si `q_trabajo ≤ q_adm`, ❌ (rojo) en caso contrario.

#### **2. Pestaña "Gráfico"**
- Representación gráfica de:
  - `q_adm` vs `B` (para diferentes valores de `L` en zapatas rectangulares).
  - `q_trabajo` (línea roja discontinua).

#### **3. Pestaña "Desglose"**
- Detalles de los **factores de capacidad** y **coeficientes de corrección**:
  - **Factores de capacidad**: `Nq`, `Nc`, `Nγ`.
  - **Forma**: `sq`, `sc`, `sγ`.
  - **Profundidad**: `dq`, `dc`, `dγ`.
  - **Inclinación**: `iq`, `ic`, `iγ`.
  - **Talud**: `tq`, `tc`, `tγ`.
  - **Otros**: `q0k` (sobrecarga), `γ_k` (peso específico de la cuña de rotura).

#### **4. Pestaña "Informes"**
- Descarga de **memoria justificativa** en formato:
  - 📄 **PDF** (próximamente).
  - 📝 **Word** (próximamente).

---

## 📚 **Metodología de Cálculo**

La aplicación implementa el **método analítico del CTE DB SE-C** para el cálculo de la **capacidad portante** en cimentaciones superficiales, basado en la fórmula general:

```
q_h = c_k * N_c * s_c * d_c * i_c * t_c + q0k * N_q * s_q * d_q * i_q * t_q + 0.5 * γ_k * B* * N_γ * s_γ * d_γ * i_γ * t_γ
```

Donde:
- **`c_k`**: Cohesión efectiva (limitada a `2*c_0` para suelos no drenados).
- **`N_c`, `N_q`, `N_γ`**: Factores de capacidad (dependen de `φ'`).
- **`s_*`, `d_*`, `i_*`, `t_*`**: Coeficientes de corrección por **forma**, **profundidad**, **inclinación** y **talud**.
- **`q0k`**: Sobrecarga efectiva al nivel de apoyo.
- **`γ_k`**: Peso específico de la cuña de rotura (ajustado por nivel freático y gradiente).

### **Presión Admisible**
- **Suelos drenados**: `q_adm = q_h / γ_R` (con `γ_R = 3.0`).
- **Suelos no drenados**: `q_adm = (term_c / γ_R) + term_q + term_g`.

---

## 🔧 **Personalización**

### Añadir nuevos tipos de zapata
1. Modificar `motor_calculo.py`:
   - Añadir lógica en `CalculadoraCapacidad.calcular()`.
   - Actualizar factores de forma (`s_c`, `s_q`, `s_γ`).

### Ajustar coeficiente de seguridad
- Modificar `gamma_R` en el constructor de `CalculadoraCapacidad` (por defecto: `3.0`).

---

## 🤝 **Contribuciones**

Las contribuciones son bienvenidas. Para colaborar:

1. **Fork** el repositorio.
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y haz commit (`git commit -m "Añadir X"`).
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un **Pull Request** en GitHub.

---

## 📜 **Licencia**

Este proyecto está bajo la **Licencia MIT**. Consulta el archivo [LICENSE](../../LICENSE) para más detalles.

---

## 📞 **Contacto**

Para preguntas o soporte:
- **Repository**: [me1lopig/Exterior](https://github.com/me1lopig/Exterior)
- **Issues**: [Reportar un problema](https://github.com/me1lopig/Exterior/issues)

---

## 🏆 **Agradecimientos**

- **CTE DB SE-C**: Código Técnico de la Edificación (España).
- **Streamlit**: Framework para aplicaciones web en Python.
- **Comunidad geotécnica**: Por su contribución al desarrollo de métodos analíticos.

---

> **Nota**: Esta herramienta es para **uso profesional** y debe validarse con cálculos manuales o software especializado en proyectos críticos.

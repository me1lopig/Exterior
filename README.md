# Exterior

**Aplicaciones web para ingeniería geotécnica** desarrolladas con **Streamlit** y Python. Este repositorio contiene herramientas especializadas para el análisis y diseño de cimentaciones, consolidación de suelos y otros cálculos geotécnicos, orientadas a su despliegue en entornos académicos y de testeo.

---

## 📁 Estructura del Repositorio

```
Exterior/
├── AsientosZapata/           # Análisis de asientos en zapatas (cimentaciones superficiales)
│   ├── app_asientos_FEM_4.py # Aplicación principal (1079 líneas)
│   └── requirements.txt      # Dependencias específicas
│
├── PilotesCTE/               # Diseño de pilotes según CTE DB-SE-C (cimentaciones profundas)
│   ├── PilotesCTE_2.py       # Aplicación principal (618 líneas)
│   └── requirements.txt      # Dependencias específicas
│
└── Consolidacion/            # Modelo de consolidación 1D para suelos
    ├── consolidacion_streamlit_3.py # Aplicación principal (582 líneas)
    └── requirements.txt      # Dependencias específicas
```

---

## 🏗️ Aplicaciones Disponibles

### 1️⃣ **AsientosZapata**
**Descripción**: Herramienta para el cálculo de **asientos en zapatas** (cimentaciones superficiales) mediante métodos teóricos y análisis por **Elementos Finitos (FEM)**.

#### 📋 Características principales:
- **Métodos teóricos implementados**:
  - **Holl**: Cálculo de tensiones bajo esquinas y centros de cargas rectangulares.
  - **Steinbrenner**: Asientos en suelos estratificados con módulos de elasticidad y coeficientes de Poisson.
  - **Método elástico**: Análisis basado en propiedades elásticas del suelo.
- **Análisis FEM (opcional)**: Simulación 3D de zapatas y suelos usando **OpenSeesPy** (si está instalado).
- **Visualización**: Gráficos de distribución de tensiones y asientos por capa (`matplotlib`).
- **Exportación**: Generación de informes detallados en formato **Word (.docx)** con tablas, gráficos y cálculos.

#### 📦 Dependencias:
- `streamlit` (interfaz web)
- `numpy` (cálculos numéricos)
- `pandas` (manipulación de datos tabulares)
- `matplotlib` (gráficos estáticos)
- `openseespy` (opcional, para análisis FEM)
- `python-docx` (generación de informes Word)

---

### 2️⃣ **PilotesCTE**
**Descripción**: Herramienta para el **diseño de pilotes** (cimentaciones profundas) según el **Código Técnico de la Edificación (CTE DB-SE-C)** de España.

#### 📋 Características principales:
- **Configuración según normativa CTE DB-SE-C**:
  - Métodos de ejecución: **Perforados** (entubados, lodos, en seco, con/sin control de parámetros) y **Hincados** (hormigón armado, pretensado, metálicos, madera).
  - Tope estructural automático según tipo de pilote y material (Tabla 5.1 del CTE).
  - Coeficientes parciales de seguridad (`γ_R`, `γ_M`).
- **Cálculos geotécnicos**:
  - Capacidad de carga por **punta** (según tipo de suelo: arcillas, arenas, rocas).
  - Capacidad de carga por **fuste** (rozamiento lateral).
  - Asientos estimados mediante métodos empíricos.
  - Combinación de cargas: axial, cortante, momento flector.
- **Visualización**: Gráficos interactivos con **Plotly** (capacidad vs. profundidad, distribución de esfuerzos).
- **Exportación**: Informes en **Word (.docx)** con resultados, gráficos y verificación normativa.

#### 📦 Dependencias:
- `streamlit` (interfaz web)
- `numpy` (cálculos numéricos)
- `pandas` (manipulación de datos tabulares)
- `plotly` (gráficos interactivos)
- `matplotlib` (gráficos adicionales)
- `python-docx` (generación de informes Word)

---

### 3️⃣ **Consolidacion**
**Descripción**: Herramienta para el **modelo de consolidación 1D** en suelos bajo cargas extensas, permitiendo analizar el comportamiento de asientos a lo largo del tiempo.

#### 📋 Características principales:
- **Análisis de consolidación 1D** para suelos saturados.
- **Métodos numéricos**: Solución explícita e implícita para la ecuación de consolidación de Terzaghi.
- **Parámetros configurables**:
  - Longitud de la capa de suelo.
  - Tensión inicial y coeficiente de consolidación.
  - Módulo de compresibilidad volumétrica (`m_v`).
  - Permeabilidad y espesor de las capas.
- **Visualización**:
  - Gráficos de **grado de consolidación vs. tiempo** (`matplotlib` y `plotly`).
  - Curvas de asientos en función del tiempo.
- **Exportación**: Generación de informes en **Word (.docx)** con resultados y gráficos.

#### 📦 Dependencias:
- `streamlit` (interfaz web)
- `numpy` (cálculos numéricos)
- `matplotlib` (gráficos estáticos)
- `pandas` (manipulación de datos tabulares)
- `plotly` (gráficos interactivos)
- `python-docx` (generación de informes Word)
- `openpyxl` (manipulación de archivos Excel)

---

## 🚀 ¿Cómo Ejecutar las Aplicaciones?

### Requisitos previos:
- Python 3.8 o superior.
- Instalar las dependencias de cada aplicación.

### Pasos para ejecutar:

#### 1. Clonar el repositorio:
```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior
```

#### 2. Instalar dependencias:
```bash
# Para AsientosZapata
cd AsientosZapata
pip install -r requirements.txt

# Para PilotesCTE
cd ../PilotesCTE
pip install -r requirements.txt

# Para Consolidacion
cd ../Consolidacion
pip install -r requirements.txt
```

#### 3. Ejecutar con Streamlit:
```bash
# AsientosZapata
streamlit run app_asientos_FEM_4.py

# PilotesCTE
streamlit run PilotesCTE_2.py

# Consolidacion
streamlit run consolidacion_streamlit_3.py
```

#### 4. Acceder a la aplicación:
Abrir el navegador en `http://localhost:8501`.

---

## 📜 Licencia
Este proyecto está licenciado bajo **GNU General Public License v3.0** (consultar el archivo [LICENSE](LICENSE) para más detalles).

---

## 📧 Contacto
Para consultas o colaboraciones, contactar con el mantenedor del repositorio.

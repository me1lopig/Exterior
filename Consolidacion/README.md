# 🏗️ Modelo de Consolidación 1D para Carga Extensa

> **Simulador académico de consolidación unidimensional de suelos basado en la teoría de Terzaghi**

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Requisitos de Sistema](#-requisitos-de-sistema)
- [Instalación](#-instalación)
- [Uso del Programa](#-uso-del-programa)
- [Fundamento Teórico](#-fundamento-teórico)
- [Funcionalidades Detalladas](#-funcionalidades-detalladas)
- [Generación de Reportes](#-generación-de-reportes)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Autor](#-autor)

---

## 📖 Descripción General

Este proyecto implementa una **herramienta de simulación numérica interactiva** para analizar el proceso de consolidación unidimensional de suelos saturados bajo cargas extensas. Utiliza la ecuación diferencial clásica de Terzaghi (1925) resuelta mediante el Método de Diferencias Finitas.

**Ideal para:**
- 🎓 Educación en Ingeniería Geotécnica
- 📊 Análisis de asientos en cimentaciones
- 🔬 Investigación académica en Mecánica de Suelos
- 💼 Evaluación preliminar de consolidación

---

## ✨ Características Principales

### 🎯 Simulación Numérica
| Característica | Descripción |
|---|---|
| **Métodos de Cálculo** | Explícito e Implícito (FDM) |
| **Condiciones de Contorno** | 3 tipos (Doble, Superior, Inferior drenaje) |
| **Precisión** | Integración por Simpson para presiones medias |
| **Convergencia** | Control automático de estabilidad numérica |

### 📊 Visualización Interactiva
| Gráfica | Contenido |
|---|---|
| **Isócronas de Presión** | Evolución de presión intersticial en profundidad |
| **Asientos vs Tiempo** | Deformación vertical progresiva |
| **Grado de Consolidación** | Porcentaje de disipación de exceso de presión |
| **Caudal de Flujo** | Variación temporal del drenaje |
| **Factor Tiempo (Tv)** | Relación logarítmica adimensional |

### 💾 Gestión de Datos
- 📁 **Cargar/Guardar perfiles** en formato JSON
- 📊 **Exportar a Excel** (parámetros, evolución temporal, matriz de presiones)
- 📄 **Generar informes Word** con gráficas integradas
- 📋 **Tablas de datos** para análisis post-procesamiento

---

## ⚙️ Requisitos de Sistema

### Software
- **Python:** 3.8 o superior
- **SO:** Windows, macOS, Linux

### Hardware Mínimo
- 2 GB de RAM
- 200 MB de espacio en disco

---

## 🚀 Instalación

### 1️⃣ Clonar el Repositorio
```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior/Consolidacion
```

### 2️⃣ Crear Entorno Virtual (Recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4️⃣ Ejecutar la Aplicación
```bash
streamlit run consolidacion_streamlit_3.py
```

La aplicación se abrirá automáticamente en tu navegador (http://localhost:8501)

---

## 🎮 Uso del Programa

### 📍 Panel de Control (Lateral Izquierdo)

#### Gestión de Perfiles
```
���� Cargar Configuración (.json)
💾 Guardar Configuración (.json)
```

#### Parámetros de Entrada
| Parámetro | Rango | Unidades | Significado |
|---|---|---|---|
| **Espesor del estrato** | 0.1 - ∞ | m | Altura del dominio |
| **Carga exterior (Ti)** | 1.0 - ∞ | kPa | Sobrecarga aplicada |
| **Cv (consolidación)** | 1e-8 - ∞ | m²/día | Permeabilidad relativa |
| **mv (compresibilidad)** | 1e-8 - ∞ | m²/kN | Deformabilidad volumétrica |

#### Configuración del Mallado
| Parámetro | Rango | Unidades | Efecto |
|---|---|---|---|
| **h (Δx)** | 0.01 - ∞ | m | Espaciamiento vertical (precisión) |
| **k (Δt)** | 0.01 - ∞ | días | Paso temporal (convergencia) |
| **Máximo U** | 10.0 - 99.9 | % | Límite de cálculo |
| **Intervalo isócronas** | 0.1 - ∞ | días | Espaciamiento temporal de gráficas |

#### Motor Numérico
```
☑ Explícito  (Rápido pero inestable con α > 0.5)
☑ Implícito  (Estable siempre, ideal para tiempos largos)
```

#### Condiciones de Contorno
```
[1] Permeable - Permeable (Doble drenaje)
[2] Permeable - Impermeable (Drenaje superior)
[3] Impermeable - Permeable (Drenaje inferior)
```

### 📊 Pestaña 1: Simulación y Resultados

#### Paso 1: Configurar Parámetros
Ajusta todos los valores en el panel lateral según tu caso de estudio.

#### Paso 2: Ejecutar Cálculo
Presiona **🚀 Iniciar Cálculo del Modelo**

```
⏳ Barra de progreso → Sigue el % de consolidación alcanzado
✅ Éxito → Cálculos completados
⚠️ Advertencia → Se muestra grado final y asiento máximo
```

#### Paso 3: Analizar Gráficas
Se generan **6 gráficas interactivas** (Plotly):
1. 📈 **Presión de poro** (isócronas)
2. 📉 **Asientos vs Tiempo**
3. 📊 **Grado de Consolidación vs Tiempo**
4. 💧 **Caudal de Flujo vs Tiempo**
5. 🔗 **Asientos vs Grado de Consolidación**
6. 📐 **Grado de Consolidación vs Factor Tiempo (log)**

#### Paso 4: Generar Documentos
Presiona **📄 Generar Informes (Word y Excel)**

### 📋 Pestaña 2: Datos Tabulados
Visualiza en tablas interactivas:
- **Evolución Temporal:** t, U, S, Q
- **Matriz de Presiones:** Todos los pasos temporales × profundidades

### 📚 Pestaña 3: Fundamento Teórico
Referencia completa:
- Ecuación de Terzaghi
- Métodos numéricos
- Factores de estabilidad
- Fórmulas de grado de consolidación

---

## 🔬 Fundamento Teórico

### 📐 Ecuación Fundamental

La consolidación 1D se rige por la **EDP parabólica de Terzaghi:**

```
∂u/∂t = Cv · ∂²u/∂x²
```

**Donde:**
- `u` = Exceso de presión intersticial [kPa]
- `Cv` = Coeficiente de consolidación [m²/día]
- `x` = Profundidad [m]
- `t` = Tiempo [días]

**Relación con propiedades del suelo:**
```
Cv = k_perm / (γw · mv)
k_perm = Permeabilidad de Darcy [m/día]
γw = Peso unitario del agua ≈ 10 kN/m³
mv = Módulo de compresibilidad volumétrica [m²/kN]
```

### 🧮 Métodos Numéricos

#### ✔️ Método Explícito
```
u_i^(t+k) = α·u_{i+1}^t + (1-2α)·u_i^t + α·u_{i-1}^t

Donde: α = Cv·k / h²
Condición: α ≤ 0.5 (ESTABILIDAD)
```
**Ventajas:** Cálculo rápido
**Desventajas:** Muy restrictivo con paso temporal

#### ✔️ Método Implícito
```
Matriz tridiagonal: A · u^(t+k) = u^t
Incondicionalmente estable
```
**Ventajas:** Estabilidad garantizada, pasos grandes
**Desventajas:** Inversión de matriz (overhead computacional)

### 📊 Grado de Consolidación

```
U(t) = 1 - [∫u(x,t)dx / ∫u(x,0)dx]

Rango: 0% (inicio) a 100% (final teórico)
```

### 📏 Asientos Totales

```
S_max = H · mv · Ti
S(t) = S_max · U(t)
```

---

## 🛠️ Funcionalidades Detalladas

### 🔄 Ciclo de Trabajo Típico

```
1. Cargar perfil JSON (opcional)
    ↓
2. Ajustar parámetros geotécnicos
    ↓
3. Configurar malla espacial y temporal
    ↓
4. Seleccionar método numérico
    ↓
5. Definir condiciones de contorno
    ↓
6. Ejecutar simulación
    ↓
7. Analizar gráficas interactivas
    ↓
8. Exportar datos (Excel/Word)
    ↓
9. Guardar configuración para reuso
```

### 📁 Formato de Archivos JSON

**Ejemplo de perfil guardado:**
```json
{
    "longitud": 10.0,
    "Ti": 100.0,
    "c": 0.05,
    "mv": 0.0002,
    "h": 1.0,
    "k": 1.0,
    "max_U_pct": 95.0,
    "intervalo_dias_curvas": 10.0,
    "tipo_calculo": 1,
    "metodo_numerico": "Implícito"
}
```

---

## 📤 Generación de Reportes

### 📊 Archivo Excel (.xlsx)

| Hoja | Contenido |
|---|---|
| **1. Parámetros** | Datos de entrada: espesor, carga, coeficientes |
| **2. Evolución temporal** | Tiempo, U%, Asientos, Caudal |
| **3. Presiones Isócronas** | Matriz completa u(x,t) |

### 📄 Archivo Word (.docx)

```
├── Título: Informe de Consolidación 1D
├── Sección: Datos del Modelo
│   ├── Espesor: X m
│   ├── Carga: Y kPa
│   ├── Cv: Z m²/día
│   └── ...
├── Sección: Resultados Gráficos
│   ├── Presión de Poro
│   ├── Asientos vs Tiempo
│   ├── Grado de Consolidación
│   ├── Caudal
│   ├── Asientos vs U
│   └── U vs Factor Tiempo
└── (Todas las imágenes en 150 DPI, 5.5 in ancho)
```

---

## 📁 Estructura del Proyecto

```
Consolidacion/
├── consolidacion_streamlit_3.py     # Aplicación principal
├── requirements.txt                  # Dependencias Python
└── README.md                         # Este archivo
```

### Flujo de Datos en la Aplicación

```
┌─────────────────────────────────────────────────────────────┐
│               ENTRADA DE PARÁMETROS                          │
│  (Panel Lateral: Carga, Cv, mv, h, k, etc.)               │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           VALIDACIÓN Y CHEQUEOS                              │
│  (Estabilidad α, rango de parámetros)                       │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    SELECCIONAR MÉTODO NUMÉRICO          │
        └────────┬──────────────────┬─────────────┘
                 ↓                  ↓
        ┌────────────────┐  ┌──────────────────┐
        │  EXPLÍCITO     │  │   IMPLÍCITO      │
        │  (α ≤ 0.5)     │  │  (Siempre OK)    │
        └────────┬───────┘  └────────┬─────────┘
                 │                   │
                 └─────────┬─────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│          RESOLUCIÓN ITERATIVA EN TIEMPO                      │
│  Δt = k [días], Δx = h [m]                                 │
│  Historial: u(x,t), Q(t), S(t), U(t)                        │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              POSTPROCESAMIENTO                               │
│  · Integración Simpson para U(t)                             │
│  · Cálculo de asientos escalados                             │
│  · Selección de isócronas para gráficas                     │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    VISUALIZACIÓN EN STREAMLIT            │
        ├─────────────────────────────────────────┤
        │  ✓ Gráficas Plotly interactivas         │
        │  ✓ Tablas Pandas filtrable             │
        │  ✓ Botones de descarga                  │
        └────────┬──────────────────┬─────────────┘
                 ↓                  ↓
        ┌────────────────┐  ┌──────────────────┐
        │  EXCEL (.xlsx) │  │  WORD (.docx)    │
        │  con 3 hojas   │  │  con gráficas    │
        └────────────────┘  └──────────────────┘
```

---

## 📦 Dependencias

| Librería | Versión | Función |
|---|---|---|
| **streamlit** | Latest | Framework web interactivo |
| **numpy** | Latest | Cálculos numéricos, álgebra lineal |
| **matplotlib** | Latest | Generación de figuras para reportes |
| **pandas** | Latest | Gestión de datos tabulares |
| **plotly** | Latest | Gráficas interactivas |
| **openpyxl** | Latest | Escritura de archivos Excel |
| **python-docx** | Latest | Generación de documentos Word |

---

## 🎓 Ejemplos de Uso

### Ejemplo 1: Consolidación en Arcilla Blanda
```
Espesor: 15 m
Carga: 150 kPa
Cv: 0.02 m²/día (arcilla blanda)
mv: 0.0003 m²/kN
Método: Implícito
Contorno: Doble drenaje
```

### Ejemplo 2: Capa Fina Bien Drenada
```
Espesor: 2 m
Carga: 50 kPa
Cv: 0.5 m²/día (arena fina)
mv: 0.00005 m²/kN
Método: Explícito
Contorno: Drenaje superior
```

---

## ⚠️ Consideraciones Importantes

### ❌ Limitaciones del Modelo
- Solo considera **consolidación vertical (1D)**
- Asume suelo **saturado** homogéneo
- No incluye efectos de **consolidación secundaria**
- Parámetros **constantes** en tiempo

### ⚡ Consejos de Estabilidad Numérica

| Problema | Solución |
|---|---|
| "Alpha > 0.5" con Explícito | Reducir k, aumentar h, o usar Implícito |
| Tiempos de cálculo muy largos | Aumentar k (paso temporal) |
| Resultados erráticos | Reducir h (refinar malla) |
| Convergencia lenta | Usar Implícito para mejor precisión/velocidad |

---

## 🔧 Troubleshooting

### ❓ La aplicación no inicia
```bash
# Verificar Streamlit instalado
pip list | grep streamlit

# Reinstalar si es necesario
pip install --upgrade streamlit
```

### ❓ Error en generación de Word/Excel
```bash
# Asegurar instalación de librerías
pip install --upgrade openpyxl python-docx
```

### ❓ Valores de consolidación anómalos
- Verificar que Ti > 0
- Confirmar que Cv y mv sean > 0
- Revisar que h y k sean apropiados

---

## 📞 Contacto y Soporte

**Autor:** me1lopig  
**Repositorio:** https://github.com/me1lopig/Exterior  
**Propósito:** Educación e investigación en Geotecnia

Para reportar errores o sugerir mejoras, favor crear un **Issue** en el repositorio.

---

## 📜 Notas Académicas

### Referencias Teóricas
- Terzaghi, K. (1925). *Erdbaumechanik* - Teoría clásica de consolidación
- Das, B.M. (2015). *Principles of Geotechnical Engineering*
- Verruijt, A. (2018). *Theory and Practice of Hydrodynamics* - Poroelasticidad

### Softwares Relacionados
- PLAXIS (Análisis de elementos finitos)
- GeoStudio Seep/w (Flujo de agua y consolidación)
- SVFLUX (Análisis de flujo multifase)

---

## 📄 Licencia

Este software es proporcionado **para uso académico y educativo**. 

**⚠️ Descargo de Responsabilidad:** Usar solo con fines de enseñanza y testeo. No es apropiado para diseño de ingeniería en proyectos reales sin validación profesional.

---

## ✅ Checklist de Uso Recomendado

- [ ] Leer sección "Fundamento Teórico"
- [ ] Revisar ejemplo de formato JSON
- [ ] Realizar prueba con parámetros de ejemplo
- [ ] Validar resultados contra literatura conocida
- [ ] Guardar perfil de configuración
- [ ] Generar reporte de prueba (Word + Excel)
- [ ] Explorar efecto de parámetros modificando uno a la vez

---

**Última actualización:** Octubre 2024  
**Versión:** 3.0  
**Estado:** ✅ En Desarrollo Activo


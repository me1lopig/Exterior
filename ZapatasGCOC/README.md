# 🏗️ **ZapatasGCOC - Dimensionamiento de Cimentaciones Superficiales**

> **Herramientas para el diseño y verificación de zapatas según la *Guía de Cimentaciones en Obras de Carretera (GCOC)***
> *Desarrollado en Python con Streamlit y NumPy*

---

## 📌 **Descripción General**

Este módulo contiene **dos scripts** para el **dimensionamiento y verificación de cimentaciones superficiales (zapatas)** basados en la metodología de **Brinch-Hansen**, adaptada a los requisitos de la **Guía de Cimentaciones en Obras de Carretera (GCOC)**. Permite:

- **Pre-dimensionamiento** de zapatas mediante **cartas de tensiones admisibles** (Modo A).
- **Verificación estructural** con cargas reales (verticales, horizontales y momentos flectores) (Modo B).
- Cálculo de **factores de seguridad** frente a hundimiento.
- Generación de **gráficas interactivas** (mapas de calor, diagramas de seguridad).
- Exportación de resultados en **CSV** para integración en informes técnicos.

---

## 📁 **Estructura del Módulo**

```bash
ZapatasGCOC/
├── 📄 zapatas_GCOC_1.py    # Motor de cálculo (función `comprobacion_hundimiento`)
└── 📄 zapatasGCOC.py        # Aplicación Streamlit (interfaz gráfica)
```

| **Archivo**               | **Tipo**       | **Descripción**                                                                                     |
|--------------------------|---------------|-------------------------------------------------------------------------------------------------|
| `zapatas_GCOC_1.py`       | Script Python | **Motor de cálculo analítico** (Brinch-Hansen modificado). Función principal: `comprobacion_hundimiento`. |
| `zapatasGCOC.py`          | App Streamlit | **Interfaz gráfica** para dimensionamiento iterativo y visualización de resultados.         |

---

## 🚀 **Cómo Empezar**

### **Requisitos Previos**
- Python **3.8 o superior**.
- Librerías necesarias:
  ```bash
  pip install streamlit numpy pandas plotly
  ```

### **Ejecución**
1. **Para usar la interfaz gráfica (recomendado)**:
   ```bash
   cd Cimentaciones/ZapatasGCOC
   streamlit run zapatasGCOC.py
   ```
   - Se abrirá automáticamente en tu navegador (normalmente en `http://localhost:8501`).

2. **Para usar el motor de cálculo directamente** (ejemplo en `zapatas_GCOC_1.py`):
   ```python
   from zapatas_GCOC_1 import comprobacion_hundimiento
   
   cumple = comprobacion_hundimiento(
       V=1500.0,         # Fuerza vertical (kN)
       H=150.0,          # Fuerza horizontal (kN)
       c=15.0,           # Cohesión efectiva (kPa)
       phi_deg=28.0,     # Ángulo de rozamiento interno (°)
       gamma_ap=18.0,    # Peso específico aparente (kN/m³)
       gamma_sat=20.0,   # Peso específico saturado (kN/m³)
       D_w=0.5,          # Profundidad del nivel freático (m)
       D=1.5,            # Profundidad de apoyo (m)
       B_star=2.0,       # Ancho efectivo de la zapata (m)
       L_star=2.0,       # Longitud efectiva de la zapata (m)
       F_h_exigido=3.0   # Factor de seguridad exigido
   )
   print(f"¿Cumple normativa? {cumple}")
   ```

---

## 🔧 **Funcionalidades Detalladas**

### **1️⃣ `zapatas_GCOC_1.py` - Motor de Cálculo**

#### **Función Principal: `comprobacion_hundimiento`**
Calcula la **presión última de hundimiento** y el **factor de seguridad** de una zapata usando la **fórmula general de Brinch-Hansen** (modificada para GCOC).

**Parámetros de entrada**:

| **Parámetro**         | **Símbolo** | **Unidad** | **Descripción**                                                                                     | **Valor por Defecto** |
|-----------------------|-------------|------------|-------------------------------------------------------------------------------------------------|-----------------------|
| `V`                   | V           | kN         | Fuerza vertical efectiva total sobre el plano de cimentación.                                   | 1500.0                |
| `H`                   | H           | kN         | Fuerza horizontal total aplicada.                                                                | 150.0                 |
| `c`                   | c           | kPa        | Cohesión efectiva del terreno (o resistencia al corte no drenada, `s_u`).                       | 15.0                  |
| `phi_deg`             | φ           | °          | Ángulo de rozamiento interno del terreno.                                                         | 28.0                  |
| `gamma_ap`            | γ_ap        | kN/m³      | Peso específico aparente del terreno.                                                             | 18.0                  |
| `gamma_sat`           | γ_sat       | kN/m³      | Peso específico saturado del terreno.                                                             | 20.0                  |
| `D_w`                 | D_w         | m          | Profundidad del nivel freático **sobre la base de la zapata**.                                   | 0.5                   |
| `D`                   | D           | m          | Profundidad de apoyo de la zapata.                                                                | 1.5                   |
| `B_star`              | B*          | m          | Ancho efectivo de la zapata (considera excentricidad).                                           | 2.0                   |
| `L_star`              | L*          | m          | Longitud efectiva de la zapata (considera excentricidad).                                        | 2.0                   |
| `psi_deg`             | ψ           | °          | Ángulo de inclinación de la base de la zapata (0° para bases horizontales).                       | 0.0                   |
| `eta_deg`             | η           | °          | Ángulo de inclinación de la carga (0° para cargas verticales).                                     | 0.0                   |
| `F_h_exigido`         | F_exigido   | -          | Factor de seguridad exigido por normativa.                                                        | 3.0                   |

**Salidas**:
- **`p_vh`**: Presión última de hundimiento teórica (kPa).
- **`p_v_adm`**: Presión admisible según normativa (kPa).
- **`F_real`**: Factor de seguridad real obtenido.
- **`cumple_normativa`**: Booleano (`True` si `F_real >= F_h_exigido`).

**Fórmula implementada**:
```
p_vh = q * Nq * dq * iq * sq * tq * rq + c * Nc * dc * ic * sc * tc * rc + 0.5 * γ * B_star * Nγ * dγ * iγ * sγ * tγ * rγ
```
Donde:
- **`Nq, Nc, Nγ`**: Factores de capacidad de carga (dependen de φ).
- **`dq, dc, dγ`**: Factores de profundidad.
- **`iq, ic, iγ`**: Factores de inclinación de la carga.
- **`sq, sc, sγ`**: Factores de forma.
- **`tq, tc, tγ`**: Factores de inclinación de la base.
- **`rq, rc, rγ`**: Factores de inclinación del terreno.

**Casos especiales**:
- **Corto plazo (no drenado)**: Se asume `φ = 0` y se usan parámetros para suelos cohesivos (`Nq = 1.0`, `Nc = π + 2`, `Nγ = 0.0`).
- **Largo plazo (drenado)**: Se usan los parámetros efectivos del suelo (`c'`, `φ'`).

**Ejemplo de salida**:
```
============================================================
INFORME DE COMPROBACIÓN FRENTE A HUNDIMIENTO
============================================================
Cargas actuantes:
  Fuerza Vertical (V)               : 1500.00 kN
  Fuerza Horizontal (H)             : 150.00 kN
  Inclinación deducida (delta)      : 5.71°
  Presión real transmitida (p_v)    : 375.00 kPa
------------------------------------------------------------
Presión última de hundimiento (p_vh): 1200.45 kPa
Presión admisible según norma       : 400.15 kPa
------------------------------------------------------------
C. DE SEGURIDAD EXIGIDO (F_exigido) : 3.00
C. DE SEGURIDAD OBTENIDO (F_real)   : 3.20
------------------------------------------------------------
>>> RESULTADO: LA CIMENTACIÓN CUMPLE LA NORMATIVA <<<
============================================================
```

---

### **2️⃣ `zapatasGCOC.py` - Aplicación Streamlit**

#### **Modos de Operación**
| **Modo** | **Descripción**                                                                                     | **Uso Recomendado**                          |
|----------|-------------------------------------------------------------------------------------------------|---------------------------------------------|
| **A**    | **Pre-dimensionamiento**: Genera una **carta de tensiones admisibles** para diferentes geometrías de zapata. | Fase inicial de diseño.                     |
| **B**    | **Verificación estructural**: Analiza zapatas con **cargas reales** (V, H, M_B, M_L).           | Comprobación de diseños existentes.         |

#### **Parámetros Configurables**

##### **📌 Configuración Global (Barra Lateral)**
| **Parámetro**               | **Opciones**                          | **Descripción**                                                                                     |
|-----------------------------|--------------------------------------|-------------------------------------------------------------------------------------------------|
| Modo de Operación           | A / B                                | Pre-dimensionamiento o verificación estructural.                                              |
| Situación de Proyecto        | Persistente / Transitoria / Accidental | Determina el **factor de seguridad objetivo (FS)**: 3.00, 2.50 o 2.00.                        |
| Condición del terreno       | Largo Plazo / Corto Plazo            | Drenado (φ > 0) o no drenado (φ = 0).                                                           |

##### **🌍 Parámetros del Terreno (Columna 1)**
| **Parámetro**               | **Símbolo** | **Unidad** | **Descripción**                                                                                     | **Valor por Defecto** |
|-----------------------------|-------------|------------|-------------------------------------------------------------------------------------------------|-----------------------|
| Cohesión efectiva           | c           | kPa        | Solo para **largo plazo**. En corto plazo, se usa como resistencia al corte (`s_u`).             | 10.0                  |
| Ángulo de rozamiento        | φ           | °          | Solo para **largo plazo**. En corto plazo, se fija a 0°.                                         | 30.0                  |
| Peso específico aparente    | γ_ap        | kN/m³      | Peso específico del terreno por encima del nivel freático.                                       | 20.0                  |
| Peso específico sumergido   | γ'          | kN/m³      | Peso específico efectivo del terreno.                                                           | 10.0                  |

##### **📏 Geometría Iterativa (Columna 2)**
| **Parámetro**               | **Símbolo** | **Unidad** | **Descripción**                                                                                     |
|-----------------------------|-------------|------------|-------------------------------------------------------------------------------------------------|
| Profundidad de apoyo        | D           | m          | Profundidad a la que se apoya la zapata.                                                          |
| Nivel freático bajo base    | h_w         | m          | Distancia desde la base de la zapata hasta el nivel freático.                                    |
| Ancho B (mínimo/máximo)     | B_min / B_max | m        | Rango de anchos de zapata a analizar.                                                            |
| Incremento de B             | B_inc       | m          | Paso para el barrido de anchos.                                                                  |
| Longitud L (mínima/máxima)  | L_min / L_max | m        | Rango de longitudes de zapata a analizar.                                                         |
| Incremento de L             | L_inc       | m          | Paso para el barrido de longitudes.                                                               |

##### **⚖️ Cargas de la Estructura (Columna 3)**
| **Parámetro**               | **Símbolo** | **Unidad** | **Descripción**                                                                                     | **Valor por Defecto** |
|-----------------------------|-------------|------------|-------------------------------------------------------------------------------------------------|-----------------------|
| Carga Vertical              | V           | kN         | Carga vertical total sobre la zapata.                                                            | 1000.0                |
| Momento en eje B            | M_B         | mkN        | Momento flector en la dirección del ancho (B).                                                   | 0.0                   |
| Momento en eje L            | M_L         | mkN        | Momento flector en la dirección de la longitud (L).                                               | 0.0                   |

> **Nota**: En el **Modo A**, las cargas se desactivan y se asume una carga **totalmente centrada y vertical** para generar la carta de tensiones admisibles.

#### **📊 Salidas Generadas**

##### **Modo A: Carta de Tensiones Admisibles**
- **Mapa de calor**: Muestra la **tensión admisible (kPa)** para cada combinación de `B` y `L`.
  - Eje X: Ancho de zapata (`B`, en metros).
  - Eje Y: Longitud de zapata (`L`, en metros).
  - Color: Tensión admisible (escala `Viridis`).
  - Valores: Se muestran directamente en las celdas.

  ![Ejemplo Mapa de Calor](https://img.shields.io/badge/Visualización-Interactiva-brightgreen)

- **Tabla de datos**: Lista todas las combinaciones de `B` y `L` con:
  - `B (m)`: Ancho de la zapata.
  - `L (m)`: Longitud de la zapata.
  - `p_hundimiento (kPa)`: Presión última de hundimiento.
  - `p_admisible (kPa)`: Presión admisible (según FS objetivo).

##### **Modo B: Verificación Estructural**
- **Diagrama de seguridad**: Gráfico de dispersión (`B` vs `L`) con:
  - Color: **Factor de seguridad (FS)** (escala `RdYlGn`: rojo = peligro, verde = seguro).
  - Tamaño de puntos: Proporcional a las dimensiones de la zapata.
  - Información al pasar el ratón: `p_actuante`, `p_hundimiento`, y si **cumple normativa**.

- **Tabla de datos**: Lista todas las combinaciones con:
  - `B (m)`, `L (m)`: Dimensiones de la zapata.
  - `Área Ef. (m²)`: Área efectiva (considera excentricidad).
  - `p_actuante (kPa)`: Presión real transmitida al terreno.
  - `p_hundimiento (kPa)`: Presión última de hundimiento.
  - `FS`: Factor de seguridad obtenido.
  - `Cumple`: ✅ Sí / ❌ No (según FS ≥ FS objetivo).

#### **💾 Exportación de Resultados**
- **Formato**: CSV (compatible con Excel, LibreOffice, etc.).
- **Contenido**: Tabla completa con todos los resultados iterativos.
- **Uso**: Ideal para integrar en **anexos de informes técnicos** o documentos de cálculo.

---

## 📚 **Fundamento Teórico**

### **1️⃣ Fórmula de Brinch-Hansen**
La presión última de hundimiento (`p_vh`) se calcula según la **fórmula general de Brinch-Hansen** (1970):

```
p_vh = q * Nq * dq * iq * sq * tq * rq + c * Nc * dc * ic * sc * tc * rc + 0.5 * γ * B * Ng * dγ * iγ * sγ * tγ * rγ
```

Donde:
- **`q = γ * D`**: Presión efectiva a la profundidad de apoyo (`D`).
- **`Nq, Nc, Ng`**: Factores de capacidad de carga (dependen de `φ`).
- **`dq, dc, dγ`**: Factores de profundidad (efecto de la profundidad de apoyo).
- **`iq, ic, iγ`**: Factores de inclinación de la carga (efecto de `H` y momentos).
- **`sq, sc, sγ`**: Factores de forma (efecto de la geometría de la zapata).
- **`tq, tc, tγ`**: Factores de inclinación de la base.
- **`rq, rc, rγ`**: Factores de inclinación del terreno.

### **2️⃣ Factores de Capacidad de Carga**
| **Condición**       | **Nq**               | **Nc**          | **Ng**               |
|--------------------|----------------------|-----------------|----------------------|
| **Corto plazo (φ = 0)** | 1.0                  | π + 2 ≈ 5.14     | 0.0                  |
| **Largo plazo (φ > 0)** | `exp(π * tan(φ)) * tan²(45 + φ/2)` | `(Nq - 1) / tan(φ)` | `2 * (Nq - 1) * tan(φ)` |

### **3️⃣ Factores de Seguridad (GCOC)**
| **Situación de Proyecto** | **Factor de Seguridad (FS)** | **Descripción**                                                                                     |
|--------------------------|-------------------------------|-------------------------------------------------------------------------------------------------|
| Persistente              | 3.00                          | Cargas permanentes (ej. peso propio de la estructura).                                          |
| Transitoria              | 2.50                          | Cargas temporales (ej. sobrecargas de uso).                                                       |
| Accidental               | 2.00                          | Cargas excepcionales (ej. sismo, viento extremo).                                                |

### **4️⃣ Excentricidad y Dimensiones Efectivas**
La excentricidad de la carga (`e_B`, `e_L`) se calcula como:
```
e_B = |M_B / V|  # Excentricidad en la dirección B
e_L = |M_L / V|  # Excentricidad en la dirección L
```

Las **dimensiones efectivas** de la zapata (`B*`, `L*`) se reducen para considerar este efecto:
```
B* = B - 2 * e_B
L* = L - 2 * e_L
```

> **⚠️ Advertencia**: Si `B* ≤ 0` o `L* ≤ 0`, la zapata **vuelca geométricamente** y se descarta en el análisis.

### **5️⃣ Efecto del Nivel Freático**
El peso específico efectivo (`γ_eff`) se calcula en función de la posición del nivel freático (`h_w`):
```
Si h_w = 0: γ_eff = γ'
Si h_w > 0: γ_eff = γ' + 0.6 * (γ_ap - γ') * (h_w / B*)  [Interpolación lineal]
```
Donde:
- `γ'` = Peso específico sumergido (efectivo).
- `γ_ap` = Peso específico aparente.

---

## 🎯 **Casos de Uso Prácticos**

| **Escenario**                          | **Modo Recomendado** | **Parámetros Clave**                                                                                     | **Salida Esperada**                                                                                     |
|---------------------------------------|----------------------|---------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| Diseño inicial de una zapata          | A                    | Rango de `B` y `L`, FS = 3.0 (persistente)                                                               | Mapa de calor con tensiones admisibles para cada geometría.                                          |
| Verificación de una zapata existente  | B                    | `B`, `L`, `V`, `H`, `M_B`, `M_L`, φ, c, FS según situación de proyecto.                                   | Factor de seguridad real y si cumple normativa.                                                        |
| Zapata en suelo cohesivo (arcilla)    | A o B                | `φ = 0`, `c = s_u` (resistencia al corte no drenada), FS = 3.0.                                         | Presión admisible baja (típica de suelos blandos).                                                     |
| Zapata en suelo granular (arena)       | A o B                | `φ > 30°`, `c = 0`, FS = 3.0.                                                                             | Presión admisible alta (típica de suelos densos).                                                      |
| Zapata con nivel freático alto        | A o B                | `h_w > 0`, `γ'` (peso específico sumergido).                                                           | Reducción de la presión admisible por efecto del agua.                                               |

---

## 📊 **Ejemplo Práctico: Dimensionamiento de una Zapata**

### **Datos de Entrada**
- **Terreno**: Arena media (`φ = 30°`, `c = 0 kPa`, `γ_ap = 18 kN/m³`, `γ' = 10 kN/m³`).
- **Cargas**: `V = 1000 kN`, `H = 0 kN`, `M_B = 0 mkN`, `M_L = 0 mkN`.
- **Geometría**: `D = 1.5 m`, `h_w = 5 m` (nivel freático profundo).
- **Rango de zapatas**: `B = 1.0 a 4.0 m` (incremento 0.5 m), `L = 1.0 a 5.0 m` (incremento 0.5 m).
- **Situación**: Persistente (`FS = 3.0`).

### **Pasos en la App Streamlit**
1. Seleccionar **Modo A** (Pre-dimensionamiento).
2. Configurar:
   - Situación: `Persistente (FS = 3.00)`.
   - Condición: `Largo Plazo (Drenado)`.
   - Terreno: `φ = 30°`, `c = 0`, `γ_ap = 18`, `γ' = 10`.
   - Geometría: `D = 1.5`, `h_w = 5`, `B_min = 1.0`, `B_max = 4.0`, `B_inc = 0.5`, `L_min = 1.0`, `L_max = 5.0`, `L_inc = 0.5`.
3. Ejecutar el cálculo.

### **Resultados Esperados**
- **Mapa de calor**: Muestra que para `B = 2.0 m` y `L = 2.5 m`, la tensión admisible es de **~400 kPa**.
- **Tabla de datos**:
  | B (m) | L (m) | p_hundimiento (kPa) | p_admisible (kPa) |
  |-------|-------|----------------------|-------------------|
  | 2.0   | 2.5   | 1200                 | 400               |
  | 2.5   | 3.0   | 1000                 | 333               |

### **Conclusión**
- Para una carga de **1000 kN**, una zapata de **2.0 m × 2.5 m** tiene una presión admisible de **400 kPa**, por lo que la presión actuante (`p = 1000 / (2.0 * 2.5) = 200 kPa`) **cumple con FS = 3.0**.

---

## 🔍 **Validación de Resultados**

Para validar los resultados, compara con:

1. **Fórmulas analíticas**:
   - Usa la fórmula de Brinch-Hansen manualmente para casos simples.
   - Ejemplo: Para una zapata cuadrada (`B = L = 2 m`), `φ = 30°`, `c = 0`, `γ = 18 kN/m³`, `D = 1.5 m`:
     ```
     Nq = exp(π * tan(30°)) * tan²(45 + 15) ≈ 18.4
     Nγ = 2 * (Nq - 1) * tan(30°) ≈ 20.7
     q = γ * D = 18 * 1.5 = 27 kPa
     p_vh = q * Nq * sq + 0.5 * γ * B * Nγ * sγ ≈ 27 * 18.4 * 1.3 + 0.5 * 18 * 2 * 20.7 * 0.6 ≈ 1200 kPa
     p_adm = p_vh / 3 = 400 kPa
     ```

2. **Software comercial**:
   - Compara con resultados de **Geo5**, **Plaxis**, o **STAAD Foundation**.

3. **Normativas**:
   - Verifica que los factores de seguridad cumplen con la **GCOC** y el **CTE DB SE-Cimientos**.

---

## ⚠️ **Limitaciones y Advertencias**

1. **Hipótesis de Brinch-Hansen**:
   - Asume que el terreno es **homogéneo** y **isotrópico**.
   - No considera **capas estratificadas** (para esto, usa el módulo `Perfiles/` del repositorio).
   - No modela **efectos dinámicos** (ej. sismo, vibraciones).

2. **Excentricidad**:
   - El método simplificado no considera **factores de inclinación de carga (`i`)** en el Modo B (se asume carga centrada).
   - Para cargas muy excéntricas (`e_B > B/6` o `e_L > L/6`), se recomienda usar métodos más avanzados.

3. **Nivel freático**:
   - La interpolación del peso específico efectivo es una **aproximación**. Para mayor precisión, usa métodos basados en **tensiones efectivas**.

4. **Forma de la zapata**:
   - El método es válido para zapatas **rectangulares y cuadradas**. Para otras formas (ej. circulares), se requieren ajustes.

---

## 🛠️ **Recomendaciones para el Uso**

1. **Pre-dimensionamiento (Modo A)**:
   - Usa rangos amplios de `B` y `L` para explorar todas las opciones.
   - Elige la geometría que ofrezca la **mayor tensión admisible** con el **menor volumen de hormigón**.

2. **Verificación (Modo B)**:
   - Introduce las **cargas reales** de la estructura (incluyendo momentos flectores).
   - Asegúrate de que el **factor de seguridad** cumpla con la normativa para la situación de proyecto.

3. **Terrenos complejos**:
   - Para suelos **estratificados**, divide el terreno en capas y usa el **método de las tensiones efectivas**.
   - Para suelos **blandos o expansivos**, considera **asientos diferenciales** (usa el módulo `Consolidacion/`).

4. **Optimización**:
   - Usa el **Modo A** para generar una carta de tensiones y luego el **Modo B** para verificar el diseño seleccionado.

---

## 📝 **Historial de Versiones**

| **Versión** | **Fecha**       | **Cambios**                                                                                     |
|-------------|-----------------|-------------------------------------------------------------------------------------------------|
| 1.0         | 2024-08-31      | Versión inicial: `zapatas_GCOC_1.py` (motor de cálculo) y `zapatasGCOC.py` (app Streamlit).         |

---

## 🤝 **Contribuciones**

Las contribuciones son bienvenidas. Para colaborar:

1. **Fork** el repositorio.
2. Crea una **rama** para tu función:
   ```bash
   git checkout -b feature/zapatas-mejora
   ```
3. **Commit** tus cambios:
   ```bash
   git commit -m "Añade funcionalidad X a ZapatasGCOC"
   ```
4. **Push** a la rama:
   ```bash
   git push origin feature/zapatas-mejora
   ```
5. Abre un **Pull Request** en GitHub.

---

## 📄 **Licencia**

Este módulo forma parte del repositorio **[Calculos](https://github.com/me1lopig/Calculos)** y se distribuye bajo la licencia **MIT**. Consulta el archivo `LICENSE` en el repositorio principal para más detalles.

---

## 📞 **Contacto**

Para preguntas o sugerencias relacionadas con este módulo:
- **Autor**: Germán López Pineda
- **GitHub**: [@me1lopig](https://github.com/me1lopig)
- **Repositorio**: [Calculos](https://github.com/me1lopig/Calculos)
- **Email**: me1lopig@uco.es / rocasysuelos@gmail.com

---

## 📚 **Recursos Adicionales**

- **Guía de Cimentaciones en Obras de Carretera (GCOC)**: [Ministerio de Fomento, España](https://www.fomento.gob.es/)
- **Libro**: *Fundamentos de Cimentaciones* - Braja M. Das.
- **Normativa**: CTE DB SE-Cimientos (Código Técnico de la Edificación, España).
- **Software**: [Geo5](https://www.finehr.com/), [Plaxis](https://www.plaxis.com/).

---

> **⚠️ Nota**: Este README se actualizará conforme se añadan nuevas funcionalidades o mejoras al módulo.

---

*© 2024 - [me1lopig](https://github.com/me1lopig)*

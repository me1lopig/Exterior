# 🏗️ PilotesCTE

Documentación del programa para el diseño geotécnico de pilotes según el CTE DB-SE-C (Anexo F.2), desarrollado en Python con Streamlit.

## 📌 Descripción general

PilotesCTE es una herramienta de cálculo y análisis para evaluar la capacidad de pilotes sometidos a carga de punta y fuste, considerando:

- Estratigrafía del terreno
- Nivel freático
- Zona de fuste nulo
- Método de ejecución del pilote
- Tope estructural según la Tabla 5.1 del CTE
- Verificación geotécnica en condiciones de corto y largo plazo
- Generación de informe ejecutivo en formato Word (.docx)

La aplicación permite comparar combinaciones de diámetro y longitud, visualizar tensiones en el terreno y obtener matrices de resistencia útil para diseño.

## 🧩 Contenido del programa

El programa incluye las siguientes funcionalidades principales:

- 📋 Definición de estratos del terreno
  - Nombre del estrato
  - Espesor
  - Peso específico seco y saturado
  - Condición geotécnica: Corto Plazo / Largo Plazo
  - Cohesión cu y ángulo de rozamiento φ

- 🌊 Análisis de tensiones
  - Tensión total
  - Presión intersticial
  - Tensión efectiva
  - Evolución con la profundidad

- 🔻 Cálculo de resistencia por punta
  - Evaluación según el criterio del CTE DB-SE-C
  - Consideración del bulbo de influencia 6D / 3D
  - Control de terreno insuficiente y marcado N/D

- 🟫 Cálculo de resistencia por fuste
  - Criterio para suelos finos y granulares
  - Consideración de la zona de fuste nulo
  - Reducción por nivel freático y condiciones del terreno

- 🌍 Cálculo de resistencia total
  - Capacidad geotécnica admisible
  - Comparación con el tope estructural
  - Matriz final de diseño

- 🛑 Verificación estructural
  - Cálculo del límite según resistencia del material del pilote
  - Identificación de combinaciones gobernadas por el tope estructural

- 📊 Visualización gráficas
  - Tensiones frente a profundidad
  - Curvas de capacidad por longitud y diámetro
  - Esquema gráfico del pilote y del bulbo de influencia

- 📄 Informe Word
  - Generación automática del anejo de cálculo con resultados y gráficos

## ✅ Aplicabilidad

Este programa es especialmente útil para:

- 🏢 Ingenieros geotécnicos
- 🧱 Consultores de cimentaciones
- 🏫 Entornos académicos y docentes
- 🏗️ Estudios de viabilidad y diseño preliminar
- 📐 Verificación de pilotes de fundación en obra civil

### Aplicaciones típicas

- Dimensionado de pilotes perforados o hincados
- Estudio de capacidad resistente por punta y fuste
- Evaluación de cargas admisibles en distintos diámetros y longitudes
- Comparación de sistemas constructivos
- Preparación de memoria de cálculo según normativa CTE

### Limitaciones

La herramienta está orientada a un análisis de diseño y verificación geotécnica en entorno académico y profesional inicial, por lo que debe utilizarse con criterio técnico y validación del proyecto específico. Las combinaciones cuya longitud y diámetro requieren terreno por debajo del sondeo efectivo se marcan como N/D y no se calculan.

## ⚙️ Requisitos del sistema

El programa requiere Python 3 y las siguientes dependencias:

```bash
pip install -r requirements.txt
```

Dependencias principales:

- streamlit
- numpy
- pandas
- plotly
- python-docx
- matplotlib
- kaleido

## 🚀 Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/me1lopig/Exterior.git
cd Exterior/PilotesCTE
```

2. Crea un entorno virtual (opcional pero recomendado):

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecuta la aplicación:

```bash
streamlit run PilotesCTE_2.py
```

## 🧭 Uso del programa

Al abrir la aplicación se visualiza la interfaz principal con varias pestañas:

### 1. Estratigrafía
- Definir los estratos del terreno
- Introducir espesor y propiedades geomecánicas
- Ajustar condiciones Corto Plazo / Largo Plazo
- Validar si existen errores de entrada

### 2. Tensiones
- Visualizar perfiles de tensión total, intersticial y efectiva
- Consultar valores puntuales a una profundidad concreta

### 3. Punta
- Matriz de resistencia por punta para distintos pares (L, Ø)
- Identificación de capacidades no calculables

### 4. Fuste
- Matriz de resistencia por fuste
- Evaluación de rozamiento lateral en cada estrato

### 5. Total
- Capacidad total del terreno
- Comparación entre resistencia geotécnica y límite estructural

### 6. Tope estructural
- Verificación de la resistencia máxima admisible del pilote
- Señalización de combinaciones gobernadas por estructura

### 7. Auditoría
- Revisión detallada de una combinación (D, L)
- Consulta del bulbo, resistencia por tramo y resistencia final

### 8. Formulación
- Resumen de ecuaciones aplicadas del CTE DB-SE-C
- Descripción del método utilizado

## 📝 Flujo de trabajo recomendado

1. Definir la estratigrafía del sondeo.
2. Introducir condiciones geotécnicas y de nivel freático.
3. Seleccionar el método de ejecución y el tipo de pilote.
4. Definir diámetro y longitud de estudio.
5. Ejecutar el cálculo.
6. Revisar la matriz final y las gráficas.
7. Generar el informe Word si procede.

## 📌 Nota técnica

La aplicación incluye comprobaciones para evitar extrapolar condiciones no reconocidas del terreno. Si el bulbo del pilote supera la profundidad definida por el sondeo, la combinación queda marcada como N/D y no se calcula.

## 🛡️ Licencia y uso

Este proyecto se entrega con fines de análisis, cálculo y documentación técnica. Su uso debe realizarse bajo criterio profesional, validando la información geotécnica, normativa vigente y condiciones particulares del proyecto.

## 🔗 Información del proyecto

- Repositorio: Exterior
- Carpeta: PilotesCTE
- Aplicación principal: PilotesCTE_2.py

Si necesitas, puedo ayudarte a personalizar este README con:

- estilo corporate más premium
- versión en inglés
- versión con logo institucional
- versión más técnica para ingeniería
- versión resumida para GitHub y otra para usuarios internos

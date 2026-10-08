# 📚 Tablas de parámetros geotécnicos

Este directorio centraliza la lógica y los datos para una base de consulta de propiedades de suelos, diseñada para presentarlas de forma clara y separada por fuente documental.

La solución está organizada en cuatro piezas principales:

- 🖥️ una interfaz de usuario en Streamlit
- ⚙️ un motor de acceso a datos
- 🗂️ archivos YAML con las fuentes tabuladas
- 🧪 validaciones automáticas de calidad y consistencia

---

## 🧭 Objetivo del módulo

El proyecto permite consultar parámetros geotécnicos del terreno (densidades, cohesión, ángulo de fricción, permeabilidad, etc.) según la fuente documental aplicable.

Cada documento se gestiona como una fuente independiente:

- no se mezclan datos entre normas o manuales
- cada pestaña representa una fuente distinta
- los valores se muestran según su formato original y su unidad
- la información puede reutilizarse desde Python, notebooks o una interfaz web

---

## 📁 Estructura del directorio

```text
tablas/
├── app.py                    # Interfaz de usuario con Streamlit
├── build_data.py             # Generador de datos desde Excel a YAML
├── soil_params_engine.py     # Motor de acceso y formateo de datos
├── requirements.txt          # Dependencias del proyecto
├── data/                     # Fuentes tabuladas en formato YAML
│   ├── grundbau_taschenbuch.yaml
│   ├── eau_1970.yaml
│   ├── navfac_1971.yaml
│   ├── metrosur_1999.yaml
│   ├── cte_densidades.yaml
│   ├── cte_prop_basicas.yaml
│   ├── cte_permeabilidad.yaml
│   └── _indice.yaml
├── tests/                    # Validaciones automáticas
│   └── test_engine.py
└── README.md                 # Documentación del módulo
```

---

## 🧩 Descripción de los archivos

### 1) `app.py` — interfaz de consulta

Archivo principal de la aplicación web.

- 🪨 crea una interfaz con Streamlit
- 📑 organiza la información por pestañas, una por fuente
- 🔎 incluye búsqueda por tipo de suelo
- 📊 presenta tablas formateadas y legibles para el usuario
- ⚠️ muestra advertencias sobre la naturaleza orientativa de los valores

Este archivo depende del motor `soil_params_engine.py` para cargar y formatear los datos.

### 2) `soil_params_engine.py` — motor de datos

Es el núcleo del sistema.

- 📦 carga automáticamente los archivos YAML de `data/`
- 🧮 expone funciones para listar fuentes y obtener tablas
- 🔄 convierte valores nativos a formato visual adecuado
- 📏 gestiona unidades, rangos, permeabilidades y texto de presentación
- 🧱 no depende de Streamlit, por lo que puede reutilizarse en scripts o notebooks

Funciones clave:

- `cargar()`
- `lista_fuentes()`
- `get_fuente(fuente_id)`
- `tabla(fuente_id)`
- `tabla_formateada(fuente_id)`

### 3) `build_data.py` — generación de datos

Este archivo transforma los datos originales desde Excel a estructura YAML normalizada.

- 📥 lee el archivo Excel fuente
- 🧹 aplica correcciones de unidades y erratas
- 📐 convierte rangos y texto a formatos consistentes
- 🧪 valida límites físicos plausibles
- 💾 genera uno o varios YAML en `data/`

Incluye reglas de saneado como:

- corrección de unidades erróneas
- separación de rangos tipo `a-b`
- conversión de valores vacíos a `null`
- normalización de nombres de suelos y etiquetas

### 4) `data/` — base de conocimiento

Carpeta que contiene los datos estructurados por fuente documental.

Cada archivo YAML incluye:

- `meta`: información de la fuente
- `columnas`: definiciones de campo, etiqueta, unidad y tipo
- `filas`: registros de cada tipo de suelo

Esto permite mantener la información legible, reutilizable y verificable.

### 5) `tests/test_engine.py` — validación automática

Conjunto de pruebas que comprueban:

- ✅ que todas las fuentes tienen referencia bibliográfica
- ✅ que columnas y filas están consistentes
- ✅ que no quedan unidades corruptas o erróneas
- ✅ que los valores caen dentro de rangos físicos plausibles
- ✅ que los datos siguen el formato esperado

### 6) `requirements.txt` — dependencias

Lista las librerías necesarias para ejecutar la aplicación y las validaciones, principalmente:

- `streamlit`
- `pandas`
- `pyyaml`
- `openpyxl`

---

## 🚀 Puesta en marcha

1. Instala las dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecuta la app:

```bash
streamlit run app.py
```

3. En la interfaz, selecciona la fuente documental aplicable y consulta sus valores.

---

## 🏗️ Modelo de datos

La estructura general de cada fuente es la siguiente:

```yaml
meta:
  id: 1
  fuente_id: grundbau_taschenbuch
  nombre: Grundbau-Taschenbuch
  cita: "Referencia bibliográfica"
  nota: "Comentario adicional"

columnas:
  - campo: gamma_ap
    etiqueta: "γ aparente"
    unidad: "kN/m³"
    tipo: rango

filas:
  - tipo_suelo: Arena
    gamma_ap: [16, 19]
    phi: [30, 35]
```

Tipos de columna típicos:

- `text`: texto libre
- `num`: valor numérico
- `rango`: intervalo `[min, max]`
- `perm`: permeabilidad
- `par`: pares de valores asociados

---

## 🔐 Nota importante

Los valores contenidos en estas tablas son de carácter orientativo y no sustituyen la caracterización geotécnica específica de un emplazamiento mediante ensayos.

---

## 📌 Resumen ejecutivo

Este módulo permite:

- mantener una base de parámetros geotécnicos ordenada por fuente
- evitar mezclar criterios de distintas normas
- reutilizar la información desde la UI o desde scripts
- normalizar y validar los datos antes de su uso

Si necesitas ampliar la base con nuevas referencias, el flujo recomendado es:

1. añadir la nueva fuente en `data/`
2. actualizar la generación si partimos del Excel original
3. ejecutar la validación con `pytest`
4. verificar la visualización en la interfaz web

---

## 🧪 Comandos útiles

```bash
python build_data.py
pytest -q
streamlit run app.py
```

---

## ✅ Conclusión

El directorio `tablas` es la capa de conocimiento y acceso a datos geotécnicos del proyecto. Combina datos estructurados, validación, reutilización y presentación clara, todo ello organizado por origen documental para asegurar trazabilidad y rigor técnico.

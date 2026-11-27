# 📐 GeoSlope — Estabilidad de taludes temporales

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Geotecnia](https://img.shields.io/badge/Geotecnia-Equilibrio_límite-4C8BF5)
![Licencia](https://img.shields.io/badge/Licencia-GNU_GPL_v3-6B7280)

Aplicación interactiva desarrollada con **Streamlit** para el análisis preliminar bidimensional de **estabilidad de taludes temporales** mediante superficies de falla circulares.

Permite configurar la geometría, el perfil estratigráfico y el nivel freático; ejecutar los métodos de **Fellenius** y **Bishop simplificado**; explorar la sensibilidad paramétrica; visualizar la sección crítica; consultar las dovelas; y generar resultados descargables.

> **⚠️ Aviso:** el software es una herramienta de apoyo al cálculo geotécnico y no sustituye la revisión de un proyectista competente, la caracterización del terreno ni las comprobaciones exigidas por la normativa aplicable.

---

## ✨ Funcionalidades

- 🏗️ Definición de proyecto, geometría, pendiente y profundidad del modelo.
- 🪨 Perfil estratigráfico horizontal con pesos unitarios secos/saturados, cohesión y ángulo de fricción.
- 💧 Nivel freático horizontal y presión intersticial hidrostatica.
- 📊 Cálculo por los métodos **Fellenius** y **Bishop simplificado**.
- 🔎 Búsqueda determinista de superficies circulares críticas con tres densidades de malla.
- 📈 Análisis de sensibilidad frente a pendiente y profundidad del nivel freático.
- 🧱 Desglose completo de la superficie crítica por dovelas.
- 🗺️ Representación interactiva de geometría, estratigrafía y superficie de falla.
- 📄 Exportación de informe técnico en **DOCX**.
- 📥 Exportación de sensibilidad y dovelas en **CSV**.
- ✅ Validación de geometría, estratigrafía, parámetros y barridos.

---

## 🧮 Modelo de cálculo

La aplicación utiliza:

- Equilibrio límite bidimensional por metro de ancho.
- Superficies circulares.
- Criterio efectivo de **Mohr-Coulomb**.
- Método de **Fellenius**.
- Método de **Bishop simplificado** con iteración del factor de seguridad.
- Discretización mediante dovelas.
- Integración del peso por estrato y condición seca/saturada.
- Presión intersticial hidrostatica bajo el nivel freático horizontal.

La búsqueda explora familias discretas de círculos y el mínimo obtenido depende de la densidad de búsqueda, el número de dovelas y el dominio admisible. Conviene contrastar el resultado con mallas más detalladas y revisar la convergencia.

### 🚫 No incluido

- Sismos o aceleraciones dinámicas.
- Sobrecargas externas.
- Anclajes, geosintéticos o sistemas de contención.
- Cargas hidráulicas externas.
- Consolidación o deformación mecánica.
- Respuesta no drenada mediante parámetros efectivos.
- Etapas constructivas o excavaciones sucesivas.

---

## 🗂️ Estructura del paquete

```text
slope_stability_app/
├── app.py                   # Interfaz Streamlit y flujo principal
├── calculations/
│   ├── geometry.py          # Geometría y construcción de círculos
│   ├── search.py            # Búsqueda de superficies críticas
│   ├── sensitivity.py       # Barridos paramétricos
│   └── stability.py         # Fellenius, Bishop y cálculo por dovelas
├── models/
│   └── inputs.py            # Dataclasses y validación del dominio
├── services/
│   ├── report.py            # Generación de informes DOCX
│   └── validation.py        # Revisión de entradas y avisos
├── utils/
│   └── tables.py            # Preparación de tablas exportables
└── visualization/
    └── charts.py            # Gráficos interactivos Plotly
```

---

## 🚀 Instalación y ejecución

Desde la raíz del repositorio:

### Windows

```bat
iniciar_windows.bat
```

### Linux o macOS

```bash
chmod +x iniciar_linux.sh
./iniciar_linux.sh
```

### Ejecución manual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abrir después la dirección que indique Streamlit, normalmente:

```text
http://localhost:8501
```

---

## 📦 Dependencias principales

- **Streamlit** — interfaz web.
- **Plotly** — visualización interactiva.
- **Pandas** — tablas y exportación CSV.
- **NumPy** — geometría, integración y cálculo numérico.
- **python-docx** — generación de informes DOCX.
- **Matplotlib** — figuras integradas en el informe.

Las dependencias completas se encuentran en `requirements.txt` de la raíz del repositorio.

---

## 🧭 Uso básico

1. **Proyecto y geometría**: indique altura, pendiente, profundidad del modelo y nivel freático.
2. **Suelos**: registre las capas horizontales y sus propiedades resistentes.
3. **Cálculo**: seleccione dovelas, densidad de búsqueda y tolerancias numéricas.
4. **Sensibilidad**: configure los rangos de pendiente y nivel freático.
5. **Calcule** el caso base desde el panel lateral.
6. Revise los factores de seguridad, la superficie crítica y el desglose por dovelas.
7. Genere y descargue el informe DOCX o los datos CSV.

---

## 📤 Exportaciones disponibles

| Exportación | Contenido |
|---|---|
| `informe_*.docx` | Informe técnico, geometría, parámetros, resultados y gráfico crítico |
| `sensibilidad_*.csv` | Combinaciones paramétricas y factores de seguridad |
| `dovelas_superficie_critica.csv` | Variables y esfuerzos de las dovelas seleccionadas |

---

## ⚠️ Consideraciones técnicas

- El factor objetivo es un criterio definido por el usuario y no se asigna automáticamente a una norma.
- Debe verificarse la profundidad suficiente del dominio.
- La suma de espesores debe cubrir la profundidad calculada.
- Los parámetros efectivos c′ y φ′ deben proceder de ensayos representativos y una hipótesis drenada adecuada.
- Los resultados discretos deben someterse a estudio de sensibilidad y convergencia.
- La densidad de búsqueda detallada puede implicar un coste computacional mayor.

---

## 🤝 Contribución

Las contribuciones deben conservar:

- Separación entre modelos, cálculos, servicios y visualización.
- Tipado explícito en las funciones principales.
- Validaciones antes de iniciar cálculos costosos.
- Pruebas numéricas de geometría y factores de seguridad.
- Mensajes de entrada y resultados claros en español.

Antes de incorporar cambios, se recomienda verificar con casos comparativos que los métodos y las exportaciones no modifican su convenio de unidades o signos.

---

## 🛡️ Alcance y responsabilidad

Este paquete forma parte de la suite geotécnica del repositorio **Exterior**. Su uso está orientado a estudios preliminares, enseñanza y apoyo a ingeniería geotécnica.

Cualquier resolución ejecutiva o verificativa debe basarse en:

- Datos geotécnicos representativos.
- Combinaciones y estados límite aplicables.
- Normativa vigente.
- Criterios de seguridad adoptados por el proyectista.
- Revisión independiente de los resultados.

---

## 📚 Módulos relacionados del repositorio

- `app.py` — punto de entrada general de la suite.
- `GeoTalud/` — variante ampliada del proyecto de taludes.
- `TaludesTemporales/` — variante independiente de entrada.
- `requirements.txt` — entorno global del repositorio.

## 📄 Licencia

Consulte el archivo [`LICENSE`](https://github.com/me1lopig/Exterior/blob/main/LICENSE) de la raíz del repositorio para conocer los términos aplicables.

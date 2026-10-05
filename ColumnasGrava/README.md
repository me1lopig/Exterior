# Diseño de Columnas de Grava

## Descripción general

Esta carpeta contiene una aplicación desarrollada en Python con Streamlit para evaluar la mejora del terreno mediante columnas de grava, siguiendo los principios del método de homogeneización propuesto por Priebe (1995). La herramienta permite analizar cómo varían los parámetros equivalentes del suelo tratado en función del diámetro de la columna, el tipo de malla y las propiedades del material granular y del terreno original.

El proyecto está orientado a aplicaciones de ingeniería geotécnica, especialmente en la predimensionamiento y estudio de mejora de terrenos mediante inclusiones granulares, con salida de resultados tabulados y reportes descargables en Excel y Word.

## Objetivo del proyecto

El objetivo principal es automatizar el cálculo de:

- geometría de la columna y el área tributaria,
- tasa de sustitución o relación Ac/A,
- parámetros intermedios del método de Priebe,
- parámetros equivalentes del terreno mejorado,
- evolución de la cohesión, ángulo de fricción y módulo de elasticidad,
- generación de informes técnicos listos para exportar.

## Estructura del código

### 1) `app.py`
Archivo principal de la interfaz gráfica.

Responsabilidades:

- Configuración de la aplicación Streamlit.
- Definición de la interfaz de usuario con parámetros de entrada.
- Generación de gráficos comparativos mediante Plotly.
- Presentación de tablas de resultados.
- Carga de la lógica de cálculo y generación de informes.
- Descarga de archivos Excel y Word desde la propia aplicación.

Incluye:

- sidebar con parámetros del terreno y de la grava,
- cálculo automático de una serie de diámetros de columnas,
- visualización de resultados en pestañas,
- botones de descarga para matrices de cálculo y memoria técnica.

### 2) `funciones_grava.py`
Módulo de cálculo matemático y estructuración de datos.

Responsabilidades:

- Cálculo del área de la columna de grava.
- Determinación del área tributaria para malla cuadrícula y tresbolillo.
- Cálculo de la relación Ac/A.
- Evaluación de variables intermedias del método de Priebe.
- Estimación del coeficiente de mejora y de los parámetros equivalentes del suelo tratado.

La función central `calcular_mejora_excel(...)` devuelve cuatro DataFrames:

- `df_geo`: geometría y relaciones de sustitución,
- `df_int1`: cálculos intermedios de la formulación,
- `df_int2`: coeficientes y factor de mejora,
- `df_params`: parámetros finales equivalentes.

### 3) `informes.py`
Módulo de exportación de resultados.

Responsabilidades:

- Generación de un libro Excel con varias hojas de cálculo.
- Generación de un documento Word con memoria técnica.
- Inclusión de tablas y gráficos en reportes descargables.

Funciones principales:

- `generar_excel_memoria(...)`: crea un archivo Excel en memoria en formato listo para descarga.
- `generar_word_memoria(...)`: crea un documento Word con título, parámetros de diseño y gráficos.

### 4) `requirements.txt`
Archivo de dependencias del proyecto.

Contiene las librerías necesarias para:

- ejecución de la aplicación web,
- procesamiento numérico,
- manipulación de datos tabulares,
- generación de gráficos,
- exportación a Excel y Word,
- renderizado de imágenes para Word.

## Metodología aplicada

El software implementa la lógica del método de Priebe (1995), que permite estimar la mejora del comportamiento del terreno al incorporar columnas de grava. El análisis considera:

- propiedades del material granular (ángulo de fricción y módulo elástico),
- propiedades del suelo original (cohesión, fricción, módulo elástico y coeficiente de Poisson),
- geometría de la malla de columnas,
- distribución de la carga y el grado de mejora del suelo tratado.

A partir de estas variables se obtienen parámetros equivalentes que representan el comportamiento homogéneo del terreno mejorado.

## Casos de uso

La aplicación es útil para:

- análisis preliminares de mejora de suelos,
- evaluación de soluciones con columnas de grava,
- comparación de distintos diámetros de columna,
- estudio de sensibilidad del sistema ante cambios geométricos y mecánicos,
- generación de documentación técnica para proyectos de ingeniería.

## Requisitos para ejecutar

Se requiere Python 3.9 o superior y las dependencias indicadas en `requirements.txt`.

### Instalación

```bash
pip install -r "ColumnasGrava/requirements.txt"
```

### Ejecución

```bash
streamlit run "ColumnasGrava/app.py"
```

## Resultados esperados

La aplicación genera:

- tablas con geometría y relaciones de sustitución,
- valores intermedios de cálculo,
- resultados equivalentes de fricción, cohesión y módulo de elasticidad,
- gráficos comparativos para cada parámetro,
- archivos Excel y Word exportables.

## Notas técnicas

- El proyecto está desarrollado de forma modular para facilitar mantenimiento y ampliación.
- La lógica de cálculo se mantiene separada de la capa visual.
- La gestión de informes se centraliza en un módulo independiente para simplificar futuras extensiones.
- La aplicación está preparada para usarse como herramienta de cálculo y presentación en entornos de ingeniería geotécnica.

## Conclusión

El contenido de esta carpeta constituye una herramienta de cálculo y análisis técnico para la mejora de terrenos mediante columnas de grava. Combina metodología geotécnica, automatización de cálculo, visualización de resultados y generación de documentos técnicos, convirtiéndola en un recurso útil para la fase de diseño y estudio comparativo de alternativas constructivas.

---

Este README está pensado como una guía técnica de referencia para comprender la finalidad y funcionamiento de la aplicación dentro de la carpeta `ColumnasGrava`.

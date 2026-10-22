# Cimentaciones superficiales en suelos

Aplicación Streamlit que reproduce la pestaña `SUELOS` del libro `zapatas_2.xlsm`.
Integra la presión vertical admisible por hundimiento, el asiento elástico por
estratos y la selección del estado límite que gobierna.

## Instalación y ejecución

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

- `app.py`: interfaz, estado y validación de entradas.
- `modelos/`: estructuras de datos tipadas.
- `calculos/`: capacidad portante, asientos y combinación de resultados.
- `visualizacion/`: gráficos de resultados.
- `utiles/`: adaptación de resultados a tablas.
- `tests/`: regresión frente a los valores almacenados en Excel.

## Métodos de asiento

La opción **Convención del Excel** reproduce la macro original mediante
`s_centro = 2 · s_esquina(B,L)`. La opción **Superposición B/2 × L/2** calcula
el centro mediante cuatro cuadrantes. La selección debe documentarse en el
proyecto porque puede modificar de forma relevante la presión limitada por
asientos en perfiles estratificados.

## Coeficiente de balasto

El selector de material distingue únicamente entre **Cohesivo** y
**Granular**. La aplicación obtiene primero `k_s,BL = q/s`, elimina el efecto
de la forma rectangular mediante la expresión E.8 y transforma el resultado
a la placa de 30 cm con E.6 (cohesivos) o E.7 (granulares) del CTE DB SE-C.

## Pruebas

Desde la carpeta del proyecto:

```bash
python -m unittest discover -s tests -v
```

Los resultados son una ayuda al cálculo y requieren revisión geotécnica,
comprobación de hipótesis y encaje con la normativa aplicable al proyecto.

# Calculo de asientos de cimentaciones

Aplicacion Streamlit para cimentaciones rectangulares, circulares y bandas. Separa la interfaz, el nucleo de calculo, los modelos, la visualizacion y la exportacion.

## Instalacion y ejecucion

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Convenciones

- Longitud: m; tensiones y presiones: kPa; asiento mostrado: mm; tiempo: anos.
- Profundidad positiva hacia abajo y asiento/compresion positivo.
- El nivel freatico `0,00 m` representa agua en la superficie. "Sin agua" es un estado distinto.
- Como alternativa puede definirse un perfil piezometrico por pares profundidad-presion `z-u`.
- La carga puede introducirse como bruta o neta. Para la carga bruta se resta el terreno excavado al calcular incrementos; el contacto siempre se comprueba con presiones brutas.

## Formulaciones

- Integracion de Boussinesq sobre rectangulo, circulo real o banda.
- Presion lineal por carga vertical y momentos con contacto sin traccion.
- Base rigida mediante matriz de flexibilidad del semiespacio y compatibilidad de un plano de desplazamientos.
- Asiento inmediato por deformacion elastica 3D o aproximacion unidimensional identificada.
- Consolidacion 1D de Terzaghi por estrato cohesivo saturado, con `cv`, drenaje y `t95` propios.
- Compresion secundaria desde el `t95` de cada unidad drenante hasta la vida de servicio.

## Alcance

El indicador de cumplimiento compara el asiento calculado con el limite definido por el usuario. No sustituye una comprobacion normativa completa. Para estratificacion con gran contraste de rigidez, cargas tridimensionales complejas o interaccion suelo-estructura evolutiva se recomienda un modelo multicapa contrastado o FEM.

Las zapatas y losas se identifican por separado. La losa se resuelve mediante los limites de base flexible o rigida; no se representa la flexion de placa. El tipo pozo/caisson se bloquea porque requiere transferencia por fuste y base y no debe reutilizar el modelo de cimentacion superficial.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

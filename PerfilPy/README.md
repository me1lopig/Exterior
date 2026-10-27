# Geocempy mejorado

Aplicacion Streamlit para revisar, corregir, visualizar y exportar perfiles geologico-geotecnicos a DXF.

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

En Linux, activa el entorno con `source .venv/bin/activate`.

## Entrada

La aplicacion acepta los XLSX individuales o un unico ZIP. Los archivos base esperados son:

- `BKFL.XLSX`
- `DPRG.XLSX`
- `ISPT.XLSX`
- `ListadoLab.XLSX`
- `UGEO.XLSX`, cuando se desee representar unidades geotecnicas

Los perfiles se reconocen por los encabezados `ESTACION`, `Distancia` y `Cota`. Otros libros, como AGS o LOCA, se conservan como auxiliares y no se ofrecen como perfiles.

## Flujo recomendado

1. Cargar los archivos y revisar las tablas normalizadas.
2. Resolver los valores ambiguos del nivel freatico.
3. Corregir errores y revisar los avisos de coherencia.
4. Comprobar la vista previa.
5. Generar el DXF y descargar, si procede, el Excel normalizado corregido.

## Escala vertical

Para cada perfil se calcula la cota del fondo de todas las prospecciones como `cota de boca - profundidad`. El limite inferior adopta la cota de fondo mas baja y añade un margen automatico del 10 % de la profundidad maxima, limitado entre 1 y 5 m. El limite superior incluye un margen entre 1 y 3 m sobre la cota maxima del terreno.

El paso vertical se selecciona en la serie `1, 2, 5 x 10^n` para obtener una reticula legible. Los limites y el paso pueden sustituirse manualmente por perfil, pero la aplicacion impide exportar si alguna prospeccion o el terreno quedan fuera del marco.

## Configuracion grafica

La barra lateral incluye los presets `Compacta`, `Normal` y `Ampliada`. Cada preset puede ajustarse antes de generar el perfil. Los controles modifican conjuntamente la vista previa y el DXF:

- altura de valores de ejes;
- altura de nombres de sondeos y DPSH;
- altura de textos litologicos y UGEO;
- altura de textos de ensayos;
- altura del titulo;
- separacion horizontal de los textos;
- separacion vertical de ensayos coincidentes;
- separacion de los nombres sobre la rasante.

Las magnitudes se expresan en metros del espacio modelo DXF. La aplicacion valida valores no fisicos o desproporcionados e invalida el DXF anterior cuando cambia la configuracion.

## Convenciones

- Cotas: positivas hacia arriba.
- Profundidades: positivas hacia abajo desde la boca de cada investigacion.
- Nivel freatico detectado a `0.00 m`: situado en superficie.
- `No detectado` y `No medido` son estados diferentes y no se sustituyen por valores numericos.
- La aplicacion no interpola contactos entre sondeos. Representa columnas en las posiciones indicadas por el perfil.

## Limitaciones

La correlacion entre unidades, la extrapolacion lateral y la interpretacion geologica requieren criterio tecnico y no se generan automaticamente. La vista previa es un control grafico; el DXF debe revisarse en el flujo CAD del proyecto antes de su emision.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

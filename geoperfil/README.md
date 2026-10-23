# GeoPerfil 2D

Aplicacion Streamlit para construir perfiles geologicos 2D a partir de sondeos y representar ensayos DPSH como polilineas `N20`-cota.

La carpeta puede renombrarse libremente al desplegarla en Streamlit Cloud.
En Streamlit Cloud seleccione `app.py` como archivo principal y mantenga `requirements.txt` en la misma carpeta.

## Alcance de la version 0.2

- Importacion y edicion de sondeos, intervalos, unidades y DPSH.
- Ejes rectos o poligonales en coordenadas XY.
- Proyeccion por minima distancia y control de corredor.
- MiniCAD SVG para dibujar, seleccionar, mover, insertar y eliminar contactos.
- Ajuste magnetico a interfaces observadas y vertices existentes.
- Deshacer, rehacer, zoom, encuadre y desplazamiento del lienzo.
- Borrador automatico opcional desde las columnas de sondeo.
- Polygonizacion topologica de lentes, intercalaciones y pinzamientos.
- Asignacion de unidad, color y trama a cada zona cerrada.
- DPSH representado mediante puntos unidos por segmentos rectos.
- Exportacion a JSON, Excel, HTML, CSV, DXF y PDF.

Los DPSH se representan sin convertirlos a SPT, sin clasificar el terreno y sin modificar los contactos. La correlacion geologica y la asignacion de zonas siguen siendo decisiones tecnicas del usuario.

## Instalacion

Entre en la carpeta descomprimida `perfil_geologico` y ejecute:

```bash
python -m venv .venv
```

En Windows:

```powershell
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

En Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Convenciones

- Coordenadas horizontales y cotas en metros.
- Cota `z` positiva hacia arriba.
- Profundidad positiva hacia abajo.
- La abscisa `s` aumenta con el orden de los vertices del eje.
- La distancia lateral es positiva a la izquierda del eje orientado.
- El DXF se exporta en coordenadas locales `X=s`, `Y=z`.

## Formato Excel

La propia aplicacion permite descargar una plantilla con datos demostrativos. Las hojas obligatorias son:

- `Sondeos`
- `Intervalos`
- `Unidades`
- `Ensayos_DPSH`
- `Lecturas_DPSH`

La hoja `Eje` es opcional durante la importacion, aunque debe definirse antes de generar el perfil.

## Pruebas

```bash
cd ..
python -m unittest discover -s perfil_geologico/tests -v
python -m compileall -q perfil_geologico
```

## Limitaciones conocidas

- La superficie del terreno se obtiene de las cotas de boca de los sondeos.
- No se representan todavia fallas ni pliegues volcados.
- Los extremos de los contactos deben alcanzar el contorno o coincidir con otro contacto para dividir una zona.
- La comprobacion topologica no sustituye la revision geologica del tecnico responsable.

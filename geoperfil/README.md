# GeoPerfil 2D

Aplicacion Streamlit para construir perfiles geologicos 2D a partir de sondeos y representar ensayos DPSH como polilineas `N20`-cota.

La carpeta puede renombrarse libremente al desplegarla en Streamlit Cloud.
En Streamlit Cloud seleccione `app.py` como archivo principal y mantenga `requirements.txt` en la misma carpeta.

## Correccion de precision v0.5.1

Esta revision es una correccion puntual sobre v0.5, no la estabilizacion integral v0.6:

- Conversion del raton a coordenadas SVG mediante la matriz real del navegador
  (`getScreenCTM().inverse()`) para evitar desfases por ajuste de ancho,
  margenes del `viewBox`, zoom o cambio de tamano de ventana.
- Distancias de captura medidas en pixeles reales de pantalla.
- Un mismo radio para resaltar y capturar las interfaces observadas.
- Las interfaces observadas tienen prioridad sobre lineas interpretadas proximas.
- No se arrastran accidentalmente vertices clasificados como observados.
- Se impide crear nuevos puntos fuera del area de trazado.
- Tooltip de interfaces posicionado con la transformacion real.

Verificacion efectuada: 17 pruebas del nucleo y 6 pruebas con Chromium
con diferentes anchos, cambio de tamano, zoom y captura magnetica.
En entornos sin Playwright/Chromium las pruebas del navegador se omiten.
Estas comprobaciones NO cierran el resto de hallazgos de la auditoria v0.5.

Para reproducir las pruebas de interfaz (opcional):

```bash
pip install playwright pytest
python -m playwright install chromium
pytest -q tests/test_minicad_browser.py
```

## Alcance de la version 0.5

- Importacion y edicion de sondeos, intervalos, unidades y DPSH.
- Ejes rectos o poligonales en coordenadas XY.
- Proyeccion por minima distancia y control de corredor.
- MiniCAD SVG simplificado con herramientas para introducir o borrar contactos
  abiertos y lentejones cerrados, rellenar o vaciar zonas y limpiar toda la
  interpretacion.
- Resaltado al pasar el cursor y marcador en aspa sobre interfaces observadas, con profundidad y unidades contiguas.
- Dibujo de contactos abiertos y lentes cerradas para intercalaciones locales y acunamientos.
- Seleccion implicita, movimiento de vertices e insercion mediante doble clic,
  sin recargar la barra principal con operaciones CAD avanzadas.
- Borrado diferenciado de contactos y lentejones; vaciado de rellenos y limpieza
  completa de bordes y zonas con confirmacion.
- Ajuste magnetico a interfaces observadas y vertices existentes, anulable temporalmente con `Alt`.
- Deshacer, rehacer, zoom, encuadre y desplazamiento del lienzo.
- Avisos de autointerseccion, cruces, extremos abiertos y zonas de area anormalmente pequena.
- Vinculos estables con interfaces de sondeo y actualizacion explicita si cambian los datos originales.
- Hipotesis alternativas persistentes, recuperables y superponibles como referencia grafica.
- Borrador orientativo opcional y conservador: solo correlaciona interfaces presentes en varios sondeos.
- Deteccion de intercalaciones locales A-B-A y propuesta de lente cerrada cuando ambos sondeos contiguos confirman la ausencia de B.
- Tratamiento independiente y con identificadores unicos de unidades alternantes
  repetidas, por ejemplo A-B-A-B-A.
- Aviso sin cierre automatico cuando falta cobertura vertical o control lateral suficiente.
- Acunamientos provisionales a media distancia, siempre identificados como interpretados y editables.
- Polygonizacion topologica de lentes, intercalaciones y pinzamientos.
- Asignacion de unidad, color y trama a cada zona cerrada.
- DPSH representado mediante puntos unidos por segmentos rectos.
- Separacion segura de tramos DPSH con lagunas de lectura, conservando su
  estructura tabular para la representacion.
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

# GeoPerfil 2D

Aplicacion Streamlit para construir perfiles geologicos 2D a partir de sondeos y representar ensayos DPSH como polilineas `N20`-cota.

La carpeta puede renombrarse libremente al desplegarla en Streamlit Cloud.
En Streamlit Cloud seleccione `app.py` como archivo principal y mantenga `requirements.txt` en la misma carpeta.

## Version v0.6.0 - Revision de estabilidad (26/10/2026)

Esta version **no incorpora un CAD generalista**. Corrige y simplifica el flujo
existente; sigue siendo un prototipo sometido a validacion geologica.

### Cambios funcionales

- Se retira **Generar borrador orientativo** de la interfaz. La geologia se interpreta
  solo dibujando contactos abiertos y lentejones cerrados.
- Al finalizar, borrar o modificar una geometria, el MiniCAD guarda la operacion y
  solicita automaticamente a Python el recalculo de zonas. Tras actualizarse las
  zonas, **Rellenar** se puede utilizar sin un guardado manual intermedio.
- Deshacer/rehacer y el borrado de rellenos solicitan su persistencia; el proyecto
  JSON conserva los datos y las zonas actualizados recibidos de MiniCAD.
- Al dividir una zona previamente clasificada, las nuevas zonas quedan **sin
  unidad asignada** hasta que el tecnico las clasifique. Solo se conserva el
  relleno si la geometria permanece esencialmente identica.
- Las interfaces observadas estan protegidas frente al arrastre y frente a edicion
  numerica no autorizada; Python verifica sus coordenadas al recibir el MiniCAD.
- Cambios de eje, importacion de Excel y restablecimiento que descarten geometria
  requieren confirmacion explicita; editar sondeos/intervalos ya no borra los
  contactos silenciosamente.
- Guardado JSON con metadatos de columnas de las tablas, compatible tambien con
  proyectos anteriores cuando no contenian ensayos DPSH.
- Validaciones adicionales de datos finitos, colores, identificadores, profundidad
  final, lecturas DPSH y contactos fuera de los valores observados.
- DPSH con lagunas se representa por tramos independientes en MiniCAD, Plotly y PDF.
- Tratamiento de huecos de poligonos en MiniCAD, Plotly y PDF; polilineas DXF
  cerradas identificadas como tales.
- Control H/V en Proyecto. La relacion se aplica en el perfil Plotly y en el PDF;
  el MiniCAD adapta el alto del lienzo y muestra el factor visual efectivo si
  los limites de altura del editor impiden mostrar exactamente la relacion pedida.
- El MiniCAD trata los textos de los sondeos como texto, no como HTML activo.

### Uso recomendado

1. Importe Excel y revise los avisos de validacion.
2. Configure eje y exageracion vertical.
3. Entre en MiniCAD y dibuje **Introducir contacto** o **Introducir lentejon**.
4. Termine con el boton **Finalizar**, Enter o doble clic; tras recalcular zonas,
   pulse **Rellenar** y asigne unidad/trama a cada cara.
5. Descargue el proyecto JSON como respaldo. Abra el JSON y compruebe que se han
   recuperado contactos y rellenos antes de considerar validada la sesion.
6. Revise la coincidencia del PDF/DXF con el perfil interpretado.

### Validacion

En el entorno de desarrollo se han superado 37 tests: 17 de nucleo anteriores,
6 del cursor mediante Chromium, 10 nuevos de regresion y 4 de dibujo/guardado/
relleno bajo distintas escalas, tambien con Chromium. Se ha ensayado un proyecto
Excel sintetico complejo, su persistencia JSON, y exportaciones PDF/DXF.
**No se ha realizado una prueba manual completa de Streamlit sobre macOS ni una
validacion geologica independiente**; por ello se suministra como version de
pruebas de estabilizacion y no como producto aprobado para uso profesional.

### Limitaciones conocidas

- El terreno se interpola a partir de las bocas de sondeo, no de un MDT.
- El trazado libre de contactos entre sondeos representa una hipotesis del tecnico.
- Los extremos abiertos que no cierran una cara no pueden rellenarse.
- Los huecos en la vista Plotly usan relleno liso, aunque las demas caras
  pueden representar las tramas seleccionadas.
- La escala H/V define la relacion geometrica visual; no convierte por si sola
  una impresion en papel a una escala fisica certificada.
- Si aparecen contactos observados desactualizados, deben revisarse explicitamente.

### Pruebas

```
python -m pytest -q tests
python -m compileall -q .
streamlit run app.py
```

Para pruebas en navegador se necesita Playwright y Chromium instalados. Si no
estan disponibles, esas pruebas se omiten; el nucleo Python se ejecuta igualmente.

El Excel `ejemplos/caso_complejo_topografia_unidades.xlsx` contiene solo datos
**sinteticos** y sirve para probar geometrias complejas y multiples DPSH.

---

## Correccion de precision v0.5.1

Descripcion historica de la mejora del cursor introducida en v0.5.1:

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
- El generador de borradores permanece como funcion heredada interna para compatibilidad, pero no esta disponible en la interfaz v0.6.
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

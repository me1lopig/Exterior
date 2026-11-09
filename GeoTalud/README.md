# GeoSlope - estabilidad de taludes temporales

Aplicacion Streamlit para analisis preliminar de taludes simples mediante equilibrio limite con superficies circulares. Incluye Fellenius, Bishop simplificado, perfil multicapa Mohr-Coulomb, nivel freatico horizontal, barridos parametricos, informe DOCX completo y libro XLSX de resultados.

## Instalacion y ejecucion

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

La aplicacion se abre habitualmente en `http://localhost:8501`.

## Organizacion de la interfaz

- Una unica barra de pestañas separa proyecto y geometria, tabla multicapa de suelos, calculo, sensibilidad, resultados, visualizacion y dovelas.
- El panel lateral concentra las acciones de calculo, el estado de validacion y las descargas.
- Las pestañas de geometria y visualizacion muestran el perfil del talud; tras calcular se incorporan la superficie critica y las dovelas.
- Las pestañas con entradas incluyen una ayuda contextual al final.
- La aplicacion avisa si los resultados visibles o descargables corresponden a entradas anteriores.

## Convenciones y alcance

- Seccion 2D por metro perpendicular al plano.
- Longitudes en m, pesos unitarios en kN/m3, tensiones y cohesion en kPa.
- Pendiente medida respecto a la horizontal.
- Las cotas internas se refieren al pie (`z=0`), pero el usuario introduce profundidades desde coronacion, positivas hacia abajo.
- El nivel freatico se introduce como profundidad desde coronacion: `dNF=0` en coronacion, `dNF=H` en el pie y `dNF>H` bajo el pie.
- La profundidad del modelo define el limite inferior de la estratigrafia y de las superficies circulares admisibles; debe ser mayor o igual que `H`.
- La tabla de suelos admite cualquier numero de capas horizontales, ordenadas desde coronacion, con espesor, pesos unitarios, `c'` y `phi'`.
- La interfaz exige espesores positivos y una suma de espesores mayor o igual que la profundidad del modelo.
- Parametros resistentes efectivos `c'` y `phi'`; no se transforma automaticamente un caso no drenado.
- Presion de poros hidrostatica bajo un nivel horizontal, recortado contra el terreno.
- Busqueda discreta de circulos con puntos de paso en coronacion, cara y berma inferior y un dominio ampliado de centros.
- Las mallas son anidadas: Equilibrada conserva todos los candidatos de Rapida y Detallada conserva los de ambas.

No se incluyen sobrecargas, sismo, refuerzos, agua exterior, succion, filtracion no hidrostatica, etapas de excavacion ni mecanismos no circulares. El factor objetivo lo define el usuario y no representa por si solo una comprobacion normativa.

## Salidas

- El informe DOCX contiene todos los resultados del barrido de sensibilidad, con encabezados repetidos cuando la tabla ocupa varias paginas.
- El libro XLSX contiene las hojas `Resumen`, `Suelos`, `Superficies criticas`, `Sensibilidad`, `Dovelas Bishop` y `Dovelas Fellenius`.
- Una combinacion de sensibilidad sin superficie valida se conserva con estado explicativo sin cancelar el resto del barrido.

## Verificacion

```bash
pytest -q
```

Las pruebas cubren geometria, anidamiento de mallas, calculo de dovelas, convergencia de Bishop, nivel freatico bajo el pie, perfiles multicapa, barrido parametrico, DOCX, XLSX y entradas adversariales.

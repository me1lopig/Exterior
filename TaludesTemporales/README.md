# GeoSlope - estabilidad de taludes temporales

Aplicacion Streamlit para analisis preliminar de taludes simples mediante equilibrio limite con superficies circulares. Incluye Fellenius, Bishop simplificado, uno o dos suelos Mohr-Coulomb, nivel freatico horizontal, barridos parametricos e informe DOCX.

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

- Una unica barra de pestañas separa proyecto y geometria, suelos, calculo, sensibilidad, resultados, visualizacion y dovelas.
- El panel lateral concentra las acciones de calculo, el estado de validacion y las descargas.
- Las pestañas de geometria y visualizacion muestran el perfil del talud; tras calcular se incorporan la superficie critica y las dovelas.

## Convenciones y alcance

- Seccion 2D por metro perpendicular al plano.
- Longitudes en m, pesos unitarios en kN/m3, tensiones y cohesion en kPa.
- Pendiente medida respecto a la horizontal.
- Cotas referidas al pie del talud (`z=0`).
- Con dos suelos, se introducen los espesores verticales de ambos estratos desde la coronacion hasta el pie; el estrato inferior se prolonga bajo el pie para el calculo.
- La interfaz comprueba que ambos espesores sean positivos y que su suma coincida con `H`; bloquea el calculo si detecta huecos, solapes o valores no finitos.
- Parametros resistentes efectivos `c'` y `phi'`; no se transforma automaticamente un caso no drenado.
- Presion de poros hidrostatica bajo un nivel horizontal, recortado contra el terreno.
- Busqueda discreta de circulos con entrada en coronacion y salida en la cara o berma inferior.

No se incluyen sobrecargas, sismo, refuerzos, agua exterior, succion, filtracion no hidrostatica, etapas de excavacion ni mecanismos no circulares. El factor objetivo lo define el usuario y no representa por si solo una comprobacion normativa.

## Verificacion

```bash
pytest -q
```

Las pruebas cubren geometria, calculo de dovelas, convergencia de Bishop, respuesta al agua, segundo estrato, barrido parametrico y entradas adversariales (espesores, `NaN`, infinitos y rangos incoherentes).

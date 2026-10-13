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

## Convenciones y alcance

- Seccion 2D por metro perpendicular al plano.
- Longitudes en m, pesos unitarios en kN/m3, tensiones y cohesion en kPa.
- Pendiente medida respecto a la horizontal.
- Cotas referidas al pie del talud (`z=0`).
- Con dos suelos, se introduce el espesor vertical del estrato superior desde la coronacion. El espesor inferior dentro de `H` se calcula automaticamente y el estrato inferior se prolonga bajo el pie.
- Parametros resistentes efectivos `c'` y `phi'`; no se transforma automaticamente un caso no drenado.
- Presion de poros hidrostatica bajo un nivel horizontal, recortado contra el terreno.
- Busqueda discreta de circulos con entrada en coronacion y salida en la cara o berma inferior.

No se incluyen sobrecargas, sismo, refuerzos, agua exterior, succion, filtracion no hidrostatica, etapas de excavacion ni mecanismos no circulares. El factor objetivo lo define el usuario y no representa por si solo una comprobacion normativa.

## Verificacion

```bash
pytest -q
```

Las pruebas cubren geometria, calculo de dovelas, convergencia de Bishop, respuesta al agua, segundo estrato y barrido parametrico.

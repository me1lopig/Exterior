# Zapatas CTE Geotecnia

Aplicacion Streamlit para el analisis geotecnico de cimentaciones directas. El alcance incluye hundimiento segun CTE DB SE-C, deslizamiento local, posicion de la resultante, presion admisible de servicio basada en SPT, estimaciones de asiento, estratigrafia, sensibilidad y optimizacion geometrica.

No incluye el dimensionamiento estructural de hormigon ni armaduras.

## Metodos implementados

- Hundimiento analitico: CTE DB SE-C 4.3.2 y Anejo F.1.1.
- Geometria efectiva: CTE 4.3.1.3, con excentricidades en valor absoluto.
- Zapata circular excentrica: equivalencia rectangular que conserva area e inercia antes de la reduccion por excentricidad. El informe identifica expresamente esta hipotesis.
- Deslizamiento local: parametros de contacto indicados en CTE 4.2.3.1.
- Presion admisible SPT: expresiones 4.9 y 4.10 y sus limites de aplicacion.
- Asiento granular SPT: Burland y Burbidge, expresiones F.19 a F.24.
- Asiento elastico: semiespacio elastico homogeneo; metodo analitico, no una correlacion normativa.
- Asiento estratificado: reparto 2:1 e integracion por capas; aproximacion analitica para comparacion y sensibilidad.
- Cobertura estratigrafica: deteccion de huecos y control de profundidad hasta `D+1.5B` para hundimiento y `D+ZI` para asientos.

Referencia normativa oficial utilizada: [CTE DB SE-C Cimientos](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf), texto con modificaciones indicadas en el propio documento. Antes de emplear la aplicacion en un proyecto debe comprobarse que esta edicion sigue siendo la exigible para el expediente.

## Instalacion

Se recomienda Python 3.11 o 3.12.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Convenciones

- Longitudes: m.
- Fuerzas: kN, salvo zapata corrida, donde son kN/m.
- Momentos: kNm, salvo zapata corrida, donde son kNm/m.
- Tensiones y resistencias: kPa.
- Pesos especificos: kN/m3.
- Profundidades positivas hacia abajo desde la superficie del terreno.
- `V` es la resultante vertical estructural en la base. La interfaz puede sumar el peso aproximado de zapata y tierras; en el barrido lo recalcula para cada geometria candidata.
- `M_B` genera excentricidad en la dimension B y `M_L` en L.
- Los parametros de resistencia deben introducirse como valores caracteristicos.

## Datos de campo

El cargador admite CSV con una de estas cabeceras:

```text
depth_m,N_spt
```

o bien:

```text
depth_m,qc_MPa
```

La conversion CPT a N equivalente requiere que el usuario declare y justifique la relacion local `qc/N`, de acuerdo con el tipo de suelo y el reconocimiento geotecnico.

## Validacion

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Las pruebas cubren geometria circular centrada, simetria frente al signo del momento, tensiones totales no drenadas, cargas horizontales bidireccionales, factores parciales, nivel freatico, formulas SPT, asientos y tratamiento de datos de campo.

## Limitaciones

- El modelo de hundimiento representa el terreno mediante parametros caracteristicos equivalentes en la zona relevante. La tabla de capas sirve para auditar estratos debiles y calcular asientos, pero no resuelve automaticamente mecanismos de rotura en terrenos estratificados.
- Las geometrías del barrido solo se consideran validas cuando el perfil de materiales cubre de forma continua su bulbo de hundimiento. El asiento estratificado se omite si el perfil no alcanza `D+ZI` o contiene huecos.
- La comprobacion de contacto completo informa sobre el nucleo central; no sustituye una verificacion de equilibrio al vuelco con acciones estabilizadoras y desestabilizadoras separadas.
- Cuando `beta > phi'/2`, cuando existe flujo ascendente o cuando la geometria queda fuera del dominio de las expresiones, la aplicacion emite un aviso o detiene el calculo.
- Los asientos secundarios, arcillas normalmente consolidadas que superan la presion de preconsolidacion, estabilidad global y problemas hidrogeologicos requieren estudios especificos.
- El informe DOCX es una memoria de calculo geotecnico y debe ser revisado por el tecnico responsable junto con el estudio geotecnico y las combinaciones de proyecto.

## Estructura

```text
app.py
calculations/
models/
services/
visualization/
tests/
requirements.txt
requirements-dev.txt
```

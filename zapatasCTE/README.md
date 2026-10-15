# Carga admisible CTE DB SE-C

Aplicacion Streamlit para obtener presiones y cargas admisibles de cimentaciones directas en una malla de dimensiones B-L. Combina la resistencia de hundimiento del CTE DB SE-C con la limitacion por asiento elastico multicapa de Steinbrenner.

No incluye dimensionamiento estructural, deslizamiento, estabilidad global ni metodos basados en SPT, CPTU u OpenSeesPy.

## Flujo principal

1. Definir el proyecto, la tipologia y la cota de apoyo.
2. Introducir la estratigrafia mediante espesores consecutivos, con c', phi', pesos especificos, E_s y Poisson por capa.
3. Seleccionar el estrato representativo para el hundimiento.
4. En condiciones no drenadas, elegir entre cu constante o un perfil tabulado cu(z). En este regimen phi' se fija en cero.
5. Definir rangos y paso de B-L, asiento admisible y profundidad de influencia.
6. Calcular la tabla de presiones y cargas limite.
7. Activar, solo si se necesita, la comprobacion de una geometria con acciones V-H-M.

## Resultados B-L

Para cada geometria se obtiene:

- resistencia bruta de calculo `qd ELU`;
- presion bruta limitada por asiento `qd ELS`;
- presion final `qadm = min(qd ELU, qd ELS)`;
- axil admisible `Nadm` tras descontar los pesos configurados;
- criterio gobernante y estado de cobertura del perfil.

## Asientos

El metodo principal es Steinbrenner multicapa para una cimentacion rigida mediante el punto caracteristico. Cada capa utiliza su modulo elastico `E_s` y su coeficiente de Poisson. La presion neta admisible se obtiene invirtiendo la relacion elastica lineal para el asiento admisible indicado.

El perfil debe cubrir de forma continua el intervalo desde la base hasta `D+ZI`. Para el control del modelo de hundimiento se comprueba adicionalmente la cobertura hasta `D+1.5B`.

## Instalacion

Se recomienda Python 3.11 o 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

En Windows PowerShell, la activacion habitual es `.venv\Scripts\Activate.ps1`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren hundimiento drenado y no drenado, geometria efectiva, perfil cu(z), nivel freatico, cobertura estratigrafica, sobrecarga integrada, Steinbrenner y generacion de la malla de capacidad.

## Convenciones

- Longitudes y profundidades: m.
- Fuerzas: kN; en zapata corrida, kN/m.
- Tensiones y resistencias: kPa.
- Modulos elasticos: MPa.
- Pesos especificos: kN/m3.
- Profundidades positivas desde la superficie hacia abajo.
- El perfil cu(z) usa profundidades absolutas desde la superficie.
- Las presiones de asiento se calculan a partir de presion neta y se muestran tambien como presiones brutas para compararlas con `qd`.

## Referencia

[CTE DB SE-C Cimientos](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf). Antes de usar la aplicacion en un expediente debe comprobarse la edicion normativa aplicable y justificarse la seleccion de parametros caracteristicos.

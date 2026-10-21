# GeoCorr

Aplicacion Streamlit para estimar parametros geotecnicos mediante correlaciones
trazables basadas en SPT, otros ensayos de campo y tablas orientativas del
CTE DB-SE-C.

## Alcance del MVP

- Entrada manual centralizada en la pestaña Datos; las pestañas de calculo usan esa fuente en modo lectura.
- Multiples grupos de datos dentro de un proyecto.
- Valores SPT previamente corregidos y tipificados por el usuario.
- Correlaciones CTE DB-SE-C 4.1, D.23, D.24, D.26-D.29 y F.24-F.26.
- Correlaciones de modulo SPT publicadas por FHWA.
- Calculos de campo para molinete, sismica, DMT, presiometro y placa de carga.
- Interpolacion controlada, sin extrapolacion silenciosa. En D.23 la interpolacion lineal es un criterio adoptado por GeoCorr, no una prescripcion del CTE.
- Informe DOCX reproducible con version, entradas, resultados, valores adoptados, advertencias, formulas y fuentes.

No se incluyen CPT/CPTu ni importaciones desde Excel o CSV.

## Matriz de capacidades

| Ensayo o fuente | Entradas | Salidas implementadas | Condiciones principales |
|---|---|---|---|
| SPT | N corregido tipificado, suelo y fraccion >20 mm cuando proceda | phi efectivo, qu, E, Es e Ic | Compatibilidad del tipo de N y dominio de cada fuente |
| Molinete | Par, geometria y par remoldeado opcional | su de pico, su remoldeada y sensibilidad | Suelos finos; entradas finitas y positivas |
| Sismica | Vs, gamma y Vp opcional | G0, E0 y nu dinamico | Modulos a pequenas deformaciones |
| DMT | p0, p1, u0, tension efectiva, suelo y cementacion | ID, KD, ED; OCR y su solo en arcilla no cementada y KD>=2 | Correlaciones originales de Marchetti |
| Presiometro | EM, plM y parametros opcionales | EM, plM, pf, E equivalente y su | su solo si se aporta presion horizontal; dominio cohesivo |
| Placa de carga | Ev1, Ev2 y K30 opcional ya interpretados | Ev1, Ev2, Ev2/Ev1 y K30 | No interpreta la curva presion-asiento bruta |
| CTE D.24 y D.26-D.29 | Categoria de suelo | Valores orientativos categoriales | No equivalen a valores caracteristicos automaticos |

No estan implementadas correlaciones directas SPT-su/cu ni penetracion dinamica. Deben incorporarse unicamente cuando se seleccione y documente una fuente acreditada y su dominio de validez.

## Instalacion

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

## Convenciones

- Tensiones y resistencias: kPa.
- Modulos: MPa, salvo indicacion expresa.
- Pesos especificos: kN/m3.
- Profundidades: m.
- `s_u` y `c_u` representan resistencia al corte no drenada.
- `C_u` queda reservado al coeficiente de uniformidad granulometrica.

# Cálculo de asientos elásticos de cimentaciones rectangulares

Aplicación Streamlit para estimar el asiento elástico inmediato de una cimentación rectangular mediante Steinbrenner y un modelo 3D de OpenSeesPy.

## Alcance

- Carga vertical centrada y presión neta de servicio.
- Terreno elástico lineal, isótropo y estratificado.
- Zapata flexible con presión uniforme o zapata rígida y lisa.
- El resultado no incluye consolidación primaria, fluencia ni interacción completa suelo-estructura.
- La geometría excavada del MEF no representa contacto lateral, estado geostático ni fases constructivas.

Los valores introducidos como `nu = 0.5` se evalúan como `nu = 0.499` en los dos métodos para evitar la singularidad de la formulación elástica incompresible.

## Instalación y ejecución

```bash
python -m pip install -r requirements.txt
streamlit run app_asientos_FEM_4.py
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren la normalización de `nu`, la validación de datos, el criterio de profundidad de influencia, la cobertura vertical del dominio, la conservación de la carga tributaria y la suma de asientos analíticos por estratos.

El cálculo MEF comprueba además durante cada ejecución el equilibrio entre la carga vertical aplicada y las reacciones de la base.

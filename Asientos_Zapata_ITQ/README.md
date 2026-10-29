# Asientos de zapata rectangular flexible

Aplicación Streamlit para calcular incrementos de tensión de Boussinesq y asientos elásticos por compresión vertical confinada en un terreno multicapa.

## Alcance técnico

- Zapata rectangular flexible con `B <= L` y presión neta uniforme.
- Capas horizontales definidas desde la superficie del terreno.
- Rigidez mediante `E` y `nu`, convirtiendo a `M`, o mediante `M` directo.
- Paso vertical controlado mediante `B/10`, `B/20`, `B/40` o un valor personalizado.
- Inserción exacta de interfaces y control automático de convergencia con `delta_z/2`.
- Tensiones geostáticas totales y efectivas considerando el nivel freático.
- Perfiles bajo el centro, bordes, esquina y puntos exteriores.
- Bulbos de tensión en las direcciones `B` y `L`.
- Exportación de memoria DOCX y datos XLSX.

El método no es una solución elástica multicapa exacta: la distribución de tensiones se obtiene para un semiespacio homogéneo y la estratificación se introduce en la relación `epsilon_z = delta_sigma_z / M`.

## Instalación

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Pruebas

```bash
pytest -q
```

## Convenciones

- Longitudes en metros.
- Tensiones y presiones en kPa o kN/m².
- Módulos de entrada en MPa y conversión interna a kPa.
- Asientos mostrados en mm.
- Profundidad positiva hacia abajo.
- Compresión positiva.


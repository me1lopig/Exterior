# ZapatasCTE v4.2 — paquete autónomo completo (reconstrucción funcional)

Este ZIP **contiene una aplicación Streamlit completa y ejecutable**, con interfaz, motor geotécnico, visualizaciones, módulos, pruebas y documentación. No requiere descargar otro repositorio ni aplicar parches. **No es una copia exacta de `Exterior/zapatasCTE`**: se ha reconstruido a partir de la documentación y código público v4 consultable, al no disponer de los archivos originales descargables en este entorno. Las salidas requieren contraste profesional y comparación con la v4 original antes de sustituirla en producción.

## Arranque

Requiere **Python 3.11 o posterior**, conexión a internet en el equipo de instalación para descargar las dependencias Python y un navegador moderno.

En la carpeta descomprimida:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux / macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Alternativa: `INICIAR_WINDOWS.bat` o `INICIAR_LINUX_MAC.sh` (crean entorno e instalan las dependencias). La aplicación se abre normalmente en `http://localhost:8501`.

## Alcance

- Datos de proyecto y malla de zapatas B × L, con B ≤ L.
- Hundimiento en situaciones drenada y no drenada, sobrecarga `q0`, geometría, profundidad, talud, flujo y nivel freático bajo las hipótesis programadas.
- Asiento inmediato por estratos con Steinbrenner y selección entre superposición central y aproximación histórica de Excel.
- Presiones netas y brutas: hundimiento, asiento y servicio, sin confundirse `q0` con la descarga previa por excavación.
- Módulo de balasto `ks,BL` obtenido de presión neta/asiento y `Ksp30` equivalente para tipo `Cohesivo` o `Granular` (CTE DB-SE-C E.5 a E.8).
- Dos criterios de conversión geométrica: `literal_cte` (por defecto) y `continuo` (adaptación técnica **no literal**; debe justificarse).
- Mapa B × L con **nueve variables**, los seis pares de presiones netas y brutas, dos balastos y estado límite; ficha de geometría y comparación neta/bruta, factores y avisos; gráficos del bulbo de Boussinesq, asiento acumulado y curvas de comparación.
- Comparación histórica de zapata corrida, etiquetada como **aproximada** (`L_asiento=100 m; L_hundimiento=1.000 m`).
- Descargas CSV/JSON y bloqueo de descargas tras modificar entradas sin recalcular. Ficha JSON con entradas, criterios y avisos.

### Hipótesis / restricciones técnicas importantes

1. **Predimensionamiento, no verificación completa de ELU/ELS.** Solo carga vertical centrada, base horizontal y valores B,L introducidos. No calcula las excentricidades, la distribución de presiones por momentos, fuerzas horizontales, deslizamiento, vuelco o dimensionamiento estructural.
2. El asiento es **elástico e inmediato**. No calcula consolidación primaria/secundaria, diferenciales ni interacción entre cimentaciones. El uso de capas por diferencias de soluciones homogéneas es una aproximación.
3. `Ksp30` se obtiene como **equivalencia inversa** de expresiones de balasto, no por ensayo de placa. El resultado cambia según se elija cohesivo o granular, aunque `ks,BL` permanece invariante.
4. La regla `literal_cte` conserva un salto al pasar de B=L a B<L; la regla `continuo` evita matemáticamente el salto normalizando E.8 respecto a 1,5 en B=L, pero **no es aplicación literal del CTE**.
5. `gamma_sub` representa peso específico **sumergido**, no peso saturado. En la versión reconstruida su valor de ejemplo es `9 kN/m³`, mientras que en el formulario v4 público figuraba otro valor inicial; comprobar los pesos del estudio real.
6. `gamma_R` se introduce con opciones 3 y 2, según la situación escogida; debe contrastarse con el caso real, el CTE y el resto de la verificación de seguridad.
7. Los datos de ejemplo son **sintéticos**, no parámetros recomendados para ninguna obra.

## Pruebas

```bash
python -m pytest -q
```

La entrega incluye `tests/test_engine.py` y `tests/test_smoke_interfaz.py`. El segundo utiliza una **simulación de la API de Streamlit**, no un navegador real.

## Documentos

- `docs/METODO_Y_LIMITACIONES.md`: hipótesis y variables del cálculo.
- `docs/VALIDACION.md`: batería de pruebas y pruebas no ejecutadas.
- `docs/CAMBIOS.md`: relación de cambios reconstruidos.
- `ejemplos/`: entradas y resultados sintéticos de referencia.

Fuente pública utilizada como guía de alcance funcional: https://github.com/me1lopig/Exterior/tree/main/zapatasCTE
Documento normativo para cotejo: https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf

**Estado:** reconstrucción funcional verificada computacionalmente en pruebas unitarias y de interfaz simulada; **no contrastada todavía con el código original íntegro, una hoja Excel original ni una sesión real de navegador**. Revisar y firmar por técnico competente antes de uso profesional.

Licencia del código generado: GNU GPLv3 o posterior, por compatibilidad con el proyecto público de referencia.

# GeoPerfil 2D v0.8.3 - Alineacion topografica

## Corregido

1. **Terreno del PDF/PNG/SVG:** antes se obtenia solo de los sondeos, aunque PERFIL1 tuviese otras estaciones como STA y penetraciones. Ahora utiliza toda la tabla de estaciones disponible, como MiniCAD/Plotly/DXF.
2. **Posicion visible de la boca:** S-01 y los demas sondeos tienen una linea en su cota de inicio; cada penetracion cuenta con una marca de origen y un eje vertical tenue desde su PK y cota reales. La curva de golpes no se desplaza a profundidad cero ni se inventan datos.
3. **MiniCAD:** los penetrómetros dibujan sus ejes y marcas de inicio en la cota original. Se corrigió la referencia al tamaño de letra en la etiqueta de penetrómetro; el margen visible del MiniCAD incluye los extremos del terreno de PERFIL1.
4. **Control de consistencia:** con campaña PERFIL1 se detectan discrepancias de cota superiores a 1 mm entre el reconocimiento y el terreno. Nunca se alteran los datos de origen automaticamente.
5. **STA:** utilizado en el terreno, nunca representado como trabajo ni como simbolo individual.

## Pruebas

- 79 pruebas automatizadas: importacion, geometricas, MiniCAD (Chromium), modelo, exportacion DXF, persistencia y regresion v0.8.3.
- Prueba integral con PERFIL1, BKFL, DPRG, ISPT y ListadoLab originales suministrados: 6 puntos de terreno, 1 sondeo y 4 penetraciones. Las cinco cotas de inicio son 0.00 m. Se verifico que todas coinciden con el terreno, pero que las primeras lecturas de penetracion mantienen su profundidad.
- Generados PDF y PNG, y se releyo el DXF con ezdxf; se verifico tambien la representacion MiniCAD en navegador.

## Pendientes de validacion

- No se ha ejecutado una sesion completa de Streamlit en macOS.
- No se ha comprobado la apertura del DXF en AutoCAD ni la escala fisica de impresion.
- Los limites de la correlacion geologica y los datos medidos deben revisarse por tecnico competente.

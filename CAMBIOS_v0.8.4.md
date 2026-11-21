# GeoPerfil 2D v0.8.4 - curvas de penetracion y captura de bordes

## Cambios funcionales

1. **Penetraciones DPRG**: los PK y las cotas de inicio se conservan exactamente. Las lecturas siguen a la cota `cota_inicio_m - profundidad_m` y mantienen sus golpes originales. Se calcula una **escala horizontal grafica comun y segura**, limitada por las mitades de las distancias a los reconocimientos vecinos y por los PK inicial y final. Las curvas situadas en el extremo derecho pueden crecer hacia la izquierda para no quedar fuera del perfil. Esta escala auxiliar no es una coordenada medida ni modifica el ensayo.
2. **Unificacion de la escala** en el perfil Plotly, MiniCAD, PNG/SVG/PDF y DXF: todos usan la misma regla de presentacion en el mismo tramo PK. Los valores N20 y la cota de cada lectura permanecen accesibles y exactos.
3. **MiniCAD: ajuste a cuatro contornos reales**: superficie topografica, lados izquierdo/derecho y base grafica. Se priorizan primero las interfaces observadas de sondeos y luego los vertices exactos del borde. El ajuste usa pixeles reales y se mantiene con zoom. Los vertices nuevos no pueden quedar fuera del dominio; `Alt` omite la captura magnetica pero no permite salirse del dominio.
4. **Guias visuales de bordes** solo durante el dibujo de contactos/lentes; las guias no se guardan como datos ni se exportan. Los puntos capturados en los bordes conservan origen `interpretado`, sin atribuirles evidencia observada.
5. **Validacion en Python**: se rechazan contactos que cruzan el terreno, el limite inferior o las caras laterales; no basta un control en el navegador. El fondo del dominio se calcula de modo coherente para editor y polygonizador e incluye penetraciones profundas y cotas topograficas bajas.
6. **STA** continua definiendo el terreno sin representarse como reconocimiento; la importacion se mantiene exclusivamente multifichero. No se han incorporado nuevas herramientas CAD.

## Pruebas

- 88 pruebas automatizadas: 79 heredadas + 5 pruebas geologico-exportacion + 4 pruebas de MiniCAD Chromium.
- Validado con los cinco archivos Excel suministrados: 1 sondeo, 4 penetraciones (218 lecturas), 6 SPT, 6 puntos de terreno incluyendo STA.
- Verificados los PK/cotas y limites de curvas en Plotly y DXF; generado PNG y PDF de comprobacion.

## Limitaciones

- La escala grafica efectiva de N20 puede ser mas pequena que la solicitada y las curvas en un extremo pueden representarse hacia la izquierda. Esto afecta solo a su disposicion en la hoja, no a datos medidos.
- Al editar las curvas o contactos no deben tratarse los desplazamientos horizontales de N20 como distancias reales.
- Topografia entre puntos de PERFIL1 linealmente interpolada.
- Falta la prueba de uso completo en Streamlit sobre Mac y apertura en AutoCAD u otros visores CAD de escritorio. Las pruebas del navegador se hicieron sobre MiniCAD embebido en Chromium.

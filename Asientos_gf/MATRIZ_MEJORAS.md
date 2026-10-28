# Matriz de las 24 mejoras

| N | Mejora aplicada | Implementacion / verificacion |
|---:|---|---|
| 1 | Consolidacion solo en cohesivos saturados | Filtrado por tipo y estado hidraulico; prueba de arcilla no saturada. |
| 2 | Nivel freatico en superficie | `zw=0` es valido y distinto de "Sin agua"; prueba de regresion. |
| 3 | Continuidad al prolongar el ultimo estrato | Integracion por fronteras de capa e hidraulicas; prueba a ambos lados del nivel. |
| 4 | Eliminacion del factor rigido 0,85 | Matriz de influencia, compatibilidad de plano y equilibrio N-Mx-My. |
| 5 | Consolidacion temporal por estrato | Cada unidad conserva `cv`, drenaje, `Hdr`, `U(t)` y `t95`. |
| 6 | Estado de carga sincronizado | Controles Streamlit tipados; no existe un estado oculto N/q independiente. |
| 7 | Circulo real | Solucion analitica en el eje y cuadratura polar fuera de el; sin "esquina" circular. |
| 8 | Motor unificado de tensiones | `PressureField` integra el nucleo de Boussinesq para presion uniforme, lineal o discretizada. |
| 9 | Excentricidad y momentos | Ley N-Mx-My; si aparece traccion se resuelve contacto parcial no negativo. |
| 10 | Asiento elastico 3D | Diferencias de desplazamiento de Boussinesq con E y nu; alternativa 1D identificada. |
| 11 | Descarga | Los incrementos netos negativos se conservan y pueden producir levantamiento. |
| 12 | Bulbo no alcanzado | Busqueda ampliable hasta `factor x B` y advertencia explicita de truncamiento. |
| 13 | Validacion fisica | Control de finitud, signos, dominios, dimensiones, modulos y parametros de consolidacion. |
| 14 | Zapata, losa y pozo separados | Zapata/losa identificadas; losa usa limites flexible/rigido. Pozo se bloquea hasta disponer de transferencia fuste-base. |
| 15 | Modelo hidraulico ampliado | Nivel horizontal, ausencia de agua o perfil piezometrico `u(z)` interpolado por puntos. |
| 16 | Preconsolidacion inconsistente | `sigma'pc < sigma'v0` genera error contextual; no se corrige silenciosamente. |
| 17 | Secundario en el tiempo | La curva incluye C-alpha desde el t95 propio y alcanza al menos la vida de servicio. |
| 18 | Sin parametros temporales ocultos | No hay minimo artificial de 0,02 anos ni `cv` equivalente global. |
| 19 | Cumplimiento correctamente rotulado | Indica "limite introducido por el usuario" y excluye una validacion normativa implicita. |
| 20 | Arquitectura modular | Interfaz, modelos, calculos, servicios, visualizacion, utiles y pruebas separados. |
| 21 | Pruebas automaticas | 16 pruebas de formulas, casos limite, agua, rigidez, consolidacion, descarga y exportacion. |
| 22 | Exportacion robusta | CSV con `Blob` nativo de Streamlit, paquete ZIP trazable y neutralizacion de formulas. |
| 23 | Eliminacion de XSS | Los datos se renderizan mediante componentes Streamlit; no se insertan nombres con `innerHTML`. |
| 24 | Accesibilidad y semantica | H1 real, etiquetas nativas, alertas de estado, tablas con encabezados y diseno responsive. |

## Limites deliberados

- El modo losa representa los limites flexible y rigido, no la flexion de una placa de rigidez finita.
- El pozo/caisson no se calcula con el motor superficial: se detiene con un error porque falta un modelo de fuste-base.
- La redistribucion rigida usa un semiespacio homogeneo equivalente. Con gran contraste de rigidez o respuesta dependiente del tiempo se requiere un modelo multicapa avanzado o FEM.

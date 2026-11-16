# Notas técnicas · v3.0.0

## Matriz de trazabilidad

| Función | Fuente | Implementación | Tests | Revisión profesional |
|---|---|---|---|---|
| `tensiones`, `perfil_tensiones` | Geostática hidrostática | Suma exacta por estrato de σv, u, σ'v; z≤zsondeo | `test_nf_*`, `test_tension_*` | Hipótesis hidrogeológicas pendientes |
| `punta` (granular) | DB-SE-C F.30, 5.3.4.1.2 | φ ponderado en 6D/3D, qp tope 20 MPa | `test_f30_*` | Mezcla de materiales: advertencia |
| `punta` (fino sin drenaje) | DB-SE-C F.32 | cu ponderado en 2D/2D, Np=9 | `test_f32_*` | Verificar representatividad de cu |
| `punta` (capa inferior fina) | DB-SE-C 5.11 | qp≤6(1+H/D)²cu | `test_511_*` | Datos bajo punta deben ser reconocidos |
| `fuste_y_negativo` | DB-SE-C F.31 y F.33 | Integración F31 por tramos; tope 100/120; F33 | `test_f31_*`, `test_f33_*` | Selección de modelo y escenarios |
| `crear_seccion` | DB-SE-C 5.1.2.2 y 5.3.4.1.2 | Circular, tubular hincado, H sin azuche | `test_area_*`, `test_tubular_*`, `test_perfil_*` | Configuración real de azuche y sección |
| `seleccionar_gamma` | DB-SE-C tabla 2.1 | 3,0 / 2,0; manual justificado | `test_gamma_*` | Situación y acciones del proyecto |
| RN opcional | DB-SE-C 5.2.2, (5.4) | ∫βσ'v·p dz en zona indicada, sin fuste positivo coincidente | `test_roz_negativo_*` | Verificar asientos, plano neutro y factor de acción |
| Memoria | Entradas y resultados de motor | `report.py` | `test_word_*` | Revisar visado y calidad documental |

## Hipótesis de implementación no directamente normativas

- En transición dentro de la ventana activa de punta entre formulación drenada y no drenada, se calcula el modelo del material de apoyo y se adopta el menor entre dicha resistencia y la aportada por materiales de otro tipo presentes en la ventana. Esta **cota conservadora no equivale a un método mixto oficial del CTE**. Se indica en la auditoría.
- Para la punta de hormigón `fp=2,5` se mantiene la tipología original perforado in situ; para hincado `fp=3`. En tipo de suelo granular el programa requiere modelo drenado.
- En condiciones persistentes/transitorias si la estratigrafía integra zonas a corto y largo plazo se adopta **γR=3,0**; el uso de γR=2,0 solo se aplica automáticamente si todas las unidades responden al modelo a corto plazo. Esto **no sustituye** la comprobación de situaciones de dimensionado completas.
- Para RN el factor de acción por defecto 1,0 se considera únicamente un valor de análisis; el usuario debe verificar si corresponde a la combinación del proyecto.
- El límite por capa cohesiva inferior se evalúa sobre las unidades finas que empiezan debajo de la punta y que han sido declaradas en el sondeo, sin establecer un umbral inventado de "arcilla blanda". El mínimo de (5.11) gobierna solo si reduce qp.

## No implementado en esta versión

- Cálculo de capacidad de empotramiento/apoyo en roca; entrada de roca no disponible.
- Escenarios de corto y largo plazo **calculados automáticamente** y envolvente (cambio deliberadamente fuera del alcance seleccionado).
- Combinaciones de acciones `Ed`, verificación ELU completa, asiento, grupo, cargas laterales, arrancamiento, deformaciones, variaciones de niveles freáticos.
- Cálculo geotécnico de sección tubular perforada sin desplazamiento ni tapones especiales; tubular se circunscribe a hincados metálicos.
- Validación con ensayo de carga ni aprobación técnica colegial.

## Fuentes oficiales y páginas del PDF consultadas

- Tabla 2.1, página impresa SE-C-7.
- Rozamiento negativo, páginas SE-C-46–47.
- Definiciones de geometría, página SE-C-43; punta y limitación 5.11, páginas SE-C-50–51.
- Formulación F.30, página SE-C-140; F.31–F.33, página SE-C-141.

PDF: https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf

## Interpretación de las pruebas

Pruebas unitarias independientes de la interfaz con referencias analíticas simples permiten detectar errores computacionales, **no** verificar todas las hipótesis normativas del modelo. La interfaz se ha recorrido con un doble de Streamlit cuando el paquete no estaba disponible; no se afirma prueba de navegador real en ese caso.

## Regresión respecto a formulaciones anteriores

Las pruebas `test_regresion_modelo_granular_homogeneo_sin_nf` y `test_regresion_fino_corto_homogeneo_sin_nf` contrastan la parte de F.30–F.33 conservada con soluciones manuales independientes para perfiles homogéneos. En perfiles heterogéneos, las nuevas reglas y la integración exacta por tramos **modifican legítimamente los resultados** respecto al archivo `PilotesCTE_2.py` original; la equivalencia numérica universal con la versión anterior no es un objetivo ni una garantía.

En caso de zona superficial de fuste nulo que se superponga con RN explícitamente activado, la resistencia positiva se anula, pero se sigue considerando conservadoramente la acción negativa en dicha zona, porque el usuario la declara susceptible de desplazamiento relativo descendente.

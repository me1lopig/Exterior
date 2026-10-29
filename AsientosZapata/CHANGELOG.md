# Cambios de la versión corregida

## Revisión de formulaciones clásicas

- Verificadas las expresiones de Holl y Steinbrenner frente a integración numérica independiente de Boussinesq.
- Admitido el límite `nu = 0.50` en el método clásico; el FEM mantiene la exigencia `nu < 0.50`.
- Aclarado que `Δσz ≤ 0.20·σ′v0` es un corte convencional y requiere sensibilidad a `z_max`.
- Documentados los límites del punto característico en perfiles estratificados y de la extensión multicapa del factor de Mayne-Poulos.
- Añadidas pruebas de invariancia al subdividir un medio homogéneo y de tensión efectiva con cruce del nivel freático.

- Eliminada la evaluación de distorsión angular del núcleo, la interfaz y el informe.
- Unificado el nombre importable del motor como `funciones_asientos.py`.
- Añadido resultado explícito del criterio de profundidad de influencia, con detección de perfil insuficiente.
- Bloqueado el cálculo cuando el perfil no alcanza el criterio o cuando no puede adoptarse `z_max >= z_i`.
- Separado el fondo del dominio MEF de la profundidad `z_max` mediante `factor_prof`.
- Añadida sensibilidad MEF frente a refinamiento de malla, ampliación lateral y aumento de profundidad.
- Condicionado el veredicto ELS a una sensibilidad MEF dentro de la tolerancia seleccionada.
- Eliminada la afirmación genérica de pruebas no demostradas del informe.
- Rechazado `nu = 0.50` sin sustitución silenciosa por 0.499.
- Corregida la discontinuidad del perfil flexible con empotramiento.
- Limitado el perfil Steinbrenner rígido al área de la zapata.
- Añadidas pruebas unitarias, requisitos y guía de instalación.

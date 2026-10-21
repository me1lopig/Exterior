# Cambios frente a v0.4

- Rehabilitados 2 métodos calculados de ángulo de rozamiento (FHWA), y consulta de intervalos de φ del CTE D.27.
- Rehabilitados 3 métodos E de arenas (FHWA, Kulhawy-Mayne) y 2 ramas Begemann con signo correcto, frontera N=15 sin asignar y conversión SI exacta.
- Añadida normalización explícita del SPT (N campo, N60, (N1)60; factores de ensayo y tensión efectiva). Usuario puede introducir valores corregidos ya conocidos o calcular desde N campo.
- Añadidos 2 métodos de consulta Cu a partir de qu de CTE D.3 y D.23, con la relación condicionada cu=qu/2. Se conservan las 4 relaciones bibliográficas de v0.4.
- Añadida alternativa para Eu de arcillas desde Gmax medido mediante CTE F.1.
- Ajustada la frontera N=10 de CTE D.23; etiquetas distinguen interpolación propia de tabla normativa.
- Corregido bug de arranque de v0.4: faltaba constante `K30_TABLA`. Se ha verificado contra CTE D.29.
- Conservadas las 7 pestañas, exportación CSV y las fórmulas desplegables; sin Cc, Cs, K0 ni módulo OCR.
- Revisión de advertencias: mensajes cortos de validación, fichas de condición y bibliografía; sin duplicar disclaimers.
- 64 pruebas de regresión y 2 recorridos Python simulados de interfaz con sustituto de Streamlit. **No** son pruebas visuales reales.

Los métodos no documentados o basados en variables incompatibles siguen excluidos del cálculo. Ver `AUDITORIA_CORRELACIONES_v05.md`.

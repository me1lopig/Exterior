# Estado de auditoria — v0.4

Los antecedentes historicos del Excel contenian 146 formulas y 11 pestanas. Cc, Cs, K0 y OCR se retiraron de la aplicacion en v0.3.

Tras revision bibliografica complementaria v0.4:

- **Cu**: se reemplazan las 19 salidas historicas sin autorizacion suficiente por cuatro metodos con ecuacion y dominio documentados. Ver `VALIDACION_CU_v04.md`.
- **phi' y E-arenas**: deshabilitados en interfaz y motor. Se mantienen pestanas vacias para una edicion posterior.
- **E-arcillas**: solo se habilita la tabla F.2 del CTE, bajo confirmacion de arcilla sobreconsolidada y c_u independiente.
- **E-CTE**: tabla D.23 e interpolacion del usuario entre N=10,25,50 sin presentarse como prescripcion normativa.
- **Poisson**: tabla D.24 CTE.
- **K30**: tabla D.29 y expresiones E.6-E.8 del CTE.

La version original del Excel sigue siendo referencia historica. La aplicacion v0.4 no requiere Excel para funcionar.

**No certificado para proyecto:** las pruebas unitarias comprueban que la implementacion responde a formulas documentadas y bloquea entradas invalidas, no la calidad estadistica ni la extrapolabilidad de cada correlacion a un emplazamiento concreto.

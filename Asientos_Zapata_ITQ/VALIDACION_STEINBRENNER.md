# Contraste de Steinbrenner - actualización 23/11/2026

Se contrastó el motor de asiento elástico de zapata rectangular flexible frente a cuatro referencias externas y la hoja `asientos_3.xlsx` del usuario. No se alteraron las fórmulas de Boussinesq ni de integración vertical.

## Resultados

| Referencia | Caso | Magnitud | Publicado | Calculado | Diferencia | Tolerancia |
|---|---|---|---:|---:|---:|---:|
| ministerio | E-1 | center_settlement | 13.7000 mm | 13.7555 mm | +0.0555 mm | 0.1000 mm |
| ministerio | P-1 | center_settlement | 33.9000 mm | 33.9730 mm | +0.0730 mm | 0.1000 mm |
| ministerio | P-2 | center_settlement | 2.4000 mm | 2.3878 mm | -0.0122 mm | 0.1000 mm |
| ministerio | P-3 | center_settlement | 2.3000 mm | 2.2721 mm | -0.0279 mm | 0.1000 mm |
| ministerio | E-2 | center_settlement | 9.8000 mm | 9.8174 mm | +0.0174 mm | 0.1000 mm |
| hkie | HB-1 | center_settlement | 27.8500 mm | 27.8533 mm | +0.0033 mm | 0.0200 mm |
| hkie | HB-1 | corner_settlement | 12.0800 mm | 12.0801 mm | +0.0001 mm | 0.0200 mm |
| hkie | HB-1 | area_mean_trapezoid_21x21 | 22.9000 mm | 22.8989 mm | -0.0011 mm | 0.0200 mm |
| geo | Example 5 | Clay | 64.9400 mm | 64.9390 mm | -0.0010 mm | 0.0200 mm |
| geo | Example 5 | Medium sand | 1.5600 mm | 1.5650 mm | +0.0050 mm | 0.0200 mm |
| geo | Example 5 | Silt | 9.0800 mm | 9.0774 mm | -0.0026 mm | 0.0200 mm |
| geo | Example 5 | total_characteristic_point | 75.5800 mm | 75.5815 mm | +0.0015 mm | 0.0200 mm |
| a4 | A-4 SE-20 | center | 43.0000 mm | 42.6976 mm | -0.3024 mm | 0.5000 mm |
| a4 | A-4 SE-20 | corner | 12.0000 mm | 12.4639 mm | +0.4639 mm | 0.5000 mm |
| excel | asientos_3.xlsx | center_settlement | 29.1912 mm | 29.1912 mm | +0.0000 mm | 0.0000 mm |
| excel | asientos_3.xlsx | q_at_50mm | 411.0828 kPa | 411.0828 kPa | +0.0000 kPa | 0.0000 kPa |

**Balance:** 16 casos dentro de tolerancia; 0 fuera.

Las tolerancias están adaptadas al redondeo de las publicaciones; la igualdad numérica no demuestra precisión experimental ni cumplimiento normativo global.

## Fuente y ejecución

Los datos y URL de las fuentes están en `tests/casos_referencias_publicadas.json`. Ejecutar desde `Asientos_Zapata_ITQ`:

```bash
python -m pytest -q
```

Se comprueban cinco ejemplos ministeriales, tres magnitudes del HB-1 (HKIE), cuatro cálculos de GEO Tools (capas y total), dos puntos del anejo A-4/SE-20 y dos resultados del Excel aportado.

## Alcance y límites

- Comparaciones de asentamiento **elástico** por Steinbrenner para carga centrada y presión uniforme; no asientos por consolidación ni plasticidad.
- La suma estratificada se realiza por diferencias de soluciones homogéneas; no equivale a una solución elástica multicapa de continuidad exacta.
- El modelo permite ahora `0 <= nu < 0.499`; `nu = 0` es válido en el modelo elástico, aunque no es un valor habitual de proyecto.
- No se ha realizado prueba real de navegador Streamlit en este entorno; se validó la sintaxis y el motor con pytest.
- El ejemplo del Hospital de Jerez no se incorporó como prueba automática al no haber parámetros completos y unívocos para reproducirlo.

El informe detallado fue preparado por separado. El Excel de ensayos no es parte del motor de cálculo ni se utiliza como dependencia en producción.

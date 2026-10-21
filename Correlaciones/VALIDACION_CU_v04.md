# Ficha de verificacion de correlaciones Cu — v0.4

## Alcance

Se retiraron las 19 salidas de la antigua funcion `calcular_cu`, incluidas formulaciones en kgf/cm2 sin fuente primaria suficiente y expresiones atribuidas erroneamente. En su lugar se implementan cuatro **metodos distintos**, identificados por referencia y dominio. Las tablas CTE NO hacen normativas estas relaciones empiricas.

| ID | Autor | Ecuacion con entrada en porcentaje | Condicion automatizada | Significado del resultado | Fuente |
|---|---|---|---|---|---|
| CU-01 | Skempton (1957) | `(0.11+0.0037*IP)*sigma_v_ef` | arcilla, NC, IP>0, sigma_v_ef>0 | `cu` estimada de molinete de campo sin corregir | [Revision](https://www.sciencedirect.com/science/article/pii/S1674775515000955) |
| CU-02 | Bjerrum y Simons (1960) | `0.45*sqrt(IP/100)*sigma_v_ef` | arcilla, NC, IP>50, sigma_v_ef>0 | ratio de resistencia sin drenaje NC | [Bowles 2-59](https://abrand-co.com/wp-content/uploads/2023/06/Foundation-Analysis-and-Design-Bowels.pdf) |
| CU-03 | Karlsson y Viberg (1967) | `0.005*LL*sigma_v_ef` | arcilla, NC, LL>20, sigma_v_ef>0 | ratio de resistencia sin drenaje NC | [Bowles 2-61](https://abrand-co.com/wp-content/uploads/2023/06/Foundation-Analysis-and-Design-Bowels.pdf) |
| CU-04 | Mesri (1975) | `0.22*sigma_p_ef` | arcilla blanda inorganica, sigma_p>0 y sigma_p>=sigma_v | **movilizada**, no VST | [ASCE](https://ascelibrary.org/doi/full/10.1061/%28ASCE%29GT.1943-5606.0001697) |

Para CU-02, Bowles utiliza IP como **fraccion** (>0.5), equivalente a IP en % (>50) al introducir `IP/100` bajo la raiz. Para CU-03, Bowles utiliza LL decimal >0.20: expresado en %, `0.5*(LL/100)` = `0.005*LL`. Para CU-01, la forma lineal usa PI porcentual, **no** `log10(IP)`.

### Datos de ensayo y condiciones

- Efectiva sigma'_v0 [kPa] frente a total: no intercambiables.
- sigma'_p [kPa] requiere una determinacion de consolidacion; no se infiere del SPT.
- Estado NC solicitado al usuario, nunca deducido por defecto. Si sigma'_p fue declarada y excede sigma'_v0, los metodos NC quedan bloqueados.
- LL e IP son % de masa expresados numericamente (ej. 55, no .55).
- No hay correlaciones Cu basadas en SPT habilitadas.
- Bjerrum y Karlsson poseen dispersion elevada; los valores no sustituyen ensayos especificos.

### Pruebas sintéticas independientes

Con sigma'_v0=150 kPa, IP=60 %, LL=80 %, NC, arcilla blanda inorganica, sigma'_p=150 kPa:

- Skempton: `(0.11+0.0037*60)*150 = 49.8 kPa`.
- Bjerrum-Simons: `0.45*sqrt(0.60)*150 = 52.285... kPa`.
- Karlsson-Viberg: `0.005*80*150 = 60 kPa`.
- Mesri: `0.22*150 = 33 kPa`.

La suite incluye casos negativos de IP=50, LL=20, sigma'_p ausente, OC, material no identificado, sigma'_p inconsistente, IP>LL, entradas NaN/inf/negativas y bloqueo de modulos pendientes. Los resultados sinteticos verifican aritmetica y controles, NO precision en campo ni acreditacion normativa.

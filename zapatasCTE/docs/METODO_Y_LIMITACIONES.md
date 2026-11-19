# Método geotécnico y límites

**Notación en la aplicación**

- B, L [m]: dimensiones eficaces de la base, con 0 < B <= L.
- D [m]: profundidad de apoyo desde rasante.
- q0 [kPa]: sobrecarga alrededor de la base, calculada como gamma_q0 × h_q0.
- sigma_pre [kPa]: tensión total preexistente retirada por la excavación, automática o manual.
- q_hund_bruta [MPa]: resistencia de cálculo dividida por gamma_R según el modelo.
- q_hund_neta = q_hund_bruta - sigma_pre/1000.
- q_asiento_neta = s_admisible / flexibilidad (Steinbrenner por estratos).
- q_asiento_bruta = q_asiento_neta + sigma_pre/1000.
- q_serv_neta = min(q_hund_neta, q_asiento_neta), solo si q_hund_neta > 0.
- q_serv_bruta = q_serv_neta + sigma_pre/1000.

**Hundimiento**: factores Nq = exp(pi tan(phi)) tan(pi/4 + phi/2)^2; Nc=(Nq-1)/tan(phi), N_gamma=1.5(Nq-1)tan(phi), con casos especiales para phi=0 y resistencia no drenada Nc=5,14. Factores de forma sc=1+0,2 B/L, sq=1+1,5 tan(phi) B/L, s_gamma=1-0,3 B/L. Factores de profundidad condicionados. Coeficiente de seguridad por entrada gamma_R. CTE DB-SE-C, capítulo 4 y Anejo F; comprobar ámbito y coeficientes antes de utilizar en proyecto.

**Asiento**: sumas de diferencias en desplazamiento vertical de Steinbrenner evaluadas en cada límite de capa, representando una deformación elástica lineal por estratos. Método central superposición de cuatro cuadrantes o aproximación histórica de dos esquinas. Esta simplificación no garantiza compatibilidad entre estratos con fuerte contraste de rigideces.

**Balasto**: ks,BL = q_neta/s [MN/m3] con q en MPa y s en m, E.5; conversión inversa Cohesivo por E.6, Granular por E.7, considerando E.8 para rectangulares. La formulación literal distingue exactamente B=L frente a B<L y presenta discontinuidad. La normalización opcional divide el factor E.8 entre 1,5 para recuperar continuidad; es una adaptación **no literal** que no debe presentarse como un requisito normativo.

**Bulbo**: distribución Boussinesq en semiespacio homogéneo, independiente del cálculo estratificado de asiento; profundidad activa estimada por intersección del incremento vertical y un umbral dependiente de la tensión efectiva inicial. Se muestra como diagnóstico, no como control geotécnico suficiente por sí mismo.

**Uso prohibido como único justificante**: no incorpora acciones combinadas reales, excentricidades, deslizamiento, vuelco, consolidación ni asientos diferenciales. No verifica hormigón armado. No traslada automáticamente a planos un valor de k_sp30 como si fuese resultado de placa.

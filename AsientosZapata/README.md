# 🏗️ Asientos elásticos de cimentaciones rectangulares

Herramienta Streamlit para la estimación del asiento ELÁSTICO inmediato de zapatas rectangulares mediante:

- ✅ Método analítico de Steinbrenner (integración capa a capa).
- ✅ Modelo tridimensional por Elementos Finitos (OpenSeesPy) para comparación.

Descripción: la aplicación calcula y compara asientos inmediatos (elásticos) de una cimentación superficial rectangular bajo presión neta de servicio. Genera una memoria de cálculo en formato Word (.docx) con tablas, gráficos y comprobaciones según criterios prácticos y el criterio de profundidad de influencia del Eurocódigo 7.

---

## ✨ Características principales

- 📐 Cálculo multicapa integrando propiedades (E, ν, espesor) por estrato.
- 🔍 Evaluación de la profundidad de influencia (criterio EC7: Δσz ≤ 0.20·σ'v0).
- 🌐 Modelo 3D MEF (OpenSeesPy) con hexaedros bbarBrick y cuarto de dominio para reducir coste computacional.
- 📝 Generación automática de informe Word con tablas, comparativa y bulbo de presiones.
- ⚖️ Comprobación en Estado Límite de Servicio frente a un asiento admisible configurado.

---

## ⚠️ Alcance y limitaciones

- El resultado corresponde al asiento ELÁSTICO (inmediato). No incluye consolidación primaria, fluencia ni efectos viscoelásticos.
- El MEF modela la excavación geométrica, pero no simula contacto lateral ni secuencias constructivas o estado geostático completo.
- Para ejecutar el MEF 3D es necesario disponer de OpenSeesPy; si no está disponible la aplicación ofrece la solución analítica y marca la indisponibilidad del motor FE.
- Valores de ν = 0.5 se normalizan internamente a ν = 0.499 para evitar singularidades numéricas.

---

## 🚀 Instalación rápida

Recomendado: usar un entorno virtual (venv, conda...).

```bash
python -m pip install -r requirements.txt
```

Contenido mínimo de requirements.txt (ya presente en el directorio):
- streamlit
- numpy
- pandas
- matplotlib
- openseespy
- python-docx

---

## ▶️ Ejecución

Iniciar la interfaz Streamlit:

```bash
streamlit run app_asientos_FEM_4.py
```

Comandos útiles en desarrollo:
- Ejecutar pruebas unitarias:

```bash
python -m unittest discover -s tests -v
```

---

## 🧾 Entradas (qué debe proporcionar el usuario)

- Dimensiones de la zapata: Ancho B (m) × Longitud L (m).
- Presión neta de trabajo p (kPa) — presión en servicio.
- Nivel freático NF (m) respecto a la superficie.
- Estratigrafía: tabla con filas desde la superficie indicando Descripción, Espesor (m), E (kPa), ν, Peso Esp. (kN/m³) y Peso Esp. Sat (kN/m³).
- Parámetros del MEF: tamaño de malla, factor de extensión del dominio y profundidad de corte z_max.

---

## 📤 Salidas

- Informe Word (informe_comparativo.docx) que incluye:
  - Ficha identificativa (obra, autor, referencia).
  - Estratigrafía y parámetros de cálculo.
  - Resultados Steinbrenner y MEF 3D (asiento por estrato y total).
  - Bulbo de presiones y profundidad de influencia EC7.
  - Comprobación frente a asiento admisible (ELS).
- Visualizaciones en Streamlit: tablas, métricas y gráficos.

---

## 🔬 Validación y pruebas

- El código incorpora pruebas unitarias (tests/) que cubren: normalización de ν, validación de estratigrafía, criterio de profundidad de influencia, conservación de carga en MEF y comprobaciones básicas del MEF frente a la solución analítica.
- En caso de error numérico en OpenSeesPy el motor MEF lanza una excepción controlada para evitar resultados no fiables.

---

## 🧾 Notas técnicas y buenas prácticas

- El dominio FE se construye como un cuarto aprovechando simetría, con elementos bbarBrick (8 nodos) y condiciones de contorno que impiden el desplazamiento normal en simetrías y empotran la base en z_max·factor_prof.
- Ajuste de la malla: aumente el tamaño_malla para reducir tiempo de cálculo; ver indicadores en la barra lateral sobre número de nodos/elementos.
- Compruebe siempre el equilibrio carga ↔ reacciones devuelto por el MEF; el código verifica y exige un error relativo bajo tolerancia.

---

## 📚 Referencias

- Steinbrenner / Bowles — solución analítica para asiento de zapatas (expresiones φ₁, φ₂).
- Eurocódigo 7 — criterio de profundidad de influencia (Δσz ≤ 0.20·σ'v0).
- OpenSeesPy — biblioteca de elementos finitos empleada en el modelo 3D.

---

## ✉️ Contacto / Autor

Dpto. Geotecnia — repositorio: me1lopig/Exterior · Directorio: AsientosZapata

Para dudas o sugerencias, abra una issue en el repositorio o contacte al autor indicado en la interfaz de la aplicación.

---

© 2026 — Licencia: consulte el repositorio principal para detalles de licencia.

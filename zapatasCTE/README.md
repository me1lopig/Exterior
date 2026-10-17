# 🧭 Carga admisible CTE DB SE-C — zapatasCTE

Aplicación Streamlit para calcular presiones y cargas admisibles de cimentaciones directas (zapatas aisladas y zapatas corridas) en mallas de dimensiones B × L. Integra los criterios del CTE DB SE-C con el método multicapa de Steinbrenner para el cálculo del hundimiento.

⚠️ Aviso: esta herramienta NO realiza dimensionamiento estructural, comprobaciones de deslizamiento o estabilidad global, ni usa métodos basados en SPT/CPTU u OpenSeesPy. Antes de usarla en un proyecto real, verifique la edición normativa aplicable.

---

## ✨ Características principales

- Cálculo de resistencia de hundimiento según CTE DB SE-C (ELU) y comprobación por asiento (ELS).
- Método de Steinbrenner multicapa para cimentación rígida (punto característico) con uso de E_s y ν por capa.
- Soporte de estados drenados y no drenados (perfil cu constante o cu(z)).
- Generación de tablas de presiones y cargas límite para una malla B–L.
- Comprobación opcional de una geometría dada con acciones V–H–M.

---

## 🧭 Flujo de uso

1. Definir metadatos del proyecto: nombre, tipología y cota de apoyo.
2. Introducir la estratigrafía: capas con espesor, c' (cohesión efectiva), φ' (ángulo eficaz), γ (peso unitario), E_s (Módulo elástico) y ν (coeficiente de Poisson).
3. Seleccionar el estrato representativo para el hundimiento.
4. Para condiciones no drenadas, elegir entre cu constante o un perfil tabulado cu(z). En este régimen φ' se fija a cero.
5. Definir rangos y paso de B y L, asiento admisible y profundidad de influencia.
6. Calcular la tabla de presiones y cargas límite.
7. Si es necesario, activar la comprobación de una geometría con acciones V–H–M.

---

## 📈 Resultados por cada geometría B × L

- qd (ELU): resistencia bruta de cálculo.
- qd (ELS): presión bruta limitada por asiento.
- q_adm = min(qd ELU, qd ELS): presión admisible final.
- N_adm: axil admisible descontando los pesos configurados.
- Criterio gobernante y estado de cobertura del perfil.

---

## 🪨 Asientos

El método principal es Steinbrenner multicapa para cimentaciones rígidas utilizando el punto característico. Cada capa considera su módulo elástico E_s y su coeficiente de Poisson ν. La presión neta se utiliza para el cálculo de asientos y también se presentan presiones brutas para comparar con qd.

Requisitos del perfil:
- El perfil debe cubrir de forma continua desde la base de la zapata hasta D + ZI.
- Para control adicional del modelo de hundimiento se verifica la cobertura hasta D + 1.5·B.

---

## 🛠️ Instalación

Recomendado: Python 3.11 o 3.12.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

---

## ✅ Pruebas

Ejecute el conjunto de pruebas unitarias:

```bash
python -m unittest discover -s tests -v
```

Las pruebas cubren escenarios drenados y no drenados, geometría efectiva, perfil cu(z), nivel freático, cobertura estratigráfica, sobrecarga integrada, el método de Steinbrenner y la generación de la malla de capas.

---

## 📐 Convenciones

- Longitudes y profundidades: m
- Fuerzas: kN (en zapata corrida: kN/m)
- Tensiones y resistencias: kPa
- Módulos elásticos: MPa
- Pesos unitarios: kN/m³
- Profundidades positivas desde la superficie hacia abajo
- El perfil cu(z) usa profundidades absolutas desde la superficie

---

## 📚 Referencias

- CTE DB SE-C — Cimientos: https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf

---

## 🧾 Notas finales

- Esta aplicación está pensada como herramienta de apoyo al cálculo geotécnico; cualquier resultado presentado debe revisarse y justificarse en la documentación del proyecto.


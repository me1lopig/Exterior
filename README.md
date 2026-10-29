# 🏗️ Exterior

Repositorio de herramientas geotécnicas y de cimentaciones desarrolladas en Python para análisis, diseño y visualización técnica. El conjunto agrupa aplicaciones de cálculo, validación, modelado y documentación para distintos problemas de ingeniería civil y geotecnia.

## 📌 Visión general

La estructura del repositorio está organizada en dos niveles:

- Aplicaciones principales, cada una enfocada a un problema específico de geotecnia o cimentación.
- Módulos auxiliares y bibliotecas reutilizables (`calculos`, `modelos`, `servicios`, `visualizacion`, `utiles`, etc.) que apoyan la lógica de cálculo y la presentación de resultados.

El repositorio combina:

- Python
- Streamlit para interfaces interactivas
- NumPy, Pandas y Plotly para análisis y visualización
- OpenSeesPy para modelos elásticos 3D en algunos casos
- Exportación a Excel, Word, PDF y DXF según la aplicación

---

## 🗂️ Estructura principal del repositorio

```text
Exterior/
├── .github/                          # Configuración de automatización y workflows
├── AsientosZapata/                  # Asientos inmediatos en zapatas rectangulares
├── Asientos_Zapata_ITQ/             # Asientos de zapata rectangular flexible
├── Asientos_gf/                    # Cimentaciones rectangulares, circulares y bandas
├── ColumnasGrava/                  # Mejora de suelos con columnas de grava
├── Consolidacion/                   # Herramientas de consolidación y análisis asociados
├── Correlaciones/                   # Correlaciones geotécnicas y estimación de parámetros
├── geoperfil/                      # Perfil geológico 2D a partir de sondeos/DPSH
├── Losas/                          # Módulo/prototipo de análisis de losas
├── MMC_tensores/                   # Herramientas de cálculo tensorial / mecánica continua
├── PilotesCTE/                     # Diseño geotécnico de pilotes según CTE
├── TaludesTemporales/              # Estabilidad de taludes temporales
├── ZapatasGCOC/                    # Análisis de zapatas y cálculo geotécnico asociado
├── zapatasCTE/                    # Herramientas de cálculo orientadas a zapatas (CTE)
├── calculos/                       # Librerías de cálculo compartidas
├── componentes/                    # Componentes reutilizables de la interfaz o datos
├── ejemplos/                       # Casos de uso y ejemplos de entrada/salida
├── expansividad/                   # Módulos o análisis relacionados con expansividad
├── geoperfil/                     # Perspectiva de perfiles geológicos y representación
├── modelos/                       # Modelos de datos y entidades del proyecto
├── paginas/                       # Páginas, vistas o módulos de presentación
├── servicios/                     # Servicios de exportación, informes y utilidades
├── spt/                           # Herramientas específicas del ensayo SPT
├── tablas/                        # Tablas y catálogo de parámetros
├── tests/                         # Suite de pruebas del repositorio
├── utiles/                        # Utilidades generales del proyecto
├── visualizacion/                 # Funciones de representación gráfica
├── LICENSE                        # Licencia del proyecto
└── README.md                      # Documentación general del repositorio
```

---

## 🧩 Aplicaciones y carpetas del proyecto

### 🏠 AsientosZapata

Carpeta orientada al cálculo de asentamientos elásticos inmediatos de zapatas rectangulares.

Incluye:

- Cálculo mediante formulación de Steinbrenner multicapa
- Comprobación analítica ELS
- Modelado tridimensional elástico con OpenSeesPy
- Comparación entre enfoque clásico y FEM
- Generación de informes y análisis de resultados

Es una aplicación de referencia para evaluaciones rápidas de asentamiento en cimentaciones superficiales.

### 🧱 Asientos_Zapata_ITQ

Aplicación enfocada en zapatas rectangulares flexibles bajo condiciones multicapa.

Su contenido se centra en:

- Incrementos de tensión por Boussinesq
- Asientos elásticos por compresión vertical confinada
- Definición de perfiles estratificados
- Consideración de nivel freático y geostática
- Exportación de resultados a Word y Excel

Es una herramienta útil para análisis más detallados de cimentaciones superficiales con estratigrafía variable.

### 🏗️ Asientos_gf

Es una de las aplicaciones más completas del repositorio para cimentaciones superficiales.

Incluye soporte para:

- Zapatas rectangulares, circulares y bandas
- Carga vertical y momentos
- Base rígida o flexible
- Asiento inmediato y consolidación 1D
- Compresión secundaria
- Visualización y exportación de resultados

La estructura interna separa claramente la interfaz, el núcleo de cálculo, los modelos, la visualización y los servicios de exportación.

### 🪨 ColumnasGrava

Aplicación para la mejora del terreno mediante columnas de grava.

Se basa principalmente en:

- Método de Priebe
- Cálculo de relación de sustitución
- Determinación de parámetros equivalentes del suelo mejorado
- Evaluación del comportamiento del terreno tratado
- Generación de informes técnicos en Excel y Word

Es una herramienta orientada a diseño de soluciones de mejora de suelos con inclusión granular.

### 📊 Correlaciones

Carpeta dedicada a la estimación de parámetros geotécnicos mediante correlaciones trazables.

Incluye:

- Correlación con SPT
- Cálculos para molinete, sísmica, DMT, presiómetro y placa de carga
- Interpolación controlada y validada
- Generación de informes DOCX con fórmulas y fuentes

Su objetivo es apoyar la selección de parámetros geotécnicos a partir de ensayos de campo y bibliografía técnica.

### 🧱 PilotesCTE

Aplicación para diseño geotécnico de pilotes según el CTE DB-SE-C.

Entre sus funcionalidades destacan:

- Definición de estratigrafía del terreno
- Evaluación de tensiones total, intersticial y efectiva
- Cálculo de resistencia por punta y por fuste
- Verificación de capacidad geotécnica y estructural
- Comparación entre combinaciones de diámetro y longitud
- Generación de informe técnico en Word

Es una herramienta orientada al dimensionado y comprobación de pilotes de cimentación.

### 🏞️ TaludesTemporales

Aplicación para análisis preliminar de estabilidad de taludes temporales.

Los módulos incluidos cubren:

- Geometría del talud
- Estratigrafía multicapa
- Cálculo de estabilidad por equilibrio límite
- Búsqueda de superficies críticas
- Análisis de sensibilidad
- Visualización de resultados y perfiles del talud

Es un proyecto útil para estudios preliminares y evaluación comparativa de escenarios.

### 🧭 geoperfil

Herramienta para construir perfiles geológicos 2D a partir de sondeos.

Su funcionalidad incluye:

- Importación de sondeos e intervalos
- Definición de unidades geológicas
- Representación de ensayos DPSH
- Edición de contactos y lentejones
- Exportación a JSON, Excel, DXF y PDF

Está pensada para interpretación geológica de perfiles y apoyo a la documentación técnica de proyecto.

### 🏢 ZapatasGCOC y zapatasCTE

Estas carpetas contienen herramientas relacionadas con cálculo de zapatas y análisis geotécnico de cimentaciones superficiales.

Su uso principal es:

- Evaluación de capacidad y asentamiento de zapatas
- Revisión bajo criterios de normativa y diseño
- Procesamiento de casos específicos de zapatas en estructuras

### 🧮 Losas, MMC_tensores, spt, tablas y utilidades

Estas carpetas actúan como complementos o herramientas especializadas del repositorio:

- Losas: análisis de comportamiento de losas de cimentación o prototipos de modelado estructural
- MMC_tensores: cálculo tensorial y operaciones relacionadas con análisis continuo
- spt: utilidades asociadas a ensayos de penetración estándar
- tablas: catalogación de tablas y datos de referencia
- utiles: funciones generales para validación, cálculo y soporte

No siempre son aplicaciones autónomas, sino módulos de apoyo que alimentan otros programas del repositorio.

### 🧪 tests

La carpeta de pruebas agrupa validaciones del comportamiento principal del software.

Su finalidad es:

- Comprobar fórmulas y cálculos geotécnicos
- Verificar exportaciones e informes
- Validar procesos de cálculo y visualización
- Reducir errores en cambios funcionales

### 🧰 calculos, modelos, servicios, visualizacion, paginas, componentes

Estas carpetas representan la base arquitectónica del repositorio:

- calculos: lógica matemática y numérica
- modelos: estructuras de datos y entidades del dominio geotécnico
- servicios: exportación, informes, validación y servicios transversales
- visualizacion: gráficos y representación de resultados
- paginas: módulos y vistas de la interfaz
- componentes: elementos reutilizables de la UX y la lógica de presentación

Su organización favorece modularidad, mantenimiento y escalabilidad del código.

---

## 🚀 Ejecución rápida

Cada carpeta es una aplicación o módulo independiente. En general, el flujo recomendado es:

```bash
cd <carpeta>
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# o .venv\Scripts\activate  # Windows
pip install -r requirements.txt
streamlit run app.py
```

Algunas carpetas pueden usar nombres alternativos de archivo principal (`PilotesCTE_2.py`, `consolidacion_streamlit_3.py`, etc.), pero la lógica es la misma.

---

## 🛠️ Tecnologías predominantes

- Python 3.x
- Streamlit
- NumPy
- Pandas
- Plotly
- OpenSeesPy
- python-docx
- xlsxwriter / openpyxl
- matplotlib / kaleido
- report generation y exportación documental

---

## ✅ Resumen del repositorio

`Exterior` es un conjunto de herramientas geotécnicas y de cimentaciones diseñadas para cubrir distintos ámbitos del cálculo estructural y geotécnico, incluyendo:

- asentamientos de cimentaciones
- estabilidad de taludes
- diseño de pilotes
- mejora de suelos
- perfiles geológicos
- correlaciones de parámetros
- exportación de documentación técnica

Su carácter modular permite reutilizar lógica y escalar nuevas funcionalidades sin perder la trazabilidad del cálculo.

---

## 📄 Licencia

El proyecto incluye la licencia del repositorio en `LICENSE` y se distribuye con el marco legal definido por el mismo.

---

Desarrollado para análisis técnico, evaluación geotécnica y documentación de proyectos de cimentación y estabilidad del terreno.

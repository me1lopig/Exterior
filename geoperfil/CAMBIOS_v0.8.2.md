# GeoPerfil 2D v0.8.2 — Cambios de interfaz

1. Cabecera azul profesional con controles funcionales Nuevo, Abrir y Guardar JSON. Confirmación para las operaciones destructivas.
2. Pestañas Datos, Trazado, Perfil, Unidades, Interpretación y Exportar. Los metadatos se acceden desde Datos.
3. Controles de capas y tipografía trasladados al panel izquierdo, tanto en Perfil como en Interpretación; guardados en el proyecto.
4. Toolbar MiniCAD horizontal, con grupos y botones activos de selección y movimiento, conservando los comandos existentes y la captura magnética.
5. STA: continúa definiendo la línea del terreno, pero ya no se rotula ni dibuja como marcador independiente en la vista del trazado. Nunca es un reconocimiento ni aparece en la guitarra.
6. El MiniCAD recibe visibilidad de capas y tamaño de letra del proyecto sin alterar coordenadas. Se protege el render inicial frente a eventos resize antes de recibir modelo.
7. Test de regresión: 71 tests de la aplicación superados (incluidas pruebas opcionales Chromium disponibles en este entorno) y ensayo adicional manual de selección/movimiento/cambio de capas en Chromium.

## Limitaciones de validación

- Sin ejecución de Streamlit integrada en esta sesión: la disposición del panel lateral y cabecera requiere revisión visual en la instalación del usuario.
- Los puntos STA no se muestran individualmente, aunque permanecen en los datos internos para el cálculo topográfico.
- Sigue pendiente comprobar la experiencia en macOS y la interpretación de tramas DXF directamente en AutoCAD.

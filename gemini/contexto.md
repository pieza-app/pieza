# Pieza (extensión)

Pieza es un framework modular y abierto: piezas probadas para apps que viven en el computador de la persona (su IA, idiomas,
actualizaciones seguras, catálogo de la comunidad…). Esta extensión trae cuatro skills (en `skills/`):

- **lanzar-proyecto-open-source**: crear una app nueva desde una idea, eligiendo piezas y mostrando antes la ficha completa
  (pantallas, configuración, permisos y red); la app sale de **un** comando (`pieza.py crear`) y la IA escribe solo lo propio.
  Comando: `/pieza:crear <idea>`.
- **revisar-aportes-open-source**: revisar pull requests de la comunidad con veredicto, sin juntar nunca sin aprobación.
  Comando: `/pieza:revisar <repo o PR>`.
- **app-escritorio-multiplataforma**: una sola interfaz web con app nativa en Mac y Electron en Windows y Linux.
- **diseno-y-calidad-de-producto**: criterios de diseño UX/UI y buenas prácticas para cualquier pantalla o función.

Si la carpeta de trabajo tiene `piezas.json`, es una app hecha con Pieza: antes de escribir algo que ya podría existir, mira
`python3 <pieza>/herramientas/pieza.py catalogo`. Las equivalencias con Claude Code están en `docs/otras-ias.md` del repo.

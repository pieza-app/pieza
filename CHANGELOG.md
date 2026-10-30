# Cambios

## 0.6.1 — 2026-10-30
- **Más seguro, después de una revisión independiente:** una pieza de la comunidad mal formada ya no tumba el catálogo; una
  búsqueda de GitHub incompleta no borra nada; el veredicto se da con el commit que se leyó (`revisar <id> aprobar <commit>`);
  si cambia una pieza revisada se sigue instalando la última revisada; un rechazo es del repo; un proyecto aprobado que cambia
  su nombre o su página vuelve a «sin revisar». Una pieza solo escribe en `bin/`, `ui/`, `app/`… (nunca `.github/`, `.git/` ni
  `.claude/`) y sin enlaces. `actualizar` agrega lo que una versión nueva requiere, no actualiza sola si pide más (otra pieza,
  permisos o red) o si falta un archivo, y nunca reemplaza una pieza de la comunidad por una oficial del mismo id. Los ciclos en
  `requiere` se detectan. Las skills ya no siguen solas una versión nueva bajada del repo: muestran qué cambió y preguntan. Flujos: crear (versión 8) y revisar (versión 7).

## 0.6.0 — 2026-10-30
- **Cada pieza tiene su ícono** (`icono.svg`, 24×24, de línea): el catálogo se entiende mirando. Es obligatorio, también en
  las piezas de la comunidad, y se valida (`herramientas/icono.py`: solo formas, sin scripts ni enlaces, ≤ 8 KB).
- **Las apps hechas con Pieza aparecen solas en la página, con su ícono** y su estado: «Sin revisar» o «Aprobada por la
  comunidad ✓» (`comunidad.py proyecto <dueño/repo> aprobar|rechazar`). Las rechazadas no se muestran.
- `pieza.py iniciar` deja `"icono": "docs/favicon.svg"` en `app.json`. Flujos: crear (versión 7) y revisar (versión 6) explican
  íconos y la revisión de proyectos.

## 0.5.0 — 2026-10-30
- **Catálogo de la comunidad que crece solo:** cualquiera publica una pieza en su repo con el topic `pieza-comunidad`; un
  workflow diario la valida y la suma como «Sin revisar». Revisada, queda fijada a ese commit y a la huella de cada archivo, y
  `pieza.py agregar` la instala verificando todo. Sin revisar, solo con `--sin-revisar`. Guía en `docs/comunidad.md`.

## 0.4.0 — 2026-10-30
- Pieza funciona igual en **Gemini CLI** (extensión con las skills y los comandos `/pieza:crear` y `/pieza:revisar`) y en
  **Codex** (skills en `.agents/skills`; `pieza.py skills instalar codex` las pone al día sin borrar tu configuración local).
- Las skills traen una tabla de equivalencias entre herramientas; guía en `docs/otras-ias.md`.
- Página: preguntas frecuentes, cómo empezar con cada IA, imagen para compartir, datos estructurados y sitemap. Logo en el README.

## 0.3.0 — 2026-10-30
- Versiones con tipo de cambio (arreglo, mejora, rompe, seguridad) y compatibilidad entre piezas.
- «Pieza al día»: cada app recibe un PR semanal con lo que se actualiza solo y un issue con los pasos para lo demás.
- Plugin de Claude Code con las dos skills (crear apps y revisar aportes), públicas y sin datos personales.
- Página pública: contador de apps «hechas con Pieza» (topic de GitHub, sin telemetría), catálogo y cómo empezar; sello y logo.

## 0.2.0 — 2026-10-30
- Todo el catálogo en `pieza.json`: 2 piezas listas y 26 planeadas, cada una con cuándo recomendarla, pantallas, permisos por
  plataforma, red y lo que solo puede hacer la persona.
- `pieza.py catalogo` y `pieza.py ficha`: la app completa antes de crearla.
- El flujo para crear una app nueva vive aquí (`skills/lanzar-proyecto-open-source`, versión 2) y se actualiza solo.

## 0.1.0 — 2026-10-30
- Primera versión: piezas `nucleo` e `ia`, herramienta `pieza.py`, contrato del enchufe y catálogo.

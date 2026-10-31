# Cambios

## Sin publicar
- **El host genérico (fase 3 de «todo como si hubiéramos partido con Pieza»):** `host-mac` 0.1.0 (Swift, target propio
  `PiezaHost`) y `host-escritorio` 0.1.0 (Electron) son la app nativa que cada app repetía: ventana, puente que solo atiende el
  marco principal con la página propia, navegación solo dentro de `ui/`, `<id>://` para la interfaz y los medios (con rangos),
  config e idioma desde `app.json`, menús en el idioma elegido, la apariencia de la pieza `tema` (`NSApp.appearance` y
  `nativeTheme.themeSource`) y los scripts de `bin/` **con límite de tiempo** (hoy ninguna app lo tenía; corta también lo que
  lanzó el script), sin variables `<ID>_*` de afuera, la entrada en una carpeta temporal propia y el secreto por stdin. Las
  acciones que solo corren un script se **declaran** (en el `pieza.json` de una pieza o en `app.json` → `acciones`) y el host las
  valida y las enruta solo; las propias de cada app se registran (`Puente.registrar` / `host.acciones.registrar`), así una app
  migra de a poco. Cada README dice qué se borra en cada app.
- `pieza.py`: arma `acciones.json` (las acciones de las piezas instaladas, guardadas en `piezas.json` con la versión copiada, más
  las de `app.json`) al agregar o actualizar si la app tiene host, y con `pieza.py acciones <app>`; lo suma a la lista blanca del
  `.gitignore`. Las reglas de una acción son las mismas en `pieza.py`, en Electron y en Swift (una prueba lo compara), con los
  campos nuevos `progreso`, `requerido`, `recortar`, `extensiones` y `de`.
- Pruebas: `pruebas/host_escritorio.mjs` (Node, con un Electron falso y Python de verdad: guardas del puente, datos, límite de
  tiempo que corta a los hijos, secreto, protocolo con rangos), `pruebas/host_escritorio_electron.mjs` (Electron de verdad con
  Xvfb, si `ELECTRON` apunta a uno) y `pruebas/swift/revisar_host_mac.sh` (en un Mac: compila la pieza y la prueba sin ventana).
- **Piezas de interfaz 0.2 con lo que encontraron las apps al migrar** (Graba, Repasa, Minuta, Corta, Esquema y Alcancía):
  `componentes` 0.2.0 (seguridad: `confirmar({peligro})` enfoca «Cancelar»; el error ya no sale gris en un diálogo; el foco va al
  título y se queda donde estaba al repintar; `envolver` para un diálogo de la app; avisos con botón; un solo botón principal en
  «Tu IA», con `detalle` y «Revisar de nuevo»; `--pz-boton-alto` y `--pz-tactil`), `tema` 0.2.0 (`<html data-pz-modo>` en vez de
  `data-tema`, sombra que ya no queda en «none», `--sobre-rojo` y `--sobre-texto`, `pieza.py agregar tema … --sin-config=tema`),
  `host-ui` 0.2.0 (`responder` con objetos y aviso si la app reasigna `window.<App>`), `bienvenida` 0.3.0 (botones `pz-`),
  `i18n` 0.3.0 (placeholder de textarea y `noTraducirAtributos`) y `actualizaciones` 0.3.0 (`desarrollo`). Cada README dice qué
  cambia para una app que ya las usa («Si venías de…»).
- **6 piezas de datos listas (fase 2 de «todo como si hubiéramos partido con Pieza»):** `catalogo` 0.1.0 (contenido de la
  comunidad: dominio fijo, sin redirecciones, tope de tamaño, SHA-256 obligatorio y el id buscado solo en el último índice
  validado; el validador lo pone cada app; Python, Swift y Electron), `red` 0.1.0 (HTTPS solo a dominios permitidos, sin
  redirecciones, con tope de tamaño y de tiempo), `cifrado` 0.1.0 (PBKDF2 600.000 + AES-256-GCM con AAD, nombres opacos,
  verificador de frase y archivos con versión; abre lo que ya guardaron Repasa y Alcancía), `transcribir` 0.1.0 (whisper con
  modelos de huella fija, vocabulario en un archivo privado que se borra, también con `whisper-cli`; VAD y filtro de inventos y
  bucles), `trabajos` 0.1.0 (trabajos largos con estado en disco, latido, «Detener», preguntas, y los lectores de progreso de
  Swift y Electron) y `contenido` 0.1.0 (md, txt, pdf, docx, odt, epub y html con topes contra zip bombas y XML sin entidades).
  Cada README dice qué cambia en cada app al pasarse.
- `ia` 0.6.0: `preguntar_vivo` (lo que lee la IA en vivo y «Detener») con el mismo armado del comando que `ejecutar`, y sin el
  aviso «Permission deny rule "MultiEdit" matches no known tool» de Claude Code 2.1 (sin dejar de prohibir lo que sí conoce).
- Pruebas: `pruebas/test_piezas_datos.py` (servidor falso, whisper falso, CLIs falsos que exigen las protecciones) y más casos
  en `piezas_js.mjs` (cifrado y catálogo de Electron contra un servidor local).
- **3 piezas de interfaz listas (fase 1 de «todo como si hubiéramos partido con Pieza»):** `host-ui` (el puente
  `host.enviar` / `window.<App>.*` con un solo `crearHost`, y `probarIA {ia}` en todas las apps), `tema` (un solo juego de nombres
  de colores, cada color escrito una vez con `light-dark()`, y el selector «Apariencia») y `componentes` (diálogo que no deja
  escapar el foco y lo devuelve al cerrar, confirmar, avisos en cola, «Tu IA», actualizaciones paso a paso, «Acerca de» y
  comentarios a GitHub). Cada README trae los pasos para pasar cada app, y el de `tema` la tabla de nombres viejos → nuevos.
- Las pruebas suman un navegador de verdad (`pruebas/interfaz.mjs`, Chromium con Playwright): CSP de las apps, foco, Esc, tema,
  contraste AA en claro y oscuro (también los colores de cada app) y celular a 390 px.
- `tema` ya no depende de `componentes` (al revés: `componentes` requiere `i18n` y `tema`).

## 0.8.0 — 2026-10-30
- **Las seis apps usan Pieza:** Graba, Repasa, Minuta, Alcancía y Corta se suman a Esquema (cada una con `nucleo` e `ia`, y casi todas
  con `i18n`). Al migrarlas se cerraron huecos: los hosts que probaban la IA lanzándola directo, sin protecciones, ahora usan
  `ia.py probar`; el vocabulario del transcriptor va en un archivo privado y no en los argumentos.
- **Lo que pidió Corta:** `nucleo` 0.7.0 (texto de config con `patron`, que calza entero) e `ia` 0.5.0 (`"ia": {"ayuda": …}` en
  `app.json` suma la frase de la app a los errores sin copiar la tabla; la lista de IA instaladas sale de `ia.py lista`). El flujo
  de crear (versión 10) pide `set -eo pipefail` en las pruebas de la app.
- **Lo que pidieron Repasa y Minuta al migrar:** `nucleo` 0.6.0 (carpeta visible recién creada en 0700, `<ID>_CARPETA` para las
  pruebas, `"privado": true` para dejar todo en 0600 y `"datos": {"carpeta": "~/…"}` para una carpeta propia), `ia` 0.4.0 (frases
  de error sin nombrar menús, «no respondió» sin detalle con su propia frase, variables de la app quitadas sin importar mayúsculas)
  e `i18n` 0.2.0 (marcadores repetidos en orden). `pieza.py iniciar --datos=visible` y sin `tema` por defecto.
- **Lo que aprendimos al migrar Graba:** `ia` 0.3.0 (seguridad): los errores traen `plantilla` para que la interfaz los traduzca
  sin copiar la tabla, un CLI sin las protecciones obligatorias pide actualizarse en vez de fallar raro, `--help` sin las variables
  de la app y Claude con `--tools` si lo conoce. `nucleo` 0.4.0: textos de config con su propio máximo y `guardar_config` conserva
  lo que no conoce. `pieza.py` respeta la sangría de los JSON de la app.
- `actualizaciones` 0.2.0: una sola forma para la interfaz. Lo que la app manda en su estado (`disponible`) trae `texto` y
  `valores` igual que la respuesta de «buscar»; Electron suma `aviso(paso, codigo)` como Mac y Mac deja ver
  `Actualizaciones.version`. Esquema ya usa `bienvenida` y `actualizaciones`.

## 0.7.0 — 2026-10-30
- **Portada en 3D:** piezas con volumen dibujadas con WebGL propio (sin librerías) y una terminal que las enchufa una a una;
  sin WebGL, con movimiento reducido o en equipos lentos, el rompecabezas de siempre.
- **5 piezas listas:** `i18n`, `bienvenida` y `actualizaciones` se suman a `nucleo` e `ia`. **Esquema es la primera app que usa
  Pieza de verdad** (`nucleo`, `ia` e `i18n`); lo que aprendimos al migrarla ya está en las piezas (`i18n` 0.1.1, `nucleo` 0.3.0,
  `bienvenida` 0.2.0) y en `pieza.py iniciar` (`--plataformas`, `.gitignore` de lista blanca).
- **Piezas MPL-2.0:** si mejoras una pieza, compartes la mejora; tu app elige su propia licencia. Las herramientas siguen AGPL-3.0.
  Cada pieza dice su `licencia` y las oficiales traen el aviso de la MPL en cada archivo de código.
- **«Pieza al día» más segura:** ejecuta una versión fija de `pieza.py` (la sube la app a mano), lee las piezas nuevas solo como
  datos, calcula y prueba en un job sin permisos de escritura y el PR trae el resultado de las pruebas de la app. No pisa una rama
  que una persona tocó.
- `ia` 0.2.0 y `nucleo` 0.2.0 (seguridad): la IA corre siempre en una carpeta temporal (la carpeta que revisa ya no le carga su
  configuración ni sus hooks) y otra app ya no puede hacerse pasar por la tuya con su variable `<ID>_RECURSOS`.
- `pieza.py`: archivos de una pieza solo para algunas plataformas (`solo`), avisa los archivos que ya no son de la pieza, amplía las
  listas de `config`, crea `ui/idiomas/en.json` si falta, `diferencias` con piezas de la comunidad; `iniciar` solo sugiere el plugin.
- Las skills **app-escritorio-multiplataforma** y **diseno-y-calidad-de-producto** vienen con Pieza (antes el flujo de crear las pedía
  sin traerlas). El flujo de crear ya no enseña a automatizar github.com con la sesión de la persona (versión 9).
- Página: «framework modular» (arma tu app por módulos, como un rompecabezas), aviso honesto de «en construcción», rompecabezas
  que se arma sin saltos.
- **Pieza `i18n` 0.1.0 (lista):** `T`, `Tp`, `Thtml`, `tr` y `traducirDOM` de las apps en un solo archivo; valida las traducciones que vienen de afuera (solo texto, mismos marcadores) y escapa también los valores.
- **Pieza `bienvenida` 0.1.0 (lista):** el idioma siempre primero (bilingüe, teclas 1/2, el del sistema sugerido) y pasos que suma cada app o pieza.
- **Pieza `actualizaciones` 0.1.0 (lista):** Mac y Windows/Linux, solo desde los Releases del propio repo, `.sha256` obligatorio y nada de la app adentro.

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

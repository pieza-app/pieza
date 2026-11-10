# Cambios

## Sin publicar
- **Todo en Rust (empieza).** Pieza y sus apps son Rust + Tauri: las piezas, la lógica de Pieza y las apps que crea van a Rust,
  una fase a la vez (plan en `docs/rust.md`). **`ia` 0.8.0 (mejora)** es la primera: `tauri/ia.rs` con las mismas protecciones
  que `ia.py` (carpeta temporal, sin MCP ni memoria, el pedido por la entrada estándar, sin las variables de la app), en vivo
  (lee, busca, escribe, tokens) y con `detener`. Se prueba con CLIs falsos en `pruebas/tauri` (`cargo test`).
  **`red` 0.3.0** (`tauri/red.rs`: solo https a sus dominios, sin redirecciones, topes, subidas por partes; probada con un servidor
  falso) y **`trabajos` 0.3.0** (`tauri/trabajos.rs`: el mismo formato en disco, latido, detener, esperar y seguir; los eventos
  van directo a la interfaz) completan la fase 1. **`host-tauri` 0.2.0** abre la fase 2: una acción de `app.json` puede ser
  una función Rust (`"rust": true` + `host.funcion`) por el mismo camino que un script (validar, inyectar, fila, límite, eco).
  **`contrato` 0.1.4** revisa que cada acción en Rust esté registrada en `escritorio/src`.
- **`tema` 0.4.0 y `componentes` 0.4.0 (mejora): el estilo de Pieza para toda la familia.** Neutros cálidos, radios de 14 px,
  títulos firmes y una barra lateral oscura (tokens `--barra-lateral*`). `componentes` suma el marco (`.pz-marco`, `.pz-lateral`,
  `.pz-contenido`), `.pz-tarjeta`, `.pz-cifras`, `.pz-oscuro`, `.pz-etapas` y `.pz-dos-columnas`. Cada app pone solo su acento.
  **`pagina` 0.1.4** copia el `tema.css` nuevo.
- **`componentes` 0.3.1 (arreglo):** la ventana ya no parpadea mientras se descarga una actualización.
- **`actualizaciones` 0.5.2 (arreglo):** en Mac, si la app se abrió desde Descargas sin moverla, pide moverla a Aplicaciones en vez de fallar al actualizar.
- **`ia` 0.7.2 (mejora):** `preguntar_vivo` cuenta los tokens reales que la IA dice haber usado (`{"t": "uso", "entrada", "cache", "salida"}`).
- **`host-tauri` 0.1.3, `actualizaciones` 0.5.1 y `catalogo` 0.3.1 (arreglo):** ureq 3, sha2 0.11 y opener 0.9 (#27). `rfd` queda en 0.15.
- **`ia` 0.7.1 (mejora):** `preguntar_vivo(..., escribir=carpeta)` cuenta en vivo los archivos que la IA cambia (`{"t": "escribe"}`).
- **`actualizaciones` 0.5.0 (mejora): versiones firmadas con Ed25519 en Rust** (rehace #13). Con llaves en `app.json`, la
  app no instala nada sin una firma válida de la llave privada, que vive fuera de GitHub. `llave.sh` crea las llaves.
  **`host-tauri` 0.1.2** suma las dependencias para verificar y **`empaquetado` 0.2.2** firma en `publicar.yml`.
- **`ia` 0.7.0 (mejora): escribir en una carpeta.** `preguntar(..., escribir=carpeta)` deja que Claude o Codex editen archivos solo
  ahí, sin terminal ni internet. Sale de la prueba real del programa Pieza.
- **El catálogo en inglés:** cada `pieza.json` trae `en: {nombre, descripcion}`. La página de Pieza y el programa los
  muestran en inglés. Una prueba revisa que ninguna pieza quede sin inglés.
- **Pieza nueva `universos` 0.1.0:** mundos que cambian los colores (un tema de «tema») y los textos que la app deja cambiar.
  Solo datos, validados igual en Python (`bin/universo_formato.py`, también validador del catálogo) y JS (`ui/universos.js`).
  Trae tres universos originales: Espacio (vidrio), Bosque (claro) y Neón (oscuro). Los de la comunidad llegan por «catalogo».
- **`tema` 0.3.0 (mejora): tema «Vidrio».** Sigue al sistema (claro u oscuro), con luces de color detrás y paneles
  esmerilados. Con «reducir transparencia», los paneles quedan sólidos. Nuevo `tema.registrar({id, nombre, base, colores})`
  para temas de afuera (universos, comunidad): solo `#rrggbb` de los tokens conocidos. `config.tema` suma `vidrio`.
- **`pagina` 0.1.3 (mejora):** `docs/tema.css` al día con `tema` 0.3.0.
- **Página de Pieza en vidrio:** tarjetas esmeriladas, luces de color y barra flotante. El programa ya crea apps.
- **`github` 0.3.1 y `esqueleto` 0.2.1 (arreglo):** el `AGENTS.md` y `ui/app.js` que genera `pieza.py crear` describen la app de
  `host-tauri`. Antes hablaban de `app/` (Swift) y de Electron. `crear` ya no pide un ícono `.icns` en `app/`.
- **El programa Pieza:** el plan está en `docs/programa.md`. La app vive en `pieza-app/estudio`.
- **`host-tauri` 0.1.1 (arreglo):** `arranque.sh` resuelve la ruta del ejecutable antes del `cd`. Con eso, «Publicar versión»
  vuelve a probar la app de Linux (fallaba en Esquema 0.3.0).
- **`github` 0.3.0 (mejora):** la wiki se escribe en `docs/wiki/` y `wiki.yml` la publica sola en cada cambio. Llegan cinco
  páginas de partida. Pieza ya tiene su wiki. El README de Pieza está en STE (frases cortas, una idea cada una).
- **`github` 0.2.1 (arreglo):** en las apps, Dependabot solo abre PR de seguridad para los crates. Las versiones nuevas
  suben en Pieza (`pruebas/tauri`, con sus pruebas) y llegan con «Pieza al día». Se ignora `glib` hasta que Tauri use gtk4.
- **`empaquetado` 0.2.1 (arreglo):** `publicar.yml` instala Playwright antes de las pruebas rápidas. Sin eso, `correr.sh`
  fallaba en la interfaz y la versión no se publicaba (Alcancía, Esquema y Repasa, al pasar a `host-tauri`).
- **Pieza nueva `host-tauri` 0.1.0: un solo host para Mac, Windows y Linux** (Rust + Tauri). La misma API que `host-mac` y
  `host-escritorio`, que quedan **retirados** (`"estado": "retirada"`, con `reemplazo`): siguen para las apps que aún no se pasan,
  pero ninguna app nueva los usa y el creador ya no los ofrece. Apps mucho más livianas (el WebView del sistema en vez de un Chromium
  en cada app) y un compilador estricto en la capa con más riesgo (el puente, los permisos, los procesos). Las reglas de una acción
  (`enchufe.rs`) se comparan con `pieza.py` compiladas de verdad; `pruebas/tauri/arranque.sh` abre una app de prueba con Xvfb y
  revisa el puente de punta a punta (plataforma, estado, una acción declarada, una propia y un medio con la CSP de las apps).
- **`host-ui` 0.3.0:** `host.medio(nombre, ruta)` y `host.base`: con `host-tauri` los medios viven en el mismo origen que la
  interfaz (sin CORS); la interfaz habla con `host-tauri` por el mismo `window.<id>Escritorio`.
- **`catalogo` 0.3.0,** **`trabajos` 0.2.2 y `actualizaciones` 0.4.0:** su parte en Rust para `host-tauri`. Campo nuevo `solo_con` en `pieza.json`: un
  archivo llega solo con el host que lo usa (el Swift con `host-mac`, el JS con `host-escritorio`, el Rust con `host-tauri`), y
  llega solo cuando ese host se agrega después.
- **`empaquetado` 0.2.0 (rompe):** todo con Tauri. `herramientas/empaquetar.sh <mac|windows|linux>` arma los mismos archivos de
  siempre (`<Base>-macOS.zip`, `-Windows.exe`, `-Linux.AppImage`, `-Linux.tar.gz`, `-Linux.deb`, con su `.sha256`), así
  `instalar.sh`, `instalar.ps1` y el actualizador no cambian; `preparar.sh` arma también el Python del Mac; `publicar.yml` compila
  en macos-15, windows-2025 y ubuntu-24.04. Ya no genera `Info.plist`/`Package.swift` de Swift ni `package.json`/NSIS de Electron.
- **`esqueleto` 0.2.0, `github` 0.2.0, `contrato`, `pagina`:** la app nueva nace con `host-tauri` (su `main.rs`), `.gitignore` y
  Dependabot para Rust, el contrato revisa lo registrado en Rust y la página cuenta el llavero de Windows y Linux.
- **Pieza nueva `mcp` 0.1.0: conversa con tus datos desde tu IA** (sale de Alcancía). Un servidor MCP local por stdio, sin puertos ni internet, que cada app arma con **las herramientas que declara** en sus módulos de `bin/` (`app.json` → `mcp.modulos`; `bin/mcp_herramientas.py` se escribe una vez con un ejemplo y desde ahí es de la app). Habla **las dos formas del protocolo**: la de siempre con `initialize` (2025-11-25 y antes, la que usan hoy Claude Desktop, Claude Code, Codex y Gemini CLI) y la nueva sin estado de 2026-07-28 (`server/discover`, la versión en `_meta`, `resultType`, `ttlMs`/`cacheScope`, `UnsupportedProtocolVersion` -32022). **Solo lectura por defecto**: una herramienta con `escribe=True` no existe para la IA hasta que la persona activa «Permitir que mi IA cambie cosas» (`mcp_escribir`). Valida cada argumento contra su esquema, rechaza pedidos de más de 1 MB y respuestas de más de 512 KB, corta a las 120 llamadas por minuto, manda a stderr lo que imprima una herramienta y anota cada llamada sin sus argumentos (`mcp-actividad.jsonl`). `mcp_conectar.py` (acciones declaradas `mcpEstado`, `mcpConectar`, `mcpReparar`) la conecta y la quita en Claude Desktop, Claude Code, ChatGPT/Codex, Gemini CLI y Antigravity con el comando de cada IA o editando solo su entrada, con respaldo y escritura atómica; un archivo roto no se toca y quitar ya no crea archivos. `ui/mcp.js` trae la sección «Conectar a tu IA» de Ajustes (qué puede leer y cambiar, lo último que consultó y la frase de privacidad). Instrucciones para conectarla a mano y para pasar Alcancía en `piezas/mcp/README.md`.
- **`host-ios` 0.1.1:** la app de iPhone usa su ícono (`AppIcon` en `movil/ios/Fuentes/Assets.xcassets`).
- **`pagina` 0.1.1:** la imagen para compartir ya no corta la intro a mitad de palabra (sale de Despeja).
- **Pieza nueva `host-ios` 0.1.0: la app de iPhone** (sale de `host-mac` 0.3.0, para Despeja). La misma interfaz de `ui/` en un
  WKWebView a pantalla completa con `host.plataforma === "movil"`, el puente con las mismas guardas (solo el marco principal con un
  archivo de `ui/`, navegación solo dentro de `ui/`, https a Safari), `Config`/`Idioma` con las reglas de `nucleo`, datos en
  Application Support con protección de archivos, `ocupar()`/`soltar()` que mantienen la pantalla encendida y piden tiempo en
  segundo plano, y el proyecto de Xcode **generado** (`movil/ios/App.xcodeproj` con el grupo `Fuentes/` sincronizado, `recursos.sh`
  que copia `app.json` y `ui/`, `Info.plist` con los permisos de `app.json → ios.permisos` y `ios.bonjour`). Sin Python en el iPhone:
  una acción que nadie atiende responde `error` con `codigo: "falta"`. `pieza.py crear` ya acepta `ios` junto a una plataforma de
  computador (Android sigue esperando a `host-movil`). En un Mac: `pruebas/swift/revisar_host_ios.sh` (tipos con el SDK de iOS) y
  `pruebas/swift/compilar_app_ios.sh` (crea una app ficticia con iPhone y la compila para el simulador). `contrato` 0.1.2 revisa
  también la app de iPhone (`movil/ios/Fuentes`).
- **Revisión de seguridad de las plantillas y de `pieza.py` (antes de publicar):** el filtro `json` también deja `<`, `>`, `&`,
  U+2028 y U+2029 como `\u…` (un texto de `docs/pagina.json` ya no puede cerrar el `<script type="application/ld+json">` de la
  página); filtro nuevo `color` (solo `#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb()`/`hsl()` con números) para el acento de `colores.css`;
  un valor insertado desde `app.json` o los datos nunca puede traer `${{`, `{{` ni `}}` (no se vuelve una expresión de Actions en
  un workflow generado). `pieza.py` escribe lo generado, lo copiado de una pieza y sus JSON con un temporal nuevo (`mkstemp`, sin
  seguir enlaces) que reemplaza al archivo: un `x.tmp` o un `x` que sean enlaces ya no hacen escribir fuera de la app. Lo generado
  en `.claude/` (ajustes que pueden definir hooks) va al aviso de «Pieza al día» igual que `.github/`, nunca con `--automatico`.
  `publicar.yml` generado corre `pruebas/correr.sh` antes de publicar (antes buscaba un `test_python.py` que una app nueva no
  tiene). `empaquetado` ya no pide «permitir que Actions cree Releases» (se contradecía con `repo configurar`). El flujo 12 corre
  `repo configurar` primero sin `--aplicar` y lo aplica con el sí de la persona, y vuelve a decir «si no sale a ninguna red,
  decirlo», comentarios desde la app nunca obligatorios ni sugeridos y el texto sobre el acento por contraste WCAG.
- **`pieza.py crear`: una app nueva andando de una vez** (`crear <carpeta> --id … --nombre … --plataformas mac,windows,linux
  [--piezas ia,…] [--repo dueño/repo]`): `iniciar` + las piezas de siempre para esas plataformas + las pedidas + la pieza nueva
  **`esqueleto` 0.1.0** (lo propio mínimo, escrito una vez y desde ahí de la app: `ui/` con bienvenida e idioma primero, una pantalla
  y un script de ejemplo con su acción declarada, `<Nombre>App.swift` con `Host.arrancar`, `escritorio/src/main.js` con `crearHost`,
  `ui/demo.json`, `pruebas/correr.sh`, `test_app.py`, `interfaz.mjs`, `contrato_app.py` vacío y `README.md`) + `github`, la acción de
  ejemplo, `acciones.json` y todo lo generado (empaquetado, workflows, guías, página). Al final dice qué le toca a la IA (cada archivo
  con sus `La app:`) y qué a la persona. La app creada pasa de una su `bash pruebas/correr.sh` (contrato, Python, la interfaz y la
  página en Chromium, privacidad) con `pieza.py estado` limpio; `pruebas/test_crear.py` lo prueba con dos apps (Receta: Mac, Windows y
  Linux con «ia»; Nota: solo Mac, sin IA) y, con `ELECTRON`, abre la de Linux de verdad (`crear_electron.mjs`). **Medido** (README de
  `esqueleto`): Pieza pone 10.875 líneas en Receta y 8.154 en Nota; lo marcado para la IA son 49 y 46 líneas `La app:` más reemplazar
  el esqueleto (475 y 441 líneas). En Esquema se escribieron a mano 264 líneas de `correr.sh` + `contrato.py`, 535 de `.github/`, 666 de
  `docs/` (HTML, JS, CSS, XML), 258 de `app/` sin las piezas y 207 de `build.sh` + `empaquetar.sh` + `package.json`: aquí vienen hechas.
- **Flujo de crear (versión 12, plugin 0.9.0):** entrevista → `catalogo`/`ficha` → **un** `pieza.py crear` → la IA llena solo lo
  marcado y lo propio → `pieza.py repo configurar` → `docs/pagina.json` + `generar` → comunidad y anuncio. Sin los pasos que ya hacen
  las piezas (escribir `revisar.yml`/`publicar.yml`, `CONTRIBUTING.md`, configurar el repo y la página a mano): 193 → 128 líneas
  (18.019 → 11.651 bytes). `app-escritorio-multiplataforma` (versión 2): lo que ya es pieza es una tabla «usa la pieza» (120 → 93
  líneas). `gemini/contexto.md`, `/pieza:crear`, `docs/otras-ias.md` y la página dicen el comando nuevo.
- **`bienvenida` 0.4.1 (arreglo):** el texto de «Todo listo» lleva `data-sin-traducir` (ya sale traducido con `T`; `traducirDOM` lo
  contaba como un texto sin traducir y la prueba de una app fallaba en inglés). **`contrato` 0.1.1 (arreglo):** `probarIA` (de las
  filas de «Tu IA» de «componentes») no se exige a una app sin la pieza «ia» que no pinta esas filas.
- **Plantillas: piezas que generan archivos desde `app.json`** (`pieza.json` → `generar`, `herramientas/plantillas.py`, sección
  «Plantillas» de `docs/enchufe.md`). Solo datos (`{{x}}`, filtros que escapan o validan, `#si`/`#cada`; `${{ … }}` de Actions
  queda tal cual): nada de una pieza se ejecuta. Lo generado queda con su huella en `piezas.json` → `generados` y nunca se pisa si
  la app lo cambió; `una_vez` para lo que completa la IA de la app; `agregar`, `actualizar` y el nuevo `pieza.py generar <app>`
  lo ponen al día con todas las piezas instaladas; lo de `.github/` nunca va en el PR automático de «Pieza al día» (va al issue);
  una pieza de la comunidad no genera. `iniciar` suma `version` (0.1.0) y `repo` a `app.json`.
- **`empaquetado` 0.1.0 y `github` 0.1.0 (nuevas):** todo el empaquetado (`Info.plist`, `Package.swift`, `build.sh`,
  `empaquetar.sh` con un solo `herramientas/python.lock`, Electron, NSIS, `instalar.sh`/`.ps1`, `publicar.yml`; publicar = subir
  `version` en `app.json`) y el repo para la comunidad (issues, PR, dependabot, `revisar.yml` en ubuntu-24.04 con job `mac`,
  Pieza al día, `AGENTS.md`/`CONTRIBUTING.md`/`SECURITY.md` con lo que llena la IA marcado, agentes, privacidad, `.gitignore`,
  `LICENSE`). `pieza.py repo configurar <app> [--aplicar]`: topics con `hecho-con-pieza`, Discussions, reporte privado de fallas,
  aprobar las pruebas de quien aporta, ruleset de la rama principal y etiquetas. Prueba que la pieza reproduce el `Info.plist` de
  las seis apps y el `empaquetar.sh` de Esquema, Corta y Graba. `correr.sh` revisa también los workflows de las plantillas.
- **Pieza nueva «pagina» 0.1.0:** la página pública bilingüe de una app **generada desde `docs/pagina.json`** (lo propio: frase,
  funciones, comparación, preguntas, capturas, color) con el mecanismo de plantillas (`generar`/`datos_app`): `docs/index.html` sin
  nada en línea (CSP `script-src 'self'`), SEO (canonical, `hreflang`, Open Graph/Twitter, `sitemap.xml`; `robots.txt` y la redirección
  para `<org>.github.io`), descarga según el sistema con los nombres fijos de los Releases, demo en `/demo/`, sello «Hecho con Pieza»
  y `.github/workflows/pagina.yml` (actions por SHA, permisos mínimos). **«Permisos e internet» y las preguntas comunes** (cómo se
  actualiza, «no puede verificar la app» con los pasos de macOS 15 y Windows, dónde están mis datos, qué IA uso, permisos, costo)
  salen de lo que ya sabe Pieza (`docs/pagina-comunes.json`), según las piezas y plataformas de la app, y el **JSON-LD
  `SoftwareApplication` + `FAQPage` se arma de los mismos textos que se ven**. `herramientas/pagina_capturas.mjs`: servir como en
  Pages, capturas desde la vista previa (por datos, sin red), `compartir.png` y la revisión (es/en, 390 px, textos sin traducir,
  contraste AA, JSON-LD = lo visible), que también corre en `pruebas/pagina.mjs`.
- **Pieza nueva «contrato» 0.1.0:** `pruebas/contrato.py` común para todas las apps (antes, uno de 120–240 líneas en cada una): cada
  acción de la interfaz atendida en cada plataforma (registrada, del host o declarada) y en la vista previa, nada que sobre,
  `acciones.json` al día, las funciones de `window.<App>` y la seguridad común (CSP, IA solo por `bin/ia.py`, ATS, bundle id = firma,
  `acciones.json` en el paquete, Electron con sandbox, celular sin red ni respaldo y sus métodos nativos). Lo propio en
  `pruebas/contrato_app.py` (excepciones con motivo que avisan si sobran, patrones y `revisar`). Corrido contra las seis apps: ver su
  README (Graba y Corta pasan; Alcancía, Repasa y Esquema con 1–4 cosas a decidir; Minuta necesita su extensión y tiene 47 acciones
  sin vista previa).
- **Flujo de crear (versión 11, plugin 0.8.1):** la línea de `CONTRIBUTING.md` ya no dice que los flujos de Pieza «se instalan
  solos al abrir el repo»: con `extraKnownMarketplaces` Claude Code los **ofrece**. A propósito no se suma `enabledPlugins` a lo que
  deja `pieza.py iniciar` (activaría el plugin a quien abra el repo sin preguntarle; la prueba lo revisa). `docs/catalogo.md`: lo que
  anotaron las seis apps al pasar al host, agrupado por pieza (lo hecho y lo pendiente), y las brechas que siguen (las de la primera
  comparación ya las cerraron las migraciones; quedan los scripts largos de Minuta sin límite y la frase de `CONTRIBUTING.md`).
- **Lo que salió al pasar las seis apps al host (capacidades):** `host-mac` 0.3.0 y `host-escritorio` 0.3.0 (seguridad): un
  enlace https tocado en la ventana pasa por el `abrirEnlace` que registró la app (Repasa, para niños, no podía limitar un
  `<a href>`); `~/<Nombre>` recién creada con `"datos": "visible"` queda 0700 como en `nucleo`; «Guardar como» con `privado`
  (0600) y `guardarArchivo`, que distingue cancelar de un error o del tamaño. Variables de la app para todos los scripts, también
  los declarados (`Procesador.entornoApp` / `crearHost({entorno})`, lo de la copia de Corta; Graba y Minuta lo necesitaban), con el
  mismo filtro de nombres y sin pisar `<ID>_RECURSOS/_DATOS/_PROGRESO/_LATIDO`. En Mac: app de barra de menú (`barraDeMenu`,
  `abrirAlArrancar`, también al reabrir), `alCrearVentana`, `barraTransparente` con franja para mover la ventana, `vidrio`,
  `nombreVentana` (apps con tilde), soltar archivos (`alSoltar`, `soltado(nombre)`), `tituloAjustes` y `menuApp`, ⌘W sin menú
  Archivo, `Menus()` público, `elegirArchivos(mensaje:)`, `limiteEstado` y `estadoEnFila`. En Electron: `ventana.frame`,
  `abrirAlArrancar` (y `--oculta`), `userData: "sistema"`, `before-quit` que guarda con la ventana que se esconde, más de una
  ventana en el puente (`host.ventanas.agregar`, la respuesta va a la que pidió), `tituloAjustes`/`menuApp`,
  `dialogos.archivos({mensaje})`, `limiteEstado` y `estadoEnFila`. `bienvenida` 0.4.0: «Ajustes» configurable (`ajustes: {es, en}`),
  «Lo hago después» y botón propio en el último paso (`saltable: true`, `despues`, `fin: {texto, principal, accion}`),
  `data-autofoco` en el idioma sugerido, `detalle` por idioma y `logo`. Cada README dice qué rodeo de qué app se borra («Si venías
  de la 0.2.0» / «de 0.3.0»). **Revisar en el Mac** (Swift no compila aquí): `bash pruebas/swift/revisar_host_mac.sh` y la lista
  «Revisar a mano en el Mac (0.3.0)» del README de `host-mac` (barra de menú y Dock, barra transparente y franja, vidrio, soltar
  con `performDragOperation` en la subclase de WKWebView, enlace por `abrirEnlace`, ⌘W, `nombreVentana`, `guardarArchivo`).
- **Lo que salió al pasar las seis apps al host (arreglos y seguridad):** `catalogo` 0.2.1: un campo `archivo` o `bytes` del
  contenido ya no se quita (eran los nombres viejos de `ruta`/`tamano` y se borraban de todo objeto: ninguna plantilla de Esquema
  pasaba el validador); ahora solo se quitan en una entrada del índice y si están en vez de `ruta`/`tamano` (el arreglo de la copia
  de Esquema, con su prueba). `nucleo` 0.7.1 (seguridad): `ruta_en` con una base vacía, relativa o que no existe da `None` (antes
  `ruta_en("", "a.md")` caía en la carpeta de trabajo del script). `trabajos` 0.2.1: `mantener_vivo()` también hace que SIGTERM
  (el host al cerrar) salga con `SystemExit`, así corren los `finally` y se borran los temporales; un manejador propio de la app
  gana. `pieza.py revisar` exige que `migrar` sea una lista de pasos (el `migrar` de `catalogo` 0.2.0 era un texto y el aviso de
  «Pieza al día» salía con una viñeta por letra; también los de `cifrado`, `red` y `transcribir`), y `aviso` aguanta un texto de
  antes como un solo paso.
- **Lo que salió al pasar Esquema a `host-mac`/`host-escritorio` (0.2.0, antes de que migren las otras cinco):** `"limite":
  "trabajo"` (sin tope mientras lata: la pieza `trabajos` 0.2.0 toca `<ID>_LATIDO`; si deja de latir por 45 s, se corta) y
  límites por orden (`{"segun": "orden", "valores": {…}, "otro": …}`); `maximo` por acción (la entrada hasta 50 MB) y `vigilar`
  (`lee` / `escribe`: lo que escribe la app no se avisa como cambio de afuera, así abrir y guardar se pueden declarar); un
  inyector responde su propio texto (`Puente.Falta` / `host.falta`); el error de datos trae el eco válido; esperar a quedar
  libre también espera a los scripts que corren, y al salir se cortan los que queden (nada huérfano); en Mac, `Puente.llamar`
  sin `Bool` (`intentarLlamar` para quien lo use), `lectorProgreso` `@MainActor` y las actualizaciones atendidas por el host
  (`p.actualizaciones`, como en Electron); menú Ayuda opcional. Capacidades nuevas, iguales en los dos: la carpeta elegida (con
  marcador en Mac), el vigilante de la carpeta (FSEvents / `fs.watch`), mostrar en el Finder o el explorador, secretos (Llavero /
  `safeStorage`, que en Linux sin llavero no guarda nada) y avisos del sistema (tomados de Esquema, Alcancía, Graba y Minuta).
  `ia` 0.6.3: `probarIA` con límite 150 (con 120 se cortaba justo cuando `ia.probar` iba a responder). `pieza.py`:
  `app.json` → `"sin_acciones"` (no adoptar una acción de una pieza), y con un `piezas.json` de antes sin acciones guardadas
  las busca en el historial de git de Pieza (si no las encuentra, no arma un `acciones.json` sin ellas y dice qué correr). Cada
  README dice qué cambia «Si venías de la 0.1.0» y qué se borra en cada app; `revisar_host_mac.sh` prueba lo nuevo de Swift.
- **Lo que salió al pasar las seis apps a las piezas de datos:** `transcribir` 0.2.0: «Gracias», «Thank you» y las demás frases
  que whisper inventa ya **no se borran siempre** (en una reunión se perdía lo dicho): con la energía del audio se quitan solo si
  caen en silencio o casi; sin ella, solo si no hay nada más; los créditos («…Amara.org») siempre, como palabras completas
  («Tamara organizó» queda). Suma carpeta de modelos en `app.json`, `vad=<ruta>`, `<ID>_MODELO_PRUEBA`, `whisper_de`, `partir=`,
  `ErrorTranscribir.frase`/`como_dict()`, el transcriptor de la app primero y palabra por palabra sin VAD. `catalogo` 0.2.0
  (rompe, seguridad): el validador recibe el **objeto entero** (antes se recortaba primero y un campo de más entraba), la frase de
  error va en `frase`, última lista sin conexión, catálogo plano, carpetas e índice con otro nombre, ids con mayúsculas, `funcion`
  y `campos` configurables, `generar` sin `nucleo.py` en el repo del catálogo. `red` 0.2.0 (User-Agent en ASCII, `subir` por
  partes), `cifrado` 0.2.0 (varios sobres, `error()`, `mensajes`, `frase`), `ia` 0.6.2 (sin ResourceWarning) y `trabajos` 0.1.1.
  `pieza.py agregar` ya no deja una pieza anotada como 0.0.0 cuando un archivo ya existe: si es igual lo cuenta, si es distinto
  no copia nada, explica y ofrece `--forzar`; suma un esqueleto de la sección que la pieza pide en `app.json` (`app_json`) y las
  frases opcionales solo si la app las usa (`textos_si_usa`). Pendientes anotados en `docs/catalogo.md`: modelos en el host, pieza
  `youtube` y el dictado de Minuta.
- **Lo que salió al pasar las seis apps a las piezas de interfaz 0.2:** `pieza.py actualizar` va en orden de dependencias y
  cuenta lo que se actualiza en la misma pasada (`componentes` que necesita el `tema` nuevo ya no se niega: se actualizan las dos,
  aunque se pida solo una; `estado` y `aviso` dicen «se actualizan juntas» con el comando), acepta varias piezas y `--sin-config`,
  y `agregar … --sin-config=tema` sobre una pieza ya instalada anota la decisión en `piezas.json` y quita la clave de `app.json` si
  la app no la cambió. `componentes` 0.3.0 (rompe): `--pz-tactil` sube solo los componentes de la pieza (no el `:root` de toda la
  app), `confirmar` sin peligro enfoca el título, la fila de actualización exige `desarrollo: true`, el título de una ventana
  `aria-modal` de la app sin anillo, `.pz-cerrar` que no se achica, el cursor queda donde estaba al repintar (y
  `mantenerCampos` para un buscador), `revisable: false` en `filasIA`, `claseTitulo` y `claseCapa`. `tema` 0.2.1, `i18n` 0.3.1
  (`[data-sin-traducir]` siempre cuenta con `noTraducirAtributos`) e `ia` 0.6.1 (`probar` sin la «ayuda» de `app.json`). Cada
  README dice qué cambia («Si venías de…»).
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

# Catálogo de piezas y plan

Sale de comparar las seis apps (oct 2026): ~60 archivos repetidos, casi todos con una versión distinta por app. Cada fila dice de
dónde se toma la pieza (la mejor versión) y qué se le suma de las otras.

> **La fuente de verdad son los `pieza.json`** (todas las piezas, listas y planeadas, ya tienen el suyo): `pieza.py catalogo`.
> Este archivo solo guarda el **orden de extracción** y las brechas encontradas. Al extraer una pieza, cambia su `estado` a
> `lista` y mueve aquí su fila.

## Listas

| Pieza | Versión | Qué es | Tomada de |
|---|---|---|---|
| `nucleo` | 0.7.1 | `app.json`, carpeta de datos, config validada, escritura atómica, `ruta_en`, contrato de scripts | Esquema `bin/comun.py` + Alcancía/Repasa |
| `ia` | 0.6.3 | La IA de la persona con su cuenta, segura; en vivo (lo que lee y «Detener») | Esquema `bin/ia.py` + `ia_vivo.py` + Alcancía (pedido en archivo) + Repasa (material) |
| `i18n` | 0.3.1 | `T`/`Tp`/`Thtml`/`tr`/`traducirDOM`, paquetes de idioma validados | Minuta (`tr`) + Esquema (`T` que escapa, `traducirDOM`) + Alcancía (`Thtml`) + Graba (prioridad) |
| `bienvenida` | 0.4.1 | Primer uso por pasos, el idioma siempre primero; cada pieza suma su paso | Repasa (teclas 1/2) + Esquema (avisos que esperan) + Graba (flechas) + Alcancía |
| `actualizaciones` | 0.4.0 | Releases del propio repo, `.sha256` obligatorio, Mac (target propio) y Electron | Esquema + Repasa (URL sin puerto ni `..`, PATH fijo, textos que traduce la interfaz) |
| `host-ui` | 0.3.0 | `crearHost({nombre, global, simular})`: `host.enviar` y `window.<App>.*` iguales en Mac, Electron, celular y navegador; `probarIA {ia}` en todas | Esquema + Repasa/Alcancía (puente del celular) + Minuta (mensaje plano mientras cambia) |
| `tema` | 0.2.1 | Un solo juego de tokens CSS (`--texto-suave`, `--panel-2`…), pares claro/oscuro con `light-dark()`, selector «Apariencia» | Esquema (`data-tema`, ahora `data-pz-modo`) + los nombres comunes de Graba, Corta, Repasa y Alcancía; tabla de nombres viejos → nuevos en su README |
| `componentes` | 0.3.0 | Diálogo con foco atrapado y Esc (`envolver` para uno de la app), confirmar, avisos en cola, filas de Tu IA, fila de actualización «Paso n de 3», Acerca de, comentarios a GitHub | Esquema + Alcancía («Cómo instalarla», error de la IA traducido) + Minuta (comentarios → issue prellenado) |
| `catalogo` | 0.3.0 | Contenido de la comunidad: índice validado (objeto entero) por el validador de la app, SHA-256 obligatorio, sin redirecciones, última lista sin conexión, catálogo plano o con categorías; Py + Swift + Electron | Esquema `plantillas.py` + `Catalogo.swift` + `catalogo.js` + Corta (`origen`, categoría = carpeta, un tipo por cosa) |
| `red` | 0.2.0 | HTTPS desde los scripts: dominios permitidos, sin redirecciones, topes de tamaño y tiempo, subidas por partes | Alcancía `bin/red.py` |
| `cifrado` | 0.2.0 | PBKDF2 600k + AES-256-GCM con AAD, HMAC para nombres, verificador, archivos con versión y con varios sobres | Repasa `motor/cifrado.js` + Alcancía `ui/copia.js` |
| `transcribir` | 0.2.0 | whisper.cpp con modelos de huella fija, vocabulario por archivo privado, VAD, filtro de inventos (con la energía: nunca borra un «gracias» dicho) y bucles | Minuta + Corta (`comando_transcribir`) + Graba |
| `trabajos` | 0.2.2 | Trabajos largos: estado en disco, latido (también para el host: `"limite": "trabajo"`), «Detener», preguntas; lectores de progreso Swift y Electron | Esquema `bin/trabajos.py` + `LectorProgreso` / `lectorProgreso` |
| `host-tauri` | 0.1.1 | **Un solo host para Mac, Windows y Linux** (Rust + Tauri, con el WebView del sistema): la misma API que `host-mac` y `host-escritorio` — ventana, puente con guardas, acciones declaradas con límite (o latido, o por orden), config/idioma de `app.json`, menús, bandeja, apariencia, carpeta, vigilante (`notify`), mostrar en carpeta, papelera, llavero del sistema, avisos, diálogos, una sola instancia; medios en el mismo origen que la interfaz | `host-mac` 0.3.0 + `host-escritorio` 0.3.0, en Rust |
| `host-mac` | 0.3.0 | **Retirada** (la reemplaza `host-tauri`). App de Mac genérica (target `PiezaHost`): ventana, puente con guardas, acciones declaradas con límite de tiempo (o latido, o por orden), config/idioma de `app.json`, menús, apariencia de `tema`, actualizaciones, carpeta con marcador, vigilante (FSEvents), Finder, Llavero y avisos | Esquema `app/Sources/Esquema/` (+ `Carpeta.swift`) + Alcancía (secreto por stdin, Llavero, avisos, carpeta de la nube) + Repasa (`conEntrada` con varios args) + Corta (`Medios.swift`) + Graba y Minuta (Llavero) |
| `host-ios` | 0.1.1 | App de iPhone genérica (WKWebView a pantalla completa, plataforma «movil»): puente con las guardas de `host-mac`, config/idioma de `app.json`, apariencia, pantalla encendida y tiempo en segundo plano mientras algo está en curso, y el proyecto de Xcode generado sin dependencias (grupo sincronizado, permisos de `app.json → ios`) | `host-mac` 0.3.0, para Despeja |
| `host-escritorio` | 0.3.0 | **Retirada** (la reemplaza `host-tauri`). Lo mismo en Electron, con `nativeTheme.themeSource` según `config.tema`; carpeta, vigilante (`fs.watch`), explorador, `safeStorage` y avisos | Esquema `escritorio/src/` (+ `vigilante.js`) + Graba (medios con rangos, permisos que abre la app, `Tokens`) + Alcancía (secreto por stdin) + Minuta (avisos) |
| `pagina` | 0.1.2 | La página pública bilingüe generada desde `docs/pagina.json`: permisos e internet y preguntas comunes que salen de las piezas, JSON-LD de lo que se ve, SEO, sello, workflow de Pages y capturas | Esquema `docs/` + `pagina_capturas.mjs` + Corta/Alcancía (permisos e internet) + Minuta (capturas) |
| `contrato` | 0.1.3 | `pruebas/contrato.py` común del puente: cada acción atendida en cada plataforma y en la vista previa, `acciones.json`, funciones y seguridad común; lo propio en `contrato_app.py` | Lo común de los seis `pruebas/contrato.py` |
| `contenido` | 0.1.0 | Leer md, txt, pdf, docx, odt, epub y html con topes (zip bombas, XML sin entidades); capítulos sin IA | Esquema `bin/contenido.py` + Alcancía (`ArchivoNoValido`) |
| `empaquetado` | 0.2.1 | Arma, firma, publica e instala desde `app.json` (plantillas) con el host de Tauri: `empaquetar.sh <mac|windows|linux>` con un solo `python.lock` y los mismos archivos de siempre (`.zip`, `.exe`, `.AppImage`, `.tar.gz`, `.deb`, cada uno con su `.sha256`), `build.sh` que no instala con la app ocupada, `preparar.sh` (también `whisper-cli` con `empaquetado.whisper`), `instalar.sh`/`.ps1` y `publicar.yml` (macos-15, windows-2025, ubuntu-24.04) | Esquema + Corta (binarios, licencias) + Graba (`binaryTarget`, frameworks, permisos, barra de menú) + las seis (no instalar ocupada) |
| `github` | 0.3.0 | El repo para la comunidad desde `app.json`: issues, PR, dependabot, `revisar.yml`, Pieza al día, `AGENTS`/`CONTRIBUTING`/`SECURITY` con lo que llena la IA marcado, agentes, privacidad, `.gitignore`, la wiki (`docs/wiki/` → `wiki.yml`); `pieza.py repo configurar` | Esquema `.github/` y guías + Alcancía/Repasa (job `mac` con `app.json`) + las seis (secciones comunes de `AGENTS.md`) |

| `esqueleto` | 0.2.0 | Lo propio mínimo de una app nueva, andando: `ui/` con bienvenida (idioma primero), pantalla y script de ejemplo (acción declarada), Mac y Windows/Linux sobre el host, demo, `correr.sh`, pruebas de Python, de interfaz y del contrato. Lo escribe una vez **`pieza.py crear`** | Graba (`app.js` con las piezas), Repasa (`RepasaApp.swift`), Esquema (`main.js`, CSP), Pieza (`interfaz.mjs`) |

**Crear una app nueva** = `pieza.py crear <carpeta> --id … --nombre … --plataformas … [--piezas …]`: las de siempre + las pedidas +
`esqueleto` + `github`, todo generado y con sus pruebas en verde (`pruebas/test_crear.py`). Ver el README de `esqueleto`.

### El paso a `host-tauri` (nov 2026)

| App | Estado |
|---|---|
| Alcancía, Corta, Despeja, Esquema, Repasa | **Hecho.** Su app de escritorio corre en `host-tauri` (Rust). Ya no tienen `app/` (Swift) ni Electron. |
| Graba, Minuta | **Falta.** Usan cosas que existen solo en Apple: capturar pantalla y audio del sistema (ScreenCaptureKit, CoreAudio), la burbuja de la cámara, dictado y diarización. Necesitan primero el **ayudante** en Swift dentro de `empaquetado` (README de `host-tauri`, «Lo que solo existe en Apple»). Siguen en `host-mac` y `host-escritorio` hasta entonces. |

## Por extraer, en este orden

| # | Pieza | Tipo | Tomar de | Sumar de | Notas |
|---|---|---|---|---|---|
| 8 | `mcp` (Py) | Py | Alcancía `mcp_servidor.py` + `mcp_conectar.py` | — | `mcp.servir(nombre, …, herramientas)`; conectar a claude/codex/gemini/Claude Desktop |
| 15 | `universos` | Py + UI | Minuta (`universo.py`, galería) | Catálogo (#6) | Lo que pediste como ejemplo: tras #6 queda casi listo |

### Pendientes que salieron al pasar las apps a las piezas de datos (anotados, sin hacer)

| # | Qué | Por qué espera |
|---|---|---|
| 4 | Descarga de modelos de whisper (`ModeloWhisper` / `Modelos` en Swift y Electron) en el host o en una pieza «modelos» | Hoy se repite en Graba, Minuta y Corta (mismas huellas que `transcribir.MODELOS`). Va con el host genérico: descarga con avance, huella y reintento son nativos; la acción `modelosVoz` ya da la lista |
| 5 | Pieza `youtube` (Graba tiene `bin/youtube.py`) | Fase aparte: necesita OAuth de la persona, la subida por partes de `red` 0.2 (`subir`) y revisar los permisos de la API. Ya está planeada (`piezas/youtube`) |
| 18 | El dictado del Gimnasio de Minuta en Electron llama a `whisper-cli` directo | Debería pasar por `transcribir` (vocabulario por archivo, VAD, filtro). Toca el dictado en vivo de Minuta (otra forma: trozos cortos), así que va con la migración de Minuta al host, no aquí |

Después: `generar_demo.py` (la página pública, el contrato genérico, el repo y el empaquetado ya son las piezas `pagina`, `contrato`, `github` y `empaquetado`; `revisar_privacidad.sh` lo genera «github»).

### Lo que salió al pasar las seis apps al host (`host-mac`/`host-escritorio` 0.2.0)

Cada app anotó lo que le faltó a las piezas al migrar (nov 2026). Agrupado por pieza y sin repetir; entre paréntesis, quién lo pidió.

**Hecho en esta pasada** (`catalogo` 0.2.1, `nucleo` 0.7.1, `trabajos` 0.2.1, `host-mac` y `host-escritorio` 0.3.0, `bienvenida`
0.4.0; ver `CHANGELOG.md` y «Si venías de…» en cada README):
- `catalogo`: «archivo»/«bytes» del contenido ya no se quitan (Esquema, bloqueante); `migrar` en lista y `pieza.py revisar` lo exige
  (Esquema); el comentario de `Catalogo.swift` y la nota de «sin conexión» en el README (Esquema).
- `nucleo`: `ruta_en` con base vacía o relativa da `None` (Esquema). `trabajos`: SIGTERM → `SystemExit` en `mantener_vivo()` (Corta).
- Los dos hosts: variables de la app para todos los scripts (Corta, bloqueante; Graba, Minuta); un enlace tocado pasa por el
  `abrirEnlace` de la app (Repasa); `~/<Nombre>` visible 0700 (Repasa); «Guardar como» privado y que distingue cancelar (Repasa);
  `mensaje` en los diálogos (Alcancía, Repasa); `limiteEstado` (Alcancía) y `estadoEnFila` (Repasa); «Ajustes…» con otro título y
  ítems propios (Repasa); notas de «Pasar una app» (`menu`, `listo`, `config` sin estado, `desdeInterfaz`, `texto.max`, `"otro": 300`:
  Alcancía, Corta, Graba, Esquema).
- `host-mac`: barra de menú con `abrirAlArrancar` (Graba, Minuta), `alCrearVentana`, barra transparente y vidrio (Alcancía, Corta,
  Graba), `nombreVentana` (Alcancía), soltar archivos (Corta), ⌘W sin menú Archivo y `Menus()` público (Repasa).
- `host-escritorio`: `ventana.frame`, `abrirAlArrancar`/`--oculta`, `userData: "sistema"`, `before-quit` con la ventana que se
  esconde y más de una ventana en el puente (Minuta, Graba).
- `bienvenida`: «Ajustes» configurable (Repasa), «Lo hago después» y botón propio en el último paso (Repasa, Alcancía),
  `data-autofoco` y `detalle` por idioma (Corta), `logo` (Alcancía, Graba).
- La skill de crear: ya no dice que los flujos «se instalan solos» (Claude Code los **ofrece**: Esquema).

**Pendiente, por pieza** (nada de esto bloquea: cada app lo resolvió en su código, con un comentario «pendiente para Pieza»):

| Pieza | Qué | Quién | Notas |
|---|---|---|---|
| enchufe (`pieza.py`, `enchufe.js`, `Enchufe.swift`) | Tipos nuevos en `datos`: `numero{min, max}` (finito, no bool), `objeto{maxBytes}` y `carpetaDe{fuente}` (una carpeta de la interfaz que un validador de la app resuelve a ruta real) | Corta, Minuta, Repasa | Hoy van por `"*": "pasar"` o un inyector que hace de guarda. Cambia las reglas: los tres lados y `HostGenerico` |
| enchufe | `$campo` de un inyector `enum`/`fecha` en `args`; decir en `enchufe.md` que un campo inyectado nunca va en `args` | Alcancía | |
| enchufe | El error de datos pierde la `ruta` que no pasó (eco solo de lo válido): un `eco` recortado y escapado | Esquema | No bloqueante |
| config (`nucleo`, los dos hosts) | Claves de config que son objetos (`{"tipo": "objeto", "campos": {…}}`) o un gancho `alGuardarConfig` | Alcancía | Alcancía registró `config` entera |
| `host-mac` | `Secretos.cuentas()` (listar las cuentas de un servicio; diff en las notas de Alcancía) y `etiqueta` al guardar | Alcancía | |
| `host-mac`, `host-escritorio` | Avisos con categoría (texto oculto en la pantalla bloqueada) y con botones (`registrarCategorias`, `alResponder`) | Alcancía, Minuta | |
| `host-mac` | Ventana y WKWebView propios (`fabricaVentana`, `fabricaWeb`, regiones de arrastre) y más de un WKWebView en el puente (`Puente.adoptar(web:)` o `correrDeclarada(…, responder:)` público) | Minuta | Electron ya tiene `ventanas.agregar` |
| `host-mac` | `PiezaHost` exporta `Idioma` y `Puente`, que chocan con nombres de la app (prefijo o documentarlo) | Minuta | |
| `host-mac`, `host-escritorio` | `Idioma.t` que lea también `<datos>/idiomas/` (idiomas descargados del catálogo), con el mismo validador | Minuta | |
| `host-mac` | `Configuracion(configArchivo:)` (una app cuyo `config.json` es otra cosa); `CarpetaElegida.elegir(guardar: false)` y un estado «falta» si la carpeta desapareció; `llamarCuandoEsteLista` (un aviso tocado con la app cerrada); un inyector común `archivoElegido`; `Actualizador(textoOcupada:)` | Minuta, Alcancía, Repasa | |
| `host-escritorio` | `listoAlCargar`; scripts largos con registro y sin salida JSON (`correr(…, {registro, sinSalida, latido})`, igual en Swift); código de un checkout de desarrollo (`"desarrollo": "carpetaDatos"`); `menu.alSalir`; `ventana.json` con otro nombre; vidrio de Windows 11 (`<ID>_VIDRIO` en el preload y `setBackgroundMaterial`); soltar archivos (`webUtils.getPathForFile` en el preload) | Minuta, Graba | |
| `host-escritorio` | `host.secretos` en Linux sin llavero: qué hacer con lo que una app guardaba antes en texto plano (¿leerlo y pedir llavero para guardar?) | Minuta | Decidir la regla |
| `host-mac`, `host-escritorio` | Que el host ponga `<ID>_PROGRAMAS`/`<ID>_HERRAMIENTAS` solo (con `entorno` ya se puede a mano) | Corta, Graba | |
| `trabajos` | Avance por archivo de estado (`emitir_avance(paso, texto, pct)` o un lector de `estado.json` en el host): `transcribir`/`exportar` de Corta y Graba siguen registrados | Corta, Graba | |
| `trabajos` (`pieza.py`) | Archivos nativos opcionales (`--solo=python` o `opcional` por archivo): hoy `LectorProgreso.swift` y `progreso.js` llegan aunque solo se use el latido | Graba, Corta | |
| `bienvenida` | Abrir mientras falte algo aunque ya se hizo (`abrir({pendiente})`) y un `Idioma.elegido` que la app pueda ampliar | Graba | |
| `bienvenida` | Pasos con sub-pantallas y estado propio, pantalla completa con el arte del tema, primer uso decidido por la app (`abrir({esPrimeraVez, idioma})`), `terminar(datos)` | Minuta | |
| `actualizaciones` | Instalación de desarrollo en Electron (`crear({desarrollo})`); reconocer un checkout sin `archivoDesarrollo`; decir en el README que «quien llama se asegura» de que no haya nada corriendo | Minuta | |
| `transcribir` | `transcribir.py dictar <entrada {wav}> <salida>` (acción `soloHost`) para dictar sin script propio | Minuta | |
| `pieza.py` | `actualizar` que avise «la versión nueva trae X y la app tiene uno propio distinto» en vez de saltarlo | Esquema | |
| `pruebas/contrato.py` común | Contemplar `copiado` sin `copiar` y `menu` como respuesta obligatoria | Repasa, Corta, Alcancía | Hecho en la pieza `contrato` 0.1.0 |
| `ia`/`componentes` (docs) | Con el host genérico, `elegirIA` tiene que mandar `config {ia}` (`probarIA` declarada no lo guarda) | Repasa | |
| `host-escritorio` | `host.ventanas.agregar(w)`: revisar que la ventana venga con `sandbox`/`contextIsolation` de `preferencias()` (`getLastWebPreferences()`) y ponerle `render-process-gone` | Revisión de 0.3.0 | Hoy lo dice el README |

## Brechas encontradas al comparar (arreglar ya en esas apps)

Las de la primera comparación (CLI viejo sin protecciones, puente sin guardas, actualizaciones y catálogo sin huella, la IA con las
variables de la app, el vocabulario de `whisper-cli`, `T()` sin escapar, procesos sin límite, rojo y verde bajo AA, `probarIA {id}` y
las ventanas de Minuta sin `aria-modal`) ya las resolvieron las migraciones a las piezas (revisado en el código de cada app, nov
2026). Quedan:

| App | Qué | Dónde | Arreglo |
|---|---|---|---|
| Minuta | Los scripts largos (`procesar.py`, `semana.py`, `universo.py`) corren con su `ejecutar` propio: **sin límite** ni latido, no se cortan al salir y (en Electron) heredan todo el entorno, también `MINUTA_*` de afuera | `MinutaApp.swift` (`ejecutar`), `escritorio/src/main.js` (`ejecutar`, `entornoPython`) | `trabajos.mantener_vivo()` en esos scripts y correrlos con el procesador del host (`latido: true`, `entorno`), o lo de «scripts largos con registro» (arriba) |
| Alcancía, Esquema, Graba, Minuta | `CONTRIBUTING.md` dice que los flujos de Pieza «se instalan solos al abrir el repo»: con `.claude/settings.json` solo con `extraKnownMarketplaces`, Claude Code los **ofrece** | `CONTRIBUTING.md` | La frase de la skill de crear (versión 11) |
| Esquema | `acciones.json` carga `catalogoInstalados`, `catalogoQuitar`, `catalogoUltima` y `listaIA`, que la interfaz nunca pide (lo vio la pieza `contrato`) | `app.json` | Sumarlas a `sin_acciones` y `pieza.py acciones .` |
| Minuta | Con la pieza `contrato` y su extensión: 47 acciones sin vista previa en `simular()`, `abrirEnlace`/`config` (de «componentes») sin caso en Mac, `menu`/`copiado` que llama el host de Electron sin función, y las ventanas `alerta` y `grabadora` sin `sandbox: true` explícito | `ui/app.js`, `VisorWeb.swift`, `escritorio/src/main.js` | Al adoptar `contrato`: decidir cada una (arreglo o excepción con motivo) |
| Corta, Esquema | Copias de piezas cambiadas: Corta, `host-mac` (`entornoApp`); Esquema, `catalogo` (los alias). Las dos ya están en Pieza | `app/Sources/PiezaHost/Procesador.swift`, `bin/catalogo.py` | `pieza.py actualizar . host-mac --forzar` / `… catalogo --forzar` |

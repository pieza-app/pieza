# Catálogo de piezas y plan

Sale de comparar las seis apps (oct 2026): ~60 archivos repetidos, casi todos con una versión distinta por app. Cada fila dice de
dónde se toma la pieza (la mejor versión) y qué se le suma de las otras.

> **La fuente de verdad son los `pieza.json`** (todas las piezas, listas y planeadas, ya tienen el suyo): `pieza.py catalogo`.
> Este archivo solo guarda el **orden de extracción** y las brechas encontradas. Al extraer una pieza, cambia su `estado` a
> `lista` y mueve aquí su fila.

## Listas

| Pieza | Versión | Qué es | Tomada de |
|---|---|---|---|
| `nucleo` | 0.7.0 | `app.json`, carpeta de datos, config validada, escritura atómica, `ruta_en`, contrato de scripts | Esquema `bin/comun.py` + Alcancía/Repasa |
| `ia` | 0.6.1 | La IA de la persona con su cuenta, segura; en vivo (lo que lee y «Detener») | Esquema `bin/ia.py` + `ia_vivo.py` + Alcancía (pedido en archivo) + Repasa (material) |
| `i18n` | 0.3.1 | `T`/`Tp`/`Thtml`/`tr`/`traducirDOM`, paquetes de idioma validados | Minuta (`tr`) + Esquema (`T` que escapa, `traducirDOM`) + Alcancía (`Thtml`) + Graba (prioridad) |
| `bienvenida` | 0.3.0 | Primer uso por pasos, el idioma siempre primero; cada pieza suma su paso | Repasa (teclas 1/2) + Esquema (avisos que esperan) + Graba (flechas) + Alcancía |
| `actualizaciones` | 0.3.0 | Releases del propio repo, `.sha256` obligatorio, Mac (target propio) y Electron | Esquema + Repasa (URL sin puerto ni `..`, PATH fijo, textos que traduce la interfaz) |
| `host-ui` | 0.2.0 | `crearHost({nombre, global, simular})`: `host.enviar` y `window.<App>.*` iguales en Mac, Electron, celular y navegador; `probarIA {ia}` en todas | Esquema + Repasa/Alcancía (puente del celular) + Minuta (mensaje plano mientras cambia) |
| `tema` | 0.2.1 | Un solo juego de tokens CSS (`--texto-suave`, `--panel-2`…), pares claro/oscuro con `light-dark()`, selector «Apariencia» | Esquema (`data-tema`, ahora `data-pz-modo`) + los nombres comunes de Graba, Corta, Repasa y Alcancía; tabla de nombres viejos → nuevos en su README |
| `componentes` | 0.3.0 | Diálogo con foco atrapado y Esc (`envolver` para uno de la app), confirmar, avisos en cola, filas de Tu IA, fila de actualización «Paso n de 3», Acerca de, comentarios a GitHub | Esquema + Alcancía («Cómo instalarla», error de la IA traducido) + Minuta (comentarios → issue prellenado) |
| `catalogo` | 0.1.0 | Contenido de la comunidad: índice validado por el validador de la app, SHA-256 obligatorio, sin redirecciones; Py + Swift + Electron | Esquema `plantillas.py` + `Catalogo.swift` + `catalogo.js` + Corta (`origen`, categoría = carpeta, un tipo por cosa) |
| `red` | 0.1.0 | HTTPS desde los scripts: dominios permitidos, sin redirecciones, topes de tamaño y tiempo | Alcancía `bin/red.py` |
| `cifrado` | 0.1.0 | PBKDF2 600k + AES-256-GCM con AAD, HMAC para nombres, verificador, archivos con versión | Repasa `motor/cifrado.js` + Alcancía `ui/copia.js` |
| `transcribir` | 0.1.0 | whisper.cpp con modelos de huella fija, vocabulario por archivo privado, VAD, filtro de inventos y bucles | Minuta + Corta (`comando_transcribir`) + Graba |
| `trabajos` | 0.1.0 | Trabajos largos: estado en disco, latido, «Detener», preguntas; lectores de progreso Swift y Electron | Esquema `bin/trabajos.py` + `LectorProgreso` / `lectorProgreso` |
| `host-mac` | 0.1.0 | App de Mac genérica (target `PiezaHost`): ventana, puente con guardas, acciones declaradas con límite de tiempo, config/idioma de `app.json`, menús, apariencia de `tema` | Esquema `app/Sources/Esquema/` + Alcancía (secreto por stdin) + Repasa (`conEntrada` con varios args) + Corta (`Medios.swift`) |
| `host-escritorio` | 0.1.0 | Lo mismo en Electron, con `nativeTheme.themeSource` según `config.tema` | Esquema `escritorio/src/` + Graba (medios con rangos, permisos que abre la app) + Alcancía (secreto por stdin) |
| `contenido` | 0.1.0 | Leer md, txt, pdf, docx, odt, epub y html con topes (zip bombas, XML sin entidades); capítulos sin IA | Esquema `bin/contenido.py` + Alcancía (`ArchivoNoValido`) |

## Por extraer, en este orden

| # | Pieza | Tipo | Tomar de | Sumar de | Notas |
|---|---|---|---|---|---|
| 8 | `mcp` (Py) | Py | Alcancía `mcp_servidor.py` + `mcp_conectar.py` | — | `mcp.servir(nombre, …, herramientas)`; conectar a claude/codex/gemini/Claude Desktop |
| 13 | `empaquetado` | build | Esquema | — | Copiar `acciones.json` junto a `app.json` (hoy cada app lo agrega a mano: ver los README de los hosts). `build.sh`, `empaquetar.sh`, `preparar.sh`, instaladores, `Package.swift`, `Info.plist` generados desde `app.json`. El Python portátil (CPython 3.13.16) ya es idéntico en las seis: un solo `python.lock` |
| 14 | `github` | repo | Esquema | — | Plantillas de issues/PR, `dependabot`, workflows reutilizables (`workflow_call`) para revisar y publicar |
| 15 | `universos` | Py + UI | Minuta (`universo.py`, galería) | Catálogo (#6) | Lo que pediste como ejemplo: tras #6 queda casi listo |

Después: la página pública (`docs/`), `revisar_privacidad.sh`, `generar_demo.py`, `pruebas/contrato.py` genérico.

## Brechas encontradas al comparar (arreglar ya en esas apps)

| App | Qué | Dónde | Arreglo |
|---|---|---|---|
| Graba, Minuta | Si el CLI de IA es viejo, **reintenta sin las protecciones** (`--strict-mcp-config`, sin herramientas): la IA corre con todo, con texto de afuera | `graba/bin/ia.py`, `minuta/bin/perfil.py` (`_opcion_desconocida`) | Reemplazar por la pieza `ia` |
| Graba, Minuta | El puente no revisa que el mensaje venga del marco principal y del origen de la app | `graba/app/Sources/Graba/Ventana.swift`, `minuta/app/Sources/Minuta/VisorWeb.swift`, `graba/escritorio/src/main.js`, `minuta/escritorio/src/main.js` | Copiar la guarda de Esquema (`isMainFrame` + `securityOrigin`; `senderFrame === mainFrame` + origen) |
| Graba | Las actualizaciones no validan que la descarga sea de su repo ni escapan la ruta en el script | `Actualizaciones.swift`, `escritorio/src/actualizaciones.js` | Pieza `actualizaciones` (lista) |
| Corta | Instalar del catálogo acepta archivos sin SHA-256 | `corta/bin/plantillas.py` (`instalar`) | Pieza `catalogo` (lista: obligatorio) |
| Corta, Graba, Repasa, Minuta | La IA hereda las variables de la app | `bin/ia.py` | Pieza `ia` |
| Graba | Con `whisper-cli` (Windows y Linux) el vocabulario no se usa | `bin/procesar.py` | Pieza `transcribir` (lista: `whisper-cli @archivo`) |
| Minuta | El catálogo de universos e idiomas no verifica SHA-256 ni tamaño | `Catalogo.swift` | Índice con `sha256`/`tamano` (`catalogo.py generar`) y pieza `catalogo` |
| Alcancía, Corta, Repasa | `T()` mete valores sin escapar en HTML | `ui/app.js` | Pieza `i18n` (lista: `T` escapa, `Thtml` para HTML armado) |
| Todas | Ningún `Procesador` tiene límite de tiempo | Swift/Electron | Piezas `host-mac` y `host-escritorio` (listas: `limite` obligatorio, corta también a los descendientes) |
| Graba, Repasa | Rojo y verde bajo AA como texto en claro (Graba también el rojo en oscuro) | `ui/app.css` | Los pares del README de `tema` (mismo tono, un poco más oscuro) |
| Graba, Corta, Repasa, Alcancía, Minuta | `probarIA` manda `{id}`; Esquema y la pieza `ia`, `{ia}` | `ui/app.js` + `Ventana.swift`/`VisorWeb.swift`, Electron y `movil/host/host.js` | Pieza `host-ui` (lista): `{ia}` en todas |
| Minuta | Sus ventanas (`.galeria-caja`, `role="dialog"`) no tienen `aria-modal` ni atrapan el foco | `ui/app.js` | Pieza `componentes` (lista) |

# Pieza «host-mac» — la app de Mac (Swift, WKWebView)

La parte nativa que cada app repetía (900–2.500 líneas casi iguales de `Ventana.swift`, `Servicios.swift` y `<App>App.swift`),
una sola vez y sin nada de una app adentro: todo sale de `app.json` (dentro de la app, en `Contents/Resources/<id>/`) y de
`Host.Configuracion`. Va en su **propio target de SwiftPM** (`PiezaHost`), como `PiezaActualizaciones`. Misma API y mismas reglas
que [`host-escritorio`](../host-escritorio/).

| Archivo (`app/Sources/PiezaHost/`) | Qué hace |
|---|---|
| `Host.swift` | `Host.arrancar/configurar`, rutas (datos, recursos, Python), `Config` (reglas de `nucleo`), `Idioma`, el delegado de la app |
| `Procesador.swift` | Scripts de `bin/` con **límite de tiempo** (corta también a los descendientes), entorno sin `<ID>_*`, entrada por archivo, secreto por stdin; `Fila` |
| `Enchufe.swift` | Acciones declaradas (`acciones.json`): revisarlas al cargar, validar los datos de cada mensaje; `Enchufe.dentro` (= `nucleo.ruta_en`) |
| `Puente.swift` | Ventana, WKWebView, puente con guardas, navegación, `<id>://` para medios, diálogos, menús, apariencia, actualizaciones |
| `Carpeta.swift` | `CarpetaElegida` (la carpeta de la persona con marcador del sistema) y `Vigilante` (FSEvents, sin avisar lo que escribió la app) |
| `Sistema.swift` | `Secretos` (Llavero) y `Notificaciones` (avisos del sistema) |

## Uso

`Package.swift`:
```swift
.executableTarget(name: "Ana", dependencies: ["PiezaHost"], path: "Sources/Ana"),
.target(name: "PiezaHost", path: "Sources/PiezaHost"),
```
`Sources/Ana/AnaApp.swift`:
```swift
import AppKit
import PiezaHost
import PiezaActualizaciones   // opcional

@main enum AnaApp {
    @MainActor static func main() {
        Host.arrancar(.init(sitio: "https://ana-app.github.io/ana/", codigo: "https://github.com/ana-app/ana")) { p in
            p.inyectores["proyecto"] = { _ -> Any? in Proyecto.actual() ?? Puente.Falta("Elige un proyecto primero.") as Any }  // nunca la interfaz
            p.estado = { base, listo in var e = base; e["carpeta"] = p.carpeta?.actual()?.path; listo(e) }
            p.menus = { m in [m.archivo([m.item("Nuevo…", "nuevo", "n"), m.nativo("Abrir carpeta…", "o") { p.carpeta?.elegir { _ in p.enviarEstado() } }]),
                              m.edicion(), m.ver([m.item("Acercar", "acercar", "+")])] }
            p.registrar("exportar") { d in
                p.guardarComo(nombre: d["nombre"] as? String ?? "ana", extension: "svg", datos: Data((d["texto"] as? String ?? "").utf8)) { u in
                    p.llamar("exportado", ["ok": u != nil])
                }
            }
            // Pieza «actualizaciones»: el host atiende buscarActualizacion/actualizar (nunca con algo en curso), revisa cada 6 h con
            // el idioma elegido y suma `actualizacion` al estado.
            Actualizaciones.configurar(.init(repo: "ana-app/ana", nombre: "Ana",
                archivoDesarrollo: Host.datos.appendingPathComponent("desarrollo"), variableProgreso: Host.prefijo + "PROGRESO"))
            p.actualizaciones = .init(revisar: Actualizaciones.revisar, revisarCadaRato: Actualizaciones.revisarCadaRato,
                seguir: Actualizaciones.seguir, instalar: Actualizaciones.instalar, aviso: Actualizaciones.aviso,
                disponible: { Actualizaciones.disponible })
            // La carpeta de la persona (con marcador) y su vigilante: `carpetaActual` para las acciones y `archivoCambiado`.
            p.carpeta = CarpetaElegida()
            p.vigilante = Vigilante(extensiones: ["md"])
            // Pieza «trabajos» (habilita `progreso` en las acciones declaradas):
            Procesador.lectorProgreso = { aviso in let l = LectorProgreso(prefijo: Host.id, aviso: aviso); return (l.url.path, l.empezar, l.terminar) }
        }
    }
}
```

## API

| | |
|---|---|
| `Host.Configuracion(ancho:alto:minAncho:minAlto:sitio:codigo:menuAyuda:avisos:global:estadoScript:cerrarSale:recursos:python:limiteEstado:estadoEnFila:tituloAjustes:barraDeMenu:abrirAlArrancar:barraTransparente:altoFranja:vidrio:nombreVentana:)` | Todo opcional. `global`: el objeto `window.<App>` (por defecto el id con mayúscula). `cerrarSale`: cerrar la ventana cierra la app. `menuAyuda: false`: sin menú Ayuda. `avisos: true`: el host atiende el toque de un aviso desde el arranque. Desde 0.3.0: `limiteEstado` (segundos del script del estado, 60), `estadoEnFila` (el estado se lee dentro de la `Fila`, nunca a medio guardar), `tituloAjustes` («Ajustes…» con otro nombre; `nil` sin él), `barraDeMenu` + `abrirAlArrancar` (app de barra de menú), `barraTransparente` + `altoFranja` y `vidrio` (ventana sin barra de título), `nombreVentana` (con qué nombre se recuerda el tamaño de la ventana). |
| `Host.arrancar(c) { puente in … }` | Configura, crea la app, deja registrar lo propio, instala menús, aplica la apariencia y abre la ventana. Lo que corre solo (`tareas`) espera al idioma elegido. Al salir, la interfaz guarda y se espera la fila (3 s). |
| `Host.id`, `.nombre`, `.app`, `.datos`, `.recursos`, `.prefijo`, `.version`, `.python`, `prepararDatos()` | Desde `app.json` (`datos`: `sistema`, `visible` o `{"carpeta": "~/…"}`, igual que `nucleo.carpeta_datos()`). |
| `Config.leer()`, `.guardar(cambios, desdeInterfaz:)`, `.texto(clave)`, `.valida(regla, valor)` | `config.json` con las claves de `app.json` (`"interfaz": false` no se cambia desde la interfaz). |
| `Idioma.codigo`, `.elegido`, `.t(_)`, `.f(_, valores)`, `.fuente` | `fuente`: si la app guarda `idioma_ui` en otro lado. |
| `Puente.shared` / `Puente.registrar("accion") { datos in … }` | Una acción propia. Gana sobre las del host y las declaradas (se migra de a poco). |
| `llamar(funcion, json)`, `intentarLlamar(…) -> Bool`, `despachar(accion, datos)` | Hacia la interfaz (solo nombres simples, nada antes de `listo`) y correr una acción. `llamar` no devuelve nada: `guard … else { return p.llamar(…) }` compila. |
| `inyectores`, `estado`, `tareas`, `alCambiarConfig`, `menus`, `menuApp`, `antesDeSalir`, `alConfigurarWeb`, `alCrearVentana` | Ganchos (ver arriba). Un inyector devuelve el valor, nil (`codigo: "falta"`) o `Puente.Falta("texto", valores)` (lo mismo con ese texto). `alConfigurarWeb`: otro manejador o preferencia del `WKWebViewConfiguration`. `menuApp: { m in [...] }`: ítems bajo «Ajustes…» en el menú de la app. `alCrearVentana: { ventana, web in }`: recién creada, antes de mostrarla. `Menus()` tiene `init` público (para armar un ítem fuera de `menus`). |
| `alSoltar = { urls in }`, `soltados`, `soltado(nombre)` | Soltar archivos en la ventana: el host siempre guarda las rutas de lo último que se soltó (sin enlaces; `alSoltar` es opcional, para enterarse) y la página recibe su `drop` como siempre (ve solo los nombres). La interfaz manda el nombre y la app pide la ruta con `soltado(nombre)`: nunca una ruta armada con lo que manda la web. |
| `actualizaciones = Puente.Actualizador(…)` | Las funciones de la pieza «actualizaciones» (arriba): el host atiende `buscarActualizacion` → `actualizacionRevisada` y `actualizar` → `actualizacionProgreso` (con `codigo: "ocupada"` si algo sigue en curso después de 5 s). |
| `carpeta = CarpetaElegida(marcador:clave:)` | `.actual()`, `.elegir(mensaje:boton:) { url in }`, `.usar(url)`, `.olvidar()`, `.textoFalta`. Marcador en `UserDefaults` (la sigue aunque la muevan) y la ruta en `config.<clave>` para los scripts (`"interfaz": false` en `app.json`). Con ella, el inyector `carpetaActual`. |
| `vigilante = Vigilante(extensiones:espera:maximo:)` | `.conocer(ruta, texto)`, `.olvidar(ruta)`, `.conocidos`, `.absoluta(rel)`, `.empezar(url)`, `.detener()`, `.alCambiarArchivo` (por defecto `archivoCambiado {ruta, texto}`), `.alCambiar` (para volver a listar). Lo mueve la carpeta y lo usan las acciones con «vigilar». |
| `mostrarEnFinder(url)` | El archivo o la carpeta, elegido en el Finder. Solo rutas que la app ya revisó. |
| `Secretos(servicio:)` / `Secretos.deLaApp` | `.guardar(valor, cuenta:)`, `.leer(cuenta)`, `.borrar(cuenta)`: el Llavero, solo en este Mac (`WhenUnlockedThisDeviceOnly`). Un secreto llega a un script solo por stdin (`Procesador.conSecreto`). Mismo `servicio` que antes = los tokens de siempre siguen ahí. |
| `Notificaciones.pedirPermiso { ok in }`, `.mostrar(id:titulo:texto:sonido:)`, `.quitar(id)`, `.alTocar` | Avisos del sistema. El permiso, cuando la app lo pide (nunca al abrir); nada antes de elegir el idioma; tocar uno muestra la ventana y llama `alTocar(id)`. |
| `registrarMedios("video") { ruta in URL? }` | `<id>://video/<ruta>` con rangos. Antes de `mostrar()` (en el bloque de `arrancar`). |
| `elegirCarpeta(mensaje:boton:desde:)`, `elegirArchivos(extensiones:varios:mensaje:boton:desde:)`, `guardarComo(nombre:extension:datos:desde:maximo:mensaje:privado:)`, `guardarArchivo(…) { Guardado in }`, `papelera(_:)`, `copiar`, `abrirEnlace` | Diálogos y capacidades comunes. `mensaje`: qué elegir o dónde guardar, en el panel. `privado`: el archivo queda 0600 (sin decirlo, lo de `app.json` → `"privado"`). `guardarArchivo` dice cómo terminó: `.guardado(url)`, `.cancelado` o `.error("vacio" \| "tamano" \| "extension" \| "escribir")` (`guardarComo` da `nil` en todos esos casos). |
| `Procesador.entornoApp` | Variables de la app para **todos** sus scripts, también los declarados: `Procesador.entornoApp[Host.prefijo + "PROGRAMAS"] = …`. Las de cada llamada (`entorno:`) ganan; nunca pisan `<ID>_RECURSOS`, `_DATOS`, `_PROGRESO` ni `_LATIDO`. |
| `ocupar()`/`soltar()`, `ocupada`, `esperarLibre(segundos:)` | Para no cerrar ni actualizar en medio de algo. |
| `aplicarApariencia()` | `config.tema` (`sistema`/`claro`/`oscuro`, pieza `tema`) → `NSApp.appearance` y la ventana. La llama `config` solo. |
| `Procesador.correrJSON(script, args, limite:latido:)`, `.conEntrada(script, "accion" \| [args], datos, limite:latido:progreso:)`, `.conSecreto(script, args, secreto:)`, `.correr(…)`, `.cortarTodo()` | `correr` y `conSecreto` dan `Resultado(respuesta, salidaEstandar, porLimite)`. `latido: true`: sin tope mientras el script lata (pieza «trabajos»; se corta a los `latidoMuerto` = 45 s sin latido). `lectorProgreso` es `@MainActor`. |
| `Fila.agregar { listo in … listo() }` | De a una y en orden. |
| `Enchufe.dentro(base, relativa, extensiones:)` | La guarda de `nucleo.ruta_en`. |

Lo que atiende solo: `listo` (estado), `config` (guarda, rearma los menús en el idioma nuevo, aplica la apariencia y arranca las
tareas), `abrirEnlace` (solo https), `copiar` → `copiado`, con `actualizaciones` `buscarActualizacion` y `actualizar`, y toda acción
declarada en `acciones.json` (validar → inyectar → fila → «vigilar» → script con su límite → `responde` con `eco` → `despues`; ver [`host-escritorio`](../host-escritorio/README.md#acciones-declaradas-accionesjson)
y [`docs/enchufe.md`](../../docs/enchufe.md#una-acción)). Errores: `{ok: false, codigo: "datos" | "falta" | "limite" | "fallo", texto, valores, error}`.

## Seguridad

- El puente solo atiende el **marco principal**, con origen `file` **y** una página dentro de `ui/` (las apps de hoy solo miraban
  las dos primeras). La ventana nunca navega fuera de `ui/`; un enlace https tocado va al navegador **por `abrirEnlace`**: si la app
  registró el suyo (una app para niños que solo abre su sitio), decide ella (antes de 0.3.0, un `<a href>` tocado se lo saltaba). `<input type=file>` solo para el marco
  principal propio. Si el proceso de la página se cae, se vuelve a cargar.
- `<id>://` sirve solo lo que aprueba el resolvedor de la app (sin `?`, `#`, usuario ni clave).
- Scripts: `<ID>_*` de afuera nunca llegan; lo de la persona en un archivo de entrada dentro de una carpeta temporal 0700;
  secreto por stdin; **límite de tiempo** (SIGTERM al script y a sus descendientes, y SIGKILL 3 s después); un trabajo sin tope
  se corta si deja de latir, y al salir se corta lo que siga corriendo (nada queda huérfano). Sin `__pycache__`.
- Secretos solo en el Llavero, solo en este Mac; los avisos nunca antes de elegir el idioma ni con el permiso pedido al abrir.
- Con `"datos": "visible"`, `~/<Nombre>` recién creada queda 0700 como `nucleo` (antes 0755; una que ya existía no se toca).

## Compilar en el Mac

Swift no compila en Linux: `bash pruebas/swift/revisar_host_mac.sh` (desde Pieza) arma un paquete temporal con la pieza, la
compila con `swift build` y corre una prueba sin ventana (reglas del enchufe con límites por orden, «maximo», «vigilar» y el eco
válido; config; carpeta con marcador y vigilante con FSEvents; procesador con Python: entrada por archivo, entorno sin `ANA_*`,
secreto por stdin, límite de tiempo, trabajo que late y que deja de latir, y cortar todo al salir). Para revisar solo los tipos:
`swiftc -typecheck -target arm64-apple-macos15.0 piezas/host-mac/mac/*.swift`.

## Si venías de la 0.2.0

Nada obligatorio (`pieza.py actualizar <app> host-mac`, sin archivos nuevos). Lo que cambia solo: un enlace https tocado pasa por tu
`abrirEnlace` registrado; `~/<Nombre>` recién creada con `"datos": "visible"` queda 0700; sin menú Archivo, «Cerrar ventana» ⌘W va
en el menú Ventana. Lo que cada app puede borrar:

| App | Se borra | Con |
|---|---|---|
| Alcancía | `AlcanciaApp.estiloVentana` (el `DispatchQueue.main.async` después de `Host.arrancar`) y su `FranjaArrastre`; la copia de `NSWindow Frame Alcancia` → `NSWindow Frame Alcancía`; el `NSOpenPanel` propio de `Cartolas.swift` | `barraTransparente: true`; `nombreVentana: "Alcancia"`; `p.elegirArchivos(extensiones:mensaje:)` |
| Repasa | `RepasaApp.ajustarMenus()` (y sus llamadas en `Task { @MainActor }` y `alCambiarConfig`); `Rutas.prepararCarpeta()` que cerraba `~/Repasa`; el `setAttributes(0o600)` después de `guardarComo` en `Copia.swift` y el «lo grande se dice antes» | `tituloAjustes: "Para adultos…"` + `p.menuApp = { m in [m.nativo("Abrir la carpeta de Repasa") { … }] }` (traduce las dos frases en `en.json`); nada (el host la crea 0700); `guardarArchivo(…, privado: true)` (`.error("tamano")` ≠ `.cancelado`). Su `abrirEnlace` registrado ya cubre también un `<a href>` tocado |
| Corta | Su cambio en `Sources/PiezaHost/Procesador.swift` (`entornoApp` ya viene: `pieza.py actualizar . host-mac --forzar`); `Ventanas.swift` (barra transparente, `CapaSoltar` y `FranjaArrastre`) | lo mismo en `CortaApp.swift` (`Procesador.entornoApp[Host.prefijo + "PROGRAMAS"] = …`); `barraTransparente: true, altoFranja: 12` y `p.alSoltar = { urls in … }` + `p.soltado(nombre)` en `soltarVideo` |
| Graba | En `Vidrio.swift`: el `DispatchQueue.main.async` que esconde la ventana y pasa a `.accessory`, el `.regular` de `Ventana.mostrar()`, el observador de `willCloseNotification` y todo `ajustar()` (vidrio, franja de 38 px, `GRABA_VIDRIO`) | `barraDeMenu: true, abrirAlArrancar: { faltaAlgo }, vidrio: true, altoFranja: 38` (la interfaz lee `window.GRABA_VIDRIO` igual) y, para `procesar.py` declarada, `Procesador.entornoApp[Host.prefijo + "HERRAMIENTAS"]` |
| Minuta | Nada todavía: su ventana sin borde (`VentanaForma`), el panel con su propio WKWebView y los avisos con botones siguen propios | `barraDeMenu: true, abrirAlArrancar: { Perfil.falta }` y `alCrearVentana` le sirven cuando pase a la ventana del host (ver «Pendientes») |
| Esquema | Nada | — |

Pendientes que siguen en las apps (anotados en `docs/catalogo.md`): config con objetos (Alcancía), `Secretos.cuentas()`, avisos
con categoría y botones, ventana y WKWebView propios (Minuta), más de un WKWebView en el puente (Minuta), `Idioma.t` con idiomas
descargados, el tipo `numero` y `carpetaDe` en `datos` (Corta).

### Revisar a mano en el Mac (0.3.0)

`revisar_host_mac.sh` compila todo y prueba `entornoApp`, pero lo que necesita ventana se mira a mano: (1) con `barraDeMenu` la
app parte sin Dock, aparece en él al abrir la ventana y se va al cerrarla; reabrir desde Spotlight la muestra con menús;
(2) `abrirAlArrancar: { false }` no abre ventana ni parpadea; (3) `barraTransparente`: los botones del semáforo sobre la interfaz,
arrastrar la franja mueve la ventana y el doble clic hace zoom; con `vidrio`, el fondo translúcido; (4) soltar un archivo llama
`alSoltar` y la página recibe su `drop` (que `performDragOperation` de `WebPieza` se llame en un WKWebView); (5) un `<a href>`
https pasa por el `abrirEnlace` registrado; (6) sin `m.archivo`, ⌘W cierra la ventana; (7) `tituloAjustes` y `menuApp` en el
idioma elegido; (8) `nombreVentana` recupera el tamaño guardado con el nombre de antes; (9) `guardarArchivo` con `privado: true`
deja 0600 y cancelar da `.cancelado`.

## Si venías de la 0.1.0

`pieza.py actualizar <app> host-mac` trae `Carpeta.swift` y `Sistema.swift` (van solos en `Sources/PiezaHost`: nada que sumar a
`Package.swift`). Lo que cambia al compilar:
- `Puente.llamar` ya no devuelve `Bool`: un `_ = Puente.shared.llamar(…)` o un envoltorio como el `responder` de Esquema siguen
  compilando (se pueden borrar: `guard … else { return p.llamar(…) }` ya compila). Si usabas el `Bool`, `intentarLlamar`.
- `Procesador.lectorProgreso` es `@MainActor` (el bloque de siempre no cambia). `Enchufe.Accion.limite` pasa a `limite(para:)`.
- `esperarLibre` también espera a los scripts que corren (`Procesador.enCurso`): un `guard libre, Procesador.enCurso == 0` queda
  como `guard libre`.
- **Esquema:** puede borrar de `EsquemaApp.swift` `buscarActualizacion`, `actualizar`, `actualizarCuandoPueda`, la revisión de
  `tareas` y `actualizacion` del estado (`p.actualizaciones = .init(…)`, arriba; el texto de «ocupada» pasa a ser el del host);
  `Carpeta.swift` propio por `p.carpeta = CarpetaElegida()` (mismo marcador `carpeta.marcador` y misma clave `carpeta`: nada se
  pierde) y `Vigilante` por `p.vigilante = Vigilante(extensiones: ["md", "mmd"])` con `alCambiar` = volver a listar (lo que hoy hace
  su `revisar`); `abrirArchivo`/`guardarArchivo` se pueden declarar (`vigilar: "lee" | "escribe"`, `maximo`); «Mostrar la carpeta
  en el Finder» con `p.mostrarEnFinder`. `proyecto` con `"limite": {"segun": "orden", "valores": {"documentar": "trabajo", …},
  "otro": 120}` en vez de 3600, y `probarIA` sube solo a 150 (pieza `ia` 0.6.3).

## Pasar una app a esta pieza

Lo que se aprendió al pasar las seis (vale igual para `host-escritorio`):
- La interfaz necesita `window.<App>.menu` aunque no tenga menús propios: el host la llama con `{accion: "ajustes"}` («Ajustes…»)
  y `{accion: "guardar"}` (al cerrar y al salir). Y manda `listo` al cargar: sin él, el host no le responde nada.
- `config` guarda y llama `alCambiarConfig`; **no** manda el estado. Si tu interfaz lo esperaba, mándalo ahí (`p.enviarEstado()`).
- `Config.guardar(x)` filtra por defecto las claves `"interfaz": false` (`desdeInterfaz: true`): lo que guarda la app va con
  `desdeInterfaz: false`, o se pierde en silencio. Un texto de config de más de 2000 caracteres necesita `{"tipo": "texto", "max": N}`.
- Con un idioma que nunca se eligió (válido en la app de antes), `Idioma.elegido` es false y nada corre solo: al migrar, guarda
  `bienvenida: true` si la persona ya tenía todo listo.
- Un `"limite"` por orden: `"otro": 300` (no 120) si las órdenes rápidas recorren repos grandes; algo largo que no es un `Trabajo`
  (p. ej. una orden que llama a `ia.preguntar`) con `"trabajo"` necesita `trabajos.mantener_vivo()`.
- El Llavero: `Secretos` busca sin filtrar por `kSecAttrAccessible`, así lee lo guardado antes; al volver a guardar queda
  `WhenUnlockedThisDeviceOnly`.

En todas: `pieza.py agregar host-mac <app>`, en `Package.swift` el target `PiezaHost` y la dependencia del ejecutable, el `@main`
con `Host.arrancar`, copiar `acciones.json` junto a `app.json` en `herramientas/empaquetar.sh`
(`cp acciones.json "$RES/<id>/"`), y borrar lo que la pieza ya hace. Las acciones que solo corren un script pasan a
`app.json` → `"acciones"` (las arma `pieza.py acciones .`); lo nativo queda con `registrar`.

| App | Se borra | Queda como acción propia | Ojo |
|---|---|---|---|
| Esquema | `Servicios.swift` (Rutas, Archivos, Config, Idioma, Procesador, EnOrden; `LectorProgreso` → pieza «trabajos»), casi todo `Ventana.swift` y `EsquemaApp.swift` (queda el `@main` y los menús con `m.item`/`m.nativo`) | `elegirCarpeta`, `abrirProyecto`, `proyecto` (o declarada: `"*": "pasar"`, `$orden` enum, `inyectar: {carpeta: "carpetaActual"}`, `progreso: "proyectoProgreso"`), `papelera`, `abrirArchivo`/`guardarArchivo` (con `Fila`, por el vigilante), `exportar`, catálogo, actualizaciones | `Carpeta.swift` y `Vigilante` quedan; `probarIA` va solo (pieza `ia`) |
| Graba | `Servicios.swift` (rutas, config, idioma, `Procesador`, `Llavero` → `Secretos(servicio: "Graba")`), el WKWebView de `Ventana.swift`, «Mostrar en el Finder» → `mostrarEnFinder` | Grabar, pausar, recortar, permisos, YouTube, teleprompter, flotantes y barra de menú (`NSStatusItem` en el bloque de `arrancar`) | `datos: "visible"` (~/Graba/.graba) ya lo resuelve el host; su puente de hoy no revisa marco ni origen: con la pieza, sí |
| Minuta | `Rutas`/`Config`/`Procesador` de `MinutaApp.swift`, el WKWebView de `VisorWeb.swift`, el `Llavero` de `Bienvenida.swift` → `Secretos(servicio:)` con el mismo servicio, los avisos inmediatos → `Notificaciones` (los suyos con botones siguen propios) | Casi todo (perfil, universos, gimnasio, avisos, calendario, coach) | **La última:** `Idioma.fuente` = `idioma_ui` de `perfil.json`; el panel de `BarraMenu.swift` es otro WKWebView: queda en la app y llama `Puente.shared.despachar` para lo compartido |
| Corta | `Servicios.swift` (salvo `Modelos`), `Medios.swift` → `registrarMedios("video") { … }` con la misma revisión de `proyecto.json`, gran parte de `Ventana.swift` y `CortaApp.swift`, «Mostrar en el Finder» → `mostrarEnFinder`, sus actualizaciones → `p.actualizaciones` | `elegirVideo`, `soltarVideo`, `exportar`, `elegirMusica`, `elegirClips`, catálogo, `descargarModelo` | `guardarProyecto`/`deshacer`/`limpiar`/`vocabulario` se declaran con `cola: "escritura"`; `transcribir`/`exportar` con `progreso` |
| Repasa | `Servicios.swift` (rutas, config, idioma, `Procesador` con su fila), `EsquemaMaterial` → `registrarMedios("material")`, gran parte de `Ventana.swift` y `RepasaApp.swift` | `elegirMaterial`, `soltarMaterial`, `guardarCopia`/`traerCopia` (`callAsyncJavaScript`) | `guardarProgreso`, `guardarPerfil`, `guardarPruebas` se declaran (`guardar.py`, `cola: "escritura"`); `crearTema`/`explicar` con su `limite` |
| Alcancía | `Servicios.swift` (rutas, config, idioma, `Procesador`: el secreto pasa a `Procesador.conSecreto`, «CREDENCIAL {json}» se lee de `salidaEstandar`), gran parte de `Ventana.swift` y `AlcanciaApp.swift`, el Llavero de `Conexiones.swift`/`Celular.swift` → `Secretos(servicio:)` con sus mismos servicios, la carpeta de la nube → `CarpetaElegida(marcador: <su clave>, clave: nil)`, `Avisos.swift` → `Notificaciones` (+ `avisos: true`) | `elegirCartola`, `conectar`/`sincronizar`/`desconectar` (Llavero), `celular`, `vigilar`, `avisos` | `datos: {"carpeta": "~/Alcancia/.alcancia"}` y `privado: true` ya los respeta el host |

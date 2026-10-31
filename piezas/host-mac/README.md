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
| `Puente.swift` | Ventana, WKWebView, puente con guardas, navegación, `<id>://` para medios, diálogos, menús, apariencia |

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
            p.inyectores["carpetaActual"] = { _ in Carpeta.actual()?.path }          // lo pone el host, nunca la interfaz
            p.estado = { base, listo in var e = base; e["carpeta"] = Carpeta.actual()?.path; listo(e) }
            p.menus = { m in [m.archivo([m.item("Nuevo…", "nuevo", "n"), m.nativo("Abrir carpeta…", "o") { abrirCarpeta() }]),
                              m.edicion(), m.ver([m.item("Acercar", "acercar", "+")])] }
            p.registrar("exportar") { d in
                p.guardarComo(nombre: d["nombre"] as? String ?? "ana", extension: "svg", datos: Data((d["texto"] as? String ?? "").utf8)) { u in
                    p.llamar("exportado", ["ok": u != nil])
                }
            }
            // Pieza «actualizaciones»:
            Actualizaciones.configurar(.init(repo: "ana-app/ana", nombre: "Ana",
                archivoDesarrollo: Host.datos.appendingPathComponent("desarrollo"), variableProgreso: Host.prefijo + "PROGRESO"))
            p.tareas = { Actualizaciones.revisarCadaRato { p.llamar("actualizacionRevisada", $0) } }
            p.registrar("buscarActualizacion") { _ in Actualizaciones.revisar { p.llamar("actualizacionRevisada", $0) } }
            p.registrar("actualizar") { _ in
                p.esperarLibre(segundos: 5) { libre in
                    guard libre, Procesador.enCurso == 0 else {
                        return p.llamar("actualizacionProgreso", ["paso": "error", "codigo": "ocupada", "texto": "Espera a que termine lo que está haciendo y vuelve a intentarlo.", "valores": [String: String](), "total": 3])
                    }
                    Actualizaciones.seguir { p.llamar("actualizacionProgreso", $0) }
                    Actualizaciones.instalar { ok, codigo in if !ok { p.llamar("actualizacionProgreso", Actualizaciones.aviso("error", codigo)) } }
                }
            }
            // Pieza «trabajos» (habilita `progreso` en las acciones declaradas):
            Procesador.lectorProgreso = { aviso in let l = LectorProgreso(prefijo: Host.id, aviso: aviso); return (l.url.path, l.empezar, l.terminar) }
        }
    }
}
```

## API

| | |
|---|---|
| `Host.Configuracion(ancho:alto:minAncho:minAlto:sitio:codigo:global:estadoScript:cerrarSale:recursos:python:)` | Todo opcional. `global`: el objeto `window.<App>` (por defecto el id con mayúscula). `cerrarSale`: cerrar la ventana cierra la app. |
| `Host.arrancar(c) { puente in … }` | Configura, crea la app, deja registrar lo propio, instala menús, aplica la apariencia y abre la ventana. Lo que corre solo (`tareas`) espera al idioma elegido. Al salir, la interfaz guarda y se espera la fila (3 s). |
| `Host.id`, `.nombre`, `.app`, `.datos`, `.recursos`, `.prefijo`, `.version`, `.python`, `prepararDatos()` | Desde `app.json` (`datos`: `sistema`, `visible` o `{"carpeta": "~/…"}`, igual que `nucleo.carpeta_datos()`). |
| `Config.leer()`, `.guardar(cambios, desdeInterfaz:)`, `.texto(clave)`, `.valida(regla, valor)` | `config.json` con las claves de `app.json` (`"interfaz": false` no se cambia desde la interfaz). |
| `Idioma.codigo`, `.elegido`, `.t(_)`, `.f(_, valores)`, `.fuente` | `fuente`: si la app guarda `idioma_ui` en otro lado. |
| `Puente.shared` / `Puente.registrar("accion") { datos in … }` | Una acción propia. Gana sobre las del host y las declaradas (se migra de a poco). |
| `llamar(funcion, json)`, `despachar(accion, datos)` | Hacia la interfaz (solo nombres simples, nada antes de `listo`) y correr una acción. |
| `inyectores`, `estado`, `tareas`, `alCambiarConfig`, `menus`, `antesDeSalir`, `alConfigurarWeb` | Ganchos (ver arriba). `alConfigurarWeb`: otro manejador o preferencia del `WKWebViewConfiguration`. |
| `registrarMedios("video") { ruta in URL? }` | `<id>://video/<ruta>` con rangos. Antes de `mostrar()` (en el bloque de `arrancar`). |
| `elegirCarpeta`, `elegirArchivos(extensiones:varios:)`, `guardarComo(nombre:extension:datos:)`, `papelera(_:)`, `copiar`, `abrirEnlace` | Diálogos y capacidades comunes. |
| `ocupar()`/`soltar()`, `ocupada`, `esperarLibre(segundos:)` | Para no cerrar ni actualizar en medio de algo. |
| `aplicarApariencia()` | `config.tema` (`sistema`/`claro`/`oscuro`, pieza `tema`) → `NSApp.appearance` y la ventana. La llama `config` solo. |
| `Procesador.correrJSON(script, args, limite:)`, `.conEntrada(script, "accion" \| [args], datos, limite:progreso:)`, `.conSecreto(script, args, secreto:)`, `.correr(…)` | `correr` y `conSecreto` dan `Resultado(respuesta, salidaEstandar, porLimite)`. |
| `Fila.agregar { listo in … listo() }` | De a una y en orden. |
| `Enchufe.dentro(base, relativa, extensiones:)` | La guarda de `nucleo.ruta_en`. |

Lo que atiende solo: `listo` (estado), `config` (guarda, rearma los menús en el idioma nuevo, aplica la apariencia y arranca las
tareas), `abrirEnlace` (solo https), `copiar` → `copiado`, y toda acción declarada en `acciones.json` (validar → inyectar → fila →
script con límite → `responde` con `eco` → `despues`; ver [`host-escritorio`](../host-escritorio/README.md#acciones-declaradas-accionesjson)
y [`docs/enchufe.md`](../../docs/enchufe.md#una-acción)). Errores: `{ok: false, codigo: "datos" | "falta" | "limite" | "fallo", texto, valores, error}`.

## Seguridad

- El puente solo atiende el **marco principal**, con origen `file` **y** una página dentro de `ui/` (las apps de hoy solo miraban
  las dos primeras). La ventana nunca navega fuera de `ui/`; un enlace https va al navegador. `<input type=file>` solo para el marco
  principal propio. Si el proceso de la página se cae, se vuelve a cargar.
- `<id>://` sirve solo lo que aprueba el resolvedor de la app (sin `?`, `#`, usuario ni clave).
- Scripts: `<ID>_*` de afuera nunca llegan; lo de la persona en un archivo de entrada dentro de una carpeta temporal 0700;
  secreto por stdin; **límite de tiempo** (SIGTERM al script y a sus descendientes, y SIGKILL 3 s después). Sin `__pycache__`.

## Compilar en el Mac

Swift no compila en Linux: `bash pruebas/swift/revisar_host_mac.sh` (desde Pieza) arma un paquete temporal con la pieza, la
compila con `swift build` y corre una prueba sin ventana (reglas del enchufe, config, procesador con Python: entrada por archivo,
entorno sin `ANA_*`, secreto por stdin y límite de tiempo). Para revisar solo los tipos:
`swiftc -typecheck -target arm64-apple-macos15.0 piezas/host-mac/mac/*.swift`.

## Pasar una app a esta pieza

En todas: `pieza.py agregar host-mac <app>`, en `Package.swift` el target `PiezaHost` y la dependencia del ejecutable, el `@main`
con `Host.arrancar`, copiar `acciones.json` junto a `app.json` en `herramientas/empaquetar.sh`
(`cp acciones.json "$RES/<id>/"`), y borrar lo que la pieza ya hace. Las acciones que solo corren un script pasan a
`app.json` → `"acciones"` (las arma `pieza.py acciones .`); lo nativo queda con `registrar`.

| App | Se borra | Queda como acción propia | Ojo |
|---|---|---|---|
| Esquema | `Servicios.swift` (Rutas, Archivos, Config, Idioma, Procesador, EnOrden; `LectorProgreso` → pieza «trabajos»), casi todo `Ventana.swift` y `EsquemaApp.swift` (queda el `@main` y los menús con `m.item`/`m.nativo`) | `elegirCarpeta`, `abrirProyecto`, `proyecto` (o declarada: `"*": "pasar"`, `$orden` enum, `inyectar: {carpeta: "carpetaActual"}`, `progreso: "proyectoProgreso"`), `papelera`, `abrirArchivo`/`guardarArchivo` (con `Fila`, por el vigilante), `exportar`, catálogo, actualizaciones | `Carpeta.swift` y `Vigilante` quedan; `probarIA` va solo (pieza `ia`) |
| Graba | `Servicios.swift` (rutas, config, idioma, `Procesador`), el WKWebView de `Ventana.swift` | Grabar, pausar, recortar, permisos, YouTube, teleprompter, flotantes y barra de menú (`NSStatusItem` en el bloque de `arrancar`) | `datos: "visible"` (~/Graba/.graba) ya lo resuelve el host; su puente de hoy no revisa marco ni origen: con la pieza, sí |
| Minuta | `Rutas`/`Config`/`Procesador` de `MinutaApp.swift`, el WKWebView de `VisorWeb.swift` | Casi todo (perfil, universos, gimnasio, avisos, calendario, coach) | **La última:** `Idioma.fuente` = `idioma_ui` de `perfil.json`; el panel de `BarraMenu.swift` es otro WKWebView: queda en la app y llama `Puente.shared.despachar` para lo compartido |
| Corta | `Servicios.swift` (salvo `Modelos`), `Medios.swift` → `registrarMedios("video") { … }` con la misma revisión de `proyecto.json`, gran parte de `Ventana.swift` y `CortaApp.swift` | `elegirVideo`, `soltarVideo`, `exportar`, `elegirMusica`, `elegirClips`, catálogo, `descargarModelo` | `guardarProyecto`/`deshacer`/`limpiar`/`vocabulario` se declaran con `cola: "escritura"`; `transcribir`/`exportar` con `progreso` |
| Repasa | `Servicios.swift` (rutas, config, idioma, `Procesador` con su fila), `EsquemaMaterial` → `registrarMedios("material")`, gran parte de `Ventana.swift` y `RepasaApp.swift` | `elegirMaterial`, `soltarMaterial`, `guardarCopia`/`traerCopia` (`callAsyncJavaScript`) | `guardarProgreso`, `guardarPerfil`, `guardarPruebas` se declaran (`guardar.py`, `cola: "escritura"`); `crearTema`/`explicar` con su `limite` |
| Alcancía | `Servicios.swift` (rutas, config, idioma, `Procesador`: el secreto pasa a `Procesador.conSecreto`, «CREDENCIAL {json}» se lee de `salidaEstandar`), gran parte de `Ventana.swift` y `AlcanciaApp.swift` | `elegirCartola`, `conectar`/`sincronizar`/`desconectar` (Llavero), `celular`, `vigilar`, `avisos` | `datos: {"carpeta": "~/Alcancia/.alcancia"}` y `privado: true` ya los respeta el host |

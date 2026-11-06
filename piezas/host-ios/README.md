# Pieza «host-ios» — la app de iPhone (Swift, WKWebView)

La misma interfaz de `ui/` que corre en Mac, Windows y Linux, ahora en el iPhone, sin Capacitor ni dependencias. Sale de
`host-mac` (mismas reglas de `app.json`, `config.json`, idioma y puente) y la usa primero Despeja. La interfaz ve
`host.plataforma === "movil"` (pieza `host-ui`) y se adapta con CSS.

| Archivo | Qué hace |
|---|---|
| `movil/ios/Fuentes/PiezaHost/Host.swift` | `Host.arrancar/configurar`, `app.json` desde `pieza/` dentro de la app (una carpeta `<id>/` chocaría con el ejecutable), datos en Application Support (protegidos), `Config`, `Idioma`, `Archivos`, `Texto` |
| `movil/ios/Fuentes/PiezaHost/Puente.swift` | WKWebView a pantalla completa, puente con guardas, navegación solo dentro de `ui/`, acciones propias, apariencia, ciclo de vida, `Host.Vista` |
| `movil/ios/App.xcodeproj` (generado) | Proyecto sin dependencias: `Fuentes/` se sincroniza sola (Xcode 16+), `recursos.sh` copia `app.json` y `ui/` en cada compilación |
| `movil/ios/Info.plist` (generado) | Los permisos de `app.json → ios.permisos` y `NSBonjourServices` de `ios.bonjour` (`"ana"` → `_ana._tcp`) |
| `movil/ios/Fuentes/Assets.xcassets/AppIcon.appiconset/` (de la app) | El ícono: un `icono.png` de 1024×1024 sin esquinas (iOS las pone) y su `Contents.json`. |
| `movil/ios/Fuentes/App.swift` (una vez) | La entrada de la app (SwiftUI): desde aquí es de la app |

## Uso

`app.json`:
```json
"plataformas": ["mac", "ios"],
"ios": {
  "permisos": [{"clave": "NSPhotoLibraryUsageDescription", "texto": "Para revisar tus fotos y respaldarlas en tu Mac."}],
  "bonjour": ["ana"],
  "equipo": "ABCDE12345"
}
```
`equipo` (opcional) es el Team de Xcode; sin él se elige en «Signing & Capabilities» (y queda como cambio de la app).

`movil/ios/Fuentes/App.swift`:
```swift
@main
struct AnaApp: App {
    init() {
        Host.arrancar(.init(sitio: "https://ana-app.github.io/ana/", codigo: "https://github.com/ana-app/ana")) { p in
            p.registrar("contarFotos") { _ in p.llamar("fotosContadas", ["ok": true, "total": 42]) }
            p.tareas = { /* recién con el idioma elegido: aquí se piden los permisos */ }
        }
    }
    var body: some Scene { WindowGroup { Host.Vista().ignoresSafeArea() } }
}
```

## API

| | |
|---|---|
| `Host.arrancar(.init(global:sitio:codigo:recursos:)) { puente in … }` | Configura una vez (en el `init` de la app) y deja registrar lo propio. |
| `Host.id`, `.nombre`, `.app`, `.datos`, `.recursos`, `.prefijo`, `.version` | Desde `app.json`. `datos`: Application Support/<Nombre>. |
| `Config`, `Idioma`, `Archivos`, `Texto` | Las mismas reglas que `host-mac` y `nucleo`. |
| `Puente.registrar("accion") { datos in }`, `llamar(f, json)`, `intentarLlamar`, `despachar` | Como en Mac. Una acción que nadie atiende responde `error` con `codigo: "falta"`. |
| `estado`, `tareas`, `alCambiarConfig`, `alIrseAlFondo`, `alVolver`, `alConfigurarWeb` | Ganchos. `tareas` corre recién con el idioma elegido: los permisos se piden ahí o cuando la persona toca algo, nunca al abrir. |
| `ocupar()` / `soltar()`, `ocupada` | Algo largo en curso: la pantalla no se apaga y, si sale de la app, iOS da unos segundos para terminar. |
| `guardarTodo()`, `aplicarApariencia()`, `abrirEnlace`, `copiar` | Como en Mac. Al irse al fondo se llama `guardarTodo()` solo. |

Lo que atiende solo: `listo` (estado con `plataforma: "movil"`), `config`, `abrirEnlace` (solo https), `copiar` → `copiado`.

## En el iPhone no hay Python

Las acciones declaradas (`acciones.json`) corren scripts de `bin/` y en el iPhone no hay intérprete: no se atienden aquí. Lo que
la app necesite se hace en Swift (`registrar`) o se le pide al computador (por ejemplo, la app de Mac de la misma app).

## Seguridad

- El puente solo atiende el **marco principal**, con origen `file` y una página dentro de `ui/`. La vista nunca navega fuera
  de `ui/`; un enlace https o una ventana nueva va a Safari por `abrirEnlace`. Si el proceso de la página se cae, se recarga.
- Los datos quedan en Application Support con protección de archivos (hasta el primer desbloqueo); config y JSON igual.
- Los permisos van con su porqué en `app.json` y se piden cuando la app los usa, nunca antes de elegir el idioma.

## Compilar

`bash pruebas/swift/revisar_host_ios.sh` (en un Mac con Xcode) revisa los tipos con el SDK del iPhone. Para una app:
`xcodebuild -project movil/ios/App.xcodeproj -scheme <Nombre> -destination 'generic/platform=iOS Simulator' build`.

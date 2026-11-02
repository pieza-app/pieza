// swift-tools-version:5.10
// Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json y las piezas instaladas
// (pieza.py generar . lo vuelve a armar al agregar una pieza). Si lo cambias, desde ahí es de la app y Pieza ya no lo toca.
import PackageDescription

// {{nombre}} para Mac: la app nativa genérica de Pieza (host-mac) con la interfaz de ui/ y los scripts de bin/ (Python portátil
// adentro). Lo propio de la app va en Sources/{{nombre_ascii}}.
let package = Package(
    name: "{{nombre_ascii}}",
    platforms: [.macOS("15.0")],
    targets: [
        .executableTarget(
            name: "{{nombre_ascii}}",
            dependencies: [{{#si piezas.host-mac}}"PiezaHost", {{/si}}{{#si piezas.actualizaciones}}"PiezaActualizaciones", {{/si}}{{#si piezas.catalogo}}"PiezaCatalogo", {{/si}}{{#si piezas.trabajos}}"PiezaTrabajos", {{/si}}],
            path: "Sources/{{nombre_ascii}}"
        ),
{{#si piezas.host-mac}}
        // Pieza «host-mac» (de Pieza: no se edita a mano): ventana, puente con guardas, config e idioma desde app.json, menús,
        // apariencia, scripts con límite de tiempo y las acciones declaradas en acciones.json.
        .target(name: "PiezaHost", path: "Sources/PiezaHost"),
{{/si}}
{{#si piezas.actualizaciones}}
        // Pieza «actualizaciones»: versiones nuevas solo desde los Releases de {{repo}}, con su .sha256.
        .target(name: "PiezaActualizaciones", path: "Sources/PiezaActualizaciones"),
{{/si}}
{{#si piezas.catalogo}}
        // Pieza «catálogo»: contenido de la comunidad (dominio fijo, sin redirecciones, SHA-256). Se configura con app.json.
        .target(name: "PiezaCatalogo", path: "Sources/PiezaCatalogo"),
{{/si}}
{{#si piezas.trabajos}}
        // Pieza «trabajos»: LectorProgreso, el avance en vivo de los trabajos largos.
        .target(name: "PiezaTrabajos", path: "Sources/PiezaTrabajos"),
{{/si}}
{{#cada app.empaquetado.mac.swift.binarios como b}}
        .binaryTarget(name: "{{b.nombre|nombre}}", url: "{{b.url|https}}", checksum: "{{b.checksum|sha256}}"),
{{/cada}}
{{#cada app.empaquetado.mac.swift.ejecutables como x}}
        .executableTarget(
            name: "{{x.nombre|nombre}}",
            dependencies: {{x.dependencias|json}},
            path: "{{x.ruta|ruta}}"{{#si x.rpath}},
            // Busca sus frameworks dentro de la app (Contents/Frameworks) y junto a sí.
            linkerSettings: [.unsafeFlags(["-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks",
                                           "-Xlinker", "-rpath", "-Xlinker", "@executable_path"])]{{/si}}
        ),
{{/cada}}
    ]
)

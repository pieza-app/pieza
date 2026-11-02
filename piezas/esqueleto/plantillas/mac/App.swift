// {{nombre}} para Mac: la app nativa genérica de Pieza (pieza «host-mac», target PiezaHost) con la interfaz de ui/ y los scripts
// de bin/ (Python portátil adentro). Empezó con «pieza.py crear»: desde ahí es de la app.
// Lo que solo corre un script NO va aquí: se declara en app.json → acciones (pieza.py acciones . arma acciones.json) y el host lo
// atiende solo, igual en Windows y Linux. Aquí va lo nativo propio (p.registrar), los menús y lo que se suma al estado.
import AppKit
import PiezaHost
{{#si piezas.actualizaciones}}
import PiezaActualizaciones
{{/si}}

@main
enum {{nombre_ascii}}App {
    @MainActor static func main() {
        Host.arrancar(.init(sitio: "{{web|https}}", codigo: "https://github.com/{{repo}}", global: "{{nombre_ascii}}")) { p in
{{#si piezas.actualizaciones}}
            // Pieza «actualizaciones»: solo los Releases de {{repo}} ({{nombre_ascii}}-macOS.zip + .sha256). El host atiende
            // buscarActualizacion y actualizar (nunca con algo en curso), revisa al abrir y cada 6 h con el idioma elegido.
            Actualizaciones.configurar(.init(repo: "{{repo}}", nombre: "{{nombre}}",
                archivoDesarrollo: Host.datos.appendingPathComponent("desarrollo"), variableProgreso: Host.prefijo + "PROGRESO"))
            p.actualizaciones = .init(revisar: Actualizaciones.revisar, revisarCadaRato: Actualizaciones.revisarCadaRato,
                seguir: Actualizaciones.seguir, instalar: Actualizaciones.instalar, aviso: Actualizaciones.aviso,
                disponible: { Actualizaciones.disponible })
{{/si}}
            // La app: lo nativo propio, p. ej. p.registrar("exportar") { d in … } (con su caso en simular() de ui/app.js y el mismo
            // en escritorio/src/main.js), y los menús con p.menus (README de «host-mac»).
        }
    }
}

// La app de iPhone de {{nombre}} (pieza «host-ios»): desde aquí es de la app. Lo nativo se registra en `preparar`;
// la interfaz es la misma de ui/ (host-ui, plataforma «movil»).
import SwiftUI

@main
struct {{nombre_ascii}}App: App {
    init() {
        Host.arrancar(.init(sitio: "{{web|https}}", codigo: "https://github.com/{{repo}}")) { p in
            // La app: p.registrar("accion") { datos in … p.llamar("respuesta", […]) }
            p.registrar("hola") { _ in p.llamar("hola", ["ok": true, "plataforma": "movil"]) }
        }
    }

    var body: some Scene {
        WindowGroup { Host.Vista().ignoresSafeArea() }
    }
}

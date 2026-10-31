// Prueba de la pieza «host-mac» (la corre pruebas/swift/revisar_host_mac.sh en un Mac). Sin ventana: reglas del enchufe,
// config, idioma y el procesador con Python de verdad.
import Foundation
import PiezaHost

var fallas: [String] = []
func revisar(_ ok: Bool, _ que: String) { if !ok { fallas.append(que) } }

let app = URL(fileURLWithPath: ProcessInfo.processInfo.environment["REVISAR_APP"] ?? "")
let datos = FileManager.default.temporaryDirectory.appendingPathComponent("ana-datos-\(UUID().uuidString)")

MainActor.assumeIsolated {
    revisar(Host.configurar(.init(recursos: app, python: URL(fileURLWithPath: "/usr/bin/python3"))), "configurar con app.json")
    revisar(Host.id == "ana" && Host.nombre == "Ana" && Host.prefijo == "ANA_", "id, nombre y prefijo")
    revisar(Host.datos.path.hasSuffix("Library/Application Support/Ana"), "carpeta de datos «sistema»")

    // Reglas de una acción (las mismas que pieza.py y enchufe.js).
    let (acciones, errores) = Enchufe.cargar(app)
    revisar(acciones["probarIA"] != nil && acciones["mala"] == nil, "la acción con texto como argumento no se carga")
    revisar(errores.contains { $0.contains("solo puede ser un campo enum o entero") }, "el error lo dice")
    revisar(!Enchufe.errores("x", ["script": "a.py", "limite": 0]).isEmpty, "límite obligatorio")
    revisar(Enchufe.errores("x", ["script": "a.py", "limite": 5, "args": ["$n"], "datos": ["n": ["tipo": "entero"]]]).isEmpty, "entero en args")
    if let a = acciones["probarIA"] {
        if case .ok(let e) = Enchufe.validar(a, ["ia": "claude", "otro": 1]) { revisar(e.count == 1, "lo no declarado no pasa") } else { revisar(false, "validar ok") }
        if case .falla(let campo, _) = Enchufe.validar(a, ["ia": "otra"]) { revisar(campo == "ia", "enum malo") } else { revisar(false, "enum malo") }
    }
    let regla: [String: Any] = ["tipo": "entero", "min": 1, "max": 3]
    revisar(Enchufe.valor(regla, NSNumber(value: true)) == nil, "un booleano no es un entero")
    revisar(Enchufe.valor(regla, 2) != nil && Enchufe.valor(regla, 4) == nil, "entero con rango")
    revisar(Enchufe.valor(["tipo": "rutaRelativa", "extensiones": [".md"]], "../a.md") == nil, "ruta con ..")
    revisar(Enchufe.valor(["tipo": "rutaRelativa", "extensiones": [".md"]], "a/b.md") != nil, "ruta buena")
    revisar(Enchufe.dentro(app, "../x.md") == nil && Enchufe.dentro(app, "bin/eco.py") != nil, "dentro()")

    // Config con las reglas de app.json.
    revisar(Config.valida(["es", "en"], "en") && !Config.valida(["es", "en"], "fr"), "config: lista")
    revisar(Config.valida("bool", NSNumber(value: true)) && !Config.valida("bool", NSNumber(value: 1)), "config: bool")
    revisar(Config.limpiar(["tema": "morado", "idioma_ui": "en", "otra": 1]).count == 1, "config: solo lo de app.json")
}

// El procesador: entrada por archivo, entorno sin ANA_*, secreto por stdin y límite de tiempo.
let espera = DispatchSemaphore(value: 0)
var pendientes = 3
func listo() { pendientes -= 1; if pendientes == 0 { espera.signal() } }
Task { @MainActor in
    Procesador.conEntrada("eco.py", "probar", ["texto": "--rm -rf ~"]) { r in
        revisar((r["argv"] as? [String] ?? []).allSatisfy { !$0.contains("rm -rf") }, "el texto nunca como argumento")
        revisar((r["entrada"] as? [String: Any])?["texto"] as? String == "--rm -rf ~", "el texto llega en la entrada")
        revisar(r["ajena"] is NSNull || r["ajena"] == nil, "sin variables ANA_* de afuera")
        listo()
    }
    Procesador.conSecreto("eco.py", ["secreto"], secreto: "llave-123") { r in
        revisar(r.respuesta["stdin"] as? String == "llave-123", "secreto por stdin")
        listo()
    }
    Procesador.correrJSON("eco.py", ["dormir"], limite: 1) { r in
        revisar(r["codigo"] as? String == "limite", "límite de tiempo")
        listo()
    }
}
while espera.wait(timeout: .now() + 0.05) == .timedOut { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
try? FileManager.default.removeItem(at: datos)
if fallas.isEmpty { print("host-mac: todo bien") } else { print("host-mac falló:\n  " + fallas.joined(separator: "\n  ")); exit(1) }

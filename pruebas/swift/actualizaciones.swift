// Prueba de la pieza «actualizaciones» en Swift (la corre pruebas/swift/revisar_actualizaciones.sh en un Mac): la firma Ed25519
// (un vector hecho en Node, para que Swift y Electron acepten lo mismo; firmas buenas y malas; otra versión, otra app, otra
// llave), la huella, la configuración con llaves y app.json y, si el guion la armó, la firma que hizo herramientas/firmar.
import CryptoKit
import Foundation
import PiezaActualizaciones

var fallas: [String] = []
func revisar(_ ok: Bool, _ que: String) { if !ok { fallas.append(que) } }
let A = Actualizaciones.self

// El mismo vector que pruebas/piezas_js.mjs (Node, semilla fija).
let pubNode = "6kpsY+KcUgq+9VB7Ey7F+ZVHdq6+vnuSQh7qaRRG0iw="
let firmaNode = "t3yMF0kMlDExph/CnhIKW5Eqqxw/8SqF/WEDb50UKpI6aittVCziTk+qlUI+fd/E7ReUMlAE2JiOcMJkno3uCQ=="
let huella = String(repeating: "ab", count: 32)
let msg = A.mensajeFirmado(id: "ana", version: "0.2.0", sha256: huella.uppercased())
revisar(msg == "ana-actualizacion|0.2.0|" + huella, "mensaje firmado")
revisar(A.firmaValida(firmaNode, mensaje: msg, llaves: [pubNode]), "Swift acepta la firma hecha en Node")
revisar(A.firmaValida(firmaNode + "\n", mensaje: msg, llaves: ["7kpsY+KcUgq+9VB7Ey7F+ZVHdq6+vnuSQh7qaRRG0iw=", pubNode]), "cualquiera de las llaves")
revisar(!A.firmaValida(firmaNode, mensaje: msg.replacingOccurrences(of: "0.2.0", with: "0.2.1"), llaves: [pubNode]), "otra versión")
revisar(!A.firmaValida("no", mensaje: msg, llaves: [pubNode]), "firma que no es base64")
revisar(A.llavePublica("corta") == nil && A.llavePublica(pubNode) != nil, "llavePublica")

// Una llave nueva, como la de herramientas/firmar.
let k = Curve25519.Signing.PrivateKey(), otra = Curve25519.Signing.PrivateKey()
let pub = k.publicKey.rawRepresentation.base64EncodedString(), pubOtra = otra.publicKey.rawRepresentation.base64EncodedString()
func firmar(_ m: String, _ llave: Curve25519.Signing.PrivateKey = k) -> String { try! llave.signature(for: Data(m.utf8)).base64EncodedString() }
let buena = firmar(A.mensajeFirmado(id: "ana", version: "0.2.0", sha256: huella))
func descarga(firma: String? = buena, version: String = "0.2.0", instalada: String = "0.1.0", id: String = "ana", llaves: [String] = [pub],
              huellaArchivo: String = huella) -> String? {
    A.revisarDescarga(huellaArchivo: huellaArchivo, textoHuella: huella.uppercased() + "  Ana-macOS.zip\n", firma: firma, version: version,
                      instalada: instalada, id: id, llaves: llaves)
}
revisar(descarga() == nil, "firma buena")
revisar(descarga(llaves: [pubOtra, pub]) == nil, "con dos llaves, la segunda")
revisar(descarga(firma: nil) == "firma", "sin firma")
revisar(descarga(firma: firmar(A.mensajeFirmado(id: "ana", version: "0.2.0", sha256: huella), otra)) == "firma", "firma de otra llave")
revisar(descarga(version: "0.3.0") == "firma", "la versión del Release no es la firmada")
revisar(descarga(instalada: "0.2.0") == "firma", "no más nueva que la instalada")
revisar(descarga(instalada: "0.10.0") == "firma", "más vieja que la instalada")
revisar(descarga(id: "pepe") == "firma", "firma de otra app")
revisar(descarga(llaves: []) == "firma", "sin llaves no hay firma que valga")
revisar(descarga(huellaArchivo: String(repeating: "cd", count: 32)) == "errorBajar", "huella distinta")
revisar(A.esMayor("0.10.0", "0.9.3") && !A.esMayor("1.0.0-beta", "0.1.0") && !A.esMayor("0.2.0", "0.2.0"), "esMayor")
revisar(A.leerHuella("no") == nil && A.leerHuella(huella.uppercased() + "  x") == huella, "leerHuella")

let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("act-\(UUID().uuidString)")
try? FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
let abc = tmp.appendingPathComponent("abc")
try? "abc".write(to: abc, atomically: true, encoding: .utf8)
revisar(A.sha256(de: abc) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 de un archivo")

MainActor.assumeIsolated {
    revisar(A.textos["firma"] != nil && A.aviso("error", "firma")["texto"] as? String == A.textos["firma"], "el texto de «firma»")
    revisar(A.configurar(.init(repo: "ana-app/ana", nombre: "Ana")), "sin llaves, como antes")
    revisar(A.configurar(.init(repo: "ana-app/ana", nombre: "Ana", llaves: [pub, pubOtra])), "con dos llaves")
    revisar(!A.configurar(.init(repo: "ana-app/ana", nombre: "Ana", llaves: ["mala"])), "una llave mala no se acepta")
    revisar(!A.configurar(.init(repo: "ana-app/ana", nombre: "Ana", llaves: [pub, pub, pub])), "hasta 2 llaves")
    let app = tmp.appendingPathComponent("app.json")
    func conApp(_ j: String) -> Actualizaciones.Config {
        try? j.write(to: app, atomically: true, encoding: .utf8)
        return .init(repo: "ana-app/ana", nombre: "Ána Café", appJSON: app)
    }
    let c = conApp(#"{"id": "ana", "actualizaciones": {"llaves": ["\#(pub)"]}}"#)
    revisar(c.id == "ana" && c.llaves == [pub] && A.configurar(c), "llaves e id de app.json")
    let sin = conApp(#"{"id": "ana"}"#)
    revisar(sin.llaves.isEmpty && sin.id == "ana", "app.json sin llaves")
    revisar(Actualizaciones.Config(repo: "ana-app/ana", nombre: "Ána Café").id == "anacafe", "sin app.json, el id es la base")
    revisar(!A.configurar(conApp(#"{"id": "ana", "actualizaciones": {"llaves": "x"}}"#)), "llaves mal escritas en app.json: sin actualizaciones")
    revisar(!A.configurar(conApp(#"{"id": "ana", "actualizaciones": []}"#)), "sección mal escrita en app.json")
    revisar(conApp(#"{"id": "ana", "actualizaciones": {"llaves": ["\#(pubOtra)"]}}"#).llaves == [pubOtra], "lee la de app.json")
    revisar(Actualizaciones.Config(repo: "ana-app/ana", nombre: "Ana", llaves: [pub], appJSON: app).llaves == [pub], "las dadas ganan")
}

// Lo que firmó herramientas/firmar/firmar.swift (si revisar_actualizaciones.sh pudo usar un llavero de prueba).
let env = ProcessInfo.processInfo.environment
if let p = env["FIRMA_PUBLICA"], let ruta = env["FIRMA_ARCHIVO"], let id = env["FIRMA_ID"] {
    let u = URL(fileURLWithPath: ruta)
    let s = (try? String(contentsOf: URL(fileURLWithPath: ruta + ".sig"), encoding: .utf8)) ?? ""
    let h = A.sha256(de: u) ?? ""
    revisar(A.revisarDescarga(huellaArchivo: h, textoHuella: h, firma: s, version: "0.2.0", instalada: "0.1.0", id: id, llaves: [p]) == nil,
            "la pieza acepta lo que firma herramientas/firmar")
    revisar(A.revisarDescarga(huellaArchivo: h, textoHuella: h, firma: s, version: "0.2.1", instalada: "0.1.0", id: id, llaves: [p]) == "firma",
            "y no para otra versión")
    print("actualizaciones: probé la firma de herramientas/firmar")
}

try? FileManager.default.removeItem(at: tmp)
if fallas.isEmpty { print("actualizaciones: todo bien") } else { print("actualizaciones falló:\n  " + fallas.joined(separator: "\n  ")); exit(1) }

// Firma de las actualizaciones (pieza «actualizaciones»): la llave Ed25519 de cada app vive en el Llavero de ESTE Mac (el de
// quien mantiene la app), nunca en GitHub ni en un secreto de Actions. Así, si alguien toma la cuenta de GitHub, la llave no cae
// con ella y no puede publicar una versión que las apps acepten. Solo biblioteca del sistema (Foundation, CryptoKit, Security).
//
//   swift herramientas/firmar/firmar.swift crear <id>                     Crea la llave (si ya hay una, no la pisa) y dice la pública.
//   swift herramientas/firmar/firmar.swift publica <id>                   La llave pública (para app.json → actualizaciones.llaves).
//   swift herramientas/firmar/firmar.swift respaldo <id>                  La privada en base64, UNA vez, para guardarla fuera de línea.
//   swift herramientas/firmar/firmar.swift importar <id>                  Vuelve a poner una privada de un respaldo (por la entrada estándar).
//   swift herramientas/firmar/firmar.swift firmar <id> <versión> <archivo>     Deja <archivo>.sig (base64).
//   swift herramientas/firmar/firmar.swift verificar <id> <versión> <archivo> [<llave pública>]
//
// Lo firmado es exactamente `<id>-actualizacion|<versión sin v>|<sha256 del archivo en minúsculas>` (lo mismo que revisan
// Actualizaciones.swift y actualizaciones.js). <id> es el «id» de app.json. Lo usa herramientas/firmar_release.sh.
// La llave queda como contraseña genérica del llavero de inicio de sesión (servicio «Pieza · firma de actualizaciones», cuenta
// <id>): no se sincroniza con iCloud, y macOS puede pedir permiso para leerla (bien: así sabes cuándo se usa).
import CryptoKit
import Foundation
import Security

let servicio = "Pieza · firma de actualizaciones"

func salir(_ texto: String, _ codigo: Int32 = 1) -> Never {
    FileHandle.standardError.write(Data((texto + "\n").utf8))
    exit(codigo)
}

func coincide(_ s: String, _ patron: String) -> Bool { s.range(of: patron, options: .regularExpression) != nil }

func idValido(_ id: String) -> String {
    guard coincide(id, #"^[a-z0-9][a-z0-9._-]{0,60}$"#) else { salir("«\(id)» no es un id de app (el «id» de app.json: minúsculas y números).") }
    return id
}

func versionValida(_ v: String) -> String {
    let s = v.hasPrefix("v") ? String(v.dropFirst()) : v
    guard coincide(s, #"^\d{1,6}(\.\d{1,6}){0,3}$"#) else { salir("«\(v)» no es una versión (X.Y.Z).") }
    return s
}

func consulta(_ id: String) -> [String: Any] {
    [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: servicio, kSecAttrAccount as String: id]
}

func existe(_ id: String) -> Bool {
    SecItemCopyMatching(consulta(id) as CFDictionary, nil) == errSecSuccess
}

func privada(_ id: String) -> Curve25519.Signing.PrivateKey {
    var q = consulta(id)
    q[kSecReturnData as String] = true
    q[kSecMatchLimit as String] = kSecMatchLimitOne
    var r: CFTypeRef?
    let s = SecItemCopyMatching(q as CFDictionary, &r)
    guard s == errSecSuccess, let d = r as? Data, let k = try? Curve25519.Signing.PrivateKey(rawRepresentation: d) else {
        salir("No encontré la llave de «\(id)» en el Llavero (código \(s)). ¿La creaste en este Mac (crear) o la importaste de tu respaldo (importar)?")
    }
    return k
}

func guardar(_ id: String, _ k: Curve25519.Signing.PrivateKey) {
    var q = consulta(id)
    q[kSecValueData as String] = k.rawRepresentation
    q[kSecAttrLabel as String] = "\(servicio) (\(id))"
    q[kSecAttrDescription as String] = "Llave privada Ed25519 de las actualizaciones de \(id)"
    q[kSecAttrSynchronizable as String] = kCFBooleanFalse
    let s = SecItemAdd(q as CFDictionary, nil)
    guard s == errSecSuccess else { salir("No pude guardar la llave en el Llavero (código \(s)).") }
}

func publica(_ k: Curve25519.Signing.PrivateKey) -> String { k.publicKey.rawRepresentation.base64EncodedString() }

func sha256(_ ruta: String) -> String {
    guard let f = FileHandle(forReadingAtPath: ruta) else { salir("No puedo leer «\(ruta)».") }
    defer { try? f.close() }
    var h = SHA256()
    do {
        while let d = try f.read(upToCount: 1 << 20), !d.isEmpty { h.update(data: d) }
    } catch { salir("No pude leer «\(ruta)» entero.") }
    return h.finalize().map { String(format: "%02x", $0) }.joined()
}

func mensaje(_ id: String, _ version: String, _ huella: String) -> String { "\(id)-actualizacion|\(version)|\(huella)" }

let a = Array(CommandLine.arguments.dropFirst())
let uso = """
Uso: swift herramientas/firmar/firmar.swift crear|publica|respaldo|importar <id>
     swift herramientas/firmar/firmar.swift firmar <id> <versión> <archivo>
     swift herramientas/firmar/firmar.swift verificar <id> <versión> <archivo> [<llave pública en base64>]
"""
guard let orden = a.first else { salir(uso, 2) }

switch (orden, a.count) {
case ("crear", 2):
    let id = idValido(a[1])
    if existe(id) { salir("Ya hay una llave de «\(id)» en este Llavero: no la piso. Su pública: swift herramientas/firmar/firmar.swift publica \(id)") }
    let k = Curve25519.Signing.PrivateKey()
    guardar(id, k)
    print(publica(k))
    FileHandle.standardError.write(Data("""

    Listo: la llave privada de «\(id)» quedó en tu Llavero (servicio «\(servicio)»). Arriba está la PÚBLICA:
      1. Pégala en app.json de la app:  "actualizaciones": {"llaves": ["\(publica(k))"]}
      2. Guarda un respaldo de la privada FUERA de línea (papel, una memoria USB en un cajón):
         swift herramientas/firmar/firmar.swift respaldo \(id)
         Sin la privada no podrás publicar versiones que las apps ya instaladas acepten.

    """.utf8))
case ("publica", 2):
    print(publica(privada(idValido(a[1]))))
case ("respaldo", 2):
    let id = idValido(a[1])
    let k = privada(id)
    FileHandle.standardError.write(Data("""
    ⚠️  Esto muestra la llave PRIVADA de «\(id)». Quien la tenga puede publicar versiones que las apps aceptan.
       Cópiala solo a un respaldo fuera de línea (papel o una memoria USB guardada), nunca a GitHub, un chat, un correo ni la nube.
    Escribe «\(id)» para mostrarla: 
    """.utf8))
    guard readLine()?.trimmingCharacters(in: .whitespaces) == id else { salir("No la muestro.") }
    print(k.rawRepresentation.base64EncodedString())
case ("importar", 2):
    let id = idValido(a[1])
    if existe(id) { salir("Ya hay una llave de «\(id)» en este Llavero: no la piso. Bórrala antes en Acceso a Llaveros si de verdad quieres cambiarla.") }
    FileHandle.standardError.write(Data("Pega la llave privada (base64) y Enter: ".utf8))
    guard let t = readLine(), let d = Data(base64Encoded: t.trimmingCharacters(in: .whitespacesAndNewlines)), d.count == 32,
          let k = try? Curve25519.Signing.PrivateKey(rawRepresentation: d) else { salir("Eso no es una llave privada Ed25519 (32 bytes en base64).") }
    guardar(id, k)
    print(publica(k))
case ("firmar", 4):
    let id = idValido(a[1]), version = versionValida(a[2]), ruta = a[3]
    let k = privada(id)
    let m = mensaje(id, version, sha256(ruta))
    guard let firma = try? k.signature(for: Data(m.utf8)), k.publicKey.isValidSignature(firma, for: Data(m.utf8)) else { salir("No pude firmar.") }
    do { try (firma.base64EncodedString() + "\n").write(toFile: ruta + ".sig", atomically: true, encoding: .utf8) } catch { salir("No pude escribir «\(ruta).sig».") }
    print("Firmado: \(m)")
case ("verificar", 4), ("verificar", 5):
    let id = idValido(a[1]), version = versionValida(a[2]), ruta = a[3]
    let llave: Curve25519.Signing.PublicKey
    if a.count == 5 {
        guard let d = Data(base64Encoded: a[4]), d.count == 32, let p = try? Curve25519.Signing.PublicKey(rawRepresentation: d) else { salir("Esa no es una llave pública Ed25519.") }
        llave = p
    } else {
        llave = privada(id).publicKey
    }
    let m = mensaje(id, version, sha256(ruta))
    guard let t = try? String(contentsOfFile: ruta + ".sig", encoding: .utf8),
          let firma = Data(base64Encoded: t.trimmingCharacters(in: .whitespacesAndNewlines)), llave.isValidSignature(firma, for: Data(m.utf8)) else {
        salir("La firma de «\(ruta)» NO es válida para \(m).")
    }
    print("Firma válida: \(m)")
default:
    salir(uso, 2)
}

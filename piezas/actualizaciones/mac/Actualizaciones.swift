// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.
import CryptoKit
import Foundation

/// Pieza «actualizaciones» (Mac). Versiones nuevas dentro de la app (nunca una alerta del sistema): se revisa al abrir y cada
/// 6 horas. Instalación normal: el Release de GitHub (`<Base>-macOS.zip` + `.sha256`). Instalación de desarrollo (la armó
/// build.sh desde un checkout de git y dejó su ruta en `Config.archivoDesarrollo`, fuera de la app para no romper su firma):
/// git pull + herramientas/empaquetar.sh. Los datos de la persona viven fuera de la app: actualizar no borra nada.
///
/// Va en su propio target de SwiftPM (`PiezaActualizaciones`): nada de la app adentro. Repo, nombre y rutas llegan en `Config`;
/// lo que hay que mostrar se devuelve como diccionarios para `window.<App>.*` con el texto en español y sus valores
/// (la interfaz los traduce con T). Ningún texto traducido ni nada variable entra a un guion sin `comillas()`.
///
/// **Firma** (opcional, desde 0.4): con `llaves` (públicas Ed25519, en `Config` o en `app.json` → `actualizaciones.llaves`) un
/// Release vale solo si trae `<Base>-macOS.zip.sig`: la firma de `<id>-actualizacion|<versión>|<sha256>` con la llave privada que
/// vive en el Mac de quien mantiene la app (nunca en GitHub). Así alguien que tome la cuenta de GitHub no puede publicar una
/// versión falsa ni volver a una vieja. Con firma, la app baja zip, .sha256 y .sig ella misma (URLSession, redirecciones solo por
/// https), lo revisa todo y recién ahí escribe el guion, que instala el zip ya revisado (no vuelve a bajar nada).
@MainActor
public enum Actualizaciones {
    public struct Config {
        /// "dueño/repo" en GitHub.
        public var repo: String
        /// Nombre visible ("Matías Café"): solo para los textos.
        public var nombre: String
        /// Nombre de los archivos ("MatiasCafe" → MatiasCafe-macOS.zip, MatiasCafe.app).
        public var base: String
        /// Archivo donde build.sh deja la ruta del checkout de desarrollo (o nil).
        public var archivoDesarrollo: URL?
        /// Variable que empaquetar.sh lee para escribir su avance ("MATIASCAFE_PROGRESO"), o nil.
        public var variableProgreso: String?
        /// Llaves públicas Ed25519 (32 bytes en base64; hasta 2, para poder cambiar de llave). Vacío: sin firma, como antes de 0.4.
        public var llaves: [String]
        /// Lo que va antes de «-actualizacion» en el mensaje firmado: el `id` de app.json (o `base` en minúsculas).
        public var id: String

        /// `appJSON`: el app.json de dentro de la app (`Host.recursos.appendingPathComponent("app.json")`); de ahí salen `id` y
        /// `actualizaciones.llaves` si no se dan aquí. Una sección `actualizaciones` mal escrita deja una llave inválida: `configurar`
        /// no la acepta (mejor sin actualizaciones que sin revisar la firma).
        public init(repo: String, nombre: String, base: String? = nil, archivoDesarrollo: URL? = nil, variableProgreso: String? = nil,
                    llaves: [String] = [], id: String? = nil, appJSON: URL? = nil) {
            self.repo = repo
            self.nombre = nombre
            self.base = base ?? Actualizaciones.baseDe(nombre)
            self.archivoDesarrollo = archivoDesarrollo
            self.variableProgreso = variableProgreso
            var deApp: [String: Any] = [:]
            if let appJSON, let d = try? Data(contentsOf: appJSON), d.count < 1_048_576,
               let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any] { deApp = j }
            self.id = id ?? (deApp["id"] as? String) ?? self.base.lowercased()
            if !llaves.isEmpty {
                self.llaves = llaves
            } else if let sec = deApp["actualizaciones"] {
                if let s = sec as? [String: Any], s["llaves"] == nil { self.llaves = [] }
                else if let s = sec as? [String: Any], let l = s["llaves"] as? [String] { self.llaves = l }
                else { self.llaves = ["(app.json → actualizaciones.llaves no es una lista de textos)"] }
            } else {
                self.llaves = []
            }
        }
    }

    /// Los textos van en español y con marcadores: son las claves de ui/idiomas.
    public static let textos: [String: String] = [
        "version": "Versión {v}",
        "bajando": "Descargando la versión nueva…",
        "preparando": "Preparando la versión nueva…",
        "instalando": "Instalando: {app} se cerrará y volverá a abrirse sola",
        "errorBajar": "No pude descargar la versión nueva. Revisa tu conexión e intenta de nuevo.",
        "errorArmar": "No pude preparar la versión nueva. {app} sigue igual que antes; intenta de nuevo más tarde.",
        "sinDescarga": "No encontré la descarga de la versión nueva.",
        "firma": "No pude comprobar que la versión nueva sea de {app}: le falta la firma o no es válida. {app} sigue igual que antes.",
    ]

    private static var config: Config?
    private static var zip: URL?, huella: URL?, firma: URL?, versionNueva: String?
    public private(set) static var disponible: [String: Any] = ["hay": false]

    /// Guarda la configuración si es válida (repo "dueño/repo", base y variable sin caracteres raros).
    @discardableResult
    public static func configurar(_ c: Config) -> Bool {
        let repoOk = c.repo.range(of: #"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$"#, options: .regularExpression) != nil
        let baseOk = c.base.range(of: #"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$"#, options: .regularExpression) != nil
        let varOk = c.variableProgreso.map { $0.range(of: #"^[A-Z][A-Z0-9_]{0,40}$"#, options: .regularExpression) != nil } ?? true
        let idOk = c.id.range(of: #"^[a-z0-9][a-z0-9._-]{0,60}$"#, options: .regularExpression) != nil
        let llavesOk = c.llaves.count <= 2 && c.llaves.allSatisfy { llavePublica($0) != nil }
        guard repoOk, baseOk, varOk, idOk, llavesOk, !c.nombre.isEmpty else { return false }
        config = c
        return true
    }

    // MARK: Firma (Ed25519)

    /// Una llave pública Ed25519 en base64 (32 bytes), o nil.
    nonisolated public static func llavePublica(_ base64: String) -> Curve25519.Signing.PublicKey? {
        guard let d = Data(base64Encoded: base64.trimmingCharacters(in: .whitespacesAndNewlines)), d.count == 32 else { return nil }
        return try? Curve25519.Signing.PublicKey(rawRepresentation: d)
    }

    /// Lo que se firma: `<id>-actualizacion|<versión sin v>|<sha256 en minúsculas>` (lo mismo que herramientas/firmar de Pieza).
    nonisolated public static func mensajeFirmado(id: String, version: String, sha256: String) -> String {
        "\(id)-actualizacion|\(version)|\(sha256.lowercased())"
    }

    /// ¿La firma (base64, 64 bytes) es de alguna de las llaves?
    nonisolated public static func firmaValida(_ firma: String, mensaje: String, llaves: [String]) -> Bool {
        guard let f = Data(base64Encoded: firma.trimmingCharacters(in: .whitespacesAndNewlines)), f.count == 64 else { return false }
        let m = Data(mensaje.utf8)
        return llaves.contains { llavePublica($0)?.isValidSignature(f, for: m) == true }
    }

    /// El primer campo de un .sha256 («<64 hex>  archivo»), en minúsculas; nil si no es una huella.
    nonisolated public static func leerHuella(_ texto: String) -> String? {
        let h = texto.split(whereSeparator: { $0 == " " || $0 == "\t" || $0 == "\n" || $0 == "\r" }).first.map { String($0).lowercased() } ?? ""
        return h.range(of: #"^[0-9a-f]{64}$"#, options: .regularExpression) != nil ? h : nil
    }

    /// ¿`a` es una versión de números más nueva que `b`? («0.10.0» > «0.9.3»; lo que no es versión nunca es más nuevo).
    nonisolated public static func esMayor(_ a: String, _ b: String) -> Bool {
        a.range(of: #"^\d{1,6}(\.\d{1,6}){0,3}$"#, options: .regularExpression) != nil && a.compare(b, options: .numeric) == .orderedDescending
    }

    /// El SHA-256 de un archivo (de a 1 MB), en hexadecimal minúsculo.
    nonisolated public static func sha256(de u: URL) -> String? {
        guard let f = try? FileHandle(forReadingFrom: u) else { return nil }
        defer { try? f.close() }
        var h = SHA256()
        do {
            while let d = try f.read(upToCount: 1 << 20), !d.isEmpty { h.update(data: d) }
        } catch { return nil }
        return h.finalize().map { String(format: "%02x", $0) }.joined()
    }

    /// Revisa una descarga con firma. nil si todo calza; si no, el código del error (una clave de `textos`): la huella publicada
    /// tiene que ser la del archivo, la versión firmada la del Release y más nueva que la instalada, y la firma de una de las llaves.
    nonisolated public static func revisarDescarga(huellaArchivo: String, textoHuella: String, firma: String?, version: String,
                                                   instalada: String, id: String, llaves: [String]) -> String? {
        guard let esperada = leerHuella(textoHuella), esperada == huellaArchivo.lowercased() else { return "errorBajar" }
        guard !llaves.isEmpty, esMayor(version, instalada), let firma,
              firmaValida(firma, mensaje: mensajeFirmado(id: id, version: version, sha256: esperada), llaves: llaves) else { return "firma" }
        return nil
    }

    /// Sin tildes ni espacios: "Matías Café" → "MatiasCafe".
    nonisolated public static func baseDe(_ nombre: String) -> String {
        nombre.folding(options: .diacriticInsensitive, locale: nil).filter { $0.isASCII && ($0.isLetter || $0.isNumber || "._-".contains($0)) }
    }

    /// Solo se descarga desde los Releases de ESTE repo en github.com. GitHub después redirige a su almacenamiento
    /// (objects.githubusercontent.com / release-assets.githubusercontent.com): curl sigue esa redirección solo por https
    /// (`--proto-redir '=https'`) y lo que llega se acepta únicamente si su SHA-256 es el del .sha256 publicado.
    nonisolated public static func esDescargaNuestra(_ u: URL, repo: String) -> Bool {
        u.scheme == "https" && u.host == "github.com" && u.port == nil && u.user == nil && u.password == nil
            && u.query == nil && u.fragment == nil && u.path.hasPrefix("/\(repo)/releases/download/") && !u.path.contains("..")
    }

    /// Texto entre comillas simples para bash: nada de lo que va adentro (rutas, URL, nombres) se interpreta como código.
    nonisolated public static func comillas(_ s: String) -> String { "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'" }

    /// Checkout de desarrollo desde el que se compiló esta app (o nil si es una instalación normal).
    public static var checkout: URL? {
        guard let archivo = config?.archivoDesarrollo,
              let t = try? String(contentsOf: archivo, encoding: .utf8) else { return nil }
        let u = URL(fileURLWithPath: t.trimmingCharacters(in: .whitespacesAndNewlines))
        return FileManager.default.fileExists(atPath: u.appendingPathComponent(".git").path) ? u : nil
    }

    /// La versión de esta copia (CFBundleShortVersionString): para el estado de la app o un User-Agent.
    public static var version: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0" }

    private static func git(_ args: [String], en: URL, _ fin: @escaping @MainActor (Bool, String) -> Void) {
        let p = Process(), salida = Pipe()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/git")
        p.arguments = args
        p.currentDirectoryURL = en
        p.standardOutput = salida
        p.standardError = FileHandle.nullDevice
        p.terminationHandler = { pr in
            let t = String(data: salida.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            let ok = pr.terminationStatus == 0
            Task { @MainActor in fin(ok, t) }
        }
        do { try p.run() } catch { fin(false, "") }
    }

    /// Revisa si hay versión nueva: ["hay", "version", "notas", "sinConexion", "texto", "valores", "desarrollo"].
    public static func revisar(_ fin: @escaping @MainActor ([String: Any]) -> Void) {
        let terminar: @MainActor (Bool, Bool, String, String) -> Void = { hay, sinConexion, v, notas in
            // `disponible` (lo que la app manda en su estado) tiene la misma forma que la respuesta, sin «sinConexion».
            // `desarrollo`: instalación de desarrollo (sin versión; `notas` son los commits nuevos de origin/main).
            disponible = ["hay": hay, "version": hay ? v : "", "notas": hay ? notas : "",
                          "texto": hay && !v.isEmpty ? textos["version"]! : "", "valores": ["v": hay ? v : ""],
                          "desarrollo": checkout != nil]
            var r = disponible
            r["sinConexion"] = sinConexion
            fin(r)
        }
        guard let c = config else { terminar(false, false, "", ""); return }
        if let raiz = checkout {
            git(["fetch", "--quiet", "origin", "main"], en: raiz) { ok, _ in
                guard ok else { terminar(false, true, "", ""); return }
                git(["rev-list", "--count", "HEAD..origin/main"], en: raiz) { _, n in
                    guard (Int(n.trimmingCharacters(in: .whitespacesAndNewlines)) ?? 0) > 0 else { terminar(false, false, "", ""); return }
                    git(["log", "--format=%s", "-n", "3", "HEAD..origin/main"], en: raiz) { _, log in
                        terminar(true, false, "", log.split(separator: "\n").map { "• " + $0 }.joined(separator: "\n"))
                    }
                }
            }
            return
        }
        let repo = c.repo, archivo = "\(c.base)-macOS.zip", actual = version
        var pedido = URLRequest(url: URL(string: "https://api.github.com/repos/\(repo)/releases/latest")!)
        pedido.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        pedido.setValue("\(c.base)/\(actual)", forHTTPHeaderField: "User-Agent")
        URLSession.shared.dataTask(with: pedido) { datos, respuesta, _ in
            let codigo = (respuesta as? HTTPURLResponse)?.statusCode ?? 0
            let o = datos.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] } ?? [:]
            let tag = (o["tag_name"] as? String ?? "").trimmingCharacters(in: CharacterSet(charactersIn: "v"))
            let assets = o["assets"] as? [[String: Any]] ?? []
            let url = { (n: String) in (assets.first { $0["name"] as? String == n }?["browser_download_url"] as? String).flatMap(URL.init(string:)) }
            let z = url(archivo), h = url(archivo + ".sha256"), f = url(archivo + ".sig")
            let notas = String((o["body"] as? String ?? "").split(separator: "\n").prefix(4).joined(separator: "\n").prefix(1000))
            let tagOk = tag.range(of: #"^\d{1,6}(\.\d{1,6}){0,3}$"#, options: .regularExpression) != nil
            Task { @MainActor in
                guard codigo == 200 || codigo == 404 else { terminar(false, true, "", ""); return }  // 404: aún no hay versiones
                guard tagOk, tag.compare(actual, options: .numeric) == .orderedDescending,
                      let z, let h, esDescargaNuestra(z, repo: repo), esDescargaNuestra(h, repo: repo) else { terminar(false, false, "", ""); return }
                zip = z; huella = h; versionNueva = tag
                firma = f.flatMap { esDescargaNuestra($0, repo: repo) ? $0 : nil }
                terminar(true, false, tag, notas)
            }
        }.resume()
    }

    /// Al abrir y cada 6 horas. `avisar` solo se llama si hay una versión nueva (no se vuelve a mandar el estado: la
    /// bienvenida o un diálogo abierto no se interrumpen). Llámalo recién cuando la persona eligió su idioma.
    public static func revisarCadaRato(_ avisar: @escaping @MainActor ([String: Any]) -> Void) {
        let si: @MainActor ([String: Any]) -> Void = { r in if r["hay"] as? Bool == true { avisar(r) } }
        revisar(si)
        Timer.scheduledTimer(withTimeInterval: 6 * 3600, repeats: true) { _ in
            Task { @MainActor in revisar(si) }
        }
    }

    // MARK: Instalar, con avance por pasos ("paso|codigo" en un archivo que se lee cada segundo)

    private static func temporal(_ sufijo: String) -> URL {
        URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("\((config?.base ?? "app").lowercased())-actualizar.\(sufijo)")
    }
    private static var reloj: Timer?

    /// El aviso de un paso: ["paso", "codigo", "texto", "valores", "total", "pct"?].
    public static func aviso(_ paso: String, _ codigo: String) -> [String: Any] {
        ["paso": paso, "codigo": codigo, "texto": textos[codigo] ?? textos["errorArmar"]!, "valores": ["app": config?.nombre ?? ""], "total": 3]
    }

    /// Lee el avance cada segundo y se lo pasa a `avisar` (para `window.<App>.actualizacionProgreso`).
    public static func seguir(_ avisar: @escaping @MainActor ([String: Any]) -> Void) {
        let archivoEstado = temporal("estado"), archivoProgreso = temporal("progreso")
        reloj?.invalidate()
        reloj = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            Task { @MainActor in
                let estado = ((try? String(contentsOf: archivoEstado, encoding: .utf8)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                let partes = estado.split(separator: "|", maxSplits: 1).map(String.init)
                guard partes.count == 2, textos[partes[1]] != nil else { return }
                var d = aviso(partes[0], partes[1])
                if partes[0] == "2", let log = try? String(contentsOf: archivoProgreso, encoding: .utf8),
                   let m = log.matches(of: #/\[(\d+)/(\d+)\]/#).last, let n = Double(m.1), let t = Double(m.2), t > 0 {
                    d["pct"] = Int(n / t * 100)
                }
                avisar(d)
                if partes[0] == "error" { reloj?.invalidate(); reloj = nil }
            }
        }
    }

    /// Escribe y lanza el guion que descarga, verifica, espera a que la app se cierre, la reemplaza y la abre (con firma: baja y
    /// revisa todo antes, y el guion solo instala el zip ya revisado). `fin(ok, codigo)`: el código de error es una clave de
    /// `textos`. Quien llama se asegura antes de que no haya nada guardándose ni la IA trabajando.
    public static func instalar(_ fin: @escaping @MainActor (Bool, String) -> Void) {
        guard let c = config else { fin(false, "sinDescarga"); return }
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("\(c.base.lowercased())-actualizacion")
        let guion = tmp.appendingPathComponent("actualizar.sh")
        try? FileManager.default.removeItem(at: tmp)
        try? FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
        let pid = ProcessInfo.processInfo.processIdentifier
        let e = temporal("estado").path, prog = temporal("progreso").path
        try? FileManager.default.removeItem(atPath: prog)
        try? "1|bajando".write(toFile: e, atomically: true, encoding: .utf8)
        // Cerrar la app por su identificador (solo si es un identificador de verdad).
        let cerrar: String
        if let id = Bundle.main.bundleIdentifier, id.range(of: #"^[A-Za-z0-9.-]+$"#, options: .regularExpression) != nil {
            cerrar = "osascript -e \(comillas("tell application id \"\(id)\" to quit")) 2>/dev/null || true"
        } else {
            cerrar = "true"
        }
        let paso = { (p: String, codigo: String) in "echo \(comillas(p + "|" + codigo)) > \(comillas(e))" }
        let lanzar = { (texto: String) in
            do { try texto.write(to: guion, atomically: true, encoding: .utf8) } catch { fin(false, "errorArmar"); return }
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/bin/bash")
            let log = NSTemporaryDirectory() + "\(c.base.lowercased())-actualizar.log"
            p.arguments = ["-c", "nohup /bin/bash \(comillas(guion.path)) > \(comillas(log)) 2>&1 &"]
            do { try p.run(); fin(true, "") } catch { fin(false, "errorArmar") }
        }
        if let raiz = checkout {
            let progreso = c.variableProgreso.map { "\($0)=\(comillas(prog)) " } ?? ""
            let texto = """
            #!/bin/bash
            # Todo lo variable va con comillas(): ni una ruta ni un nombre se interpreta como código.
            export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin
            cd \(comillas(raiz.path)) || exit 1
            \(paso("1", "bajando"))
            git pull --ff-only || { \(paso("error", "errorBajar")); exit 1; }
            \(paso("2", "preparando"))
            \(progreso)bash ./herramientas/empaquetar.sh || { \(paso("error", "errorArmar")); exit 1; }
            [ -d \(comillas("dist/" + c.base + ".app")) ] || { \(paso("error", "errorArmar")); exit 1; }
            \(paso("3", "instalando"))
            sleep 1.5
            \(cerrar)
            while kill -0 \(pid) 2>/dev/null; do sleep 0.5; done
            APP="$HOME/Applications/"\(comillas(c.base + ".app"))
            rm -rf "$APP" && ditto \(comillas("dist/" + c.base + ".app")) "$APP"
            rm -f \(comillas(e)) \(comillas(prog))
            open "$APP"
            """
            lanzar(texto)
            return
        }
        guard let zip, let huella, esDescargaNuestra(zip, repo: c.repo), esDescargaNuestra(huella, repo: c.repo) else {
            try? "error|sinDescarga".write(toFile: e, atomically: true, encoding: .utf8)
            fin(false, "sinDescarga")
            return
        }
        let app = Bundle.main.bundlePath
        let anterior = app + ".anterior"
        let archivo = "\(c.base)-macOS.zip", nueva = "nueva/\(c.base).app"
        // Lo mismo con o sin firma, una vez que el zip está en `tmp` y revisado: descomprimir, esperar a que la app se cierre,
        // cambiarla (deja la anterior si algo falla) y abrirla.
        let instalarZip = """
        ditto -x -k \(comillas(archivo)) nueva || { \(paso("error", "errorArmar")); exit 1; }
        [ -d \(comillas(nueva)) ] || { \(paso("error", "errorArmar")); exit 1; }
        xattr -dr com.apple.quarantine \(comillas(nueva)) 2>/dev/null || true
        \(paso("3", "instalando"))
        sleep 1.5
        \(cerrar)
        while kill -0 \(pid) 2>/dev/null; do sleep 0.5; done
        rm -rf \(comillas(anterior)); mv \(comillas(app)) \(comillas(anterior))
        ditto \(comillas(nueva)) \(comillas(app)) && rm -rf \(comillas(anterior)) || mv \(comillas(anterior)) \(comillas(app))
        rm -f \(comillas(e))
        open \(comillas(app))
        """
        guard !c.llaves.isEmpty else {
            let texto = """
            #!/bin/bash
            # Baja la versión nueva, verifica su huella, espera a que la app se cierre, la reemplaza y la abre.
            # Todo lo variable va con comillas(): ni una URL ni un nombre se interpreta como código.
            export PATH=/usr/bin:/bin:/usr/sbin:/sbin
            cd \(comillas(tmp.path)) || exit 1
            \(paso("1", "bajando"))
            curl -fsSL --proto '=https' --proto-redir '=https' \(comillas(zip.absoluteString)) -o \(comillas(archivo)) && curl -fsSL --proto '=https' --proto-redir '=https' \(comillas(huella.absoluteString)) -o \(comillas(archivo + ".sha256")) || { \(paso("error", "errorBajar")); exit 1; }
            \(paso("2", "preparando"))
            ESPERADA="$(cut -d' ' -f1 \(comillas(archivo + ".sha256")) | tr 'A-F' 'a-f')"
            [ ${#ESPERADA} -eq 64 ] && [ "$(shasum -a 256 \(comillas(archivo)) | cut -d' ' -f1)" = "$ESPERADA" ] || { \(paso("error", "errorBajar")); exit 1; }
            \(instalarZip)
            """
            lanzar(texto)
            return
        }
        // Con firma: sin .sig en el Release, ni se baja.
        let fallar = { (codigo: String) in
            try? "error|\(codigo)".write(toFile: e, atomically: true, encoding: .utf8)
            fin(false, codigo)
        }
        guard let firma, esDescargaNuestra(firma, repo: c.repo), let vNueva = versionNueva else { fallar("firma"); return }
        let destino = tmp.appendingPathComponent(archivo), llaves = c.llaves, id = c.id, instalada = version, estado = e
        Task {
            let codigo = await bajarYRevisar(zip: zip, huella: huella, firma: firma, destino: destino, version: vNueva,
                                             instalada: instalada, id: id, llaves: llaves, estado: estado)
            if let codigo { try? FileManager.default.removeItem(at: tmp); fallar(codigo); return }
            let texto = """
            #!/bin/bash
            # La versión nueva ya está bajada y revisada (huella y firma): espera a que la app se cierre, la reemplaza y la abre.
            # Todo lo variable va con comillas(): ni una ruta ni un nombre se interpreta como código.
            export PATH=/usr/bin:/bin:/usr/sbin:/sbin
            cd \(comillas(tmp.path)) || exit 1
            \(paso("2", "preparando"))
            \(instalarZip)
            """
            lanzar(texto)
        }
    }

    /// Un archivo chico (.sha256, .sig): solo 200, por https y hasta `maximo` bytes.
    nonisolated private static func bajarTexto(_ u: URL, maximo: Int = 4096) async -> String? {
        guard let (d, r) = try? await URLSession.shared.data(for: URLRequest(url: u), delegate: SoloHttps()),
              let h = r as? HTTPURLResponse, h.statusCode == 200, h.url?.scheme == "https", d.count <= maximo else { return nil }
        return String(data: d, encoding: .utf8)
    }

    /// Baja el zip a `destino`, su .sha256 y su .sig, y los revisa (`revisarDescarga`). nil si todo calza; si no, el código.
    nonisolated private static func bajarYRevisar(zip: URL, huella: URL, firma: URL, destino: URL, version: String, instalada: String,
                                                  id: String, llaves: [String], estado: String) async -> String? {
        guard let (temporal, r) = try? await URLSession.shared.download(for: URLRequest(url: zip), delegate: SoloHttps()) else { return "errorBajar" }
        guard let h = r as? HTTPURLResponse, h.statusCode == 200, h.url?.scheme == "https",
              (try? FileManager.default.moveItem(at: temporal, to: destino)) != nil else {
            try? FileManager.default.removeItem(at: temporal)
            return "errorBajar"
        }
        guard let textoHuella = await bajarTexto(huella), let textoFirma = await bajarTexto(firma) else { return "errorBajar" }
        try? "2|preparando".write(toFile: estado, atomically: true, encoding: .utf8)
        guard let calculada = sha256(de: destino) else { return "errorBajar" }
        return revisarDescarga(huellaArchivo: calculada, textoHuella: textoHuella, firma: textoFirma, version: version,
                               instalada: instalada, id: id, llaves: llaves)
    }
}

/// Sigue una redirección solo si va por https (GitHub manda la descarga a su almacenamiento).
private final class SoloHttps: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(request.url?.scheme == "https" ? request : nil)
    }
}

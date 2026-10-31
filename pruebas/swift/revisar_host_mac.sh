#!/usr/bin/env bash
# La pieza «host-mac» en un Mac (Swift solo compila en macOS): arma un paquete temporal con la pieza tal cual
# (target PiezaHost, como queda en una app) y un ejecutable de prueba que revisa las reglas del enchufe y el procesador
# (límite de tiempo, entorno sin <ID>_*, entrada por archivo, secreto por stdin) con una app ficticia («Ana»).
#   bash pruebas/swift/revisar_host_mac.sh
set -euo pipefail
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/Sources/PiezaHost" "$TMP/Sources/RevisarHost"
cp "$BASE"/piezas/host-mac/mac/*.swift "$TMP/Sources/PiezaHost/"
cp "$BASE/pruebas/swift/main.swift" "$TMP/Sources/RevisarHost/main.swift"
cat > "$TMP/Package.swift" <<'SWIFT'
// swift-tools-version:5.10
import PackageDescription
let package = Package(
    name: "RevisarHost",
    platforms: [.macOS("15.0")],
    targets: [
        .target(name: "PiezaHost", path: "Sources/PiezaHost"),
        .executableTarget(name: "RevisarHost", dependencies: ["PiezaHost"], path: "Sources/RevisarHost"),
    ]
)
SWIFT
# La app ficticia: app.json, un script y acciones.json.
APP="$TMP/ana"
mkdir -p "$APP/bin" "$APP/ui/idiomas"
printf '{"id": "ana", "nombre": "Ana", "config": {"idioma_ui": ["es", "en"], "tema": ["sistema", "claro", "oscuro"], "bienvenida": "bool"}}' > "$APP/app.json"
printf '{"codigo": "en", "textos": {"Archivo": "File"}}' > "$APP/ui/idiomas/en.json"
cat > "$APP/bin/eco.py" <<'PY'
import json, os, sys, time
args = sys.argv[1:]
if args[0] == "dormir":
    time.sleep(60)
entrada = json.load(open(args[-2])) if len(args) >= 3 else {}
json.dump({"ok": True, "argv": args[:-1], "entrada": entrada, "ajena": os.environ.get("ANA_AJENA"),
           "stdin": sys.stdin.read() if args[0] == "secreto" else None}, open(args[-1], "w"))
PY
printf '{"formato": 1, "acciones": {"probarIA": {"script": "eco.py", "args": ["probar"], "entrada": "archivo", "datos": {"ia": {"tipo": "enum", "valores": ["claude"]}}, "responde": "iaProbada", "eco": ["ia"], "limite": 30}, "mala": {"script": "eco.py", "args": ["$t"], "entrada": "archivo", "datos": {"t": {"tipo": "texto", "max": 9}}, "limite": 30}}}' > "$APP/acciones.json"
cd "$TMP"
swift build -c debug 2>&1 | tail -30
ANA_AJENA=de-otro-programa REVISAR_APP="$APP" "$TMP/.build/debug/RevisarHost"

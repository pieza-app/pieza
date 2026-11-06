#!/usr/bin/env bash
# En un Mac con Xcode: crea una app ficticia con iPhone («Ana», mac + ios) con pieza.py crear y compila su app de iPhone
# para el simulador (sin firmar). Comprueba que el proyecto generado, recursos.sh y host-ios andan juntos.
#   bash pruebas/swift/compilar_app_ios.sh
set -euo pipefail
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 "$BASE/herramientas/pieza.py" crear "$TMP/ana" --id ana --nombre Ana --plataformas mac,ios > "$TMP/crear.log"
cd "$TMP/ana/movil/ios"
xcodebuild -project App.xcodeproj -scheme Ana -configuration Debug -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$TMP/dd" CODE_SIGNING_ALLOWED=NO build > "$TMP/build.log" 2>&1 || { tail -40 "$TMP/build.log"; exit 1; }
APP="$(find "$TMP/dd" -name Ana.app -type d | head -1)"
test -f "$APP/pieza/app.json" && test -f "$APP/pieza/ui/index.html" || { echo "✗ la app no trae pieza/app.json y pieza/ui/"; exit 1; }
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Info.plist"
echo "✓ la app de iPhone de una app nueva compila y trae su interfaz"

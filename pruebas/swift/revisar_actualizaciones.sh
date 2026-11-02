#!/usr/bin/env bash
# La pieza «actualizaciones» en un Mac (Swift solo compila en macOS): arma un paquete temporal con la pieza tal cual (target
# PiezaActualizaciones, como queda en una app) y un ejecutable que prueba la firma Ed25519, la huella y la configuración (llaves y
# app.json). Revisa que herramientas/firmar/firmar.swift compile y, con PIEZA_PROBAR_LLAVERO=1 (lo pone GitHub), lo usa de verdad en
# un llavero temporal: crear (y que no pise una llave), publica, respaldo (solo con la confirmación), firmar y verificar; la pieza
# acepta esa firma. Lo que no se puede probar sin una app instalada (bajar un Release, reemplazar la app) queda en el README.
#   bash pruebas/swift/revisar_actualizaciones.sh
set -euo pipefail
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
LLAVERO=""
ANTES_DEFECTO=""
ANTES_LISTA=()
limpiar() {
  if [ -n "$LLAVERO" ]; then
    [ -z "$ANTES_DEFECTO" ] || security default-keychain -d user -s "$ANTES_DEFECTO" || true
    [ ${#ANTES_LISTA[@]} -eq 0 ] || security list-keychains -d user -s "${ANTES_LISTA[@]}" || true
    security delete-keychain "$LLAVERO" || true
  fi
  rm -rf "$TMP"
}
trap limpiar EXIT
FIRMAR="$BASE/herramientas/firmar/firmar.swift"
swiftc -typecheck "$FIRMAR"
echo "firmar.swift compila"

mkdir -p "$TMP/Sources/PiezaActualizaciones" "$TMP/Sources/RevisarActualizaciones"
cp "$BASE/piezas/actualizaciones/mac/Actualizaciones.swift" "$TMP/Sources/PiezaActualizaciones/"
cp "$BASE/pruebas/swift/actualizaciones.swift" "$TMP/Sources/RevisarActualizaciones/main.swift"
cat > "$TMP/Package.swift" <<'SWIFT'
// swift-tools-version:5.10
import PackageDescription
let package = Package(
    name: "RevisarActualizaciones",
    platforms: [.macOS("15.0")],
    targets: [
        .target(name: "PiezaActualizaciones", path: "Sources/PiezaActualizaciones"),
        .executableTarget(name: "RevisarActualizaciones", dependencies: ["PiezaActualizaciones"], path: "Sources/RevisarActualizaciones"),
    ]
)
SWIFT

if [ "${PIEZA_PROBAR_LLAVERO:-}" = 1 ]; then
  # Un llavero temporal como el de omisión (y al final, todo como estaba): firmar.swift guarda y lee ahí.
  LLAVERO="$TMP/firma-prueba.keychain-db"
  ANTES_DEFECTO="$(security default-keychain -d user | tr -d ' "')"
  while read -r l; do ANTES_LISTA+=("$(echo "$l" | tr -d ' "')"); done < <(security list-keychains -d user)
  security create-keychain -p prueba "$LLAVERO"
  security set-keychain-settings "$LLAVERO"
  security unlock-keychain -p prueba "$LLAVERO"
  security list-keychains -d user -s "$LLAVERO" "${ANTES_LISTA[@]}"
  security default-keychain -d user -s "$LLAVERO"
  ID="prueba-$$"
  F=(swift "$FIRMAR")
  PUB="$("${F[@]}" crear "$ID" 2>/dev/null)"
  [[ "$PUB" =~ ^[A-Za-z0-9+/]{43}=$ ]] || { echo "crear no dio una llave pública: $PUB"; exit 1; }
  if "${F[@]}" crear "$ID" 2>/dev/null; then echo "crear pisó una llave que ya estaba"; exit 1; fi
  [ "$("${F[@]}" publica "$ID")" = "$PUB" ] || { echo "publica no es la de crear"; exit 1; }
  if echo no | "${F[@]}" respaldo "$ID" >/dev/null 2>&1; then echo "respaldo la mostró sin confirmar"; exit 1; fi
  PRIV="$(echo "$ID" | "${F[@]}" respaldo "$ID" 2>/dev/null)"
  [[ "$PRIV" =~ ^[A-Za-z0-9+/]{43}=$ ]] || { echo "respaldo no dio la privada"; exit 1; }
  if echo "$PRIV" | "${F[@]}" importar "$ID" 2>/dev/null; then echo "importar pisó una llave"; exit 1; fi
  printf 'la versión nueva' > "$TMP/Ana-macOS.zip"
  "${F[@]}" firmar "$ID" v0.2.0 "$TMP/Ana-macOS.zip"
  "${F[@]}" verificar "$ID" 0.2.0 "$TMP/Ana-macOS.zip" "$PUB"
  "${F[@]}" verificar "$ID" 0.2.0 "$TMP/Ana-macOS.zip"
  if "${F[@]}" verificar "$ID" 0.2.1 "$TMP/Ana-macOS.zip" "$PUB" 2>/dev/null; then echo "verificó otra versión"; exit 1; fi
  if "${F[@]}" firmar "Ana Mala" 0.2.0 "$TMP/Ana-macOS.zip" 2>/dev/null; then echo "aceptó un id raro"; exit 1; fi
  export FIRMA_PUBLICA="$PUB" FIRMA_ARCHIVO="$TMP/Ana-macOS.zip" FIRMA_ID="$ID"
  echo "firmar.swift: crear, publica, respaldo, firmar y verificar en un llavero temporal"
fi

cd "$TMP"
swift build -c debug 2>&1 | tail -30
"$TMP/.build/debug/RevisarActualizaciones"

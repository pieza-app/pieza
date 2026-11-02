#!/bin/bash
# Arma dist/{{nombre_ascii}}-Windows.exe (instalador) y su .sha256 a partir de dist/win-unpacked (electron-builder --win dir).
# Necesita makensis (Ubuntu/Debian: apt install nsis; Mac: brew install makensis). Sin Wine.
# Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(node -p 'require("./package.json").version')
[ -d dist/win-unpacked ] || { echo "Falta dist/win-unpacked: corre electron-builder --win dir"; exit 1; }
makensis -V2 -DVERSION="$VERSION" -DORIGEN="$PWD/dist/win-unpacked" -DICONO="$PWD/iconos/{{id}}.ico" -DSALIDA="$PWD/dist/{{nombre_ascii}}-Windows.exe" herramientas/instalador.nsi
(cd dist && sha256sum {{nombre_ascii}}-Windows.exe > {{nombre_ascii}}-Windows.exe.sha256)
echo "Listo: dist/{{nombre_ascii}}-Windows.exe ($(du -h dist/{{nombre_ascii}}-Windows.exe | cut -f1))"

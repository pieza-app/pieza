#!/bin/bash
# Arma dist/{{nombre_ascii}}.app (autosuficiente) y dist/{{nombre_ascii}}-macOS.zip + .sha256, sin instalar nada. Solo en un Mac (Apple Silicon).
# Lo usan build.sh (en tu Mac), la pieza «actualizaciones» (instalación de desarrollo) y publicar.yml (cada versión).
# Dentro van: la app, Python portátil y el código (bin/, ui/, app.json, acciones.json y lo de app.json → empaquetado.carpetas) en
# Contents/Resources/{{id}}. Todo lo que se descarga tiene su huella SHA-256 fija: si no coincide, no se usa y el armado se detiene.
# Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json: si lo cambias, desde ahí
# es de la app y Pieza ya no lo toca. Lo propio va en app.json → empaquetado o en herramientas/empaquetar-extra.sh.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
[ "$(uname -s)" = Darwin ] || { echo "✗ La app de Mac se arma en un Mac." >&2; exit 1; }
[ "$(uname -m)" = arm64 ] || { echo "✗ Por ahora {{nombre}} para Mac es solo para Apple Silicon (arm64)." >&2; exit 1; }
# La versión sale de app.json (la única que se sube para publicar).
VERSION=$(plutil -extract version raw -o - "$RAIZ/app.json" 2>/dev/null || echo {{version}})
cd "$RAIZ/app"
PROGRESO={{ID}}_PROGRESO   # la pieza «actualizaciones» muestra el avance de la compilación
swift build -c release 2>&1 | tee "${!PROGRESO:-/dev/null}" | tail -20
REL=.build/release
CACHE=.build/descargas
mkdir -p "$CACHE"

huella() { shasum -a 256 "$1" | cut -d' ' -f1; }
bajar() { # url huella destino
  if [ -f "$3" ] && [ "$(huella "$3")" = "$2" ]; then return; fi
  echo "→ $(basename "$3")"
  curl -fsSL --proto '=https' --retry 3 "$1" -o "$3.tmp"
  [ "$(huella "$3.tmp")" = "$2" ] || { rm -f "$3.tmp"; echo "✗ $(basename "$3") no coincide con su huella: no se usa." >&2; exit 1; }
  mv "$3.tmp" "$3"
}

# Python portátil (python-build-standalone): el mismo en todas las apps de la familia (herramientas/python.lock). La persona no instala nada.
read -r _ PY_URL PY_SHA < <(grep '^mac ' "$RAIZ/herramientas/python.lock")
PY_VER=$(sed -n 's/^version //p' "$RAIZ/herramientas/python.lock")
bajar "$PY_URL" "$PY_SHA" "$CACHE/python-$PY_VER.tar.gz"
{{#cada app.empaquetado.mac.binarios como b}}
bajar "{{b.url|https}}" "{{b.sha256|sha256}}" "$CACHE/{{b.sha256|sha256}}-{{b.nombre|nombre}}"
{{/cada}}

DIST="$RAIZ/dist"; APP="$DIST/{{nombre_ascii}}.app"; R="$APP/Contents/Resources/{{id}}"
rm -rf "$DIST"; mkdir -p "$APP/Contents/MacOS" "$R" "$APP/Contents/Frameworks"
cp "$REL/{{nombre_ascii}}" "$APP/Contents/MacOS/"
{{#cada app.empaquetado.mac.ejecutables como x}}
cp "$REL/{{x|nombre}}" "$APP/Contents/MacOS/"
{{/cada}}
{{#cada app.empaquetado.mac.binarios como b}}
{{#si b.gz}}
gzip -dc "$CACHE/{{b.sha256|sha256}}-{{b.nombre|nombre}}" > "$APP/Contents/MacOS/{{b.nombre|nombre}}"
{{#sino}}
cp "$CACHE/{{b.sha256|sha256}}-{{b.nombre|nombre}}" "$APP/Contents/MacOS/{{b.nombre|nombre}}"
{{/si}}
{{/cada}}
chmod +x "$APP/Contents/MacOS/"*
cp Info.plist "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" -c "Set :CFBundleVersion $VERSION" "$APP/Contents/Info.plist"
[ -f {{nombre_ascii}}.icns ] && cp {{nombre_ascii}}.icns "$APP/Contents/Resources/{{nombre_ascii}}.icns"
{{#cada app.empaquetado.mac.frameworks como f}}
ditto "$REL/{{f|nombre}}" "$APP/Contents/Frameworks/{{f|nombre}}"
{{/cada}}
tar -xzf "$CACHE/python-$PY_VER.tar.gz" -C "$APP/Contents/Resources"   # → Resources/python/bin/python3
# Más liviano: la app solo usa la biblioteca estándar (sin pruebas, tkinter, idle ni pip).
for d in lib/python3.13/test lib/python3.13/idlelib lib/python3.13/tkinter lib/python3.13/turtledemo lib/python3.13/ensurepip lib/tcl9.0 lib/tk9.0 include share; do
  rm -rf "$APP/Contents/Resources/python/$d"
done
for d in bin ui{{#cada app.empaquetado.carpetas como c}} {{c|ruta}}{{/cada}}; do ditto "$RAIZ/$d" "$R/$d"; done
# app.json (la descripción de la app que leen las piezas: bin/nucleo.py la busca junto a bin/) y acciones.json (las acciones
# declaradas que atiende el host; lo arma pieza.py): sin ellos la app no arranca.
cp "$RAIZ/app.json" "$RAIZ/acciones.json" "$R/"
# La app usa los datos de la persona, nunca la demo de la vista previa.
rm -rf "$R/ui/demo.json"{{#cada app.empaquetado.quitar como q}} "$R/{{q|ruta}}"{{/cada}}
find "$R" -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$R/bin/"*.py
cat > "$APP/Contents/Resources/LICENCIAS-TERCEROS.txt" <<'TXT'
{{nombre}} se distribuye con la licencia {{#si app.empaquetado.licencia}}{{app.empaquetado.licencia|nombre}}{{#sino}}AGPL-3.0{{/si}} (https://github.com/{{repo}}). Dentro de la app va{{#si app.empaquetado.licencias}}n{{/si}}, como programa{{#si app.empaquetado.licencias}}s{{/si}} aparte:

- Python 3.13 de python-build-standalone (https://github.com/astral-sh/python-build-standalone), licencia PSF y las de sus partes.
{{#cada app.empaquetado.licencias como l}}
- {{l|linea}}
{{/cada}}
TXT
# Lo que la app arma a su manera (opcional): recibe la app y la carpeta de swift build.
if [ -f "$RAIZ/herramientas/empaquetar-extra.sh" ]; then bash "$RAIZ/herramientas/empaquetar-extra.sh" "$APP" "$PWD/$REL"; fi

# Firma ad hoc, de adentro hacia afuera, con requisito por identificador: macOS reconoce la app entre versiones (los permisos que
# dio la persona no se vuelven a pedir después de cada actualización).
for f in "$APP/Contents/Frameworks/"*; do [ -e "$f" ] && codesign --force --sign - "$f"; done
find "$APP/Contents/Resources/python" -type f \( -name "*.so" -o -name "*.dylib" -o -perm -u+x \) -exec codesign --force --sign - {} \; 2>/dev/null || true
for p in "$APP/Contents/MacOS/"*; do [ "$(basename "$p")" = {{nombre_ascii}} ] || codesign --force --sign - "$p"; done
codesign --force --sign - --requirements '=designated => identifier "{{bundle}}"' "$APP"

cd "$DIST"
ditto -c -k --keepParent {{nombre_ascii}}.app {{nombre_ascii}}-macOS.zip
shasum -a 256 {{nombre_ascii}}-macOS.zip > {{nombre_ascii}}-macOS.zip.sha256
echo "Listo: $DIST/{{nombre_ascii}}-macOS.zip ($(du -h {{nombre_ascii}}-macOS.zip | cut -f1))"

#!/bin/bash
# Instala (o actualiza) {{nombre}} con un solo comando{{#si mac}}{{#si linux}}, en Mac o Linux{{#sino}}, en Mac{{/si}}{{#sino}}, en Linux{{/si}}:
#   curl -fsSL https://raw.githubusercontent.com/{{repo}}/main/instalar.sh | bash
{{#si windows}}
# (En Windows: irm https://raw.githubusercontent.com/{{repo}}/main/instalar.ps1 | iex)
{{/si}}
# Baja la última versión publicada en GitHub, verifica su huella SHA-256 y la instala solo para tu usuario.
# No pide contraseña ni instala nada más: tus datos quedan en tu computador y nunca se tocan.
# Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json.
set -euo pipefail
REPO="{{repo}}"
verde() { printf "\033[32m%s\033[0m\n" "$1"; }
error() { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }
huella() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

SO=$(uname -s)
case "$SO" in
{{#si mac}}
  Darwin)
    [ "$(uname -m)" = "arm64" ] || error "{{nombre}} para Mac necesita chip Apple (M1 o posterior)."
    VER=$(sw_vers -productVersion | cut -d. -f1)
    [ "$VER" -ge 15 ] || error "{{nombre}} necesita macOS 15 (Sequoia) o posterior. Tienes $(sw_vers -productVersion)."
    ARCHIVO={{nombre_ascii}}-macOS.zip ;;
{{/si}}
{{#si linux}}
  Linux)
    [ "$(uname -m)" = "x86_64" ] || error "Por ahora {{nombre}} para Linux es para procesadores x86_64 (Intel/AMD)."
    ARCHIVO={{nombre_ascii}}-Linux.tar.gz ;;
{{/si}}
  *) error "Este instalador no tiene {{nombre}} para tu sistema.{{#si windows}} En Windows usa: irm https://raw.githubusercontent.com/$REPO/main/instalar.ps1 | iex{{/si}}" ;;
esac

echo "Buscando la última versión de {{nombre}}…"
INFO=$(curl -fsSL -H "Accept: application/vnd.github+json" "https://api.github.com/repos/$REPO/releases/latest") || error "No pude consultar GitHub."
# (sin python: en un Mac recién comprado /usr/bin/python3 pide instalar herramientas de Apple)
TAG=$(printf '%s' "$INFO" | tr ',' '\n' | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || error "No encontré una versión publicada."
BASE="https://github.com/$REPO/releases/download/$TAG"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
echo "Descargando {{nombre}} $TAG…"
curl -fL --proto '=https' --progress-bar "$BASE/$ARCHIVO" -o "$TMP/$ARCHIVO" || error "Esta versión aún no tiene descarga para tu sistema."
curl -fsSL --proto '=https' "$BASE/$ARCHIVO.sha256" -o "$TMP/$ARCHIVO.sha256"
[ "$(huella "$TMP/$ARCHIVO")" = "$(cut -d' ' -f1 "$TMP/$ARCHIVO.sha256")" ] || error "La descarga no coincide con su huella. No instalé nada."
verde "✓ Descarga verificada"

{{#si mac}}
if [ "$SO" = Darwin ]; then
  ditto -x -k "$TMP/$ARCHIVO" "$TMP/app"
  xattr -dr com.apple.quarantine "$TMP/app/{{nombre_ascii}}.app" 2>/dev/null || true
  mkdir -p "$HOME/Applications"
  osascript -e 'tell application id "{{bundle}}" to quit' >/dev/null 2>&1 || true
  sleep 1
  rm -rf "$HOME/Applications/{{nombre_ascii}}.app"
  ditto "$TMP/app/{{nombre_ascii}}.app" "$HOME/Applications/{{nombre_ascii}}.app"
  verde "✓ {{nombre}} $TAG instalada en ~/Applications"
  open "$HOME/Applications/{{nombre_ascii}}.app"
fi
{{/si}}
{{#si linux}}
if [ "$SO" = Linux ]; then
  DIR="$HOME/.local/share/{{nombre_ascii}}"
  mkdir -p "$TMP/app" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
  tar -xzf "$TMP/$ARCHIVO" -C "$TMP/app" --strip-components=1
  pkill -f "$DIR/{{id}}" 2>/dev/null && sleep 1 || true
  rm -rf "$DIR.anterior"; [ -d "$DIR" ] && mv "$DIR" "$DIR.anterior"
  mv "$TMP/app" "$DIR" && rm -rf "$DIR.anterior"
  # Lanzador: en Ubuntu 24.04+ (y otras) el sandbox de Chromium necesita user namespaces que vienen restringidos.
  cat > "$HOME/.local/bin/{{id}}" <<'LANZADOR'
#!/bin/bash
D="$HOME/.local/share/{{nombre_ascii}}"
ARGS=()
if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null)" = 1 ] || [ "$(cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null)" = 0 ]; then ARGS+=(--no-sandbox); fi
exec "$D/{{id}}" "${ARGS[@]}" "$@"
LANZADOR
  chmod +x "$HOME/.local/bin/{{id}}"
  cp "$DIR/resources/{{id}}.png" "$HOME/.local/share/icons/hicolor/256x256/apps/{{id}}.png" 2>/dev/null || true
  cat > "$HOME/.local/share/applications/{{id}}.desktop" <<ESCRITORIO
[Desktop Entry]
Type=Application
Name={{nombre}}
Comment={{#si app.empaquetado.descripcion}}{{app.empaquetado.descripcion}}{{#sino}}{{nombre}}{{/si}}
Exec=$HOME/.local/bin/{{id}} %U
Icon={{id}}
Terminal=false
Categories={{#si app.empaquetado.linux_categoria}}{{app.empaquetado.linux_categoria|nombre}}{{#sino}}Utility{{/si}};
StartupWMClass={{nombre_ascii}}
ESCRITORIO
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
  verde "✓ {{nombre}} $TAG instalada (búscala en tus aplicaciones o escribe: {{id}})"
  nohup "$HOME/.local/bin/{{id}}" >/dev/null 2>&1 &
fi
{{/si}}
echo "Se abrió {{nombre}}: lo primero es elegir tu idioma."

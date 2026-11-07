#!/usr/bin/env bash
# Abre la app de prueba de «host-tauri» de verdad (Linux, con Xvfb) y revisa que el puente funcione de punta a punta: la
# plataforma, el estado, una acción declarada, una propia y un medio por el protocolo, con la CSP de las apps.
# Con un HOME temporal: nada de la persona se toca. Necesita xvfb-run y dbus-run-session.
set -euo pipefail
cd "$(dirname "$0")"
cargo build --quiet
BIN="${CARGO_TARGET_DIR:-$PWD/target}/debug/prueba"
casa=$(mktemp -d)
pid=""
trap '[ -n "$pid" ] && kill "$pid" 2>/dev/null; rm -rf "$casa" 2>/dev/null || true' EXIT
HOME="$casa" XDG_CONFIG_HOME="$casa/.config" PIEZA_REGISTRO="$casa/puente.txt" \
  xvfb-run -a dbus-run-session -- "$BIN" >"$casa/salida.txt" 2>&1 &
pid=$!
visto="$casa/.config/prueba/visto.json"
# WebKit sin GPU en GitHub tarda: hasta 4 minutos.
for i in $(seq 1 240); do
  sleep 1
  if [ -f "$visto" ] && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('medio')==32 and d.get('propia')=={'n':4} and d.get('anotado') and d['estado']['idioma']=='es' else 1)" "$visto" 2>/dev/null; then
    echo "host-tauri: la app de prueba abrió y el puente funciona en ${i} s ($(cat "$visto"))"
    exit 0
  fi
  kill -0 "$pid" 2>/dev/null || break
done
echo "host-tauri: la app de prueba no respondió a tiempo" >&2
echo "Lo que llegó por el puente:" >&2; cat "$casa/puente.txt" >&2 2>/dev/null || echo "  (nada)" >&2
echo "Lo que anotó la interfaz:" >&2; cat "$visto" >&2 2>/dev/null || echo "  (nada)" >&2
find "$casa" -maxdepth 3 -not -path "*/.local/*" >&2
grep -v -e xdg-desktop-portal -e '^$' "$casa/salida.txt" | tail -40 >&2 || true
exit 1

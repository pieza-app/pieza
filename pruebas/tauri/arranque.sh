#!/usr/bin/env bash
# Abre la app de prueba de «host-tauri» de verdad (Linux, con Xvfb) y revisa que el puente funcione de punta a punta: la
# plataforma, el estado, una acción declarada, una propia y un medio por el protocolo, con la CSP de las apps.
set -euo pipefail
cd "$(dirname "$0")"
cargo build --quiet
casa=$(mktemp -d)
trap 'rm -rf "$casa" 2>/dev/null || true' EXIT
HOME="$casa" XDG_CONFIG_HOME="$casa/.config" timeout 40 xvfb-run -a dbus-run-session -- ./target/debug/prueba >/dev/null 2>&1 &
visto="$casa/.config/prueba/visto.json"
for _ in $(seq 1 35); do
  sleep 1
  if [ -f "$visto" ] && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('medio')==32 and d.get('propia')=={'n':4} and d.get('anotado') and d['estado']['idioma']=='es' else 1)" "$visto" 2>/dev/null; then
    echo "host-tauri: la app de prueba abrió y el puente funciona ($(cat "$visto"))"
    exit 0
  fi
done
echo "host-tauri: la app de prueba no respondió a tiempo" >&2
cat "$visto" 2>/dev/null >&2 || true
exit 1

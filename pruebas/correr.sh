#!/usr/bin/env bash
# Todas las pruebas de la base. Sin dependencias.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 herramientas/pieza.py revisar
python3 -W ignore -m unittest -q pruebas/test_piezas.py pruebas/test_piezas_datos.py
# Las piezas de JavaScript (i18n, bienvenida, actualizaciones de Electron): Node, sin dependencias.
node --test pruebas/piezas_js.mjs > /dev/null || node --test pruebas/piezas_js.mjs
# Las piezas de interfaz en un navegador de verdad (foco, CSP, tema, contraste, 390 px): Chromium con Playwright, instalado aparte
# (PLAYWRIGHT=/ruta/a/node_modules/playwright). En GitHub corre en Linux; sin Playwright se avisa y se sigue.
if PLAYWRIGHT="${PLAYWRIGHT:-playwright}" node -e 'require(process.env.PLAYWRIGHT)' 2>/dev/null; then
  node pruebas/interfaz.mjs > /dev/null || node pruebas/interfaz.mjs
  echo "Interfaz: todo bien"
else
  echo "Interfaz: sin Playwright, no la pruebo aquí (PLAYWRIGHT=/ruta/a/playwright)"
fi
# El flujo oficial tiene que decir su versión: las skills instaladas la comparan para saber si quedaron atrás.
for s in skills/*/SKILL.md; do
  grep -Eq '^Versión del flujo: [0-9]+$' "$s" || { echo "Falta «Versión del flujo: N» en $s"; exit 1; }
done
# Workflows: toda action fijada por SHA completo con su versión en un comentario, y la plantilla «Pieza al día» con las mismas
# versiones que los workflows de aquí (Dependabot solo ve .github/workflows).
python3 - <<'PY'
import glob, re, sys
mal, fijadas = [], {}
for f in sorted(glob.glob(".github/workflows/*.yml")) + ["plantillas/pieza-al-dia.yml"]:
    for n, l in enumerate(open(f, encoding="utf-8"), 1):
        m = re.search(r"uses:\s*(\S+)", l)
        if not m:
            continue
        if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", m.group(1)) or not re.search(r"#\s*v\d", l):
            mal.append(f"{f}:{n}: fíjala por SHA con su versión en un comentario")
        elif f.startswith(".github"):
            fijadas.setdefault(m.group(1).split("@")[0], set()).add(m.group(1))
for n, l in enumerate(open("plantillas/pieza-al-dia.yml", encoding="utf-8"), 1):
    m = re.search(r"uses:\s*(\S+)", l)
    if m and m.group(1).split("@")[0] in fijadas and m.group(1) not in fijadas[m.group(1).split("@")[0]]:
        mal.append(f"plantillas/pieza-al-dia.yml:{n}: usa otra versión que .github/workflows")
if mal:
    print("\n".join(mal)); sys.exit(1)
PY
echo "Privacidad"; bash herramientas/revisar_privacidad.sh --generico
if [ -s .terminos-privados ]; then bash herramientas/revisar_privacidad.sh --todo; fi

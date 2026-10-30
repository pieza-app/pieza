#!/usr/bin/env bash
# Todas las pruebas de la base. Sin dependencias.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 herramientas/pieza.py revisar
python3 -W ignore -m unittest -q pruebas/test_piezas.py
# El flujo oficial tiene que decir su versión: las skills instaladas la comparan para saber si quedaron atrás.
for s in skills/*/SKILL.md; do
  grep -Eq '^Versión del flujo: [0-9]+$' "$s" || { echo "Falta «Versión del flujo: N» en $s"; exit 1; }
done

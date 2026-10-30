#!/usr/bin/env bash
# Todas las pruebas de la base. Sin dependencias.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 herramientas/pieza.py revisar
python3 -W ignore -m unittest -q pruebas/test_piezas.py
# El flujo oficial tiene que decir su versión: las skills instaladas la comparan para saber si quedaron atrás.
grep -Eq '^Versión del flujo: [0-9]+$' skills/lanzar-proyecto-open-source/SKILL.md || { echo "Falta «Versión del flujo: N» en la skill"; exit 1; }

#!/usr/bin/env bash
# Todas las pruebas de la base. Sin dependencias.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 herramientas/pieza.py revisar
python3 -W ignore -m unittest -q pruebas/test_piezas.py

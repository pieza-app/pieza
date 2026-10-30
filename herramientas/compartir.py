#!/usr/bin/env python3
"""Arma docs/img/compartir.png (1200×630) con una captura real de la portada: la página servida localmente, el rompecabezas 3D ya
armado y los datos de docs/datos (ficticios o públicos). Necesita Playwright de Python (solo para desarrollo, no es dependencia).

  python3 herramientas/pagina.py todo && (cd docs && python3 -m http.server 8799) &
  python3 herramientas/compartir.py [http://localhost:8799/]
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8799/"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1, locale="es-CL",
                    reduced_motion="reduce")  # con movimiento reducido se dibuja armado de una vez
    # El render por software es lento: se apaga la guardia que volvería al rompecabezas CSS.
    pg.add_init_script("window.__pieza3dSinGuardia = true")
    pg.goto(URL + "?lang=es")
    pg.wait_for_timeout(6000)
    pg.evaluate("document.querySelectorAll('.construccion').forEach(e => e.hidden = true)")
    pg.screenshot(path=os.path.join(BASE, "docs", "img", "compartir.png"))
    b.close()
print("docs/img/compartir.png")

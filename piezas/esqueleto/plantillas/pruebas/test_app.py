"""Pruebas de lo propio de {{nombre|linea}} en Python. Cada una corre con una carpeta temporal: nunca toca datos reales.

La app: suma aquí las de lo propio (una clase por script de bin/), con datos ficticios (Ana Pérez, Matías Soto).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def correr(script, *args, entrada=None):
    """Corre bin/<script> como lo corre el host: lo de la persona en un archivo de entrada y el último argumento es la salida."""
    with tempfile.TemporaryDirectory() as tmp:
        archivos = []
        if entrada is not None:
            ruta = os.path.join(tmp, "entrada.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(entrada, f)
            archivos.append(ruta)
        salida = os.path.join(tmp, "salida.json")
        entorno = {**os.environ, "HOME": tmp, "{{ID}}_DATOS": os.path.join(tmp, "datos")}
        r = subprocess.run([sys.executable, os.path.join(RAIZ, "bin", script), *args, *archivos, salida],
                           capture_output=True, text=True, timeout=60, env=entorno)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        with open(salida, encoding="utf-8") as f:
            return json.load(f)


class Ejemplo(unittest.TestCase):
    def test_cuenta_palabras_y_letras(self):
        self.assertEqual(correr("ejemplo.py", "contar", entrada={"texto": "Hola, soy Ana Pérez"}),
                         {"ok": True, "palabras": 4, "letras": 15})

    def test_sin_texto(self):
        self.assertEqual(correr("ejemplo.py", "contar", entrada={}), {"ok": True, "palabras": 0, "letras": 0})

    def test_la_accion_declarada_manda_el_texto_por_archivo(self):
        # Regla de oro: lo que escribe la persona nunca va como argumento del proceso.
        with open(os.path.join(RAIZ, "acciones.json"), encoding="utf-8") as f:
            a = json.load(f)["acciones"]["ejemplo"]
        self.assertEqual(a["entrada"], "archivo")
        self.assertFalse(any(x.startswith("$") for x in a["args"]))


if __name__ == "__main__":
    unittest.main()

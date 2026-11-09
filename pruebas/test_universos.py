"""Pieza «universos»: el formato (Python) acepta los de base y rechaza lo que podría colarse (HTML, CSS, colores raros)."""
import glob
import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "piezas", "universos", "python"))
import universo_formato as F  # noqa: E402


def base():
    return {"id": "mar", "nombre": "Mar", "idioma": "es", "descripcion": "Azul de Ana Pérez.", "categorias": ["Naturaleza"],
            "tema": {"base": "oscuro", "colores": {"acento": "#33aaff"}}, "textos": {"saludo": "Hola"},
            "listas": {"elogios": ["¡Bien!"]}}


class Universos(unittest.TestCase):
    def test_los_de_base_sirven(self):
        rutas = glob.glob(os.path.join(BASE, "piezas", "universos", "ui", "universos", "*.json"))
        self.assertEqual(len(rutas), 3)
        for r in rutas:
            with open(r, encoding="utf-8") as f:
                u = json.load(f)
            self.assertEqual(F.validar(u), [], r)
            self.assertEqual(os.path.basename(r), u["id"] + ".json")

    def test_rechaza_lo_que_no_es_dato(self):
        self.assertEqual(F.validar(base()), [])
        for cambio in ({"textos": {"saludo": "<img src=x onerror=alert(1)>"}}, {"tema": {"base": "oscuro", "colores": {"acento": "red;}"}}},
                       {"tema": {"base": "oscuro", "colores": {"otro": "#ffffff"}}}, {"tema": {"base": "morado"}},
                       {"listas": {"elogios": []}}, {"id": "Mar Grande"}, {"script": "x"}, {"categorias": ["Marvel"]},
                       {"textos": {"Saludo": "x"}}):
            u = base()
            u.update(cambio)
            self.assertNotEqual(F.validar(u), [], cambio)


if __name__ == "__main__":
    unittest.main()

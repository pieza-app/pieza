"""«pieza.py crear»: una app nueva queda andando de una vez, y sus propias pruebas pasan.

Dos apps ficticias: «Receta» (Mac, Windows y Linux, con la pieza «ia») y «Nota» (solo Mac, sin IA). Cada una se crea en una carpeta
temporal, se corre su pruebas/correr.sh (contrato, Python, interfaz con Playwright si está —PLAYWRIGHT=…— y privacidad) y se revisa
que `pieza.py estado` quede limpio, que sus workflows cumplan las reglas y que lo que le toca a la IA esté dicho. Con TAURI=1 (y
Rust), la app nativa de la receta compila de verdad.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIEZA = os.path.join(BASE, "herramientas", "pieza.py")


def correr(*args, cwd=None, entorno=None):
    return subprocess.run(list(args), capture_output=True, text=True, timeout=600, cwd=cwd, env={**os.environ, **(entorno or {})})


def errores_workflow(ruta):
    """Las reglas de los workflows de Pieza: actions por SHA con su versión, permisos declarados, checkout sin credenciales
    guardadas, nada de pull_request_target ni ${{ … }} dentro de un run:."""
    texto = open(ruta, encoding="utf-8").read()
    e = []
    if "pull_request_target" in texto:
        e.append("pull_request_target")
    if not re.search(r"^permissions:", texto, re.M):
        e.append("sin permissions arriba")
    lineas = texto.splitlines()
    for n, l in enumerate(lineas):
        m = re.search(r"uses:\s*(\S+)", l)
        if m and not (re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", m.group(1)) and re.search(r"#\s*v\d", l)):
            e.append(f"{n + 1}: action sin SHA")
        paso = [l]
        for x in lineas[n + 1:]:
            if re.match(r"^\s*- ", x):
                break
            paso.append(x)
        if m and m.group(1).startswith("actions/checkout@") and "persist-credentials: false" not in "\n".join(paso):
            e.append(f"{n + 1}: checkout sin persist-credentials: false")
        r = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", l)
        if r:
            sangria, bloque = len(r.group(1)), [r.group(2)]
            for x in lineas[n + 1:]:
                if x.strip() and len(x) - len(x.lstrip()) <= sangria:
                    break
                bloque.append(x)
            if any("${{" in x for x in bloque):
                e.append(f"{n + 1}: ${{{{ … }}}} dentro de run:")
    return e


class Crear(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def crear(self, nombre, *extra):
        app = os.path.join(self.tmp, nombre.lower())
        r = correr(sys.executable, PIEZA, "crear", app, "--id", nombre.lower(), "--nombre", nombre, *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return app, r.stdout

    def revisar_app(self, app, salida):
        # Lo que imprime: qué le toca a la IA (los «La app:» de lo propio) y a la persona.
        self.assertIn("LE TOCA A LA IA", salida)
        self.assertIn("LE TOCA A LA PERSONA", salida)
        for x in ("AGENTS.md", "ui/app.js", "docs/pagina.json", "README.md"):
            self.assertIn(f"     {x} (", salida)
        self.assertNotIn("docs/index.html (", salida)   # se genera de docs/pagina.json: no se completa ahí
        # pieza.py estado: todo al día y nada cambiado.
        r = correr(sys.executable, PIEZA, "estado", app, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        for e in json.loads(r.stdout):
            self.assertTrue(e["al_dia"], e["pieza"])
            self.assertFalse(e["cambiados_por_la_app"] or e["generados_por_la_app"] or e["github"] or e["faltan"], e)
        # Workflows con las reglas de siempre.
        for f in glob.glob(os.path.join(app, ".github", "workflows", "*.yml")):
            self.assertEqual(errores_workflow(f), [], f)
        # Sus propias pruebas, de una (en un repo git, como queda al subirla).
        self.assertEqual(correr("git", "init", "-q", cwd=app).returncode, 0)
        # Sin compilar el Rust de cada app (minutos cada una): eso lo hace TAURI=1 una vez y revisar.yml.
        r = correr("bash", "pruebas/correr.sh", cwd=app, entorno={"SIN_RUST": "1"})
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
        self.assertIn("Todo bien", r.stdout)
        return r.stdout

    def test_receta_mac_windows_linux_con_ia(self):
        app, salida = self.crear("Receta", "--plataformas", "mac,windows,linux", "--piezas", "ia")
        a = json.load(open(os.path.join(app, "app.json"), encoding="utf-8"))
        self.assertEqual(a["acciones"]["ejemplo"]["entrada"], "archivo")
        acciones = json.load(open(os.path.join(app, "acciones.json"), encoding="utf-8"))["acciones"]
        self.assertEqual({"ejemplo", "probarIA", "listaIA"}, set(acciones))
        for f in ("escritorio/src/main.rs", "escritorio/Cargo.toml", "escritorio/tauri.conf.json", "escritorio/src/pieza/host.rs", "bin/ia.py",
                  "ui/index.html", "ui/demo.json", "pruebas/contrato_app.py", ".github/workflows/publicar.yml", "docs/index.html"):
            self.assertTrue(os.path.isfile(os.path.join(app, f)), f)
        rs = open(os.path.join(app, "escritorio/src/main.rs"), encoding="utf-8").read()
        self.assertIn("actualizaciones: actualizaciones::Actualizaciones::nuevas(", rs)
        self.assertIn('global: Some("Receta".into())', rs)
        self.assertNotIn("{{", rs)
        for viejo in ("app/Sources", "escritorio/src/main.js", "escritorio/package.json"):
            self.assertFalse(os.path.exists(os.path.join(app, viejo)), viejo)
        self.revisar_app(app, salida)
        # Con TAURI=1 (y Rust con lo de Linux), la app nueva compila de verdad.
        if os.environ.get("TAURI") == "1" and shutil.which("cargo"):
            r = correr("cargo", "build", "--quiet", cwd=os.path.join(app, "escritorio"))
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])

    def test_nota_solo_mac_sin_ia(self):
        app, salida = self.crear("Nota", "--plataformas", "mac", "--repo", "ana-app/nota")
        self.assertTrue(os.path.isfile(os.path.join(app, "escritorio", "src", "main.rs")), "host-tauri también en un Mac solo")
        self.assertFalse(os.path.exists(os.path.join(app, "instalar.ps1")))
        self.assertFalse(os.path.exists(os.path.join(app, "bin", "ia.py")))
        self.assertNotIn("filasIA", open(os.path.join(app, "ui", "app.js"), encoding="utf-8").read())
        self.assertEqual(json.load(open(os.path.join(app, "app.json"), encoding="utf-8"))["repo"], "ana-app/nota")
        self.assertIn("ana-app/nota", open(os.path.join(app, "README.md"), encoding="utf-8").read())
        self.revisar_app(app, salida)

    def test_con_iphone(self):
        """mac + ios: la app de iPhone de host-ios queda generada (proyecto, permisos, recursos y la entrada) y la app pasa sus pruebas."""
        app = os.path.join(self.tmp, "conios")
        r = correr(sys.executable, PIEZA, "crear", app, "--id", "ana", "--nombre", "Ana", "--plataformas", "mac,ios")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in ("movil/ios/App.xcodeproj/project.pbxproj", "movil/ios/Info.plist", "movil/ios/recursos.sh",
                    "movil/ios/Fuentes/App.swift", "movil/ios/Fuentes/PiezaHost/Host.swift", "movil/ios/Fuentes/PiezaHost/Puente.swift"):
            self.assertTrue(os.path.isfile(os.path.join(app, rel)), rel)
        proyecto = open(os.path.join(app, "movil/ios/App.xcodeproj/project.pbxproj"), encoding="utf-8").read()
        self.assertNotIn("{{", proyecto)
        self.assertIn("PRODUCT_BUNDLE_IDENTIFIER = app.ana.ios;", proyecto)
        self.assertIn("productName = Ana;", proyecto)
        self.assertIn("pieza", open(os.path.join(app, "movil/ios/recursos.sh"), encoding="utf-8").read())
        r = correr("bash", os.path.join(app, "pruebas", "correr.sh"), cwd=app, entorno={"SIN_RUST": "1"})
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-3000:])

    def test_lo_que_no_crea(self):
        ocupada = os.path.join(self.tmp, "ocupada")
        os.makedirs(ocupada)
        open(os.path.join(ocupada, "algo.txt"), "w").close()
        casos = [(ocupada, "ana", "Ana", []), (os.path.join(self.tmp, "a"), "ana", "Mi App", []),
                 (os.path.join(self.tmp, "b"), "ana", "Ana", ["--plataformas", "mac,android"]),
                 (os.path.join(self.tmp, "b2"), "ana", "Ana", ["--plataformas", "ios"]),
                 (os.path.join(self.tmp, "c"), "ana", "Ana", ["--piezas", "notas-git"]),
                 (os.path.join(self.tmp, "d"), "Ana", "Ana", [])]
        for carpeta, aid, nombre, extra in casos:
            r = correr(sys.executable, PIEZA, "crear", carpeta, "--id", aid, "--nombre", nombre, *extra)
            self.assertNotEqual(r.returncode, 0, f"{nombre} {extra}")
        self.assertEqual(os.listdir(ocupada), ["algo.txt"])


if __name__ == "__main__":
    unittest.main()

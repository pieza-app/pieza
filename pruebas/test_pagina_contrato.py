"""Pruebas de las piezas «pagina» y «contrato» con una app ficticia («Ana»). Solo biblioteca estándar.

La revisión en un navegador de verdad (contraste AA, 390 px, textos sin traducir, JSON-LD = lo que se ve) está en
pruebas/pagina.mjs (Playwright); aquí, todo lo que se puede revisar sin navegador."""
import glob
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIEZA = os.path.join(BASE, "herramientas", "pieza.py")
sys.path.insert(0, os.path.join(BASE, "herramientas"))


def correr(*args, cwd=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd)


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(texto))


class Faq(html.parser.HTMLParser):
    """Las preguntas que se ven (en español) y el JSON-LD, leídos del HTML generado."""

    def __init__(self):
        super().__init__()
        self.pila, self.en_es, self.preguntas, self.ld, self.actual, self.en_ld = [], 0, [], [], None, False
        self.en_faq = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type") == "application/ld+json":
            self.en_ld = True
        if tag == "section" and a.get("id") == "preguntas":
            self.en_faq = True
        if self.en_faq and tag == "details":
            self.actual = ["", ""]
        if self.en_faq and tag in ("summary", "p") and self.actual is not None:
            self.parte = 0 if tag == "summary" else 1
        if "data-es" in a:
            self.en_es += 1
        self.pila.append("data-es" in a)

    def handle_endtag(self, tag):
        if tag == "script":
            self.en_ld = False
        if tag == "details" and self.actual is not None:
            self.preguntas.append(tuple(self.actual))
            self.actual = None
        if tag == "section":
            self.en_faq = False
        if self.pila and self.pila.pop():
            self.en_es -= 1

    def handle_data(self, d):
        if self.en_ld:
            self.ld.append(d)
        elif self.actual is not None and self.en_es:
            self.actual[self.parte] += d


class Pagina(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "ana")
        os.makedirs(os.path.join(self.app, "ui"))
        escribir(os.path.join(self.app, "ui", "index.html"), "<!doctype html><title>Ana</title>\n")

    def tearDown(self):
        self.tmp.cleanup()

    def iniciar(self, plataformas="mac,windows,linux", piezas=("pagina",)):
        r = correr(PIEZA, "iniciar", self.app, "ana", "Ana", f"--plataformas={plataformas}")
        self.assertEqual(r.returncode, 0, r.stderr)
        for p in piezas:
            r = correr(PIEZA, "agregar", p, self.app)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def generar(self, *extra):
        r = correr(PIEZA, "generar", self.app, *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def completar(self, **cambios):
        ruta = os.path.join(self.app, "docs", "pagina.json")
        d = json.loads(leer(ruta))
        d.update({
            "titulo": {"es": "Ana — notas de Ana Pérez", "en": "Ana — Ana Pérez's notes"},
            "frase": {"es": "Tus notas, en tu computador.", "en": "Your notes, on your computer."},
            "preguntas": [{"pregunta": {"es": "¿Sirve sin internet? «Sí» & <b>", "en": "Does it work offline?"},
                           "respuesta": {"es": "Sí, siempre. Matías Soto lo usa en el avión.", "en": "Yes, always."}}],
            "comparacion": {"con": ["Otra app"], "filas": [{"que": {"es": "Precio", "en": "Price"},
                                                           "valores": [{"es": "Gratis", "en": "Free"}, {"es": "De pago", "en": "Paid"}]}]},
            "pasos": [{"titulo": {"es": "Abre", "en": "Open"}, "texto": {"es": "Y escribe.", "en": "And type."}}],
            **cambios})
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)

    def test_genera_todo_sin_marcas_y_con_json_valido(self):
        self.iniciar(piezas=("pagina", "actualizaciones", "ia", "catalogo"))
        self.completar()
        self.generar()
        for ruta in ("docs/index.html", "docs/colores.css", "docs/sitemap.xml", "docs/pagina.json", "docs/favicon.svg",
                     "herramientas/org.github.io/robots.txt", "herramientas/org.github.io/index.html", ".github/workflows/pagina.yml",
                     "docs/pagina.js", "docs/pagina.css", "docs/tema.css", "docs/sello.svg", "docs/sello-en.svg",
                     "herramientas/pagina_capturas.mjs"):
            texto = leer(os.path.join(self.app, ruta))
            self.assertNotIn("{{", texto.replace("${{", ""), ruta)
        idx = leer(os.path.join(self.app, "docs", "index.html"))
        # Lo que escribió la app va escapado; nada en línea (la CSP solo deja script-src 'self').
        self.assertIn("«Sí» &amp; &lt;b&gt;", idx)
        self.assertNotRegex(idx, r"<script(?![^>]*(src=|application/ld\+json))")
        self.assertNotRegex(idx, r"<[^>]+\son[a-z]+=")
        self.assertNotIn("<style", idx)
        self.assertIn("script-src 'self'", idx)
        for x in ('hreflang="en" href="https://ana-app.github.io/ana/?lang=en"', 'rel="canonical"', "og:image", "twitter:card",
                  "releases/latest/download/Ana-macOS.zip", "Ana-Windows.exe", "Ana-Linux.AppImage", "sello-en.svg", 'href="demo/"'):
            self.assertIn(x, idx)
        # El JSON-LD dice lo mismo que se ve.
        p = Faq()
        p.feed(idx)
        ld = json.loads("".join(p.ld))
        faq = next(x for x in ld["@graph"] if x["@type"] == "FAQPage")
        self.assertEqual([(q["name"], q["acceptedAnswer"]["text"]) for q in faq["mainEntity"]], p.preguntas)
        self.assertEqual(len(p.preguntas), 7)  # la propia + actualizar, verificar, datos, IA, permisos, costo
        sa = ld["@graph"][0]
        self.assertEqual((sa["name"], sa["operatingSystem"]), ("Ana", "macOS 15, Windows 10, Windows 11, Linux"))
        # Permisos e internet: lo de las piezas que tiene (y nada de las que no).
        self.assertIn("raw.githubusercontent.com", idx)
        self.assertIn("api.github.com", idx)
        self.assertNotIn("huggingface.co", idx)
        self.assertIn("Tu IA", idx)
        # Sitemap y robots son XML/texto válidos.
        import xml.dom.minidom
        xml.dom.minidom.parseString(leer(os.path.join(self.app, "docs", "sitemap.xml")))
        self.assertIn("Sitemap: https://ana-app.github.io/ana/sitemap.xml", leer(os.path.join(self.app, "herramientas", "org.github.io", "robots.txt")))

    def test_sin_actualizaciones_ni_ia_y_solo_mac(self):
        self.iniciar(plataformas="mac")
        self.completar(preguntas=[])
        self.generar()
        idx = leer(os.path.join(self.app, "docs", "index.html"))
        p = Faq()
        p.feed(idx)
        nombres = [q for q, _ in p.preguntas]
        self.assertIn("¿Cómo se actualiza? ¿Pierdo algo?", nombres)  # la versión «a mano»
        self.assertIn("Baja la versión nueva", idx)
        self.assertNotIn("Windows protegió", idx)
        self.assertIn("Abrir igualmente", idx)
        self.assertNotIn("Tu IA", idx)
        self.assertNotIn("Ana-Windows.exe", idx)
        self.assertEqual(json.loads("".join(p.ld))["@graph"][0]["operatingSystem"], "macOS 15")

    def test_workflow_cumple_las_reglas(self):
        self.iniciar()
        self.completar()
        self.generar()
        wf = leer(os.path.join(self.app, ".github", "workflows", "pagina.yml"))
        for linea in wf.splitlines():
            m = re.search(r"uses:\s*(\S+)", linea)
            if m:
                self.assertRegex(m.group(1), r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
                self.assertRegex(linea, r"#\s*v\d")
        self.assertIn("persist-credentials: false", wf)
        self.assertNotIn("pull_request_target", wf)
        self.assertNotRegex(wf, r"run:[^\n]*\$\{\{|\n\s+[^\n]*\$\{\{\s*github\.event")
        self.assertRegex(wf, r"(?m)^permissions:\n  contents: read$")
        # Las mismas versiones de las actions que los workflows de Pieza (Dependabot solo ve .github/workflows).
        fijadas = {m.group(1).split("@")[0]: m.group(1) for f in glob.glob(os.path.join(BASE, ".github", "workflows", "*.yml"))
                   for m in re.finditer(r"uses:\s*(\S+)", leer(f))}
        for m in re.finditer(r"uses:\s*(\S+)", wf):
            accion = m.group(1).split("@")[0]
            if accion in fijadas:
                self.assertEqual(m.group(1), fijadas[accion])

    def test_no_pisa_lo_que_la_app_cambio(self):
        self.iniciar()
        self.completar()
        self.generar()
        idx = os.path.join(self.app, "docs", "index.html")
        with open(idx, "a", encoding="utf-8") as f:
            f.write("<!-- de la app -->\n")
        self.completar(frase={"es": "Otra frase.", "en": "Another headline."})
        salida = self.generar()
        self.assertIn("de la app", leer(idx))
        self.assertIn("la app lo cambió", salida)
        # pagina.json se escribe una sola vez: lo de la app queda.
        self.assertIn("Otra frase.", leer(os.path.join(self.app, "docs", "pagina.json")))
        # Se puede volver a correr sin cambios.
        self.assertIn("Otra frase.", leer(os.path.join(self.app, "docs", "colores.css")) + leer(idx) + "Otra frase.")
        self.generar()

    def test_comunes_cubren_lo_que_piden_las_piezas(self):
        """Toda pieza lista que sale a internet o pide un permiso tiene su texto en pagina-comunes.json (y la plantilla lo usa)."""
        comunes = json.loads(leer(os.path.join(BASE, "piezas", "pagina", "datos", "pagina-comunes.json")))
        plantilla = leer(os.path.join(BASE, "piezas", "pagina", "plantillas", "index.html"))
        permisos = {"host-mac": {"Notificaciones": "notificaciones", "Llavero": "llavero"}, "transcribir": {"NSMicrophoneUsageDescription": "microfono"}}
        for f in sorted(glob.glob(os.path.join(BASE, "piezas", "*", "pieza.json"))):
            p = json.loads(leer(f))
            if p.get("estado") != "lista":
                continue
            if p.get("red"):
                self.assertIn(p["id"], comunes["red"], f"«{p['id']}» sale a {p['red']}: falta su texto en pagina-comunes.json → red")
                self.assertEqual(sorted(comunes["red"][p["id"]]["lista"]), sorted(p["red"]), p["id"])
                self.assertIn(f"{{{{#si piezas.{p['id']}}}}}", plantilla)
                self.assertIn(f"datos.comunes.red.{p['id']}.", plantilla)
            for plat, lista in (p.get("permisos") or {}).items():
                for x in lista:
                    clave = permisos.get(p["id"], {}).get(x["clave"])
                    self.assertTrue(clave and clave in comunes["permisos"], f"«{p['id']}» pide {x['clave']} en {plat}: falta en pagina-comunes.json")
                    self.assertIn(f"datos.comunes.permisos.{clave}.", plantilla)
        for k, v in comunes["preguntas"].items():
            for parte in ("p", "r"):
                if parte in v:
                    self.assertEqual(set(v[parte]), {"es", "en"}, k)

    def test_copias_iguales_a_su_pieza(self):
        self.assertEqual(leer(os.path.join(BASE, "piezas", "pagina", "docs", "tema.css")), leer(os.path.join(BASE, "piezas", "tema", "ui", "tema.css")),
                         "docs/tema.css de «pagina» es la copia de piezas/tema/ui/tema.css")
        for s in ("sello.svg", "sello-en.svg"):
            self.assertEqual(leer(os.path.join(BASE, "piezas", "pagina", "docs", s)), leer(os.path.join(BASE, "docs", s)))


# ── contrato ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

UI = """\
(() => {
  const host = PiezaHost.crearHost({ nombre: "ana", global: "Ana", simular: (accion, d, c) => simular(accion, d, c) });
  function guardar(t) { host.enviar("guardarNota", { texto: t }); }
  function abrir() { host.enviar("elegirCarpeta"); host.enviar("listo"); }
  host.responder({
    estado(e) { const x = { a: { b: 1 } }; return x; },
    /** guardarNota → notaGuardada */
    notaGuardada(r) { if (!r.ok) console.log(`no ${r.error} {`); },
    carpetaElegida: (r) => r,
    menu(r) {},
    async iaProbada(r) { return /[{]/.test(r.texto); },
    actualizacionRevisada(r) {}, actualizacionProgreso(r) {},
  });
  const COMUNES = PiezaHost.simulacionesComunes();
  function simular(accion, d, c) {
    switch (accion) {
      case "listo": case "config": return c.responder("estado", {});
      case "guardarNota": return c.responder("notaGuardada", { ok: true });
      case "elegirCarpeta": return c.responder("carpetaElegida", { ruta: "~/Ana" });
      default: return Object.hasOwn(COMUNES, accion) ? COMUNES[accion](d, c) : undefined;
    }
  }
})();
"""


class Contrato(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "ana")
        os.makedirs(self.app)
        self.assertEqual(correr(PIEZA, "iniciar", self.app, "ana", "Ana", "--plataformas=mac,windows,linux").returncode, 0)
        a = os.path.join(self.app, "app.json")
        d = json.loads(leer(a))
        d["acciones"] = {"guardarNota": {"script": "notas.py", "args": ["guardar"], "entrada": "archivo", "scriptDeLaApp": True,
                                         "datos": {"texto": {"tipo": "texto", "max": 2000}}, "responde": "notaGuardada", "limite": 30,
                                         "cola": "escritura"}}
        d["sin_acciones"] = ["listaIA"]
        with open(a, "w") as f:
            json.dump(d, f)
        escribir(os.path.join(self.app, "bin", "notas.py"), "print('ok')\n")
        for p in ("host-ui", "componentes", "ia", "host-mac", "host-escritorio", "contrato"):
            r = correr(PIEZA, "agregar", p, self.app)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        escribir(os.path.join(self.app, "ui", "app.js"), UI)
        escribir(os.path.join(self.app, "ui", "index.html"), """\
            <!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; object-src 'none'">
            <script src="host.js"></script><script src="app.js"></script></head><body></body></html>
            """)
        escribir(os.path.join(self.app, "app", "Sources", "Ana", "AnaApp.swift"), """\
            import PiezaHost
            // registrar("ejemplo") en un comentario no cuenta
            Host.arrancar(.init()) { p in
                p.actualizaciones = .init(repo: "ana-app/ana")
                p.registrar("elegirCarpeta") { d in p.llamar("carpetaElegida", ["ruta": "~/Ana"]) }
            }
            """)
        escribir(os.path.join(self.app, "escritorio", "src", "main.js"), """\
            const host = crearHost({ electron, ventana: {}, actualizaciones, });
            const ACCIONES = {
              async elegirCarpeta(d) { host.llamar("carpetaElegida", { ruta: "~/Ana" }); },
            };
            for (const [nombre, fn] of Object.entries(ACCIONES)) host.acciones.registrar(nombre, fn);
            const w = new BrowserWindow({ webPreferences: { sandbox: true, contextIsolation: true } });
            """)
        escribir(os.path.join(self.app, "escritorio", "package.json"), json.dumps(
            {"version": "0.1.0", "build": {"extraResources": [{"from": "../acciones.json", "to": "ana/acciones.json"}]}}))
        escribir(os.path.join(self.app, "escritorio", ".npmrc"), "ignore-scripts=true\n")
        escribir(os.path.join(self.app, "app", "Info.plist"), """\
            <plist><dict><key>CFBundleIdentifier</key>
            <string>app.ana.mac</string>
            <key>CFBundleShortVersionString</key><string>0.1.0</string></dict></plist>
            """)
        escribir(os.path.join(self.app, "herramientas", "empaquetar.sh"), """\
            cp "$RAIZ/acciones.json" "$CODIGO/acciones.json"
            codesign --force --sign - --requirements '=designated => identifier "app.ana.mac"' "$APP"
            """)
        r = correr(PIEZA, "acciones", self.app)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def tearDown(self):
        self.tmp.cleanup()

    def contrato(self, *extra):
        r = correr(os.path.join(self.app, "pruebas", "contrato.py"), "--json", *extra)
        return r.returncode, {x["codigo"] for x in json.loads(r.stdout)["problemas"]}, r.stdout

    def cambiar(self, ruta, viejo, nuevo):
        t = leer(os.path.join(self.app, ruta))
        self.assertIn(viejo, t)
        escribir(os.path.join(self.app, ruta), t.replace(viejo, nuevo))

    def test_app_en_orden(self):
        codigo, problemas, salida = self.contrato()
        self.assertEqual((codigo, problemas), (0, set()), salida)
        # También desde Pieza, sobre otra app, sin escribir nada en ella.
        antes = {f: os.path.getmtime(f) for f in glob.glob(os.path.join(self.app, "**"), recursive=True)}
        r = correr(os.path.join(BASE, "piezas", "contrato", "python", "contrato.py"), "--app", self.app)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(antes, {f: os.path.getmtime(f) for f in glob.glob(os.path.join(self.app, "**"), recursive=True)})

    def test_detecta_lo_que_falta(self):
        self.cambiar("ui/app.js", 'host.enviar("listo");', 'host.enviar("listo"); host.enviar("exportar");')
        self.cambiar("escritorio/src/main.js", "sandbox: true, ", "")
        self.cambiar("ui/index.html", "<body>", '<body onload="x()">')
        self.cambiar("herramientas/empaquetar.sh", 'identifier "app.ana.mac"', 'identifier "app.otra.mac"')
        self.cambiar("app/Sources/Ana/AnaApp.swift", '["ruta": "~/Ana"]', '["ruta": "~/Ana"]); p.llamar("noExiste", [:]')
        codigo, problemas, salida = self.contrato()
        self.assertEqual(codigo, 1)
        for c in ("simular:exportar", "mac:exportar", "escritorio:exportar", "electron-ventana:escritorio/src/main.js",
                  "en-linea:index.html", "bundle", "funcion:noExiste"):
            self.assertIn(c, problemas, salida)

    def test_acciones_json_y_argumentos(self):
        a = os.path.join(self.app, "app.json")
        d = json.loads(leer(a))
        d["acciones"]["guardarNota"]["args"] = ["$texto"]
        with open(a, "w") as f:
            json.dump(d, f)
        codigo, problemas, salida = self.contrato()
        self.assertIn("acciones-json:guardarNota", problemas, salida)
        correr(PIEZA, "acciones", self.app)  # pieza.py no lo deja: texto como argumento
        codigo, problemas, salida = self.contrato()
        self.assertTrue({"acciones-json:guardarNota", "argumento:guardarNota"} & problemas, salida)

    def test_excepciones_con_motivo_y_que_avisan_si_sobran(self):
        self.cambiar("ui/app.js", 'host.enviar("listo");', 'host.enviar("listo"); host.enviar("soloMac");')
        self.cambiar("ui/app.js", 'case "listo":', 'case "soloMac": return;\n      case "listo":')
        self.cambiar("app/Sources/Ana/AnaApp.swift", 'p.registrar("elegirCarpeta")', 'p.registrar("soloMac") { _ in }\n    p.registrar("elegirCarpeta")')
        codigo, problemas, _ = self.contrato()
        self.assertEqual(problemas, {"escritorio:soloMac"})
        escribir(os.path.join(self.app, "pruebas", "contrato_app.py"), """\
            EXCEPCIONES = {"escritorio:soloMac": "solo en Mac: usa algo del sistema", "mac:viejo": "ya no existe"}
            def revisar(c):
                if "notaGuardada" not in c.funciones:
                    c.problema("propio", "", "falta notaGuardada")
            """)
        codigo, problemas, salida = self.contrato()
        self.assertEqual(problemas, {"excepcion:mac:viejo"}, salida)

    def test_pagina_dice_lo_que_usa(self):
        escribir(os.path.join(self.app, "docs", "pagina.json"), json.dumps({"usa": {"llavero": False, "notificaciones": False}}))
        self.assertEqual(self.contrato()[1], set())
        self.cambiar("app/Sources/Ana/AnaApp.swift", "Host.arrancar", 'let s = Secretos(servicio: "Ana")\nHost.arrancar')
        self.assertIn("pagina-usa:llavero", self.contrato()[1])


if __name__ == "__main__":
    unittest.main()

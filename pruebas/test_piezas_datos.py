"""Pruebas de las piezas de datos (fase 2): red, catálogo, transcribir, trabajos, contenido y la IA en vivo. Solo biblioteca
estándar: python3 -m unittest pruebas/test_piezas_datos.py. Cada prueba arma una app ficticia («Prueba») con pieza.py y corre el
código copiado ahí, con HOME y carpeta de datos temporales: nunca toca nada real."""
import hashlib
import http.server
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIEZA = os.path.join(BASE, "herramientas", "pieza.py")
SECRETO = "vocabulario-secreto-de-ana-perez"


def correr(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd, env=env)


class App(unittest.TestCase):
    PIEZAS = ()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "prueba")
        os.makedirs(os.path.join(self.app, "ui", "idiomas"))
        with open(os.path.join(self.app, "ui", "idiomas", "en.json"), "w") as f:
            json.dump({"codigo": "en", "nombre": "English", "textos": {}}, f)
        self.assertEqual(correr(PIEZA, "iniciar", self.app, "prueba", "Prueba").returncode, 0)
        for p in self.PIEZAS:
            r = correr(PIEZA, "agregar", p, self.app)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.bin = os.path.join(self.app, "bin")
        self.clis = os.path.join(self.tmp.name, "clis")
        os.makedirs(self.clis)
        self.datos = os.path.join(self.tmp.name, "datos")
        self.env = {"PATH": self.clis + os.pathsep + "/usr/bin:/bin", "HOME": self.tmp.name, "PRUEBA_DATOS": self.datos,
                    "TMPDIR": os.path.join(self.tmp.name, "tmp")}
        os.makedirs(self.env["TMPDIR"])

    def tearDown(self):
        self.tmp.cleanup()

    def py(self, codigo, env=None):
        r = subprocess.run([sys.executable, "-c", textwrap.dedent(codigo)], capture_output=True, text=True, cwd=self.bin,
                           env={**self.env, **(env or {})})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def script(self, script, accion, entrada=None):
        salida = os.path.join(self.tmp.name, "salida.json")
        args = [script, accion]
        if entrada is not None:
            e = os.path.join(self.tmp.name, "entrada.json")
            with open(e, "w") as f:
                json.dump(entrada, f)
            args.append(e)
        r = subprocess.run([sys.executable, *args, salida], capture_output=True, text=True, cwd=self.bin, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(salida) as f:
            return json.load(f)

    def cli(self, nombre, codigo):
        ruta = os.path.join(self.clis, nombre)
        with open(ruta, "w") as f:
            f.write(f"#!{sys.executable}\n" + textwrap.dedent(codigo))
        os.chmod(ruta, 0o755)
        return ruta

    def app_json(self, **extra):
        ruta = os.path.join(self.app, "app.json")
        a = json.load(open(ruta))
        a.update(extra)
        json.dump(a, open(ruta, "w"), ensure_ascii=False)


# ───────────── pieza.py agregar con lo que ya está en la app ─────────────

class Agregar(App):
    def agregar(self, *args):
        return correr(PIEZA, "agregar", *args, self.app)

    def lock(self):
        ruta = os.path.join(self.app, "piezas.json")
        return json.load(open(ruta))["piezas"] if os.path.exists(ruta) else {}

    def test_archivo_que_ya_existe(self):
        os.makedirs(self.bin, exist_ok=True)
        propio = os.path.join(self.bin, "contenido.py")
        open(propio, "w").write("# el módulo propio de la app\n")
        r = self.agregar("contenido")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bin/contenido.py", r.stderr)
        self.assertIn("--forzar", r.stderr)
        self.assertIn("renómbralo", r.stderr)
        self.assertNotIn("contenido", self.lock(), "no queda anotada a medias (antes: versión 0.0.0 y huella vacía)")
        self.assertEqual(open(propio).read(), "# el módulo propio de la app\n", "no se tocó nada")
        r = correr(PIEZA, "agregar", "contenido", self.app, "--forzar")
        self.assertEqual(r.returncode, 0, r.stderr)
        info = self.lock()["contenido"]
        self.assertEqual(info["version"], json.load(open(os.path.join(BASE, "piezas/contenido/pieza.json")))["version"])
        self.assertEqual(info["archivos"]["bin/contenido.py"], hashlib.sha256(open(propio, "rb").read()).hexdigest())

    def test_archivo_igual_al_de_la_pieza(self):
        os.makedirs(self.bin, exist_ok=True)
        import shutil
        shutil.copy(os.path.join(BASE, "piezas/red/python/red.py"), os.path.join(self.bin, "red.py"))
        r = self.agregar("red")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("no lo pisé", r.stdout)
        self.assertNotEqual(self.lock()["red"]["version"], "0.0.0", "el mismo archivo de la pieza cuenta como copiado")

    def test_seccion_de_app_json_y_textos_si_usa(self):
        r = self.agregar("catalogo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("«catalogo»", r.stdout)
        a = json.load(open(os.path.join(self.app, "app.json")))
        self.assertEqual(a["catalogo"]["tipos"], {}, "esqueleto de «catalogo» en app.json")
        r = subprocess.run([sys.executable, "-c", "import catalogo; catalogo.config()"], cwd=self.bin, env=self.env, capture_output=True, text=True)
        self.assertIn("dueño/repo", r.stderr, "el esqueleto sin completar da un error claro")
        en = os.path.join(self.app, "ui", "idiomas", "en.json")
        self.assertEqual(self.agregar("cifrado").returncode, 0)
        textos = json.load(open(en))["textos"]
        self.assertIn("La frase no es la correcta.", textos)
        self.assertNotIn("Muy corta", textos, "la app no usa fuerzaFrase: sus frases no entran")
        otra = os.path.join(self.tmp.name, "otra")
        os.makedirs(os.path.join(otra, "ui", "idiomas"))
        json.dump({"codigo": "en", "textos": {}}, open(os.path.join(otra, "ui", "idiomas", "en.json"), "w"))
        open(os.path.join(otra, "ui", "app.js"), "w").write("const f = PiezaCifrado.fuerzaFrase(x);\n")
        correr(PIEZA, "iniciar", otra, "otra", "Otra")
        self.assertEqual(correr(PIEZA, "agregar", "cifrado", otra).returncode, 0)
        self.assertIn("Muy corta", json.load(open(os.path.join(otra, "ui", "idiomas", "en.json")))["textos"])


# ───────────── red ─────────────

class _Servidor(http.server.BaseHTTPRequestHandler):
    vistos = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        _Servidor.vistos.append(self.path)
        ruta = self.path
        if ruta.startswith("/api.ejemplo.com/ok"):
            cuerpo = json.dumps({"saldo": 100, "auth": self.headers.get("Authorization"), "agente": self.headers.get("User-Agent")}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)
        elif ruta.startswith("/api.ejemplo.com/redirige"):
            self.send_response(302); self.send_header("Location", "http://127.0.0.1:1/robar"); self.end_headers()
        elif ruta.startswith("/api.ejemplo.com/grande"):
            self.send_response(200); self.end_headers()  # sin Content-Length: se corta al leer
            try:
                for _ in range(64):
                    self.wfile.write(b"x" * 65536)
            except OSError:
                pass  # el cliente cortó al pasar del máximo: eso es lo que se prueba
        elif ruta.startswith("/api.ejemplo.com/llave"):
            self.send_response(401); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"no")
        else:
            self.send_response(404); self.end_headers()


    recibido = b""

    def do_PUT(self):
        # Una subida «resumable»: guarda cada parte, responde 308 con lo que tiene (la primera vez se «pierde» la mitad de la parte,
        # para probar que se retoma desde lo que dice el servicio) y 200 al completar.
        rango = self.headers.get("Content-Range", "")
        datos = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        _Servidor.vistos.append(rango)
        a, total = rango.split(" ")[1].split("/")
        inicio = int(a.split("-")[0])
        if inicio != len(_Servidor.recibido):
            self.send_response(400); self.end_headers(); return
        guardo = datos[: len(datos) // 2] if len(_Servidor.vistos) == 1 else datos
        _Servidor.recibido += guardo
        if len(_Servidor.recibido) < int(total):
            self.send_response(308); self.send_header("Range", f"bytes=0-{len(_Servidor.recibido) - 1}")
            self.send_header("Content-Length", "0"); self.end_headers()
        else:
            cuerpo = json.dumps({"id": "video-1", "bytes": len(_Servidor.recibido)}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)


class Red(App):
    PIEZAS = ("red",)

    def setUp(self):
        super().setUp()
        _Servidor.vistos = []
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Servidor)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.env["PRUEBA_RED_PRUEBA"] = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        super().tearDown()

    def pedir(self, url, **kw):
        return self.py(f"""
            import json, red
            r = red.Red(["api.ejemplo.com"], "Banco Ejemplo", maximo=1024 * 1024)
            try:
                print(json.dumps({{"ok": True, "r": r.get({url!r}, cabeceras={{"Authorization": "Bearer llave-secreta"}}, **{kw!r})}}))
            except red.ErrorRed as e:
                print(json.dumps({{**e.como_dict(), "estado": e.estado}}))
            """)

    def test_pide_y_devuelve_json(self):
        r = self.pedir("https://api.ejemplo.com/ok")
        self.assertEqual(r["r"]["saldo"], 100)

    def test_dominio_no_permitido_ni_http_ni_puerto_ni_usuario(self):
        for url in ("https://otro.com/ok", "http://api.ejemplo.com/ok", "https://api.ejemplo.com:8443/ok",
                    "https://ana:clave@api.ejemplo.com/ok", "https://api.ejemplo.com.otro.com/ok", "ftp://api.ejemplo.com/"):
            r = self.pedir(url)
            self.assertEqual(r["codigo"], "no_permitida", url)
        self.assertEqual(_Servidor.vistos, [], "nada salió")

    def test_no_sigue_redirecciones_y_la_llave_no_sale(self):
        r = self.pedir("https://api.ejemplo.com/redirige")
        self.assertEqual((r["codigo"], r["estado"]), ("redireccion", 302))
        self.assertEqual(_Servidor.vistos, ["/api.ejemplo.com/redirige"])
        self.assertNotIn("llave-secreta", json.dumps(r))
        r = self.pedir("https://api.ejemplo.com/llave")
        self.assertEqual(r["codigo"], "llave")
        self.assertIn("{servicio}", r["plantilla"])
        self.assertEqual(r["valores"]["servicio"], "Banco Ejemplo")
        self.assertNotIn("llave-secreta", r["error"])

    def test_respuesta_grande_se_corta(self):
        r = self.pedir("https://api.ejemplo.com/grande", crudo=True)
        self.assertEqual(r["codigo"], "grande")

    def test_agente_en_ascii_con_repo(self):
        self.app_json(nombre="Pruebaña ☃", repo="ana-app/prueba")
        r = self.pedir("https://api.ejemplo.com/ok")
        self.assertEqual(r["r"]["agente"], "Pruebana (ana-app/prueba)", "un nombre fuera de latin-1 ya no rompe el pedido")
        self.app_json(repo="no es un repo")
        self.assertEqual(self.pedir("https://api.ejemplo.com/ok")["r"]["agente"], "Pruebana")

    def test_subir_por_partes_con_avance(self):
        _Servidor.recibido = b""
        archivo = os.path.join(self.tmp.name, "video.bin")
        datos = os.urandom(700 * 1024)
        open(archivo, "wb").write(datos)
        r = self.py(f"""
            import json, red
            avance = []
            r = red.Red(["upload.ejemplo.com"], "Videos")
            res = r.subir("https://upload.ejemplo.com/subida?id=1", {archivo!r}, parte=256 * 1024, avance=lambda a, t: avance.append([a, t]))
            print(json.dumps({{"res": res, "avance": avance}}))
            """)
        self.assertEqual(_Servidor.recibido, datos)
        self.assertEqual(r["res"], {"id": "video-1", "bytes": len(datos)})
        self.assertEqual(r["avance"][-1], [len(datos), len(datos)])
        self.assertEqual(_Servidor.vistos[0], f"bytes 0-{256 * 1024 - 1}/{len(datos)}")
        self.assertEqual(_Servidor.vistos[1].split(" ")[1].split("-")[0], str(128 * 1024), "sigue desde lo que el servicio dice tener")

    def test_dentro_de_la_app_no_hay_servidor_falso(self):
        self.env["PRUEBA_RECURSOS"] = self.app
        r = self.py("""
            import json, red
            print(json.dumps(red.Red(["api.ejemplo.com"], "X").prueba))
            """)
        self.assertEqual(r, "")


# ───────────── catálogo ─────────────

FORMATO = '''
FORMATO = 1
CATEGORIAS = ("basicas", "mas-cosas")
CAMPOS = {"formato", "id", "categoria", "nombre"}
def validar(p):
    e = [k for k in p if k not in CAMPOS]
    if p.get("formato") != 1: e.append("formato")
    if not isinstance(p.get("nombre"), str) or not 0 < len(p["nombre"]) <= 40: e.append("nombre")
    return e
'''


class Catalogo(App):
    PIEZAS = ("catalogo",)

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.bin, "formato_prueba.py"), "w") as f:
            f.write(FORMATO)
        self.app_json(catalogo={"repo": "ana-app/ana-catalogo", "tipos": {
            "plantillas": {"validador": "formato_prueba", "max_bytes": 2000, "singular": "plantilla"}}})
        os.makedirs(os.path.join(self.app, "plantillas", "basicas"))
        self.guardar(os.path.join(self.app, "plantillas", "basicas", "hola.json"), self.p("hola", "Hola"))

    def p(self, i, nombre, categoria="basicas"):
        return {"formato": 1, "id": i, "categoria": categoria, "nombre": nombre}

    def guardar(self, ruta, obj):
        crudo = json.dumps(obj).encode()
        with open(ruta, "wb") as f:
            f.write(crudo)
        return crudo

    def entrada(self, obj):
        crudo = json.dumps(obj).encode()
        return {**obj, "ruta": f"plantillas/{obj['categoria']}/{obj['id']}.json", "sha256": hashlib.sha256(crudo).hexdigest(),
                "tamano": len(crudo)}, crudo

    def indice(self, entradas):
        ruta = os.path.join(self.tmp.name, "index.json")
        with open(ruta, "w") as f:
            json.dump({"formato": 1, "plantillas": entradas}, f)
        return self.script("catalogo.py", "indice", {"tipo": "plantillas", "archivo": ruta})

    def test_indice_solo_lo_valido(self):
        buena, crudo = self.entrada(self.p("buena", "Buena"))
        malas = [
            {**buena, "id": "otra"},                                            # el id no calza con la ruta
            {**buena, "ruta": "plantillas/mas-cosas/buena.json", "id": "buena"},  # la categoría no es la carpeta
            {**self.entrada(self.p("sin-huella", "X"))[0], "sha256": "abc"},
            {**self.entrada(self.p("enorme", "X"))[0], "tamano": 999999},
            {**self.entrada(self.p("rara", "X", "inventada"))[0]},
            {**self.entrada(self.p("../fuera", "X"))[0]},
            self.entrada({**self.p("campos", "X"), "script": "alert(1)"})[0],
            buena,  # repetida
        ]
        r = self.indice([buena] + malas)
        self.assertTrue(r["ok"])
        self.assertEqual([x["id"] for x in r["plantillas"]], ["buena"],
                         "un campo de más que el validador no acepta se rechaza (antes se recortaba y entraba)")
        # «archivo» y «bytes» (el nombre que usaba Corta) también sirven
        alias = {k: v for k, v in buena.items() if k not in ("ruta", "tamano")}
        r = self.indice([{**alias, "archivo": buena["ruta"], "bytes": buena["tamano"]}])
        self.assertEqual(r["plantillas"][0]["ruta"], buena["ruta"])

    def test_un_campo_archivo_del_contenido_no_se_quita(self):
        # Una plantilla de Esquema tiene su propio «archivo» (el nombre sugerido): es contenido, no el alias viejo de «ruta».
        with open(os.path.join(self.bin, "formato_archivo.py"), "w") as f:
            f.write("CAMPOS = ('id', 'categoria', 'nombre', 'archivo')\n"
                    "def validar(p):\n    return [k for k in p if k not in CAMPOS] + ([] if isinstance(p.get('archivo'), str) else ['archivo'])\n")
        self.app_json(catalogo={"repo": "ana-app/ana-catalogo", "tipos": {"plantillas": {"validador": "formato_archivo"}}})
        obj = {"id": "acta", "categoria": "basicas", "nombre": "Acta", "archivo": "acta-{fecha}.md"}
        buena, crudo = self.entrada(obj)
        r = self.indice([buena])
        self.assertEqual([(x["id"], x["archivo"], x["ruta"]) for x in r["plantillas"]],
                         [("acta", "acta-{fecha}.md", "plantillas/basicas/acta.json")], "«archivo» con «ruta» es contenido")
        archivo = os.path.join(self.tmp.name, "acta.json")
        open(archivo, "wb").write(crudo)
        i = self.script("catalogo.py", "instalar", {"tipo": "plantillas", "archivo": archivo, "id": "acta", "sha256": buena["sha256"]})
        self.assertTrue(i["ok"], i)
        self.assertEqual(i["item"]["archivo"], "acta-{fecha}.md")
        lista = self.script("catalogo.py", "listar", {"tipo": "plantillas"})["plantillas"]
        self.assertEqual([x.get("archivo") for x in lista if x["id"] == "acta"], ["acta-{fecha}.md"])

    def test_instalar_exige_huella_e_indice_validado(self):
        buena, crudo = self.entrada(self.p("buena", "Buena"))
        archivo = os.path.join(self.tmp.name, "bajado.json")
        open(archivo, "wb").write(crudo)
        pedir = lambda **kw: self.script("catalogo.py", "instalar", {"tipo": "plantillas", "archivo": archivo, "id": "buena",
                                                                    "sha256": buena["sha256"], **kw})
        self.assertEqual(pedir()["codigo"], "no_esta", "sin índice validado no se instala nada")
        self.indice([buena])
        self.assertEqual(pedir(sha256="0" * 64)["codigo"], "no_esta", "otra huella que la del índice")
        self.assertEqual(pedir(sha256="")["codigo"], "no_valido", "huella obligatoria")
        open(archivo, "wb").write(crudo + b" ")
        self.assertEqual(pedir()["codigo"], "danado")
        open(archivo, "wb").write(crudo)
        r = pedir()
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["item"]["origen"], r["plantilla"]["id"]), ("descargado", "buena"))
        guardado = os.path.join(self.datos, "plantillas", "buena.json")
        self.assertEqual(stat.S_IMODE(os.stat(guardado).st_mode), 0o600)

    def test_listar_con_origen_y_quitar(self):
        buena, crudo = self.entrada(self.p("hola", "Hola de la comunidad"))
        self.indice([buena])
        archivo = os.path.join(self.tmp.name, "b.json")
        open(archivo, "wb").write(crudo)
        self.assertTrue(self.script("catalogo.py", "instalar", {"tipo": "plantillas", "archivo": archivo, "id": "hola",
                                                                "sha256": buena["sha256"]})["ok"])
        lista = self.script("catalogo.py", "listar", {"tipo": "plantillas"})["plantillas"]
        self.assertEqual([(x["nombre"], x["origen"]) for x in lista], [("Hola de la comunidad", "descargado")], "lo descargado gana")
        self.assertTrue(self.script("catalogo.py", "quitar", {"tipo": "plantillas", "id": "hola"})["ok"])
        lista = self.script("catalogo.py", "listar", {"tipo": "plantillas"})["plantillas"]
        self.assertEqual([(x["nombre"], x["origen"]) for x in lista], [("Hola", "incluido")])
        self.assertFalse(self.script("catalogo.py", "quitar", {"tipo": "plantillas", "id": "../../app"})["ok"])
        self.assertEqual(self.script("catalogo.py", "listar", {"tipo": "otro"})["codigo"], "no_valido")

    def test_se_valida_entero_y_se_recorta_despues(self):
        with open(os.path.join(self.bin, "formato_suelto.py"), "w") as f:
            f.write("CLAVES = ('formato', 'id', 'categoria', 'nombre')\n"
                    "def revisar(p):\n    return [] if p.get('formato') == 1 and 'script' not in p else ['no']\n")
        self.app_json(catalogo={"repo": "ana-app/ana-catalogo", "tipos": {
            "plantillas": {"validador": "formato_suelto", "funcion": "revisar", "campos": "CLAVES"}}})
        buena, _ = self.entrada({**self.p("buena", "Buena"), "nota": "se acepta pero no se guarda"})
        mala, _ = self.entrada({**self.p("mala", "Mala"), "script": "alert(1)"})
        r = self.indice([buena, mala])
        self.assertEqual([x["id"] for x in r["plantillas"]], ["buena"], "la función y los campos salen de app.json")
        self.assertNotIn("nota", r["plantillas"][0], "lo que acepta el validador se recorta a sus campos después")

    def test_plano_otra_carpeta_mayusculas_y_sin_conexion(self):
        with open(os.path.join(self.bin, "idioma_prueba.py"), "w") as f:
            f.write("CAMPOS = ('id', 'nombre')\ndef validar(p):\n    return [k for k in p if k not in CAMPOS]\n")
        self.app_json(catalogo={"repo": "ana-app/ana-catalogo", "tipos": {"idiomas": {
            "validador": "idioma_prueba", "categoria": False, "mayusculas": True, "carpeta": "traducciones", "local": "lenguas",
            "singular": "plantilla"}}})
        self.assertEqual(self.script("catalogo.py", "ultima", {"tipo": "idiomas"})["codigo"], "sin_conexion")
        def e(i):
            crudo = json.dumps({"id": i, "nombre": i}).encode()
            return {"id": i, "nombre": i, "ruta": f"traducciones/{i}.json", "sha256": hashlib.sha256(crudo).hexdigest(),
                    "tamano": len(crudo)}, crudo
        pt, crudo = e("pt-BR")
        ruta = os.path.join(self.tmp.name, "index.json")
        json.dump({"formato": 1, "idiomas": [pt, e("pt-br")[0], {**e("de")[0], "ruta": "traducciones/x/de.json"}]}, open(ruta, "w"))
        r = self.script("catalogo.py", "indice", {"tipo": "idiomas", "archivo": ruta})
        self.assertEqual([x["id"] for x in r["idiomas"]], ["pt-BR"], "mayúsculas sí; repetido sin distinguir mayúsculas no; plano")
        sin = self.script("catalogo.py", "ultima", {"tipo": "idiomas"})
        self.assertEqual(([x["id"] for x in sin["idiomas"]], sin["guardada"]), (["pt-BR"], True), "la última lista, sin conexión")
        json.dump([pt], open(ruta, "w"))
        self.assertEqual([x["id"] for x in self.script("catalogo.py", "indice", {"tipo": "idiomas", "archivo": ruta})["idiomas"]], ["pt-BR"],
                         "un índice que es solo una lista también sirve")
        archivo = os.path.join(self.tmp.name, "b.json")
        open(archivo, "wb").write(crudo)
        r = self.script("catalogo.py", "instalar", {"tipo": "idiomas", "archivo": archivo, "id": "pt-BR", "sha256": pt["sha256"]})
        self.assertEqual(r["plantilla"]["id"], "pt-BR", "con singular «plantilla», ahí va el objeto")
        self.assertTrue(os.path.isfile(os.path.join(self.datos, "lenguas", "pt-BR.json")), "guardado en «local»")
        mal = self.script("catalogo.py", "instalar", {"tipo": "idiomas", "archivo": archivo, "id": "pt-BR", "sha256": "0" * 64})
        self.assertEqual((mal["frase"], "plantilla" in mal), ("Ya no está en el catálogo. Vuelve a abrirlo.", False),
                         "la frase del error va en «frase»: no choca con el objeto")

    def test_generar_en_el_repo_del_catalogo_sin_nucleo(self):
        repo = os.path.join(self.tmp.name, "repo-catalogo")
        os.makedirs(os.path.join(repo, "herramientas"))
        os.makedirs(os.path.join(repo, "traducciones"))
        import shutil
        shutil.copy(os.path.join(self.bin, "catalogo.py"), os.path.join(repo, "herramientas"))
        with open(os.path.join(repo, "herramientas", "idioma_formato.py"), "w") as f:
            f.write("CAMPOS = ('id', 'nombre')\ndef validar(p):\n    return [k for k in p if k not in CAMPOS]\n")
        self.guardar(os.path.join(repo, "traducciones", "pt-BR.json"), {"id": "pt-BR", "nombre": "Português"})
        self.guardar(os.path.join(repo, "traducciones", "mal.json"), {"id": "mal", "nombre": "x", "extra": 1})
        r = subprocess.run([sys.executable, "herramientas/catalogo.py", "generar", "idiomas", ".", "traducciones/index.json",
                            "--validador=herramientas/idioma_formato.py",
                            '--opciones={"categoria": false, "mayusculas": true, "carpeta": "traducciones"}'],
                           cwd=repo, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("mal.json", r.stdout)
        d = json.load(open(os.path.join(repo, "traducciones", "index.json")))
        self.assertEqual([x["ruta"] for x in d["idiomas"]], ["traducciones/pt-BR.json"])
        r = subprocess.run([sys.executable, "herramientas/catalogo.py", "generar", "idiomas", ".", "x.json"], cwd=repo,
                           capture_output=True, text=True)
        self.assertIn("--validador", r.stderr, "sin app.json ni --validador, lo dice claro")

    def test_generar_el_indice_del_repo(self):
        raiz = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(raiz, "plantillas", "basicas"))
        os.makedirs(os.path.join(raiz, "plantillas", "mas-cosas"))
        self.guardar(os.path.join(raiz, "plantillas", "basicas", "una.json"), self.p("una", "Una"))
        self.guardar(os.path.join(raiz, "plantillas", "mas-cosas", "mal.json"), self.p("mal", "X", "basicas"))
        salida = os.path.join(self.tmp.name, "index.json")
        r = subprocess.run([sys.executable, "catalogo.py", "generar", "plantillas", raiz, salida], cwd=self.bin, env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("mal.json", r.stdout)
        d = json.load(open(salida))
        self.assertEqual([x["id"] for x in d["plantillas"]], ["una"])
        self.assertEqual(d["plantillas"][0]["sha256"], hashlib.sha256(open(os.path.join(raiz, "plantillas", "basicas", "una.json"), "rb").read()).hexdigest())


# ───────────── transcribir ─────────────

WHISPER = '''
import json, os, stat, sys
registro = os.environ["REGISTRO"]
args = sys.argv[1:]
info = {"argv": sys.argv}
if len(args) == 1 and args[0].startswith("@"):
    archivo = args[0][1:]
    info["modo"] = oct(stat.S_IMODE(os.stat(archivo).st_mode))
    info["archivo"] = archivo
    args = open(archivo, "rb").read().decode("utf-8").splitlines()
if "--prompt-archivo" in args:
    archivo = args[args.index("--prompt-archivo") + 1]
    info["modo"] = oct(stat.S_IMODE(os.stat(archivo).st_mode))
    info["archivo"] = archivo
    info["prompt"] = open(archivo, encoding="utf-8").read()
elif "--prompt" in args:
    info["prompt"] = args[args.index("--prompt") + 1]
info["args"] = args
json.dump(info, open(registro, "w"))
salida = args[args.index("-of") + 1]
seg = lambda d, h, t: {"offsets": {"from": d, "to": h}, "text": t}
if "-ml" in args:
    t = [seg(0, 400, "Hola"), seg(400, 450, ","), seg(500, 900, "Ana")]
else:
    t = [seg(0, 2000, "Hola, soy Ana."), seg(2000, 2500, "[Música]"), seg(2500, 4000, "Gracias por ver el video."),
         seg(4000, 5000, "Sí."), seg(5000, 6000, "Sí."), seg(6000, 7000, "sí"), seg(7000, 8000, "Sí."),
         seg(8000, 9000, "Subtítulos realizados por la comunidad de Amara.org")]
json.dump({"transcription": t}, open(salida + ".json", "w"))
'''


class Transcribir(App):
    PIEZAS = ("transcribir",)

    def setUp(self):
        super().setUp()
        self.registro = os.path.join(self.tmp.name, "registro.json")
        self.env["REGISTRO"] = self.registro
        self.modelo = os.path.join(self.tmp.name, "modelo.bin")
        open(self.modelo, "wb").write(b"m")
        self.wav = os.path.join(self.tmp.name, "audio.wav")
        open(self.wav, "wb").write(b"")

    def transcribir(self, **kw):
        return self.py(f"""
            import json, transcribir
            print(json.dumps(transcribir.transcribir({self.wav!r}, modelo={self.modelo!r}, vocabulario={SECRETO!r} + "\\n-m otro", **{kw!r})))
            """)

    def revisar_vocabulario(self):
        r = json.load(open(self.registro))
        self.assertNotIn(SECRETO, " ".join(r["argv"]), "el vocabulario nunca va como argumento")
        self.assertEqual(r["modo"], "0o600")
        self.assertFalse(os.path.exists(r["archivo"]), "el archivo privado se borra al terminar")
        self.assertEqual(r["prompt"], SECRETO + " -m otro", "en una sola línea: un salto de línea no cuela otra opción")
        self.assertEqual(r["args"].count("-m"), 1)
        return r

    def test_whisper_cli_con_archivo_de_argumentos(self):
        self.cli("whisper-cli", WHISPER)
        segs = self.transcribir(idioma="es")
        r = self.revisar_vocabulario()
        self.assertTrue(r["argv"][1].startswith("@"))
        self.assertIn("es", r["args"])
        self.assertEqual([s["texto"] for s in segs], ["Hola, soy Ana.", "Gracias por ver el video.", "Sí.", "Sí."],
                         "sin marcas, sin créditos y sin bucles; sin la energía, un «gracias» puede haberse dicho: queda")

    def test_binario_de_la_app_con_prompt_archivo(self):
        self.cli("prueba-transcribir", WHISPER)
        self.cli("whisper-cli", "raise SystemExit(9)")
        self.transcribir()
        r = self.revisar_vocabulario()
        self.assertTrue(r["argv"][0].endswith("prueba-transcribir"))
        self.assertIn("--prompt-archivo", r["argv"])

    def test_palabras_y_idioma_raro(self):
        self.cli("whisper-cli", WHISPER)
        pal = self.transcribir(palabras=True, idioma="es -m x")
        self.assertEqual(pal, [{"t": "Hola,", "i": 0.0, "f": 0.45}, {"t": "Ana", "i": 0.5, "f": 0.9}])
        r = json.load(open(self.registro))
        self.assertEqual(r["args"][r["args"].index("-l") + 1], "auto", "un idioma raro no entra")

    def test_inventos_con_y_sin_energia(self):
        r = self.py("""
            import json, transcribir as t
            s = lambda d, h, x: {"desde": d, "hasta": h, "texto": x}
            segs = [s(0, 1, "Hola, Ana."), s(1, 2, "Gracias."), s(2, 3, "Gracias, Ana, por venir."), s(3, 4, "Thank you."),
                    s(4, 5, "Tamara organizó todo."), s(5, 6, "Subtítulos realizados por la comunidad de Amara.org y más")]
            # 0-2 s se habla fuerte; 3-4 s, ruido de fondo (bajo UMBRAL_INVENTO pero sobre el silencio); el resto, voz
            energia = [0.1] * 20 + [0.1] * 10 + [0.007] * 10 + [0.1] * 20
            print(json.dumps({
                "sin": [x["texto"] for x in t.limpiar(segs)],
                "con": [x["texto"] for x in t.limpiar(segs, energia)],
                "solo": t.limpiar([s(0, 1, "Gracias."), s(1, 2, "Thank you.")]),
                "vacia": [x["texto"] for x in t.limpiar(segs[:2], [])],
                "exacta": [t.es_alucinacion("Gracias."), t.es_alucinacion("Gracias, Ana"), t.es_credito("amara.org"),
                           t.es_credito("Tamara organizó")],
                "partir": [x["texto"] for x in t.limpiar([s(0, 2, "Hola. Gracias.")], energia,
                                                          partir=lambda ss: [s(0, 1, "Hola."), s(3, 4, "Gracias.")])],
            }))
            """)
        self.assertEqual(r["sin"], ["Hola, Ana.", "Gracias.", "Gracias, Ana, por venir.", "Thank you.", "Tamara organizó todo."],
                         "sin la energía solo se quitan los créditos (subcadena con palabras completas: «Tamara organizó» queda)")
        self.assertEqual(r["con"], ["Hola, Ana.", "Gracias.", "Gracias, Ana, por venir.", "Tamara organizó todo."],
                         "con la energía, «Thank you» sobre ruido se va y el «Gracias.» dicho con voz queda")
        self.assertEqual(r["solo"], [], "sin nada real en toda la transcripción, los inventos se van")
        self.assertEqual(r["vacia"], ["Hola, Ana.", "Gracias."], "energía vacía (WAV raro) es como no tenerla: no borra todo")
        self.assertEqual(r["exacta"], [True, False, True, False])
        self.assertEqual(r["partir"], ["Hola."], "partir corre antes de filtrar: cada parte se filtra sola")

    def test_vad_carpeta_de_modelos_y_modelo_de_prueba(self):
        self.cli("whisper-cli", WHISPER)
        modelos = os.path.join(self.tmp.name, "mis-modelos")
        self.app_json(transcribir={"modelos": modelos})
        os.makedirs(modelos)
        open(os.path.join(modelos, "ggml-silero-v5.1.2.bin"), "wb").write(b"vad")
        self.transcribir()
        self.assertIn("--vad", json.load(open(self.registro))["args"], "con segmentos, el VAD de la carpeta de app.json")
        self.transcribir(palabras=True)
        self.assertNotIn("--vad", json.load(open(self.registro))["args"], "palabra por palabra, sin VAD por defecto")
        otro = os.path.join(self.tmp.name, "otro-vad.bin")
        open(otro, "wb").write(b"v")
        self.transcribir(palabras=True, vad=otro)
        a = json.load(open(self.registro))["args"]
        self.assertEqual(a[a.index("-vm") + 1], otro, "vad=<ruta> usa ese modelo")
        self.transcribir(vad=False)
        self.assertNotIn("--vad", json.load(open(self.registro))["args"])
        falso = os.path.join(self.tmp.name, "falso.bin")
        open(falso, "wb").write(b"x")
        r = self.py("import json, transcribir; print(json.dumps(transcribir.modelo_elegido()))", env={"PRUEBA_MODELO_PRUEBA": falso})
        self.assertEqual(r, falso)
        r = self.py("import json, transcribir; print(json.dumps(transcribir.modelo_elegido()))",
                    env={"PRUEBA_MODELO_PRUEBA": falso, "PRUEBA_RECURSOS": self.app})
        self.assertIsNone(r, "dentro de la app el modelo de prueba no cuenta")
        self.app_json(transcribir={"modelos": "../fuera"})
        r = subprocess.run([sys.executable, "-c", "import transcribir; transcribir.carpeta_modelos()"], cwd=self.bin, env=self.env,
                           capture_output=True, text=True)
        self.assertIn("transcribir.modelos", r.stderr)

    def test_primero_las_carpetas_de_la_app_con_todos_los_nombres(self):
        programas = os.path.join(self.tmp.name, "programas")
        os.makedirs(programas)
        self.cli("prueba-transcribir", "raise SystemExit(9)")  # en el PATH
        propio = os.path.join(programas, "whisper-cli")
        open(propio, "w").write("#!/bin/sh\n")
        os.chmod(propio, 0o755)
        r = self.py("import json, transcribir; print(json.dumps(transcribir.transcriptor()))", env={"PRUEBA_PROGRAMAS": programas})
        self.assertEqual(r, propio, "el whisper-cli que trae la app gana sobre un <id>-transcribir del sistema")

    def test_whisper_de_es_lo_inverso_y_el_error_con_detalle(self):
        r = self.py("""
            import json, transcribir as t
            segs = [{"desde": 0.0, "hasta": 1.25, "texto": "Hola."}, {"desde": 1.25, "hasta": 2.0, "texto": "Chao."}]
            e = t.ErrorTranscribir("fallo", "error: \\n  no pude abrir el modelo")
            print(json.dumps({"ida": t.segmentos_de(t.whisper_de(segs)) == segs, "w": t.whisper_de(segs)["transcription"][0],
                              "e": e.como_dict(), "str": str(e), "sin": t.ErrorTranscribir("fallo").como_dict()}))
            """)
        self.assertTrue(r["ida"])
        self.assertEqual(r["w"], {"offsets": {"from": 0, "to": 1250}, "text": "Hola."})
        self.assertEqual(r["e"]["error"], "La transcripción falló: error: no pude abrir el modelo")
        self.assertEqual((r["e"]["plantilla"], r["e"]["valores"]), ("La transcripción falló: {detalle}", {"detalle": "error: no pude abrir el modelo"}))
        self.assertEqual(r["str"], "La transcripción falló.", "str(e) sigue siendo la frase corta de siempre")
        self.assertEqual((r["sin"]["plantilla"], r["sin"]["valores"]), ("La transcripción falló.", {}))

    def test_sin_modelo_o_sin_transcriptor_da_codigo(self):
        r = self.py("""
            import json, transcribir
            try:
                transcribir.transcribir("a.wav")
            except transcribir.ErrorTranscribir as e:
                print(json.dumps(e.codigo))
            """)
        self.assertEqual(r, "sin_modelo")

    def test_modelos_con_huella_fija_y_verificar(self):
        r = self.script("transcribir.py", "modelos")
        ids = {m["id"]: m for m in r["modelos"]}
        self.assertEqual(ids["turbo"]["sha256"], "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2")
        self.assertTrue(ids["vad"]["url"].startswith("https://huggingface.co/ggml-org/whisper-vad/"))
        os.makedirs(os.path.join(self.datos, "modelos"), exist_ok=True)
        open(os.path.join(self.datos, "modelos", "ggml-silero-v5.1.2.bin"), "wb").write(b"falso")
        self.assertFalse(self.script("transcribir.py", "verificar", {"id": "vad"})["valido"])


# ───────────── trabajos ─────────────

class Trabajos(App):
    PIEZAS = ("trabajos",)

    def test_estado_eventos_detener_y_latido(self):
        progreso = os.path.join(self.tmp.name, "progreso.jsonl")
        r = self.py("""
            import json, trabajos
            t = trabajos.Trabajo.nuevo("resumir", "/carpeta/ficticia", ["leer", "escribir"], {"x": 1})
            t.etapa("escribir")
            t.leyo("src/a.py")
            t.poner_item("a.md", titulo="A", estado="escribiendo")
            print(json.dumps(t.id))
            """, env={"PRUEBA_PROGRESO": progreso})
        eventos = [json.loads(l) for l in open(progreso)]
        self.assertEqual({e["t"] for e in eventos}, {"estado", "lee"})
        self.assertEqual(eventos[-1]["trabajo"]["etapa"], "escribir")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.datos, "trabajos", r + ".json")).st_mode), 0o600)
        d = self.script("trabajos.py", "detener", {"id": r})
        self.assertTrue(d["deteniendo"])
        self.assertEqual(self.py(f"import json, trabajos; print(json.dumps(trabajos.Trabajo.cargar({r!r}).detenido()))"), True)
        # Sin latido por más de MUERTO segundos: el proceso ya no está.
        ruta = os.path.join(self.datos, "trabajos", r + ".json")
        x = json.load(open(ruta))
        x["latido"] = time.time() - 100
        json.dump(x, open(ruta, "w"))
        self.assertEqual(self.script("trabajos.py", "ver", {"id": r})["trabajo"]["estado"], "interrumpido")
        self.assertFalse(self.script("trabajos.py", "ver", {"id": "../../etc"})["ok"])

    def test_terminar_con_error_de_la_ia_y_esperar(self):
        r = self.py("""
            import json, trabajos
            t = trabajos.Trabajo.nuevo("x", "/c", ["a"], {})
            t.poner_item("a.md", estado="escribiendo")
            t.terminar("error", {"codigo": "demora", "plantilla": "{ia} se demoró.", "valores": {"ia": "Claude"}})
            v = t.vista()
            t2 = trabajos.Trabajo.nuevo("x", "/c", ["a"], {})
            t2.esperar(trabajos.limpiar_preguntas([{"pregunta": "¿Para qué es?", "opciones": ["A", "A", "B"]}], "p"))
            print(json.dumps([v["error"], v["error_ia"]["codigo"], v["items"][0]["estado"], [x.id for x in trabajos.esperando("/c")],
                              t2.vista()["preguntas"][0]["opciones"], t2.id]))
            """)
        self.assertEqual(r[:3], ["Claude se demoró.", "demora", "cola"])
        self.assertEqual(r[3], [r[5]])
        self.assertEqual(r[4], ["A", "B"])

    def test_error_de_la_ia_con_valores_raros(self):
        r = self.py("""
            import json, trabajos
            t = trabajos.Trabajo.nuevo("x", "/c", ["a"], {})
            t.terminar("error", {"codigo": None, "plantilla": "{ia} tardó {n} min ({nada}).", "valores": {"ia": "Claude", "n": 20, "nada": None}})
            u = trabajos.Trabajo.nuevo("x", "/c", ["a"], {})
            u.terminar("error", {"codigo": "x", "plantilla": "Falló.", "valores": ["no", "es", "objeto"]})
            print(json.dumps([t.vista()["error"], t.vista()["error_ia"]["valores"], u.vista()["error"]]))
            """)
        self.assertEqual(r, ["Claude tardó 20 min ().", {"ia": "Claude", "n": "20", "nada": ""}, "Falló."])


# ───────────── contenido ─────────────

def _zip(partes):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in partes.items():
            z.writestr(n, d)
    return b.getvalue()


DOCX = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Acta</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Ana Pérez y Matías Soto acordaron revisar el informe.</w:t></w:r></w:p></w:body></w:document>')


class Contenido(App):
    PIEZAS = ("contenido",)

    def extraer(self, nombre, datos):
        ruta = os.path.join(self.tmp.name, nombre)
        open(ruta, "wb").write(datos)
        return self.py(f"""
            import json, contenido
            try:
                print(json.dumps(contenido.extraer_archivo({ruta!r})))
            except contenido.NoSePuede as e:
                print(json.dumps(e.como_dict()))
            """)

    def test_docx_md_html(self):
        r = self.extraer("acta.docx", _zip({"word/document.xml": DOCX}))
        self.assertEqual(r["texto"], "# Acta\n\nAna Pérez y Matías Soto acordaron revisar el informe.\n")
        r = self.extraer("nota.html", b"<html><head><title>T</title><script>alert(1)</script></head><body><h2>Hola</h2><p>Texto</p></body></html>")
        self.assertEqual((r["texto"], r["titulo"]), ("## Hola\n\nTexto\n", "T"))
        self.assertEqual(self.extraer("a.md", "# Título\n\nCuerpo".encode())["formato"], "md")

    def test_zip_bomba(self):
        bomba = _zip({"word/document.xml": DOCX.encode() + b" " * (90 * 1024 * 1024)})
        self.assertLess(len(bomba), 1024 * 1024)
        self.assertEqual(self.extraer("bomba.docx", bomba)["codigo"], "grande_adentro")
        muchas = _zip({f"p{i}.xml": b"" for i in range(5001)})
        self.assertEqual(self.extraer("muchas.epub", muchas)["codigo"], "grande_adentro")

    def test_xml_con_entidades_no_se_abre(self):
        risas = ('<?xml version="1.0"?><!DOCTYPE w [<!ENTITY a "jajaja"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]>'
                 '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&b;</w:t></w:r></w:p></w:body></w:document>')
        r = self.extraer("risas.docx", _zip({"word/document.xml": risas}))
        self.assertEqual(r["codigo"], "raro")
        externa = '<!DOCTYPE x SYSTEM "file:///etc/passwd"><x/>'
        self.assertEqual(self.extraer("ext.odt", _zip({"content.xml": externa}))["codigo"], "raro")

    def test_formatos_que_no_lee_y_errores_traducibles(self):
        r = self.extraer("viejo.doc", b"\xd0\xcf\x11\xe0")
        self.assertEqual(r["codigo"], "formato")
        self.assertIn("{app}", r["plantilla"])
        self.assertTrue(r["error"].startswith("Prueba no lee"))
        self.assertEqual(self.extraer("roto.docx", b"no es zip")["codigo"], "danado")
        self.assertEqual(self.extraer("x.pdf", b"%PDF-1.4 /Encrypt")["codigo"], "pdf_clave")

    def test_partir_capitulos(self):
        texto = "\n\n".join(f"Capítulo {i}: Parte {i}\n\n" + ("Texto del capítulo. " * 40) for i in range(1, 4))
        r = self.py(f"import json, contenido; print(json.dumps([c['titulo'] for c in contenido.partir_capitulos({texto!r})]))")
        self.assertEqual(r, ["Parte 1", "Parte 2", "Parte 3"])


# ───────────── IA en vivo ─────────────

CLAUDE = '''
import json, os, sys, time
if "--help" in sys.argv:
    print("--safe-mode --strict-mcp-config --disallowedTools --tools --setting-sources --output-format <f> text, json or stream-json")
    sys.exit(0)
if "--version" in sys.argv:
    print(os.environ.get("VERSION_FALSA", "2.1.314") + " (Claude Code)"); sys.exit(0)
entrada = sys.stdin.read()
json.dump({"argv": sys.argv, "stdin": entrada, "env": {k: v for k, v in os.environ.items() if k.startswith(("PRUEBA_", "CLAUDE_CODE"))}},
          open(os.environ["REGISTRO"], "w"))
deny = sys.argv[sys.argv.index("--disallowedTools") + 1]
if "MultiEdit" in deny:
    print('Permission deny rule "MultiEdit" matches no known tool — check for typos.', file=sys.stderr)
if os.environ.get("LENTO"):
    time.sleep(30)
paso = lambda o: print(json.dumps(o), flush=True)
paso({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/codigo/src/a.py"}}]}})
paso({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {"pattern": "def "}}]}})
paso({"type": "result", "is_error": False, "result": "listo"})
'''

CODEX = '''
import json, os, sys
if "--help" in sys.argv:
    print("Usage: codex exec [OPTIONS] --json  Print events as JSONL"); sys.exit(0)
json.dump({"argv": sys.argv, "stdin": sys.stdin.read()}, open(os.environ["REGISTRO"], "w"))
print(json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": "bash -lc 'cat src/b.py'"}}), flush=True)
open(sys.argv[sys.argv.index("-o") + 1], "w").write("listo")
'''


class IAVivo(App):
    PIEZAS = ("ia",)

    def setUp(self):
        super().setUp()
        self.registro = os.path.join(self.tmp.name, "registro.json")
        self.env.update({"REGISTRO": self.registro, "PRUEBA_RECURSOS": self.app, "PRUEBA_LLAVE": "no-debe-salir"})
        self.cli("claude", CLAUDE)
        self.cli("codex", CODEX)

    def vivo(self, ia="claude", extra=""):
        return self.py(f"""
            import json, ia
            ev = []
            t, e = ia.preguntar_vivo({SECRETO!r}, ia={ia!r}, al_evento=ev.append{extra})
            print(json.dumps([t.strip(), e, ev]))
            """)

    def test_claude_en_vivo_con_las_mismas_protecciones(self):
        texto, error, ev = self.vivo()
        self.assertEqual((texto, error), ("listo", None))
        self.assertEqual(ev, [{"t": "lee", "ruta": "/codigo/src/a.py"}, {"t": "busca", "patron": "def "}])
        r = json.load(open(self.registro))
        argv = r["argv"]
        self.assertNotIn(SECRETO, " ".join(argv))
        self.assertEqual(r["stdin"], SECRETO)
        for x in ("--strict-mcp-config", "--safe-mode", "stream-json"):
            self.assertIn(x, argv)
        self.assertEqual(argv[argv.index("--disallowedTools") + 1], "*")
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "user")
        self.assertEqual(r["env"].get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "1")
        self.assertFalse([k for k in r["env"] if k.startswith("PRUEBA_")])

    def test_eventos_de_escribir(self):
        ev = self.py("""
            import json, ia
            ev = []
            ia._evento_claude(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Write", "input": {"file_path": "/app/bin/recetas.py"}},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/app/ui/app.js"}}]}}), ev.append)
            ia._evento_codex(json.dumps({"type": "item.started", "item": {"type": "file_change",
                             "changes": [{"path": "/app/README.md", "kind": "update"}]}}), ev.append)
            print(json.dumps(ev))
            """)
        self.assertEqual(ev, [{"t": "escribe", "ruta": "/app/bin/recetas.py"}, {"t": "escribe", "ruta": "/app/ui/app.js"},
                              {"t": "escribe", "ruta": "/app/README.md"}])

    def test_eventos_de_uso(self):
        ev = self.py("""
            import json, ia
            ev = []
            r = ia._evento_claude(json.dumps({"type": "result", "result": "listo", "usage": {
                "input_tokens": 120, "cache_creation_input_tokens": 3000, "cache_read_input_tokens": 45000,
                "output_tokens": 900}}), ev.append)
            ia._evento_codex(json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": 5000, "cached_input_tokens": 4000, "output_tokens": 300}}), ev.append)
            ia._evento_claude(json.dumps({"type": "result", "result": "", "usage": {"input_tokens": "mucho", "output_tokens": -3}}),
                              ev.append)
            print(json.dumps([r, ev]))
            """)
        self.assertEqual(ev[0], ["listo", False])
        self.assertEqual(ev[1], [{"t": "uso", "entrada": 3120, "cache": 45000, "salida": 900},
                                 {"t": "uso", "entrada": 1000, "cache": 4000, "salida": 300}])

    def test_sin_aviso_de_multiedit_y_sin_dejar_de_prohibir(self):
        material = os.path.join(self.tmp.name, "foto.png")
        open(material, "wb").write(b"x")
        for f in ("preguntar", "preguntar_vivo"):
            r = self.py(f"""
                import json, ia
                t, e = ia.{f}("hola", ia="claude", archivos=[{material!r}])
                print(json.dumps(e))
                """)
            self.assertIsNone(r)
            argv = json.load(open(self.registro))["argv"]
            deny = argv[argv.index("--disallowedTools") + 1].split(",")
            self.assertNotIn("MultiEdit", deny, f)
            for h in ("Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Task"):
                self.assertIn(h, deny, f)
            self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep")

    def test_una_version_vieja_aprende_del_aviso(self):
        self.env["VERSION_FALSA"] = "2.0.9"
        codigo = """
            import json, ia
            t, e = ia.preguntar("hola", ia="claude", archivos=[__import__("sys").executable])
            argv = json.load(open(__import__("os").environ["REGISTRO"]))["argv"]
            print(json.dumps([e, argv[argv.index("--disallowedTools") + 1]]))
            """
        e, deny = self.py(codigo)
        self.assertIsNone(e, "el aviso no es un error")
        self.assertIn("MultiEdit", deny)
        e, deny = self.py(codigo)
        self.assertNotIn("MultiEdit", deny, "lo aprendió de su propio aviso")
        self.assertIn("Bash", deny)

    def test_detener(self):
        self.env["LENTO"] = "1"
        inicio = time.time()
        texto, error, _ = self.vivo(extra=", detener=lambda: True")
        self.assertLess(time.time() - inicio, 15)
        self.assertEqual(error["codigo"], "detenido")
        self.assertEqual(error["plantilla"], "Detuviste a {ia}.")

    def test_cli_viejo_no_corre_en_vivo(self):
        self.cli("claude", """
            import os, sys
            if "--help" in sys.argv: print("-p --print"); sys.exit(0)
            open(os.environ["REGISTRO"], "w").write("corrio")
            """)
        _, error, _ = self.vivo()
        self.assertEqual(error["codigo"], "actualizar")
        self.assertFalse(os.path.exists(self.registro))

    def test_codex_json_cuenta_lo_que_lee(self):
        texto, error, ev = self.vivo("codex")
        self.assertEqual((texto, error), ("listo", None))
        self.assertEqual(ev, [{"t": "lee", "ruta": "src/b.py"}])
        argv = json.load(open(self.registro))["argv"]
        self.assertIn("--json", argv)
        self.assertIn("read-only", argv)
        self.assertNotIn(SECRETO, " ".join(argv))

    def test_codex_lee_su_salida_cerrando_el_archivo(self):
        codigo = textwrap.dedent("""
            import gc, json, ia
            t, e = ia.preguntar("hola", ia="codex")
            t2, e2 = ia.preguntar_vivo("hola", ia="codex")
            gc.collect()
            print(json.dumps([t.strip(), t2.strip()]))
            """)
        r = subprocess.run([sys.executable, "-X", "dev", "-W", "always::ResourceWarning", "-c", codigo], cwd=self.bin, env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), ["listo", "listo"])
        self.assertNotIn("ResourceWarning", r.stderr)


if __name__ == "__main__":
    unittest.main()


class Fichas(unittest.TestCase):
    """Lo que dicen los pieza.json de las piezas de datos: nada de una app adentro y cada frase visible con su inglés."""
    PIEZAS = {"catalogo": ["python/catalogo.py", "mac/Catalogo.swift", "escritorio/catalogo.js"], "red": ["python/red.py"],
              "cifrado": ["ui/cifrado.js"], "transcribir": ["python/transcribir.py"],
              "trabajos": ["python/trabajos.py", "mac/LectorProgreso.swift", "escritorio/progreso.js"],
              "contenido": ["python/contenido.py"]}

    def ficha(self, pid):
        with open(os.path.join(BASE, "piezas", pid, "pieza.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_nada_de_una_app_adentro(self):
        import re
        for pid, rutas in self.PIEZAS.items():
            for ruta in rutas:
                texto = open(os.path.join(BASE, "piezas", pid, ruta), encoding="utf-8").read()
                # «corta» y «graba» también son verbos: los nombres de las apps van con mayúscula o como id.
                self.assertIsNone(re.search(r"(?i:esquema|minuta|repasa|alcanc)|\bGraba\b|\bCorta\b|graba-|corta-", texto), f"{pid}/{ruta}")

    def test_frases_con_su_ingles_y_los_mismos_marcadores(self):
        import re
        marcas = lambda t: sorted(re.findall(r"\{(\w+)\}", t))
        frases = {
            "red": r'^\s+"\w+": "([^"]+)",$', "catalogo": r'^\s+"?\w+"?: "([^"]+)",$', "cifrado": r'^\s+\w+: "([^"]+)",$',
            "contenido": r'^\s+"\w+": "([^"]+)",$', "transcribir": r'^\s+"\w+": "([^"]+)",$',
        }
        archivos = {"red": "python/red.py", "catalogo": "escritorio/catalogo.js", "cifrado": "ui/cifrado.js",
                    "contenido": "python/contenido.py", "transcribir": "python/transcribir.py"}
        for pid, patron in frases.items():
            textos = self.ficha(pid)["textos"]
            for es, en in textos.items():
                self.assertEqual(marcas(es), marcas(en), f"{pid}: {es}")
            codigo = open(os.path.join(BASE, "piezas", pid, archivos[pid]), encoding="utf-8").read()
            usadas = {m for m in re.findall(patron, codigo, re.M) if " " in m and m[0].isupper() or m.startswith("{")}
            self.assertTrue(usadas, pid)
            self.assertEqual(usadas - set(textos), set(), f"{pid}: frases sin inglés en pieza.json")
        self.assertIn("Detuviste a {ia}.", self.ficha("ia")["textos"])
        # Las frases de Swift y de Python del catálogo son las mismas que las de Electron.
        js = open(os.path.join(BASE, "piezas/catalogo/escritorio/catalogo.js"), encoding="utf-8").read()
        for otro in ("python/catalogo.py", "mac/Catalogo.swift"):
            texto = open(os.path.join(BASE, "piezas/catalogo", otro), encoding="utf-8").read()
            for f in self.ficha("catalogo")["textos"]:
                self.assertIn(f, texto, otro)
                self.assertIn(f, js)

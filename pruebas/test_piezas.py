"""Pruebas de la base: las piezas de Python y la herramienta pieza.py. Solo biblioteca estándar: python3 -m unittest pruebas/test_piezas.py"""
import json
import os
import stat
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIEZA = os.path.join(BASE, "herramientas", "pieza.py")
SECRETO = "pedido-secreto-de-ana-perez"


def correr(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd, env=env)


class AppDePrueba(unittest.TestCase):
    """Una app ficticia («Prueba») con las piezas copiadas por pieza.py, y CLIs de IA falsos que anotan cómo los llamaron."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "prueba")
        os.makedirs(os.path.join(self.app, "ui", "idiomas"))
        with open(os.path.join(self.app, "ui", "idiomas", "en.json"), "w") as f:
            json.dump({"codigo": "en", "nombre": "English", "textos": {"Hola": "Hello"}}, f)
        self.assertEqual(correr(PIEZA, "iniciar", self.app, "prueba", "Prueba").returncode, 0)
        r = correr(PIEZA, "agregar", "ia", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.bin = os.path.join(self.tmp.name, "clis")
        os.makedirs(self.bin)
        self.registro = os.path.join(self.tmp.name, "registro.json")
        falso = textwrap.dedent(f"""\
            #!{sys.executable}
            import json, os, sys
            entrada = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
            if "--help" in sys.argv:
                print("--safe-mode --strict-mcp-config --disallowedTools"); sys.exit(0)
            archivos = {{n: open(n).read() for n in os.listdir(".") if n.endswith(".md")}}
            json.dump({{"argv": sys.argv, "stdin": entrada, "cwd": os.getcwd(), "archivos": archivos,
                       "env": {{k: v for k, v in os.environ.items() if k.startswith(("PRUEBA_", "CLAUDE_CODE"))}}}},
                      open({self.registro!r}, "w"))
            if "-o" in sys.argv:
                open(sys.argv[sys.argv.index("-o") + 1], "w").write("listo")
            else:
                print("listo")
            """)
        for nombre in ("claude", "codex", "agy"):
            ruta = os.path.join(self.bin, nombre)
            with open(ruta, "w") as f:
                f.write(falso)
            os.chmod(ruta, 0o755)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin", "HOME": self.tmp.name,
                    "PRUEBA_RECURSOS": self.app, "PRUEBA_DATOS": os.path.join(self.tmp.name, "datos"), "PRUEBA_LLAVE": "no-debe-salir"}

    def tearDown(self):
        self.tmp.cleanup()

    def py(self, codigo):
        r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, cwd=os.path.join(self.app, "bin"), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def registro_ia(self):
        with open(self.registro) as f:
            return json.load(f)


class Nucleo(AppDePrueba):
    def test_config_solo_lo_declarado(self):
        salida = self.py("import nucleo, json; print(json.dumps(nucleo.guardar_config("
                         "{'ia': 'codex', 'tema': 'morado', 'raro': 1, 'bienvenida': True})))")
        self.assertEqual(json.loads(salida), {"ia": "codex", "bienvenida": True})

    def test_carpeta_privada_y_escritura_atomica(self):
        self.py("import nucleo; nucleo.escribir_json(nucleo.carpeta_datos() + '/x.json', {'a': 1})")
        datos = self.env["PRUEBA_DATOS"]
        self.assertEqual(stat.S_IMODE(os.stat(datos).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(datos, "x.json")).st_mode), 0o600)
        self.assertEqual(sorted(os.listdir(datos)), ["x.json"])

    def test_texto_con_patron(self):
        ruta = os.path.join(self.app, "app.json")
        a = json.load(open(ruta))
        a["config"]["idioma_audio"] = {"tipo": "texto", "patron": "auto|[a-z]{2,3}"}
        a["config"]["roto"] = {"tipo": "texto", "patron": "("}
        json.dump(a, open(ruta, "w"))
        salida = self.py("import nucleo, json; print(json.dumps([nucleo.limpiar_config({'idioma_audio': v, 'roto': 'x'}) "
                         "for v in ['auto', 'es', 'es -l', 'ESP', 'auto\\n-x']]))")
        self.assertEqual(json.loads(salida), [{"idioma_audio": "auto"}, {"idioma_audio": "es"}, {}, {}, {}])

    def test_ruta_en_no_sale(self):
        salida = self.py("import nucleo; print([nucleo.ruta_en('/tmp', p) is None for p in ['a/b', '../x', '/etc', '', 'a/../../x']])")
        self.assertEqual(salida.strip(), "[False, True, True, True, True]")
        # Una base vacía o relativa (el inyector carpetaActual manda "" sin carpeta) nunca es la carpeta de trabajo del script.
        salida = self.py("import nucleo; print([nucleo.ruta_en(b, 'a.md') is None for b in ['', '.', 'docs', None, '/tmp', '/no/existe/x']])")
        self.assertEqual(salida.strip(), "[True, True, True, True, False, True]")

    def test_contrato_error_como_json(self):
        entrada, salida = os.path.join(self.tmp.name, "e.json"), os.path.join(self.tmp.name, "s.json")
        with open(entrada, "w") as f:
            f.write("{no es json")
        r = subprocess.run([sys.executable, "ia.py", "probar", entrada, salida], cwd=os.path.join(self.app, "bin"), env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(json.load(open(salida))["ok"])


class IA(AppDePrueba):
    def preguntar(self, ia, extra=""):
        return self.py(f"import ia; t, e = ia.preguntar({SECRETO!r}, ia={ia!r}{extra}); print(t.strip(), e)")

    def test_cli_viejo_pide_actualizar_y_no_corre(self):
        viejo = os.path.join(self.tmp.name, "viejo")
        os.makedirs(viejo)
        with open(os.path.join(viejo, "claude"), "w") as f:
            f.write(f"#!{sys.executable}\nimport sys\nif '--help' in sys.argv: print('-p --print'); sys.exit(0)\n"
                    f"open({self.registro!r}, 'w').write('corrio')\nprint('listo')\n")
        os.chmod(os.path.join(viejo, "claude"), 0o755)
        env = {**self.env, "PATH": viejo + os.pathsep + "/usr/bin:/bin"}
        r = subprocess.run([sys.executable, "-c", "import ia, json; t, e = ia.preguntar('hola', ia='claude'); print(json.dumps(e))"],
                           cwd=os.path.join(self.app, "bin"), env=env, capture_output=True, text=True)
        e = json.loads(r.stdout)
        self.assertEqual(e["codigo"], "actualizar")
        self.assertIn("{app}", e["plantilla"])
        self.assertEqual(e["valores"]["app"], "Prueba")
        self.assertFalse(os.path.exists(self.registro))  # nunca se corrió sin las protecciones

    def test_ayuda_de_la_app_en_los_errores(self):
        ruta = os.path.join(self.app, "app.json")
        a = json.load(open(ruta))
        a["ia"] = {"ayuda": "Revisa en Ajustes → Tu IA."}
        json.dump(a, open(ruta, "w"), ensure_ascii=False)
        env = {**self.env, "PATH": "/usr/bin:/bin"}
        r = subprocess.run([sys.executable, "-c", "import ia, json; t, e = ia.preguntar('hola', ia='claude'); "
                            "print(json.dumps({**e, 'frase': ia.frase(e)}, ensure_ascii=False))"],
                           cwd=os.path.join(self.app, "bin"), env=env, capture_output=True, text=True)
        e = json.loads(r.stdout)
        self.assertEqual((e["codigo"], e["ayuda"]), ("no_instalada", "Revisa en Ajustes → Tu IA."))
        self.assertEqual(e["frase"], "No encontré Claude en este computador. Revisa en Ajustes → Tu IA.")
        # probar se usa desde «Tu IA»: ahí la ayuda sobra (ni en el campo ni en la frase).
        r = subprocess.run([sys.executable, "-c", "import ia, json; print(json.dumps(ia.probar('claude'), ensure_ascii=False))"],
                           cwd=os.path.join(self.app, "bin"), env=env, capture_output=True, text=True)
        e = json.loads(r.stdout)
        self.assertEqual(e["codigo"], "no_instalada")
        self.assertNotIn("ayuda", e)
        self.assertEqual(e["error"], "No encontré Claude en este computador.")
        a["ia"] = {"ayuda": "<b>{x}</b>"}
        json.dump(a, open(ruta, "w"))
        r = subprocess.run([sys.executable, "-c", "import ia, json; t, e = ia.preguntar('hola', ia='claude'); print(json.dumps(e))"],
                           cwd=os.path.join(self.app, "bin"), env=env, capture_output=True, text=True)
        self.assertNotIn("ayuda", json.loads(r.stdout))

    def test_claude_sin_herramientas_ni_memoria_y_pedido_por_stdin(self):
        self.assertIn("listo None", self.preguntar("claude"))
        r = self.registro_ia()
        self.assertNotIn(SECRETO, " ".join(r["argv"]))
        self.assertEqual(r["stdin"], SECRETO)
        self.assertIn("--strict-mcp-config", r["argv"])
        self.assertEqual(r["argv"][r["argv"].index("--disallowedTools") + 1], "*")
        self.assertIn("--safe-mode", r["argv"])
        self.assertEqual(r["env"].get("CLAUDE_CODE_DISABLE_CLAUDE_MDS"), "1")
        self.assertFalse([k for k in r["env"] if k.startswith("PRUEBA_")])

    def test_claude_con_material_solo_lee(self):
        foto = os.path.join(self.tmp.name, "cuaderno.PNG")
        open(foto, "wb").write(b"x")
        self.preguntar("claude", f", archivos=[{foto!r}]")
        argv = self.registro_ia()["argv"]
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Glob,Grep")
        self.assertIn("Bash", argv[argv.index("--disallowedTools") + 1])

    def test_claude_escribe_solo_en_la_carpeta_y_sin_terminal(self):
        carpeta = os.path.join(self.tmp.name, "mi-app")
        os.makedirs(carpeta)
        self.preguntar("claude", f", escribir={carpeta!r}")
        r = self.registro_ia()
        argv = r["argv"]
        permitidas = argv[argv.index("--allowedTools") + 1].split(",")
        self.assertTrue({"Read", "Edit", "Write"} <= set(permitidas))
        prohibidas = argv[argv.index("--disallowedTools") + 1].split(",")
        self.assertTrue({"Bash", "WebFetch", "WebSearch", "Task"} <= set(prohibidas))
        self.assertNotIn("Edit", prohibidas)
        self.assertEqual(argv[argv.index("--add-dir") + 1], carpeta)
        self.assertIn(carpeta, r["stdin"])  # se le dice dónde trabaja en el pedido, no como argumento suelto
        self.assertNotIn(SECRETO, " ".join(argv))

    def test_codex_escribe_en_su_sandbox(self):
        carpeta = os.path.join(self.tmp.name, "mi-app")
        os.makedirs(carpeta)
        self.preguntar("codex", f", escribir={carpeta!r}")
        argv = self.registro_ia()["argv"]
        self.assertEqual(argv[argv.index("-s") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("-C") + 1], carpeta)

    def test_codex_solo_lectura(self):
        self.assertIn("listo None", self.preguntar("codex"))
        r = self.registro_ia()
        self.assertIn("read-only", r["argv"])
        self.assertNotIn(SECRETO, " ".join(r["argv"]))

    def test_antigravity_pedido_en_archivo(self):
        self.assertIn("listo None", self.preguntar("gemini"))
        r = self.registro_ia()
        self.assertNotIn(SECRETO, " ".join(r["argv"]))
        self.assertEqual(r["archivos"].get("instrucciones.md"), SECRETO)

    def test_no_instalada_da_codigo_traducible(self):
        os.remove(os.path.join(self.bin, "codex"))
        salida = self.py("import ia, json; print(json.dumps(ia.probar('codex')))")
        r = json.loads(salida)
        self.assertEqual((r["ok"], r["codigo"]), (False, "no_instalada"))
        self.assertIn("ChatGPT (Codex)", r["error"])

    def test_textos_en_ingles_sumados(self):
        textos = json.load(open(os.path.join(self.app, "ui", "idiomas", "en.json")))["textos"]
        self.assertEqual(textos["Hola"], "Hello")
        self.assertIn("No conozco esa IA.", textos)


MODERNA = {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}}
HERRAMIENTAS_MCP = textwrap.dedent("""\
    import mcp, nucleo
    INSTRUCCIONES = "Prueba guarda notas ficticias de Ana Pérez."
    def buscar(args):
        return {"texto": args.get("texto", ""), "limite": args.get("limite", 30)}
    def ruidosa(args):
        print("esto no debe romper el protocolo")
        return {"ok": True}
    def enorme(args):
        return {"x": "a" * (600 * 1024)}
    def anotar(args):
        return {"anotado": args["nota"]}
    def falla(args):
        int("Ana Pérez")
    HERRAMIENTAS = [
        mcp.herramienta("buscar", "Busca notas por texto.", buscar,
                        {"texto": {"type": "string", "maxLength": 50}, "limite": {"type": "integer", "minimum": 1, "maximum": 200},
                         "desde": mcp.FECHA}),
        mcp.herramienta("ruidosa", "Imprime algo.", ruidosa),
        mcp.herramienta("falla", "Falla con un dato adentro.", falla),
        mcp.herramienta("enorme", "Devuelve demasiado.", enorme),
        mcp.herramienta("anotar", "Anota algo.", anotar, {"nota": {"type": "string"}}, ["nota"], escribe=True),
    ]
    """)


class MCP(AppDePrueba):
    """La pieza «mcp»: el servidor (las dos formas del protocolo), sus topes y permisos, y conectarlo a cada IA sin romper nada."""

    def setUp(self):
        super().setUp()
        r = correr(PIEZA, "agregar", "mcp", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.app, "bin", "mcp_herramientas.py"), "w") as f:
            f.write(HERRAMIENTAS_MCP)

    def servidor(self, *mensajes, crudo=None):
        entrada = crudo if crudo is not None else "".join(json.dumps(m) + "\n" for m in mensajes)
        r = subprocess.run([sys.executable, "mcp_servidor.py"], input=entrada, capture_output=True, text=True,
                           cwd=os.path.join(self.app, "bin"), env=self.env, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [json.loads(x) for x in r.stdout.splitlines()], r.stderr

    def llamar(self, nombre, args=None, **extra):
        return {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": nombre, "arguments": args or {}, **extra}}

    def conectar(self, *args):
        salida = os.path.join(self.tmp.name, "salida.json")
        r = subprocess.run([sys.executable, "mcp_conectar.py", *args, salida], capture_output=True, text=True,
                           cwd=os.path.join(self.app, "bin"), env=self.env, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.load(open(salida))

    def test_lo_que_suma_a_la_app(self):
        a = json.load(open(os.path.join(self.app, "app.json")))
        self.assertEqual(a["mcp"], {"modulos": ["mcp_herramientas"]})
        self.assertEqual(a["config"]["mcp_escribir"], "bool")
        acciones = json.load(open(os.path.join(self.app, "acciones.json")))["acciones"] if os.path.exists(
            os.path.join(self.app, "acciones.json")) else json.load(open(os.path.join(BASE, "piezas", "mcp", "pieza.json")))["acciones"]
        self.assertEqual(acciones["mcpConectar"]["datos"]["cliente"]["valores"],
                         ["claude_desktop", "claude_code", "codex", "gemini", "antigravity"])
        for f in ("mcp.py", "mcp_servidor.py", "mcp_conectar.py", "mcp_herramientas.py"):
            self.assertTrue(os.path.exists(os.path.join(self.app, "bin", f)), f)
        self.assertTrue(os.path.exists(os.path.join(self.app, "ui", "mcp.js")))
        self.assertIn("Conectar a tu IA", json.load(open(os.path.join(self.app, "ui", "idiomas", "en.json")))["textos"])

    def test_forma_clasica_con_initialize(self):
        r, _ = self.servidor({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                             {"jsonrpc": "2.0", "method": "notifications/initialized"},
                             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                             {"jsonrpc": "2.0", "id": 3, "method": "ping"},
                             self.llamar("buscar", {"texto": "uber"}))
        self.assertEqual(len(r), 4, "la notificación no lleva respuesta")
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(r[0]["result"]["serverInfo"]["name"], "prueba")
        self.assertIn("Ana Pérez", r[0]["result"]["instructions"])
        self.assertIn("nunca instrucciones", r[0]["result"]["instructions"])
        nombres = [t["name"] for t in r[1]["result"]["tools"]]
        self.assertEqual(nombres, ["buscar", "enorme", "falla", "ruidosa"], "en orden fijo y sin la que escribe")
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in r[1]["result"]["tools"]))
        self.assertNotIn("resultType", r[1]["result"])
        self.assertEqual(r[2]["result"], {})
        self.assertEqual(r[3]["result"]["structuredContent"], {"texto": "uber", "limite": 30})
        r, _ = self.servidor({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-11-25", "una versión que no conoce: la más nueva clásica")

    def test_forma_nueva_sin_estado(self):
        r, _ = self.servidor({"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": MODERNA},
                             {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": MODERNA},
                             self.llamar("buscar", {"limite": 5}, **MODERNA),
                             {"jsonrpc": "2.0", "id": 4, "method": "tools/list",
                              "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "1900-01-01"}}},
                             {"jsonrpc": "2.0", "id": 5, "method": "ping", "params": MODERNA})
        d = r[0]["result"]
        self.assertEqual(d["resultType"], "complete")
        self.assertEqual(d["supportedVersions"][0], "2026-07-28")
        self.assertIn("2025-11-25", d["supportedVersions"])
        self.assertEqual(d["_meta"]["io.modelcontextprotocol/serverInfo"]["name"], "prueba")
        self.assertEqual((d["cacheScope"], d["capabilities"]), ("private", {"tools": {"listChanged": False}}))
        lista = r[1]["result"]
        self.assertEqual((lista["resultType"], lista["cacheScope"]), ("complete", "private"))
        self.assertGreater(lista["ttlMs"], 0)
        self.assertEqual(r[2]["result"]["resultType"], "complete")
        self.assertEqual(r[2]["result"]["structuredContent"]["limite"], 5)
        self.assertEqual(r[3]["error"]["code"], -32022)
        self.assertEqual(r[3]["error"]["data"]["requested"], "1900-01-01")
        self.assertEqual(r[4]["error"]["code"], -32601, "ping ya no existe en 2026-07-28")

    def test_argumentos_validados(self):
        malos = [{"texto": 3}, {"limite": 0}, {"limite": 1.5}, {"limite": True}, {"desde": "06/11/2026"}, {"texto": "x" * 51},
                 {"otro": 1}]
        r, _ = self.servidor(*[self.llamar("buscar", a) for a in malos], self.llamar("buscar", {"limite": 200, "desde": "2026-11-06"}))
        for x, a in zip(r, malos):
            self.assertTrue(x["result"]["isError"], a)
            self.assertNotIn("structuredContent", x["result"])
        self.assertFalse(r[-1]["result"]["isError"])
        r, _ = self.servidor(self.llamar("falla"))
        self.assertEqual(r[0]["result"]["content"][0]["text"], "No se pudo (ValueError).", "el texto de un error cualquiera no llega a la IA")
        r, _ = self.servidor(self.llamar("nada"), {"jsonrpc": "2.0", "id": 2, "method": "resources/read"})
        self.assertEqual(r[0]["error"]["code"], -32602)
        self.assertEqual(r[1]["error"]["code"], -32601)

    def test_topes_y_lo_que_imprime_una_herramienta(self):
        gigante = json.dumps(self.llamar("buscar", {"texto": "a" * (1100 * 1024)}))
        r, err = self.servidor(crudo=gigante + "\n" + "no es json\n" + "[1]\n" + json.dumps(self.llamar("ruidosa")) + "\n"
                               + json.dumps(self.llamar("enorme")) + "\n")
        self.assertEqual(r[0]["error"]["message"], "Pedido demasiado grande")
        self.assertEqual(r[1]["error"]["code"], -32700)
        self.assertEqual(r[2]["error"]["code"], -32600)
        self.assertFalse(r[3]["result"]["isError"])
        self.assertIn("esto no debe romper el protocolo", err)
        self.assertTrue(r[4]["result"]["isError"])
        self.assertIn("muy grande", r[4]["result"]["content"][0]["text"])
        self.assertEqual(len(r), 5)

    def test_demasiadas_llamadas_seguidas(self):
        r, _ = self.servidor(*[self.llamar("buscar") for _ in range(125)])
        self.assertTrue(r[124]["result"]["isError"])
        self.assertIn("Demasiadas", r[124]["result"]["content"][0]["text"])
        # Con un reloj falso (sin depender de lo rápida que sea la máquina): 120 por minuto, y al minuto se libera.
        salida = self.py(textwrap.dedent("""\
            import mcp, json
            s = mcp.Servidor([])
            t = [0.0]
            r = [s._demasiadas(lambda: t[0]) for _ in range(121)]
            t[0] = 61.0
            r.append(s._demasiadas(lambda: t[0]))
            print(json.dumps([r[119], r[120], r[121]]))"""))
        self.assertEqual(json.loads(salida), [False, True, False])

    def test_escribir_solo_si_la_persona_lo_permite(self):
        r, _ = self.servidor(self.llamar("anotar", {"nota": "hola"}))
        self.assertEqual(r[0]["error"]["code"], -32602, "sin permiso, la herramienta no existe para la IA")
        self.py("import nucleo; nucleo.guardar_config({'mcp_escribir': True})")
        r, _ = self.servidor({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.llamar("anotar", {"nota": "hola"}),
                             self.llamar("anotar", {}))
        anotar = [t for t in r[0]["result"]["tools"] if t["name"] == "anotar"][0]
        self.assertFalse(anotar["annotations"]["readOnlyHint"])
        self.assertEqual(r[1]["result"]["structuredContent"], {"anotado": "hola"})
        self.assertIn("falta «nota»", r[2]["result"]["content"][0]["text"])

    def test_actividad_sin_argumentos(self):
        self.servidor(self.llamar("buscar", {"texto": SECRETO[:50]}), self.llamar("buscar", {"limite": 0}))
        texto = open(os.path.join(self.env["PRUEBA_DATOS"], "mcp-actividad.jsonl")).read()
        self.assertNotIn(SECRETO[:20], texto)
        act = json.loads(self.py("import mcp, json; print(json.dumps(mcp.actividad()))"))
        self.assertEqual([(a["herramienta"], a["ok"]) for a in act], [("buscar", True), ("buscar", False)])

    def test_modulos_de_app_json(self):
        ruta = os.path.join(self.app, "app.json")
        a = json.load(open(ruta))
        for modulos, error in ((["os"], "Falta bin/os.py"), (["../x"], "nombres inválidos"), (["mcp"], "nombres inválidos")):
            a["mcp"] = {"modulos": modulos}
            json.dump(a, open(ruta, "w"))
            r = subprocess.run([sys.executable, "mcp_servidor.py"], input="", capture_output=True, text=True,
                               cwd=os.path.join(self.app, "bin"), env=self.env, timeout=120)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(error, r.stderr)
        with open(os.path.join(self.app, "bin", "mcp_otro.py"), "w") as f:
            f.write("import mcp\nHERRAMIENTAS = {'resumen': (lambda a: {'n': 1}, 'Un resumen.', mcp.esquema())}\n"
                    "INSTRUCCIONES = 'Otra parte de la app.'\n")
        a["mcp"] = {"modulos": ["mcp_herramientas", "mcp_otro"]}
        json.dump(a, open(ruta, "w"))
        r, _ = self.servidor({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, self.llamar("resumen"))
        self.assertIn("Otra parte de la app.", r[0]["result"]["instructions"])
        self.assertIn("resumen", [t["name"] for t in r[1]["result"]["tools"]], "la forma de Alcancía también sirve")
        self.assertEqual(r[2]["result"]["structuredContent"], {"n": 1})

    def test_conectar_claude_de_escritorio_sin_romper_su_configuracion(self):
        # Donde la busca mcp_conectar.py en cada sistema (en el Mac, Library/Application Support).
        partes = ("Library", "Application Support", "Claude") if sys.platform == "darwin" else (".config", "Claude")
        carpeta = os.path.join(self.tmp.name, *partes)
        os.makedirs(carpeta)
        ruta = os.path.join(carpeta, "claude_desktop_config.json")
        original = {"mcpServers": {"otro": {"command": "node", "args": ["x.js"]}}, "preferencia": 1}
        json.dump(original, open(ruta, "w"))
        r = self.conectar("conectar", "claude_desktop")
        self.assertTrue(r["ok"], r)
        d = json.load(open(ruta))
        self.assertEqual(d["mcpServers"]["otro"], original["mcpServers"]["otro"])
        self.assertEqual(d["preferencia"], 1)
        self.assertEqual([os.path.realpath(x) for x in d["mcpServers"]["prueba"]["args"]], [os.path.realpath(os.path.join(self.app, "bin", "mcp_servidor.py"))])
        self.assertEqual(json.load(open(ruta + ".antes-de-prueba")), original)
        c = {x["id"]: x for x in r["clientes"]}["claude_desktop"]
        self.assertEqual((c["instalado"], c["conectado"], c["al_dia"]), (True, True, True))
        self.assertEqual([h["nombre"] for h in r["herramientas"]], ["anotar", "buscar", "enorme", "falla", "ruidosa"])
        self.assertFalse({h["nombre"]: h for h in r["herramientas"]}["anotar"]["activa"])
        # La app se movió: reparar la deja apuntando a la ruta nueva.
        d["mcpServers"]["prueba"]["args"] = ["/ruta/vieja/mcp_servidor.py"]
        json.dump(d, open(ruta, "w"))
        self.assertEqual(self.conectar("reparar")["arreglados"], ["claude_desktop"])
        self.assertEqual([os.path.realpath(x) for x in json.load(open(ruta))["mcpServers"]["prueba"]["args"]],
                         [os.path.realpath(os.path.join(self.app, "bin", "mcp_servidor.py"))])
        r = self.conectar("quitar", "claude_desktop")
        self.assertTrue(r["ok"])
        self.assertEqual(json.load(open(ruta))["mcpServers"], original["mcpServers"])

    def test_archivo_roto_no_se_toca_y_quitar_no_crea_nada(self):
        carpeta = os.path.join(self.tmp.name, ".gemini", "config")
        os.makedirs(carpeta)
        ruta = os.path.join(carpeta, "mcp_config.json")
        open(ruta, "w").write("{roto")
        r = self.conectar("conectar", "antigravity")
        self.assertFalse(r["ok"])
        self.assertEqual(open(ruta).read(), "{roto")
        os.remove(ruta)
        self.assertTrue(self.conectar("quitar", "antigravity")["ok"])
        self.assertFalse(os.path.exists(ruta))
        r = self.conectar("conectar", "claude_desktop")
        self.assertFalse(r["ok"])
        self.assertEqual((r["error"], r["valores"]["ia"]), ("No encontré {ia} en este computador.", "Claude (app de escritorio)"))

    def test_conectar_con_el_comando_de_la_ia(self):
        r = self.conectar("conectar", "claude_code")
        self.assertTrue(r["ok"], r)
        argv = self.registro_ia()["argv"]
        self.assertEqual(argv[1:6], ["mcp", "add", "--scope", "user", "prueba"])
        real = os.path.realpath  # en el Mac, /var es /private/var
        self.assertEqual(real(argv[-1]), real(os.path.join(self.app, "bin", "mcp_servidor.py")))
        self.assertEqual(real(self.registro_ia()["cwd"]), real(self.tmp.name))
        r = self.conectar("conectar", "codex")
        self.assertEqual(self.registro_ia()["argv"][1:4], ["mcp", "add", "prueba"])
        salida = os.path.join(self.tmp.name, "s.json")
        r = subprocess.run([sys.executable, "mcp_conectar.py", "conectar", "--rm", salida], capture_output=True, text=True,
                           cwd=os.path.join(self.app, "bin"), env=self.env)
        self.assertEqual(r.returncode, 2, "un cliente que no está en la lista no corre nada")


class Herramienta(AppDePrueba):
    def test_revisar_la_base(self):
        r = correr(PIEZA, "revisar")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_requisitos_y_config(self):
        lock = json.load(open(os.path.join(self.app, "piezas.json")))
        self.assertEqual(sorted(lock["piezas"]), ["ia", "nucleo"])
        self.assertEqual(json.load(open(os.path.join(self.app, "app.json")))["config"]["ia"], ["claude", "codex", "gemini"])

    def test_no_pisa_lo_que_la_app_cambio(self):
        ruta = os.path.join(self.app, "bin", "ia.py")
        with open(ruta, "a") as f:
            f.write("\n# mejora propia de la app\n")
        lock_ruta = os.path.join(self.app, "piezas.json")
        lock = json.load(open(lock_ruta))
        lock["piezas"]["ia"]["version"] = "0.0.1"
        json.dump(lock, open(lock_ruta, "w"))
        self.assertIn("la app cambió bin/ia.py", correr(PIEZA, "estado", self.app).stdout)
        self.assertIn("no actualicé bin/ia.py", correr(PIEZA, "actualizar", self.app).stdout)
        self.assertIn("mejora propia", open(ruta).read())
        self.assertIn("+# mejora propia", correr(PIEZA, "diferencias", self.app, "ia").stdout)

    def test_planeada_no_se_agrega(self):
        r = correr(PIEZA, "agregar", "youtube", self.app)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("aún no está extraída", r.stderr)

    def test_ficha_suma_todo(self):
        r = correr(PIEZA, "ficha", "microfono", "--plataformas", "mac,android", "--json")
        f = json.loads(r.stdout)
        ids = [x["id"] for x in f["piezas"]]
        self.assertIn("nucleo", ids)            # siempre, por estar en mac
        self.assertIn("host-tauri", ids)
        self.assertNotIn("host-mac", ids)         # retirada: la reemplaza host-tauri
        self.assertNotIn("host-escritorio", ids)
        self.assertEqual([x["clave"] for x in f["permisos"]["android"]], ["RECORD_AUDIO"])
        self.assertTrue(any(x["pieza"] == "nucleo" and x["plataformas"] == ["android"] for x in f["faltan_en"]))
        self.assertEqual(f["pantallas"][0]["nombre"], "Idioma")

    def test_iniciar_deja_al_dia_y_plugin(self):
        self.assertTrue(os.path.isfile(os.path.join(self.app, ".github", "workflows", "pieza-al-dia.yml")))
        with open(os.path.join(self.app, ".claude", "settings.json")) as f:
            ajustes = json.load(f)
        # Se SUGIERE el marketplace de Pieza; nadie lo recibe activado por abrir el repo.
        self.assertIn("pieza", ajustes["extraKnownMarketplaces"])
        self.assertNotIn("enabledPlugins", ajustes)

    def test_en_json_conserva_su_sangria(self):
        ruta = os.path.join(self.app, "ui", "idiomas", "en.json")
        with open(ruta, "w") as f:
            json.dump({"codigo": "en", "nombre": "English", "textos": {"Hola": "Hello"}}, f, indent=2)
        correr(PIEZA, "agregar", "i18n", self.app)
        texto = open(ruta).read()
        self.assertIn('\n  "codigo"', texto)
        self.assertIn("Hola", texto)

    def test_archivos_solo_de_algunas_plataformas(self):
        ruta = os.path.join(self.app, "app.json")
        a = json.load(open(ruta)); a["plataformas"] = ["mac"]; json.dump(a, open(ruta, "w"))
        correr(PIEZA, "agregar", "host-mac", self.app)
        correr(PIEZA, "agregar", "actualizaciones", self.app)
        self.assertTrue(os.path.isfile(os.path.join(self.app, "app", "Sources", "PiezaActualizaciones", "Actualizaciones.swift")))
        self.assertFalse(os.path.exists(os.path.join(self.app, "escritorio", "src", "actualizaciones.js")))
        self.assertFalse(os.path.exists(os.path.join(self.app, "escritorio", "src", "pieza", "actualizaciones.rs")), "solo con host-tauri")

    def test_si_pide_mas_no_se_actualiza_solo(self):
        nueva = self._base_con_version("mejora", cambiar={"red": ["ejemplo.com"]})
        e = json.loads(correr(nueva, "estado", self.app, "--json").stdout)
        ia = next(x for x in e if x["pieza"] == "ia")
        self.assertEqual((ia["pide_mas"], ia["automatico"]), (True, False))
        self.assertEqual(correr(nueva, "actualizar", self.app, "--automatico").stdout.strip(), "")

    def test_archivo_que_ya_no_es_de_la_pieza(self):
        nueva = self._base_con_version("arreglo")
        base = os.path.dirname(os.path.dirname(nueva))
        ruta = os.path.join(base, "piezas", "ia", "pieza.json")
        with open(ruta) as f:
            p = json.load(f)
        p["archivos"] = {"python/ia.py": "bin/ia_nueva.py"}
        with open(ruta, "w") as f:
            json.dump(p, f)
        salida = correr(nueva, "actualizar", self.app).stdout
        self.assertIn("ya no es de la pieza: bin/ia.py", salida)
        self.assertTrue(os.path.isfile(os.path.join(self.app, "bin", "ia.py")))  # nunca se borra solo
        lock = json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]["ia"]["archivos"]
        self.assertEqual(sorted(lock), ["bin/ia_nueva.py"])

    def _base_con_version(self, tipo, version=None, seguridad=False, cambiar=None):
        """Copia la base a un temporal y le sube la versión a «ia» con un cambio de este tipo (y lo que diga `cambiar`)."""
        import shutil
        base = os.path.join(self.tmp.name, "base")
        shutil.copytree(BASE, base, ignore=shutil.ignore_patterns(".git", "__pycache__", "target"))
        ruta = os.path.join(base, "piezas", "ia", "pieza.json")
        with open(ruta) as f:
            p = json.load(f)
        x, y, z = map(int, p["version"].split("."))
        version = version or (f"{x}.{y + 1}.0" if tipo == "rompe" else f"{x}.{y}.{z + 1}")
        p["version"] = version
        p.update(cambiar or {})
        c = {"version": version, "tipo": tipo, "resumen": "prueba", "seguridad": seguridad}
        if tipo == "rompe":
            c["migrar"] = ["Cambia ejecutar_ia por ejecutar."]
        p["cambios"].insert(0, c)
        with open(ruta, "w") as f:
            json.dump(p, f)
        with open(os.path.join(base, "piezas", "ia", "python", "ia.py"), "a") as f:
            f.write("\n# versión nueva\n")
        return os.path.join(base, "herramientas", "pieza.py")

    def test_arreglo_se_actualiza_solo(self):
        nueva = self._base_con_version("arreglo", seguridad=True)
        e = json.loads(correr(nueva, "estado", self.app, "--json").stdout)
        ia = next(x for x in e if x["pieza"] == "ia")
        self.assertEqual((ia["tipo"], ia["seguridad"], ia["automatico"]), ("arreglo", True, True))
        self.assertIn("(seguridad)", correr(nueva, "actualizar", self.app, "--automatico").stdout)
        self.assertIn("# versión nueva", open(os.path.join(self.app, "bin", "ia.py")).read())
        self.assertEqual(correr(nueva, "aviso", self.app).stdout.strip(), "")

    def test_lo_que_rompe_va_a_mano_con_pasos(self):
        nueva = self._base_con_version("rompe")
        self.assertIn("a mano", correr(nueva, "estado", self.app).stdout)
        self.assertEqual(correr(nueva, "actualizar", self.app, "--automatico").stdout.strip(), "")
        self.assertIn("Cambia ejecutar_ia por ejecutar.", correr(nueva, "aviso", self.app).stdout)

    def test_archivo_cambiado_por_la_app_va_a_mano(self):
        with open(os.path.join(self.app, "bin", "ia.py"), "a") as f:
            f.write("\n# propio\n")
        nueva = self._base_con_version("arreglo")
        self.assertEqual(correr(nueva, "actualizar", self.app, "--automatico").stdout.strip(), "")
        self.assertIn("pieza.py diferencias", correr(nueva, "aviso", self.app).stdout)

    def test_skills_para_codex_conservan_lo_local(self):
        destino = os.path.join(self.tmp.name, "agents-skills")
        env = {**os.environ, "PIEZA_SKILLS_DESTINO": destino}
        mia = os.path.join(destino, "lanzar-proyecto-open-source", "SKILL.md")
        os.makedirs(os.path.dirname(mia))
        with open(mia, "w") as f:
            f.write("---\nname: x\n---\nVersión del flujo: 1\n\n## Configuración local\n- mi computador\n")
        self.assertIn("hay", correr(PIEZA, "skills", "estado", "codex", env=env).stdout)
        self.assertEqual(correr(PIEZA, "skills", "instalar", "codex", env=env).returncode, 0)
        texto = open(mia).read()
        self.assertIn("## Configuración local\n- mi computador", texto)
        self.assertNotIn("Versión del flujo: 1\n", texto)
        self.assertNotIn("hay", correr(PIEZA, "skills", "estado", "codex", env=env).stdout)

    def test_extension_de_gemini(self):
        import tomllib
        with open(os.path.join(BASE, "gemini-extension.json")) as f:
            ext = json.load(f)
        self.assertEqual(ext["name"], "pieza")
        self.assertTrue(os.path.isfile(os.path.join(BASE, ext["contextFileName"])))
        for c in ("crear", "revisar"):
            with open(os.path.join(BASE, "commands", "pieza", c + ".toml"), "rb") as f:
                t = tomllib.load(f)
            self.assertIn("{{args}}", t["prompt"])
        with open(os.path.join(BASE, ".claude-plugin", "plugin.json")) as f:
            self.assertEqual(json.load(f)["version"], ext["version"], "sube la versión igual en plugin.json y gemini-extension.json")
        for s in os.listdir(os.path.join(BASE, "skills")):
            self.assertTrue(os.path.isfile(os.path.join(BASE, ".agents", "skills", s, "SKILL.md")), s)

    def test_regla_de_oro_texto_nunca_en_args(self):
        sys.path.insert(0, os.path.join(BASE, "herramientas"))
        import pieza
        mala = {"id": "mala", "version": "1.0.0", "archivos": {}, "categoria": "base", "descripcion": "x", "recomendar": {"cuando": "x"},
                "acciones": {"x": {"script": "x.py", "scriptDeLaApp": True, "args": ["$pedido"], "limite": 10,
                                   "datos": {"pedido": {"tipo": "texto", "max": 100}}}}}
        errores = " ".join(pieza.errores_pieza("mala", mala, {}))
        self.assertIn("solo puede ser un campo enum o entero", errores)

    def test_migrar_es_una_lista_de_pasos(self):
        sys.path.insert(0, os.path.join(BASE, "herramientas"))
        import pieza
        base = {"id": "x", "version": "0.2.0", "archivos": {}, "categoria": "base", "descripcion": "x", "recomendar": {"cuando": "x"},
                "licencia": "MPL-2.0"}
        texto = {**base, "cambios": [{"version": "0.2.0", "tipo": "rompe", "resumen": "x", "migrar": "1. Haz esto. 2. Y esto."},
                                     {"version": "0.1.0", "tipo": "inicial", "resumen": "x"}]}
        lista = {**texto, "cambios": [{**texto["cambios"][0], "migrar": ["Haz esto.", "Y esto."]}, texto["cambios"][1]]}
        self.assertIn("«migrar» es una lista", " ".join(pieza.errores_pieza("x", texto, {})))
        self.assertNotIn("«migrar»", " ".join(pieza.errores_pieza("x", lista, {})))


if __name__ == "__main__":
    unittest.main()


class Comunidad(unittest.TestCase):
    """El catálogo que crece solo: se encuentra, se valida, se revisa y solo lo revisado se instala sin preguntar."""

    def setUp(self):
        sys.path.insert(0, os.path.join(BASE, "herramientas"))
        import comunidad
        import pieza
        self.c, self.p = comunidad, pieza
        self.tmp = tempfile.TemporaryDirectory()
        self.antes = comunidad.CATALOGO
        comunidad.CATALOGO = os.path.join(self.tmp.name, "catalogo.json")
        self.antes_p = comunidad.PROYECTOS
        comunidad.PROYECTOS = os.path.join(self.tmp.name, "proyectos.json")
        self.repos = {}  # repo → {commit, archivos}
        prueba = self

        class RedFalsa:
            def json(self, url):
                if "/search/repositories" in url:
                    return {"items": [{"full_name": r, "default_branch": "main", "name": r.split("/")[1],
                                       "description": "Una app\x00 de prueba", "homepage": "javascript:alert(1)"}
                                      for r in prueba.repos]}
                repo = url.split("/repos/")[1].split("/commits/")[0]
                return {"sha": prueba.repos[repo]["commit"]}

            def archivo(self, repo, commit, ruta):
                r = prueba.repos[repo]
                if commit not in r["versiones"]:
                    raise ValueError("commit desconocido")
                if ruta not in r["versiones"][commit]:
                    raise ValueError("404")
                return r["versiones"][commit][ruta].encode()

        self.red = RedFalsa()
        comunidad.Red = RedFalsa

    def tearDown(self):
        self.c.CATALOGO = self.antes
        self.c.PROYECTOS = self.antes_p
        self.p._EXTRA.clear()
        self.p._FUENTE.clear()
        self.tmp.cleanup()

    ICONO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9"/></svg>'

    def publicar(self, repo, commit, codigo="print('hola')\n", icono=None, **cambios):
        pj = {"formato": 1, "id": "saludo", "version": "1.0.0", "estado": "lista", "nombre": "Saludo", "icono": "icono.svg", "licencia": "MIT",
              "categoria": "interfaz",
              "descripcion": "Saluda.", "recomendar": {"cuando": "Para saludar."}, "requiere": ["nucleo"],
              "archivos": {"python/saludo.py": "bin/saludo.py"},
              "cambios": [{"version": "1.0.0", "tipo": "inicial", "resumen": "Primera."}], **cambios}
        r = self.repos.setdefault(repo, {"versiones": {}})
        r["commit"] = commit
        r["versiones"][commit] = {"pieza.json": json.dumps(pj), "python/saludo.py": codigo, "icono.svg": icono or self.ICONO}

    def entrada(self):
        return self.c.entrada("saludo")

    def test_se_encuentra_sin_revisar_y_se_revisa(self):
        self.publicar("ana/saludo", "a" * 40)
        self.assertIn("+ saludo", " ".join(self.c.buscar(self.red, hoy="2026-10-30")))
        self.assertEqual(self.entrada()["revision"]["estado"], "sin-revisar")
        self.c.revisar("saludo", "aprobar", "a" * 40, hoy="2026-10-31")
        self.assertEqual(self.entrada()["revision"]["estado"], "revisada")
        # Un commit nuevo con los mismos archivos sigue revisado; si cambia el código, vuelve a «sin revisar».
        self.publicar("ana/saludo", "b" * 40)
        self.c.buscar(self.red)
        self.assertEqual(self.entrada()["revision"]["estado"], "revisada")
        self.publicar("ana/saludo", "c" * 40, codigo="import os; os.system('algo')\n")
        self.c.buscar(self.red)
        self.assertEqual(self.entrada()["revision"]["estado"], "sin-revisar")

    def test_reglas_de_seguridad_y_ids(self):
        self.publicar("ana/malo", "d" * 40, acciones={"x": {"script": "saludo.py", "args": ["$t"], "limite": 9,
                                                            "datos": {"t": {"tipo": "texto", "max": 9}}}})
        self.publicar("ana/oficial", "e" * 40, id="ia")
        resumen = " ".join(self.c.buscar(self.red))
        self.assertIn("enum o entero", resumen)
        self.assertIn("es de una pieza oficial", resumen)
        self.assertEqual(self.c.leer()["piezas"], [])

    def test_revision_atada_y_rechazo_pegajoso(self):
        self.publicar("ana/saludo", "a" * 40)
        self.c.buscar(self.red)
        with self.assertRaises(SystemExit):  # se aprueba lo que se leyó, no lo que haya ahora
            self.c.revisar("saludo", "aprobar", "b" * 40)
        self.c.revisar("saludo", "aprobar", "aaaaaaa")
        # Cambia el código: queda sin revisar, pero se sigue instalando lo último revisado.
        self.publicar("ana/saludo", "c" * 40, codigo="otra\n")
        self.c.buscar(self.red)
        e = self.entrada()
        self.assertEqual((e["revision"]["estado"], e["revision"]["ultima_revisada"]["commit"]), ("sin-revisar", "a" * 40))
        carpeta, f = self.c.descargar("saludo", red=self.red, cache=os.path.join(self.tmp.name, "k"))
        self.assertEqual((f["commit"], f["revision"]), ("a" * 40, "revisada"))
        # Un rechazo es del repo: un commit nuevo no lo devuelve a la página.
        self.c.revisar("saludo", "rechazar", "c" * 40, "no")
        self.publicar("ana/saludo", "d" * 40, codigo="otra mas\n")
        self.c.buscar(self.red)
        self.assertEqual(self.entrada()["revision"]["estado"], "rechazada")

    def test_pieza_rara_no_tumba_el_catalogo_y_busqueda_vacia_no_borra(self):
        self.publicar("ana/saludo", "a" * 40)
        for i, raro in enumerate(({"permisos": ["x"]}, {"cambios": ["x"]}, {"acciones": {"a": "x"}}, {"red": [5]},
                                  {"archivos": {"python/saludo.py": 5}}, {"archivos": {"python/saludo.py": ".github/workflows/x.yml"}},
                                  {"archivos": {"python/saludo.py": ".git/hooks/pre-commit"}})):
            self.publicar(f"ana/raro{i}", f"{i:x}" * 40, id=f"raro{i}", **raro)
        self.c.buscar(self.red)
        self.assertEqual([x["id"] for x in self.c.leer()["piezas"]], ["saludo"])
        self.c.revisar("saludo", "aprobar", "a" * 40)
        guardado = self.c.Red.json
        self.c.Red.json = lambda yo, url: {"items": [], "incomplete_results": True} if "search" in url else guardado(yo, url)
        try:
            self.c.buscar(self.red)
        finally:
            self.c.Red.json = guardado
        self.assertEqual(self.entrada()["revision"]["estado"], "revisada")

    def test_icono_obligatorio_y_seguro(self):
        self.publicar("ana/saludo", "a" * 40)
        self.c.buscar(self.red)
        e = self.entrada()
        self.assertIn("<circle", e["pieza"]["icono_svg"])
        self.assertIn("icono.svg", e["huellas"])  # cambiar el ícono también vuelve a «sin revisar»
        self.publicar("ana/raro", "b" * 40, id="raro", icono='<svg viewBox="0 0 24 24"><script>alert(1)</script></svg>')
        self.publicar("ana/sin", "c" * 40, id="sin")
        del self.repos["ana/sin"]["versiones"]["c" * 40]["icono.svg"]
        self.publicar("ana/rojo", "d" * 40, id="rojo", icono='<svg viewBox="0 0 24 24"><path d="M1 1" stroke="red"/></svg>')
        resumen = " ".join(self.c.buscar(self.red))
        self.assertIn("<script>", resumen)
        self.assertIn("no pude leer el ícono", resumen)
        self.assertIn("currentColor", resumen)
        self.assertEqual([x["id"] for x in self.c.leer()["piezas"]], ["saludo"])

    def test_icono_validador(self):
        import icono
        for malo in ('<svg viewBox="0 0 24 24"><image href="https://x"/></svg>',
                     '<svg viewBox="0 0 24 24" onload="x"/>',
                     '<svg viewBox="0 0 24 24"><style>*{}</style></svg>',
                     '<!DOCTYPE svg [<!ENTITY a "b">]><svg viewBox="0 0 24 24"/>',
                     '<svg viewBox="0 0 24 24"><path d="M1" fill="url(javascript:x)"/></svg>',
                     '<svg><path d="M1"/></svg>', "x" * 9000, "no es svg"):
            self.assertTrue(icono.errores(malo), malo[:40])
        self.assertEqual(icono.errores('<svg viewBox="0 0 64 64"><rect width="64" height="64" fill="#1f1b2e"/></svg>'), [])
        for pid in self.p.todas():
            ruta = os.path.join(self.p.carpeta_de(pid), "icono.svg")
            self.assertEqual(icono.errores(open(ruta).read(), solo_current=True), [], pid)

    def test_proyectos_con_icono_y_revision(self):
        import pagina
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#123456"/></svg>'
        self.repos["ana/notas"] = {"commit": "a" * 40, "versiones": {"a" * 40: {"app.json": '{"icono": "arte/logo.svg"}',
                                                                               "arte/logo.svg": svg}}}
        self.repos["ana/fea"] = {"commit": "b" * 40, "versiones": {"b" * 40: {"docs/favicon.svg": "<svg><script/></svg>",
                                                                             "favicon.svg": svg}}}
        self.repos["pieza-app/pieza"] = {"commit": "c" * 40, "versiones": {"c" * 40: {}}}
        resumen = " ".join(self.c.buscar_proyectos(self.red, hoy="2026-10-30"))
        self.assertIn("+ ana/notas", resumen)
        reg = {e["repo"]: e for e in self.c.leer_proyectos()["proyectos"]}
        self.assertEqual(reg["ana/notas"]["icono"], "arte/logo.svg")
        self.assertEqual(reg["ana/fea"]["icono"], "favicon.svg")  # el inseguro se salta
        self.assertEqual(reg["pieza-app/pieza"]["icono_svg"], "")
        self.assertEqual(reg["ana/notas"]["pagina"], "")  # solo https
        self.assertNotIn("\x00", reg["ana/notas"]["descripcion"])
        self.assertEqual(reg["ana/notas"]["revision"]["estado"], "sin-revisar")
        self.c.revisar_proyecto("ana/notas", "aprobar", hoy="2026-10-31")
        self.c.revisar_proyecto("ana/fea", "rechazar", "No es una app hecha con Pieza")
        # Volver a buscar no borra la revisión.
        self.c.buscar_proyectos(self.red)
        reg = {e["repo"]: e for e in self.c.leer_proyectos()["proyectos"]}
        self.assertEqual(reg["ana/notas"]["revision"]["estado"], "revisado")
        # La página: sin los rechazados, la familia primero, íconos copiados.
        antes = (pagina.DATOS, pagina.ICONOS)
        pagina.DATOS, pagina.ICONOS = os.path.join(self.tmp.name, "datos"), os.path.join(self.tmp.name, "iconos")
        try:
            with open(pagina.proyectos()) as f:
                d = json.load(f)
        finally:
            pagina.DATOS, pagina.ICONOS = antes
        self.assertEqual([x["repo"] for x in d["proyectos"]], ["pieza-app/pieza", "ana/notas"])
        self.assertEqual((d["total"], d["aprobados"]), (2, 1))
        self.assertEqual(d["proyectos"][1]["icono"], "iconos/proyectos/ana--notas.svg")
        self.assertEqual(d["proyectos"][0]["icono"], "")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, "iconos", "proyectos", "ana--notas.svg")))

    def test_instalar_solo_lo_revisado_o_con_permiso(self):
        app = os.path.join(self.tmp.name, "app")
        os.makedirs(app)
        self.p.escribir(os.path.join(app, "app.json"), {"nombre": "Prueba", "id": "prueba", "config": {}})
        cache = os.path.join(self.tmp.name, "cache")
        self.publicar("ana/saludo", "a" * 40)
        self.c.buscar(self.red)
        with self.assertRaises(SystemExit) as e:
            self.c.descargar("saludo", red=self.red, cache=cache)
        self.assertIn("--sin-revisar", str(e.exception))
        carpeta, fuente = self.c.descargar("saludo", sin_revisar=True, red=self.red, cache=cache)
        self.assertEqual(fuente["revision"], "sin-revisar")
        self.c.revisar("saludo", "aprobar", self.entrada()["commit"])
        # Lo revisado se baja del commit revisado, aunque el repo haya cambiado después, y se compara con su huella.
        self.publicar("ana/saludo", "f" * 40, codigo="otra cosa\n")
        carpeta, fuente = self.c.descargar("saludo", red=self.red, cache=cache)
        self.assertEqual((fuente["revision"], fuente["commit"]), ("revisada", "a" * 40))
        with open(os.path.join(carpeta, "python", "saludo.py")) as f:
            self.assertEqual(f.read(), "print('hola')\n")
        # Si alguien cambia lo que hay en ese commit (o la red miente), no se instala nada.
        self.repos["ana/saludo"]["versiones"]["a" * 40]["python/saludo.py"] = "trampa\n"
        with self.assertRaises(SystemExit) as e:
            self.c.descargar("saludo", red=self.red, cache=os.path.join(self.tmp.name, "cache2"))
        self.assertIn("no coincide", str(e.exception))

    def test_agregar_a_una_app(self):
        app = os.path.join(self.tmp.name, "app")
        os.makedirs(app)
        self.p.escribir(os.path.join(app, "app.json"), {"nombre": "Prueba", "id": "prueba", "config": {}})
        self.publicar("ana/saludo", "a" * 40)
        self.c.buscar(self.red)
        self.c.revisar("saludo", "aprobar", self.entrada()["commit"])
        antes = self.c.descargar
        self.c.descargar = lambda pid, sin_revisar=False: antes(pid, sin_revisar, red=self.red, cache=os.path.join(self.tmp.name, "c"))
        try:
            self.p.agregar("saludo", app)
        finally:
            self.c.descargar = antes
        lock = self.p.candado(app)["piezas"]
        self.assertEqual(sorted(lock), ["nucleo", "saludo"])
        self.assertEqual(lock["saludo"]["fuente"], {"repo": "ana/saludo", "commit": "a" * 40, "revision": "revisada"})
        self.assertTrue(os.path.isfile(os.path.join(app, "bin", "saludo.py")))

    def test_rechazada_nunca_se_instala(self):
        self.publicar("ana/saludo", "a" * 40)
        self.c.buscar(self.red)
        self.c.revisar("saludo", "rechazar", self.entrada()["commit"], "lee archivos de más")
        with self.assertRaises(SystemExit) as e:
            self.c.descargar("saludo", sin_revisar=True, red=self.red, cache=self.tmp.name)
        self.assertIn("rechazada", str(e.exception))


class PiezasDeInterfaz(unittest.TestCase):
    """i18n, bienvenida y actualizaciones: se agregan a una app con sus requisitos, textos y config, y su código no trae
    nada de una app. La lógica de JavaScript se prueba en pruebas/piezas_js.mjs (node --test)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "prueba")
        os.makedirs(os.path.join(self.app, "ui", "idiomas"))
        with open(os.path.join(self.app, "ui", "idiomas", "en.json"), "w") as f:
            json.dump({"codigo": "en", "nombre": "English", "textos": {"Atrás": "Volver (de la app)"}}, f)
        self.assertEqual(correr(PIEZA, "iniciar", self.app, "prueba", "Prueba").returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def ficha(self, pid):
        with open(os.path.join(BASE, "piezas", pid, "pieza.json"), encoding="utf-8") as f:
            return json.load(f)

    def fuente(self, pid, ruta):
        with open(os.path.join(BASE, "piezas", pid, ruta), encoding="utf-8") as f:
            return f.read()

    def test_bienvenida_trae_i18n_textos_y_config(self):
        r = correr(PIEZA, "agregar", "bienvenida", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        for ruta in ("ui/i18n.js", "ui/bienvenida.js", "ui/bienvenida.css"):
            self.assertTrue(os.path.isfile(os.path.join(self.app, ruta)), ruta)
        lock = json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]
        self.assertEqual(sorted(lock), ["bienvenida", "i18n"])
        en = json.load(open(os.path.join(self.app, "ui", "idiomas", "en.json")))["textos"]
        self.assertEqual(en["Atrás"], "Volver (de la app)", "lo que la app ya tenía no se pisa")
        self.assertEqual(en["Siguiente"], "Next")
        config = json.load(open(os.path.join(self.app, "app.json")))["config"]
        self.assertIn("idioma_ui", config)
        self.assertEqual(config["bienvenida"], "bool")

    def test_actualizaciones_queda_en_su_target_y_en_escritorio(self):
        for host in ("host-mac", "host-escritorio"):
            self.assertEqual(correr(PIEZA, "agregar", host, self.app).returncode, 0)
        r = correr(PIEZA, "agregar", "actualizaciones", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.app, "app", "Sources", "PiezaActualizaciones", "Actualizaciones.swift")))
        self.assertTrue(os.path.isfile(os.path.join(self.app, "escritorio", "src", "actualizaciones.js")))

    def test_textos_completos_y_con_los_mismos_marcadores(self):
        import re
        marcas = lambda t: sorted(re.findall(r"\{(\w+)\}", t))
        for pid in ("i18n", "bienvenida", "actualizaciones", "host-ui", "componentes", "tema"):
            for es, en in self.ficha(pid)["textos"].items():
                self.assertEqual(marcas(es), marcas(en), f"{pid}: {es}")
        bv = self.ficha("bienvenida")["textos"]
        codigo = self.fuente("bienvenida", "ui/bienvenida.js")
        usados = set(re.findall(r'\bT\("([^"]+)"', codigo)) | set(re.findall(r'titulo \|\| "([^"]+)"', codigo))
        self.assertTrue(usados)
        self.assertEqual(usados - set(bv), set(), "cada frase de la bienvenida tiene su inglés en pieza.json")
        act = self.ficha("actualizaciones")["textos"]
        js = self.fuente("actualizaciones", "escritorio/actualizaciones.js")
        bloque = js[js.index("const TEXTOS = {"):js.index("};", js.index("const TEXTOS = {"))]
        frases = re.findall(r':\s*"([^"]+)"', bloque)
        self.assertEqual(len(frases), 7)
        self.assertEqual(set(frases) - set(act), set())

    def test_componentes_trae_i18n_y_tema_con_sus_textos(self):
        r = correr(PIEZA, "agregar", "componentes", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        for ruta in ("ui/i18n.js", "ui/tema.css", "ui/tema.js", "ui/componentes.js", "ui/componentes.css"):
            self.assertTrue(os.path.isfile(os.path.join(self.app, ruta)), ruta)
        lock = json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]
        self.assertEqual(sorted(lock), ["componentes", "i18n", "tema"])
        config = json.load(open(os.path.join(self.app, "app.json")))["config"]
        self.assertEqual(config["tema"], ["sistema", "claro", "oscuro", "vidrio"])
        self.assertIn("--sin-config=tema", r.stdout, "avisa cuándo no hace falta «tema»")
        en = json.load(open(os.path.join(self.app, "ui", "idiomas", "en.json")))["textos"]
        self.assertEqual(en["Usar y probar"], "Use and test")
        self.assertEqual(en["Como el sistema"], "Match system")
        self.assertEqual(correr(PIEZA, "agregar", "host-ui", self.app).returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.app, "ui", "host.js")))

    def test_tema_sin_apariencia_no_suma_tema_a_la_config_ni_al_actualizar(self):
        r = correr(PIEZA, "agregar", "tema", self.app, "--sin-config=tema")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no sumé «tema»", r.stdout)
        self.assertNotIn("tema", json.load(open(os.path.join(self.app, "app.json")))["config"])
        lock = json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]
        self.assertEqual(lock["tema"]["sin_config"], ["tema"])
        # Al actualizar (forzar la copia de nuevo) la decisión se respeta.
        lock["tema"]["version"] = "0.0.1"
        with open(os.path.join(self.app, "piezas.json"), "w") as f:
            json.dump({"formato": 1, "piezas": lock}, f)
        self.assertEqual(correr(PIEZA, "actualizar", self.app, "tema", "--forzar").returncode, 0)
        self.assertNotIn("tema", json.load(open(os.path.join(self.app, "app.json")))["config"])
        self.assertEqual(json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]["tema"]["sin_config"], ["tema"])

    def _base_con(self, cambios):
        """Copia la base a un temporal y sube la versión de cada pieza de `cambios` ({pieza: {tipo, compatible?}})."""
        import shutil
        base = os.path.join(self.tmp.name, "base")
        shutil.copytree(BASE, base, ignore=shutil.ignore_patterns(".git", "__pycache__", "target"))
        for pid, c in cambios.items():
            ruta = os.path.join(base, "piezas", pid, "pieza.json")
            with open(ruta, encoding="utf-8") as f:
                p = json.load(f)
            x, y, z = map(int, p["version"].split("."))
            p["version"] = f"{x}.{y + 1}.0" if c["tipo"] != "arreglo" else f"{x}.{y}.{z + 1}"
            p["compatible"] = {**p.get("compatible", {}), **c.get("compatible", {})}
            p["cambios"].insert(0, {"version": p["version"], "tipo": c["tipo"], "resumen": "prueba",
                                    **({"migrar": ["Nada."]} if c["tipo"] == "rompe" else {})})
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(p, f, ensure_ascii=False)
            primero = next(iter(p["archivos"]))
            with open(os.path.join(base, "piezas", pid, primero), "a") as f:
                f.write("\n/* versión nueva */\n")
        return os.path.join(base, "herramientas", "pieza.py")

    def _versiones(self):
        return {k: v["version"] for k, v in json.load(open(os.path.join(self.app, "piezas.json")))["piezas"].items()}

    def test_actualizar_va_en_orden_de_dependencias_y_cuenta_lo_de_la_misma_pasada(self):
        self.assertEqual(correr(PIEZA, "agregar", "componentes", self.app).returncode, 0)
        tema = self.ficha("tema")["version"]
        x, y, _ = map(int, tema.split("."))
        nueva = self._base_con({"tema": {"tipo": "mejora"},
                                "componentes": {"tipo": "mejora", "compatible": {"tema": f">={x}.{y + 1}.0 <1.0.0"}}})
        e = {x["pieza"]: x for x in json.loads(correr(nueva, "estado", self.app, "--json").stdout)}
        self.assertTrue(e["componentes"]["choques"], "sola, componentes chocaría con el tema de antes")
        self.assertEqual(e["componentes"]["juntas"], ["tema"])
        self.assertTrue(e["componentes"]["automatico"] and e["tema"]["automatico"], "juntas, las dos se actualizan solas")
        self.assertIn("se actualizan juntas", correr(nueva, "estado", self.app).stdout)
        r = correr(nueva, "actualizar", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("no actualicé", r.stdout)
        self.assertLess(r.stdout.index("↑ tema"), r.stdout.index("↑ componentes"), "lo requerido va primero")
        v = self._versiones()
        self.assertEqual((v["tema"], v["componentes"]), (f"{x}.{y + 1}.0", self._version_de(nueva, "componentes")))
        self.assertIn("versión nueva", open(os.path.join(self.app, "ui", "componentes.js")).read())

    def _version_de(self, pieza_py, pid):
        base = os.path.dirname(os.path.dirname(pieza_py))
        return json.load(open(os.path.join(base, "piezas", pid, "pieza.json")))["version"]

    def test_actualizar_una_trae_lo_que_necesita_y_aviso_dice_como(self):
        self.assertEqual(correr(PIEZA, "agregar", "componentes", self.app).returncode, 0)
        x, y, _ = map(int, self.ficha("tema")["version"].split("."))
        nueva = self._base_con({"tema": {"tipo": "rompe"},
                                "componentes": {"tipo": "rompe", "compatible": {"tema": f">={x}.{y + 1}.0 <1.0.0"}}})
        aviso = correr(nueva, "aviso", self.app).stdout
        self.assertIn("pieza.py actualizar . componentes tema", aviso)
        self.assertEqual(correr(nueva, "actualizar", self.app, "--automatico").stdout.strip(), "", "lo que rompe, nunca solo")
        r = correr(nueva, "actualizar", self.app, "componentes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(la necesita componentes)", r.stdout)
        self.assertEqual(self._versiones()["tema"], f"{x}.{y + 1}.0")
        self.assertEqual(correr(nueva, "aviso", self.app).stdout.strip(), "")

    def test_si_no_hay_version_que_sirva_no_se_toca(self):
        self.assertEqual(correr(PIEZA, "agregar", "componentes", self.app).returncode, 0)
        x, y, _ = map(int, self.ficha("tema")["version"].split("."))
        nueva = self._base_con({"componentes": {"tipo": "mejora", "compatible": {"tema": f">={x}.{y + 5}.0 <1.0.0"}}})
        antes = self._versiones()
        r = correr(nueva, "actualizar", self.app)
        self.assertIn("! no actualicé componentes", r.stdout)
        self.assertEqual(self._versiones(), antes)
        self.assertIn("todavía no hay una versión de `tema` que sirva", correr(nueva, "aviso", self.app).stdout)

    def test_sin_config_al_actualizar_y_sobre_una_pieza_ya_instalada(self):
        self.assertEqual(correr(PIEZA, "agregar", "componentes", self.app).returncode, 0)
        self.assertEqual(json.load(open(os.path.join(self.app, "app.json")))["config"]["tema"], ["sistema", "claro", "oscuro", "vidrio"])
        r = correr(PIEZA, "agregar", "tema", self.app, "--sin-config=tema")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ya estaba", r.stdout)
        self.assertIn("quité «tema» de app.json", r.stdout)
        self.assertNotIn("tema", json.load(open(os.path.join(self.app, "app.json")))["config"])
        self.assertEqual(json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]["tema"]["sin_config"], ["tema"])
        # actualizar también lo acepta (aunque no haya nada que actualizar), y una clave que la app cambió no se borra.
        app = json.load(open(os.path.join(self.app, "app.json")))
        app["config"]["tema"] = ["sistema", "oscuro"]
        json.dump(app, open(os.path.join(self.app, "app.json"), "w"))
        lock = json.load(open(os.path.join(self.app, "piezas.json")))
        del lock["piezas"]["tema"]["sin_config"]
        json.dump(lock, open(os.path.join(self.app, "piezas.json"), "w"))
        r = correr(PIEZA, "actualizar", self.app, "--sin-config=tema,nada")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("la app la cambió", r.stdout)
        self.assertIn("--sin-config=nada", r.stdout)
        self.assertEqual(json.load(open(os.path.join(self.app, "app.json")))["config"]["tema"], ["sistema", "oscuro"])
        self.assertEqual(json.load(open(os.path.join(self.app, "piezas.json")))["piezas"]["tema"]["sin_config"], ["tema"])

    def test_cada_frase_visible_de_las_piezas_de_interfaz_tiene_su_ingles(self):
        import re
        literal = r'"((?:[^"\\]|\\.)+)"'
        casos = {
            "componentes": (self.fuente("componentes", "ui/componentes.js"), r"\b(?:L|F|T|Tp|tr|aviso)\(" + literal),
            "tema": (self.fuente("tema", "ui/tema.js"), r'\["(?:sistema|claro|oscuro)", ' + literal + r"\]|aria-label=" + literal),
            "host-ui": (self.fuente("host-ui", "ui/host.js"), r"texto: " + literal),
        }
        for pid, (codigo, patron) in casos.items():
            usados = {x for m in re.finditer(patron, codigo) for x in m.groups() if x}
            usados -= {"Guardado"}   # solo en el ejemplo del encabezado
            self.assertTrue(usados, pid)
            self.assertEqual(usados - set(self.ficha(pid)["textos"]), set(), f"{pid}: frases sin inglés en pieza.json")
        # Las frases por defecto de confirmar y el título del formulario, que van en variables.
        comp = self.ficha("componentes")["textos"]
        for x in ("Aceptar", "Cancelar", "Enviar comentarios", "No respondió.", "No se pudo actualizar"):
            self.assertIn(x, comp)

    def test_el_guion_de_swift_solo_mete_lo_variable_con_comillas(self):
        import re
        swift = self.fuente("actualizaciones", "mac/Actualizaciones.swift")
        guiones = re.findall(r'texto = """(.*?)"""', swift, re.S)
        self.assertEqual(len(guiones), 2)
        permitidos = ("comillas(", "paso(", "pid)", "progreso)", "cerrar)")
        for g in guiones:
            for m in re.finditer(r"\\\(", g):
                self.assertTrue(g[m.end():].startswith(permitidos), g[m.start():m.start() + 60])
        # Lo que arma «paso» y «cerrar» también pasa por comillas, y la variable del avance se valida antes.
        self.assertIn('"echo \\(comillas(p + "|" + codigo)) > \\(comillas(e))"', swift)
        self.assertIn('osascript -e \\(comillas(', swift)
        self.assertIn('^[A-Z][A-Z0-9_]{0,40}$', swift)
        self.assertIn("--proto-redir '=https'", swift)

    def test_nada_de_una_app_adentro(self):
        import re
        for pid, rutas in (("i18n", ["ui/i18n.js"]), ("bienvenida", ["ui/bienvenida.js", "ui/bienvenida.css"]),
                           ("actualizaciones", ["mac/Actualizaciones.swift", "escritorio/actualizaciones.js"]),
                           ("host-ui", ["ui/host.js"]), ("tema", ["ui/tema.js", "ui/tema.css"]),
                           ("componentes", ["ui/componentes.js", "ui/componentes.css"])):
            for ruta in rutas:
                self.assertIsNone(re.search(r"esquema|minuta|graba|corta|repasa|alcanc", self.fuente(pid, ruta), re.I), f"{pid}/{ruta}")


class HostGenerico(unittest.TestCase):
    """host-mac y host-escritorio: pieza.py arma acciones.json con las acciones de las piezas y de app.json, y las reglas de
    una acción son las mismas en pieza.py, en el host de Electron (enchufe.js) y en el de Mac (Enchufe.swift)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = os.path.join(self.tmp.name, "prueba")
        os.makedirs(os.path.join(self.app, "bin"))
        self.assertEqual(correr(PIEZA, "iniciar", self.app, "prueba", "Prueba", "--plataformas=mac,linux").returncode, 0)
        with open(os.path.join(self.app, ".gitignore"), "w") as f:
            f.write("/*\n!/app.json\n!/piezas.json\n")

    def tearDown(self):
        self.tmp.cleanup()

    def leer(self, *ruta):
        with open(os.path.join(self.app, *ruta), encoding="utf-8") as f:
            return json.load(f) if ruta[-1].endswith(".json") else f.read()

    def test_agregar_arma_acciones_json_y_lista_blanca(self):
        self.assertEqual(correr(PIEZA, "agregar", "ia", self.app).returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.app, "acciones.json")), "sin host, no hace falta")
        r = correr(PIEZA, "agregar", "host-escritorio", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = correr(PIEZA, "agregar", "host-mac", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        a = self.leer("acciones.json")
        self.assertEqual(a["formato"], 1)
        self.assertEqual(a["acciones"]["probarIA"]["pieza"], "ia")
        self.assertEqual(a["acciones"]["probarIA"]["script"], "ia.py")
        self.assertIn("!/acciones.json", self.leer(".gitignore"))
        for f in ("host.js", "enchufe.js", "procesador.js", "preload.js"):
            self.assertTrue(os.path.isfile(os.path.join(self.app, "escritorio", "src", f)), f)
        for f in ("Host", "Procesador", "Enchufe", "Puente"):
            self.assertTrue(os.path.isfile(os.path.join(self.app, "app", "Sources", "PiezaHost", f + ".swift")), f)
        # piezas.json guarda las acciones de la versión copiada: de ahí sale acciones.json aunque la base cambie.
        self.assertIn("probarIA", self.leer("piezas.json")["piezas"]["ia"]["acciones"])

    def test_acciones_propias_de_la_app(self):
        self.assertEqual(correr(PIEZA, "agregar", "host-escritorio", self.app).returncode, 0)
        app = self.leer("app.json")
        app["acciones"] = {"exportar": {"script": "exportar.py", "args": ["$formato"], "entrada": "archivo", "limite": 60,
                                        "datos": {"formato": {"tipo": "enum", "valores": ["svg", "png"]}, "texto": {"tipo": "texto", "max": 100}},
                                        "responde": "exportado"}}
        with open(os.path.join(self.app, "app.json"), "w") as f:
            json.dump(app, f)
        r = correr(PIEZA, "acciones", self.app)
        self.assertNotEqual(r.returncode, 0, "el script tiene que estar en bin/")
        open(os.path.join(self.app, "bin", "exportar.py"), "w").close()
        r = correr(PIEZA, "acciones", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.leer("acciones.json")["acciones"]["exportar"]["pieza"], "app")
        # El texto de la persona como argumento, nunca.
        app["acciones"]["exportar"]["args"] = ["$texto"]
        with open(os.path.join(self.app, "app.json"), "w") as f:
            json.dump(app, f)
        r = correr(PIEZA, "acciones", self.app)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("enum o entero", r.stdout + r.stderr)
        # Dos con el mismo nombre, tampoco.
        app["acciones"] = {"probarIA": {"script": "exportar.py", "limite": 5}}
        with open(os.path.join(self.app, "app.json"), "w") as f:
            json.dump(app, f)
        self.assertEqual(correr(PIEZA, "agregar", "ia", self.app).returncode, 1)

    def test_mismas_reglas_en_python_js_rust_y_swift(self):
        sys.path.insert(0, os.path.join(BASE, "herramientas"))
        import pieza
        casos = [
            {"script": "a.py", "limite": 5},
            {"script": "a.py", "limite": 0},
            {"script": "a.py", "limite": 5, "args": ["$t"], "datos": {"t": {"tipo": "texto", "max": 9}}, "entrada": "archivo"},
            {"script": "a.py", "limite": 5, "args": ["$n"], "datos": {"n": {"tipo": "entero"}}},
            {"script": "a.py", "limite": 5, "datos": {"t": {"tipo": "texto", "max": 9}}},
            {"script": "a.py", "limite": 5, "datos": {"t": {"tipo": "texto"}}, "entrada": "archivo"},
            {"script": "../a.py", "limite": 5},
            {"script": "a.py", "limite": 5, "args": ["a b"]},
            {"script": "a.py", "limite": 5, "inyectar": {"carpeta": "carpetaActual"}},
            {"script": "a.py", "limite": 5, "inyectar": {"carpeta": "carpetaActual"}, "entrada": "archivo"},
            {"script": "a.py", "limite": 5, "inyectar": {"c": "x"}, "datos": {"c": {"tipo": "bool"}}, "entrada": "archivo"},
            {"script": "a.py", "limite": 5, "cola": "lectura"},
            {"script": "a.py", "limite": 5, "eco": ["ia"], "despues": ["estado"], "responde": "listo", "progreso": "avance"},
            {"script": "a.py", "limite": 5, "responde": "x();alert(1)"},
            {"script": "a.py", "limite": 5, "datos": {"l": {"tipo": "lista", "de": {"tipo": "lista"}}}, "entrada": "archivo"},
            {"script": "a.py", "limite": 5, "datos": {"e": {"tipo": "enum", "valores": ["a b"]}}, "entrada": "archivo"},
            {"script": "a.py", "limite": 5, "datos": {"*": "pasar"}, "entrada": "archivo"},
            {"script": "a.py", "limite": True},
            # 0.2: «limite» "trabajo" o por orden, «maximo» y «vigilar».
            {"script": "a.py", "limite": "trabajo"},
            {"script": "a.py", "limite": "siempre"},
            {"script": "a.py", "args": ["$o"], "datos": {"o": {"tipo": "enum", "valores": ["a", "b"]}},
             "limite": {"segun": "o", "valores": {"a": "trabajo", "b": 60}, "otro": 120}},
            {"script": "a.py", "args": ["$o"], "datos": {"o": {"tipo": "enum", "valores": ["a"]}}, "limite": {"segun": "o", "valores": {"z": 5}, "otro": 5}},
            {"script": "a.py", "args": ["$o"], "datos": {"o": {"tipo": "enum", "valores": ["a"]}}, "limite": {"segun": "o", "valores": {}}},
            {"script": "a.py", "entrada": "archivo", "datos": {"t": {"tipo": "texto", "max": 9}}, "limite": {"segun": "t", "valores": {}, "otro": 5}},
            {"script": "a.py", "args": ["$o"], "datos": {"o": {"tipo": "enum", "valores": ["a"]}}, "limite": {"segun": "o", "valores": {}, "otro": 5, "x": 1}},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "datos": {"t": {"tipo": "texto", "max": 6 * 1024 * 1024}}},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "maximo": 7 * 1024 * 1024, "datos": {"t": {"tipo": "texto", "max": 6 * 1024 * 1024}}},
            {"script": "a.py", "limite": 5, "maximo": 51 * 1024 * 1024},
            {"script": "a.py", "limite": 5, "maximo": True},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "vigilar": "lee", "datos": {"ruta": {"tipo": "rutaRelativa"}}},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "vigilar": "escribe", "datos": {"ruta": {"tipo": "rutaRelativa"}}},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "vigilar": "escribe",
             "datos": {"ruta": {"tipo": "rutaRelativa"}, "texto": {"tipo": "texto", "max": 9}}},
            {"script": "a.py", "limite": 5, "entrada": "archivo", "vigilar": "borra", "datos": {"ruta": {"tipo": "rutaRelativa"}}},
        ]
        py = [not pieza.errores_accion("x", c, None) for c in casos]
        js = subprocess.run(["node", "-e", "const E = require(process.argv[1]); const c = JSON.parse(process.argv[2]);"
                             "console.log(JSON.stringify(c.map((a) => E.erroresAccion('x', a).length === 0)))",
                             os.path.join(BASE, "piezas", "host-escritorio", "escritorio", "enchufe.js"), json.dumps(casos)],
                            capture_output=True, text=True)
        self.assertEqual(js.returncode, 0, js.stderr)
        self.assertEqual(py, json.loads(js.stdout))
        self.assertEqual(py[:4], [True, False, False, True])
        self.assertEqual(py[18:], [True, False, True, False, False, False, False, False, True, False, False, True, False, True, False])
        # Rust (host-tauri): las mismas reglas, compiladas de verdad (si hay cargo; GitHub siempre lo tiene).
        if shutil.which("cargo"):
            rs = subprocess.run(["cargo", "run", "--quiet", "--bin", "reglas", "--", json.dumps(casos)],
                                cwd=os.path.join(BASE, "pruebas", "tauri"), capture_output=True, text=True)
            self.assertEqual(rs.returncode, 0, rs.stderr[-2000:])
            self.assertEqual(py, json.loads(rs.stdout))
        # Acciones en Rust («rust»: true, host-tauri 0.2.0): solo Python y Rust (los hosts retirados no las conocen).
        casos_rust = [
            {"rust": True, "limite": 5},
            {"rust": True, "limite": 5, "datos": {"t": {"tipo": "texto", "max": 9}}},
            {"rust": True, "limite": 5, "script": "a.py"},
            {"rust": True, "limite": 5, "args": ["x"]},
            {"rust": True, "limite": 5, "entrada": "archivo"},
            {"rust": "si", "limite": 5, "script": "a.py"},
            {"rust": True},
        ]
        py_rust = [not pieza.errores_accion("x", c, None) for c in casos_rust]
        self.assertEqual(py_rust, [True, True, False, False, False, False, False])
        if shutil.which("cargo"):
            rs = subprocess.run(["cargo", "run", "--quiet", "--bin", "reglas", "--", json.dumps(casos_rust)],
                                cwd=os.path.join(BASE, "pruebas", "tauri"), capture_output=True, text=True)
            self.assertEqual(rs.returncode, 0, rs.stderr[-2000:])
            self.assertEqual(py_rust, json.loads(rs.stdout))
        # Swift no compila aquí: al menos las mismas frases (lo que ve quien escribe una acción) y los mismos tipos.
        swift = open(os.path.join(BASE, "piezas", "host-mac", "mac", "Enchufe.swift"), encoding="utf-8").read()
        for frase in ("solo puede ser un campo enum o entero", "lo pone el host", "«limite» es obligatorio: segundos (1 a 3600)",
                      "una lista de listas no", "«cola» solo puede ser", "«maximo» (bytes de la entrada)", "«vigilar» es"):
            self.assertIn(frase, swift)
        for tipo in pieza.TIPOS:
            self.assertIn(f'"{tipo}"', swift)

    def test_sin_acciones_no_adopta_una_accion_de_una_pieza(self):
        self.assertEqual(correr(PIEZA, "agregar", "host-escritorio", self.app).returncode, 0)
        self.assertEqual(correr(PIEZA, "agregar", "ia", self.app).returncode, 0)
        self.assertIn("listaIA", self.leer("acciones.json")["acciones"])
        app = self.leer("app.json")
        app["sin_acciones"] = ["listaIA", "noExiste"]
        with open(os.path.join(self.app, "app.json"), "w") as f:
            json.dump(app, f)
        r = correr(PIEZA, "acciones", self.app)
        self.assertEqual(r.returncode, 0, r.stderr)
        a = self.leer("acciones.json")["acciones"]
        self.assertNotIn("listaIA", a)
        self.assertIn("probarIA", a)
        self.assertIn("noExiste", r.stdout)

    def test_piezas_json_viejo_sin_acciones(self):
        """Una app con piezas.json de antes (sin «acciones») y otra versión que la base: se buscan en el historial de git de
        Pieza; si no hay historial, no se arma un acciones.json sin ellas (y se dice qué correr)."""
        self.assertEqual(correr(PIEZA, "agregar", "ia", self.app).returncode, 0)
        lock = self.leer("piezas.json")
        del lock["piezas"]["ia"]["acciones"]
        lock["piezas"]["ia"]["version"] = "0.5.0"
        with open(os.path.join(self.app, "piezas.json"), "w") as f:
            json.dump(lock, f)
        r = correr(PIEZA, "agregar", "host-escritorio", self.app)
        hay_historia = subprocess.run(["git", "-C", BASE, "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip() not in ("", "0", "1")
        if hay_historia:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("probarIA", self.leer("acciones.json")["acciones"])
            self.assertIn("probarIA", self.leer("piezas.json")["piezas"]["ia"]["acciones"], "quedan anotadas")
        else:
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("actualizar", r.stdout + r.stderr)

    def test_trabajos_late_para_el_host(self):
        """trabajos.latir() toca <ID>_LATIDO (lo pide el host para «limite»: "trabajo"); sin la variable no hace nada."""
        self.assertEqual(correr(PIEZA, "agregar", "trabajos", self.app).returncode, 0)
        latido = os.path.join(self.tmp.name, "latido")
        codigo = ("import sys, time; sys.path.insert(0, 'bin'); import trabajos; trabajos.LATIDO = 0.1;"
                  "t = trabajos.Trabajo.nuevo('x', '/tmp', ['a'], {}); t.latir(); time.sleep(0.5); t.terminar('listo')")
        env = {**os.environ, "PRUEBA_LATIDO": latido, "PRUEBA_DATOS": os.path.join(self.tmp.name, "datos")}
        r = subprocess.run([sys.executable, "-c", codigo], cwd=self.app, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(latido))
        os.remove(latido)
        env.pop("PRUEBA_LATIDO")
        r = subprocess.run([sys.executable, "-c", codigo], cwd=self.app, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(latido))

    def test_mantener_vivo_limpia_al_cortar(self):
        """El host manda SIGTERM al cerrar la app: con mantener_vivo() el script sale con SystemExit y corren sus finally."""
        self.assertEqual(correr(PIEZA, "agregar", "trabajos", self.app).returncode, 0)
        marca = os.path.join(self.tmp.name, "limpio")
        codigo = ("import sys, time; sys.path.insert(0, 'bin'); import trabajos\n"
                  "trabajos.mantener_vivo()\n"
                  f"try:\n    print('listo', flush=True); time.sleep(30)\nfinally:\n    open({marca!r}, 'w').write('si')\n")
        env = {**os.environ, "PRUEBA_DATOS": os.path.join(self.tmp.name, "datos")}
        p = subprocess.Popen([sys.executable, "-c", codigo], cwd=self.app, env=env, stdout=subprocess.PIPE, text=True)
        self.assertEqual(p.stdout.readline().strip(), "listo")
        p.terminate()
        self.assertEqual(p.wait(10), 143)
        self.assertTrue(os.path.exists(marca), "el finally corrió")
        propio = ("import signal, sys; sys.path.insert(0, 'bin'); import trabajos\n"
                  "signal.signal(signal.SIGTERM, lambda *a: None)\n"
                  "trabajos.mantener_vivo(); print(signal.getsignal(signal.SIGTERM) is not trabajos._salir_por_senal)\n")
        r = subprocess.run([sys.executable, "-c", propio], cwd=self.app, env=env, capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "True", "un manejador propio de la app gana")

    def test_nada_de_una_app_en_el_host(self):
        import re
        for pid, carpeta in (("host-mac", "mac"), ("host-escritorio", "escritorio")):
            d = os.path.join(BASE, "piezas", pid, carpeta)
            for f in os.listdir(d):
                t = open(os.path.join(d, f), encoding="utf-8").read()
                for app in ("Esquema", "Graba", "Minuta", "Corta", "Repasa", "Alcancia", "Alcancía"):
                    self.assertIsNone(re.search(rf"(^|[^\w]){app}(?!\w)", t), f"{pid}/{f}: {app}")
                for marca in ("ESQUEMA_", "GRABA_", "MINUTA_", "CORTA_", "REPASA_", "ALCANCIA_", "-app/"):
                    self.assertNotIn(marca, t, f"{pid}/{f}: {marca}")


# ── Plantillas (pieza.json → «generar») y las piezas «empaquetado» y «github» ─────────────────────────────────────────────────

sys.path.insert(0, os.path.join(BASE, "herramientas"))
import plantillas  # noqa: E402


def yaml_valido(ruta):
    """None si el YAML se lee bien; el error si no. Con PyYAML o con Ruby (los dos vienen en los runners de GitHub)."""
    try:
        import yaml
        try:
            yaml.safe_load(open(ruta, encoding="utf-8"))
            return None
        except yaml.YAMLError as e:
            return str(e)
    except ImportError:
        pass
    import shutil
    if shutil.which("ruby"):
        r = subprocess.run(["ruby", "-ryaml", "-e", "YAML.load_file(ARGV[0])", ruta], capture_output=True, text=True)
        return None if r.returncode == 0 else r.stderr
    raise unittest.SkipTest("sin PyYAML ni Ruby para leer YAML")


def errores_workflow(texto):
    """Las reglas de los workflows de la familia: actions fijadas por SHA con su versión, permisos declarados, sin credenciales
    guardadas, sin pull_request_target y sin expresiones de GitHub dentro de run:."""
    import re
    e = []
    if "pull_request_target" in texto:
        e.append("pull_request_target")
    if not re.search(r"(?m)^permissions:", texto):
        e.append("sin permissions arriba")
    for n, linea in enumerate(texto.splitlines(), 1):
        m = re.search(r"uses:\s*(\S+)", linea)
        if m and not (re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", m.group(1)) and re.search(r"#\s*v\d", linea)):
            e.append(f"{n}: action sin fijar por SHA")
    for bloque in re.findall(r"(?m)^( *)(?:- )?run: \|\n((?:\1  .*\n|\s*\n)*)", texto + "\n"):
        if "${{" in bloque[1]:
            e.append("expresión de GitHub dentro de run:")
    for linea in texto.splitlines():
        if re.match(r"\s*(- )?run: [^|]", linea) and "${{" in linea:
            e.append("expresión de GitHub dentro de run:")
    checkouts = texto.count("actions/checkout@")
    if texto.count("persist-credentials: false") < checkouts:
        e.append("un checkout sin persist-credentials: false")
    return e


class Plantillas(unittest.TestCase):
    """El motor de plantillas (herramientas/plantillas.py): solo datos, valores seguros o escapados, errores con línea."""

    def setUp(self):
        self.ctx = plantillas.contexto({"id": "ana", "nombre": "Ána", "plataformas": ["mac", "linux"],
                                        "x": {"lista": [{"n": "uno"}, {"n": "dos"}], "raro": "a\"b$c", "url": "https://a.b/c"}},
                                       piezas=["host-mac"])

    def test_valores_bloques_y_lineas_solas(self):
        t = "{{nombre}} {{ID}} {{nombre_ascii}}\n{{#si mac}}\nmac\n{{#sino}}\nno\n{{/si}}\n{{#no windows}}sin windows{{/no}}\n" \
            "{{#cada app.x.lista como i}}\n- {{i.n}}{{#no i_ultimo}},{{/no}}\n{{/cada}}\n{{#si piezas.host-mac}}host{{/si}}{{! nada }}\n"
        self.assertEqual(plantillas.llenar(t, self.ctx), "Ána ANA Ana\nmac\nsin windows\n- uno,\n- dos\nhost\n")

    def test_expresiones_de_github_quedan(self):
        self.assertEqual(plantillas.llenar("a: ${{ github.ref }} {{id}}", self.ctx), "a: ${{ github.ref }} ana")

    def test_lo_raro_necesita_un_filtro(self):
        with self.assertRaisesRegex(plantillas.PlantillaMala, "filtro"):
            plantillas.llenar("{{app.x.raro}}", self.ctx)
        self.assertEqual(plantillas.llenar("{{app.x.raro|sh}}", self.ctx), "'a\"b$c'")
        self.assertEqual(plantillas.llenar("{{app.x.raro|xml}}", self.ctx), "a&quot;b$c")
        self.assertEqual(plantillas.llenar("{{app.x.raro|json}}", self.ctx), '"a\\"b$c"')
        self.assertEqual(plantillas.llenar("{{app.x.lista|json}}", self.ctx), '[{"n": "uno"}, {"n": "dos"}]')
        with self.assertRaisesRegex(plantillas.PlantillaMala, "lista u objeto"):
            plantillas.llenar("{{app.x.lista}}", self.ctx)

    def test_filtros_que_validan(self):
        self.assertEqual(plantillas.llenar("{{app.x.url|https}}", self.ctx), "https://a.b/c")
        for marca in ("{{app.x.raro|https}}", "{{nombre|sha256}}", "{{app.x.raro|nombre}}", "{{nombre|version}}"):
            with self.assertRaises(plantillas.PlantillaMala, msg=marca):
                plantillas.llenar(marca, self.ctx)
        with self.assertRaises(plantillas.PlantillaMala):
            plantillas.llenar("{{u|ruta}}", {**self.ctx, "u": "../fuera"})

    def test_errores_con_linea(self):
        for t, que in (("a\n{{falta}}", "línea 2: falta"), ("{{#si mac}}", "falta cerrar"), ("{{/si}}", "no cierra"),
                       ("{{id|nada}}", "filtro desconocido"), ("{{#sino}}", "fuera de"), ("{{ id id }}", "marca rara")):
            with self.assertRaisesRegex(plantillas.PlantillaMala, que):
                plantillas.llenar(t, self.ctx)
            self.assertTrue(plantillas.revisar(t) or que.startswith("línea 2"))

    def test_un_valor_no_trae_marcas(self):
        with self.assertRaises(plantillas.PlantillaMala):
            plantillas.llenar("{{v}}", {**self.ctx, "v": "{{id}}"})

    def test_json_sirve_dentro_de_un_script(self):
        malo = '</script><meta http-equiv="refresh" content="0;url=https://evil.example"> & \u2028'
        r = plantillas.llenar("{{v|json}}", {**self.ctx, "v": malo})
        for x in ("<", ">", "&", "\u2028"):
            self.assertNotIn(x, r)
        self.assertEqual(json.loads(r), malo)  # sigue siendo el mismo JSON

    def test_ningun_valor_trae_expresiones_de_actions(self):
        for v in ("${{ secrets.TOKEN }}", "a }} b", "x {{ y", ["ok", "${{ github.token }}"], {"k": "${{ x }}"},
                  {"${{ k }}": 1}):
            for t in ("{{v|json}}", "{{v|yaml}}", "{{v|sh}}", "{{v|xml}}", "{{v|linea}}"):
                if isinstance(v, (list, dict)) and t not in ("{{v|json}}", "{{v|yaml}}"):
                    continue
                with self.assertRaisesRegex(plantillas.PlantillaMala, "Actions", msg=f"{t} {v}"):
                    plantillas.llenar(t, {**self.ctx, "v": v})
        with self.assertRaises(plantillas.PlantillaMala):
            plantillas.llenar("{{#cada v como x}}{{x|linea}}{{/cada}}", {**self.ctx, "v": ["${{ github.ref }}"]})
        # En el texto de la plantilla sí (son de GitHub Actions), y un objeto con }} propio del JSON también.
        self.assertEqual(plantillas.llenar("${{ github.ref }} {{v|json}}", {**self.ctx, "v": {"a": {"b": 1}}}),
                         '${{ github.ref }} {"a": {"b": 1}}')

    def test_filtro_color(self):
        for bueno in ("#fff", "#1a2b3c", "#1a2b3c80", "rgb(1, 2, 3)", "rgba(1 2 3 / 50%)", "hsl(210 50% 40%)"):
            self.assertEqual(plantillas.llenar("{{v|color}}", {**self.ctx, "v": bueno}), bueno)
        for malo in ("red", "#ffff0", "#fff;}body{background:url(https://evil.example)", "rgb(1,2,3) url(x)",
                     "expression(alert(1))", "rgb(a,b,c)", "", 3):
            with self.assertRaises(plantillas.PlantillaMala, msg=malo):
                plantillas.llenar("{{v|color}}", {**self.ctx, "v": malo})

    def test_contexto(self):
        c = plantillas.contexto({"id": "ana", "nombre": "Ána", "datos": "visible", "repo": "ana-app/ana", "version": "1.2.3"})
        self.assertEqual((c["bundle"], c["repo"], c["web"], c["datos_mac"], c["version"]),
                         ("app.ana.mac", "ana-app/ana", "https://ana-app.github.io/ana/", "Ána/.ana", "1.2.3"))
        c = plantillas.contexto({"id": "ana", "plataformas": ["windows"]})
        self.assertEqual((c["repo"], c["escritorio"], c["mac_o_linux"], c["datos_mac"], c["version"]),
                         ("ana-app/ana", True, False, "Library/Application Support/Ana", "0.1.0"))
        for malo in ({"id": "Ana"}, {"id": "ana", "nombre": "a\"b"}, {"id": "ana", "datos": {"carpeta": "~/../x"}}):
            with self.assertRaises(plantillas.PlantillaMala):
                plantillas.contexto(malo)


class Generar(unittest.TestCase):
    """«empaquetado» y «github» en una app ficticia: lo que generan es válido, sigue las reglas y nunca pisa lo de la app."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def app(self, plataformas="mac,windows,linux", nombre="ana", piezas=("host-tauri", "empaquetado", "github"), env=None):
        app = os.path.join(self.tmp.name, nombre)
        os.makedirs(os.path.join(app, "bin"))
        r = correr(PIEZA, "iniciar", app, "ana", "Ána", f"--plataformas={plataformas}", "--datos=visible")
        self.assertEqual(r.returncode, 0, r.stderr)
        for p in piezas:
            r = correr(PIEZA, "agregar", p, app, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return app

    def leer(self, app, ruta):
        return open(os.path.join(app, ruta), encoding="utf-8").read()

    def revisar_todo(self, app):
        import plistlib
        import re
        lock = json.load(open(os.path.join(app, "piezas.json")))
        rutas = set()
        for pid in ("host-tauri", "empaquetado", "github"):
            if pid in lock["piezas"]:
                rutas |= set(lock["piezas"][pid].get("generados", {})) | set(lock["piezas"][pid].get("una_vez", []))
        for ruta in sorted(rutas):
            t = self.leer(app, ruta)
            self.assertIsNone(re.search(r"(?<!\$)\{\{", t), f"{ruta}: quedó una marca")
            if ruta.endswith(".sh"):
                r = subprocess.run(["bash", "-n", os.path.join(app, ruta)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{ruta}: {r.stderr}")
                self.assertTrue(os.stat(os.path.join(app, ruta)).st_mode & stat.S_IXUSR, f"{ruta} no es ejecutable")
            elif ruta.endswith(".json"):
                json.loads(t)
            elif ruta.endswith(".plist"):
                plistlib.loads(t.encode())
            elif ruta.endswith(".yml"):
                self.assertIsNone(yaml_valido(os.path.join(app, ruta)), ruta)
                if "/workflows/" in ruta:
                    self.assertEqual(errores_workflow(t), [], ruta)
        return rutas

    def test_mac_windows_linux(self):
        app = self.app()
        rutas = self.revisar_todo(app)
        for r in ("build.sh", "herramientas/empaquetar.sh", "escritorio/Info.plist", "escritorio/Cargo.toml", "escritorio/build.rs",
                  "escritorio/tauri.conf.json", "escritorio/herramientas/preparar.sh", "instalar.sh", "instalar.ps1", ".github/workflows/publicar.yml",
                  ".github/workflows/revisar.yml", ".github/workflows/pieza-al-dia.yml", ".github/dependabot.yml",
                  ".github/ISSUE_TEMPLATE/probar.yml", ".claude/agents/ana-revisor.md", ".claude/agents/ana-privacidad.md",
                  "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE", ".gitignore", "herramientas/revisar_privacidad.sh"):
            self.assertIn(r, rutas)
        self.assertTrue(os.path.isfile(os.path.join(app, "herramientas", "python.lock")))
        pub = self.leer(app, ".github/workflows/publicar.yml")
        for nombre in ("Ana-macOS.zip", "Ana-Windows.exe", "Ana-Linux.AppImage", "Ana-Linux.tar.gz"):
            self.assertIn(nombre, pub)
        self.assertNotIn("Ana-Linux.deb", pub)
        self.assertIn('identifier "app.ana.mac"', self.leer(app, "herramientas/empaquetar.sh"))
        self.assertIn("Ána/.ana/desarrollo", self.leer(app, "build.sh").replace('"$DATOS/desarrollo"', "Ána/.ana/desarrollo"))
        conf = json.loads(self.leer(app, "escritorio/tauri.conf.json"))
        self.assertEqual((conf["version"], conf["identifier"], conf["productName"]), ("0.1.0", "app.ana.mac", "Ána"))
        self.assertEqual(conf["bundle"]["resources"]["../acciones.json"], "recursos/acciones.json")
        self.assertIn('name = "ana"', self.leer(app, "escritorio/Cargo.toml"))
        self.assertTrue(os.path.isfile(os.path.join(app, "escritorio", "src", "pieza", "host.rs")))
        self.assertIn("arrancar(tauri::generate_context!()", self.leer(app, "escritorio/src/main.rs"))
        # Lo que la IA de la app completa queda marcado.
        for doc in ("AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", ".claude/agents/ana-revisor.md"):
            self.assertIn("<!-- La app:", self.leer(app, doc), doc)
        self.assertIn("| `host-tauri` | 0.2", self.leer(app, "AGENTS.md"))
        self.assertIn("ofrece su marketplace", self.leer(app, "CONTRIBUTING.md"))
        self.assertEqual(json.loads(self.leer(app, ".claude/settings.json")),
                         {"extraKnownMarketplaces": {"pieza": {"source": {"source": "github", "repo": "pieza-app/pieza"}}}})
        self.assertNotIn("enabledPlugins", self.leer(app, ".claude/settings.json"))
        rev = self.leer(app, ".github/workflows/revisar.yml")
        self.assertIn("ubuntu-24.04", rev)
        self.assertNotIn("ubuntu-latest", rev)
        self.assertIn("playwright@1.56.1", rev)
        # La app nativa se prueba en el job «app», en los tres sistemas, y no se compila Swift.
        self.assertIn("SIN_RUST=1", rev)
        for so in ("macos-15", "windows-2025", "bash pruebas/arranque.sh", "cargo clippy --locked"):
            self.assertIn(so, rev)
        self.assertNotIn("swift build", rev)

    def test_solo_mac_y_solo_linux(self):
        mac = self.app("mac", "mac")
        self.revisar_todo(mac)
        for r in ("instalar.ps1",):
            self.assertFalse(os.path.exists(os.path.join(mac, r)), r)
        self.assertNotIn("windows-2025", self.leer(mac, ".github/workflows/publicar.yml"))
        self.assertNotIn("ubuntu-24.04 }", self.leer(mac, ".github/workflows/publicar.yml"))
        linux = self.app("linux", "linux", piezas=("host-tauri", "empaquetado", "github"))
        self.revisar_todo(linux)
        for r in ("escritorio/Info.plist", "build.sh", "instalar.ps1"):
            self.assertFalse(os.path.exists(os.path.join(linux, r)), r)
        self.assertNotIn("mac:", self.leer(linux, ".github/workflows/revisar.yml"))
        self.assertIn("Linux)", self.leer(linux, "instalar.sh"))
        self.assertNotIn("Darwin)", self.leer(linux, "instalar.sh"))

    def test_lo_propio_de_la_app(self):
        """Binarios extra, permisos, barra de menú, carpetas, deb: lo de app.json → empaquetado llega a cada archivo."""
        app = self.app(piezas=("host-tauri",))
        a = json.load(open(os.path.join(app, "app.json")))
        a["empaquetado"] = {
            "descripcion": "Notas rápidas de Ana (prueba)", "barra_de_menu": True, "deb": True, "carpetas": ["plantillas"],
            "quitar": ["ui/demo"], "permisos": [{"clave": "NSCameraUsageDescription", "texto": "Para ver <tu> cara & más"}],
            "ocupada": [{"proceso": "bin/procesar.py", "mensaje": "✗ Ána está procesando. Espera a que termine."}],
            "licencias": ["Programa de prueba (https://example.org), licencia MIT."],
            "mac": {"ejecutables": ["ana-cli"], "frameworks": ["algo.framework"],
                    "binarios": [{"nombre": "herramienta", "gz": True, "url": "https://example.org/h.gz", "sha256": "a" * 64}],
                    "swift": {"binarios": [{"nombre": "algo", "url": "https://example.org/a.zip", "checksum": "b" * 64}],
                              "ejecutables": [{"nombre": "ana-cli", "ruta": "Sources/Cli", "dependencias": ["algo"], "rpath": True}]}},
            "escritorio": {"binarios": [{"nombre": "herramienta", "gz": True,
                                         "linux": {"url": "https://example.org/l.gz", "sha256": "c" * 64},
                                         "windows": {"url": "https://example.org/w.gz", "sha256": "d" * 64}}]}}
        json.dump(a, open(os.path.join(app, "app.json"), "w"), ensure_ascii=False)
        for p in ("empaquetado", "github"):
            r = correr(PIEZA, "agregar", p, app)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.revisar_todo(app)
        import plistlib
        pl = plistlib.load(open(os.path.join(app, "escritorio", "Info.plist"), "rb"))
        self.assertEqual((pl["LSUIElement"], pl["NSCameraUsageDescription"]), (True, "Para ver <tu> cara & más"))
        emp = self.leer(app, "herramientas/empaquetar.sh")
        for x in (" plantillas; do", "ui/demo.json ui/demo", "Programa de prueba", "appimage,deb", 'identifier "app.ana.mac"'):
            self.assertIn(x, emp)
        self.assertIn('pgrep -f bin/procesar.py', self.leer(app, "build.sh"))
        prep = self.leer(app, "escritorio/herramientas/preparar.sh")
        for x in ("a" * 64, "https://example.org/h.gz", "c" * 64, "d" * 64):
            self.assertIn(x, prep)
        conf = json.loads(self.leer(app, "escritorio/tauri.conf.json"))
        self.assertEqual(conf["bundle"]["resources"]["../plantillas/"], "recursos/plantillas/")
        self.assertIn("Ana-Linux.deb", self.leer(app, ".github/workflows/publicar.yml"))

    def test_lo_de_afuera_se_valida(self):
        app = self.app(piezas=("host-tauri",))
        a = json.load(open(os.path.join(app, "app.json")))
        for malo in ({"mac": {"binarios": [{"nombre": "x", "url": "http://inseguro/x", "sha256": "a" * 64}]}},
                     {"mac": {"binarios": [{"nombre": "x", "url": "https://a.b/x", "sha256": "corta"}]}},
                     {"carpetas": ["../fuera"]},
                     {"permisos": [{"clave": "NS'; rm", "texto": "x"}]},
                     {"ocupada": [{"proceso": "x", "mensaje": ["no", "texto"]}]}):
            a["empaquetado"] = malo
            json.dump(a, open(os.path.join(app, "app.json"), "w"))
            r = correr(PIEZA, "agregar", "empaquetado", app)
            self.assertNotEqual(r.returncode, 0, malo)
            self.assertIn("No pude generar", r.stderr)

    def test_no_pisa_lo_de_la_app_y_se_pone_al_dia(self):
        app = self.app()
        # La app cambia build.sh y completa AGENTS.md: nada de eso se vuelve a tocar.
        with open(os.path.join(app, "build.sh"), "a") as f:
            f.write("# propio de la app\n")
        with open(os.path.join(app, "AGENTS.md"), "w") as f:
            f.write("# Guía de Ana\n")
        os.remove(os.path.join(app, "CODE_OF_CONDUCT.md"))
        a = json.load(open(os.path.join(app, "app.json")))
        a["version"] = "0.2.0"
        json.dump(a, open(os.path.join(app, "app.json"), "w"))
        r = correr(PIEZA, "generar", app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no regeneré build.sh", r.stdout)
        self.assertIn("# propio de la app", self.leer(app, "build.sh"))
        self.assertEqual(self.leer(app, "AGENTS.md"), "# Guía de Ana\n")
        self.assertFalse(os.path.exists(os.path.join(app, "CODE_OF_CONDUCT.md")))
        self.assertIn('"version": "0.2.0"', self.leer(app, "escritorio/tauri.conf.json"))
        self.assertIn('version = "0.2.0"', self.leer(app, "escritorio/Cargo.toml"))
        e = correr(PIEZA, "estado", app)
        self.assertIn("build.sh es de la app", e.stdout)
        d = correr(PIEZA, "diferencias", app, "empaquetado")
        self.assertIn("+# propio de la app", d.stdout)
        # Volver a correr no cambia nada.
        antes = {r: self.leer(app, r) for r in ("escritorio/tauri.conf.json", "instalar.sh", ".github/workflows/publicar.yml")}
        r = correr(PIEZA, "generar", app)
        self.assertEqual({k: self.leer(app, k) for k in antes}, antes)
        self.assertNotIn("+ ", r.stdout)
        # --forzar sí lo reemplaza.
        correr(PIEZA, "generar", app, "empaquetado", "--forzar")
        self.assertNotIn("# propio de la app", self.leer(app, "build.sh"))

    def test_una_pieza_nueva_pone_al_dia_lo_generado(self):
        app = self.app("mac", piezas=("host-tauri", "empaquetado"))
        self.assertNotIn("ureq", self.leer(app, "escritorio/Cargo.toml"))
        r = correr(PIEZA, "agregar", "actualizaciones", app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ureq", self.leer(app, "escritorio/Cargo.toml"))
        self.assertTrue(os.path.isfile(os.path.join(app, "escritorio", "src", "pieza", "actualizaciones.rs")))
        self.assertFalse(os.path.exists(os.path.join(app, "app", "Sources", "PiezaActualizaciones")), "lo de Swift va solo con host-mac")

    def test_un_archivo_que_ya_existia_queda_de_la_app(self):
        app = os.path.join(self.tmp.name, "vieja")
        os.makedirs(os.path.join(app, "bin"))
        correr(PIEZA, "iniciar", app, "ana", "Ána", "--plataformas=mac")
        with open(os.path.join(app, "build.sh"), "w") as f:
            f.write("#!/bin/bash\necho propio\n")
        r = correr(PIEZA, "agregar", "empaquetado", app)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("build.sh ya existe y es distinto", r.stdout)
        self.assertEqual(self.leer(app, "build.sh"), "#!/bin/bash\necho propio\n")
        self.assertEqual(json.load(open(os.path.join(app, "piezas.json")))["piezas"]["empaquetado"]["version"],
                         json.load(open(os.path.join(BASE, "piezas", "empaquetado", "pieza.json")))["version"])

    def test_lo_de_github_nunca_va_solo(self):
        """Una versión nueva que cambia un workflow no se actualiza sola (el token de Actions no puede escribirlo y lo tiene que
        ver una persona): va al issue de «Pieza al día». Lo demás de la misma pieza sí."""
        import shutil
        app = self.app("mac", piezas=("host-tauri", "empaquetado"))
        cat = os.path.join(self.tmp.name, "catalogo")
        shutil.copytree(os.path.join(BASE, "piezas"), cat)
        pj = os.path.join(cat, "empaquetado", "pieza.json")
        p = json.load(open(pj))
        x, y, z = map(int, p["version"].split("."))
        p["version"] = f"{x}.{y}.{z + 1}"
        p["cambios"].insert(0, {"version": p["version"], "tipo": "arreglo", "resumen": "Prueba."})
        json.dump(p, open(pj, "w"), ensure_ascii=False)
        for f, extra in (("github/workflows/publicar.yml", "# cambio de prueba\n"), ("build.sh", "# arreglo de prueba\n")):
            with open(os.path.join(cat, "empaquetado", "plantillas", f), "a") as g:
                g.write(extra)
        env = {**os.environ, "PIEZA_CATALOGO": cat}
        e = json.loads(correr(PIEZA, "estado", app, "--json", env=env).stdout)
        emp = next(x for x in e if x["pieza"] == "empaquetado")
        self.assertEqual((emp["automatico"], emp["github"]), (False, [".github/workflows/publicar.yml"]))
        self.assertIn("publicar.yml", correr(PIEZA, "aviso", app, env=env).stdout)
        r = correr(PIEZA, "actualizar", app, "--automatico", env=env)
        self.assertNotIn("cambio de prueba", self.leer(app, ".github/workflows/publicar.yml"))
        # A mano sí (y build.sh, que no es de .github/, también llega).
        r = correr(PIEZA, "actualizar", app, "empaquetado", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cambio de prueba", self.leer(app, ".github/workflows/publicar.yml"))
        self.assertIn("arreglo de prueba", self.leer(app, "build.sh"))

    def test_lo_de_claude_nunca_va_solo(self):
        """.claude/ (ajustes que pueden definir hooks, agentes) va al aviso igual que .github/: nunca con --automatico."""
        import shutil
        app = self.app("mac", piezas=("host-mac", "github"))
        cat = os.path.join(self.tmp.name, "catalogo")
        shutil.copytree(os.path.join(BASE, "piezas"), cat)
        pj = os.path.join(cat, "github", "pieza.json")
        p = json.load(open(pj))
        p["version"] = "9.9.9"
        p["cambios"].insert(0, {"version": "9.9.9", "tipo": "arreglo", "resumen": "Prueba."})
        json.dump(p, open(pj, "w"), ensure_ascii=False)
        ajustes = os.path.join(cat, "github", "plantillas", "claude", "settings.json")
        a = json.load(open(ajustes))
        a["hooks"] = {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hola"}]}]}
        json.dump(a, open(ajustes, "w"))
        env = {**os.environ, "PIEZA_CATALOGO": cat}
        e = json.loads(correr(PIEZA, "estado", app, "--json", env=env).stdout)
        gh = next(x for x in e if x["pieza"] == "github")
        self.assertFalse(gh["automatico"])
        self.assertIn(".claude/settings.json", gh["github"])
        self.assertIn(".claude/settings.json", correr(PIEZA, "aviso", app, env=env).stdout)
        correr(PIEZA, "actualizar", app, "--automatico", env=env)
        self.assertNotIn("hooks", self.leer(app, ".claude/settings.json"))
        r = correr(PIEZA, "actualizar", app, "github", env=env)  # a mano, sí
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("echo hola", self.leer(app, ".claude/settings.json"))

    def test_nunca_sigue_un_enlace_al_escribir(self):
        """Un «Info.plist.tmp» o un «Info.plist» que son enlaces a otro lado: generar no escribe ahí y deja un archivo normal."""
        app = self.app("mac", piezas=("host-tauri", "empaquetado"))
        fuera = os.path.join(self.tmp.name, "fuera.txt")
        with open(fuera, "w") as f:
            f.write("no tocar\n")
        plist = os.path.join(app, "escritorio", "Info.plist")
        os.symlink(fuera, plist + ".tmp")
        r = correr(PIEZA, "generar", app, "host-tauri", "--forzar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.islink(plist))
        self.assertIn("LSApplicationCategoryType", self.leer(app, "escritorio/Info.plist"))
        os.remove(plist)
        os.symlink(fuera, plist)
        r = correr(PIEZA, "generar", app, "host-tauri", "--forzar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.islink(plist))
        self.assertIn("LSApplicationCategoryType", self.leer(app, "escritorio/Info.plist"))
        self.assertEqual(open(fuera).read(), "no tocar\n")
        self.assertTrue(os.path.islink(plist + ".tmp"))
        self.assertEqual([x for x in os.listdir(os.path.join(app, "escritorio")) if x.endswith(".tmp") and x != "Info.plist.tmp"], [])
        # Lo mismo al copiar los archivos de una pieza (host-tauri) sobre un enlace.
        lock = json.load(open(os.path.join(app, "piezas.json")))
        destino = next(iter(lock["piezas"]["host-tauri"]["archivos"]))
        ruta = os.path.join(app, destino)
        os.remove(ruta)
        os.symlink(fuera, ruta)
        r = correr(PIEZA, "actualizar", app, "host-tauri", "--forzar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.islink(ruta))
        self.assertEqual(open(fuera).read(), "no tocar\n")

    def test_destinos_y_comunidad(self):
        sys.path.insert(0, os.path.join(BASE, "herramientas"))
        import pieza as P
        for d, ok in (("build.sh", True), (".github/workflows/a.yml", True), (".claude/agents/a.md", True),
                      (".claude/settings.json", True), ("escritorio/.npmrc", True), (".gitignore", True),
                      (".github/.oculto", False), (".git/hooks/pre-commit", False), (".claude/hooks.json", False),
                      ("app.json", False), ("piezas.json", False), ("acciones.json", False), ("../fuera", False),
                      ("otra/carpeta.txt", False), (".env", False), ("/abs", False)):
            self.assertEqual(P.destino_generado_ok(d), ok, d)
        # Una pieza que no es oficial nunca genera (ahí un archivo de .github/ ejecutaría código).
        P._EXTRA["github"] = os.path.join(BASE, "piezas", "github")
        try:
            with self.assertRaises(SystemExit):
                P.generados_de("github", self.tmp.name, {"piezas": {}})
        finally:
            P._EXTRA.pop("github")

    def test_pieza_al_dia_es_la_misma(self):
        self.assertEqual(open(os.path.join(BASE, "plantillas", "pieza-al-dia.yml"), encoding="utf-8").read(),
                         open(os.path.join(BASE, "piezas", "github", "plantillas", "github", "workflows", "pieza-al-dia.yml"),
                              encoding="utf-8").read())

    def test_repo_configurar_solo_muestra(self):
        app = self.app("mac", piezas=())
        r = correr(PIEZA, "repo", "configurar", app, env={"PATH": "/nada", "HOME": self.tmp.name})
        self.assertEqual(r.returncode, 0, r.stderr)
        for x in ("--add-topic hecho-con-pieza", "--enable-discussions", "approval_policy=all_external_contributors",
                  "repos/ana-app/ana/rulesets", '"non_fast_forward"', '"deletion"', "'good first issue'", "label create probar",
                  "private-vulnerability-reporting"):
            self.assertIn(x, r.stdout)

    def test_reproduce_las_apps(self):
        """Para el mismo app.json, la pieza arma con Tauri lo que ya funciona en las seis apps: el mismo identificador (el Llavero y
        los permisos del Mac siguen a la app), el mismo nombre, los mismos permisos con su texto, la barra de menú, las carpetas
        extra y los mismos programas con la misma huella."""
        import plistlib
        import re
        datos = os.path.join(BASE, "pruebas", "datos", "empaquetado")
        apps = json.load(open(os.path.join(datos, "apps.json"), encoding="utf-8"))
        tpl_t = os.path.join(BASE, "piezas", "host-tauri", "plantillas", "tauri")
        tpl_e = os.path.join(BASE, "piezas", "empaquetado", "plantillas")
        for aid, a in apps.items():
            ctx = plantillas.contexto(a, piezas=["host-tauri", "actualizaciones"])
            real = plistlib.load(open(os.path.join(datos, aid, "Info.plist"), "rb"))
            conf = json.loads(plantillas.llenar(open(os.path.join(tpl_t, "tauri.conf.json"), encoding="utf-8").read(), ctx))
            self.assertEqual(conf["identifier"], real["CFBundleIdentifier"], aid)
            self.assertEqual(conf["productName"], real.get("CFBundleDisplayName", real["CFBundleName"]), aid)
            self.assertEqual(conf["version"], a["version"], aid)
            nuevo = plistlib.loads(plantillas.llenar(open(os.path.join(tpl_t, "Info.plist"), encoding="utf-8").read(), ctx).encode())
            for k, v in real.items():
                if k.startswith("NS") and k.endswith("UsageDescription") or k == "LSUIElement":
                    self.assertEqual(nuevo.get(k), v, f"{aid}: {k}")
            for c in (a.get("empaquetado") or {}).get("carpetas") or []:
                self.assertEqual(conf["bundle"]["resources"][f"../{c}/"], f"recursos/{c}/", aid)
            ruta = os.path.join(datos, aid, "empaquetar.sh")
            if os.path.isfile(ruta):
                prep = plantillas.llenar(open(os.path.join(tpl_e, "preparar.sh"), encoding="utf-8").read(), ctx)
                emp = plantillas.llenar(open(os.path.join(tpl_e, "empaquetar.sh"), encoding="utf-8").read(), ctx)
                for b in ((a.get("empaquetado") or {}).get("mac") or {}).get("binarios") or []:
                    self.assertIn(b["sha256"], prep, f"{aid}: {b['nombre']}")
                ident = re.search(r'identifier "([^"]+)"', open(ruta, encoding="utf-8").read()).group(1)
                self.assertIn(f'identifier "{ident}"', emp, aid)

    def test_plantillas_sin_nada_de_una_app(self):
        import re
        for pid in ("empaquetado", "github"):
            for raiz, _, archivos in os.walk(os.path.join(BASE, "piezas", pid, "plantillas")):
                for f in archivos:
                    t = open(os.path.join(raiz, f), encoding="utf-8").read()
                    for app in ("Esquema", "Graba", "Minuta", "Corta", "Repasa", "Alcancia", "Alcancía"):
                        self.assertIsNone(re.search(rf"(^|[^\w]){app}(?!\w)", t), f"{pid}/{f}: {app}")

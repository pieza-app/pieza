"""Pruebas de la base: las piezas de Python y la herramienta pieza.py. Solo biblioteca estándar: python3 -m unittest pruebas/test_piezas.py"""
import json
import os
import stat
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
                print("--safe-mode"); sys.exit(0)
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

    def test_ruta_en_no_sale(self):
        salida = self.py("import nucleo; print([nucleo.ruta_en('/tmp', p) is None for p in ['a/b', '../x', '/etc', '', 'a/../../x']])")
        self.assertEqual(salida.strip(), "[False, True, True, True, True]")

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
        r = correr(PIEZA, "agregar", "transcribir", self.app)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("aún no está extraída", r.stderr)

    def test_ficha_suma_todo(self):
        r = correr(PIEZA, "ficha", "microfono", "--plataformas", "mac,android", "--json")
        f = json.loads(r.stdout)
        ids = [x["id"] for x in f["piezas"]]
        self.assertIn("nucleo", ids)            # siempre, por estar en mac
        self.assertIn("host-mac", ids)
        self.assertNotIn("host-escritorio", ids)  # no se pidió Windows ni Linux
        self.assertEqual([x["clave"] for x in f["permisos"]["android"]], ["RECORD_AUDIO"])
        self.assertTrue(any(x["pieza"] == "nucleo" and x["plataformas"] == ["android"] for x in f["faltan_en"]))
        self.assertEqual(f["pantallas"][0]["nombre"], "Idioma")

    def test_iniciar_deja_al_dia_y_plugin(self):
        self.assertTrue(os.path.isfile(os.path.join(self.app, ".github", "workflows", "pieza-al-dia.yml")))
        with open(os.path.join(self.app, ".claude", "settings.json")) as f:
            self.assertTrue(json.load(f)["enabledPlugins"]["pieza@pieza"])

    def _base_con_version(self, tipo, version="0.1.1", seguridad=False):
        """Copia la base a un temporal y le sube la versión a «ia» con un cambio de este tipo."""
        import shutil
        base = os.path.join(self.tmp.name, "base")
        shutil.copytree(BASE, base, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        ruta = os.path.join(base, "piezas", "ia", "pieza.json")
        with open(ruta) as f:
            p = json.load(f)
        p["version"] = version
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
        nueva = self._base_con_version("rompe", version="0.2.0")
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

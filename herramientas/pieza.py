#!/usr/bin/env python3
"""pieza — enchufa piezas de esta base en una app. Solo biblioteca estándar.

  pieza.py listar                         Las piezas disponibles.
  pieza.py crear <carpeta> --id <id> --nombre <Nombre> [--plataformas mac,windows,linux] [--piezas ia,…] [--repo dueño/repo]
          [--datos sistema|visible]
                                          Una app nueva andando de una vez: app.json, las piezas de siempre para esas plataformas,
                                          las pedidas, lo propio mínimo (pieza «esqueleto»: interfaz con bienvenida, pantalla y
                                          script de ejemplo, Mac y Windows/Linux, demo y pruebas), acciones.json y lo generado
                                          (empaquetado, repo, página). Al final dice qué le toca a la IA y qué a la persona.
  pieza.py iniciar <app> <id> <Nombre> [--plataformas=mac,windows,linux] [--datos=sistema|visible]
                                          Crea app.json en una app que aún no lo tiene.
  pieza.py agregar <pieza> <app> [--sin-revisar] [--sin-config=clave,…] [--forzar]
                                          Copia la pieza (y lo que requiere) a la app y la anota en piezas.json. Si un archivo ya
                                          existe y es distinto (la pieza salió de esa app, o la app tiene un módulo con el mismo
                                          nombre), no copia nada y lo explica; --forzar lo reemplaza. Oficial o de la
                                          comunidad: las de la comunidad revisadas se verifican con su huella; las que aún no se
                                          revisan solo con --sin-revisar (bajo tu responsabilidad). --sin-config=tema no suma
                                          esa clave opcional a app.json (p. ej. una app sin «Apariencia» en Ajustes); sobre una
                                          pieza ya instalada, anota la decisión y quita la clave si la app no la cambió.
  pieza.py estado <app> [--json]          Qué piezas tiene la app, qué versiones nuevas hay, de qué tipo (arreglo, mejora,
                                          rompe, seguridad), qué archivos cambió la app y qué se puede actualizar solo.
  pieza.py actualizar <app> [pieza…] [--automatico] [--forzar] [--sin-config=clave,…]
                                          Trae la versión nueva. Nunca pisa un archivo que la app cambió, salvo --forzar.
                                          Va en orden de dependencias y cuenta lo que se actualiza en la misma pasada (una
                                          pieza que necesita la versión nueva de otra se actualiza junto con ella).
                                          --automatico: solo arreglos y mejoras compatibles sobre archivos que la app no tocó.
  pieza.py aviso <app>                    En Markdown, lo que hay que actualizar a mano (cambios que rompen o archivos de la
                                          app) con los pasos para migrar. Es el cuerpo del issue que abre «Pieza al día».
  pieza.py diferencias <app> <pieza>      Lo que la app cambió de una pieza (para devolverlo a la base si es mejor), también de lo
                                          que la pieza genera.
  pieza.py generar <app> [pieza…] [--forzar]
                                          Vuelve a llenar lo que generan las piezas (pieza.json → «generar», desde app.json)
                                          después de cambiar app.json. Nunca pisa lo que la app cambió, salvo --forzar.
  pieza.py acciones <app>                 Arma acciones.json (lo lee el host genérico): las acciones de las piezas instaladas más
                                          las de app.json → «acciones». agregar/actualizar lo hacen solos si la app tiene host.
  pieza.py repo configurar <app> [--aplicar]
                                          Los comandos de gh que dejan el repo de la app listo para la comunidad (topics con
                                          hecho-con-pieza, Discussions, reporte privado de fallas, aprobar las pruebas de quien
                                          aporta, ruleset de la rama principal, etiquetas). Sin --aplicar solo los muestra.
  pieza.py revisar                        Valida todos los pieza.json de la base (formato y reglas de seguridad).
  pieza.py skills estado [codex|claude]   Qué versión de cada flujo (skill) tienes instalada y cuál trae esta Pieza.
  pieza.py skills instalar codex|claude   Instala o pone al día las skills (Codex: ~/.agents/skills; Claude Code: ~/.claude/skills)
                                          sin perder tu sección «Configuración local». Gemini CLI: `gemini extensions install`.
  pieza.py catalogo [--json]              Todas las piezas, listas y planeadas, con todo lo que declaran (lo lee la skill).
  pieza.py ficha <pieza>… [--plataformas mac,windows,linux,ios,android] [--json]
                                          La ficha de una app con esas piezas: requisitos, pantallas, config, permisos por
                                          plataforma, red, acciones y lo que solo puede hacer la persona. Se muestra antes de crear.

Modelo «copiar y adueñarse» (como shadcn/ui): la pieza se copia dentro de la app y desde ahí es de la app. piezas.json guarda la
versión y la huella de cada archivo copiado, así se sabe qué cambió la app y qué trae la base de nuevo.
"""
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: De dónde se leen las piezas. «Pieza al día» corre esta herramienta fijada a una versión y le pasa las piezas nuevas solo
#: como datos (PIEZA_CATALOGO): así nunca ejecuta código que no fijó la app.
PIEZAS = os.environ.get("PIEZA_CATALOGO") or os.path.join(BASE, "piezas")
ID = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
SCRIPT = re.compile(r"^\w+\.py$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
TIPOS = {"texto", "enum", "bool", "entero", "rutaRelativa", "base64", "lista"}
ESTADOS = {"lista", "planeada", "retirada"}
ID_PIEZA = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
PLATAFORMAS = ("mac", "windows", "linux", "ios", "android")
CATEGORIAS = {"base", "ia", "interfaz", "datos", "medios", "conexiones", "plataforma", "repo"}
TIPOS_CAMBIO = {"inicial": 0, "arreglo": 1, "mejora": 2, "rompe": 3}
RANGO = re.compile(r"^(>=|<=|>|<|==)(\d+\.\d+\.\d+)$")


# ── Versiones ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# X.Y.Z. Arreglo: sube Z. Mejora compatible: sube Y. Cambio que rompe: sube X (o Y mientras X sea 0, como en semver).
# Arreglos y mejoras se pueden actualizar solos; lo que rompe nunca, y trae pasos para migrar.

def semver(v):
    return tuple(int(x) for x in str(v).split("."))


def satisface(version, rango):
    """«>=0.1.0 <1.0.0»: todas las condiciones, separadas por espacio."""
    ops = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b, "==": lambda a, b: a == b}
    for parte in rango.split():
        m = RANGO.match(parte)
        if not m or not ops[m.group(1)](semver(version), semver(m.group(2))):
            return False
    return True


def cambios_entre(p, desde, hasta):
    """Las entradas de «cambios» con desde < versión <= hasta, de la más nueva a la más vieja."""
    return [c for c in p.get("cambios", []) if semver(desde) < semver(c["version"]) <= semver(hasta)]


def incompatibles(versiones):
    """Con estas versiones instaladas ({pieza: versión}), qué requisitos no se cumplen: [(pieza, requiere, rango, tiene)]."""
    malas = []
    for pid, v in versiones.items():
        p = todas().get(pid) or {}
        for req, rango in p.get("compatible", {}).items():
            if req in versiones and not satisface(versiones[req], rango):
                malas.append((pid, req, rango, versiones[req]))
    return malas


def plan_juntas(versiones, nuevas, candidatas):
    """Qué piezas de `candidatas` se pueden actualizar en la misma pasada: con las versiones nuevas de todas las que van, ningún
    requisito queda sin cumplir. Si una choca, sale la que pide algo que no hay (o la que rompería a otra que se queda como
    está) y se vuelve a revisar, porque lo que dependía de ella puede chocar ahora. Devuelve (las que van, {pieza: choques})."""
    van = set(candidatas)
    fuera = {}
    while True:
        plan = {**versiones, **{p: nuevas[p] for p in van}}
        malas = incompatibles(plan)
        sacar = {}
        for a, b, rango, tiene in malas:
            quien = a if a in van else b if b in van else None
            if quien:
                sacar.setdefault(quien, []).append((a, b, rango, tiene))
        if not sacar:
            return van, fuera
        for p, ch in sacar.items():
            van.discard(p)
            fuera[p] = ch


def orden_dependencias(pids, requisitos=None):
    """Las piezas con lo que cada una requiere (o con lo que declara compatible) antes que ella. El resto, en orden alfabético."""
    pids = set(pids)
    ps = todas()
    orden, vistos = [], set()

    def reqs(pid):
        p = ps.get(pid) or {}
        r = set(p.get("requiere", [])) | set(p.get("compatible", {})) | set((requisitos or {}).get(pid, []))
        return sorted(r & pids)

    def visitar(pid, camino=()):
        if pid in vistos or pid in camino:
            return
        for r in reqs(pid):
            visitar(r, camino + (pid,))
        vistos.add(pid)
        orden.append(pid)
    for pid in sorted(pids):
        visitar(pid)
    return orden


def leer(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def escribir(ruta, valor, indent=None):
    """JSON atómico. Si el archivo ya existe, respeta su sangría (2 espacios, una tabulación…): así un en.json de la app no
    queda con un diff de cientos de líneas por un cambio de formato."""
    if indent is None:
        indent = 1
        try:
            with open(ruta, encoding="utf-8") as f:
                for linea in f:
                    m = re.match(r"^([ \t]+)\S", linea)
                    if m:
                        indent = m.group(1) if "\t" in m.group(1) else len(m.group(1))
                        break
        except OSError:
            pass
    escribir_atomico(ruta, (json.dumps(valor, ensure_ascii=False, indent=indent) + "\n").encode("utf-8"))


def escribir_atomico(ruta, contenido, modo=0o644):
    """Escribe `contenido` (bytes) en `ruta` de una vez y sin seguir enlaces: el temporal es nuevo (mkstemp, O_EXCL) en la misma
    carpeta, se le ponen los permisos con fchmod y reemplaza a `ruta` (si `ruta` era un enlace, se reemplaza el enlace, no lo
    que apunta). Así un «x.tmp» o un «x» que sean enlaces a otro lado nunca hacen escribir fuera de la app."""
    carpeta = os.path.dirname(ruta) or "."
    fd, tmp = tempfile.mkstemp(dir=carpeta, prefix="." + os.path.basename(ruta) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenido)
            os.fchmod(f.fileno(), modo)
        os.replace(tmp, ruta)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def huella(ruta):
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def version_num(v):
    return tuple(int(x) for x in v.split("."))


#: Licencias que acepta una pieza (las oficiales, MPL-2.0: quien mejora la pieza la comparte; la app que la usa elige la suya).
LICENCIAS = {"MPL-2.0", "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "LGPL-3.0", "GPL-3.0", "AGPL-3.0"}
AVISO_MPL = "mozilla.org/MPL/2.0"
CODIGO = (".py", ".js", ".mjs", ".swift", ".kt", ".css", ".sh")

_EXTRA = {}  # piezas de la comunidad ya bajadas y verificadas: id → carpeta
_FUENTE = {}  # y de dónde salieron: {repo, commit, revision}


def carpeta_de(pid):
    return _EXTRA.get(pid, os.path.join(PIEZAS, pid))


def pieza(pid):
    p = leer(os.path.join(carpeta_de(pid), "pieza.json"))
    if not p:
        sys.exit(f"No existe la pieza «{pid}». Mira: pieza.py listar")
    return p


def todas():
    return {d: leer(os.path.join(PIEZAS, d, "pieza.json")) for d in sorted(os.listdir(PIEZAS))
            if os.path.isfile(os.path.join(PIEZAS, d, "pieza.json"))}


def con_requisitos(pid, vistos=None, camino=()):
    """La pieza y todo lo que requiere, en orden (primero lo que se necesita antes). Un ciclo es un error."""
    vistos = vistos if vistos is not None else []
    if pid in camino:
        sys.exit("«requiere» tiene un ciclo: " + " → ".join(camino + (pid,)))
    for r in pieza(pid).get("requiere", []):
        if r not in vistos:
            con_requisitos(r, vistos, camino + (pid,))
    if pid not in vistos:
        vistos.append(pid)
    return vistos


#: Dónde puede escribir una pieza dentro de una app. Nunca .github/, .git/, .claude/ ni nada que empiece con punto: ahí un
#: archivo «más» ejecuta código (workflows, hooks de git, hooks de la IA).
PREFIJOS_DESTINO = ("bin/", "ui/", "app/", "escritorio/", "movil/", "docs/", "pruebas/", "herramientas/")


def ruta_relativa_ok(r):
    return (isinstance(r, str) and 0 < len(r) < 200 and not r.startswith("/") and "\\" not in r and ":" not in r
            and all(x not in ("", ".", "..") and not x.startswith(".") for x in r.split("/")))


#: La forma de cada campo, antes de mirar su contenido (un pieza.json de afuera puede traer cualquier cosa).
FORMA = {"version": str, "estado": str, "nombre": str, "icono": str, "categoria": str, "descripcion": str, "recomendar": dict,
         "requiere": list, "compatible": dict, "plataformas": list, "pantallas": list, "permisos": dict, "red": list,
         "red_nota": str, "tareas_persona": list, "archivos": dict, "solo": dict, "solo_con": dict, "config": dict, "config_opcional": dict,
         "acciones": dict, "textos": dict, "textos_si_usa": dict, "app_json": dict,
         "cambios": list, "tomar_de": (str, list), "origen": str, "generar": dict, "datos_app": dict}


#: Las claves de app.json que son de la app (o de nucleo): una pieza no puede sumarlas con «app_json».
APP_JSON_PROPIAS = {"formato", "id", "nombre", "repo", "version", "datos", "privado", "plataformas", "config", "acciones", "sin_acciones",
                    "ia", "icono"}


def errores_forma(p):
    if not isinstance(p, dict):
        return ["pieza.json no es un objeto"]
    e = [f"«{k}» tiene el tipo equivocado" for k, t in FORMA.items() if k in p and not isinstance(p[k], t)]
    if e:
        return e
    if not all(isinstance(x, str) for x in p.get("requiere", []) + p.get("red", []) + p.get("plataformas", [])):
        e.append("«requiere», «red» y «plataformas» son listas de textos")
    if not all(isinstance(v, list) for v in p.get("permisos", {}).values()):
        e.append("«permisos» es {plataforma: [{clave, por}]}")
    if not all(isinstance(c, dict) for c in p.get("cambios", [])):
        e.append("cada cambio es un objeto")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in p.get("archivos", {}).items()):
        e.append("«archivos» es {origen: destino} con textos")
    if not all(isinstance(k, str) and k in p.get("config", {}) and isinstance(v, str) for k, v in p.get("config_opcional", {}).items()):
        e.append("«config_opcional» es {clave de «config»: cuándo la suma la app}")
    if not all(isinstance(k, str) and re.match(r"^[A-Za-z_$][\w$]{1,60}$", k) and isinstance(v, dict)
               and all(isinstance(a, str) and isinstance(b, str) for a, b in v.items()) for k, v in p.get("textos_si_usa", {}).items()):
        e.append("«textos_si_usa» es {identificador que usa la app: {frase: traducción}}")
    if not all(isinstance(k, str) and re.match(r"^[a-z][a-z0-9_]{1,30}$", k) and k not in APP_JSON_PROPIAS and isinstance(v, dict)
               and isinstance(v.get("esqueleto"), dict) and isinstance(v.get("que"), str) for k, v in p.get("app_json", {}).items()):
        e.append("«app_json» es {sección de app.json (no una de la app): {esqueleto: {…}, que: \"qué completar\"}}")
    if not all(isinstance(v, str) for v in p.get("compatible", {}).values()):
        e.append("«compatible» es {pieza: rango}")
    for a in p.get("acciones", {}).values():
        if not isinstance(a, dict) or not isinstance(a.get("datos", {}), dict) or not isinstance(a.get("args", []), list) \
                or not all(isinstance(x, str) for x in a.get("args", [])) \
                or not all(isinstance(r, dict) for r in a.get("datos", {}).values()):
            e.append("cada acción es {script, args: [textos], datos: {campo: {tipo…}}, limite}")
            break
    return e


#: Lo que el host puede poner en una acción («inyectar»): las fuentes del host y las que registre la app (mismo formato).
CAMPO = re.compile(r"^[A-Za-z_]\w{0,60}$")
NOMBRE_ACCION = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,60}$")


def errores_accion(nombre, a, scripts=None):
    """Las reglas de una acción declarada (docs/enchufe.md, «Una acción»). Las mismas revisan los hosts al cargar
    acciones.json (enchufe.js de «host-escritorio» y Enchufe.swift de «host-mac»). `scripts`: los de la pieza (None: los de la app)."""
    donde = f"acción «{nombre}»"
    e = []
    if not NOMBRE_ACCION.match(nombre):
        e.append(f"{donde}: nombre raro (letras y números, empieza con letra)")
    if not isinstance(a, dict):
        return e + [f"{donde}: no es un objeto"]
    # Una acción en Rust («rust»: true) la atiende una función de la app (`host.funcion`), sin script ni argumentos: el host
    # valida igual sus datos y le pasa la entrada en el mismo proceso (docs/rust.md, fase 2).
    rust = a.get("rust") is True
    if "rust" in a and not rust:
        e.append(f"{donde}: «rust» solo puede ser true")
    if rust:
        if "script" in a or a.get("args") or "entrada" in a:
            e.append(f"{donde}: una acción en Rust no lleva «script», «args» ni «entrada»")
    elif not SCRIPT.match(a.get("script", "") if isinstance(a.get("script"), str) else ""):
        e.append(f"{donde}: «script» debe ser nombre.py")
    elif scripts is not None and a["script"] not in scripts and not a.get("scriptDeLaApp"):
        e.append(f"{donde}: el script {a['script']} no viene en la pieza (o marca scriptDeLaApp)")
    datos, args = a.get("datos", {}), a.get("args", [])
    if not isinstance(datos, dict) or not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        return e + [f"{donde}: «datos» es {{campo: regla}} y «args» una lista de textos"]
    maximo = a.get("maximo", MAXIMO_ENTRADA)
    if not _entero(maximo) or not 0 < maximo <= TOPE_ENTRADA:
        e.append(f"{donde}: «maximo» (bytes de la entrada) es un entero hasta {TOPE_ENTRADA}")
        maximo = MAXIMO_ENTRADA
    for campo, regla in datos.items():
        if campo == "*":
            if regla != "pasar":
                e.append(f"{donde}: «*» solo puede ser \"pasar\"")
            continue
        if not CAMPO.match(campo) or campo in ("__proto__", "constructor", "prototype"):
            e.append(f"{donde}: campo raro «{campo}»")
        e += _errores_regla(f"{donde}: «{campo}»", regla, maximo)
    for arg in args:
        if arg.startswith("$"):
            regla = datos.get(arg[1:], {})
            # Regla de oro: lo que escribe la persona nunca va como argumento del proceso, solo por el archivo de entrada.
            if not isinstance(regla, dict) or regla.get("tipo") not in ("enum", "entero"):
                e.append(f"{donde}: el argumento {arg} solo puede ser un campo enum o entero")
        elif not re.match(r"^[\w.-]+$", arg):
            e.append(f"{donde}: argumento literal raro «{arg}»")
    por_archivo = [k for k in datos if k == "*" or ("$" + k) not in args]
    inyectar = a.get("inyectar", {})
    if not isinstance(inyectar, dict) or not all(isinstance(k, str) and CAMPO.match(k) and isinstance(v, str) and CAMPO.match(v)
                                                 for k, v in inyectar.items()):
        e.append(f"{donde}: «inyectar» es {{campo: fuente}}")
    else:
        e += [f"{donde}: «{k}» lo pone el host: no puede venir también en «datos»" for k in inyectar if k in datos]
        por_archivo += list(inyectar)
    if por_archivo and a.get("entrada") != "archivo" and not rust:
        e.append(f"{donde}: {', '.join(por_archivo)} no van en args: necesita \"entrada\": \"archivo\"")
    if a.get("entrada") not in (None, "archivo"):
        e.append(f"{donde}: «entrada» es \"archivo\" o null")
    e += _errores_limite(donde, a.get("limite"), datos)
    v = a.get("vigilar")
    if v is not None:
        ruta, texto = datos.get("ruta"), datos.get("texto")
        if v not in ("lee", "escribe") or not (isinstance(ruta, dict) and ruta.get("tipo") == "rutaRelativa") \
                or (v == "escribe" and not (isinstance(texto, dict) and texto.get("tipo") == "texto")):
            e.append(f"{donde}: «vigilar» es \"lee\" o \"escribe\", con «ruta» (rutaRelativa) en datos (y «texto» para escribe)")
    for k in ("responde", "progreso"):
        v = a.get(k)
        if v is not None and not (isinstance(v, str) and NOMBRE_ACCION.match(v)):
            e.append(f"{donde}: «{k}» es el nombre de una función")
    for k, patron in (("eco", CAMPO), ("despues", NOMBRE_ACCION)):
        v = a.get(k)
        if v is not None and not (isinstance(v, list) and all(isinstance(x, str) and patron.match(x) for x in v)):
            e.append(f"{donde}: «{k}» es una lista de nombres")
    if a.get("cola") not in (None, "escritura"):
        e.append(f"{donde}: «cola» solo puede ser \"escritura\"")
    return e


#: Lo que puede pesar la entrada de una acción: 5 MB salvo que diga «maximo» (hasta 50 MB, p. ej. guardar un documento grande).
MAXIMO_ENTRADA = 5 * 1024 * 1024
TOPE_ENTRADA = 50 * 1024 * 1024


def _entero(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _limite_ok(x):
    return x == "trabajo" or (_entero(x) and 1 <= x <= 3600)


def _errores_limite(donde, limite, datos):
    """«limite»: segundos (1 a 3600), "trabajo" (sin tope, mientras lata: pieza «trabajos») o según el valor de un campo enum:
    {"segun": "orden", "valores": {"documentar": "trabajo", "leer": 60}, "otro": 120}."""
    malo = [f"{donde}: «limite» es obligatorio: segundos (1 a 3600), \"trabajo\" o {{\"segun\": campo, \"valores\": {{…}}, \"otro\": …}}"]
    if not isinstance(limite, dict):
        return [] if _limite_ok(limite) else malo
    regla = datos.get(limite.get("segun")) if isinstance(limite.get("segun"), str) else None
    valores = limite.get("valores")
    if set(limite) - {"segun", "valores", "otro"} or not (isinstance(regla, dict) and regla.get("tipo") == "enum") \
            or not isinstance(valores, dict) or not _limite_ok(limite.get("otro")) \
            or not all(k in (regla.get("valores") or []) and _limite_ok(v) for k, v in valores.items()):
        return malo
    return []


def _errores_regla(donde, r, maximo=MAXIMO_ENTRADA):
    if not isinstance(r, dict) or r.get("tipo") not in TIPOS:
        return [f"{donde}: tipo desconocido"]
    e, t = [], r["tipo"]
    entero = _entero
    if t == "texto" and not (entero(r.get("max")) and 0 < r["max"] <= maximo):
        e.append(f"{donde}: un texto necesita «max»")
    if t == "enum" and not (isinstance(r.get("valores"), list) and r["valores"]
                            and all(isinstance(x, str) and re.match(r"^[\w.-]+$", x) for x in r["valores"])):
        e.append(f"{donde}: un enum necesita «valores» (textos simples)")
    if t == "entero" and any(k in r and not entero(r[k]) for k in ("min", "max")):
        e.append(f"{donde}: «min»/«max» son enteros")
    if t == "base64" and not (entero(r.get("maxBytes")) and 0 < r["maxBytes"] <= maximo):
        e.append(f"{donde}: base64 necesita «maxBytes»")
    if t == "rutaRelativa" and "extensiones" in r and not (isinstance(r["extensiones"], list)
                                                          and all(isinstance(x, str) and re.match(r"^\.\w{1,10}$", x) for x in r["extensiones"])):
        e.append(f"{donde}: «extensiones» es una lista como [\".md\"]")
    if t == "lista":
        if "max" in r and not (entero(r["max"]) and 0 < r["max"] <= 10000):
            e.append(f"{donde}: «max» de una lista es un entero")
        if "de" in r:
            e += [f"{donde}: una lista de listas no"] if isinstance(r["de"], dict) and r["de"].get("tipo") == "lista" \
                else _errores_regla(f"{donde} (cada uno)", r["de"], maximo)
    return e


def destino_seguro(app, relativa):
    """La ruta donde escribir `relativa` dentro de la app. Se resuelven los enlaces de las carpetas (tienen que quedar dentro),
    pero no el del archivo: si el destino es un enlace, se reemplaza el enlace (escribir_atomico), nunca lo que apunta."""
    nombre = os.path.basename(relativa)
    carpeta = os.path.realpath(os.path.dirname(os.path.join(app, relativa)))
    ruta = os.path.join(carpeta, nombre)
    if os.path.isabs(relativa) or nombre in ("", ".", "..") or not ruta.startswith(os.path.realpath(app) + os.sep):
        sys.exit(f"Destino fuera de la app: {relativa}")
    return ruta


def origen_seguro(app, relativa):
    """Para LEER algo de la app: aquí sí se sigue el enlace, pero lo que apunta tiene que quedar dentro."""
    ruta = os.path.realpath(destino_seguro(app, relativa))
    if not ruta.startswith(os.path.realpath(app) + os.sep):
        sys.exit(f"Fuera de la app: {relativa}")
    return ruta


# ── Generar (pieza.json → «generar»: archivos que se llenan desde app.json) ──────────────────────────────────────────────────
# Una pieza puede, además de copiar archivos, GENERARLOS desde una plantilla (herramientas/plantillas.py, solo datos: nunca se
# ejecuta código de la pieza). El resultado se anota con su huella en piezas.json → «generados»: si la app lo cambia, la pieza ya
# no lo toca. Ver docs/enchufe.md, «Plantillas».

#: Los únicos lugares con punto donde una pieza OFICIAL puede generar (workflows, plantillas de GitHub, agentes de la IA): ahí un
#: archivo ejecuta código, así que una pieza de la comunidad nunca genera, y lo de .github/ nunca se actualiza solo.
PUNTO_GENERADO = (".github/", ".claude/agents/", ".claude/settings.json", ".gitignore", "escritorio/.npmrc")
#: Lo generado que «Pieza al día» (--automatico) nunca actualiza solo: va al aviso para que lo vea una persona. En .github/ un
#: workflow corre con los permisos del repo (y el token de Actions no puede escribirlos); en .claude/ unos ajustes pueden
#: definir hooks que corren en el computador de quien abre el repo con su IA.
A_MANO = (".github/", ".claude/")
#: Lo que escribe pieza.py o la app: una plantilla nunca lo pisa.
NO_GENERAR = {"app.json", "piezas.json", "acciones.json"}


def destino_generado_ok(d):
    if not isinstance(d, str) or not 0 < len(d) < 200 or d.startswith("/") or "\\" in d or ":" in d or d in NO_GENERAR:
        return False
    partes = d.split("/")
    if any(x in ("", ".", "..") for x in partes) or d.startswith(".git/"):
        return False
    if not any(x.startswith(".") for x in partes):
        return len(partes) == 1 or d.startswith(PREFIJOS_DESTINO)
    for x in PUNTO_GENERADO:  # con punto: solo lo de la lista, y nada más con punto adentro
        if d == x:
            return True
        if x.endswith("/") and d.startswith(x):
            return not any(y.startswith(".") for y in d[len(x):].split("/"))
    return False


def reglas_generar(p):
    """{origen: {destino, una_vez, si}} con la forma larga."""
    r = {}
    for origen, v in (p.get("generar") or {}).items():
        v = {"destino": v} if isinstance(v, str) else (v if isinstance(v, dict) else {})
        r[origen] = {"destino": v.get("destino"), "una_vez": bool(v.get("una_vez")), "si": v.get("si")}
    return r


def errores_generar(pid, p, carpeta="local"):
    import plantillas
    e = []
    for origen, v in (p.get("generar") or {}).items():
        if not (isinstance(v, str) or (isinstance(v, dict) and set(v) <= {"destino", "una_vez", "si"})):
            e.append(f"generar «{origen}»: es \"destino\" o {{destino, una_vez?, si?}}")
            continue
        r = reglas_generar({"generar": {origen: v}})[origen]
        if not ruta_relativa_ok(origen) or not origen.startswith("plantillas/"):
            e.append(f"generar: origen inválido {origen} (va en plantillas/ de la pieza, sin carpetas con punto)")
        try:  # el destino puede llevar marcas ({{id}}): se revisa como quedaría en una app de ejemplo
            destino = plantillas.llenar(str(r["destino"]), plantillas.contexto({"id": "ana", "nombre": "Ana"}))
        except plantillas.PlantillaMala as x:
            destino = None
            e.append(f"generar «{origen}»: destino {r['destino']}: {x}")
        if destino is not None and not destino_generado_ok(destino):
            e.append(f"generar: destino inválido {r['destino']} (no app.json/piezas.json/acciones.json; con punto solo "
                     f"{', '.join(PUNTO_GENERADO)})")
        if r["si"] is not None and not (isinstance(r["si"], str) and re.fullmatch(r"!?[A-Za-z_][\w-]*(\.[\w-]+)*", r["si"])):
            e.append(f"generar «{origen}»: «si» es una ruta del contexto (ej. \"mac\", \"escritorio\", \"!windows\")")
        ruta = os.path.join(carpeta_de(pid), origen)
        if carpeta is not None:
            if not os.path.isfile(ruta) or os.path.islink(ruta):
                e.append(f"falta la plantilla {origen}")
            else:
                e += [f"plantilla {origen}: {x}" for x in plantillas.revisar(open(ruta, encoding="utf-8").read())]
    for nombre, ruta in (p.get("datos_app") or {}).items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", str(nombre)) or not ruta_relativa_ok(ruta) or not str(ruta).endswith(".json"):
            e.append(f"datos_app: «{nombre}» → «{ruta}» (un nombre y un .json de la app)")
    return e


def contexto_de(pid, app, lock):
    """El contexto de las plantillas de una pieza en esta app: app.json, las piezas instaladas y los datos que pide."""
    import plantillas
    p = pieza(pid)
    a = leer(os.path.join(app, "app.json"), {}) or {}
    datos = {}
    for nombre, ruta in (p.get("datos_app") or {}).items():
        datos[nombre] = leer(origen_seguro(app, ruta)) if ruta_relativa_ok(ruta) else None
    ctx = plantillas.contexto(a, piezas=sorted(set(lock["piezas"]) | {pid}), datos=datos)
    ctx["pieza"] = {"id": pid, "version": p["version"]}
    # Las piezas instaladas con su nombre, versión y archivos (para la tabla «Piezas» de AGENTS.md y lo que no se edita a mano).
    ctx["piezas_lista"] = [{"id": x, "nombre": (todas().get(x) or {}).get("nombre", x), "version": i.get("version", ""),
                            "archivos": sorted(i.get("archivos", {}))} for x, i in sorted(lock["piezas"].items())]
    return ctx


def generados_de(pid, app, lock):
    """[(destino, texto o None si no corresponde, una_vez)] de lo que la pieza genera para esta app."""
    import plantillas
    p = pieza(pid)
    if not p.get("generar"):
        return []
    if pid in _EXTRA:
        sys.exit(f"«{pid}» es de la comunidad: una pieza de la comunidad no genera archivos.")
    try:
        ctx = contexto_de(pid, app, lock)
        r = []
        for origen, regla in reglas_generar(p).items():
            destino = plantillas.llenar(str(regla["destino"]), ctx)  # puede llevar marcas: ".claude/agents/{{id}}-revisor.md"
            if not destino_generado_ok(destino) or not ruta_relativa_ok(origen):
                sys.exit(f"{pid}: no genero {origen} → {destino} (ruta no permitida)")
            si = regla["si"]
            cumple = True
            if si:
                cumple = plantillas.verdad(plantillas.buscar(ctx, si.lstrip("!")))
                cumple = not cumple if si.startswith("!") else cumple
            texto = None
            if cumple:
                fuente = os.path.join(carpeta_de(pid), origen)
                if os.path.islink(fuente):
                    sys.exit(f"{pid}: {origen} es un enlace")
                try:
                    texto = plantillas.llenar(open(fuente, encoding="utf-8").read(), ctx)
                except plantillas.PlantillaMala as e:
                    raise plantillas.PlantillaMala(f"{origen}: {e}") from None
            r.append((destino, texto, regla["una_vez"]))
        return r
    except plantillas.PlantillaMala as e:
        sys.exit(f"No pude generar los archivos de «{pid}»: {e}\n(revisa app.json: lo que pide la pieza está en su README)")


def _huella_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _escribir_texto(ruta, texto):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    escribir_atomico(ruta, texto.encode("utf-8"), 0o755 if ruta.endswith((".sh", ".command")) else 0o644)


def generar_pieza(pid, app, lock, forzar=False, automatico=False):
    """Escribe lo que genera la pieza, sin pisar lo que la app cambió (salvo --forzar). Anota en lock (no lo guarda)."""
    info = lock["piezas"].get(pid)
    if info is None:
        return
    generados, una_vez = dict(info.get("generados", {})), list(info.get("una_vez", []))
    vistos = set()
    for destino, texto, solo_una in generados_de(pid, app, lock):
        vistos.add(destino)
        ruta = destino_seguro(app, destino)
        if texto is None:
            if destino in generados:
                print(f"    ! {pid}: ya no genera {destino} (app.json cambió); bórralo si la app no lo usa")
                generados.pop(destino)
            continue
        if solo_una:
            if destino not in una_vez:
                if not os.path.exists(ruta):
                    _escribir_texto(ruta, texto)
                    print(f"    + {destino} (para completar: lo que dice <!-- La app: … -->)" if "<!-- La app:" in texto
                          else f"    + {destino}")
                else:
                    print(f"    · {destino} ya existía: queda el de la app")
                una_vez.append(destino)
            continue
        nueva = _huella_texto(texto)
        anotada = generados.get(destino)
        actual = huella(ruta) if os.path.isfile(ruta) else None
        if actual == nueva:
            generados[destino] = nueva
            continue
        if actual is not None and not forzar and (anotada is None or anotada == "" or actual != anotada):
            if anotada is None:
                print(f"    ! {destino} ya existe y es distinto de lo que genera «{pid}»: queda el de la app"
                      f" (compara: pieza.py diferencias {app} {pid}; reemplázalo con pieza.py generar {app} {pid} --forzar)")
            elif anotada != "":
                print(f"    ! no regeneré {destino}: la app lo cambió (pieza.py diferencias {app} {pid})")
            generados[destino] = anotada if anotada is not None else ""
            continue
        if automatico and destino.startswith(A_MANO):
            # El token de Actions no puede escribir workflows, y un workflow o unos ajustes de la IA (hooks) los ve una persona.
            print(f"    ! {destino} cambia: va a mano (pieza.py generar . {pid})")
            continue
        _escribir_texto(ruta, texto)
        generados[destino] = nueva
        print(f"    {'~' if actual is not None else '+'} {destino}")
    for d in sorted(set(generados) - vistos):
        print(f"    ! {pid}: ya no genera {d}; bórralo si la app no lo usa")
        generados.pop(d)
    info["generados"] = dict(sorted(generados.items()))
    if una_vez:
        info["una_vez"] = sorted(una_vez)
    if not info["generados"]:
        info.pop("generados")


def generar_todo(app, solas=None, forzar=False, automatico=False):
    """Vuelve a llenar lo generado de las piezas instaladas (después de agregar, actualizar o cambiar app.json). Solo las que
    están en la misma versión que la base: una que quedó atrás se regenera cuando se actualice."""
    lock = candado(app)
    hubo = False
    for pid in orden_dependencias(lock["piezas"]):
        if solas and pid not in solas:
            continue
        info = lock["piezas"][pid]
        p = {} if info.get("fuente") else (todas().get(pid) or {})
        if not p.get("generar"):
            continue
        if p.get("version") != info.get("version"):
            print(f"    · {pid}: no regeneré (la app tiene {info.get('version')}, la base {p.get('version')}: actualízala primero)")
            continue
        generar_pieza(pid, app, lock, forzar=forzar, automatico=automatico)
        hubo = True
    if hubo:
        escribir(os.path.join(app, "piezas.json"), lock)


def pendientes_github(pid, app, lock):
    """Los archivos de .github/ y .claude/ (A_MANO) que la versión de la base generaría distinto de lo que hay (y que la app no
    cambió): van al aviso, nunca solos."""
    info = lock["piezas"].get(pid) or {}
    p = todas().get(pid) or {}
    if info.get("fuente") or not any(r["destino"].startswith(A_MANO) for r in reglas_generar(p).values()):
        return []
    try:
        salida = generados_de(pid, app, lock)
    except SystemExit:
        return []
    r = []
    for destino, texto, solo_una in salida:
        if texto is None or solo_una or not destino.startswith(A_MANO):
            continue
        ruta = os.path.join(app, destino)
        actual = huella(ruta) if os.path.isfile(ruta) else None
        anotada = info.get("generados", {}).get(destino)
        if actual != _huella_texto(texto) and (actual is None or anotada == actual):
            r.append(destino)
    return r


# ── Revisar ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def errores_pieza(pid, p, ids, carpeta="local"):
    e = errores_forma(p)
    if e:
        return e
    if p.get("id") != pid or not ID.match(pid):
        e.append("«id» debe ser igual a la carpeta: minúsculas, números y guiones")
    if not VERSION.match(str(p.get("version", ""))):
        e.append("«version» debe ser X.Y.Z")
    if p.get("estado", "lista") not in ESTADOS:
        e.append("«estado» debe ser lista, planeada o retirada")
    if p.get("estado") == "retirada" and not (isinstance(p.get("reemplazo"), str) and p["reemplazo"]):
        e.append("una pieza «retirada» dice qué la reemplaza («reemplazo»)")
    if p.get("estado") == "planeada" and (p.get("archivos") or not p.get("tomar_de")):
        e.append("una pieza planeada no trae archivos y dice de dónde tomarla («tomar_de»)")
    if p.get("categoria") not in CATEGORIAS:
        e.append(f"«categoria» debe ser una de {sorted(CATEGORIAS)}")
    if not isinstance(p.get("descripcion"), str) or not p["descripcion"]:
        e.append("falta «descripcion»")
    if not isinstance(p.get("icono"), str) or not p["icono"].endswith(".svg") or ".." in p["icono"] or p["icono"].startswith("/"):
        e.append("«icono» es obligatorio: un .svg dentro de la pieza (24×24, currentColor), p. ej. \"icono.svg\"")
    elif carpeta is not None:
        ruta = os.path.join(carpeta_de(pid), p["icono"])
        if not os.path.isfile(ruta):
            e.append(f"falta el ícono {p['icono']}")
        else:
            import icono
            e += [f"ícono: {x}" for x in icono.errores(open(ruta, encoding="utf-8").read(), solo_current=True)]
    if p.get("licencia") not in LICENCIAS:
        e.append(f"«licencia» es obligatoria: una de {', '.join(sorted(LICENCIAS))} (las oficiales, MPL-2.0)")
    elif carpeta is not None and pid not in _EXTRA:
        if p["licencia"] != "MPL-2.0":
            e.append("las piezas oficiales son MPL-2.0")
        for origen in p.get("archivos", {}):
            ruta = os.path.join(carpeta_de(pid), origen)
            if origen.endswith(CODIGO) and os.path.isfile(ruta) and AVISO_MPL not in open(ruta, encoding="utf-8").read(2000):
                e.append(f"{origen}: falta el aviso de la MPL-2.0 al inicio (ver docs/enchufe.md, «Licencia»)")
    rec = p.get("recomendar")
    if not isinstance(rec, dict) or not isinstance(rec.get("cuando"), str):
        e.append("«recomendar» necesita {\"cuando\": \"…\"} (y opcional \"siempre\": true, \"palabras\": […])")
    for x in p.get("pantallas", []):
        if not (isinstance(x, dict) and {"donde", "nombre", "que"} <= set(x)):
            e.append("cada pantalla es {donde, nombre, que}")
    for plat, lista in p.get("permisos", {}).items():
        if plat not in PLATAFORMAS:
            e.append(f"permisos: plataforma desconocida «{plat}»")
        for x in lista:
            if not (isinstance(x, dict) and {"clave", "por"} <= set(x)):
                e.append(f"permisos {plat}: cada uno es {{clave, por}}")
    for d in p.get("red", []):
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", d):
            e.append(f"red: dominio raro «{d}»")
    for plat in p.get("plataformas", PLATAFORMAS):
        if plat not in PLATAFORMAS:
            e.append(f"plataformas: «{plat}» desconocida")
    for origen, plats in p.get("solo", {}).items():
        if origen not in p.get("archivos", {}) or not isinstance(plats, list) or not plats or any(x not in PLATAFORMAS for x in plats):
            e.append(f"solo: «{origen}» tiene que ser un archivo de la pieza con una lista de plataformas")
    for origen, con in p.get("solo_con", {}).items():
        if origen not in p.get("archivos", {}) or not isinstance(con, list) or not con or not all(isinstance(x, str) and ID_PIEZA.match(x) for x in con):
            e.append(f"solo_con: «{origen}» tiene que ser un archivo de la pieza con una lista de piezas (ej. [\"host-tauri\"])")
    cambios = p.get("cambios", [])
    if p.get("estado", "lista") == "lista":
        if not cambios or cambios[0].get("version") != p.get("version"):
            e.append("«cambios» debe empezar con la versión actual (lo que cambió, para avisar a las apps)")
        previa = None
        for c in cambios:
            if c.get("tipo") not in TIPOS_CAMBIO or not isinstance(c.get("resumen"), str) or not VERSION.match(str(c.get("version", ""))):
                e.append("cada cambio es {version, tipo: inicial|arreglo|mejora|rompe, resumen, seguridad?, migrar?}")
                continue
            if c["tipo"] == "rompe" and not c.get("migrar"):
                e.append(f"cambio {c['version']}: lo que rompe necesita «migrar» (los pasos)")
            if "migrar" in c and (not isinstance(c["migrar"], list)
                                  or not all(isinstance(x, str) and x.strip() for x in c["migrar"])):
                # «Pieza al día» recorre la lista: un texto saldría con una viñeta por letra.
                e.append(f"cambio {c['version']}: «migrar» es una lista de pasos (textos), no un texto")
            if previa and semver(c["version"]) >= semver(previa["version"]):
                e.append("«cambios» va de la versión más nueva a la más vieja, sin repetir")
            if previa:
                a, b = semver(c["version"]), semver(previa["version"])
                rompe_ok = (b[0] > a[0]) or (a[0] == 0 and b[0] == 0 and b[1] > a[1])
                if previa["tipo"] == "rompe" and not rompe_ok:
                    e.append(f"{previa['version']} rompe: sube X (o Y si X es 0)")
            previa = c
    for req, rango in p.get("compatible", {}).items():
        if req not in p.get("requiere", []):
            e.append(f"compatible: «{req}» no está en requiere")
        elif any(not RANGO.match(x) for x in rango.split()):
            e.append(f"compatible: rango raro «{rango}» (ej. \">=0.1.0 <1.0.0\")")
        elif req in ids and (ids[req] or {}).get("estado", "lista") == "lista" and not satisface(ids[req]["version"], rango):
            e.append(f"compatible: «{req}» {ids[req]['version']} no cumple {rango}: actualiza esta pieza o el rango")
    for r in p.get("requiere", []):
        if r not in ids:
            e.append(f"requiere «{r}», que no existe")
    for origen, destino in p.get("archivos", {}).items():
        if carpeta is not None and not os.path.isfile(os.path.join(carpeta_de(pid), origen)):
            e.append(f"falta el archivo {origen}")
        if not ruta_relativa_ok(origen):
            e.append(f"origen inválido {origen}")
        elif carpeta is not None and os.path.islink(os.path.join(carpeta_de(pid), origen)):
            e.append(f"{origen} es un enlace: copia el archivo")
        if not ruta_relativa_ok(destino) or not destino.startswith(PREFIJOS_DESTINO):
            e.append(f"destino inválido {destino}: va dentro de {', '.join(PREFIJOS_DESTINO)} (nunca carpetas que empiezan con punto)")
    e += errores_generar(pid, p, carpeta)
    scripts = {os.path.basename(d) for d in p.get("archivos", {}).values()}
    for nombre, a in p.get("acciones", {}).items():
        e += errores_accion(nombre, a, scripts)
    return e


def revisar():
    ps = todas()
    total = 0
    def ciclo(pid, camino=()):
        if pid in camino:
            return " → ".join(camino + (pid,))
        for r in ((ps.get(pid) or {}).get("requiere") or []):
            c = ciclo(r, camino + (pid,)) if r in ps else None
            if c:
                return c
        return None
    for pid, p in ps.items():
        e = errores_pieza(pid, p or {}, ps)
        c = ciclo(pid)
        if c:
            e.append(f"«requiere» tiene un ciclo: {c}")
        total += len(e)
        print(f"{'✗' if e else '✓'} {pid}" + "".join(f"\n    {x}" for x in e))
    return 1 if total else 0


# ── App ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def candado(app):
    return leer(os.path.join(app, "piezas.json"), {"formato": 1, "piezas": {}})


def iniciar(app, aid, nombre, plataformas=None, datos="sistema"):
    ruta = os.path.join(app, "app.json")
    if os.path.exists(ruta):
        sys.exit("Esta app ya tiene app.json.")
    if not re.match(r"^[a-z][a-z0-9]{0,30}$", aid):  # la misma regla que nucleo.app()
        sys.exit("El id va en minúsculas, solo letras y números (ej. esquema).")
    plataformas = plataformas or list(PLATAFORMAS)
    if datos not in ("sistema", "visible"):
        sys.exit("--datos=sistema (Application Support…) o --datos=visible (~/<Nombre>/.<id>).")
    if any(x not in PLATAFORMAS for x in plataformas):
        sys.exit(f"Plataformas: {', '.join(PLATAFORMAS)}.")
    escribir(ruta, {"nombre": nombre, "id": aid, "version": "0.1.0", "repo": f"{aid}-app/{aid}", "datos": datos, "icono": "docs/favicon.svg", "plataformas": plataformas,
                    "config": {"idioma_ui": ["es", "en"], "bienvenida": "bool"}})
    print(f"+ {ruta}")
    # Muchas apps tienen un .gitignore de lista blanca («/*» y luego «!…»): ahí app.json y piezas.json quedarían fuera sin aviso.
    gi = os.path.join(app, ".gitignore")
    if os.path.isfile(gi):
        lineas = [l.strip() for l in open(gi, encoding="utf-8")]
        if "/*" in lineas or "*" in lineas:
            faltan = [x for x in ("!/app.json", "!/piezas.json") if x not in lineas and x.replace("/", "", 1) not in lineas]
            if faltan:
                with open(gi, "a", encoding="utf-8") as f:
                    f.write("\n# Pieza: la descripción de la app y las piezas que usa\n" + "\n".join(faltan) + "\n")
                print(f"~ {gi}: agregué {', '.join(faltan)} (es una lista blanca)")
    # «Pieza al día»: avisa cada semana si hay versiones nuevas de las piezas (PR solo o issue con los pasos).
    flujo = os.path.join(app, ".github", "workflows", "pieza-al-dia.yml")
    if not os.path.exists(flujo):
        os.makedirs(os.path.dirname(flujo), exist_ok=True)
        with open(os.path.join(BASE, "plantillas", "pieza-al-dia.yml"), "rb") as f:
            escribir_atomico(flujo, f.read())
        print(f"+ {flujo}")
    # Quien abra el repo en Claude Code recibe la sugerencia de instalar el plugin de Pieza (mismos flujos para aportar).
    ajustes_ruta = os.path.join(app, ".claude", "settings.json")
    ajustes = leer(ajustes_ruta, {}) or {}
    ajustes.setdefault("extraKnownMarketplaces", {}).setdefault("pieza", {"source": {"source": "github", "repo": "pieza-app/pieza"}})
    os.makedirs(os.path.dirname(ajustes_ruta), exist_ok=True)
    escribir(ajustes_ruta, ajustes)
    print(f"+ {ajustes_ruta}")
    print("Falta (con permiso de quien mantiene): el topic «hecho-con-pieza» en el repo, el sello en el README y la página, y el"
          " ícono en docs/favicon.svg (solo formas, ≤ 8 KB): así la app aparece con su ícono en la página de Pieza.")


# ── Crear una app nueva de una vez ──────────────────────────────────────────────────────────────────────────────────────────
# iniciar + las piezas de siempre para esas plataformas + las pedidas + «esqueleto» (lo propio mínimo, andando) + «github» al final
# (su AGENTS.md lista las demás), la acción de ejemplo en app.json, acciones.json y todo lo generado. Lo propio de la app sale de
# las plantillas de la pieza «esqueleto» (una vez; desde ahí es de la app): aquí no hay nada de ninguna app.

#: La acción de ejemplo que llama bin/ejemplo.py (de la pieza «esqueleto»): el texto va por archivo, nunca como argumento.
ACCION_EJEMPLO = {"script": "ejemplo.py", "args": ["contar"], "entrada": "archivo",
                  "datos": {"texto": {"tipo": "texto", "max": 20000}}, "responde": "ejemploListo", "limite": 30}
#: Archivos generados que nunca son «para completar» aunque digan «La app:» (de piezas, o la explicación de un formato).
_SIN_PENDIENTE = ("herramientas/org.github.io/",)


def pendientes_ia(app):
    """{archivo: líneas} con lo que dice «La app:» (lo que completa la IA), sin los archivos copiados de las piezas."""
    lock = candado(app)
    # Lo copiado y lo que se vuelve a generar (docs/index.html sale de docs/pagina.json) es de las piezas: no se completa ahí.
    copiados = {d for i in lock["piezas"].values() for k in ("archivos", "generados") for d in i.get(k, {})}
    r = {}
    for carpeta, dirs, archivos in os.walk(app):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "node_modules", "dist", ".build", "vendor"))
        for nombre in sorted(archivos):
            ruta = os.path.join(carpeta, nombre)
            rel = os.path.relpath(ruta, app).replace(os.sep, "/")
            if rel in copiados or rel in NO_GENERAR or rel.startswith(_SIN_PENDIENTE) or os.path.getsize(ruta) > 512 * 1024:
                continue
            try:
                n = sum(1 for l in open(ruta, encoding="utf-8") if re.search(r"\bLa app:", l))
            except (OSError, UnicodeDecodeError):
                continue
            if n:
                r[rel] = n
    return r


def crear(app, aid, nombre, plataformas, extra=(), repo=None, datos="sistema"):
    import contextlib
    import io
    import plantillas
    if not re.match(r"^[a-z][a-z0-9]{0,30}$", aid):  # la regla de iniciar (y de nucleo.app()), antes de crear la carpeta
        sys.exit("El id va en minúsculas, solo letras y números (ej. receta).")
    if os.path.exists(os.path.join(app, "app.json")) or (os.path.isdir(app) and os.listdir(app)):
        sys.exit(f"{app} ya existe y no está vacía: crear es para una app nueva (en una que ya existe: iniciar y agregar).")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,40}", plantillas._ascii(nombre) or "-") or not re.fullmatch(r"\w+", nombre) \
            or len(nombre) > 40:
        sys.exit("El nombre es una palabra que empieza con letra (puede llevar tildes: «Alcancía»): con él se llaman la app, su"
                 " carpeta de Mac y los archivos de las versiones.")
    plataformas = list(plataformas or ("mac", "windows", "linux"))
    if "android" in plataformas:
        sys.exit("Android todavía no: «host-movil» está por extraer (docs/catalogo.md). El iPhone sí («host-ios»).")
    if "ios" in plataformas and not set(plataformas) & {"mac", "windows", "linux"}:
        sys.exit("El iPhone va junto a una app de computador (mac, windows o linux): la interfaz y las pruebas se arman ahí.")
    if repo is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}", repo):
        sys.exit("--repo es «dueño/repo» (p. ej. ana-app/ana).")
    for pid in extra:
        if pid not in todas():
            sys.exit(f"No conozco la pieza «{pid}» (pieza.py catalogo).")
        if pieza(pid).get("estado") == "planeada":
            sys.exit(f"«{pid}» está por extraer (de {pieza(pid)['tomar_de']}): extráela primero en Pieza (AGENTS.md).")
    f = ficha(list(extra) + ["esqueleto"], plataformas)
    # Las de «siempre» que aún están por extraer (p. ej. «privacidad», que hoy trae «github») no detienen nada: se dicen al final.
    # «esqueleto» y «github» van al final: lo que escriben una vez mira qué piezas ya están (el Swift suma las actualizaciones,
    # AGENTS.md lista todas).
    orden = [x["id"] for x in f["piezas"] if x["id"] not in ("esqueleto", "github") and x["estado"] == "lista"] + ["esqueleto", "github"]
    os.makedirs(app, exist_ok=True)
    detalle = io.StringIO()
    with contextlib.redirect_stdout(detalle):
        iniciar(app, aid, nombre, plataformas, datos)
        if repo:
            ruta = os.path.join(app, "app.json")
            a = leer(ruta)
            a["repo"] = repo
            escribir(ruta, a)
        for pid in orden:
            agregar(pid, app)
        # La acción de ejemplo, ahora que bin/ejemplo.py existe (la generó «esqueleto»), y todo lo generado otra vez: lo que
        # depende de otro generado (la página, de docs/pagina.json) sale en esta pasada.
        ruta = os.path.join(app, "app.json")
        a = leer(ruta)
        a.setdefault("acciones", {})["ejemplo"] = ACCION_EJEMPLO
        escribir(ruta, a)
        armar_acciones(app, forzar=True)
        generar_todo(app)
    if os.environ.get("PIEZA_DETALLE"):
        print(detalle.getvalue())
    lock = candado(app)
    print(f"✓ {nombre} en {app}")
    print("  Piezas: " + ", ".join(f"{p} {lock['piezas'][p]['version']}" for p in orden))
    print("  Pruébala:  bash pruebas/correr.sh   ·   cd ui && python3 -m http.server 8765  (?bienvenida, ?idioma=en)")
    print("\nLE TOCA A LA IA (solo lo propio; lo demás ya está y se mantiene con pieza.py actualizar/generar):")
    print("  1. Lo marcado «La app:» en cada archivo:")
    for rel, n in pendientes_ia(app).items():
        print(f"     {rel} ({n})")
    print("  2. Lo propio: reemplazar el ejemplo (ui/app.js, bin/ejemplo.py, la acción «ejemplo» de app.json, ui/demo.json,"
          " pruebas/test_app.py e interfaz.mjs) por la app; cada texto nuevo con su inglés en ui/idiomas/en.json.")
    print("  3. app.json → empaquetado (descripcion, categoria) y los íconos (docs/favicon.svg"
          + (", escritorio/iconos/" if set(plataformas) & {"mac", "windows", "linux"} else "") + ").")
    print("  4. docs/pagina.json completo → pieza.py generar . pagina; después bash pruebas/correr.sh en verde.")
    print("\nLE TOCA A LA PERSONA:")
    for t in f["tareas_persona"]:
        print(f"  - {t}")


def _textos_en(app):
    """El archivo de inglés de la app, si existe (los tres formatos de hoy guardan las frases en «textos»)."""
    ruta = os.path.join(app, "ui", "idiomas", "en.json")
    return ruta if os.path.isfile(ruta) else None


#: Claves opcionales de config que no se suman a app.json (`agregar … --sin-config=tema`). Se guardan en piezas.json, por pieza.
_SIN_CONFIG = set()


def aplica(p, origen, plataformas_app, lock, agregando=None):
    """¿Va este archivo de la pieza en esta app? Su plataforma (`solo`) y, si lo dice, una de las piezas que lo usan (`solo_con`:
    el código de un host, p. ej. el lector de progreso en Rust solo con «host-tauri»)."""
    if not plataformas_app & set(p.get("solo", {}).get(origen, PLATAFORMAS)):
        return False
    con = p.get("solo_con", {}).get(origen)
    return not con or any(x in lock["piezas"] or x == agregando for x in con)


def copiar(pid, app, forzar=False, lock=None):
    p = pieza(pid)
    lock = lock or candado(app)
    antes = lock["piezas"].get(pid, {})
    copiados, saltados = {}, []
    plataformas_app = set((leer(os.path.join(app, "app.json"), {}) or {}).get("plataformas") or PLATAFORMAS)
    for origen, destino in p.get("archivos", {}).items():
        if not aplica(p, origen, plataformas_app, lock, pid):
            continue  # el archivo es de una plataforma (app.json → «plataformas») o de un host que esta app no tiene
        dst = destino_seguro(app, destino)
        anterior = antes.get("archivos", {}).get(destino)
        fuente = os.path.join(carpeta_de(pid), origen)
        if os.path.exists(dst) and not forzar:
            # Ya estaba sin estar anotado: si es igual al de la pieza, es el mismo (no lo cambió la app).
            igual = anterior is None and os.path.isfile(fuente) and huella(dst) == huella(fuente)
            cambiado_por_la_app = not igual and (anterior is None or huella(dst) != anterior)
            if cambiado_por_la_app:
                saltados.append(destino)
                copiados[destino] = anterior or ""
                continue
        if not ruta_relativa_ok(origen) or not ruta_relativa_ok(destino) or not destino.startswith(PREFIJOS_DESTINO) \
                or os.path.islink(fuente):
            sys.exit(f"{pid}: no copio {origen} → {destino} (ruta no permitida o enlace)")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(fuente, "rb") as f:
            escribir_atomico(dst, f.read(), os.stat(fuente).st_mode & 0o777)
        copiados[destino] = huella(dst)
    # Archivos que la versión anterior traía y esta ya no: nunca se borran solos (la app puede usarlos); se avisa y salen del candado.
    for viejo in antes.get("archivos", {}):
        if viejo not in copiados:
            print(f"    ! ya no es de la pieza: {viejo} (bórralo si la app no lo usa)")
    # Config: suma las claves que la pieza necesita a app.json. Una clave que ya existe no se pisa, pero si es una lista de
    # valores posibles se le suman los nuevos (si no, la app descartaría en silencio un valor que la pieza ahora acepta).
    # Una clave de `config_opcional` (p. ej. «tema»: solo si la app ofrece «Apariencia») se salta con --sin-config, y la
    # decisión queda en piezas.json para que `actualizar` no la vuelva a sumar.
    sin_config = sorted(set(antes.get("sin_config", [])) | (_SIN_CONFIG & set(p.get("config_opcional", {}))))
    ruta_app = os.path.join(app, "app.json")
    a = leer(ruta_app)
    if a is not None and p.get("config"):
        a.setdefault("config", {})
        for k, v in p["config"].items():
            if k in sin_config and k in p.get("config_opcional", {}):
                continue
            actual = a["config"].setdefault(k, v)
            if isinstance(actual, list) and isinstance(v, list):
                actual.extend(x for x in v if x not in actual)
        escribir(ruta_app, a)
    # Textos: suma al inglés de la app las frases que falten.
    en = _textos_en(app)
    if not en and p.get("textos") and os.path.isdir(os.path.join(app, "ui")):
        en = os.path.join(app, "ui", "idiomas", "en.json")
        os.makedirs(os.path.dirname(en), exist_ok=True)
        escribir(en, {"codigo": "en", "nombre": "English", "textos": {}})
    if en and p.get("textos"):
        d = leer(en, {})
        textos = d.setdefault("textos", {})
        nuevas = {k: v for k, v in p["textos"].items() if k not in textos}
        if nuevas:
            textos.update(nuevas)
            escribir(en, d)
    # Frases que solo hacen falta si la app usa algo opcional de la pieza (p. ej. fuerzaFrase de «cifrado»): solo si lo nombra.
    if en and p.get("textos_si_usa"):
        usados = _usa(app, set(p["textos_si_usa"]), set(copiados))
        d = leer(en, {})
        textos = d.setdefault("textos", {})
        nuevas = {k: v for nombre in sorted(usados) for k, v in p["textos_si_usa"][nombre].items() if k not in textos}
        if nuevas:
            textos.update(nuevas)
            escribir(en, d)
        for nombre in sorted(set(p["textos_si_usa"]) - usados):
            print(f"    · no sumé las frases de «{nombre}» a en.json (la app no lo usa; si lo usas después, vuelve a correr"
                  f" pieza.py actualizar {app} {pid} --forzar o cópialas de pieza.json → textos_si_usa)")
    # Secciones de app.json que la pieza necesita (p. ej. «catalogo»): se suma un esqueleto si falta, nunca se pisa.
    if a is not None and p.get("app_json"):
        faltan = {k: v for k, v in p["app_json"].items() if k not in a}
        if faltan:
            for k, v in faltan.items():
                a[k] = json.loads(json.dumps(v["esqueleto"]))
                print(f"    ! sumé «{k}» a app.json con un esqueleto: complétalo ({v['que']})")
            escribir(ruta_app, a)
    # Si algún archivo quedó sin actualizar (la app lo cambió), la versión anotada no avanza: estado sigue avisando.
    version = p["version"] if not saltados else antes.get("version", "0.0.0")
    lock["piezas"][pid] = {"version": version, "archivos": copiados,
                           **({"sin_config": sin_config} if sin_config else {}),
                           # Lo que la app aceptó: si una versión nueva pide más (otra pieza, permisos, red), no se aplica sola.
                           "ficha": {k: p.get(k, [] if k != "permisos" else {}) for k in ("requiere", "permisos", "red")},
                           # Lo generado (plantillas) se anota aparte: lo pone al día generar_todo, al final.
                           **{k: antes[k] for k in ("generados", "una_vez") if k in antes}}
    # Las acciones de la versión que quedó copiada (si la app no aceptó la nueva, siguen las de antes): de aquí sale acciones.json.
    acciones = p.get("acciones") if not saltados else antes.get("acciones", p.get("acciones"))
    if acciones:
        lock["piezas"][pid]["acciones"] = acciones
    if pid in _FUENTE:
        lock["piezas"][pid]["fuente"] = _FUENTE[pid]
    escribir(os.path.join(app, "piezas.json"), lock)
    return saltados


#: Dónde se busca si la app usa algo opcional de una pieza (textos_si_usa): su código propio, sin dependencias ni lo copiado.
_CODIGO_APP = ("ui", "bin", "motor", "escritorio/src", "app/Sources", "app/web", "movil/host")
_EXT_CODIGO = (".js", ".mjs", ".py", ".swift", ".html", ".kt")


def _usa(app, nombres, copiados):
    """Cuáles de `nombres` aparecen como palabra en el código de la app (fuera de los archivos que copió la pieza)."""
    encontrados = set()
    patron = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(nombres)) + r")\b")
    for raiz in _CODIGO_APP:
        for carpeta, dirs, archivos in os.walk(os.path.join(app, raiz)):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".build", "build", "dist") and not d.startswith(".")]
            for nombre in archivos:
                ruta = os.path.join(carpeta, nombre)
                if not nombre.endswith(_EXT_CODIGO) or os.path.relpath(ruta, app).replace(os.sep, "/") in copiados:
                    continue
                try:
                    with open(ruta, encoding="utf-8", errors="replace") as f:
                        encontrados |= set(patron.findall(f.read(2 * 1024 * 1024)))
                except OSError:
                    continue
                if encontrados == nombres:
                    return encontrados
    return encontrados


def choques(pid, app, lock):
    """Archivos de la pieza que ya existen en la app sin estar anotados y son distintos: [(destino, origen)]."""
    p = pieza(pid)
    plataformas_app = set((leer(os.path.join(app, "app.json"), {}) or {}).get("plataformas") or PLATAFORMAS)
    anotados = set(lock["piezas"].get(pid, {}).get("archivos", {}))
    r = []
    for origen, destino in p.get("archivos", {}).items():
        if not aplica(p, origen, plataformas_app, lock, pid) or destino in anotados:
            continue
        dst, fuente = origen_seguro(app, destino), os.path.join(carpeta_de(pid), origen)
        if os.path.isfile(dst) and os.path.isfile(fuente) and huella(dst) != huella(fuente):
            r.append((destino, origen))
    return r


#: Las piezas que leen acciones.json (el host genérico). Con alguna de ellas en la app, agregar/actualizar lo arman solos.
HOSTS = ("host-tauri", "host-mac", "host-escritorio")


def armar_acciones(app, forzar=False):
    """acciones.json en la raíz de la app: las acciones de las piezas instaladas (las de la versión copiada, guardadas en
    piezas.json) más las de app.json → «acciones» (las propias de la app, con su script en bin/). Lo lee el host genérico; va
    dentro de la app junto a app.json. Dos acciones con el mismo nombre o una que no pasa las reglas detienen todo."""
    lock = candado(app)
    ruta = os.path.join(app, "acciones.json")
    if not forzar and not os.path.exists(ruta) and not any(h in lock["piezas"] for h in HOSTS):
        return None
    todas_a, origen, errores = {}, {}, []
    fuentes, sin_saber, resueltas = [], [], False
    for pid, info in sorted(lock["piezas"].items()):
        acciones = info.get("acciones")
        if acciones is None and not info.get("fuente"):
            # Instalada antes de que piezas.json guardara las acciones: las de la base si es la misma versión; si no, las de esa
            # versión en el historial de git de Pieza. Se anotan en piezas.json para no buscarlas otra vez.
            base = todas().get(pid) or {}
            if base.get("version") == info.get("version"):
                acciones = base.get("acciones")
            elif base.get("acciones"):
                acciones = acciones_de_version(pid, info.get("version"))
                if acciones is None:
                    sin_saber.append(f"{pid} {info.get('version')}")
            if acciones:
                info["acciones"] = acciones
                resueltas = True
        fuentes.append((pid, acciones or {}))
    if sin_saber:
        # Sin sus acciones, acciones.json saldría sin ellas (y la app perdería, p. ej., probarIA sin avisar): mejor no armarlo.
        sys.exit("No armé acciones.json: piezas.json es de antes de que guardara las acciones y no encontré en el historial de\n"
                 f"Pieza las de: {', '.join(sin_saber)}. Ponlas al día primero:\n"
                 f"  python3 {os.path.relpath(__file__)} actualizar {app} {' '.join(x.split()[0] for x in sin_saber)}\n"
                 "(y vuelve a correr lo que estabas haciendo, o pieza.py acciones <app>).")
    if resueltas:
        escribir(os.path.join(app, "piezas.json"), lock)
    a = leer(os.path.join(app, "app.json"), {}) or {}
    propias = a.get("acciones") or {}
    if not isinstance(propias, dict):
        sys.exit("app.json: «acciones» es {nombre: acción}.")
    # «No adoptar» una acción de una pieza que la app no usa (app.json → "sin_acciones": ["listaIA"]): no se carga en el host.
    sin = a.get("sin_acciones") or []
    if not isinstance(sin, list) or not all(isinstance(x, str) and NOMBRE_ACCION.match(x) for x in sin):
        sys.exit("app.json: «sin_acciones» es una lista de nombres de acciones.")
    de_piezas = {n for _, acc in fuentes for n in acc}
    for x in sorted(set(sin) - de_piezas):
        print(f"    ! app.json → sin_acciones: ninguna pieza instalada declara «{x}» (bórrala de la lista)")
    for x in sorted(set(sin) & set(propias)):
        errores.append(f"app: «{x}» está en «acciones» y en «sin_acciones»")
    scripts_app = set(os.listdir(os.path.join(app, "bin"))) if os.path.isdir(os.path.join(app, "bin")) else set()
    for pid, acciones in fuentes + [("app", propias)]:
        for nombre, accion in acciones.items():
            if pid != "app" and nombre in sin:
                continue
            e = errores_accion(nombre, accion, scripts_app if pid == "app" else None)
            if pid == "app" and not e and not accion.get("rust") and accion["script"] not in scripts_app:
                e.append(f"acción «{nombre}»: no está bin/{accion['script']}")
            if nombre in todas_a:
                e.append(f"acción «{nombre}»: la declaran {origen[nombre]} y {pid}")
            errores += [f"{pid}: {x}" for x in e]
            if not e:
                todas_a[nombre] = {k: v for k, v in accion.items() if k != "scriptDeLaApp"}
                origen[nombre] = pid
    if errores:
        sys.exit("No armé acciones.json:\n  " + "\n  ".join(errores))
    escribir(ruta, {"formato": 1, "acciones": {k: {**todas_a[k], "pieza": origen[k]} for k in sorted(todas_a)}})
    _lista_blanca(app, ["!/acciones.json"])
    return ruta


def acciones_de_version(pid, version):
    """Las acciones del pieza.json de `pid` en esa versión, del historial de git de Pieza (si las piezas están en un checkout).
    None si no hay git o esa versión no aparece."""
    if not isinstance(version, str) or not VERSION.match(version) or not ID.match(pid):
        return None
    raiz, ruta = os.path.dirname(os.path.abspath(PIEZAS)), f"{os.path.basename(os.path.abspath(PIEZAS))}/{pid}/pieza.json"
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        r = subprocess.run(["git", "-C", raiz, "log", "--format=%H", "--", ruta], capture_output=True, text=True, timeout=30, env=entorno)
        for h in r.stdout.split()[:300]:
            if not re.fullmatch(r"[0-9a-f]{40}", h):
                continue
            x = subprocess.run(["git", "-C", raiz, "show", f"{h}:{ruta}"], capture_output=True, text=True, timeout=30, env=entorno)
            try:
                d = json.loads(x.stdout)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("version") == version:
                acc = d.get("acciones") or {}
                return acc if isinstance(acc, dict) else None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _lista_blanca(app, entradas):
    """Muchas apps tienen un .gitignore de lista blanca («/*» y luego «!…»): ahí un archivo nuevo de la raíz quedaría fuera."""
    gi = os.path.join(app, ".gitignore")
    if not os.path.isfile(gi):
        return
    lineas = [l.strip() for l in open(gi, encoding="utf-8")]
    if "/*" in lineas or "*" in lineas:
        faltan = [x for x in entradas if x not in lineas and x.replace("/", "", 1) not in lineas]
        if faltan:
            with open(gi, "a", encoding="utf-8") as f:
                f.write("\n# Pieza: archivos de la raíz que usa la app\n" + "\n".join(faltan) + "\n")
            print(f"~ {gi}: agregué {', '.join(faltan)} (es una lista blanca)")


def anotar_sin_config(app, lock, pids):
    """`--sin-config` sobre piezas ya instaladas: anota la decisión en piezas.json (`sin_config`) y quita la clave de app.json
    si sigue como la dejó la pieza (si la app la cambió, solo avisa). `actualizar` la respeta desde ahí."""
    if not _SIN_CONFIG:
        return
    ruta_app = os.path.join(app, "app.json")
    a = leer(ruta_app)
    cambio_app = cambio_lock = False
    for pid in pids:
        info = lock["piezas"].get(pid)
        if not info or info.get("fuente"):
            continue
        p = todas().get(pid) or {}
        nuevas = (_SIN_CONFIG & set(p.get("config_opcional", {}))) - set(info.get("sin_config", []))
        if not nuevas:
            continue
        info["sin_config"] = sorted(set(info.get("sin_config", [])) | nuevas)
        cambio_lock = True
        for k in sorted(nuevas):
            config = (a or {}).get("config") or {}
            if k in config and config[k] == p.get("config", {}).get(k):
                del config[k]
                cambio_app = True
                print(f"    · {pid}: quité «{k}» de app.json y anoté --sin-config={k} en piezas.json")
            elif k in config:
                print(f"    · {pid}: anoté --sin-config={k}; «{k}» sigue en app.json porque la app la cambió (bórrala si no la usas)")
            else:
                print(f"    · {pid}: anoté --sin-config={k} en piezas.json")
    if cambio_app:
        escribir(ruta_app, a)
    if cambio_lock:
        escribir(os.path.join(app, "piezas.json"), lock)


def avisar_sin_config_desconocida(pids):
    """Una clave de --sin-config que ninguna de estas piezas declara opcional no hace nada: mejor decirlo."""
    opcionales = set()
    for pid in pids:
        opcionales |= set((todas().get(pid) or {}).get("config_opcional", {}))
    for k in sorted(_SIN_CONFIG - opcionales):
        print(f"! --sin-config={k}: ninguna de estas piezas tiene «{k}» como clave opcional; no hice nada con ella")


def agregar(pid, app, sin_revisar=False, forzar=False):
    if not ID.match(pid):
        sys.exit("El id de una pieza va en minúsculas, números y guiones.")
    if not os.path.isfile(os.path.join(app, "app.json")):
        sys.exit("La app no tiene app.json. Créalo con: pieza.py iniciar <app> <id> <Nombre>")
    if not os.path.isfile(os.path.join(PIEZAS, pid, "pieza.json")):
        # No es oficial: se busca en el catálogo de la comunidad. Solo lo revisado se instala sin preguntar.
        import comunidad
        _EXTRA[pid], _FUENTE[pid] = comunidad.descargar(pid, sin_revisar=sin_revisar)
    lock = candado(app)
    for p in con_requisitos(pid):
        if pieza(p).get("estado") == "planeada":
            sys.exit(f"«{p}» aún no está extraída. Se toma de: {pieza(p)['tomar_de']}. Extráela primero (ver AGENTS.md).")
    # Antes de copiar nada: un archivo que ya existe y es distinto dejaría piezas.json a medias (versión 0.0.0, huella vacía).
    malos = [(p, d, o) for p in con_requisitos(pid) if p not in lock["piezas"] for d, o in choques(p, app, lock)]
    if malos and not forzar:
        lineas = "\n".join(f"  {d}  (de «{p}»; compara: diff {os.path.join(app, d)} {os.path.join(carpeta_de(p), o)})"
                           for p, d, o in malos)
        sys.exit(f"No agregué «{pid}»: estos archivos ya existen en la app y son distintos de los de la pieza:\n{lineas}\n"
                 f"- Si la pieza salió de ese archivo (o quieres el de la pieza): pieza.py agregar {pid} {app} --forzar\n"
                 f"  (lo reemplaza: guarda antes tus cambios en git y pasa a la app lo que la pieza no traiga).\n"
                 f"- Si es otro módulo de la app que se llama igual: renómbralo (y sus import) y vuelve a agregar la pieza.")
    for p in con_requisitos(pid):
        if p in lock["piezas"]:
            print(f"· {p} ya estaba")
            anotar_sin_config(app, lock, [p])
            continue
        saltados = copiar(p, app, forzar=forzar and any(x == p for x, _, _ in malos), lock=lock)
        print(f"+ {p} {pieza(p)['version']}")
        for k, cuando in pieza(p).get("config_opcional", {}).items():
            if k in _SIN_CONFIG:
                print(f"    · no sumé «{k}» a app.json (--sin-config)")
            else:
                print(f"    · sumé «{k}» a app.json: {cuando} Si no, vuelve a agregarla con --sin-config={k}.")
        for s in saltados:
            print(f"    ! {s} ya existía en la app y no lo pisé. Compara con: pieza.py diferencias {app} {p}")
    avisar_sin_config_desconocida(con_requisitos(pid))
    # Una pieza ya instalada puede traer código que va solo con la que se acaba de agregar (`solo_con`: el lector de progreso
    # en Rust llega cuando llega «host-tauri»): se copia ahora, sin tocar lo que la app cambió.
    nuevas = set(con_requisitos(pid))
    for otra in sorted(lock["piezas"]):
        if otra in nuevas or not os.path.isfile(os.path.join(carpeta_de(otra), "pieza.json")):
            continue
        con = (pieza(otra).get("solo_con") or {}).values()
        if any(set(x) & nuevas for x in con):
            copiar(otra, app, lock=lock)
            print(f"~ {otra}: lo que va con {', '.join(sorted(set().union(*map(set, con)) & nuevas))}")
    if armar_acciones(app):
        print("~ acciones.json (lo lee el host: va dentro de la app junto a app.json)")
    # Lo que generan las piezas (plantillas) se llena con todas las piezas ya instaladas: una pieza nueva puede cambiar lo de
    # otra (p. ej. Package.swift suma el target de «catalogo»).
    generar_todo(app, forzar=forzar)


def estado_app(app):
    """Por pieza instalada: versión actual y nueva, cambios pendientes, el tipo más fuerte, si es de seguridad, qué archivos
    cambió la app y si se puede actualizar sola."""
    lock = candado(app)
    nuevas = {pid: (todas().get(pid) or {}).get("version", info["version"]) for pid, info in lock["piezas"].items()}
    salida = []
    for pid, info in sorted(lock["piezas"].items()):
        if info.get("fuente"):  # de la comunidad: nunca se compara (ni se reemplaza) con una oficial del mismo id
            nuevas[pid] = info["version"]
        p = {} if info.get("fuente") else (todas().get(pid) or {})
        nueva = nuevas[pid]
        pendientes = cambios_entre(p, info["version"], nueva) if p else []
        tipo = max((c["tipo"] for c in pendientes), key=lambda t: TIPOS_CAMBIO[t], default=None)
        cambiados, faltan = [], []
        for destino, h in info["archivos"].items():
            ruta = os.path.join(app, destino)
            if not os.path.exists(ruta):
                faltan.append(destino)
            elif huella(ruta) != h:
                cambiados.append(destino)
        con_esta = {**{k: v["version"] for k, v in lock["piezas"].items()}, pid: nueva}
        choques = [x for x in incompatibles(con_esta) if pid in (x[0], x[1])]
        pide_mas = bool(p) and bool(pendientes) and info.get("ficha") != {k: p.get(k, [] if k != "permisos" else {})
                                                                     for k in ("requiere", "permisos", "red")}
        # Lo generado: lo que la app cambió (la pieza ya no lo toca) y lo de .github/ y .claude/ que cambiaría (nunca va solo).
        gen_app = [d for d, h in info.get("generados", {}).items()
                   if h == "" or (os.path.isfile(os.path.join(app, d)) and huella(os.path.join(app, d)) != h)]
        github = pendientes_github(pid, app, lock) if p else []
        salida.append({"pieza": pid, "actual": info["version"], "generados_por_la_app": gen_app, "github": github, "comunidad": bool(info.get("fuente")), "pide_mas": pide_mas, "nueva": nueva, "al_dia": semver(info["version"]) >= semver(nueva),
                       "tipo": tipo, "seguridad": any(c.get("seguridad") for c in pendientes), "cambios": pendientes,
                       "cambiados_por_la_app": cambiados, "faltan": faltan, "choques": choques, "juntas": [],
                       "automatico": bool(pendientes) and tipo != "rompe" and not cambiados and not faltan and not pide_mas
                                     and not github})
    # Un choque que se arregla actualizando las dos en la misma pasada (componentes 0.2 necesita tema 0.2) no frena nada: se
    # cuentan las versiones nuevas de todo lo que se va a actualizar. Lo automático, solo entre lo que también es automático.
    versiones = {k: v["version"] for k, v in lock["piezas"].items()}
    auto, _ = plan_juntas(versiones, nuevas, [x["pieza"] for x in salida if x["automatico"]])
    todas_van, _ = plan_juntas(versiones, nuevas, [x["pieza"] for x in salida if not x["al_dia"]])
    for x in salida:
        x["automatico"] = x["pieza"] in auto
        if x["choques"] and x["pieza"] in todas_van:
            x["juntas"] = sorted({p for a, b, _r, _t in x["choques"] for p in (a, b)} - {x["pieza"]})
    return salida


def estado(app, como_json=False):
    e = estado_app(app)
    if como_json:
        print(json.dumps(e, ensure_ascii=False, indent=1))
        return
    if not e:
        print("Esta app aún no tiene piezas.")
    for x in e:
        if x["al_dia"]:
            marca = "al día"
        else:
            marca = f"hay {x['nueva']}: {x['tipo']}" + (" · SEGURIDAD" if x["seguridad"] else "") + \
                    (" · se actualiza sola" if x["automatico"] else " · a mano") + \
                    (" · pide más (otra pieza, permisos o red)" if x.get("pide_mas") else "")
        print(f"{x['pieza']} {x['actual']} ({marca})")
        for d in x["cambiados_por_la_app"]:
            print(f"    ~ la app cambió {d}")
        for d in x["faltan"]:
            print(f"    ✗ falta {d}")
        for d in x.get("generados_por_la_app", []):
            print(f"    ~ {d} es de la app (la pieza lo generó y la app lo cambió: ya no lo toca)")
        for d in x.get("github", []):
            print(f"    ! {d} cambia con la versión de la base: va a mano (pieza.py generar {app} {x['pieza']})")
        for pid, req, rango, tiene in x["choques"]:
            print(f"    ! {pid} necesita {req} {rango} (hay {tiene})" +
                  (f": se actualizan juntas (pieza.py actualizar {app} {' '.join(sorted([x['pieza']] + x['juntas']))})"
                   if x["juntas"] else ""))


def actualizar(app, solas=None, forzar=False, automatico=False):
    """Trae las versiones nuevas (de todas o de `solas`). Va en orden de dependencias (lo requerido primero) y revisa los
    requisitos con las versiones que quedan después de esta pasada: si `componentes` nueva necesita `tema` nueva, se actualizan
    las dos (aunque se pida solo `componentes`), una sola vez."""
    lock = candado(app)
    solas = [solas] if isinstance(solas, str) else list(solas or [])
    for pid in solas:
        if pid not in lock["piezas"]:
            sys.exit(f"La app no tiene la pieza «{pid}».")
    anotar_sin_config(app, lock, solas or sorted(lock["piezas"]))
    if _SIN_CONFIG:
        avisar_sin_config_desconocida(solas or sorted(lock["piezas"]))
    e = {x["pieza"]: x for x in estado_app(app)}
    nuevas = {pid: x["nueva"] for pid, x in e.items()}
    candidatas = [p for p in (solas or sorted(lock["piezas"]))
                  if (forzar or not e[p]["al_dia"]) and (not automatico or e[p]["automatico"])]
    # Lo que una pieza pedida necesita en su versión nueva también va (si no, se negaría por un choque que esta pasada arregla).
    agregadas = {}
    while not automatico:
        mas = {b: a for p in candidatas for a, b, _r, _t in e[p]["choques"]
               if a == p and b in e and b not in candidatas and not e[b]["al_dia"]}
        if not mas:
            break
        for b, a in sorted(mas.items()):
            candidatas.append(b)
            agregadas[b] = a
    versiones = {k: v["version"] for k, v in lock["piezas"].items()}
    van, fuera = (set(candidatas), {}) if forzar else plan_juntas(versiones, nuevas, candidatas)
    for pid in sorted(fuera):
        print(f"! no actualicé {pid}: " + "; ".join(f"{a} necesita {b} {c} (hay {d})" for a, b, c, d in fuera[pid]))
    requisitos = {pid: (lock["piezas"][pid].get("ficha") or {}).get("requiere", []) for pid in van}
    for pid in orden_dependencias(van, requisitos):
        x = e[pid]
        for r in con_requisitos(pid):  # lo que la versión nueva requiere y la app aún no tiene
            if r != pid and r not in lock["piezas"]:
                if pieza(r).get("estado") == "planeada":
                    sys.exit(f"{pid} ahora requiere «{r}», que aún no está extraída.")
                copiar(r, app, lock=lock)
                print(f"+ {r} {pieza(r)['version']} (la requiere {pid})")
        saltados = copiar(pid, app, forzar=forzar, lock=lock)
        print(f"↑ {pid} {x['actual']} → {pieza(pid)['version']}" + (" (seguridad)" if x["seguridad"] else "")
              + (f" (la necesita {agregadas[pid]})" if pid in agregadas else ""))
        for s in saltados:
            print(f"    ! no actualicé {s}: la app lo cambió. Revisa: pieza.py diferencias {app} {pid}")
    # Si un archivo cambiado por la app dejó una pieza en su versión de antes, lo que dependía de ella puede chocar: se avisa.
    for a, b, rango, tiene in incompatibles({k: v["version"] for k, v in lock["piezas"].items()}):
        if a in van or b in van:
            print(f"! {a} necesita {b} {rango} (quedó {tiene}): revisa pieza.py diferencias {app} {b}")
    if armar_acciones(app):
        print("~ acciones.json al día")
    generar_todo(app, forzar=forzar, automatico=automatico)


def aviso(app):
    """Markdown con lo que no se puede actualizar solo, para un issue."""
    manual = [x for x in estado_app(app) if (not x["al_dia"] and not x["automatico"]) or x.get("github")]
    if not manual:
        return ""
    l = ["Hay versiones nuevas de piezas que **no se pueden actualizar solas**. Esto es lo que cambió y qué hacer.", ""]
    for x in manual:
        l.append(f"### {x['pieza']} {x['actual']} → {x['nueva']}" + (" · seguridad" if x["seguridad"] else "")
                 if not x["al_dia"] else f"### {x['pieza']} {x['actual']}")
        if x.get("github"):
            l.append(f"- Cambia lo que genera en {', '.join(f'`{d}`' for d in x['github'])}: un workflow o unos ajustes de la IA "
                     f"(pueden traer hooks) los revisa una persona (y el token de Actions no puede escribir workflows). "
                     f"Míralo y aplícalo con "
                     f"`pieza.py {'actualizar' if not x['al_dia'] else 'generar'} . {x['pieza']}`.")
        for c in x["cambios"]:
            l.append(f"- **{c['version']}** ({c['tipo']}{', seguridad' if c.get('seguridad') else ''}): {c['resumen']}")
            pasos = c.get("migrar", [])
            for paso in [pasos] if isinstance(pasos, str) else pasos:  # una pieza de antes con un texto: un solo paso
                l.append(f"  - {paso}")
        if x["cambiados_por_la_app"]:
            l.append(f"- Esta app cambió {', '.join(f'`{d}`' for d in x['cambiados_por_la_app'])}: compara con "
                     f"`pieza.py diferencias . {x['pieza']}`, pasa tus cambios y luego `pieza.py actualizar . {x['pieza']} --forzar`. "
                     "Si tu cambio sirve para todas las apps, propónlo en pieza-app/pieza.")
        for pid, req, rango, tiene in x["choques"]:
            if x["juntas"]:
                juntas = " ".join(sorted([x["pieza"]] + x["juntas"]))
                l.append(f"- `{pid}` necesita `{req}` {rango} (hay {tiene}): se actualizan juntas con "
                         f"`pieza.py actualizar . {juntas}` (o `pieza.py actualizar .`, que va en orden de dependencias).")
            else:
                l.append(f"- `{pid}` necesita `{req}` {rango} (hay {tiene}) y todavía no hay una versión de `{req}` que sirva.")
        l.append("")
    l.append("Lo abrió «Pieza al día» (`.github/workflows/pieza-al-dia.yml`). Se cierra solo cuando todo queda al día.")
    return "\n".join(l)


def diferencias(app, pid):
    if not ID.match(pid):
        sys.exit("El id de una pieza va en minúsculas, números y guiones.")
    fuente = candado(app)["piezas"].get(pid, {}).get("fuente")
    if fuente:  # de la comunidad: se compara con el commit que se instaló, verificado con sus huellas
        import comunidad
        _EXTRA[pid], _ = comunidad.descargar(pid, sin_revisar=fuente.get("revision") != "revisada")
    lock = candado(app)
    if pid in lock["piezas"]:
        for destino, texto, una in generados_de(pid, app, lock):
            ruta = os.path.join(app, destino)
            if texto is None or una or not os.path.isfile(ruta):
                continue
            local = open(ruta, encoding="utf-8").read().splitlines(keepends=True)
            sys.stdout.writelines(difflib.unified_diff(texto.splitlines(keepends=True), local, f"generado/{destino}", f"app/{destino}"))
    for origen, destino in pieza(pid).get("archivos", {}).items():
        base = open(os.path.join(carpeta_de(pid), origen), encoding="utf-8").read().splitlines(keepends=True)
        ruta = os.path.join(app, destino)
        local = open(ruta, encoding="utf-8").read().splitlines(keepends=True) if os.path.exists(ruta) else []
        sys.stdout.writelines(difflib.unified_diff(base, local, f"base/{origen}", f"app/{destino}"))


def ficha(ids, plataformas=PLATAFORMAS):
    """Todo lo que implica una app con estas piezas, las de «siempre» para esas plataformas y sus requisitos, sin repetir."""
    elegidas = list(ids)
    for pid, p in todas().items():
        if p.get("recomendar", {}).get("siempre") and pid not in elegidas and set(p.get("plataformas", PLATAFORMAS)) & set(plataformas):
            elegidas.append(pid)
    orden = []
    for pid in elegidas:
        for x in con_requisitos(pid):
            if x not in orden:
                orden.append(x)
    f = {"piezas": [], "pantallas": [], "config": {}, "permisos": {k: [] for k in PLATAFORMAS}, "red": [], "acciones": [],
         "tareas_persona": [], "plataformas": list(plataformas), "faltan_en": [], "por_extraer": []}
    for pid in orden:
        p = pieza(pid)
        motivo = "pedida" if pid in ids else ("siempre" if p.get("recomendar", {}).get("siempre") else "requisito")
        f["piezas"].append({"id": pid, "nombre": p.get("nombre", pid), "version": p["version"], "estado": p.get("estado", "lista"),
                            "motivo": motivo})
        if p.get("estado") == "planeada":
            f["por_extraer"].append({"id": pid, "tomar_de": p["tomar_de"]})
        f["pantallas"] += [{**x, "pieza": pid} for x in p.get("pantallas", [])]
        for k, v in p.get("config", {}).items():
            f["config"].setdefault(k, v)
        for plat, lista in p.get("permisos", {}).items():
            for x in lista:
                if x["clave"] not in [y["clave"] for y in f["permisos"][plat]]:
                    f["permisos"][plat].append({**x, "pieza": pid})
        f["red"] += [d for d in p.get("red", []) if d not in f["red"]]
        if p.get("red_nota"):
            f.setdefault("red_notas", []).append({"pieza": pid, "nota": p["red_nota"]})
        f["acciones"] += [{"accion": k, "responde": v.get("responde"), "pieza": pid} for k, v in p.get("acciones", {}).items()]
        f["tareas_persona"] += [t for t in p.get("tareas_persona", []) if t not in f["tareas_persona"]]
        if not pid.startswith("host-"):
            falta = [x for x in plataformas if x not in p.get("plataformas", PLATAFORMAS)]
            if falta:
                f["faltan_en"].append({"pieza": pid, "plataformas": falta})
    # Bienvenida primero (y su paso de idioma antes que todo), después la app, Ajustes y la web.
    lugar = {"Bienvenida": 0, "Ajustes": 2, "Web": 3}
    f["pantallas"].sort(key=lambda x: (lugar.get(x["donde"], 1), x["nombre"] != "Idioma", x["nombre"] == "Listo"))
    return f


def ficha_texto(f):
    l = ["PLATAFORMAS", "  " + ", ".join(f["plataformas"])]
    l += ["PIEZAS"] + [f"  {x['id']} {x['version']} ({x['estado']}, {x['motivo']})" for x in f["piezas"]]
    if f["por_extraer"]:
        l += ["POR EXTRAER ANTES"] + [f"  {x['id']}: tomar de {x['tomar_de']}" for x in f["por_extraer"]]
    if f["faltan_en"]:
        l += ["NO DISPONIBLES EN"] + [f"  {x['pieza']}: {', '.join(x['plataformas'])}" for x in f["faltan_en"]]
    l += ["PANTALLAS"] + [f"  {x['donde']} → {x['nombre']}: {x['que']}" for x in f["pantallas"]]
    l += ["CONFIG (app.json)"] + [f"  {k}: {v}" for k, v in f["config"].items()]
    l += ["PERMISOS"]
    for plat, lista in ((k, v) for k, v in f["permisos"].items() if k in f["plataformas"]):
        l += [f"  {plat}: " + ("ninguno" if not lista else "; ".join(f"{x['clave']} ({x['por']})" for x in lista))]
    l += ["RED (dominios a los que sale)", "  " + (", ".join(f["red"]) or "ninguno")]
    l += [f"  {x['pieza']}: {x['nota']}" for x in f.get("red_notas", [])]
    l += ["ACCIONES"] + [f"  {x['accion']} → {x['responde']}" for x in f["acciones"]]
    if f["tareas_persona"]:
        l += ["SOLO LA PERSONA"] + [f"  {t}" for t in f["tareas_persona"]]
    return "\n".join(l)



# ── Configurar el repo de GitHub de una app (lo que antes se hacía a mano) ──────────────────────────────────────────────────────

#: Las etiquetas que usan las plantillas de issues y CONTRIBUTING.md (nombre, color, descripción).
ETIQUETAS = [("good first issue", "7057ff", "Para empezar a aportar / Good for newcomers"),
             ("idea", "a2eeef", "Algo que te gustaría que la app hiciera / Feature idea"),
             ("error", "d73a4a", "Algo falla / Something's broken"),
             ("probar", "0e8a16", "Probarla en un equipo de verdad / Test it on a real device")]
REGLAS_RAMA = {"name": "Rama principal", "target": "branch", "enforcement": "active",
               "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
               "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}


def comandos_repo(app):
    """[(qué hace, comando como lista, entrada o None)] para dejar el repo de la app listo para la comunidad."""
    a = leer(os.path.join(app, "app.json"), {}) or {}
    repo = a.get("repo")
    if not (isinstance(repo, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}", repo)):
        sys.exit("app.json no tiene «repo» («dueño/repo», p. ej. \"ana-app/ana\"): agrégalo primero.")
    temas = ["hecho-con-pieza"] + [t for t in (a.get("github") or {}).get("topics", [])
                                    if isinstance(t, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", t)]
    c = [("Discussions y los topics (hecho-con-pieza: la app aparece en la página de Pieza)",
          ["gh", "repo", "edit", repo, "--enable-discussions"] + [x for t in temas for x in ("--add-topic", t)], None),
         ("Reporte privado de fallas de seguridad (lo usa SECURITY.md)",
          ["gh", "api", "-X", "PUT", f"repos/{repo}/private-vulnerability-reporting"], None),
         ("Las pruebas de quien aporta desde un fork esperan la aprobación de quien mantiene",
          ["gh", "api", "-X", "PUT", f"repos/{repo}/actions/permissions/fork-pr-contributor-approval",
           "-f", "approval_policy=all_external_contributors"], None),
         ("Los workflows leen por defecto y pueden abrir PRs (lo necesita «Pieza al día»)",
          ["gh", "api", "-X", "PUT", f"repos/{repo}/actions/permissions/workflow",
           "-f", "default_workflow_permissions=read", "-F", "can_approve_pull_request_reviews=true"], None),
         ("La rama principal no se borra ni se reescribe (ruleset «Rama principal»)",
          ["gh", "api", "-X", "POST", f"repos/{repo}/rulesets", "--input", "-"], json.dumps(REGLAS_RAMA, ensure_ascii=False))]
    for nombre, color, desc in ETIQUETAS:
        c.append((f"Etiqueta «{nombre}»", ["gh", "label", "create", nombre, "--color", color, "--description", desc,
                                         "--force", "-R", repo], None))
    return repo, c


def repo_configurar(app, aplicar=False):
    import shlex
    repo, c = comandos_repo(app)
    if not aplicar:
        print(f"# Configuración de {repo} (nada se cambió: con --aplicar los corre, con gh y permisos de admin del repo)")
        for que, cmd, entrada in c:
            print(f"\n# {que}")
            linea = " ".join(shlex.quote(x) for x in cmd)
            print(f"{linea} <<'JSON'\n{entrada}\nJSON" if entrada else linea)
        return 0
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    malos = 0
    for que, cmd, entrada in c:
        if any(x.endswith("/rulesets") for x in cmd):
            # Una sola vez: si ya hay un ruleset con ese nombre, no se crea otro.
            r = subprocess.run(["gh", "api", f"repos/{repo}/rulesets"], capture_output=True, text=True, timeout=60, env=entorno)
            try:
                if any(x.get("name") == REGLAS_RAMA["name"] for x in json.loads(r.stdout or "[]")):
                    print(f"· {que}: ya estaba")
                    continue
            except ValueError:
                pass
        r = subprocess.run(cmd, input=entrada, capture_output=True, text=True, timeout=60, env=entorno)
        print(f"{'✓' if r.returncode == 0 else '✗'} {que}" + ("" if r.returncode == 0 else f"\n    {(r.stderr or r.stdout).strip()[:300]}"))
        malos += r.returncode != 0
    return 1 if malos else 0


# ── Skills (los flujos) para otras IA ───────────────────────────────────────────────────────────────────────────────────────

SKILLS = os.path.join(BASE, "skills")
DESTINOS_SKILLS = {"codex": os.path.join("~", ".agents", "skills"), "claude": os.path.join("~", ".claude", "skills")}
LOCAL = "## Configuración local"


def version_flujo(texto):
    m = re.search(r"^Versión del flujo: (\d+)$", texto, re.M)
    return int(m.group(1)) if m else 0


def _destino_skills(donde):
    if donde not in DESTINOS_SKILLS:
        sys.exit("Elige dónde: codex o claude. (Gemini CLI: gemini extensions install https://github.com/pieza-app/pieza)")
    return os.path.expanduser(os.environ.get("PIEZA_SKILLS_DESTINO") or DESTINOS_SKILLS[donde])


def skills_estado(donde):
    destino = _destino_skills(donde)
    for nombre in sorted(os.listdir(SKILLS)):
        nueva = version_flujo(open(os.path.join(SKILLS, nombre, "SKILL.md"), encoding="utf-8").read())
        ruta = os.path.join(destino, nombre, "SKILL.md")
        if not os.path.isfile(ruta):
            print(f"{nombre}: no instalada (Pieza trae la versión {nueva})")
            continue
        tiene = version_flujo(open(ruta, encoding="utf-8").read())
        print(f"{nombre}: versión {tiene}" + (" (al día)" if tiene >= nueva else f" → hay {nueva}: pieza.py skills instalar {donde}"))


def skills_instalar(donde):
    """Copia cada skill; si ya había una copia con «Configuración local» (lo propio de quien la usa), la conserva al final."""
    destino = _destino_skills(donde)
    for nombre in sorted(os.listdir(SKILLS)):
        texto = open(os.path.join(SKILLS, nombre, "SKILL.md"), encoding="utf-8").read().rstrip("\n") + "\n"
        ruta = os.path.join(destino, nombre, "SKILL.md")
        local = ""
        if os.path.isfile(ruta):
            anterior = open(ruta, encoding="utf-8").read()
            if LOCAL in anterior:
                local = "\n" + anterior[anterior.index(LOCAL):].rstrip("\n") + "\n"
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        escribir_atomico(ruta, (texto + local).encode("utf-8"))
        print(f"✓ {nombre} versión {version_flujo(texto)}" + (" (con tu configuración local)" if local else "") + f" → {ruta}")


def main(a):
    if not a or a[0] in ("-h", "--help", "ayuda"):
        print(__doc__)
        return 0
    orden, resto = a[0], a[1:]
    forzar = "--forzar" in resto
    resto = [x for x in resto if x != "--forzar"]
    como_json = "--json" in resto
    plats = PLATAFORMAS
    if "--plataformas" in resto:
        i = resto.index("--plataformas")
        plats = tuple(x for x in resto[i + 1].split(",") if x in PLATAFORMAS) if i + 1 < len(resto) else PLATAFORMAS
        resto = resto[:i] + resto[i + 2:]
    resto = [x for x in resto if x != "--json"]
    if orden == "listar":
        for pid, p in todas().items():
            req = f"  (requiere {', '.join(p['requiere'])})" if p.get("requiere") else ""
            est = "" if p.get("estado", "lista") == "lista" else " [planeada]"
            print(f"{pid:18} {p['version']:8} {p['descripcion']}{req}{est}")
    elif orden == "catalogo":
        ps = todas()
        if como_json:
            print(json.dumps(ps, ensure_ascii=False, indent=1))
        else:
            for cat in sorted(CATEGORIAS):
                grupo = {k: v for k, v in ps.items() if v.get("categoria") == cat}
                if grupo:
                    print(f"[{cat}]")
                    for pid, p in grupo.items():
                        siempre = " ★ siempre" if p.get("recomendar", {}).get("siempre") else ""
                        print(f"  {pid} ({p.get('estado', 'lista')}){siempre}: {p['descripcion']}\n      cuándo: {p['recomendar']['cuando']}")
    elif orden == "ficha" and resto:
        f = ficha(resto, plats or PLATAFORMAS)
        print(json.dumps(f, ensure_ascii=False, indent=1) if como_json else ficha_texto(f))
    elif orden == "revisar":
        return revisar()
    elif orden == "skills" and len(resto) == 2 and resto[0] in ("estado", "instalar"):
        (skills_estado if resto[0] == "estado" else skills_instalar)(resto[1])
    elif orden == "crear" and resto:
        op, libres, i = {}, [], 0
        while i < len(resto):
            if resto[i] in ("--id", "--nombre", "--piezas", "--repo", "--datos") and i + 1 < len(resto):
                op[resto[i][2:]] = resto[i + 1]
                i += 2
            elif resto[i].startswith("--") and "=" in resto[i]:
                k, v = resto[i][2:].split("=", 1)
                op[k] = v
                i += 1
            else:
                libres.append(resto[i])
                i += 1
        if len(libres) != 1 or not op.get("id") or not op.get("nombre"):
            print(__doc__)
            return 2
        plats_crear = op["plataformas"].split(",") if op.get("plataformas") else (list(plats) if plats != PLATAFORMAS else None)
        crear(os.path.abspath(libres[0]), op["id"], op["nombre"], plats_crear,
              [x for x in op.get("piezas", "").split(",") if x], op.get("repo"), op.get("datos", "sistema"))
    elif orden == "iniciar" and len([x for x in resto if not x.startswith("--")]) == 3:
        plats = next((x.split("=", 1)[1].split(",") for x in resto if x.startswith("--plataformas=")), None)
        datos = next((x.split("=", 1)[1] for x in resto if x.startswith("--datos=")), "sistema")
        iniciar(*[x for x in resto if not x.startswith("--")], plataformas=plats, datos=datos)
    elif orden == "agregar" and len([x for x in resto if x != "--sin-revisar" and not x.startswith("--sin-config=")]) == 2:
        libres = [x for x in resto if x != "--sin-revisar" and not x.startswith("--sin-config=")]
        for x in resto:
            if x.startswith("--sin-config="):
                _SIN_CONFIG.update(k for k in x.split("=", 1)[1].split(",") if k)
        agregar(libres[0], os.path.abspath(libres[1]), "--sin-revisar" in resto, forzar)
    elif orden == "estado" and len(resto) == 1:
        estado(os.path.abspath(resto[0]), como_json)
    elif orden == "aviso" and len(resto) == 1:
        print(aviso(os.path.abspath(resto[0])))
    elif orden == "actualizar" and len([x for x in resto if not x.startswith("--")]) >= 1:
        automatico = "--automatico" in resto
        for x in resto:
            if x.startswith("--sin-config="):
                _SIN_CONFIG.update(k for k in x.split("=", 1)[1].split(",") if k)
        libres = [x for x in resto if not x.startswith("--")]
        actualizar(os.path.abspath(libres[0]), libres[1:], forzar, automatico)
    elif orden == "acciones" and len(resto) == 1:
        print(armar_acciones(os.path.abspath(resto[0]), forzar=True))
    elif orden == "generar" and len(resto) >= 1:
        app = os.path.abspath(resto[0])
        lock = candado(app)
        for pid in resto[1:]:
            if pid not in lock["piezas"]:
                sys.exit(f"La app no tiene la pieza «{pid}».")
        generar_todo(app, resto[1:] or None, forzar=forzar)
    elif orden == "repo" and len([x for x in resto if x != "--aplicar"]) == 2 and resto[0] == "configurar":
        return repo_configurar(os.path.abspath([x for x in resto if x != "--aplicar"][1]), "--aplicar" in resto)
    elif orden == "diferencias" and len(resto) == 2:
        diferencias(os.path.abspath(resto[0]), resto[1])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:  # pieza.py diferencias … | head
        sys.exit(0)

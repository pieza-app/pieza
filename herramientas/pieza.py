#!/usr/bin/env python3
"""pieza — enchufa piezas de esta base en una app. Solo biblioteca estándar.

  pieza.py listar                         Las piezas disponibles.
  pieza.py iniciar <app> <id> <Nombre> [--plataformas=mac,windows,linux] [--datos=sistema|visible]
                                          Crea app.json en una app que aún no lo tiene.
  pieza.py agregar <pieza> <app> [--sin-revisar] [--sin-config=clave,…]
                                          Copia la pieza (y lo que requiere) a la app y la anota en piezas.json. Oficial o de la
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
  pieza.py diferencias <app> <pieza>      Lo que la app cambió de una pieza (para devolverlo a la base si es mejor).
  pieza.py acciones <app>                 Arma acciones.json (lo lee el host genérico): las acciones de las piezas instaladas más
                                          las de app.json → «acciones». agregar/actualizar lo hacen solos si la app tiene host.
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
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: De dónde se leen las piezas. «Pieza al día» corre esta herramienta fijada a una versión y le pasa las piezas nuevas solo
#: como datos (PIEZA_CATALOGO): así nunca ejecuta código que no fijó la app.
PIEZAS = os.environ.get("PIEZA_CATALOGO") or os.path.join(BASE, "piezas")
ID = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
SCRIPT = re.compile(r"^\w+\.py$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
TIPOS = {"texto", "enum", "bool", "entero", "rutaRelativa", "base64", "lista"}
ESTADOS = {"lista", "planeada"}
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
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(valor, ensure_ascii=False, indent=indent) + "\n")
    os.replace(tmp, ruta)


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
         "red_nota": str, "tareas_persona": list, "archivos": dict, "solo": dict, "config": dict, "config_opcional": dict,
         "acciones": dict, "textos": dict,
         "cambios": list, "tomar_de": (str, list), "origen": str}


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
    if not SCRIPT.match(a.get("script", "") if isinstance(a.get("script"), str) else ""):
        e.append(f"{donde}: «script» debe ser nombre.py")
    elif scripts is not None and a["script"] not in scripts and not a.get("scriptDeLaApp"):
        e.append(f"{donde}: el script {a['script']} no viene en la pieza (o marca scriptDeLaApp)")
    datos, args = a.get("datos", {}), a.get("args", [])
    if not isinstance(datos, dict) or not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        return e + [f"{donde}: «datos» es {{campo: regla}} y «args» una lista de textos"]
    for campo, regla in datos.items():
        if campo == "*":
            if regla != "pasar":
                e.append(f"{donde}: «*» solo puede ser \"pasar\"")
            continue
        if not CAMPO.match(campo) or campo in ("__proto__", "constructor", "prototype"):
            e.append(f"{donde}: campo raro «{campo}»")
        e += _errores_regla(f"{donde}: «{campo}»", regla)
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
    if por_archivo and a.get("entrada") != "archivo":
        e.append(f"{donde}: {', '.join(por_archivo)} no van en args: necesita \"entrada\": \"archivo\"")
    if a.get("entrada") not in (None, "archivo"):
        e.append(f"{donde}: «entrada» es \"archivo\" o null")
    if not isinstance(a.get("limite"), int) or isinstance(a.get("limite"), bool) or not 1 <= a["limite"] <= 3600:
        e.append(f"{donde}: «limite» (segundos) es obligatorio, entre 1 y 3600")
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


def _errores_regla(donde, r):
    if not isinstance(r, dict) or r.get("tipo") not in TIPOS:
        return [f"{donde}: tipo desconocido"]
    e, t = [], r["tipo"]
    entero = lambda x: isinstance(x, int) and not isinstance(x, bool)
    if t == "texto" and not (entero(r.get("max")) and 0 < r["max"] <= 5 * 1024 * 1024):
        e.append(f"{donde}: un texto necesita «max»")
    if t == "enum" and not (isinstance(r.get("valores"), list) and r["valores"]
                            and all(isinstance(x, str) and re.match(r"^[\w.-]+$", x) for x in r["valores"])):
        e.append(f"{donde}: un enum necesita «valores» (textos simples)")
    if t == "entero" and any(k in r and not entero(r[k]) for k in ("min", "max")):
        e.append(f"{donde}: «min»/«max» son enteros")
    if t == "base64" and not (entero(r.get("maxBytes")) and 0 < r["maxBytes"] <= 5 * 1024 * 1024):
        e.append(f"{donde}: base64 necesita «maxBytes»")
    if t == "rutaRelativa" and "extensiones" in r and not (isinstance(r["extensiones"], list)
                                                          and all(isinstance(x, str) and re.match(r"^\.\w{1,10}$", x) for x in r["extensiones"])):
        e.append(f"{donde}: «extensiones» es una lista como [\".md\"]")
    if t == "lista":
        if "max" in r and not (entero(r["max"]) and 0 < r["max"] <= 10000):
            e.append(f"{donde}: «max» de una lista es un entero")
        if "de" in r:
            e += [f"{donde}: una lista de listas no"] if isinstance(r["de"], dict) and r["de"].get("tipo") == "lista" \
                else _errores_regla(f"{donde} (cada uno)", r["de"])
    return e


def destino_seguro(app, relativa):
    ruta = os.path.realpath(os.path.join(app, relativa))
    if os.path.isabs(relativa) or not ruta.startswith(os.path.realpath(app) + os.sep):
        sys.exit(f"Destino fuera de la app: {relativa}")
    return ruta


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
        e.append("«estado» debe ser lista o planeada")
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
    escribir(ruta, {"nombre": nombre, "id": aid, "datos": datos, "icono": "docs/favicon.svg", "plataformas": plataformas,
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
        shutil.copy2(os.path.join(BASE, "plantillas", "pieza-al-dia.yml"), flujo)
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


def _textos_en(app):
    """El archivo de inglés de la app, si existe (los tres formatos de hoy guardan las frases en «textos»)."""
    ruta = os.path.join(app, "ui", "idiomas", "en.json")
    return ruta if os.path.isfile(ruta) else None


#: Claves opcionales de config que no se suman a app.json (`agregar … --sin-config=tema`). Se guardan en piezas.json, por pieza.
_SIN_CONFIG = set()


def copiar(pid, app, forzar=False, lock=None):
    p = pieza(pid)
    lock = lock or candado(app)
    antes = lock["piezas"].get(pid, {})
    copiados, saltados = {}, []
    plataformas_app = set((leer(os.path.join(app, "app.json"), {}) or {}).get("plataformas") or PLATAFORMAS)
    for origen, destino in p.get("archivos", {}).items():
        if not plataformas_app & set(p.get("solo", {}).get(origen, PLATAFORMAS)):
            continue  # el archivo es de una plataforma que esta app no tiene (app.json → «plataformas»)
        dst = destino_seguro(app, destino)
        anterior = antes.get("archivos", {}).get(destino)
        if os.path.exists(dst) and not forzar:
            cambiado_por_la_app = anterior is None or huella(dst) != anterior
            if cambiado_por_la_app:
                saltados.append(destino)
                copiados[destino] = anterior or ""
                continue
        fuente = os.path.join(carpeta_de(pid), origen)
        if not ruta_relativa_ok(origen) or not ruta_relativa_ok(destino) or not destino.startswith(PREFIJOS_DESTINO) \
                or os.path.islink(fuente):
            sys.exit(f"{pid}: no copio {origen} → {destino} (ruta no permitida o enlace)")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(fuente, dst)
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
    # Si algún archivo quedó sin actualizar (la app lo cambió), la versión anotada no avanza: estado sigue avisando.
    version = p["version"] if not saltados else antes.get("version", "0.0.0")
    lock["piezas"][pid] = {"version": version, "archivos": copiados,
                           **({"sin_config": sin_config} if sin_config else {}),
                           # Lo que la app aceptó: si una versión nueva pide más (otra pieza, permisos, red), no se aplica sola.
                           "ficha": {k: p.get(k, [] if k != "permisos" else {}) for k in ("requiere", "permisos", "red")}}
    # Las acciones de la versión que quedó copiada (si la app no aceptó la nueva, siguen las de antes): de aquí sale acciones.json.
    acciones = p.get("acciones") if not saltados else antes.get("acciones", p.get("acciones"))
    if acciones:
        lock["piezas"][pid]["acciones"] = acciones
    if pid in _FUENTE:
        lock["piezas"][pid]["fuente"] = _FUENTE[pid]
    escribir(os.path.join(app, "piezas.json"), lock)
    return saltados


#: Las piezas que leen acciones.json (el host genérico). Con alguna de ellas en la app, agregar/actualizar lo arman solos.
HOSTS = ("host-mac", "host-escritorio")


def armar_acciones(app, forzar=False):
    """acciones.json en la raíz de la app: las acciones de las piezas instaladas (las de la versión copiada, guardadas en
    piezas.json) más las de app.json → «acciones» (las propias de la app, con su script en bin/). Lo lee el host genérico; va
    dentro de la app junto a app.json. Dos acciones con el mismo nombre o una que no pasa las reglas detienen todo."""
    lock = candado(app)
    ruta = os.path.join(app, "acciones.json")
    if not forzar and not os.path.exists(ruta) and not any(h in lock["piezas"] for h in HOSTS):
        return None
    todas_a, origen, errores = {}, {}, []
    fuentes = []
    for pid, info in sorted(lock["piezas"].items()):
        acciones = info.get("acciones")
        if acciones is None and not info.get("fuente"):
            # Instalada antes de que piezas.json guardara las acciones: las de la base, si es la misma versión.
            base = todas().get(pid) or {}
            if base.get("version") == info.get("version"):
                acciones = base.get("acciones")
            elif base.get("acciones"):
                print(f"    ! {pid} {info.get('version')}: no sé sus acciones (la base tiene {base.get('version')}); actualízala")
        fuentes.append((pid, acciones or {}))
    a = leer(os.path.join(app, "app.json"), {}) or {}
    propias = a.get("acciones") or {}
    if not isinstance(propias, dict):
        sys.exit("app.json: «acciones» es {nombre: acción}.")
    scripts_app = set(os.listdir(os.path.join(app, "bin"))) if os.path.isdir(os.path.join(app, "bin")) else set()
    for pid, acciones in fuentes + [("app", propias)]:
        for nombre, accion in acciones.items():
            e = errores_accion(nombre, accion, scripts_app if pid == "app" else None)
            if pid == "app" and not e and accion["script"] not in scripts_app:
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


def agregar(pid, app, sin_revisar=False):
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
        if p in lock["piezas"]:
            print(f"· {p} ya estaba")
            anotar_sin_config(app, lock, [p])
            continue
        saltados = copiar(p, app, lock=lock)
        print(f"+ {p} {pieza(p)['version']}")
        for k, cuando in pieza(p).get("config_opcional", {}).items():
            if k in _SIN_CONFIG:
                print(f"    · no sumé «{k}» a app.json (--sin-config)")
            else:
                print(f"    · sumé «{k}» a app.json: {cuando} Si no, vuelve a agregarla con --sin-config={k}.")
        for s in saltados:
            print(f"    ! {s} ya existía en la app y no lo pisé. Compara con: pieza.py diferencias {app} {p}")
    avisar_sin_config_desconocida(con_requisitos(pid))
    if armar_acciones(app):
        print("~ acciones.json (lo lee el host: va dentro de la app junto a app.json)")


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
        salida.append({"pieza": pid, "actual": info["version"], "comunidad": bool(info.get("fuente")), "pide_mas": pide_mas, "nueva": nueva, "al_dia": semver(info["version"]) >= semver(nueva),
                       "tipo": tipo, "seguridad": any(c.get("seguridad") for c in pendientes), "cambios": pendientes,
                       "cambiados_por_la_app": cambiados, "faltan": faltan, "choques": choques, "juntas": [],
                       "automatico": bool(pendientes) and tipo != "rompe" and not cambiados and not faltan and not pide_mas})
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


def aviso(app):
    """Markdown con lo que no se puede actualizar solo, para un issue."""
    manual = [x for x in estado_app(app) if not x["al_dia"] and not x["automatico"]]
    if not manual:
        return ""
    l = ["Hay versiones nuevas de piezas que **no se pueden actualizar solas**. Esto es lo que cambió y qué hacer.", ""]
    for x in manual:
        l.append(f"### {x['pieza']} {x['actual']} → {x['nueva']}" + (" · seguridad" if x["seguridad"] else ""))
        for c in x["cambios"]:
            l.append(f"- **{c['version']}** ({c['tipo']}{', seguridad' if c.get('seguridad') else ''}): {c['resumen']}")
            for paso in c.get("migrar", []):
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
        with open(ruta + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            f.write(texto + local)
        os.replace(ruta + ".tmp", ruta)
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
    elif orden == "iniciar" and len([x for x in resto if not x.startswith("--")]) == 3:
        plats = next((x.split("=", 1)[1].split(",") for x in resto if x.startswith("--plataformas=")), None)
        datos = next((x.split("=", 1)[1] for x in resto if x.startswith("--datos=")), "sistema")
        iniciar(*[x for x in resto if not x.startswith("--")], plataformas=plats, datos=datos)
    elif orden == "agregar" and len([x for x in resto if x != "--sin-revisar" and not x.startswith("--sin-config=")]) == 2:
        libres = [x for x in resto if x != "--sin-revisar" and not x.startswith("--sin-config=")]
        for x in resto:
            if x.startswith("--sin-config="):
                _SIN_CONFIG.update(k for k in x.split("=", 1)[1].split(",") if k)
        agregar(libres[0], os.path.abspath(libres[1]), "--sin-revisar" in resto)
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

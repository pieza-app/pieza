#!/usr/bin/env python3
"""pieza — enchufa piezas de esta base en una app. Solo biblioteca estándar.

  pieza.py listar                         Las piezas disponibles.
  pieza.py iniciar <app> <id> <Nombre>    Crea app.json en una app que aún no lo tiene.
  pieza.py agregar <pieza> <app> [--sin-revisar]
                                          Copia la pieza (y lo que requiere) a la app y la anota en piezas.json. Oficial o de la
                                          comunidad: las de la comunidad revisadas se verifican con su huella; las que aún no se
                                          revisan solo con --sin-revisar (bajo tu responsabilidad).
  pieza.py estado <app> [--json]          Qué piezas tiene la app, qué versiones nuevas hay, de qué tipo (arreglo, mejora,
                                          rompe, seguridad), qué archivos cambió la app y qué se puede actualizar solo.
  pieza.py actualizar <app> [pieza] [--automatico] [--forzar]
                                          Trae la versión nueva. Nunca pisa un archivo que la app cambió, salvo --forzar.
                                          --automatico: solo arreglos y mejoras compatibles sobre archivos que la app no tocó.
  pieza.py aviso <app>                    En Markdown, lo que hay que actualizar a mano (cambios que rompen o archivos de la
                                          app) con los pasos para migrar. Es el cuerpo del issue que abre «Pieza al día».
  pieza.py diferencias <app> <pieza>      Lo que la app cambió de una pieza (para devolverlo a la base si es mejor).
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
PIEZAS = os.path.join(BASE, "piezas")
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


def leer(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def escribir(ruta, valor):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(valor, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, ruta)


def huella(ruta):
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def version_num(v):
    return tuple(int(x) for x in v.split("."))


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
         "red_nota": str, "tareas_persona": list, "archivos": dict, "config": dict, "acciones": dict, "textos": dict,
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
    if not all(isinstance(v, str) for v in p.get("compatible", {}).values()):
        e.append("«compatible» es {pieza: rango}")
    for a in p.get("acciones", {}).values():
        if not isinstance(a, dict) or not isinstance(a.get("datos", {}), dict) or not isinstance(a.get("args", []), list) \
                or not all(isinstance(x, str) for x in a.get("args", [])) \
                or not all(isinstance(r, dict) for r in a.get("datos", {}).values()):
            e.append("cada acción es {script, args: [textos], datos: {campo: {tipo…}}, limite}")
            break
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
        donde = f"acción «{nombre}»"
        if not SCRIPT.match(a.get("script", "")):
            e.append(f"{donde}: «script» debe ser nombre.py")
        elif a["script"] not in scripts and not a.get("scriptDeLaApp"):
            e.append(f"{donde}: el script {a['script']} no viene en la pieza (o marca scriptDeLaApp)")
        datos = a.get("datos", {})
        for campo, regla in datos.items():
            if campo == "*":
                continue
            if regla.get("tipo") not in TIPOS:
                e.append(f"{donde}: «{campo}» con tipo desconocido")
            if regla.get("tipo") == "texto" and not isinstance(regla.get("max"), int):
                e.append(f"{donde}: «{campo}» de texto necesita «max»")
        for arg in a.get("args", []):
            if arg.startswith("$"):
                regla = datos.get(arg[1:], {})
                # Regla de oro: lo que escribe la persona nunca va como argumento del proceso, solo por el archivo de entrada.
                if regla.get("tipo") not in ("enum", "entero"):
                    e.append(f"{donde}: el argumento {arg} solo puede ser un campo enum o entero")
            elif not re.match(r"^[\w.-]+$", arg):
                e.append(f"{donde}: argumento literal raro «{arg}»")
        por_archivo = [k for k in datos if k == "*" or ("$" + k) not in a.get("args", [])]
        if por_archivo and a.get("entrada") != "archivo":
            e.append(f"{donde}: {', '.join(por_archivo)} no van en args: necesita \"entrada\": \"archivo\"")
        if not isinstance(a.get("limite"), int) or not 1 <= a["limite"] <= 3600:
            e.append(f"{donde}: «limite» (segundos) es obligatorio, entre 1 y 3600")
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


def iniciar(app, aid, nombre):
    ruta = os.path.join(app, "app.json")
    if os.path.exists(ruta):
        sys.exit("Esta app ya tiene app.json.")
    if not re.match(r"^[a-z][a-z0-9]{1,30}$", aid):
        sys.exit("El id va en minúsculas, solo letras y números (ej. esquema).")
    escribir(ruta, {"nombre": nombre, "id": aid, "datos": "sistema", "icono": "docs/favicon.svg",
                    "config": {"idioma_ui": ["es", "en"], "tema": ["sistema", "claro", "oscuro"], "bienvenida": "bool"}})
    print(f"+ {ruta}")
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
    ajustes.setdefault("enabledPlugins", {}).setdefault("pieza@pieza", True)
    os.makedirs(os.path.dirname(ajustes_ruta), exist_ok=True)
    escribir(ajustes_ruta, ajustes)
    print(f"+ {ajustes_ruta}")
    print("Falta (con permiso de quien mantiene): el topic «hecho-con-pieza» en el repo, el sello en el README y la página, y el"
          " ícono en docs/favicon.svg (solo formas, ≤ 8 KB): así la app aparece con su ícono en la página de Pieza.")


def _textos_en(app):
    """El archivo de inglés de la app, si existe (los tres formatos de hoy guardan las frases en «textos»)."""
    ruta = os.path.join(app, "ui", "idiomas", "en.json")
    return ruta if os.path.isfile(ruta) else None


def copiar(pid, app, forzar=False, lock=None):
    p = pieza(pid)
    lock = lock or candado(app)
    antes = lock["piezas"].get(pid, {})
    copiados, saltados = {}, []
    for origen, destino in p.get("archivos", {}).items():
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
    # Config: suma las claves que la pieza necesita a app.json (sin tocar las que ya existen).
    ruta_app = os.path.join(app, "app.json")
    a = leer(ruta_app)
    if a is not None and p.get("config"):
        a.setdefault("config", {})
        for k, v in p["config"].items():
            a["config"].setdefault(k, v)
        escribir(ruta_app, a)
    # Textos: suma al inglés de la app las frases que falten.
    en = _textos_en(app)
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
                           # Lo que la app aceptó: si una versión nueva pide más (otra pieza, permisos, red), no se aplica sola.
                           "ficha": {k: p.get(k, [] if k != "permisos" else {}) for k in ("requiere", "permisos", "red")}}
    if pid in _FUENTE:
        lock["piezas"][pid]["fuente"] = _FUENTE[pid]
    escribir(os.path.join(app, "piezas.json"), lock)
    return saltados


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
            continue
        saltados = copiar(p, app, lock=lock)
        print(f"+ {p} {pieza(p)['version']}")
        for s in saltados:
            print(f"    ! {s} ya existía en la app y no lo pisé. Compara con: pieza.py diferencias {app} {p}")


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
                       "cambiados_por_la_app": cambiados, "faltan": faltan, "choques": choques,
                       "automatico": bool(pendientes) and tipo != "rompe" and not cambiados and not faltan and not choques
                       and not pide_mas})
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
            print(f"    ! {pid} necesita {req} {rango} (hay {tiene})")


def actualizar(app, solo=None, forzar=False, automatico=False):
    lock = candado(app)
    e = {x["pieza"]: x for x in estado_app(app)}
    for pid in [solo] if solo else sorted(lock["piezas"]):
        if pid not in lock["piezas"]:
            sys.exit(f"La app no tiene la pieza «{pid}».")
        x = e[pid]
        if x["al_dia"] and not forzar:
            continue
        if automatico and not x["automatico"]:
            continue
        if x["choques"] and not forzar:
            print(f"! no actualicé {pid}: " + "; ".join(f"{a} necesita {b} {c} (hay {d})" for a, b, c, d in x["choques"]))
            continue
        for r in con_requisitos(pid):  # lo que la versión nueva requiere y la app aún no tiene
            if r != pid and r not in lock["piezas"]:
                if pieza(r).get("estado") == "planeada":
                    sys.exit(f"{pid} ahora requiere «{r}», que aún no está extraída.")
                copiar(r, app, lock=lock)
                print(f"+ {r} {pieza(r)['version']} (la requiere {pid})")
        saltados = copiar(pid, app, forzar=forzar, lock=lock)
        print(f"↑ {pid} {x['actual']} → {pieza(pid)['version']}" + (" (seguridad)" if x["seguridad"] else ""))
        for s in saltados:
            print(f"    ! no actualicé {s}: la app lo cambió. Revisa: pieza.py diferencias {app} {pid}")


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
            l.append(f"- `{pid}` necesita `{req}` {rango} (hay {tiene}): actualiza las dos juntas.")
        l.append("")
    l.append("Lo abrió «Pieza al día» (`.github/workflows/pieza-al-dia.yml`). Se cierra solo cuando todo queda al día.")
    return "\n".join(l)


def diferencias(app, pid):
    for origen, destino in pieza(pid).get("archivos", {}).items():
        base = open(os.path.join(PIEZAS, pid, origen), encoding="utf-8").read().splitlines(keepends=True)
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
    elif orden == "iniciar" and len(resto) == 3:
        iniciar(*resto)
    elif orden == "agregar" and len([x for x in resto if x != "--sin-revisar"]) == 2:
        libres = [x for x in resto if x != "--sin-revisar"]
        agregar(libres[0], os.path.abspath(libres[1]), "--sin-revisar" in resto)
    elif orden == "estado" and len(resto) == 1:
        estado(os.path.abspath(resto[0]), como_json)
    elif orden == "aviso" and len(resto) == 1:
        print(aviso(os.path.abspath(resto[0])))
    elif orden == "actualizar" and len(resto) in (1, 2):
        automatico = "--automatico" in resto
        resto = [x for x in resto if x != "--automatico"]
        actualizar(os.path.abspath(resto[0]), resto[1] if len(resto) == 2 else None, forzar, automatico)
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

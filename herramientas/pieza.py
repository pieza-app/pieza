#!/usr/bin/env python3
"""pieza — enchufa piezas de esta base en una app. Solo biblioteca estándar.

  pieza.py listar                         Las piezas disponibles.
  pieza.py iniciar <app> <id> <Nombre>    Crea app.json en una app que aún no lo tiene.
  pieza.py agregar <pieza> <app>          Copia la pieza (y lo que requiere) a la app y la anota en piezas.json.
  pieza.py estado <app> [--json]          Qué piezas tiene la app, qué versiones nuevas hay, de qué tipo (arreglo, mejora,
                                          rompe, seguridad), qué archivos cambió la app y qué se puede actualizar solo.
  pieza.py actualizar <app> [pieza] [--automatico] [--forzar]
                                          Trae la versión nueva. Nunca pisa un archivo que la app cambió, salvo --forzar.
                                          --automatico: solo arreglos y mejoras compatibles sobre archivos que la app no tocó.
  pieza.py aviso <app>                    En Markdown, lo que hay que actualizar a mano (cambios que rompen o archivos de la
                                          app) con los pasos para migrar. Es el cuerpo del issue que abre «Pieza al día».
  pieza.py diferencias <app> <pieza>      Lo que la app cambió de una pieza (para devolverlo a la base si es mejor).
  pieza.py revisar                        Valida todos los pieza.json de la base (formato y reglas de seguridad).
  pieza.py catalogo [--json]              Todas las piezas, listas y planeadas, con todo lo que declaran (lo lee la skill).
  pieza.py ficha <pieza>… [--plataformas mac,windows,linux,ios,android] [--json]
                                          La ficha de una app con esas piezas: requisitos, pantallas, config, permisos por
                                          plataforma, red, acciones y tareas de David. Es lo que se le muestra antes de crear.

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


def pieza(pid):
    p = leer(os.path.join(PIEZAS, pid, "pieza.json"))
    if not p:
        sys.exit(f"No existe la pieza «{pid}». Mira: pieza.py listar")
    return p


def todas():
    return {d: leer(os.path.join(PIEZAS, d, "pieza.json")) for d in sorted(os.listdir(PIEZAS))
            if os.path.isfile(os.path.join(PIEZAS, d, "pieza.json"))}


def con_requisitos(pid, vistos=None):
    """La pieza y todo lo que requiere, en orden (primero lo que se necesita antes)."""
    vistos = vistos if vistos is not None else []
    for r in pieza(pid).get("requiere", []):
        if r not in vistos:
            con_requisitos(r, vistos)
    if pid not in vistos:
        vistos.append(pid)
    return vistos


def destino_seguro(app, relativa):
    ruta = os.path.realpath(os.path.join(app, relativa))
    if os.path.isabs(relativa) or not ruta.startswith(os.path.realpath(app) + os.sep):
        sys.exit(f"Destino fuera de la app: {relativa}")
    return ruta


# ── Revisar ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def errores_pieza(pid, p, ids):
    e = []
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
        if not os.path.isfile(os.path.join(PIEZAS, pid, origen)):
            e.append(f"falta el archivo {origen}")
        if os.path.isabs(destino) or ".." in destino.split("/"):
            e.append(f"destino inválido {destino}")
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
    for pid, p in ps.items():
        e = errores_pieza(pid, p or {}, ps)
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
    escribir(ruta, {"nombre": nombre, "id": aid, "datos": "sistema",
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
    print("Falta (con permiso de quien mantiene): el topic «hecho-con-pieza» en el repo y el sello en el README y la página.")


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
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(PIEZAS, pid, origen), dst)
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
    lock["piezas"][pid] = {"version": version, "archivos": copiados}
    escribir(os.path.join(app, "piezas.json"), lock)
    return saltados


def agregar(pid, app):
    if not os.path.isfile(os.path.join(app, "app.json")):
        sys.exit("La app no tiene app.json. Créalo con: pieza.py iniciar <app> <id> <Nombre>")
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
        p = todas().get(pid) or {}
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
        salida.append({"pieza": pid, "actual": info["version"], "nueva": nueva, "al_dia": semver(info["version"]) >= semver(nueva),
                       "tipo": tipo, "seguridad": any(c.get("seguridad") for c in pendientes), "cambios": pendientes,
                       "cambiados_por_la_app": cambiados, "faltan": faltan, "choques": choques,
                       "automatico": bool(pendientes) and tipo != "rompe" and not cambiados and not choques})
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
                    (" · se actualiza sola" if x["automatico"] else " · a mano")
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
         "tareas_david": [], "plataformas": list(plataformas), "faltan_en": [], "por_extraer": []}
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
        f["tareas_david"] += [t for t in p.get("tareas_david", []) if t not in f["tareas_david"]]
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
    if f["tareas_david"]:
        l += ["SOLO DAVID"] + [f"  {t}" for t in f["tareas_david"]]
    return "\n".join(l)


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
    elif orden == "iniciar" and len(resto) == 3:
        iniciar(*resto)
    elif orden == "agregar" and len(resto) == 2:
        agregar(resto[0], os.path.abspath(resto[1]))
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

#!/usr/bin/env python3
"""pieza — enchufa piezas de esta base en una app. Solo biblioteca estándar.

  pieza.py listar                         Las piezas disponibles.
  pieza.py iniciar <app> <id> <Nombre>    Crea app.json en una app que aún no lo tiene.
  pieza.py agregar <pieza> <app>          Copia la pieza (y lo que requiere) a la app y la anota en piezas.json.
  pieza.py estado <app>                   Qué piezas tiene la app, si hay versión nueva y qué archivos cambió la app.
  pieza.py actualizar <app> [pieza] [--forzar]
                                          Trae la versión nueva. Nunca pisa un archivo que la app cambió, salvo --forzar.
  pieza.py diferencias <app> <pieza>      Lo que la app cambió de una pieza (para devolverlo a la base si es mejor).
  pieza.py revisar                        Valida todos los pieza.json de la base (formato y reglas de seguridad).

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
    print(f"Listo: {ruta}")


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
    lock["piezas"][pid] = {"version": p["version"], "archivos": copiados}
    escribir(os.path.join(app, "piezas.json"), lock)
    return saltados


def agregar(pid, app):
    if not os.path.isfile(os.path.join(app, "app.json")):
        sys.exit("La app no tiene app.json. Créalo con: pieza.py iniciar <app> <id> <Nombre>")
    lock = candado(app)
    for p in con_requisitos(pid):
        if p in lock["piezas"]:
            print(f"· {p} ya estaba")
            continue
        saltados = copiar(p, app, lock=lock)
        print(f"+ {p} {pieza(p)['version']}")
        for s in saltados:
            print(f"    ! {s} ya existía en la app y no lo pisé. Compara con: pieza.py diferencias {app} {p}")


def estado(app):
    lock = candado(app)
    if not lock["piezas"]:
        print("Esta app aún no tiene piezas.")
        return
    for pid, info in sorted(lock["piezas"].items()):
        nueva = (todas().get(pid) or {}).get("version", "?")
        marca = "al día" if nueva == info["version"] else f"hay {nueva}"
        print(f"{pid} {info['version']} ({marca})")
        for destino, h in info["archivos"].items():
            ruta = os.path.join(app, destino)
            if not os.path.exists(ruta):
                print(f"    ✗ falta {destino}")
            elif huella(ruta) != h:
                print(f"    ~ la app cambió {destino}")


def actualizar(app, solo=None, forzar=False):
    lock = candado(app)
    for pid in [solo] if solo else sorted(lock["piezas"]):
        if pid not in lock["piezas"]:
            sys.exit(f"La app no tiene la pieza «{pid}».")
        antes, nueva = lock["piezas"][pid]["version"], pieza(pid)["version"]
        if antes == nueva and not forzar:
            continue
        saltados = copiar(pid, app, forzar=forzar, lock=lock)
        print(f"↑ {pid} {antes} → {nueva}")
        for s in saltados:
            print(f"    ! no actualicé {s}: la app lo cambió. Revisa: pieza.py diferencias {app} {pid}")


def diferencias(app, pid):
    for origen, destino in pieza(pid).get("archivos", {}).items():
        base = open(os.path.join(PIEZAS, pid, origen), encoding="utf-8").read().splitlines(keepends=True)
        ruta = os.path.join(app, destino)
        local = open(ruta, encoding="utf-8").read().splitlines(keepends=True) if os.path.exists(ruta) else []
        sys.stdout.writelines(difflib.unified_diff(base, local, f"base/{origen}", f"app/{destino}"))


def main(a):
    if not a or a[0] in ("-h", "--help", "ayuda"):
        print(__doc__)
        return 0
    orden, resto = a[0], a[1:]
    forzar = "--forzar" in resto
    resto = [x for x in resto if x != "--forzar"]
    if orden == "listar":
        for pid, p in todas().items():
            req = f"  (requiere {', '.join(p['requiere'])})" if p.get("requiere") else ""
            print(f"{pid:12} {p['version']:8} {p['descripcion']}{req}")
    elif orden == "revisar":
        return revisar()
    elif orden == "iniciar" and len(resto) == 3:
        iniciar(*resto)
    elif orden == "agregar" and len(resto) == 2:
        agregar(resto[0], os.path.abspath(resto[1]))
    elif orden == "estado" and len(resto) == 1:
        estado(os.path.abspath(resto[0]))
    elif orden == "actualizar" and len(resto) in (1, 2):
        actualizar(os.path.abspath(resto[0]), resto[1] if len(resto) == 2 else None, forzar)
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

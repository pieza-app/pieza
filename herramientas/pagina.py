#!/usr/bin/env python3
"""Arma los datos de la página pública (docs/datos/). Solo biblioteca estándar.

  pagina.py catalogo      docs/datos/catalogo.json desde los pieza.json (lo que la página muestra del catálogo).
  pagina.py proyectos     docs/datos/proyectos.json: los repos públicos con el topic «hecho-con-pieza», desde la búsqueda de GitHub.
  pagina.py skills        docs/skills/<skill>.zip: cada skill lista para subir a claude.ai.
  pagina.py todo          Todo lo anterior.

Sin telemetría: solo cuentan los repos públicos que eligieron aparecer poniéndose el topic. Usa GITHUB_TOKEN si existe (más
consultas por hora); sin él también funciona.
"""
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(BASE, "docs", "datos")
TOPIC = "hecho-con-pieza"
#: La familia: apps de quienes mantienen Pieza (se marcan aparte en la página, igual cuentan).
FAMILIA = {"minuta-app", "graba-app", "corta-app", "alcancia-app", "repasa-app", "esquema-app", "pieza-app"}
MAXIMO = 1000  # lo más que entrega la búsqueda de GitHub


def escribir(nombre, valor):
    os.makedirs(DATOS, exist_ok=True)
    ruta = os.path.join(DATOS, nombre)
    with open(ruta + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump(valor, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(ruta + ".tmp", ruta)
    return ruta


def catalogo():
    sys.path.insert(0, os.path.join(BASE, "herramientas"))
    import pieza
    campos = ("nombre", "categoria", "estado", "version", "descripcion", "plataformas", "pantallas", "permisos", "red", "red_nota", "requiere", "compatible", "cambios")
    piezas = []
    for pid, p in pieza.todas().items():
        d = {"id": pid, **{k: p[k] for k in campos if k in p}}
        d["siempre"] = bool(p.get("recomendar", {}).get("siempre"))
        d["cuando"] = p.get("recomendar", {}).get("cuando", "")
        piezas.append(d)
    for d in piezas:
        d["fuente"] = "oficial"
    # Las de la comunidad (las rechazadas no se muestran): con su repo y su estado de revisión.
    com = pieza.leer(os.path.join(BASE, "comunidad", "catalogo.json"), {"piezas": []})
    for e in com.get("piezas", []):
        rev = e.get("revision", {})
        if rev.get("estado") == "rechazada":
            continue
        p = e.get("pieza", {})
        d = {"id": e["id"], **{k: p[k] for k in campos if k in p}, "fuente": "comunidad", "repo": e["repo"],
             "revision": {"estado": rev.get("estado", "sin-revisar"), **({"fecha": rev["fecha"]} if rev.get("fecha") else {})}}
        d["siempre"] = False
        d["cuando"] = p.get("recomendar", {}).get("cuando", "")
        piezas.append(d)
    listas = sum(1 for x in piezas if x.get("estado", "lista") == "lista" and x["fuente"] == "oficial")
    return escribir("catalogo.json", {"total": len(piezas), "listas": listas, "piezas": piezas})


def skills():
    """Un .zip por skill (carpeta <skill>/SKILL.md adentro), para descargarlo desde la página y subirlo a claude.ai."""
    import zipfile
    destino = os.path.join(BASE, "docs", "skills")
    os.makedirs(destino, exist_ok=True)
    hechos = []
    for nombre in sorted(os.listdir(os.path.join(BASE, "skills"))):
        carpeta = os.path.join(BASE, "skills", nombre)
        if not os.path.isfile(os.path.join(carpeta, "SKILL.md")):
            continue
        ruta = os.path.join(destino, nombre + ".zip")
        with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
            for raiz, _, archivos in os.walk(carpeta):
                for a in sorted(archivos):
                    completo = os.path.join(raiz, a)
                    z.write(completo, os.path.join(nombre, os.path.relpath(completo, carpeta)))
        hechos.append(ruta)
    return hechos


def texto(v, maximo):
    """Texto de afuera: solo string, sin caracteres de control y acotado. La página lo pone con textContent, nunca como HTML."""
    if not isinstance(v, str):
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", " ", v).strip()[:maximo]


def https(v):
    v = texto(v, 300)
    p = urllib.parse.urlsplit(v)
    return v if p.scheme == "https" and p.netloc and not p.username else ""


def limpiar_repo(r):
    nombre = texto(r.get("full_name"), 140)
    if not re.match(r"^[\w.-]+/[\w.-]+$", nombre):
        return None
    return {"nombre": nombre, "descripcion": texto(r.get("description"), 280), "url": f"https://github.com/{nombre}",
            "pagina": https(r.get("homepage")), "actualizado": texto(r.get("pushed_at"), 25),
            "familia": nombre.split("/")[0].lower() in FAMILIA}


def buscar(pedir=None):
    """Todos los repos con el topic (de a 100). `pedir(url)` devuelve el JSON; se puede reemplazar en las pruebas."""
    pedir = pedir or _pedir
    repos, pagina = [], 1
    while len(repos) < MAXIMO:
        q = urllib.parse.urlencode({"q": f"topic:{TOPIC} is:public fork:false archived:false", "sort": "updated", "per_page": 100, "page": pagina})
        d = pedir(f"https://api.github.com/search/repositories?{q}")
        items = d.get("items") or []
        repos += [x for x in map(limpiar_repo, items) if x]
        if len(items) < 100:
            break
        pagina += 1
    return repos


def _pedir(url):
    pedido = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "pieza-pagina"})
    if os.environ.get("GITHUB_TOKEN"):
        pedido.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.load(r)


def proyectos(pedir=None):
    repos = buscar(pedir)
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return escribir("proyectos.json", {"topic": TOPIC, "total": len(repos), "actualizado": ahora, "proyectos": repos})


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden in ("catalogo", "todo"):
        print(catalogo())
    if orden in ("skills", "todo"):
        print("\n".join(skills()))
    if orden in ("proyectos", "todo"):
        print(proyectos())
    if orden not in ("catalogo", "proyectos", "skills", "todo"):
        print(__doc__)
        sys.exit(2)

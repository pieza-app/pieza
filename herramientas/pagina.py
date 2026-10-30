#!/usr/bin/env python3
"""Arma los datos de la página pública (docs/datos/). Solo biblioteca estándar.

  pagina.py catalogo      docs/datos/catalogo.json desde los pieza.json (lo que la página muestra del catálogo).
  pagina.py proyectos     docs/datos/proyectos.json desde comunidad/proyectos.json (lo arma `comunidad.py proyectos` cada día):
                          los repos públicos con el topic «hecho-con-pieza», con su ícono y su estado de revisión.
  pagina.py skills        docs/skills/<skill>.zip: cada skill lista para subir a claude.ai.
  pagina.py todo          Todo lo anterior.

Sin telemetría: solo cuentan los repos públicos que eligieron aparecer poniéndose el topic. No sale a internet: lee lo que el
workflow «comunidad» ya bajó y validó. Los íconos se vuelven a validar (herramientas/icono.py) y se copian a docs/iconos/.
"""
import datetime
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(BASE, "docs", "datos")
ICONOS = os.path.join(BASE, "docs", "iconos")
sys.path.insert(0, os.path.join(BASE, "herramientas"))
import icono as I  # noqa: E402
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


def guardar_icono(tipo, nombre, svg, solo_current):
    """Escribe docs/iconos/<tipo>/<nombre>.svg si el ícono es válido y devuelve su ruta para la página ("" si no)."""
    if not svg or I.errores(svg, solo_current=solo_current) or not re.match(r"^[\w.-]+$", nombre):
        return ""
    carpeta = os.path.join(ICONOS, tipo)
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, nombre + ".svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg.strip() + "\n")
    return f"iconos/{tipo}/{nombre}.svg"


def catalogo():
    import pieza
    campos = ("nombre", "categoria", "estado", "version", "descripcion", "plataformas", "pantallas", "permisos", "red", "red_nota", "requiere", "compatible", "cambios")
    piezas = []
    for pid, p in pieza.todas().items():
        d = {"id": pid, **{k: p[k] for k in campos if k in p}}
        d["siempre"] = bool(p.get("recomendar", {}).get("siempre"))
        d["cuando"] = p.get("recomendar", {}).get("cuando", "")
        ruta = os.path.join(pieza.carpeta_de(pid), p.get("icono") or "icono.svg")
        d["icono"] = guardar_icono("piezas", pid, open(ruta, encoding="utf-8").read() if os.path.isfile(ruta) else "", True)
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
        d["icono"] = guardar_icono("piezas", "comunidad--" + e["id"], p.get("icono_svg", ""), True)
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


def proyectos():
    """Los proyectos del registro (sin los rechazados): la familia primero, después los aprobados y al final los sin revisar."""
    sys.path.insert(0, os.path.join(BASE, "herramientas"))
    import comunidad
    reg = comunidad.leer_proyectos()
    lista = []
    for e in reg.get("proyectos", []):
        estado = e.get("revision", {}).get("estado", "sin-revisar")
        if estado == "rechazado" or not re.match(r"^[\w.-]+/[\w.-]+$", e.get("repo", "")):
            continue
        dueno = e["repo"].split("/")[0].lower()
        lista.append({"nombre": comunidad.texto(e.get("nombre"), 80), "repo": e["repo"],
                      "descripcion": comunidad.texto(e.get("descripcion"), 280), "url": f"https://github.com/{e['repo']}",
                      "pagina": comunidad.https(e.get("pagina")), "actualizado": comunidad.texto(e.get("actualizado"), 25),
                      "familia": dueno in FAMILIA,
                      "icono": guardar_icono("proyectos", e["repo"].replace("/", "--"), e.get("icono_svg", ""), False),
                      "revision": {"estado": estado, **({"fecha": e["revision"]["fecha"]} if e.get("revision", {}).get("fecha") else {})}})
    orden = {"revisado": 0, "sin-revisar": 1}
    lista.sort(key=lambda x: (not x["familia"], orden.get(x["revision"]["estado"], 2), x["nombre"].lower()))
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return escribir("proyectos.json", {"topic": TOPIC, "total": len(lista),
                                       "aprobados": sum(1 for x in lista if x["revision"]["estado"] == "revisado"),
                                       "actualizado": ahora, "proyectos": lista})


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

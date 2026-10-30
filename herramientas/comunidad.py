#!/usr/bin/env python3
"""Catálogo de la comunidad: piezas que viven en repos de otras personas y crece solo. Solo biblioteca estándar.

  comunidad.py buscar                        Busca repos públicos con el topic «pieza-comunidad», valida su pieza.json y sus
                                             archivos, y los suma (o actualiza) en comunidad/catalogo.json como «sin revisar».
                                             Lo corre el workflow «comunidad» una vez al día.
  comunidad.py listar                        Lo que hay, con su estado de revisión.
  comunidad.py revisar <id> aprobar|rechazar [nota]
                                             Quien mantiene Pieza marca el commit actual como revisado (o rechazado). Lo revisado
                                             queda fijado a ese commit y a la huella de cada archivo: es lo único que se instala
                                             como seguro.

Seguridad: todo se baja de raw.githubusercontent.com en un commit fijo (nunca de una rama), sin seguir redirecciones, con
tamaño máximo, y se compara con su sha256. Si el autor cambia algo, vuelve a «sin revisar» hasta que alguien lo mire. Una pieza
de la comunidad solo puede requerir piezas oficiales y no puede usar el id de una oficial.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "herramientas"))
import pieza as P  # noqa: E402

CATALOGO = os.path.join(BASE, "comunidad", "catalogo.json")
TOPIC = "pieza-comunidad"
MAXIMO_ARCHIVO = 512 * 1024
MAXIMO_ARCHIVOS = 40
REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
#: Lo que se copia del pieza.json al catálogo (lo que necesitan la página, la ficha y el creador).
CAMPOS = ("id", "version", "estado", "nombre", "categoria", "descripcion", "recomendar", "requiere", "compatible", "plataformas",
          "pantallas", "permisos", "red", "red_nota", "tareas_persona", "archivos", "config", "acciones", "textos", "cambios")
ESTADOS = ("sin-revisar", "revisada", "rechazada")


# ── Red ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _abrir(url, maximo):
    if not url.startswith(("https://api.github.com/", "https://raw.githubusercontent.com/")):
        raise ValueError(f"Dominio no permitido: {url}")
    pedido = urllib.request.Request(url, headers={"User-Agent": "pieza-comunidad", "Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN") and url.startswith("https://api.github.com/"):
        pedido.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.build_opener(_SinRedirecciones).open(pedido, timeout=30) as r:
        datos = r.read(maximo + 1)
    if len(datos) > maximo:
        raise ValueError(f"Demasiado grande: {url}")
    return datos


class Red:
    """Lo que hace falta de GitHub. En las pruebas se reemplaza por una falsa."""

    def json(self, url):
        return json.loads(_abrir(url, 2 * 1024 * 1024))

    def archivo(self, repo, commit, ruta):
        return _abrir(f"https://raw.githubusercontent.com/{repo}/{commit}/{urllib.parse.quote(ruta)}", MAXIMO_ARCHIVO)


# ── Catálogo ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def leer():
    return P.leer(CATALOGO, {"formato": 1, "topic": TOPIC, "piezas": []})


def guardar(cat):
    os.makedirs(os.path.dirname(CATALOGO), exist_ok=True)
    cat["piezas"].sort(key=lambda e: e["id"])
    P.escribir(CATALOGO, cat)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ruta_segura(r):
    return isinstance(r, str) and r and not r.startswith("/") and ".." not in r.split("/") and "\\" not in r and len(r) < 200


def validar_remota(repo, commit, red, oficiales, ocupados):
    """Baja pieza.json y sus archivos en ese commit y los valida. Devuelve (pieza, huellas, errores)."""
    try:
        crudo = red.archivo(repo, commit, "pieza.json")
        p = json.loads(crudo)
    except Exception as e:  # noqa: BLE001
        return None, {}, [f"no pude leer pieza.json: {e}"]
    if not isinstance(p, dict):
        return None, {}, ["pieza.json no es un objeto"]
    pid = p.get("id")
    errores = []
    if not isinstance(pid, str) or not P.ID.match(pid):
        return None, {}, ["«id» inválido"]
    if pid in oficiales:
        errores.append(f"el id «{pid}» es de una pieza oficial: usa otro")
    if pid in ocupados and ocupados[pid] != repo:
        errores.append(f"el id «{pid}» ya lo usa {ocupados[pid]}")
    if p.get("estado", "lista") != "lista":
        errores.append("una pieza de la comunidad tiene que estar «lista» (con su código)")
    for r in p.get("requiere", []):
        if r not in oficiales:
            errores.append(f"requiere «{r}», que no es una pieza oficial")
    archivos = p.get("archivos", {})
    if not isinstance(archivos, dict) or not archivos or len(archivos) > MAXIMO_ARCHIVOS:
        errores.append(f"«archivos» tiene que tener entre 1 y {MAXIMO_ARCHIVOS}")
        archivos = {}
    # Las mismas reglas que una pieza oficial (regla de oro, permisos, red, cambios…), sin mirar el disco.
    errores += [e for e in P.errores_pieza(pid, p, oficiales, carpeta=None) if not e.startswith("falta el archivo")]
    huellas = {"pieza.json": sha(crudo)}
    for origen in archivos:
        if not ruta_segura(origen):
            errores.append(f"ruta rara en archivos: {origen!r}")
            continue
        try:
            huellas[origen] = sha(red.archivo(repo, commit, origen))
        except Exception as e:  # noqa: BLE001
            errores.append(f"no pude bajar {origen}: {e}")
    return {k: p[k] for k in CAMPOS if k in p}, huellas, errores


def buscar(red=None, hoy=None):
    """Recorre los repos con el topic y deja el catálogo al día. Devuelve un resumen de lo que cambió."""
    red = red or Red()
    hoy = hoy or datetime.date.today().isoformat()
    cat = leer()
    oficiales = P.todas()
    previas = {e["repo"]: e for e in cat["piezas"]}
    ocupados = {e["id"]: e["repo"] for e in cat["piezas"]}
    q = urllib.parse.urlencode({"q": f"topic:{TOPIC} is:public fork:false archived:false", "per_page": 100})
    repos = [r for r in red.json(f"https://api.github.com/search/repositories?{q}").get("items", [])
             if isinstance(r.get("full_name"), str) and REPO.match(r["full_name"])]
    nuevas, cambio, resumen = [], False, []
    for r in repos:
        repo = r["full_name"]
        rama = urllib.parse.quote(str(r.get("default_branch") or "main"))
        try:
            commit = red.json(f"https://api.github.com/repos/{repo}/commits/{rama}").get("sha", "")
        except Exception:  # noqa: BLE001
            commit = ""
        anterior = previas.get(repo)
        if not COMMIT.match(commit):
            if anterior:
                nuevas.append(anterior)
            continue
        if anterior and anterior.get("commit") == commit:
            nuevas.append(anterior)
            continue
        p, huellas, errores = validar_remota(repo, commit, red, oficiales, ocupados)
        if errores:
            resumen.append(f"✗ {repo}: " + "; ".join(errores[:5]))
            if anterior:  # un cambio malo no borra lo que ya estaba: queda la versión anterior (y su revisión)
                nuevas.append(anterior)
            continue
        rev = (anterior or {}).get("revision", {"estado": "sin-revisar"})
        if rev.get("estado") in ("revisada", "rechazada") and rev.get("huellas") != huellas:
            rev = {"estado": "sin-revisar", "antes": rev.get("estado")}
        entrada = {"id": p["id"], "repo": repo, "commit": commit, "encontrada": (anterior or {}).get("encontrada", hoy),
                   "actualizada": hoy, "pieza": p, "huellas": huellas, "revision": rev}
        ocupados[p["id"]] = repo
        nuevas.append(entrada)
        cambio = True
        resumen.append(("↑ " if anterior else "+ ") + f"{p['id']} ({repo}) → {rev['estado']}")
    quitadas = set(previas) - {e["repo"] for e in nuevas}
    for repo in quitadas:
        cambio = True
        resumen.append(f"− {previas[repo]['id']} ({repo}): ya no tiene el topic o no existe")
    if cambio:
        cat["piezas"] = nuevas
        guardar(cat)
    return resumen


def revisar(pid, veredicto, nota="", hoy=None):
    cat = leer()
    e = next((x for x in cat["piezas"] if x["id"] == pid), None)
    if not e:
        sys.exit(f"No hay una pieza de la comunidad «{pid}».")
    estado = {"aprobar": "revisada", "rechazar": "rechazada"}.get(veredicto)
    if not estado:
        sys.exit("El veredicto es aprobar o rechazar.")
    e["revision"] = {"estado": estado, "commit": e["commit"], "huellas": e["huellas"],
                     "fecha": hoy or datetime.date.today().isoformat(), "nota": nota[:300]}
    guardar(cat)
    print(f"{pid}: {estado} en {e['commit'][:7]}")


def entrada(pid):
    return next((x for x in leer()["piezas"] if x["id"] == pid), None)


def descargar(pid, sin_revisar=False, red=None, cache=None):
    """Baja la pieza al commit fijado y verifica cada archivo con su huella. Devuelve la carpeta lista para copiar."""
    red = red or Red()
    e = entrada(pid)
    if not e:
        sys.exit(f"No existe la pieza «{pid}» (ni oficial ni de la comunidad).")
    rev = e.get("revision", {})
    if rev.get("estado") == "rechazada":
        sys.exit(f"«{pid}» fue revisada y rechazada: {rev.get('nota') or 'no es segura'}.")
    if rev.get("estado") == "revisada":
        commit, huellas = rev["commit"], rev["huellas"]
    elif sin_revisar:
        commit, huellas = e["commit"], e["huellas"]
        print(f"⚠️  «{pid}» aún NO está revisada por Pieza. La instalas bajo tu responsabilidad (commit {commit[:7]} de {e['repo']}).")
    else:
        sys.exit(f"«{pid}» aún no está revisada. Si confías en {e['repo']}, agrégala con --sin-revisar (bajo tu responsabilidad).")
    cache = cache or os.path.join(os.path.expanduser("~"), ".cache", "pieza", "comunidad")
    carpeta = os.path.join(cache, f"{pid}@{commit}")
    for ruta, esperada in huellas.items():
        if not ruta_segura(ruta):
            sys.exit(f"Ruta rara en el catálogo: {ruta!r}")
        datos = red.archivo(e["repo"], commit, ruta)
        if sha(datos) != esperada:
            sys.exit(f"La huella de {ruta} no coincide con la {'revisada' if rev.get('estado') == 'revisada' else 'registrada'}: no instalo nada.")
        destino = os.path.join(carpeta, ruta)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(datos)
    return carpeta, {"repo": e["repo"], "commit": commit, "revision": rev.get("estado", "sin-revisar")}


def listar():
    for e in leer()["piezas"]:
        marca = {"revisada": "✓ revisada", "rechazada": "✗ rechazada"}.get(e["revision"].get("estado"), "· sin revisar")
        print(f"{e['id']:20} {marca:14} {e['repo']}@{e['commit'][:7]}  {e['pieza'].get('descripcion', '')[:80]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["buscar"]:
        print("\n".join(buscar()) or "Sin cambios.")
    elif a[:1] == ["listar"]:
        listar()
    elif len(a) >= 3 and a[0] == "revisar":
        revisar(a[1], a[2], " ".join(a[3:]))
    else:
        print(__doc__)
        sys.exit(2)

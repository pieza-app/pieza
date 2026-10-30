#!/usr/bin/env python3
"""Catálogo de la comunidad: piezas que viven en repos de otras personas y crece solo. Solo biblioteca estándar.

  comunidad.py buscar                        Busca repos públicos con el topic «pieza-comunidad», valida su pieza.json y sus
                                             archivos, y los suma (o actualiza) en comunidad/catalogo.json como «sin revisar».
                                             Lo corre el workflow «comunidad» una vez al día.
  comunidad.py proyectos                     Busca los repos públicos con el topic «hecho-con-pieza» (apps hechas con Pieza), lee
                                             su ícono (validado) y los deja en comunidad/proyectos.json; los nuevos, «sin revisar».
  comunidad.py listar                        Lo que hay (piezas y proyectos), con su estado de revisión.
  comunidad.py revisar <id> aprobar|rechazar <commit> [nota]
                                             Quien mantiene Pieza marca como revisado (o rechazado) el commit que LEYÓ (si el
                                             catálogo ya apunta a otro, no hace nada). Lo revisado queda fijado a ese commit y a la
                                             huella de cada archivo: es lo único que se instala como seguro. Un rechazo es del repo:
                                             sigue rechazado aunque cambie, hasta que alguien lo apruebe.
  comunidad.py proyecto <dueño/repo> aprobar|rechazar [nota]
                                             Marca un proyecto como aprobado por la comunidad (o lo saca de la página). Se aprueba
                                             el proyecto, no un commit: si cambia su ícono, sigue aprobado (el ícono siempre se
                                             vuelve a validar).

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
import icono as I  # noqa: E402

CATALOGO = os.path.join(BASE, "comunidad", "catalogo.json")
PROYECTOS = os.path.join(BASE, "comunidad", "proyectos.json")
TOPIC = "pieza-comunidad"
TOPIC_PROYECTOS = "hecho-con-pieza"
#: Dónde se busca el ícono de un proyecto si su app.json no dice «icono».
ICONOS_PROYECTO = ("docs/favicon.svg", "favicon.svg", "ui/favicon.svg", "docs/img/icono.svg", "icono.svg")
MAXIMO_ARCHIVO = 512 * 1024
MAXIMO_ARCHIVOS = 40
REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
#: Lo que se copia del pieza.json al catálogo (lo que necesitan la página, la ficha y el creador).
CAMPOS = ("id", "version", "estado", "nombre", "icono", "categoria", "descripcion", "recomendar", "requiere", "compatible", "plataformas",
          "pantallas", "permisos", "red", "red_nota", "tareas_persona", "archivos", "config", "acciones", "textos", "cambios")
ESTADOS = ("sin-revisar", "revisada", "rechazada")
ESTADOS_PROYECTO = ("sin-revisar", "revisado", "rechazado")


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
    try:
        errores += [e for e in P.errores_pieza(pid, p, oficiales, carpeta=None) if not e.startswith("falta el archivo")]
    except Exception as e:  # noqa: BLE001 — un pieza.json raro nunca tumba el catálogo de los demás
        errores.append(f"pieza.json con una forma que no entiendo: {type(e).__name__}")
    if errores:
        return None, {}, errores
    huellas = {"pieza.json": sha(crudo)}
    svg = ""
    if isinstance(p.get("icono"), str) and ruta_segura(p["icono"]) and p["icono"].endswith(".svg"):
        try:
            datos = red.archivo(repo, commit, p["icono"])
            svg = datos.decode("utf-8")
            errores += [f"ícono: {x}" for x in I.errores(svg, solo_current=True)]
            huellas[p["icono"]] = sha(datos)
        except Exception as e:  # noqa: BLE001
            errores.append(f"no pude leer el ícono {p['icono']}: {e}")
    for origen in archivos:
        if not ruta_segura(origen):
            errores.append(f"ruta rara en archivos: {origen!r}")
            continue
        try:
            huellas[origen] = sha(red.archivo(repo, commit, origen))
        except Exception as e:  # noqa: BLE001
            errores.append(f"no pude bajar {origen}: {e}")
    salida = {k: p[k] for k in CAMPOS if k in p}
    salida["icono_svg"] = svg
    return salida, huellas, errores


def buscar_repos(red, topic):
    """Todos los repos públicos con el topic (de a 100). completo=False si GitHub dijo que la búsqueda quedó incompleta."""
    repos, completo, pagina = [], True, 1
    while len(repos) < 1000:
        q = urllib.parse.urlencode({"q": f"topic:{topic} is:public fork:false archived:false", "sort": "updated",
                                    "per_page": 100, "page": pagina})
        d = red.json(f"https://api.github.com/search/repositories?{q}")
        if not isinstance(d, dict) or d.get("incomplete_results"):
            completo = False
        items = (d.get("items") if isinstance(d, dict) else None) or []
        repos += [r for r in items if isinstance(r, dict) and isinstance(r.get("full_name"), str) and REPO.match(r["full_name"])]
        if len(items) < 100:
            break
        pagina += 1
    return repos, completo


def se_puede_quitar(antes, encontrados, completo):
    """Solo se quita lo que desapareció si la búsqueda fue completa y no cayó de golpe (un error de GitHub no borra revisiones)."""
    return completo and (antes < 4 or encontrados >= antes // 2)


def buscar(red=None, hoy=None):
    """Recorre los repos con el topic y deja el catálogo al día. Devuelve un resumen de lo que cambió."""
    red = red or Red()
    hoy = hoy or datetime.date.today().isoformat()
    cat = leer()
    oficiales = P.todas()
    previas = {e["repo"]: e for e in cat["piezas"]}
    ocupados = {e["id"]: e["repo"] for e in cat["piezas"]}
    repos, completo = buscar_repos(red, TOPIC)
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
        try:
            p, huellas, errores = validar_remota(repo, commit, red, oficiales, ocupados)
        except Exception as e:  # noqa: BLE001
            p, huellas, errores = None, {}, [f"error al validar: {type(e).__name__}"]
        if errores:
            resumen.append(f"✗ {repo}: " + "; ".join(errores[:5]))
            if anterior:  # un cambio malo no borra lo que ya estaba: queda la versión anterior (y su revisión)
                nuevas.append(anterior)
            continue
        rev = dict((anterior or {}).get("revision", {"estado": "sin-revisar"}))
        if (anterior or {}).get("repo") and rev.get("estado") == "rechazada":
            pass  # un rechazo es del repo: no vuelve solo a la página
        elif rev.get("estado") == "revisada" and rev.get("huellas") != huellas:
            # Cambió el código: lo nuevo queda sin revisar, pero lo último revisado sigue siendo lo que se instala como seguro.
            rev = {"estado": "sin-revisar", "ultima_revisada": {k: rev[k] for k in ("commit", "huellas", "fecha") if k in rev}}
        elif rev.get("estado") == "sin-revisar" and rev.get("ultima_revisada", {}).get("huellas") == huellas:
            rev = {"estado": "revisada", **rev["ultima_revisada"]}  # volvió a lo que ya se revisó
        entrada = {"id": p["id"], "repo": repo, "commit": commit, "encontrada": (anterior or {}).get("encontrada", hoy),
                   "actualizada": hoy, "pieza": p, "huellas": huellas, "revision": rev}
        ocupados[p["id"]] = repo
        nuevas.append(entrada)
        cambio = True
        resumen.append(("↑ " if anterior else "+ ") + f"{p['id']} ({repo}) → {rev['estado']}")
    quitadas = set(previas) - {e["repo"] for e in nuevas}
    if quitadas and not se_puede_quitar(len(previas), len(repos), completo):
        resumen.append(f"! la búsqueda vino incompleta o cayó de golpe: no quito {len(quitadas)} pieza(s)")
        nuevas += [previas[r] for r in quitadas]
        quitadas = set()
    for repo in quitadas:
        cambio = True
        resumen.append(f"− {previas[repo]['id']} ({repo}): ya no tiene el topic o no existe")
    if cambio:
        cat["piezas"] = nuevas
        guardar(cat)
    return resumen


def revisar(pid, veredicto, commit, nota="", hoy=None):
    cat = leer()
    e = next((x for x in cat["piezas"] if x["id"] == pid), None)
    if not e:
        sys.exit(f"No hay una pieza de la comunidad «{pid}».")
    estado = {"aprobar": "revisada", "rechazar": "rechazada"}.get(veredicto)
    if not estado:
        sys.exit("El veredicto es aprobar o rechazar.")
    if not re.match(r"^[0-9a-f]{7,40}$", commit or "") or not e["commit"].startswith(commit):
        sys.exit(f"El catálogo apunta a {e['commit'][:12]}, no a lo que revisaste ({commit}). Revisa ese commit y vuelve a dar"
                 " el veredicto con su sha.")
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
    elif rev.get("ultima_revisada") and not sin_revisar:
        commit, huellas = rev["ultima_revisada"]["commit"], rev["ultima_revisada"]["huellas"]
        print(f"«{pid}» tiene cambios sin revisar: instalo la última versión revisada ({commit[:7]}).")
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
    revisado = rev.get("estado") == "revisada" or (rev.get("ultima_revisada", {}).get("commit") == commit)
    return carpeta, {"repo": e["repo"], "commit": commit, "revision": "revisada" if revisado else "sin-revisar"}


# ── Proyectos hechos con Pieza ───────────────────────────────────────────────────────────────────────────────────────────────

def leer_proyectos():
    return P.leer(PROYECTOS, {"formato": 1, "topic": TOPIC_PROYECTOS, "proyectos": []})


def guardar_proyectos(reg):
    os.makedirs(os.path.dirname(PROYECTOS), exist_ok=True)
    reg["proyectos"].sort(key=lambda e: e["repo"].lower())
    P.escribir(PROYECTOS, reg)


def texto(v, maximo):
    """Texto de afuera: solo string, sin caracteres de control y acotado. La página lo pone con textContent, nunca como HTML."""
    return re.sub(r"[\x00-\x1f\x7f]", " ", v).strip()[:maximo] if isinstance(v, str) else ""


def https(v):
    v = texto(v, 300)
    p = urllib.parse.urlsplit(v)
    return v if p.scheme == "https" and p.netloc and not p.username else ""


def icono_proyecto(repo, commit, red):
    """(svg, ruta) del ícono del proyecto: el que dice su app.json («icono») o el primero de ICONOS_PROYECTO que pase la
    validación. ("", "") si no tiene uno válido: la página muestra una pieza genérica."""
    rutas = []
    try:
        app = json.loads(red.archivo(repo, commit, "app.json"))
        if isinstance(app, dict) and isinstance(app.get("icono"), str) and app["icono"].endswith(".svg") and ruta_segura(app["icono"]):
            rutas.append(app["icono"])
    except Exception:  # noqa: BLE001
        pass
    for ruta in rutas + [r for r in ICONOS_PROYECTO if r not in rutas]:
        try:
            svg = red.archivo(repo, commit, ruta).decode("utf-8")
        except Exception:  # noqa: BLE001
            continue
        if not I.errores(svg):
            return svg, ruta
    return "", ""


def buscar_proyectos(red=None, hoy=None):
    """Recorre los repos con el topic «hecho-con-pieza» y deja comunidad/proyectos.json al día. Devuelve lo que cambió."""
    red = red or Red()
    hoy = hoy or datetime.date.today().isoformat()
    reg = leer_proyectos()
    previos = {e["repo"]: e for e in reg["proyectos"]}
    repos, completo = buscar_repos(red, TOPIC_PROYECTOS)
    nuevos, resumen = [], []
    for r in repos:
        repo = r["full_name"]
        anterior = previos.get(repo, {})
        rama = urllib.parse.quote(str(r.get("default_branch") or "main"))
        try:
            commit = red.json(f"https://api.github.com/repos/{repo}/commits/{rama}").get("sha", "")
        except Exception:  # noqa: BLE001
            commit = ""
        svg, ruta = (anterior.get("icono_svg", ""), anterior.get("icono", ""))
        if COMMIT.match(commit) and commit != anterior.get("commit"):
            svg, ruta = icono_proyecto(repo, commit, red)
        entrada = {"repo": repo, "nombre": texto(r.get("name"), 80) or repo.split("/")[1],
                   "descripcion": texto(r.get("description"), 280), "url": f"https://github.com/{repo}",
                   "pagina": https(r.get("homepage")), "commit": commit if COMMIT.match(commit) else anterior.get("commit", ""),
                   "icono": ruta, "icono_svg": svg, "encontrado": anterior.get("encontrado", hoy),
                   "actualizado": texto(r.get("pushed_at"), 25),
                   "revision": anterior.get("revision", {"estado": "sin-revisar"})}
        if entrada["revision"].get("estado") == "revisado" and any(entrada[k] != anterior.get(k) for k in ("nombre", "pagina")):
            # Lo aprobado fue ese nombre y esa página: si cambian, se vuelve a mirar (un enlace no puede cambiar a escondidas).
            entrada["revision"] = {"estado": "sin-revisar", "antes": "revisado"}
            resumen.append(f"! {repo}: cambió su nombre o su página → vuelve a «sin revisar»")
        if not anterior:
            resumen.append(f"+ {repo} → sin revisar")
        elif {k: v for k, v in entrada.items() if k != "actualizado"} != {k: v for k, v in anterior.items() if k != "actualizado"}:
            resumen.append(f"↑ {repo}")
        nuevos.append(entrada)
    quitados = set(previos) - {e["repo"] for e in nuevos}
    if quitados and not se_puede_quitar(len(previos), len(repos), completo):
        resumen.append(f"! la búsqueda vino incompleta o cayó de golpe: no quito {len(quitados)} proyecto(s)")
        nuevos += [previos[r] for r in quitados]
        quitados = set()
    for repo in quitados:
        resumen.append(f"− {repo}: ya no tiene el topic o no existe")
    if nuevos != reg["proyectos"]:
        reg["proyectos"] = nuevos
        guardar_proyectos(reg)
    return resumen


def revisar_proyecto(repo, veredicto, nota="", hoy=None):
    reg = leer_proyectos()
    e = next((x for x in reg["proyectos"] if x["repo"].lower() == repo.lower()), None)
    if not e:
        sys.exit(f"No hay un proyecto «{repo}». Corre primero: comunidad.py proyectos")
    estado = {"aprobar": "revisado", "rechazar": "rechazado"}.get(veredicto)
    if not estado:
        sys.exit("El veredicto es aprobar o rechazar.")
    e["revision"] = {"estado": estado, "fecha": hoy or datetime.date.today().isoformat(), "nota": texto(nota, 300)}
    guardar_proyectos(reg)
    print(f"{e['repo']}: {estado}")


def listar():
    for e in leer()["piezas"]:
        marca = {"revisada": "✓ revisada", "rechazada": "✗ rechazada"}.get(e["revision"].get("estado"), "· sin revisar")
        print(f"{e['id']:20} {marca:14} {e['repo']}@{e['commit'][:7]}  {e['pieza'].get('descripcion', '')[:80]}")
    for e in leer_proyectos()["proyectos"]:
        marca = {"revisado": "✓ aprobado", "rechazado": "✗ rechazado"}.get(e["revision"].get("estado"), "· sin revisar")
        print(f"{e['repo']:34} {marca:14} {'ícono ✓' if e.get('icono_svg') else 'sin ícono'}  {e.get('descripcion', '')[:60]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["buscar"]:
        print("\n".join(buscar()) or "Sin cambios.")
    elif a[:1] == ["proyectos"]:
        print("\n".join(buscar_proyectos()) or "Sin cambios.")
    elif len(a) >= 3 and a[0] == "proyecto":
        revisar_proyecto(a[1], a[2], " ".join(a[3:]))
    elif a[:1] == ["listar"]:
        listar()
    elif len(a) >= 4 and a[0] == "revisar":
        revisar(a[1], a[2], a[3], " ".join(a[4:]))
    else:
        print(__doc__)
        sys.exit(2)

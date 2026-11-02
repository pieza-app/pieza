#!/usr/bin/env python3
"""plantillas — llena los archivos que una pieza GENERA desde app.json (pieza.json → «generar»). Solo biblioteca estándar.

Una plantilla es un archivo de texto con marcas `{{…}}`. Es **solo datos**: no ejecuta nada de la pieza ni de la app (así «Pieza
al día» puede leer las piezas nuevas sin ejecutar su código). La sintaxis, entera:

  {{ruta}}                     El valor (app.id, nombre, piezas.host-mac…). Un texto solo pasa si es «seguro» (sin comillas,
                               $, `, \\, <, >, &, {, }, |, ; ni saltos de línea); si no, la plantilla tiene que decir cómo
                               escaparlo con un filtro. Si la ruta no existe, es un error (así un error de tipeo no pasa callado).
  {{ruta|filtro|filtro}}       Filtros, en orden. Para escapar: xml, json (también < > & U+2028 U+2029: sirve en un <script>),
                               yaml, sh. Para transformar: ascii, minus, mayus. Para validar (fallan si no calza): https,
                               sha256, nombre, ruta, version, id, color (CSS: #rgb, #rrggbb, #rrggbbaa, rgb()/hsl() con
                               números), y linea (texto libre de una línea, solo donde nada se interpreta: un heredoc entre
                               comillas, Markdown).
  {{#si ruta}}…{{#sino}}…{{/si}}   Si el valor existe y no está vacío (false, 0, "", [], {} y lo que falta cuentan como no).
  {{#no ruta}}…{{/no}}         Al revés.
  {{#cada ruta como x}}…{{/cada}}  Por cada elemento de una lista; adentro, {{x}} o {{x.campo}}. También {{#si x_ultimo}}.
  {{! comentario }}            No sale en el archivo.

`${{ … }}` (las expresiones de GitHub Actions) NO es una marca: queda tal cual. Pero un VALOR insertado nunca puede traer
`${{`, `{{` ni `}}` (error): así un dato de app.json no se vuelve una expresión en un workflow. Una línea que solo tiene una marca de bloque
(`{{#si …}}`, `{{/si}}`, `{{#cada …}}`…) desaparece entera, así el archivo generado queda limpio.

Uso desde Python: `plantillas.llenar(texto, contexto)` → texto, o `PlantillaMala` con la línea. `plantillas.contexto(app_json,
piezas=…, datos=…)` arma el contexto común (ver `docs/enchufe.md`, «Plantillas»). Desde la terminal:

  plantillas.py llenar <plantilla> <app.json>     Imprime el resultado (para probar una plantilla).
  plantillas.py contexto <app.json>               Imprime el contexto en JSON.
"""
import json
import os
import re
import shlex
import sys
import unicodedata


class PlantillaMala(ValueError):
    """Una plantilla con un error (sintaxis, un valor que falta o que no pasa un filtro). Dice la línea."""


# ── Valores ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

#: Lo que se puede insertar sin filtro: letras (con tildes), números, espacio y signos que no cambian el sentido en shell entre
#: comillas dobles, YAML entre comillas, XML, JSON, Swift o NSIS. Lo demás necesita un filtro que lo escape.
SEGURO = re.compile(r"^[^\"'`$\\<>&{}|;\x00-\x1f\x7f]*$")
FALTA = object()


def _ascii(v):
    t = unicodedata.normalize("NFKD", str(v))
    return re.sub(r"[^A-Za-z0-9]", "", "".join(c for c in t if not unicodedata.combining(c)))


def _validar(nombre, patron):
    def f(v):
        if not isinstance(v, str) or not re.fullmatch(patron, v):
            raise ValueError(f"«{v}» no es {nombre}")
        return v
    return f


def _yaml(v):
    # Un texto JSON es un escalar YAML válido entre comillas dobles (y una lista o un objeto JSON, un flujo YAML).
    return json.dumps(v, ensure_ascii=False)


def _json(v):
    # JSON que también sirve dentro de un <script> (ld+json o JS) y en HTML: «</script>», «<!--» y «&…;» nunca salen tal
    # cual, y U+2028/U+2029 (fin de línea en JS antiguo) tampoco. Sigue siendo el mismo JSON.
    return (json.dumps(v, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


_NUM = r"\s*-?(?:\d+(?:\.\d+)?|\.\d+)(?:%|deg)?\s*"
#: Un color de CSS sin nada más: #rgb, #rgba, #rrggbb, #rrggbbaa, rgb()/rgba()/hsl()/hsla() con números (con comas o espacios).
COLOR = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|(?:rgba?|hsla?)\("
                   + _NUM + r"(?:[,\s/]" + _NUM + r"){2,3}\)")


def _escalar(f):
    def g(v):
        if isinstance(v, (dict, list)):
            raise ValueError("es una lista u objeto: usa |json o recórrelo con #cada")
        return f(v)
    return g


FILTROS = {
    "xml": lambda v: _escalar(str)(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"),
    "json": _json,
    "yaml": _yaml,
    "sh": lambda v: shlex.quote(_escalar(str)(v)),
    "ascii": _ascii,
    "minus": lambda v: str(v).lower(),
    "mayus": lambda v: str(v).upper(),
    "https": _validar("una dirección https", r"https://[A-Za-z0-9.-]+(/[A-Za-z0-9._~%/+=@:,-]*)?(\?[A-Za-z0-9._~%/+=&-]*)?"),
    "sha256": _validar("una huella SHA-256 (64 hex)", r"[0-9a-f]{64}"),
    "nombre": _validar("un nombre simple (letras, números, . _ -)", r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}"),
    "ruta": _validar("una ruta relativa simple", r"(?!.*(^|/)\.\.?(/|$))[A-Za-z0-9_][A-Za-z0-9._/-]{0,200}"),
    "version": _validar("una versión X.Y.Z", r"\d+\.\d+\.\d+"),
    "id": _validar("un id (minúsculas y números)", r"[a-z][a-z0-9]{0,30}"),
    "color": _validar("un color (#rgb, #rrggbb, #rrggbbaa, rgb(), rgba(), hsl() con números)", COLOR.pattern),
    # Un texto libre de una línea, para donde nada se interpreta (un heredoc entre comillas, un comentario, Markdown).
    "linea": _validar("una línea de texto (sin saltos ni caracteres de control)", r"[^\x00-\x1f\x7f]{0,500}"),
}
#: Los filtros que dejan el valor listo para insertar (escapan): después de ellos no se exige «seguro».
ESCAPAN = {"xml", "json", "yaml", "sh", "linea"}
VALIDAN = {"https", "sha256", "nombre", "ruta", "version", "id", "color", "ascii"}


def buscar(ctx, ruta):
    v = ctx
    for parte in ruta.split("."):
        if isinstance(v, dict) and parte in v:
            v = v[parte]
        elif isinstance(v, list) and parte.isdigit() and int(parte) < len(v):
            v = v[int(parte)]
        else:
            return FALTA
    return v


def verdad(v):
    return v is not FALTA and v is not None and v is not False and v != 0 and v != "" and v != [] and v != {}


# ── Sintaxis ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

MARCA = re.compile(r"(?<!\$)\{\{(.*?)\}\}", re.S)
#: Una línea con solo una marca de bloque (o un comentario) desaparece entera.
SOLA = re.compile(r"(?m)^[ \t]*((?<!\$)\{\{\s*(?:[#/!][^}]*)\}\})[ \t]*\r?\n")
RUTA = r"[A-Za-z_][\w-]*(?:\.[\w-]+)*"


def _partir(texto):
    """[(tipo, valor, línea)]: ("texto", …), ("valor", (ruta, filtros)), ("si"/"no"/"cada", …), ("sino"), ("fin", tipo)."""
    texto = SOLA.sub(r"\1", texto)
    partes, pos = [], 0
    for m in MARCA.finditer(texto):
        linea = texto.count("\n", 0, m.start()) + 1
        if m.start() > pos:
            partes.append(("texto", texto[pos:m.start()], linea))
        pos = m.end()
        dentro = m.group(1).strip()
        if dentro.startswith("!"):
            continue
        if dentro == "#sino":
            partes.append(("sino", None, linea))
        elif re.fullmatch(r"/(si|no|cada)", dentro):
            partes.append(("fin", dentro[1:], linea))
        elif re.fullmatch(rf"#(si|no)\s+{RUTA}", dentro):
            tipo, ruta = dentro[1:].split(None, 1)
            partes.append((tipo, ruta.strip(), linea))
        elif re.fullmatch(rf"#cada\s+{RUTA}\s+como\s+[A-Za-z_]\w*", dentro):
            _, ruta, _, nombre = dentro.split()
            partes.append(("cada", (ruta, nombre), linea))
        elif re.fullmatch(rf"{RUTA}(\s*\|\s*[a-z0-9]+)*", dentro):
            trozos = [x.strip() for x in dentro.split("|")]
            for f in trozos[1:]:
                if f not in FILTROS:
                    raise PlantillaMala(f"línea {linea}: filtro desconocido «{f}» (hay: {', '.join(sorted(FILTROS))})")
            partes.append(("valor", (trozos[0], trozos[1:]), linea))
        else:
            raise PlantillaMala(f"línea {linea}: marca rara «{{{{{dentro}}}}}»")
    if pos < len(texto):
        partes.append(("texto", texto[pos:], texto.count("\n", 0, pos) + 1))
    return partes


def _arbol(partes):
    """Anida los bloques: [nodo] con nodo = ("texto", t) | ("valor", …) | (tipo, arg, hijos, sino, línea)."""
    raiz, pila = [], []
    actual = raiz
    for tipo, valor, linea in partes:
        if tipo in ("texto", "valor"):
            actual.append((tipo, valor, linea))
        elif tipo in ("si", "no", "cada"):
            nodo = [tipo, valor, [], None, linea]
            actual.append(nodo)
            pila.append((nodo, actual))
            actual = nodo[2]
        elif tipo == "sino":
            if not pila or pila[-1][0][0] not in ("si", "no") or pila[-1][0][3] is not None:
                raise PlantillaMala(f"línea {linea}: {{{{#sino}}}} fuera de un {{{{#si}}}}")
            pila[-1][0][3] = []
            actual = pila[-1][0][3]
        else:  # fin
            if not pila or pila[-1][0][0] != valor:
                raise PlantillaMala(f"línea {linea}: {{{{/{valor}}}}} no cierra nada" + (f" (falta {{{{/{pila[-1][0][0]}}}}})" if pila else ""))
            nodo, actual = pila.pop()
    if pila:
        raise PlantillaMala(f"línea {pila[-1][0][4]}: falta cerrar {{{{#{pila[-1][0][0]}}}}}")
    return raiz


#: Lo que nunca puede traer un valor insertado (en cualquier parte, también dentro de una lista u objeto): `${{` sería una
#: expresión de GitHub Actions en un workflow generado, y `{{`/`}}` una marca a medias.
PROHIBIDO_EN_VALOR = ("${{", "{{", "}}")


def _con_marca(v):
    if isinstance(v, str):
        return next((x for x in PROHIBIDO_EN_VALOR if x in v), None)
    if isinstance(v, dict):
        return next((m for x in (*v.keys(), *v.values()) if (m := _con_marca(x))), None)
    if isinstance(v, list):
        return next((m for x in v if (m := _con_marca(x))), None)
    return None


def _render(nodos, ctx, salida):
    for n in nodos:
        if n[0] == "texto":
            salida.append(n[1])
        elif n[0] == "valor":
            (ruta, filtros), linea = n[1], n[2]
            v = buscar(ctx, ruta)
            if v is FALTA or v is None:
                raise PlantillaMala(f"línea {linea}: falta «{ruta}» (en app.json o en el contexto)")
            marca = _con_marca(v)
            if marca:
                raise PlantillaMala(f"línea {linea}: «{ruta}» trae «{marca}»: un dato no puede traer marcas de plantilla ni"
                                    " expresiones de GitHub Actions")
            escapado = False
            for f in filtros:
                try:
                    v = FILTROS[f](v)
                except ValueError as e:
                    raise PlantillaMala(f"línea {linea}: «{ruta}»: {e}") from None
                escapado = escapado or f in ESCAPAN
            if isinstance(v, bool):
                v = "true" if v else "false"
            if isinstance(v, (dict, list)) and not escapado:
                raise PlantillaMala(f"línea {linea}: «{ruta}» es una lista u objeto: usa |json o |yaml, o recórrelo con #cada")
            v = str(v)
            if not escapado and not SEGURO.match(v):
                raise PlantillaMala(f"línea {linea}: «{ruta}» trae signos que hay que escapar: usa un filtro (|sh, |xml, |json, |yaml)")
            salida.append(v)
        else:
            tipo, arg, hijos, sino, linea = n
            if tipo in ("si", "no"):
                cumple = verdad(buscar(ctx, arg))
                if tipo == "no":
                    cumple = not cumple
                _render(hijos if cumple else (sino or []), ctx, salida)
            else:
                ruta, nombre = arg
                lista = buscar(ctx, ruta)
                if not verdad(lista):
                    continue
                if not isinstance(lista, list):
                    raise PlantillaMala(f"línea {linea}: «{ruta}» no es una lista")
                for i, x in enumerate(lista):
                    _render(hijos, {**ctx, nombre: x, nombre + "_ultimo": i == len(lista) - 1,
                                    nombre + "_primero": i == 0}, salida)


def llenar(texto, ctx):
    """El texto de la plantilla con sus marcas llenas. `PlantillaMala` si algo no calza."""
    salida = []
    _render(_arbol(_partir(texto)), ctx, salida)
    r = "".join(salida)
    if MARCA.search(r):
        raise PlantillaMala("el resultado todavía tiene «{{»: un valor traía una marca")
    return r


def revisar(texto):
    """Errores de sintaxis de una plantilla (sin llenarla). Lista vacía si está bien."""
    try:
        _arbol(_partir(texto))
        return []
    except PlantillaMala as e:
        return [str(e)]


# ── El contexto común ────────────────────────────────────────────────────────────────────────────────────────────────────────

PLATAFORMAS = ("mac", "windows", "linux", "ios", "android")
ID = re.compile(r"^[a-z][a-z0-9]{0,30}$")
REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def contexto(app, piezas=(), datos=None):
    """Lo que ve una plantilla. `app` es app.json (validado aquí lo común); `piezas`, las instaladas; `datos`, los archivos de
    datos de la app que pide la pieza («datos_app»). Ver docs/enchufe.md, «Plantillas»."""
    if not isinstance(app, dict) or not isinstance(app.get("id"), str) or not ID.match(app["id"]):
        raise PlantillaMala("app.json: «id» en minúsculas, letras y números")
    aid = app["id"]
    nombre = app.get("nombre") if isinstance(app.get("nombre"), str) else aid.capitalize()
    if not nombre or len(nombre) > 40 or not SEGURO.match(nombre):
        raise PlantillaMala("app.json: «nombre» es un nombre corto sin comillas ni signos raros")
    plataformas = [x for x in (app.get("plataformas") or PLATAFORMAS) if x in PLATAFORMAS]
    repo = app.get("repo")
    if not (isinstance(repo, str) and REPO.match(repo)):
        repo = f"{aid}-app/{aid}"
    version = app.get("version") if isinstance(app.get("version"), str) and VERSION.match(app["version"]) else "0.1.0"
    nombre_ascii = _ascii(nombre) or aid.capitalize()
    datos_app = app.get("datos", "sistema")
    # Dónde guarda la app sus datos en el Mac, relativo a la casa (la misma regla que nucleo.carpeta_datos): ahí build.sh deja
    # «desarrollo» para la pieza «actualizaciones».
    if isinstance(datos_app, dict) and isinstance(datos_app.get("carpeta"), str) and datos_app["carpeta"].startswith("~/"):
        datos_mac = datos_app["carpeta"][2:]
    elif datos_app == "visible":
        datos_mac = f"{nombre}/.{aid}"
    else:
        datos_mac = f"Library/Application Support/{nombre}"
    if not SEGURO.match(datos_mac) or ".." in datos_mac.split("/"):
        raise PlantillaMala("app.json: «datos.carpeta» raro")
    ctx = {
        "app": app,
        "id": aid, "ID": aid.upper(), "nombre": nombre, "nombre_ascii": nombre_ascii, "version": version,
        "repo": repo, "dueno": repo.split("/")[0], "repo_nombre": repo.split("/")[1],
        "web": f"https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/",
        "bundle": f"app.{aid}.mac", "bundle_escritorio": f"app.{aid}.escritorio",
        "datos_mac": datos_mac,
        "plataformas": plataformas,
        **{p: p in plataformas for p in PLATAFORMAS},
        "escritorio": "windows" in plataformas or "linux" in plataformas,
        "mac_o_linux": "mac" in plataformas or "linux" in plataformas,
        "movil": "ios" in plataformas or "android" in plataformas,
        "piezas": {p: True for p in piezas},
        "datos": datos or {},
    }
    return ctx


def main(a):
    if len(a) == 3 and a[0] in ("llenar", "contexto") or len(a) == 2 and a[0] == "contexto":
        with open(a[-1], encoding="utf-8") as f:
            ctx = contexto(json.load(f))
        if a[0] == "contexto":
            print(json.dumps(ctx, ensure_ascii=False, indent=1))
        else:
            with open(a[1], encoding="utf-8") as f:
                sys.stdout.write(llenar(f.read(), ctx))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except PlantillaMala as e:
        sys.exit(f"✗ {e}")

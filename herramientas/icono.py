"""Validar un ícono SVG que viene de afuera: solo formas de dibujo, nada que se ejecute o cargue algo. Solo biblioteca estándar.

Reglas (las mismas para piezas oficiales, piezas de la comunidad y proyectos):
- hasta 8 KB, raíz <svg> con viewBox, sin DOCTYPE ni entidades;
- solo las etiquetas de FORMAS y los atributos de ATRIBUTOS (nada de <script>, <style>, <image>, <use>, <foreignObject>, href,
  style, on*…);
- colores: none, currentColor o #hex. Una pieza se dibuja con currentColor (la página la pinta con su color); un proyecto puede
  traer sus colores.
"""
import re
import xml.etree.ElementTree as ET

MAXIMO = 8 * 1024
NS = "{http://www.w3.org/2000/svg}"
FORMAS = {"svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "title", "defs", "linearGradient",
          "radialGradient", "stop", "clipPath"}
ATRIBUTOS = {"xmlns", "viewBox", "width", "height", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
             "stroke-dasharray", "stroke-opacity", "fill-opacity", "fill-rule", "clip-rule", "opacity", "d", "cx", "cy", "r", "rx",
             "ry", "x", "y", "x1", "y1", "x2", "y2", "points", "transform", "id", "offset", "stop-color", "stop-opacity",
             "gradientUnits", "gradientTransform", "clip-path", "role", "aria-hidden", "aria-label", "version"}
COLOR = re.compile(r"^(none|currentColor|#[0-9a-fA-F]{3,8}|url\(#[A-Za-z][\w-]{0,40}\))$")
NUMEROS = re.compile(r"^[0-9eE.,\s+\-a-zA-Z()#%]*$")


def errores(texto, solo_current=False):
    """Lista de problemas (vacía = válido). solo_current: los colores tienen que ser currentColor o none (íconos de piezas)."""
    if not isinstance(texto, str) or not texto.strip():
        return ["el ícono está vacío"]
    if len(texto.encode()) > MAXIMO:
        return [f"el ícono pesa más de {MAXIMO // 1024} KB"]
    if "<!DOCTYPE" in texto.upper() or "<!ENTITY" in texto.upper() or "<?xml-stylesheet" in texto:
        return ["el ícono no puede traer DOCTYPE, entidades ni hojas de estilo"]
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as e:
        return [f"el ícono no es un SVG válido: {e}"]
    e = []
    if raiz.tag not in ("svg", NS + "svg") or not raiz.get("viewBox"):
        e.append("la raíz tiene que ser <svg> con viewBox")
    for nodo in raiz.iter():
        etiqueta = nodo.tag.replace(NS, "")
        if etiqueta not in FORMAS:
            e.append(f"etiqueta no permitida: <{etiqueta}>")
        for atributo, valor in nodo.attrib.items():
            nombre = re.sub(r"^\{[^}]+\}", "", atributo)
            if nombre not in ATRIBUTOS:
                e.append(f"atributo no permitido: {nombre}")
            elif nombre in ("fill", "stroke", "stop-color"):
                if not COLOR.match(valor.strip()) or (solo_current and valor.strip() not in ("none", "currentColor")):
                    e.append(f"color no permitido en {nombre}: {valor[:30]}" + (" (una pieza usa currentColor)" if solo_current else ""))
            elif "url(" in valor and nombre != "clip-path" or "javascript" in valor.lower() or not NUMEROS.match(valor):
                e.append(f"valor raro en {nombre}")
    return sorted(set(e))[:10]

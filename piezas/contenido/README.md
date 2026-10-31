# Pieza «contenido» — leer lo que la persona agrega

```python
import contenido
try:
    r = contenido.extraer_archivo(ruta)          # o extraer(nombre, datos) con bytes
    # {texto (Markdown sencillo), titulo, formato, recortado}
except contenido.NoSePuede as e:
    responder(salida, e.como_dict())             # {ok: false, codigo, plantilla, valores: {app}, error}
capitulos = contenido.partir_capitulos(r["texto"])   # [{n, titulo, archivo: "01-el-comienzo.md", texto}], sin IA
contenido.titulo_de(texto, nombre)
```
- `.md`, `.txt`, `.pdf` (con texto; uno escaneado o con clave da una frase clara), `.docx`, `.odt`, `.epub`, `.html`. `.doc`,
  `.pages`, `.rtf`, presentaciones y planillas: «guárdalo como…» (`formato`).
- Topes: 25 MB por archivo; un zip (.docx/.odt/.epub) con hasta 5.000 partes, 40 MB por parte y 80 MB en total, **contados al
  descomprimir**; un PDF, 60 MB descomprimidos en total; 3 millones de caracteres de texto (`recortado`).
- XML sin `DOCTYPE` ni `ENTITY` en ninguna parte (`raro`): nada de «mil millones de risas» ni entidades externas. Nada se ejecuta,
  ningún enlace se abre.
- Códigos: `grande`, `formato`, `desconocido`, `vacio`, `raro`, `danado`, `grande_adentro`, `no_pdf`, `pdf_clave`,
  `pdf_sin_texto`, `epub_indice`.

## Si la app ya tiene un `bin/contenido.py` propio
La pieza se instala en `bin/contenido.py` (los scripts la importan como `contenido`). Si la app ya tiene un módulo con ese
nombre, `pieza.py agregar contenido` **no copia nada** y lo explica: si la pieza salió de ese archivo (Esquema), pasa lo propio
a otro módulo y usa `--forzar`; si es otro módulo de la app, renómbralo (y sus `import`) antes de agregar la pieza.

## Pasar una app a esta pieza
**Esquema** (`bin/contenido.py`): queda en Esquema solo lo suyo —`detectar`,
`id_historia`, `enlace_ticket`, `solo_enlace`, `RE_*`, `SUBTIPOS`— en otro módulo (p. ej. `bin/detectar.py`), y `contenido.py`
pasa a ser la pieza. `NoSePuede(mensaje)` pasa a `NoSePuede(codigo)`: donde se mostraba `str(e)` la frase es la misma (con
«Esquema» en vez de nombrarlo fijo); para traducir, mandar `e.como_dict()`. Los textos en `en.json` ya vienen en la pieza.
**Repasa** (material en PDF o texto para la IA) y **Alcancía** (cartolas PDF, que tiene su propio `pdf.py` con posiciones:
no se reemplaza) pueden usarla para leer apuntes y documentos sin escribir otro lector.

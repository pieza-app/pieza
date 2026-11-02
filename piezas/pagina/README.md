# Pieza «pagina» — la página pública de la app, generada desde sus datos

La página de GitHub Pages (`docs/`) en español e inglés, sin escribir HTML: la app pone **lo suyo** en `docs/pagina.json` (la frase,
las funciones, la comparación, sus preguntas, las capturas, el color) y la pieza arma todo lo demás con lo que ya sabe Pieza.

```bash
python3 <pieza>/herramientas/pieza.py agregar pagina .     # copia lo fijo y escribe docs/pagina.json para completar (una vez)
# … completa docs/pagina.json …
python3 <pieza>/herramientas/pieza.py generar . pagina     # arma docs/index.html y lo demás (nunca pisa lo que la app cambió)
node herramientas/pagina_capturas.mjs capturas             # las capturas de docs/pagina.json → «capturas», desde la vista previa
node herramientas/pagina_capturas.mjs imagenes             # docs/img/compartir.png (1200×630) y docs/apple-touch-icon.png
node herramientas/pagina_capturas.mjs revisar              # es/en, 1280 y 390 px, claro y oscuro: la misma revisión que la de Pieza
```

## Qué genera (mecanismo de plantillas de Pieza: `docs/enchufe.md`, «Plantillas»)

| Archivo | Cómo |
|---|---|
| `docs/index.html` | Generado. Un solo HTML con los dos idiomas (`data-es`/`data-en`; el inglés con `?lang=en`, lo que eligió antes o el idioma del navegador). Sin scripts ni estilos en línea: CSP `script-src 'self'`. Title, description, canonical, `hreflang`, Open Graph y Twitter con `img/compartir.png`, y el JSON-LD `SoftwareApplication` + `FAQPage` **hecho de los mismos textos que se ven** (las preguntas visibles, en español y en el mismo orden). Descarga según el sistema con los nombres fijos de los Releases (`<Nombre>-macOS.zip`, `-Windows.exe`, `-Linux.AppImage`), demo en `/demo/` si `demo: true`, sello «Hecho con Pieza» (es/en) en el pie. |
| `docs/colores.css` | Generado: el acento de la app (`acento.claro`/`acento.oscuro`) sobre los tokens de «tema». |
| `docs/sitemap.xml` | Generado, con las dos versiones de idioma. |
| `.github/workflows/pagina.yml` | Generado: publica `docs/` (y `ui/` en `/demo/` si hay demo) en Pages. Actions fijadas por SHA, solo `contents: read` arriba y `pages`/`id-token` en el job que publica, `persist-credentials: false`. Como todo lo de `.github/`, nunca se actualiza solo. |
| `herramientas/org.github.io/robots.txt`, `index.html` | Generados, para el repo `<org>/<org>.github.io` (la raíz de la organización): `robots.txt` con el sitemap y una página que redirige a la app. Cópialos allá. |
| `docs/pagina.json` | Generado **una vez** con todo lo que hay que completar («La app: …»); desde ahí es de la app. |
| `docs/favicon.svg` | Generado una vez (un ícono genérico): cámbialo por el de la app. |
| `docs/pagina.js`, `docs/pagina.css`, `docs/tema.css`, `docs/sello*.svg` | Copiados (huella en `piezas.json`). `tema.css` es la misma de la pieza «tema». |
| `docs/pagina-comunes.json` | Copiado: **lo que ya sabe Pieza**. Qué pide y a qué se conecta cada pieza (`red`, `permisos`, `ia`) y las preguntas comunes ya escritas en es/en: cómo se actualiza (con o sin la pieza «actualizaciones»), «¿por qué mi computador dice que no puede verificar la app?» (los pasos de macOS 15 y/o Windows, según las plataformas), dónde están mis datos, qué IA uso (si tiene «ia»), permisos y costo. |
| `herramientas/pagina_capturas.mjs` | Copiado: servir como en Pages, capturas desde la vista previa (sin red, con hora fija si se pide, elegidas por datos), `compartir.png` y la revisión. |

**«Permisos e internet» sale solo de las piezas.** Si la app tiene «actualizaciones», «catalogo» o «transcribir», la página dice a
qué dominio sale cada una y para qué; con «ia», qué recibe tu IA. Los permisos que solo pide una pieza si la app usa algo (avisos y
Llavero de «host-mac», micrófono de «transcribir») van con `usa` de `docs/pagina.json`, y la pieza «contrato» revisa que `usa` diga lo
que el código usa. Lo propio de la app (otro dominio, otro permiso) va en `red` y `permisos`. Una prueba de Pieza
(`test_comunes_cubren_lo_que_piden_las_piezas`) falla si una pieza nueva sale a internet o pide un permiso y esta pieza no lo cuenta:
así la página nunca promete de más ni de menos.

## `docs/pagina.json`

Todo es texto plano en `{"es": "…", "en": "…"}` (se escapa). Lo que falta es un error al generar (dice qué).

| Campo | Qué |
|---|---|
| `titulo`, `descripcion` | Para buscadores (title ~60–70 caracteres, description ~155). |
| `frase`, `intro` | La portada. |
| `categoria` | `applicationCategory` de schema.org (`DeveloperApplication`, `MultimediaApplication`, `FinanceApplication`…). |
| `licencia`, `licencia_url` | `AGPL-3.0` y su enlace. |
| `acento` | `{"claro": "#rrggbb", "oscuro": "#rrggbb"}`. Con `--sobre-acento` (blanco en claro) tiene que pasar AA: `revisar` lo mide. |
| `descargas`, `demo` | `true`/`false`: el botón de descarga y la vista previa en `/demo/`. |
| `estado` | Opcional: un aviso bajo los botones («La versión para descargar llega pronto…»). |
| `datos` | La respuesta de «¿Dónde están mis datos?». |
| `usa` | `{"notificaciones", "llavero", "microfono"}`: lo que la app usa de verdad de sus piezas. |
| `funciones`, `pasos` | `[{titulo, texto}]`. |
| `comparacion` | `{"con": ["Otra app"], "filas": [{"que", "valores": [la app, cada otra]}]}` o `null`. |
| `capturas` | `[{archivo: "img/x.png", alt, ancho, alto, demo?: "?idioma=en#…", tema?: "claro"\|"oscuro", tocar?: ["selector"], hora?: "ISO"}]`. La primera va en la portada y en el JSON-LD. |
| `compartir` | Opcional: `{captura, frase}` para `img/compartir.png` (si no, la primera captura y la frase). |
| `preguntas` | `[{pregunta, respuesta}]`: las propias. Van antes de las comunes. |
| `red`, `permisos` | Lo propio de la app: `[{dominio, por}]` y `[{sistema: "Mac", nombre, por}]`. |
| `comunidad` | `[{titulo, texto, url (https)}]`. |

## Qué sigue escribiendo la IA a mano
Solo `docs/pagina.json` (los textos de la app), `docs/favicon.svg` y las capturas (con `pagina_capturas.mjs`). Lo propio de la página
que no cabe en los datos (una animación, una demo especial) va en un archivo de la app; `docs/index.html` deja de regenerarse si la app
lo cambia (`pieza.py estado` lo dice).

## Pruebas
`pruebas/test_pagina_contrato.py` (`Pagina`: sin marcas, JSON-LD = lo visible, workflow con las reglas, no pisa lo de la app, cubre
lo que piden las piezas, copias iguales) y `pruebas/pagina.mjs` (dos apps ficticias en Chromium: es/en, 1280 y 390 px, claro y
oscuro, sin errores ni CSP, sin textos sin traducir, contraste AA, el título en su idioma, solo lo que la app tiene).

## Revisar a mano
- En GitHub: activar Pages (Source: GitHub Actions) y ver que el workflow publique; abrir `https://<org>.github.io/<repo>/?lang=en`.
- Google Search Console y la vista previa al compartir (Open Graph) con la URL real.
- Mirar `docs/img/compartir.png` y las capturas antes de subirlas: datos ficticios, nada personal.
- Que el acento de la app pase AA en claro y oscuro (`pagina_capturas.mjs revisar`).

## Cómo la adoptan las apps de hoy
Opt-in: Esquema, Alcancía, Corta, Minuta, Graba y Repasa tienen su `docs/index.html` escrito a mano. Para pasar: `pieza.py agregar
pagina .` (no pisa su `index.html`: queda de la app), llevar sus textos a `docs/pagina.json`, borrar su `index.html` y correr
`pieza.py generar . pagina`. Lo que no cabe (el editor en vivo de Esquema, el video de Corta) queda en un archivo propio o espera a la
0.2 (secciones propias).

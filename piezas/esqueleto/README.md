# Pieza «esqueleto» — lo propio de una app nueva, andando desde el primer minuto

No se agrega a mano: la pone **`pieza.py crear`**, el comando que deja una app nueva entera de una vez.

```bash
python3 herramientas/pieza.py crear ../receta --id receta --nombre Receta --plataformas mac,windows,linux --piezas ia [--repo receta-app/receta]
cd ../receta && git init && bash pruebas/correr.sh          # en verde de una
cd ui && python3 -m http.server 8765                       # la vista previa: ?bienvenida (el idioma primero), ?idioma=en, ?tema=oscuro
```

`crear` = `iniciar` (`app.json`) + las piezas de siempre para esas plataformas (`ficha`: núcleo, interfaz, host de Mac y/o de
Electron, actualizaciones, bienvenida, empaquetado, página, contrato) + las pedidas + **esta pieza** + `github` al final, la acción
de ejemplo en `app.json` → `acciones`, `acciones.json` y todo lo generado. Al final imprime **qué le toca a la IA** (cada archivo con
sus `La app:`) y **qué le toca a la persona** (`tareas_persona` de las piezas). No toca una carpeta que ya tiene algo; el celular
todavía no (`host-movil` está por extraer).

## Qué escribe (una vez: desde ahí es de la app, sin huella; `actualizar` nunca lo toca)

| Archivo | Qué es |
|---|---|
| `ui/index.html` | Con la CSP de las apps (`script-src 'self'`, nada en línea) y las piezas de interfaz en orden. |
| `ui/app.js` | `crearHost` (vista previa con `simular` y las comunes), `i18n`, `tema`, `componentes`, `bienvenida` (el idioma primero y solo; «Elige tu IA» si tiene «ia»), una pantalla de ejemplo, Ajustes (idioma, apariencia, Tu IA, actualizaciones, Acerca de) y las respuestas (`estado`, `menu`, `ejemploListo`…). |
| `ui/app.css`, `ui/demo.json` | Lo propio sobre los tokens de «tema»; los datos ficticios de la vista previa. |
| `bin/ejemplo.py` | Un script con `nucleo.script`: el texto llega por archivo, nunca como argumento. Lo llama la acción **declarada** `ejemplo` de `app.json` (ningún código nativo). |
| `app/Sources/<Nombre>/<Nombre>App.swift` | (Mac) `Host.arrancar` con las actualizaciones. Lo nativo propio va aquí con `p.registrar`. |
| `escritorio/src/main.js` | (Windows/Linux) `crearHost` con las actualizaciones. Lo nativo propio, con `host.acciones.registrar`. |
| `pruebas/correr.sh` | Sintaxis, contrato del puente, `test_*.py`, la interfaz y la página en Chromium (si hay Playwright) y privacidad. Lo corre `revisar.yml`. |
| `pruebas/test_app.py`, `pruebas/interfaz.mjs`, `pruebas/contrato_app.py` | Python con HOME temporal; la interfaz con la CSP (sin errores, el idioma primero, nada sin traducir en inglés, 390 px, capturas con `CAPTURAS=`); lo propio del contrato (vacío). |
| `README.md` | Instalar en un comando, cómo está hecha, el sello «Hecho con Pieza». |

Las frases del esqueleto van con su inglés en `ui/idiomas/en.json` (`textos` de esta pieza). Lo marcado `La app:` (también en los
textos de ejemplo) es lo que la IA reemplaza.

## Lo que queda para la IA (medido, nov 2026)

Dos apps creadas con `crear` en un temporal (`pruebas/test_crear.py` las crea y corre sus pruebas):

| | Receta (Mac, Windows, Linux, con «ia») | Nota (solo Mac, sin IA) |
|---|---|---|
| Líneas que pone Pieza | 10.875 | 8.154 |
| · copiadas de las piezas (se actualizan) | 7.586 | 5.368 |
| · generadas desde `app.json` (se regeneran) | 1.168 | 812 |
| · documentos para completar (`AGENTS.md`, `CONTRIBUTING.md`…, `docs/pagina.json`) | 1.105 | 1.100 |
| · el esqueleto de esta pieza | 475 | 441 |
| · `app.json`, `piezas.json`, `acciones.json`, `en.json`, Pieza al día | 541 | 433 |
| Líneas marcadas `La app:` (lo que completa la IA) | 49 | 46 |

Lo demás que escribe la IA es lo propio de la app (reemplazar el ejemplo). Como referencia, lo que en Esquema se escribió a mano y
aquí ya viene: `pruebas/correr.sh` + `pruebas/contrato.py` (264 líneas; aquí la app pone un `contrato_app.py` de 7), `.github/` (535),
`docs/` (666 de HTML, JS, CSS y XML; aquí lo propio es `docs/pagina.json`), `app/` sin las piezas (258; aquí `RecetaApp.swift` tiene 24
y `Info.plist`/`Package.swift` se generan) y `build.sh` + `empaquetar.sh` + `package.json` (207, generados).

## Revisar a mano
- En un Mac: `cd app && swift build -c release` (el Swift imita el de Repasa, que compila; aquí no se puede compilar).
- Electron: `pruebas/test_crear.py` abre la app de Linux de verdad si `ELECTRON` apunta a uno (con Xvfb). Windows no se prueba aquí.
- Los íconos (`docs/favicon.svg`, `app/<Nombre>.icns`, `escritorio/iconos/`) los pone la app.

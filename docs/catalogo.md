# Catálogo de piezas y plan

Sale de comparar las seis apps (oct 2026): ~60 archivos repetidos, casi todos con una versión distinta por app. Cada fila dice de
dónde se toma la pieza (la mejor versión) y qué se le suma de las otras.

> **La fuente de verdad son los `pieza.json`** (todas las piezas, listas y planeadas, ya tienen el suyo): `pieza.py catalogo`.
> Este archivo solo guarda el **orden de extracción** y las brechas encontradas. Al extraer una pieza, cambia su `estado` a
> `lista` y mueve aquí su fila.

## Listas

| Pieza | Versión | Qué es | Tomada de |
|---|---|---|---|
| `nucleo` | 0.7.0 | `app.json`, carpeta de datos, config validada, escritura atómica, `ruta_en`, contrato de scripts | Esquema `bin/comun.py` + Alcancía/Repasa |
| `ia` | 0.5.0 | La IA de la persona con su cuenta, segura | Esquema `bin/ia.py` + Alcancía (pedido en archivo) + Repasa (material) |
| `i18n` | 0.2.0 | `T`/`Tp`/`Thtml`/`tr`/`traducirDOM`, paquetes de idioma validados | Minuta (`tr`) + Esquema (`T` que escapa, `traducirDOM`) + Alcancía (`Thtml`) + Graba (prioridad) |
| `bienvenida` | 0.2.0 | Primer uso por pasos, el idioma siempre primero; cada pieza suma su paso | Repasa (teclas 1/2) + Esquema (avisos que esperan) + Graba (flechas) + Alcancía |
| `actualizaciones` | 0.2.0 | Releases del propio repo, `.sha256` obligatorio, Mac (target propio) y Electron | Esquema + Repasa (URL sin puerto ni `..`, PATH fijo, textos que traduce la interfaz) |

## Por extraer, en este orden

| # | Pieza | Tipo | Tomar de | Sumar de | Notas |
|---|---|---|---|---|---|
| 2 | `host-ui` (JS) | UI | Esquema | — | `crearHost({nombre, global, simular})`. Antes: `probarIA` lleva `{ia}` en todas (hoy unas usan `{id}`) |
| 4 | `componentes` (JS+CSS) | UI | Esquema | Minuta (`formComentarios` → issue en GitHub) | Diálogo, toast con cola, filas de IA, fila de actualización «Paso n de 3». Antes: unificar tokens CSS (`--suave` hoy es texto en 4 apps y fondo en Esquema) |
| 5 | `tema` (CSS) | UI | Esquema (sistema/claro/oscuro) | — | Con `light-dark()` para no repetir el bloque oscuro |
| 6 | `catalogo` (Py + host) | Py + (b) | Esquema `plantillas.py` + `Catalogo.swift` + `catalogo.js` | Corta (`origen`, categoría = carpeta) | SHA-256 **obligatorio** (en Corta es opcional) |
| 7 | `red` (Py) | Py | Alcancía `bin/red.py` | — | HTTPS sin redirecciones, dominios permitidos |
| 8 | `mcp` (Py) | Py | Alcancía `mcp_servidor.py` + `mcp_conectar.py` | — | `mcp.servir(nombre, …, herramientas)`; conectar a claude/codex/gemini/Claude Desktop |
| 9 | `cifrado` (JS) | UI | Repasa `motor/cifrado.js` | Alcancía (límite, «versión más nueva») | PBKDF2 600k + AES-256-GCM |
| 10 | `transcribir` (Swift + Py) | (c) + Py | Minuta (VAD, filtro de alucinaciones con bucles) | Corta (vocabulario por archivo, no como argumento) | Paquete Swift compartido + `ModeloWhisper` una sola vez |
| 11 | `host-mac` (Swift) | (b) | Esquema `app/Sources/Esquema/` | Alcancía (secreto por stdin), Repasa (`conEntrada` con varios args) | Host genérico: lee `pieza.json`. **Agregar timeout** |
| 12 | `host-escritorio` (Electron) | (b) | Esquema `escritorio/src/` | — | Ídem |
| 13 | `empaquetado` | build | Esquema | — | `build.sh`, `empaquetar.sh`, `preparar.sh`, instaladores, `Package.swift`, `Info.plist` generados desde `app.json`. El Python portátil (CPython 3.13.16) ya es idéntico en las seis: un solo `python.lock` |
| 14 | `github` | repo | Esquema | — | Plantillas de issues/PR, `dependabot`, workflows reutilizables (`workflow_call`) para revisar y publicar |
| 15 | `universos` | Py + UI | Minuta (`universo.py`, galería) | Catálogo (#6) | Lo que pediste como ejemplo: tras #6 queda casi listo |

Después: la página pública (`docs/`), `revisar_privacidad.sh`, `generar_demo.py`, `pruebas/contrato.py` genérico.

## Brechas encontradas al comparar (arreglar ya en esas apps)

| App | Qué | Dónde | Arreglo |
|---|---|---|---|
| Graba, Minuta | Si el CLI de IA es viejo, **reintenta sin las protecciones** (`--strict-mcp-config`, sin herramientas): la IA corre con todo, con texto de afuera | `graba/bin/ia.py`, `minuta/bin/perfil.py` (`_opcion_desconocida`) | Reemplazar por la pieza `ia` |
| Graba, Minuta | El puente no revisa que el mensaje venga del marco principal y del origen de la app | `graba/app/Sources/Graba/Ventana.swift`, `minuta/app/Sources/Minuta/VisorWeb.swift`, `graba/escritorio/src/main.js`, `minuta/escritorio/src/main.js` | Copiar la guarda de Esquema (`isMainFrame` + `securityOrigin`; `senderFrame === mainFrame` + origen) |
| Graba | Las actualizaciones no validan que la descarga sea de su repo ni escapan la ruta en el script | `Actualizaciones.swift`, `escritorio/src/actualizaciones.js` | Pieza `actualizaciones` (lista) |
| Corta | Instalar del catálogo acepta archivos sin SHA-256 | `corta/bin/plantillas.py` (`instalar`) | Hacerlo obligatorio |
| Corta, Graba, Repasa, Minuta | La IA hereda las variables de la app | `bin/ia.py` | Pieza `ia` |
| Graba, Minuta | El vocabulario de whisper va como argumento | `procesar.py` | Por archivo, como Corta |
| Alcancía, Corta, Repasa | `T()` mete valores sin escapar en HTML | `ui/app.js` | Pieza `i18n` (lista: `T` escapa, `Thtml` para HTML armado) |
| Todas | Ningún `Procesador` tiene límite de tiempo | Swift/Electron | `limite` en el enchufe (#11, #12) |

# Pieza «empaquetado» — armar, firmar, publicar e instalar la app

Lo que cada app copiaba a mano de otra (y cambiaba nombre por nombre): `Info.plist`, `Package.swift`, `build.sh`,
`empaquetar.sh`, el `package.json` de Electron, `preparar.sh`, el instalador de Windows, `instalar.sh`/`instalar.ps1` y
`publicar.yml`. Aquí sale **generado desde `app.json`** con las plantillas de Pieza (`docs/enchufe.md`, «Plantillas»): la IA de una
app nueva no escribe nada de esto, solo completa `app.json` → `empaquetado` si necesita algo propio.

```bash
python3 herramientas/pieza.py agregar empaquetado <app>     # genera todo (y copia herramientas/python.lock)
python3 herramientas/pieza.py generar <app>                 # después de cambiar app.json (p. ej. la versión)
```

## Qué genera

| Archivo | Cuándo | Qué hace |
|---|---|---|
| `herramientas/python.lock` | siempre (se **copia**) | El Python portátil de todas las apps (python-build-standalone 3.13.16), una línea por sistema: url y SHA-256. Subirlo es un arreglo de esta pieza que llega solo con «Pieza al día». |
| `app/Info.plist` | `mac` | Bundle `app.<id>.mac`, nombre (con tildes), ejecutable e ícono `<NombreAscii>`, versión, macOS 15, barra de menú, categoría, permisos con su texto y copyright. |
| `app/Package.swift` | `mac` | El ejecutable `Sources/<NombreAscii>` y un target por cada pieza nativa instalada (`host-mac`, `actualizaciones`, `catalogo`, `trabajos`: agregar una lo pone al día), más los `binaryTarget` y ejecutables propios. |
| `build.sh` | `mac` | Compila e instala en `~/Applications`; no instala si la app está trabajando (`ocupada` y `herramientas/antes-de-instalar.sh`, o `FORZAR=1`); deja `desarrollo` en la carpeta de datos para la pieza «actualizaciones». |
| `herramientas/empaquetar.sh` | `mac` | `swift build`, Python del lock, binarios extra con huella, `bin/`, `ui/`, `app.json`, `acciones.json` y las carpetas extra; quita la demo; `LICENCIAS-TERCEROS.txt`; la versión de `app.json`; firma ad hoc con requisito por identificador; zip + `.sha256`. |
| `escritorio/package.json`, `escritorio/.npmrc` | `windows` o `linux` | electron-builder con versión exacta, `extraResources` con `app.json`, `acciones.json`, las carpetas extra, el Python y `vendor/<os>/herramientas`; nombres fijos; `ignore-scripts=true`. |
| `escritorio/herramientas/preparar.sh` | `windows` o `linux` | Python del lock y los binarios de `escritorio.binarios` con huella; llama `herramientas/preparar-extra.sh` si la app lo tiene. |
| `escritorio/herramientas/instalador-windows.sh`, `instalador.nsi` | `windows` | NSIS propio por usuario (`%LOCALAPPDATA%\Programs\<Nombre>`), `/S` silencioso, sin Wine. |
| `instalar.sh` | `mac` o `linux` | Un comando (`curl … \| bash`): baja el último Release, verifica la huella e instala para el usuario. |
| `instalar.ps1` | `windows` | Lo mismo en PowerShell (`irm … \| iex`). |
| `.github/workflows/publicar.yml` | siempre | Al cambiar `app.json` (o con una etiqueta `vX.Y.Z`): si la versión no está publicada, compila Mac (macos-15), Linux y Windows (ubuntu-24.04) y crea el Release con `<Nombre>-macOS.zip`, `-Windows.exe`, `-Linux.AppImage`, `-Linux.tar.gz` (y `-Linux.deb` si `deb`), cada uno con `.sha256`. |

**Publicar una versión = subir `version` en `app.json`** y hacer push a `main` (`empaquetar.sh` y CI la ponen en el `Info.plist` y el
`package.json` empaquetados; `pieza.py generar .` deja también al día los del repo).

## Lo que la app puede personalizar (`app.json` → `empaquetado`, todo opcional)

```json
"empaquetado": {
 "descripcion": "Una frase (package.json y el lanzador de Linux)",
 "categoria": "public.app-category.productivity",
 "linux_categoria": "Utility",
 "licencia": "AGPL-3.0",
 "correo": "mantiene@users.noreply.github.com",
 "barra_de_menu": false,
 "deb": false,
 "carpetas": ["plantillas", "estilos"],
 "quitar": ["ui/demo"],
 "permisos": [{"clave": "NSMicrophoneUsageDescription", "texto": "Ana graba tu voz para…"}],
 "ocupada": [{"proceso": "bin/procesar.py", "mensaje": "✗ Ana está procesando. Espera a que termine."}],
 "licencias": ["ffmpeg (https://ffmpeg.org), licencia GPL; …"],
 "whisper": true,
 "mac": {
  "binarios": [{"nombre": "ffmpeg", "url": "https://…/ffmpeg-darwin-arm64.gz", "sha256": "<64 hex>", "gz": true}]
 },
 "escritorio": {"binarios": [{"nombre": "ffmpeg", "gz": true, "linux": {"url": "https://…", "sha256": "…"}, "windows": {"url": "https://…", "sha256": "…"}}]}
}
```

Todo lo de aquí se valida al generar (direcciones solo `https`, huellas de 64 hex, nombres y rutas simples, textos sin signos que
cambien un script); si algo no calza, no se genera nada y se dice qué. Lo que no cabe en datos va en ganchos **de la app** (no los
genera la pieza, nunca los pisa):
- `herramientas/antes-de-instalar.sh`: `build.sh` lo corre antes de instalar; si sale con error, no instala (p. ej. «hay una
  grabación en curso»).
- `herramientas/empaquetar-extra.sh <App.app> <.build/release>`: lo propio antes de firmar.
- `escritorio/herramientas/preparar-extra.sh <mac|linux|win> <vendor/os> <caché>`: lo que la app arma a su manera.

`"whisper": true` compila `whisper-cli` (whisper.cpp v1.8.3, commit fijo) en `vendor/<os>/herramientas`: en el Mac con Apple clang,
Metal y Accelerate (Apple Silicon); en Windows y Linux con zig, sin bibliotecas aparte. Necesita `git` y `cmake`. Los scripts lo
encuentran en `<ID>_HERRAMIENTAS` (pieza «host-tauri») y la pieza «transcribir» lo usa con su archivo de argumentos.

Lo que sigue escribiendo la app: los íconos (`app/<NombreAscii>.icns`, `escritorio/iconos/<id>.png`, `<id>-256.png`, `<id>.ico`),
`Sources/<NombreAscii>/` y `escritorio/src/main.js`, y `npm install --ignore-scripts` en `escritorio/` para el `package-lock.json`.
Si cambias a mano un archivo generado, desde ahí es de la app (`pieza.py estado` lo dice; `pieza.py diferencias . empaquetado` lo
compara; `pieza.py generar . empaquetado --forzar` vuelve al de la pieza).

## Revisar a mano (no se puede probar aquí)
- En un Mac: `bash build.sh` arma, firma e instala; la app abre; `codesign -dr - ~/Applications/<Nombre>.app` dice el requisito por
  identificador; «Buscar actualizaciones» en una instalación de desarrollo hace `git pull` + `empaquetar.sh` (lee `desarrollo`).
- `plutil -extract version raw -o - app.json` lee la versión de un JSON (macOS 15) y `PlistBuddy` la escribe en la app.
- `swift build` con el `Package.swift` generado (coma final en `dependencies`, `binaryTarget` y `linkerSettings` como en Graba).
- En GitHub: `publicar.yml` de punta a punta con una versión de prueba (el Release con todos los nombres y sus `.sha256`), y
  `instalar.sh`/`instalar.ps1` contra ese Release. Windows: el instalador en un Windows de verdad (issue `probar`).

## Cómo lo adoptan las seis apps
Ya tienen todo esto escrito a mano y funciona: `pieza.py agregar empaquetado .` deja **como de la app** cada archivo que ya existe y
es distinto (no lo pisa) y genera solo lo que falta; `pieza.py diferencias . empaquetado` muestra la distancia. Para pasarse:
completar `app.json` → `version` y `empaquetado` (en `pruebas/datos/empaquetado/apps.json` está el de cada una, probado contra su
`Info.plist` y su `empaquetar.sh`), mover lo propio a los ganchos y correr `pieza.py generar . empaquetado --forzar`. Diferencias
con lo de hoy: `CFBundleVersion` es la versión (antes `1`), siempre hay ícono y copyright en el `Info.plist`, la versión sale de
`app.json` (antes `Info.plist` y `package.json`, que el contrato de cada app compara) y `publicar.yml` se dispara con `app.json`.

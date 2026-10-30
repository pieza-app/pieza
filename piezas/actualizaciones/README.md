# Pieza «actualizaciones» — versiones nuevas sin salir de la app

Mac (Swift) y Windows/Linux (Electron). Pregunta a GitHub por el último Release del repo de la app, avisa dentro de la app
(nunca una alerta del sistema) y, cuando la persona lo pide, descarga **solo** de `https://github.com/<repo>/releases/download/…`,
exige el `.sha256` publicado junto al archivo, reemplaza la app (deja la anterior si algo falla) y la vuelve a abrir. Los datos
de la persona viven fuera de la app: no se tocan.

**La redirección de GitHub:** esa URL responde con una redirección a su almacenamiento (`objects.githubusercontent.com` /
`release-assets.githubusercontent.com`). Se sigue solo por https (`curl --proto-redir '=https'`; en Electron se revisa la URL
final) y lo bajado vale solo si su SHA-256 es igual al del `.sha256`. Igual que Esquema, la mejor versión de las apps.

Nombres fijos de cada Release (los de `publicar.yml`, `instalar.sh` e `instalar.ps1`): `<Base>-macOS.zip`, `<Base>-Windows.exe`,
`<Base>-Linux.AppImage`, `<Base>-Linux.tar.gz`, cada uno con su `.sha256`. `<Base>` es el nombre sin tildes («Matías Café» → `MatiasCafe`).

## Electron (`escritorio/src/actualizaciones.js`)
```js
const { crear } = require("./actualizaciones");
const act = crear({ app, net, repo: "ana-app/ana", nombre: "Ana" });   // base, ejecutable: opcionales
act.revisarCadaRato((r) => llamar("actualizacionRevisada", r));          // recién cuando hay idioma elegido
ACCIONES.buscarActualizacion = async () => llamar("actualizacionRevisada", await act.revisar());
ACCIONES.actualizar = () => act.instalar((a) => llamar("actualizacionProgreso", a));  // antes: guardar todo
```
Linux: la instalación de `instalar.sh` (`~/.local/share/<Base>/<ejecutable>`) o el AppImage. Sin empaquetar o puesta a mano en
otra parte, nunca hay versión nueva (se actualiza con git o a mano).

## Mac (`app/Sources/PiezaActualizaciones/Actualizaciones.swift`)
Va en su propio target. En `Package.swift`: `.target(name: "PiezaActualizaciones")` y `"PiezaActualizaciones"` en las dependencias
del ejecutable; en la app, `import PiezaActualizaciones`.
```swift
Actualizaciones.configurar(.init(repo: "ana-app/ana", nombre: "Ana",
    archivoDesarrollo: Rutas.datos.appendingPathComponent("desarrollo"), variableProgreso: "ANA_PROGRESO"))
Actualizaciones.revisarCadaRato { r in Ventana.shared.llamar("actualizacionRevisada", r) }   // con Idioma.elegido
// case "buscarActualizacion": Actualizaciones.revisar { r in self.llamar("actualizacionRevisada", r) }
// case "actualizar": Actualizaciones.seguir { a in self.llamar("actualizacionProgreso", a) }
//                    Actualizaciones.instalar { ok, codigo in if !ok { self.llamar("actualizacionProgreso", Actualizaciones.aviso("error", codigo)) } }
```
Instalación de desarrollo (build.sh dejó la ruta del checkout en `archivoDesarrollo`): `git pull --ff-only` + `herramientas/empaquetar.sh`.

## Lo que llega a la interfaz
- `actualizacionRevisada`: `{hay, version, notas, sinConexion, texto: "Versión {v}", valores: {v}}`.
- `actualizacionProgreso`: `{paso: "1"|"2"|"3"|"error", codigo, texto, valores: {app}, total: 3, pct?}`.

`texto` es la frase en español con marcadores: muéstrala con `T(texto, valores)` (pieza `i18n`). Ningún texto traducido ni nada
variable entra al guion de instalación sin `comillas()`: el guion solo escribe códigos de paso.

## Pasar una app a esta pieza
Esquema, Repasa, Alcancía y Corta tienen su `Actualizaciones` con el nombre y el repo escritos adentro. Cambiar las llamadas por
las de arriba (`revisar` ahora devuelve un diccionario; `instalar` devuelve un código de `textos` en vez de un texto) y mostrar
`texto` con `T()`. Graba no valida el origen de la descarga: pasarla primero.

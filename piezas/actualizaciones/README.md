# Pieza «actualizaciones» — versiones nuevas sin salir de la app

Mac (Swift) y Windows/Linux (Electron). Pregunta a GitHub por el último Release del repo de la app, avisa dentro de la app
(nunca una alerta del sistema) y, cuando la persona lo pide, descarga **solo** de `https://github.com/<repo>/releases/download/…`,
exige el `.sha256` publicado junto al archivo, reemplaza la app (deja la anterior si algo falla) y la vuelve a abrir. Los datos
de la persona viven fuera de la app: no se tocan.

**La redirección de GitHub:** esa URL responde con una redirección a su almacenamiento (`objects.githubusercontent.com` /
`release-assets.githubusercontent.com`). Se sigue solo por https (`curl --proto-redir '=https'`; en Electron se revisa la URL
final) y lo bajado vale solo si su SHA-256 es igual al del `.sha256`. Igual que Esquema, la mejor versión de las apps.

**Firma (opcional, desde 0.4; recomendada antes del primer Release):** el `.sha256` detecta una descarga rota, pero no una versión
falsa subida por alguien que tome la cuenta de GitHub (subiría las dos cosas). Con **llaves** (abajo), cada archivo además tiene que
traer su `.sig`: la firma Ed25519 de quien mantiene la app, hecha en su Mac con una llave que nunca está en GitHub.

Nombres fijos de cada Release (los de `publicar.yml`, `instalar.sh` e `instalar.ps1`): `<Base>-macOS.zip`, `<Base>-Windows.exe`,
`<Base>-Linux.AppImage`, `<Base>-Linux.tar.gz`, cada uno con su `.sha256`. `<Base>` es el nombre sin tildes («Matías Café» → `MatiasCafe`).

## Electron (`escritorio/src/actualizaciones.js`)
```js
const { crear } = require("./actualizaciones");
const act = crear({ app, net, repo: "ana-app/ana", nombre: "Ana" });   // base, ejecutable, llaves, id: opcionales
// con el host: crearHost({…, actualizaciones: act}) y después act.usarApp(host.app) (las llaves de app.json, si las hay)
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
    archivoDesarrollo: Rutas.datos.appendingPathComponent("desarrollo"), variableProgreso: "ANA_PROGRESO",
    appJSON: Host.recursos.appendingPathComponent("app.json")))   // o llaves: ["…"]; sin las dos, sin firma
Actualizaciones.revisarCadaRato { r in Ventana.shared.llamar("actualizacionRevisada", r) }   // con Idioma.elegido
// case "buscarActualizacion": Actualizaciones.revisar { r in self.llamar("actualizacionRevisada", r) }
// case "actualizar": Actualizaciones.seguir { a in self.llamar("actualizacionProgreso", a) }
//                    Actualizaciones.instalar { ok, codigo in if !ok { self.llamar("actualizacionProgreso", Actualizaciones.aviso("error", codigo)) } }
```
Instalación de desarrollo (build.sh dejó la ruta del checkout en `archivoDesarrollo`): `git pull --ff-only` + `herramientas/empaquetar.sh`.

## Firma de las actualizaciones (Ed25519)

**Por qué:** si alguien toma la cuenta de GitHub de la app, puede subir un Release con su propio zip y su propio `.sha256`. La firma
lo impide: la llave privada vive solo en el Llavero del Mac de quien mantiene la app (nunca en GitHub ni en un secreto de Actions) y
cada app instalada trae la pública adentro. La app instalada es la que decide: un Release nuevo solo puede cambiar las llaves si viene
firmado por una de las de antes.

**Dónde van las llaves:** `app.json` de la app (va dentro de la app):
```json
"actualizaciones": {"llaves": ["6kpsY+KcUgq+9VB7Ey7F+ZVHdq6+vnuSQh7qaRRG0iw="]}
```
Cada una es la pública Ed25519 (32 bytes en base64). Hasta **2**, para cambiar de llave sin dejar a nadie atrás (una versión firmada
con la vieja trae las dos; la siguiente, solo la nueva). Swift la lee con `appJSON:` y Electron con `usarApp(host.app)`; también se
puede dar directo (`llaves:` en Swift, `crear({llaves})` en Electron), y eso gana. `pieza.py generar` revisa su forma (mal escritas,
no genera) y con llaves `publicar.yml` (pieza «empaquetado») crea el Release como **borrador**. Unas llaves que no sirven apagan las
actualizaciones (Swift: `configurar` devuelve `false`; Electron: `revisar` nunca encuentra nada y lo dice en la consola): mejor sin
actualizaciones que sin revisar la firma. **Sin llaves, todo es igual que en 0.3.**

**Lo que se firma** (exactamente, en UTF-8): `<id>-actualizacion|<versión sin v>|<sha256 del archivo en minúsculas>`, p. ej.
`ana-actualizacion|0.2.0|9f86d0…`. `<id>` es el `id` de `app.json` (sin app.json: `id:` o la base en minúsculas). La firma va en
`<archivo>.sig`, en base64 (64 bytes), junto a cada archivo del Release (`<Base>-macOS.zip.sig`, `<Base>-Windows.exe.sig`,
`<Base>-Linux.AppImage.sig`, `<Base>-Linux.tar.gz.sig`).

**Lo que revisa la app** antes de tocar nada: la huella del archivo es la del `.sha256`; la versión firmada es la del Release (la
etiqueta) y más nueva que la instalada (así no se puede reetiquetar una versión vieja con fallas ni volver atrás); la firma es de una
de sus llaves. Si algo no calza: no instala y avisa `codigo: "firma"` («No pude comprobar que la versión nueva sea de {app}: le falta
la firma o no es válida. {app} sigue igual que antes.»). En el **Mac**, con llaves, la app baja zip, `.sha256` y `.sig` ella misma
(URLSession, solo de las URLs de `esDescargaNuestra`, redirecciones solo por https), calcula el SHA-256 (CryptoKit), revisa la firma
(`Curve25519.Signing.PublicKey.isValidSignature`) y recién ahí escribe el guion, que instala el zip ya revisado (no vuelve a bajar
nada). Avance: paso 1 mientras baja, 2 al revisar y descomprimir, 3 al instalar. En **Electron**, lo mismo antes de lanzar el
instalador o reemplazar el AppImage o la carpeta (`crypto.verify` con una llave ed25519).

**Funciones** (para probar o para otra herramienta): Swift `mensajeFirmado`, `firmaValida`, `llavePublica`, `revisarDescarga`,
`sha256(de:)`, `leerHuella`, `esMayor`; Electron `mensajeFirmado`, `firmaValida`, `llavePublica`, `revisarDescarga`.

### Lo que hace quien mantiene la app (en su Mac, una vez)
Desde un checkout de Pieza (necesita Xcode o sus herramientas de línea de comandos):
```bash
swift herramientas/firmar/firmar.swift crear <id>       # crea la llave en tu Llavero y muestra la PÚBLICA (si ya hay una, no la pisa)
swift herramientas/firmar/firmar.swift respaldo <id>    # la PRIVADA, una vez, para un respaldo fuera de línea (pide escribir <id>)
```
1. La pública va a `app.json` → `"actualizaciones": {"llaves": ["…"]}`, y `pieza.py generar .` (publicar.yml pasa a borrador).
2. El respaldo de la privada, **fuera de línea** (papel o una memoria USB guardada): nunca a GitHub, un chat, un correo ni la nube.
   Sin ella no se pueden publicar versiones que las apps acepten. Para recuperarla en otro Mac: `firmar.swift importar <id>`.
3. La llave queda en el llavero de inicio de sesión (contraseña genérica, servicio «Pieza · firma de actualizaciones», cuenta `<id>`),
   que no se sincroniza con iCloud. macOS puede pedir permiso para leerla: bien, así sabes cuándo se usa.

### En cada versión
Subir `version` en `app.json` y push (como siempre). `publicar.yml` compila y deja el Release **borrador**. Después, en el Mac:
```bash
bash herramientas/firmar_release.sh <dueño/repo> vX.Y.Z <id>
```
Baja el borrador (con tu sesión de `gh`), revisa cada `.sha256`, firma cada archivo (`firmar.swift firmar`), comprueba la firma,
sube los `.sig` y, si escribes «sí», lo publica como la última versión. Las apps instaladas lo ven en unas horas.

### Cambiar de llave
La herramienta guarda una llave por app en cada Mac. Para rotar: crea la nueva en otro Mac (u otra cuenta de usuario) con
`crear <id>`, publica una versión firmada con la vieja que traiga **las dos** públicas en `app.json`, y desde la siguiente firma con la
nueva y saca la vieja. Si se perdió la privada y no hay respaldo, las apps instaladas no pueden recibir más versiones: hay que
reinstalarlas a mano (`instalar.sh`).

### Revisar a mano en el Mac (antes del primer Release firmado)
`pruebas/swift/revisar_actualizaciones.sh` (en GitHub, en cada cambio) prueba la firma, la huella, la configuración y la herramienta
`firmar.swift` en un llavero temporal. Lo que necesita una app instalada y un Release de verdad, una vez por app:
1. Con una versión de prueba firmada (`firmar_release.sh`): «Buscar actualizaciones» la ve, «Actualizar» pasa los tres pasos y la app
   se vuelve a abrir en la versión nueva.
2. Borrar el `.sig` del Release (o subir uno de otra versión): «Actualizar» termina en el aviso de `firma` y la app sigue igual.
3. En Windows y Linux, lo mismo con el instalador y el AppImage.

## Lo que llega a la interfaz (una sola forma)
- `actualizacionRevisada`: `{hay, version, notas, sinConexion, texto: "Versión {v}", valores: {v}, desarrollo}`.
- `disponible` (lo que la app manda en su estado, p. ej. `estado.actualizacion`): lo mismo, sin `sinConexion`.
- `actualizacionProgreso`: `{paso: "1"|"2"|"3"|"error", codigo, texto, valores: {app}, total: 3, pct?}` (`aviso(paso, codigo)`
  lo arma en Swift y en Electron).

`texto` es la frase en español con marcadores (una clave de `ui/idiomas`): la interfaz la muestra con `T(texto, valores)` (pieza
`i18n`); `notas` son las del Release, tal cual (con `esc()`). Nunca se traduce en la app nativa ni se manda un texto ya traducido.
En una instalación de desarrollo (Mac) `hay` puede venir sin versión: `desarrollo: true`, `texto` vacío y en `notas` los commits
nuevos (la fila de `componentes` lo muestra como «Hay cambios nuevos en el código de {app}»). Una interfaz de antes que esperaba
`detalle` puede seguir: `componentes` 0.2.0 lee `notas` o `detalle`.

Si la app suma un aviso propio (por ejemplo «espera a que termine de guardar»), usa la misma forma, con su frase en español en
`texto` y su inglés en `ui/idiomas/en.json`:
```js
llamar("actualizacionProgreso", { paso: "error", codigo: "ocupada", texto: "Espera a que termine de guardar y vuelve a intentarlo.", valores: {} });
```
```js
// En la interfaz:
const linea = (r) => (r.texto ? T(r.texto, r.valores || {}) : "");
```
Ningún texto traducido ni nada variable entra al guion de instalación sin `comillas()`: el guion solo escribe códigos de paso.

## Pasar una app a esta pieza
Repasa, Alcancía y Corta tienen su `Actualizaciones` con el nombre y el repo escritos adentro (Esquema ya usa la pieza). Cambiar
las llamadas por las de arriba (`revisar` ahora devuelve un diccionario; `instalar` devuelve un código de `textos` en vez de un
texto), mandar `disponible` en el estado tal cual y mostrar `texto` con `T()` (si la interfaz esperaba un `detalle` ya traducido,
ahora son `texto`/`valores` + `notas`). En Mac, `Actualizaciones.version` sirve para el estado o un User-Agent. Graba no valida
el origen de la descarga: pasarla primero.

## Si venías de 0.3.0

| Qué cambió | Qué hacer en la app |
|---|---|
| Firma opcional (`llaves`, `.sig`) | Nada si no la usas. Para usarla: la llave (arriba), `appJSON:` en `Actualizaciones.configurar` (Mac) y `act.usarApp(host.app)` después de `crearHost` (Electron), `pieza.py generar .` para el borrador en `publicar.yml`. |
| Error nuevo `firma` | `pieza.py actualizar` suma su frase a `ui/idiomas/en.json`; si tu interfaz traduce a mano, súmala. |
| Mac: sin `.sha256`/zip al instalar, el estado dice `error\|sinDescarga` | Nada: el avance ya no se queda en «Descargando…» si no había descarga. |

## Si venías de 0.2.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `desarrollo` en la respuesta de revisar y en `disponible` | Nada: lo lee la fila de `componentes` 0.2.0. Si tu interfaz mostraba «Versión» vacía en una instalación de desarrollo, ya no. |

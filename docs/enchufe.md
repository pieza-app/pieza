# El enchufe: cómo se conecta una pieza a una app

Una app de la familia (Minuta, Graba, Corta, Alcancía, Repasa, Esquema y las que vengan) tiene siempre las mismas cuatro capas:

```
ui/            interfaz web única (la misma en Mac, Windows, Linux, iPhone y Android)
   │  host.enviar(accion, datos)            ▲ window.<App>.<respuesta>(json)
   ▼                                        │
host           Mac, Windows y Linux: host-tauri (Rust + WebView del sistema) · iPhone: host-ios · Android: Capacitor
   │  correr bin/<script>.py <args…> [entrada.json] <salida.json>
   ▼
bin/           scripts Python, solo biblioteca estándar (en el móvil: motor JS)
```

El problema de hoy: **cada acción nueva se escribe a mano en tres hosts** (un `case` en Swift, una entrada en `ACCIONES` de
Electron, otra en el móvil) más el contrato y la simulación. Son 168 acciones en las seis apps; ~70 % son de dos tipos que no
necesitan código nativo propio. El enchufe hace que esas se declaren una vez, en el `pieza.json` de la pieza, y los hosts las
enruten solos.

## Los tres tipos de acción

| Tipo | Qué es | Hoy | Con el enchufe |
|---|---|---|---|
| **(a) Script** | Validar datos → correr un `.py` → devolver su JSON | 26 % (43) | Se **declara** en `pieza.json`. Cero código nativo. |
| **(b) Capacidad común** | Diálogo de carpeta, portapapeles, enlace, exportar, actualizaciones, catálogo, notificaciones… | 44 % (74) | La **base** las trae una sola vez, iguales en los tres hosts. La UI las llama por nombre. |
| **(c) Nativo propio** | Grabar pantalla, micrófono, calendario, llavero… | 30 % (49) | **Pieza nativa**: su parte en Rust registra `host.registrar(nombre, …)` en `host-tauri`. Lo que solo existe en Apple va en un ayudante en Swift que se corre como un script. |

## `pieza.json`

```json
{
 "formato": 1,
 "id": "ia",
 "version": "0.1.0",
 "nombre": "Tu IA",
 "icono": "icono.svg",
 "licencia": "MPL-2.0",
 "descripcion": "Una línea: qué resuelve.",
 "en": {"nombre": "The name in English", "descripcion": "One line: what it solves."},
 "origen": "De qué app salió y qué mejoras sumó de las otras.",
 "requiere": ["nucleo"],
 "archivos": {"python/ia.py": "bin/ia.py"},
 "config": {"ia": ["claude", "codex", "gemini"]},
 "acciones": {
  "probarIA": {
   "script": "ia.py", "args": ["probar"], "entrada": "archivo",
   "datos": {"ia": {"tipo": "enum", "valores": ["claude", "codex", "gemini"]}},
   "responde": "iaProbada", "limite": 150
  }
 },
 "textos": {"No conozco esa IA.": "I don't know that AI."}
}
```

| Campo | Para qué |
|---|---|
| `licencia` | **Obligatoria.** Las oficiales, `MPL-2.0` (ver «Licencia»). |
| `solo` | Opcional: `{origen: [plataformas]}` para un archivo que es de algunas plataformas (el Swift solo en `mac`). Se copia solo si la app tiene alguna de ellas en `app.json` → `plataformas` (sin esa clave, todo). |
| `icono` | **Obligatorio.** Un `.svg` dentro de la pieza (ver «El ícono»). Es lo que la gente ve en el catálogo, la página y el creador. |
| `archivos` | Origen en la pieza → destino en la app. `pieza.py agregar` los copia y anota su huella. El destino va dentro de `bin/`, `ui/`, `app/`, `escritorio/`, `movil/`, `docs/`, `pruebas/` o `herramientas/`, nunca en carpetas que empiezan con punto (`.github/`, `.git/`, `.claude/`: ahí un archivo ejecuta código), y sin enlaces. |
| `requiere` | Otras piezas que se agregan antes, solas. |
| `config` | Claves que la pieza necesita en `app.json` (lista = valores posibles; `"bool"`, `"texto"`, `"numero"` = tipo). Se suman sin pisar. |
| `config_opcional` | `{clave: "cuándo"}`: claves de `config` que solo sirven si la app ofrece algo (p. ej. `tema`: «Apariencia» en Ajustes). Se suman igual, salvo `pieza.py agregar … --sin-config=tema` (o `actualizar … --sin-config=tema`; sobre una pieza ya instalada, quita la clave de `app.json` si la app no la cambió); esa decisión queda en `piezas.json` (`sin_config`) y `actualizar` la respeta. |
| `acciones` | Las acciones tipo (a) que trae la pieza (abajo). |
| `textos` | Frases en español → inglés. Se suman al `ui/idiomas/en.json` de la app si faltan. |
| `textos_si_usa` | `{identificador: {frase: traducción}}`: frases de algo opcional de la pieza (p. ej. `fuerzaFrase` de «cifrado»). Se suman solo si el código propio de la app (`ui/`, `bin/`, `motor/`, `escritorio/src/`, `app/Sources/`, `app/web/`, `movil/host/`, sin lo copiado por la pieza) nombra ese identificador. |
| `app_json` | `{sección: {esqueleto, que}}`: una sección de `app.json` que la pieza necesita (p. ej. `catalogo`). `agregar` suma el esqueleto si falta (nunca pisa una que ya está) y dice qué completar. No puede ser una clave de la app (`id`, `nombre`, `datos`, `config`, `acciones`…). |
| `estado` | `lista` (trae código) o `planeada` (aún por extraer: sin `archivos`, con `tomar_de`). |
| `categoria` | `base`, `ia`, `interfaz`, `datos`, `medios`, `conexiones`, `plataforma` o `repo`. |
| `recomendar` | `{"cuando": "…", "siempre": true?, "palabras": […]?}`: cuándo sugerirla al crear una app. `siempre` = va en toda app de esas plataformas. |
| `plataformas` | Dónde funciona: `mac`, `windows`, `linux`, `ios`, `android`. |
| `pantallas` | `[{donde, nombre, que}]`: lo que suma a la app (Bienvenida, Ajustes, Galería, Web…). |
| `permisos` | Por plataforma, `[{clave, por}]`: la clave de Info.plist, el permiso de Android o el aviso del sistema, y para qué. |
| `red` | Dominios a los que sale. Vacío = funciona sin internet. |
| `tareas_persona` | Lo que solo puede hacer una persona (crear una org, una cuenta de desarrollador, verificar un sitio). |
| `compatible` | `{"nucleo": ">=0.1.0 <1.0.0"}`: con qué versiones de lo que requiere funciona. `pieza.py` no deja combinar versiones que no se llevan. |
| `cambios` | De la más nueva a la más vieja: `{version, tipo, resumen, seguridad?, migrar?}` (`migrar`: una **lista** de pasos, cada uno un texto; `pieza.py revisar` lo exige). Es lo que se le avisa a cada app. |
| `red_nota` | Cuando la app no sale a internet pero algo de la persona sí (su IA, su proveedor): dicho en una frase. |

Estos campos son los que lee el creador de proyectos: `pieza.py ficha <piezas> --plataformas …` los suma y muestra la app
completa antes de crearla. Agregar una pieza (o un campo nuevo a una) la hace aparecer sola en el creador.

### Una acción

| Campo | Regla |
|---|---|
| `script` | `nombre.py`, dentro de `bin/`. Si es de la app y no de la pieza: `"scriptDeLaApp": true`. |
| `args` | Literales, o `$campo` **solo si el campo es `enum` o `entero`** ya validado. |
| `entrada` | `"archivo"` si hay datos que no van en `args`: el host los escribe en un JSON temporal y lo pasa antes de la salida. |
| `datos` | Esquema cerrado de lo que manda la UI. Tipos: `texto{max, recortar?}`, `enum{valores}`, `bool`, `entero{min?,max?}`, `rutaRelativa{extensiones?}` (relativa, sin `..`), `base64{maxBytes}`, `lista{max?, de?}` (sin `de`: textos de hasta 2000). `"requerido": true` en cualquiera; un campo de `args` siempre lo es. Un valor que no calza **no corre** el script (responde `codigo: "datos"`); `recortar` corta un texto largo en vez de rechazarlo. Lo no declarado se descarta (salvo `"*": "pasar"`, cuando el script valida todo). |
| `inyectar` | Valores que pone el host y nunca la UI: `{"carpeta": "carpetaActual"}`, `{"idioma": "idiomaUI"}`. El host trae `idiomaUI`, `carpetaDatos` y, si la app usa la carpeta elegida, `carpetaActual`; las demás fuentes las registra la app. Sin valor, no corre (`codigo: "falta"`); el inyector puede devolver su propio texto (`Puente.Falta("…")` / `host.falta("…")`). Un campo inyectado no puede estar también en `datos`. |
| `responde` | Función `window.<App>.<responde>(json)` a la que va el resultado. `null` = no responde. |
| `eco` | Campos de la entrada que vuelven en la respuesta (ej. `orden`). También en el error de datos, los que son válidos por sí solos. |
| `cola` | `"escritura"` = va en la fila `EnOrden` (nunca dos escrituras a la vez). |
| `despues` | Acciones que corre el host al terminar, ej. `["estado"]` (registradas por la app o declaradas). |
| `progreso` | Función que recibe `{eventos}` mientras corre (pieza «trabajos»: el script escribe en `<ID>_PROGRESO`). |
| `limite` | **Obligatorio.** Segundos (1 a 3600); `"trabajo"`: sin tope **mientras lata** (pieza «trabajos» 0.2.0: `Trabajo.latir()` o `trabajos.mantener_vivo()` tocan `<ID>_LATIDO`; sin latido por 45 s —120 el primero— el host lo corta); o según el valor de un campo `enum`: `{"segun": "orden", "valores": {"documentar": "trabajo", "leer": 60}, "otro": 120}`. |
| `maximo` | Bytes que puede pesar la entrada (5 MB si no lo dice; hasta 50 MB). Un `texto.max` o `base64.maxBytes` no puede pasarlo. |
| `vigilar` | `"lee"` o `"escribe"`, con `ruta` (`rutaRelativa`) en `datos` (y `texto` para escribir): el vigilante de la carpeta conoce el texto que la app leyó (el `texto` de la respuesta) o va a escribir (antes de correr el script; si falla, vuelve el de antes), así lo de la app nunca se avisa como un cambio de afuera. |
| `movil` | `{"motor": "modulo.funcion"}` para correrlo en JS en el celular, o `{"soloEscritorio": true}`. |

### Reglas de seguridad (las revisa `pieza.py revisar`, y el host al cargar)

1. **Lo que escribe la persona nunca va como argumento** del proceso: cualquier programa del computador ve los argumentos. Va en
   el archivo de entrada. Un `$campo` de tipo `texto` en `args` se rechaza.
2. **Rutas absolutas, secretos y la carpeta actual nunca vienen de la UI**: solo por `inyectar` o por una capacidad. Los secretos
   van por la entrada estándar (patrón de Alcancía).
3. **El script tiene que existir en `bin/`** y llamarse `^\w+\.py$`.
4. **El entorno del script** no hereda nada raro; el de la IA, además, sin las variables `<ID>_*` de la app.
5. **Todo tiene límite de tiempo** (o, si es un trabajo largo, un latido: si deja de latir, se corta). Al salir de la app se corta lo
   que siga corriendo: nada queda huérfano.


## Plantillas (`generar`): archivos que se llenan desde `app.json`

Algunas piezas no copian un archivo igual para todas las apps: lo **generan** para cada una (`Info.plist`, `build.sh`, los
workflows, `AGENTS.md`…). En `pieza.json`:

```json
"generar": {
 "plantillas/build.sh": "build.sh",
 "plantillas/Info.plist": {"destino": "app/Info.plist", "si": "mac"},
 "plantillas/AGENTS.md": {"destino": "AGENTS.md", "una_vez": true}
},
"datos_app": {"pagina": "docs/pagina.json"}
```

| Campo | Para qué |
|---|---|
| origen | La plantilla, dentro de `plantillas/` de la pieza (sin carpetas con punto: `plantillas/github/workflows/x.yml` → `.github/workflows/x.yml`). |
| `destino` | Dónde queda en la app: un archivo de la raíz, algo dentro de `bin/`, `ui/`, `app/`… (como `archivos`) o, **solo en piezas oficiales**, uno de estos lugares con punto: `.github/`, `.claude/agents/`, `.claude/settings.json`, `.gitignore`, `escritorio/.npmrc`. Nunca `app.json`, `piezas.json`, `acciones.json` ni `.git/`. |
| `si` | Solo si esa ruta del contexto es verdad (`"mac"`, `"escritorio"`, `"!windows"`, `"piezas.catalogo"`, `"app.empaquetado.deb"`). |
| `una_vez` | Se escribe solo si no existe, la primera vez, y desde ahí es de la app (no se anota huella ni se vuelve a generar). Para lo que la IA de la app completa (`AGENTS.md`, `CONTRIBUTING.md`…). |
| `datos_app` | `{nombre: "ruta/en/la/app.json"}`: un archivo de datos de la app que la plantilla lee como `datos.<nombre>` (`null` si no existe). |

**Sintaxis** (`herramientas/plantillas.py`, sin dependencias, solo datos: nada de la pieza se ejecuta, así «Pieza al día» puede leer
las piezas nuevas sin ejecutar su código):

| Marca | Qué hace |
|---|---|
| `{{nombre}}`, `{{app.empaquetado.categoria}}` | El valor. Si no existe, **error** (un tipeo nunca pasa callado). Un texto solo entra si es «seguro» (sin comillas, acento grave, `$`, `\`, `<`, `>`, `&`, llaves, barra vertical, `;` ni saltos de línea); si no, la plantilla dice cómo escaparlo. |
| `{{x\|filtro\|filtro}}` | Escapar: `xml`, `json` (también deja `<`, `>`, `&`, U+2028 y U+2029 como `\u…`: sirve dentro de un `<script>`), `yaml`, `sh`. Transformar: `ascii` (Alcancía → Alcancia), `minus`, `mayus`. Validar (fallan si no calza): `https`, `sha256`, `nombre`, `ruta`, `version`, `id`, `color` (`#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb()`/`rgba()`/`hsl()`/`hsla()` con números: para CSS) y `linea` (texto libre de una línea, solo donde nada se interpreta: un heredoc entre comillas, Markdown). |
| `{{#si x}}…{{#sino}}…{{/si}}`, `{{#no x}}…{{/no}}` | Condición (`false`, `0`, `""`, `[]`, `{}` y lo que falta cuentan como no). |
| `{{#cada lista como b}}…{{b.url}}…{{/cada}}` | Recorrer; adentro también `b_primero` y `b_ultimo`. |
| `{{! comentario }}` | No sale. |

`${{ … }}` (GitHub Actions) no es una marca y queda tal cual en la plantilla; un **valor** que se inserta (de `app.json` o de
los datos) nunca puede traer `${{`, `{{` ni `}}`: es un error (así un dato no se vuelve una expresión de Actions). Una línea que
solo tiene una marca de bloque desaparece entera.

**Contexto** (lo que ve toda plantilla; `python3 herramientas/plantillas.py contexto app.json` lo muestra):

| Clave | Qué es |
|---|---|
| `app` | `app.json` entero (las secciones propias de una pieza, p. ej. `app.empaquetado`). |
| `id`, `ID`, `nombre`, `nombre_ascii` | `ana`, `ANA`, `Ána`, `Ana` (para nombres de archivo y ejecutables). |
| `version` | `app.json` → `version` (X.Y.Z; `0.1.0` si no está). |
| `repo`, `dueno`, `repo_nombre`, `web` | De `app.json` → `repo` (`<id>-app/<id>` si no está) y su página `https://<dueño>.github.io/<repo>/`. |
| `bundle`, `bundle_escritorio` | `app.<id>.mac` y `app.<id>.escritorio`. |
| `datos_mac` | La carpeta de datos en el Mac, relativa a la casa (la regla de `nucleo`). |
| `plataformas`, `mac`, `windows`, `linux`, `ios`, `android`, `escritorio`, `mac_o_linux`, `movil` | La lista y cada una como verdadero o falso (`escritorio` = Windows o Linux). |
| `piezas` | `{id: true}` de las piezas instaladas: `{{#si piezas.catalogo}}`. |
| `piezas_lista` | `[{id, nombre, version, archivos}]` de las piezas instaladas (para una tabla «Piezas»). |
| `pieza` | `{id, version}` de la pieza que genera. |
| `datos` | Lo de `datos_app`. |

**Cómo se mantiene al día:** `agregar`, `actualizar` y `pieza.py generar <app> [pieza…]` (después de cambiar `app.json`) llenan
otra vez lo generado de **todas** las piezas instaladas (una pieza nueva puede cambiar lo de otra). La huella de cada archivo queda
en `piezas.json` → `generados`: si la app lo cambió, la pieza ya no lo toca (`estado` lo dice; `diferencias` muestra lo generado
contra lo de la app; `--forzar` lo reemplaza). Un archivo que ya existía y es distinto queda como de la app (no detiene `agregar`).
Lo de `.github/` y `.claude/` **nunca se actualiza solo**: el token de Actions no puede escribir workflows, y un workflow o unos
ajustes de la IA (que pueden definir hooks) los tiene que ver una persona; «Pieza al día» lo pone en el issue. Lo generado se
escribe con un temporal nuevo en la misma carpeta (sin seguir enlaces) que reemplaza al archivo. Una pieza de la comunidad no puede generar archivos.

## Licencia

Toda pieza dice su `licencia` (MPL-2.0, MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, LGPL-3.0, GPL-3.0 o AGPL-3.0). Las
**oficiales son MPL-2.0** ([texto](../piezas/LICENSE)): quien cambia un archivo de la pieza comparte ese cambio, y la app que la
usa elige su propia licencia. Cada archivo de código de una pieza oficial empieza con el aviso (después del shebang si hay):

```
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
```

(con `//` o `/* */` en JS, Swift y CSS). El aviso viaja con el archivo cuando se copia a la app. `pieza.py revisar` lo exige.

## El ícono (toda pieza, oficial o de la comunidad)

Cada pieza trae `icono.svg`: un dibujo de línea que se entiende sin leer el nombre (una llave para el cifrado, una nube para la
red). Así el catálogo se recorre mirando, no leyendo.

- **Formato:** `viewBox="0 0 24 24"`, trazo de 2 (`stroke-width="2"`), puntas y uniones redondeadas, `fill="none"`.
- **Color:** solo `currentColor` (o `none`): la página, la app y el creador lo pintan con su color, en claro y oscuro.
- **Seguro:** solo formas (`svg`, `g`, `path`, `circle`, `ellipse`, `rect`, `line`, `polyline`, `polygon`, `title`; los de
  proyectos también degradados: `defs`, `linearGradient`, `radialGradient`, `stop`, `clipPath`), hasta 8 KB,
  sin `<script>`, `<style>`, `<image>`, `<use>`, `<a>`, `href`, `style` ni `on…`, sin DOCTYPE ni entidades.
  `herramientas/icono.py` lo revisa (en `pieza.py revisar`, en el catálogo de la comunidad y al armar la página): si no pasa,
  la pieza no entra.
- **Mira los que hay** en `piezas/*/icono.svg` para mantener el mismo trazo. Un ícono no lleva texto ni logos de marcas.

## Crear una app nueva (`pieza.py crear`)

`pieza.py crear <carpeta> --id <id> --nombre <Nombre> [--plataformas mac,windows,linux] [--piezas ia,…] [--repo dueño/repo]
[--datos sistema|visible]` = `iniciar` + las piezas con `recomendar.siempre` para esas plataformas (las que están por extraer se
saltan y se dicen) + las pedidas + `esqueleto` + `github` (las dos al final: lo que escriben una vez mira qué piezas ya están) + la
acción de ejemplo en `app.json` → `acciones` + `acciones.json` + `generar`. Lo propio de la app sale de las plantillas `una_vez` de
la pieza [`esqueleto`](../piezas/esqueleto/) (desde ahí es de la app): `pieza.py` no tiene nada de ninguna app. Al final imprime cada
archivo con sus `La app:` (lo que completa la IA; sin lo copiado ni lo que se regenera) y las `tareas_persona` de las piezas. No toca
una carpeta que ya tiene algo; el nombre es una palabra (de él salen el target de Swift y los archivos de las versiones).

## `app.json` (en la raíz de cada app)

```json
{"nombre": "Esquema", "id": "esquema", "datos": "sistema", "plataformas": ["mac", "windows", "linux"],
 "config": {"idioma_ui": ["es", "en"], "tema": ["sistema", "claro", "oscuro"], "bienvenida": "bool", "ia": ["claude", "codex", "gemini"]}}
```

`"sin_acciones": ["listaIA"]`: acciones de una pieza que la app **no adopta** (no entran a `acciones.json`, así el host no carga
algo que la interfaz nunca pide). Una que ninguna pieza declara se avisa.

Claves que usan las piezas además: `"repo": "dueño/repo"` (el repo de GitHub de la app, p. ej. `"ana-app/ana"`: «red» lo pone en
el User-Agent; si no tiene esa forma, se ignora), `"privado": true` (todo archivo
0600) y las secciones propias de una pieza (`catalogo`, `transcribir`, `ia`…: ver su README).

Es la única descripción de la app que leen las piezas: de aquí sale el prefijo de las variables (`ESQUEMA_DATOS`,
`ESQUEMA_RECURSOS`), dónde se guardan los datos y qué claves de config se aceptan. `"icono": "docs/favicon.svg"` (opcional)
dice cuál es el ícono de la app para la lista de proyectos de la página de Pieza; sin él se busca `docs/favicon.svg`,
`favicon.svg` y `ui/favicon.svg`. Un ícono de app puede tener sus colores, pero pasa por las mismas reglas de seguridad. `"version": "X.Y.Z"` es la versión de
la app (`iniciar` la pone en `0.1.0`): con la pieza «empaquetado», es lo único que se sube para publicar. `Info.plist`,
`package.json`, el instalador y los workflows salen de aquí con las plantillas (abajo, «Plantillas»).

## `piezas.json` (en la raíz de cada app, lo escribe `pieza.py`)

```json
{"formato": 1, "piezas": {"ia": {"version": "0.1.0", "archivos": {"bin/ia.py": "<sha256 al copiar>"}}}}
```

Con eso `pieza.py estado` sabe qué cambió la app (huella distinta) y qué trae la base de nuevo (versión distinta), y
`actualizar` nunca pisa un cambio de la app. Va en orden de dependencias (lo que una pieza `requiere` primero) y revisa `compatible`
con las versiones que quedan **después** de la pasada: si `componentes` nueva necesita `tema` nueva, se actualizan las dos juntas
(aunque se pida solo `componentes`); si no hay una versión que sirva, esa pieza no se toca y se dice por qué.

## El host genérico (`host-tauri`)

Desde nov 2026 el host es **`host-tauri`**: uno solo para Mac, Windows y Linux, con la misma API que los dos de antes
(`piezas/host-tauri/README.md`). `host-mac` (Swift) y `host-escritorio` (Electron) están **retirados**: solo los usan Graba y
Minuta mientras se arma el ayudante de Swift. Lo de abajo vale para los tres.

`pieza.py agregar`/`actualizar` arman **`acciones.json`** en la raíz de la app (si tiene un host; o a mano con `pieza.py acciones
<app>`): las `acciones` de cada pieza instalada (las de la versión copiada, guardadas en `piezas.json`) más las de `app.json` →
`"acciones"`, las propias de la app (mismo formato; su script tiene que estar en `bin/`), menos las de `"sin_acciones"`. Dos con el
mismo nombre o una que no cumple las reglas detienen todo. Con un `piezas.json` de antes (sin las acciones guardadas) y otra versión
en la base, las busca en el historial de git de Pieza y las anota; si no las encuentra, **no** arma un `acciones.json` sin ellas y
dice qué `pieza.py actualizar` correr. Va dentro de la app junto a `app.json` (en `empaquetar.sh` y en `extraResources`).

```json
{"formato": 1, "acciones": {"probarIA": {"script": "ia.py", "args": ["probar"], "entrada": "archivo",
  "datos": {"ia": {"tipo": "enum", "valores": ["claude", "codex", "gemini"]}}, "responde": "iaProbada", "limite": 150, "pieza": "ia"}}}
```

Cada host, al arrancar y en cada mensaje, sin código por acción:

1. Lee `app.json` y `acciones.json` de **dentro del paquete** de la app (nunca de afuera) y vuelve a revisar cada acción con las
   mismas reglas que `pieza.py` (`errores_accion`, `enchufe.rs` y, mientras existan, `enchufe.js` y `Enchufe.swift`: una prueba los compara). Lo que no pasa no
   se carga.
2. Llega `{accion, datos}` del marco principal con la página propia (si no, se ignora).
3. Primero lo que **registró la app** (`Puente.registrar` / `host.acciones.registrar`: lo nativo propio, y lo que todavía no se
   migró), después lo que **trae el host** (`listo`, `config`, `abrirEnlace`, `copiar`; en Electron también las actualizaciones si se
   le pasan) y al final lo **declarado**.
4. Una declarada: valida `datos` (hasta `maximo`) → agrega `inyectar` → (fila si `cola`) → `vigilar` → escribe la entrada en una
   carpeta temporal 0700 → corre el script con su `limite` (al cumplirse, o si un trabajo deja de latir, corta también lo que lanzó)
   → agrega `eco` → `window.<App>.<responde>(r)` → corre `despues`.
5. Si no está en ninguna parte, se ignora.

Errores del host: `{ok: false, codigo: "datos" | "falta" | "limite" | "fallo", campo?, texto, valores, error}` (`texto` en español
con marcadores para `T()`; `error` ya traducido para las interfaces de antes).

`pruebas/contrato.py` es uno solo para todas las apps: la pieza «contrato» (`pieza.py agregar contrato .`). Lee `acciones.json`,
la interfaz, la vista previa y el código de cada host, y revisa que digan lo mismo; lo propio de la app va en
`pruebas/contrato_app.py` (ver `piezas/contrato/README.md`).

## Capacidades comunes

`estado` · `config.guardar` · `idioma` · `dialogo.carpeta` (con marcador y vigilante) · `dialogo.archivos` ·
`dialogo.guardarComo` · `portapapeles.copiar` · `enlace.abrir` (solo https) · `finder.mostrar` · `papelera.mover` ·
`notificaciones` · `actualizaciones.revisar/instalar` · `catalogo.listar/descargar` · `descarga.verificada` (url + sha256) ·
`ventana` (menú, cerrar, minimizar, zoom) · `soltar` · `secretos` (llavero / safeStorage).

En los hosts retirados (0.3), con la misma API en los dos. `host-tauri` trae todo esto (también `soltar`) con una sola API: su README tiene la tabla.


| Capacidad | Mac (`host-mac`) | Windows y Linux (`host-escritorio`) |
|---|---|---|
| estado, config, idioma, menús, apariencia | `Host`, `Config`, `Idioma`, `p.menus` (`menuAyuda: false` sin Ayuda) | `crearHost({menu, ayuda: false})` |
| diálogos, portapapeles, enlace, papelera, medios | `elegirCarpeta`, `elegirArchivos`, `guardarComo`, `copiar`, `abrirEnlace`, `papelera`, `registrarMedios` | `dialogos.*`, `copiar`, `abrirEnlace`, `papelera`, `medios.registrar` |
| carpeta elegida | `p.carpeta = CarpetaElegida()` (marcador del sistema: la sigue aunque la muevan) | `carpeta: {clave}` (la ruta real) |
| vigilante de la carpeta | `p.vigilante = Vigilante(extensiones:)` (FSEvents) | `vigilar: {extensiones, alCambiar}` (`fs.watch`) |
| mostrar en el Finder / explorador | `p.mostrarEnFinder(url)` | `host.mostrarEnCarpeta(ruta)` |
| actualizaciones | `p.actualizaciones = .init(…)` (pieza «actualizaciones») | `actualizaciones: crear(…)` |
| secretos | `Secretos(servicio:)` (Llavero, solo este Mac) | `host.secretos(nombre)` (`safeStorage`; sin llavero en Linux, nada) |
| avisos | `Notificaciones` (permiso cuando la app lo pide) | `host.notificaciones` |
| variables de la app para todos los scripts (0.3) | `Procesador.entornoApp` | `crearHost({entorno})` |
| app de bandeja / barra de menú (0.3) | `barraDeMenu`, `abrirAlArrancar` | `ventana.alCerrar: "esconder"`, `abrirAlArrancar` (y `--oculta`) |
| la ventana de la app (0.3) | `alCrearVentana`, `barraTransparente`, `vidrio`, `nombreVentana` | `alCrearVentana`, `ventana.frame`, `userData: "sistema"`, `ventanas.agregar` (otra ventana en el puente) |
| menú de la app (0.3) | `tituloAjustes`, `menuApp` | `tituloAjustes`, `menuApp` |
| soltar archivos (0.3) | `alSoltar`, `soltado(nombre)` | pendiente (con `webUtils.getPathForFile` en el preload) |

Un enlace https tocado en la ventana pasa por `abrirEnlace` como si lo pidiera la interfaz (0.3): si la app registró el suyo,
decide ella. Las variables de `entorno` nunca pisan `<ID>_RECURSOS`, `<ID>_DATOS`, `<ID>_PROGRESO` ni `<ID>_LATIDO`.

Pendientes: `soltar` en Electron, `catalogo` (ya es
la pieza «catálogo», dos líneas por tipo en cada app: el host no la envuelve) y `descarga.verificada`. Los avisos **programados**
(que llegan con la app cerrada) siguen en la pieza «notificaciones», planeada.

## Versiones y actualizaciones

Cada pieza usa X.Y.Z y anota en `cambios` qué cambió y de qué **tipo**:

| Tipo | Versión | ¿Se actualiza sola? |
|---|---|---|
| `arreglo` | sube Z | Sí, si la app no cambió esos archivos |
| `mejora` (compatible) | sube Y | Sí, igual |
| `rompe` | sube X (o Y mientras X sea 0) | **Nunca**: trae `migrar`, los pasos |
| `seguridad: true` | cualquiera | Se marca en el título del PR o del issue |

**Cómo se entera cada app, sin servidor ni telemetría:** `pieza.py iniciar` le agrega `.github/workflows/pieza-al-dia.yml`, que
una vez por semana, en el repo de la app, trae la última Pieza y:
- con lo que se puede actualizar solo (`pieza.py actualizar --automatico`) abre un **PR**: las pruebas de la app corren ahí;
- con lo que va a mano (`pieza.py aviso`) abre o pone al día un **issue** con qué cambió y los pasos, y lo cierra cuando todo
  queda al día.

Sin GitHub: `pieza.py estado <app>` dice lo mismo.

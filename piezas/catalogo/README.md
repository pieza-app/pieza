# Pieza «catálogo» — contenido de la comunidad, seguro

Plantillas, efectos, temas o universos que la gente comparte en un repo **de solo datos** (`<org>/<app>-catalogo`) y la app
descarga. La descarga la hace el host (Swift o Electron): **solo** `https://raw.githubusercontent.com/<repo>/<rama>/`, sin
seguir redirecciones, con tamaño máximo cortado al leer. Python valida y guarda: el índice con el **validador que pone la app**,
y cada archivo contra el **último índice validado** (id, tamaño y SHA-256 obligatorios), nunca contra lo que mande la interfaz.

## app.json
```json
"catalogo": {"repo": "ana-app/ana-catalogo", "rama": "main",
             "tipos": {"plantillas": {"validador": "plantilla_formato", "indice": "index.json", "max_bytes": 102400,
                                      "max_indice": 1048576, "max_en_indice": 1000, "singular": "plantilla", "origen": true}}}
```
- En el repo del catálogo cada cosa va en `<tipo>/<categoria>/<id>.json`: **la categoría es la carpeta**. El índice (`indice`, por
  defecto `<tipo>/index.json`) es `{"formato": 1, "<tipo>": [{…el contenido…, "ruta", "sha256", "tamano"}]}` (también se aceptan
  `archivo`/`bytes`).
- `validador`: un módulo de `bin/` de la app con `validar(obj) -> [problemas]` (otro nombre con `"funcion"`) y, si quiere,
  `CATEGORIAS`, `CAMPOS` (otra constante con `"campos": "CLAVES"`, o la lista misma) y `FORMATO`. El validador recibe el objeto
  **entero** (sin `ruta`/`sha256`/`tamano`/`origen`): un campo de más que no acepta deja la entrada fuera; recién después se
  recorta a `CAMPOS`. El mismo archivo puede vivir en `herramientas/` del catálogo.
- `"categoria": false`: catálogo plano, `<carpeta>/<id>.json`, sin campo `categoria`. `"carpeta"` (en el catálogo), `"local"` (en la
  carpeta de datos), `"incluidos"` (en la app) y `"clave"` (la lista dentro del índice) son el id del tipo si no se dicen.
  `"mayusculas": true`: ids como `pt-BR` (sin repetir aunque cambie una mayúscula). El índice también puede ser una lista sola.
- Lo incluido en la app: `<recursos>/<incluidos>/[<categoria>/]<id>.json`. Lo descargado: `<carpeta de datos>/<local>/<id>.json`
  (0600), gana sobre lo incluido. `origen: false` si la interfaz no quiere el campo `origen`.
- Sin conexión, `listar` del host devuelve la última lista validada (`catalogo.py ultima`, acción `catalogoUltima`) con
  `sin_conexion: true`, `fecha` y la frase: la galería se ve; descargar pide abrirla de nuevo con conexión. Una redirección o un
  índice que no llega también cuentan como «sin conexión» (no `ok: false`): una prueba de la app que esperaba `ok: false` ahí
  tiene que esperar `sin_conexion: true`.
- `archivo` y `bytes` (los nombres viejos de `ruta` y `tamano` en algunos índices) solo se leen en una entrada del índice y solo si
  falta `ruta`/`tamano`: un campo `archivo` del contenido (el nombre sugerido de una plantilla) es contenido y se queda.
- `pieza.py agregar catalogo` suma a `app.json` un esqueleto de `catalogo` para completar (`repo` y `tipos`).

## API
| Dónde | Qué |
|---|---|
| `bin/catalogo.py indice <entrada {tipo, archivo}>` | `{ok, tipo, <tipo>: […]}` y guarda ese índice validado para `instalar` |
| `bin/catalogo.py instalar <entrada {tipo, archivo, id, sha256}>` | `{ok, tipo, id, item, <singular>?}` |
| `bin/catalogo.py listar <entrada {tipo}>` / acción `catalogoInstalados` | incluidos + descargados con `origen` |
| `bin/catalogo.py quitar <entrada {tipo, id}>` / acción `catalogoQuitar` | borra uno descargado |
| `bin/catalogo.py ultima <entrada {tipo}>` / acción `catalogoUltima` | la última lista validada (sin conexión), con `fecha` |
| `catalogo.py generar <tipo> <raíz> <salida> [--validador=x.py] [--opciones='{…}']` / `validar <tipo> <archivos…>` | para el repo del catálogo y su workflow; ahí no hace falta `nucleo.py` ni `app.json` (con `--validador`) |
| Electron `crear({fetch, procesador, appJson, agente})` | `listar(tipo)`, `descargar(tipo, id)` |
| Swift `Catalogo.configurar(appJSON:agente:correr:)` (target `PiezaCatalogo`) | `Catalogo.listar(tipo)`, `Catalogo.descargar(tipo, id)` |

Errores: `{ok: false, codigo, frase, error}` con `codigo` en `sin_conexion`, `indice`, `no_valido`, `danado`, `no_esta`; la
interfaz muestra `Tp(r.frase)` (las frases ya están en `textos`). No va en `plantilla`: con `"singular": "plantilla"` ahí llega el
objeto descargado.

```swift
// Package.swift: .target(name: "PiezaCatalogo") y "PiezaCatalogo" en las dependencias del ejecutable.
Catalogo.configurar(appJSON: Host.recursos.appendingPathComponent("app.json"), agente: "Ana/\(version)") { s, a, d, fin in
    Procesador.conEntrada(s, a, d, fin: fin)
}
// case "catalogo": Catalogo.listar(tipo) { self.llamar("catalogoListo", $0) }
```
```js
const cat = require("./catalogo").crear({ fetch: net.fetch, procesador: Procesador, appJson, agente: `Ana/${version}` });
ACCIONES.catalogo = async ({ tipo }) => llamar("catalogoListo", await cat.listar(tipo));
```

## Si venías de la 0.2.0
- **Todas:** nada que cambiar. Un contenido con su propio campo `archivo` o `bytes` ya pasa el validador.
- **Esquema:** tu copia de `bin/catalogo.py` tenía este mismo arreglo (`ALIAS`): con `pieza.py actualizar . catalogo --forzar`
  vuelve a ser la de Pieza y `pieza.py estado` deja de mostrarla como cambiada.

## Si venías de la 0.1
- **Todas:** `Tp(r.frase)` en vez de `Tp(r.plantilla)` para los errores. Revisa que tu validador acepte el objeto entero del
  catálogo (antes se recortaba a `CAMPOS` antes de validar, y un campo de más entraba sin él). Swift: compila de nuevo el target
  `PiezaCatalogo`.
- **Minuta:** puede dejar la categoría inventada (`comunidad`) de los idiomas con `"categoria": false`, `"mayusculas": true` para
  `pt-BR`, y llamar al tipo como quiera con `"carpeta"`/`"local"`/`"incluidos"` (el catálogo en `universos/`, lo descargado en
  `temas/`). Su workflow puede correr `catalogo.py generar … --validador=herramientas/universo_formato.py` sin copiar
  `nucleo.py` ni `app.json`.
- **Corta:** `"campos": "CLAVES"` en vez de repetir `CAMPOS = CLAVES` en `efecto_formato.py`.
- **Esquema:** la plantilla descargada sigue en `r.plantilla`; el error, en `r.frase`.

## Pasar una app a esta pieza
**Esquema** (plantillas): `app.json` con `"catalogo": {"repo": "esquema-app/esquema-catalogo", "tipos": {"plantillas":
{"validador": "plantilla_formato", "indice": "index.json", "singular": "plantilla"}}}`. Borrar de `bin/plantillas.py` lo de
`catalogo`/`instalar`/`indice`/`descargadas` (queda lo propio, o se borra entero si solo listaba: `catalogo.py listar`) y
dejar `plantilla_formato.py` solo con `validar`, `CATEGORIAS`, `CAMPOS`, `FORMATO` (`indice`/`validar_indice` ahora son de la
pieza; el catálogo usa `catalogo.py generar plantillas <raíz>`). Borrar `app/Sources/Esquema/Catalogo.swift` y
`escritorio/src/catalogo.js` (la pieza los trae). En `Ventana.swift`/`main.js`: `Catalogo.listar("plantillas")` y
`descargar("plantillas", id)`; la respuesta trae la lista en `plantillas` (igual que antes) más `tipo`, y los errores traen
`codigo` + `plantilla` (frase nueva: «Eso no es válido.» / «Llegó dañado…» en vez de «Esa plantilla no es válida.»; la interfaz
traduce `plantilla`). Los elementos de `listar` ahora traen `origen`: aceptarlo en `validarPlantilla` (o `"origen": false`).
**Corta** (efectos y plantillas): un tipo por cosa en `app.json` (`efectos` con `validador: "efecto_formato"`, `plantillas`
con `"plantilla_formato"`), `CAMPOS` = `efecto_formato.CLAVES`. Borrar `validar_indice`/`instalar` de `efectos.py` y
`plantillas.py`, el `Tipo` y `Catalogo.swift` propios. El índice pasa de `archivo`/`bytes` a `ruta`/`tamano` (la pieza lee los
dos; la interfaz debe leer `ruta`/`tamano`), y los descargados pasan de `~/Corta/.corta/efectos/` a `<carpeta de datos>/efectos/`
(la misma si `app.json` → `datos: "visible"`). La categoría del catálogo ahora puede tener guiones (más permisivo).
**Minuta** (universos e idiomas, cuando se extraiga `universos`): su `Catalogo.swift` **no verifica SHA-256**: el índice del
catálogo tiene que sumar `sha256` y `tamano` (`catalogo.py generar`) antes de usar la pieza.

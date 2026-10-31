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
- `validador`: un módulo de `bin/` de la app con `validar(obj) -> [problemas]` y, si quiere, `CATEGORIAS`, `CAMPOS` y `FORMATO`.
  El mismo archivo puede vivir en `herramientas/` del catálogo (así lo hacía Esquema con `plantilla_formato.py`).
- Lo incluido en la app: `<recursos>/<tipo>/<categoria>/<id>.json`. Lo descargado: `<carpeta de datos>/<tipo>/<id>.json` (0600),
  gana sobre lo incluido. `origen: false` si la interfaz no quiere el campo `origen`.

## API
| Dónde | Qué |
|---|---|
| `bin/catalogo.py indice <entrada {tipo, archivo}>` | `{ok, tipo, <tipo>: […]}` y guarda ese índice validado para `instalar` |
| `bin/catalogo.py instalar <entrada {tipo, archivo, id, sha256}>` | `{ok, tipo, id, item, <singular>?}` |
| `bin/catalogo.py listar <entrada {tipo}>` / acción `catalogoInstalados` | incluidos + descargados con `origen` |
| `bin/catalogo.py quitar <entrada {tipo, id}>` / acción `catalogoQuitar` | borra uno descargado |
| `bin/catalogo.py generar <tipo> <raíz> <salida>` / `validar <tipo> <archivos…>` | para el repo del catálogo y su workflow |
| Electron `crear({fetch, procesador, appJson, agente})` | `listar(tipo)`, `descargar(tipo, id)` |
| Swift `Catalogo.configurar(appJSON:agente:correr:)` (target `PiezaCatalogo`) | `Catalogo.listar(tipo)`, `Catalogo.descargar(tipo, id)` |

Errores: `{ok: false, codigo, plantilla, error}` con `codigo` en `sin_conexion`, `indice`, `no_valido`, `danado`, `no_esta`; la
interfaz muestra `Tp(r.plantilla)` (las frases ya están en `textos`).

```swift
// Package.swift: .target(name: "PiezaCatalogo") y "PiezaCatalogo" en las dependencias del ejecutable.
Catalogo.configurar(appJSON: Rutas.recursos.appendingPathComponent("app.json"), agente: "Ana/\(version)") { s, a, d, fin in
    Procesador.conEntrada(s, a, d, fin: fin)
}
// case "catalogo": Catalogo.listar(tipo) { self.llamar("catalogoListo", $0) }
```
```js
const cat = require("./catalogo").crear({ fetch: net.fetch, procesador: Procesador, appJson, agente: `Ana/${version}` });
ACCIONES.catalogo = async ({ tipo }) => llamar("catalogoListo", await cat.listar(tipo));
```

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

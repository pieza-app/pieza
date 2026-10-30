# El enchufe: cómo se conecta una pieza a una app

Una app de la familia (Minuta, Graba, Corta, Alcancía, Repasa, Esquema y las que vengan) tiene siempre las mismas cuatro capas:

```
ui/            interfaz web única (la misma en Mac, Windows, Linux, iPhone y Android)
   │  host.enviar(accion, datos)            ▲ window.<App>.<respuesta>(json)
   ▼                                        │
host           Mac: Swift + WKWebView · Windows/Linux: Electron · móvil: Capacitor
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
| **(c) Nativo propio** | Grabar pantalla, micrófono, calendario, llavero… | 30 % (49) | **Pieza nativa**: un archivo Swift y uno JS que registran `acciones[nombre] = handler` con el mismo contexto. |

## `pieza.json`

```json
{
 "formato": 1,
 "id": "ia",
 "version": "0.1.0",
 "nombre": "Tu IA",
 "descripcion": "Una línea: qué resuelve.",
 "origen": "De qué app salió y qué mejoras sumó de las otras.",
 "requiere": ["nucleo"],
 "archivos": {"python/ia.py": "bin/ia.py"},
 "config": {"ia": ["claude", "codex", "gemini"]},
 "acciones": {
  "probarIA": {
   "script": "ia.py", "args": ["probar"], "entrada": "archivo",
   "datos": {"ia": {"tipo": "enum", "valores": ["claude", "codex", "gemini"]}},
   "responde": "iaProbada", "limite": 120
  }
 },
 "textos": {"No conozco esa IA.": "I don't know that AI."}
}
```

| Campo | Para qué |
|---|---|
| `archivos` | Origen en la pieza → destino en la app. `pieza.py agregar` los copia y anota su huella. |
| `requiere` | Otras piezas que se agregan antes, solas. |
| `config` | Claves que la pieza necesita en `app.json` (lista = valores posibles; `"bool"`, `"texto"`, `"numero"` = tipo). Se suman sin pisar. |
| `acciones` | Las acciones tipo (a) que trae la pieza (abajo). |
| `textos` | Frases en español → inglés. Se suman al `ui/idiomas/en.json` de la app si faltan. |

### Una acción

| Campo | Regla |
|---|---|
| `script` | `nombre.py`, dentro de `bin/`. Si es de la app y no de la pieza: `"scriptDeLaApp": true`. |
| `args` | Literales, o `$campo` **solo si el campo es `enum` o `entero`** ya validado. |
| `entrada` | `"archivo"` si hay datos que no van en `args`: el host los escribe en un JSON temporal y lo pasa antes de la salida. |
| `datos` | Esquema cerrado de lo que manda la UI. Tipos: `texto{max}`, `enum{valores}`, `bool`, `entero{min,max}`, `rutaRelativa`, `base64{maxBytes}`, `lista`. Lo no declarado se descarta (salvo `"*": "pasar"`, cuando el script valida todo). |
| `inyectar` | Valores que pone el host y nunca la UI: `{"carpeta": "carpetaActual"}`, `{"idioma": "idiomaUI"}`. |
| `responde` | Función `window.<App>.<responde>(json)` a la que va el resultado. `null` = no responde. |
| `eco` | Campos de la entrada que vuelven en la respuesta (ej. `orden`). |
| `cola` | `"escritura"` = va en la fila `EnOrden` (nunca dos escrituras a la vez). |
| `despues` | Lo que corre el host al terminar, ej. `["estado"]`. |
| `limite` | Segundos. **Obligatorio**: hoy ningún `Procesador` tiene timeout. |
| `movil` | `{"motor": "modulo.funcion"}` para correrlo en JS en el celular, o `{"soloEscritorio": true}`. |

### Reglas de seguridad (las revisa `pieza.py revisar`, y el host al cargar)

1. **Lo que escribe la persona nunca va como argumento** del proceso: cualquier programa del computador ve los argumentos. Va en
   el archivo de entrada. Un `$campo` de tipo `texto` en `args` se rechaza.
2. **Rutas absolutas, secretos y la carpeta actual nunca vienen de la UI**: solo por `inyectar` o por una capacidad. Los secretos
   van por la entrada estándar (patrón de Alcancía).
3. **El script tiene que existir en `bin/`** y llamarse `^\w+\.py$`.
4. **El entorno del script** no hereda nada raro; el de la IA, además, sin las variables `<ID>_*` de la app.
5. **Todo tiene límite de tiempo.**

## `app.json` (en la raíz de cada app)

```json
{"nombre": "Esquema", "id": "esquema", "datos": "sistema",
 "config": {"idioma_ui": ["es", "en"], "tema": ["sistema", "claro", "oscuro"], "bienvenida": "bool", "ia": ["claude", "codex", "gemini"]}}
```

Es la única descripción de la app que leen las piezas: de aquí sale el prefijo de las variables (`ESQUEMA_DATOS`,
`ESQUEMA_RECURSOS`), dónde se guardan los datos y qué claves de config se aceptan. Más adelante también saldrán de aquí
`Info.plist`, `package.json`, el instalador y los íconos (ver «Plan»).

## `piezas.json` (en la raíz de cada app, lo escribe `pieza.py`)

```json
{"formato": 1, "piezas": {"ia": {"version": "0.1.0", "archivos": {"bin/ia.py": "<sha256 al copiar>"}}}}
```

Con eso `pieza.py estado` sabe qué cambió la app (huella distinta) y qué trae la base de nuevo (versión distinta), y
`actualizar` nunca pisa un cambio de la app.

## El host genérico (fase 2)

Cuando exista, cada host hace esto al arrancar y en cada mensaje, sin código por acción:

1. Lee los `pieza.json` de las piezas instaladas (dentro del paquete firmado de la app, nunca de afuera).
2. Llega `{accion, datos}` desde el marco principal y con el origen de la app (si no, se ignora).
3. Si la acción es una capacidad común o una pieza nativa, la atiende ese código.
4. Si es de un `pieza.json`: valida `datos` → agrega `inyectar` → (fila si `cola`) → escribe la entrada → corre el script con
   `limite` → traduce el error → agrega `eco` → `window.<App>.<responde>(r)` → corre `despues`.
5. Si no está en ninguna parte, se ignora (igual que el `default: break` de hoy).

`pruebas/contrato.py` pasa a ser uno solo para todas las apps: lee los `pieza.json` y revisa que la UI, la simulación del navegador,
los scripts y los tres hosts digan lo mismo.

## Capacidades comunes que traerá la base

`estado` · `config.guardar` · `idioma` · `dialogo.carpeta` (con marcador y vigilante) · `dialogo.archivos` ·
`dialogo.guardarComo` · `portapapeles.copiar` · `enlace.abrir` (solo https) · `finder.mostrar` · `papelera.mover` ·
`notificaciones` · `actualizaciones.revisar/instalar` · `catalogo.listar/descargar` · `descarga.verificada` (url + sha256) ·
`ventana` (menú, cerrar, minimizar, zoom) · `soltar` · `secretos` (llavero / safeStorage).

La referencia para cada una es la versión de Esquema (Swift `app/Sources/Esquema/` y Electron `escritorio/src/`), la más
completa y la única con todas las guardas.

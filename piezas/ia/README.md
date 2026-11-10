# Pieza «ia» — tu IA, con tu cuenta

Corre la IA que la persona ya tiene instalada (Claude Code, Codex o Gemini/Antigravity) para que la app nunca necesite una cuenta
ni una llave propia.

```python
import ia
texto, error = ia.preguntar("Resume esto: …")                     # sin herramientas
texto, error = ia.preguntar(pedido, archivos=["foto.jpg"])         # puede leer copias del material
texto, error = ia.preguntar(pedido, leer=repo, no_leer=[".env*"])  # revisión a fondo, solo lectura
if error:
    print(ia.frase(error))   # o manda error["codigo"] + error["valores"] a la interfaz para traducir
```

| Función | Devuelve |
|---|---|
| `lista()` | `[{id, nombre, instalada}]` |
| `elegida()` / `nombre(ia)` | La IA de la config / su nombre visible |
| `preguntar(prompt, *, ia, timeout, archivos, leer, no_leer, modelo)` | `(texto, None)` o `("", {codigo, valores})` |
| `ejecutar(...)` | El `CompletedProcess`, para quien necesite más control |
| `preguntar_vivo(prompt, *, ia, timeout, archivos, leer, no_leer, modelo, al_evento, detener, escribir)` | Como `preguntar`, contando en vivo lo que lee (`al_evento({"t": "lee", "ruta"})`, `{"t": "busca", "patron"}`, con `escribir` también `{"t": "escribe", "ruta"}`, y al final `{"t": "uso", "entrada", "cache", "salida"}` con los tokens reales) y cortando si `detener()` da True (código `detenido`) |
| `detenido(error)` | Si el error es que la persona detuvo la IA (no es una falla) |
| `probar(ia)` | `{ia, ok, codigo?, error?}` |

Garantías (probadas en `pruebas/test_piezas.py`): el pedido nunca va como argumento; Claude corre sin MCP, sin herramientas
(o solo lectura con material) y sin la memoria de la persona; la IA no ve las variables `<ID>_*` de la app; nunca se quitan
protecciones para que un CLI viejo funcione.

Acciones que declara: `probarIA` → `iaProbada`, `listaIA` → `iaLista`. Requiere `nucleo`.

## En Rust (0.8.0)
Con host-tauri, la pieza también se instala en `escritorio/src/pieza/ia.rs` (`#[path = "pieza/ia.rs"] mod ia;` en `main.rs`).
Mismas protecciones y mismos errores que `ia.py`:

```rust
let ia = ia::Ia::nueva(ia::Contexto { app_id: "recetas".into(), app_nombre: "Recetas".into(), prefijo: "RECETAS".into(),
                                      datos: carpeta_datos, ayuda: "Revisa en Ajustes → Tu IA.".into() });
let mut o = ia::Opciones::de("claude");
o.escribir = Some(carpeta_app);                       // opcional: editar solo ahí
let texto = ia.preguntar_vivo(&pedido, &o, &mut |e| avisar(e.json()), &|| detenido())?;  // Err(ErrorIa) con codigo/plantilla/valores
```

`ErrorIa::detenido()` dice si se cortó con `detener`. `Evento::json()` da lo mismo que `al_evento` en Python
(`{"t": "lee" | "busca" | "escribe" | "uso", …}`).

## Pasar una app a esta pieza

Las apps hoy tienen su propio `bin/ia.py`, así que `pieza.py agregar ia` no lo pisa y avisa. Para pasarla:
1. `pieza.py diferencias <app> ia` y revisar si la copia de la app tiene algo mejor (traerlo aquí primero).
2. `pieza.py actualizar <app> ia --forzar`.
3. Ajustar quien llama: `preguntar()` ahora devuelve el error como `{codigo, valores}` (antes, un texto). Donde se mostraba el
   texto, usar `ia.frase(error)`, o mandar el código a la interfaz para traducirlo. `ejecutar_ia` pasó a llamarse `ejecutar`.

## Pasar una app a esta pieza (lo que aprendimos con Esquema)

- **El host llama `probar` con un archivo de entrada**, no con la IA como argumento: `ia.py probar <entrada.json> <salida.json>`
  con `{"ia": "claude"}`. En Swift, `Procesador.conEntrada("ia.py", "probar", ["ia": ia])`; en Electron, lo mismo con el JSON de
  entrada. Cambia esas dos llamadas al adoptar la pieza.
- **Errores:** `preguntar` devuelve `(texto, None)` o `("", {"codigo", "plantilla", "valores"})`. Un script responde
  `{"ok": false, "codigo": …, "plantilla": …, "valores": …}` y la interfaz muestra `Tp(r.plantilla, r.valores)`: la plantilla es la
  frase en español (clave de `en.json`, ya viene en `textos` de la pieza), así nadie copia la tabla `ERRORES`. Decide por `codigo`
  (`no_instalada` → ofrecer instalarla; `actualizar` → pedir actualizar el CLI). `ia.frase(error)` la da en español para registros.
- **Dónde se elige la IA en tu app:** `"ia": {"ayuda": "Revisa en Ajustes → Tu IA."}` en `app.json`. Los errores `no_instalada` y
  `actualizar` traen esa frase en `ayuda` (la interfaz la traduce con el `en.json` de la app) y `ia.frase` la suma. Así no copias la
  tabla `ERRORES` para agregar una frase. `probar` no la trae: se prueba desde «Tu IA», donde «Revisa en Ajustes → Tu IA» sobra.

## Si venías de 0.6.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `probar` ya no trae `ayuda` (ni la suma a `error`) | Nada. Si en «Tu IA» quitabas a mano la frase de la ayuda del resultado de `iaProbada`, bórralo. |
- **La lista de IA instaladas** sale de `ia.py lista` (acción `listaIA`): no la busques por tu cuenta en Swift o Electron.
- **Borra la prueba nativa del CLI** en Swift y Electron: si el host lanzaba `claude`/`codex` directo para «Probar», lo hacía sin
  las protecciones. Todo pasa por `ia.py probar`.
- Lo propio de la app (frases de su asistente, instrucciones fijas como «responde solo con…») va en sus módulos, no en esta copia:
  así `pieza.py actualizar` puede traer las versiones nuevas sin chocar.
- **Las IA falsas de tus pruebas** tienen que responder `--help` con `--strict-mcp-config` y `--disallowedTools` (como el Claude
  real): sin eso, desde la 0.3.0 la pieza no corre y responde `actualizar`.

## En vivo (0.6.0)
`preguntar_vivo` usa el **mismo** armado del comando que `ejecutar` (`_armar`): carpeta temporal, sin MCP ni memoria, sin
herramientas o solo leer, `--tools`, `--setting-sources user`, «actualiza» si falta una protección. Claude cuenta lo que hace con
`--output-format stream-json --verbose` (si lo conoce), Codex con `exec --json` (si `codex exec --help` lo conoce); Gemini solo
responde. A Claude ya no se le prohíben herramientas que su versión no conoce (`MultiEdit` desde la 2.1, y las que avise él mismo
con «Permission deny rule … matches no known tool», que se recuerdan en `<datos>/ia-herramientas.json`), solo cuando conoce
`--tools`: ahí las demás herramientas ni se cargan. El aviso tampoco llega como detalle de un error.

**Esquema:** borrar `bin/ia_vivo.py`; `ia_vivo.preguntar_vivo(prompt, timeout, ia_, leer, no_leer, al_evento, detener)` →
`ia.preguntar_vivo(prompt, timeout=…, ia=…, leer=…, no_leer=…, al_evento=…, detener=…)` (todo con nombre; `ia_` pasa a `ia`),
`ia_vivo.detenido` → `ia.detenido`, `ia_vivo.frase` → `ia.frase` (ahora suma la `ayuda` de `app.json` si la hay) y
`ia_vivo.ERRORES` → `ia.ERRORES` (trae `detenido`). Las IA falsas de sus pruebas siguen sirviendo: con `--version` o sin él.

## Escribir en una carpeta (0.7.0)

Para que la IA cree o cambie archivos de un proyecto (el programa Pieza lo usa en cada paso):

```python
if ia.puede_escribir():
    texto, error = ia.preguntar(pedido, escribir="/ruta/de/la/app", timeout=1800)
```

- La IA lee y edita archivos **solo** en esa carpeta. No tiene terminal, internet ni subagentes.
- Claude: `Read`, `Glob`, `Grep`, `Edit` y `Write`, con `--permission-mode acceptEdits` y `--add-dir`. Lo demás va prohibido.
- Codex: su sandbox `workspace-write` en esa carpeta (sin red).
- Gemini no lo ofrece: `puede_escribir()` devuelve `False`. Pide los archivos en la respuesta.
- La IA sigue corriendo en una carpeta temporal: no carga la configuración ni los hooks del proyecto (Claude).
- **Revisa lo que cambió** antes de confiar en el resultado. Pieza revierte los archivos de piezas y corre las pruebas.

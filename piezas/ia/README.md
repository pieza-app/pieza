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
| `probar(ia)` | `{ia, ok, codigo?, error?}` |

Garantías (probadas en `pruebas/test_piezas.py`): el pedido nunca va como argumento; Claude corre sin MCP, sin herramientas
(o solo lectura con material) y sin la memoria de la persona; la IA no ve las variables `<ID>_*` de la app; nunca se quitan
protecciones para que un CLI viejo funcione.

Acciones que declara: `probarIA` → `iaProbada`, `listaIA` → `iaLista`. Requiere `nucleo`.

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
- **Borra la prueba nativa del CLI** en Swift y Electron: si el host lanzaba `claude`/`codex` directo para «Probar», lo hacía sin
  las protecciones. Todo pasa por `ia.py probar`.
- Lo propio de la app (frases de su asistente, instrucciones fijas como «responde solo con…») va en sus módulos, no en esta copia:
  así `pieza.py actualizar` puede traer las versiones nuevas sin chocar.
- **Las IA falsas de tus pruebas** tienen que responder `--help` con `--strict-mcp-config` y `--disallowedTools` (como el Claude
  real): sin eso, desde la 0.3.0 la pieza no corre y responde `actualizar`.

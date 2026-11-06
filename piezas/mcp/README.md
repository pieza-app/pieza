# Pieza «mcp» — conversa con tus datos desde tu IA

La persona le pregunta a la IA que ya usa (Claude, ChatGPT/Codex, Gemini) por sus datos de la app: «¿cuánto gasté en comida?»,
«¿de qué hablamos en mi última reunión?». Sin copiar ni pegar, y sin que la app tenga servidores.

- **Local:** un servidor [MCP](https://modelcontextprotocol.io) por la entrada y salida estándar. Lo abre la IA cuando lo necesita;
  no abre puertos ni sale a internet.
- **Cada app trae su propio MCP sin escribirlo:** declara sus herramientas en un módulo y la pieza arma el servidor.
- **Solo lectura por defecto.** Lo que cambia algo solo aparece si la persona lo permite en Ajustes.
- **En un clic:** Ajustes → «Conectar a tu IA» lo agrega en Claude (app de escritorio), Claude Code, ChatGPT (app de escritorio y
  Codex), Gemini CLI y Antigravity, con respaldo de su configuración.
- **Las dos formas del protocolo:** la de siempre, con `initialize` (2025-11-25 y antes: la que usan hoy esas IA), y la nueva sin
  estado (2026-07-28, con `server/discover`). Una IA nueva o una vieja conversan igual.

Requiere `nucleo`, `ia` (deja los CLI en el PATH), `i18n` y `componentes` (la sección de Ajustes usa sus clases).

## Agregarla a una app

```bash
python3 herramientas/pieza.py agregar mcp <app>
```

Eso copia `bin/mcp.py`, `bin/mcp_servidor.py`, `bin/mcp_conectar.py` y `ui/mcp.js`; escribe **una vez** `bin/mcp_herramientas.py`
(de la app desde ahí, con un ejemplo); suma `"mcp": {"modulos": ["mcp_herramientas"]}` a `app.json` y las acciones `mcpEstado`,
`mcpConectar` y `mcpReparar` a `acciones.json` (el host las corre sin código propio).

## 1. Declarar las herramientas (lo que escribe la app)

En `bin/mcp_herramientas.py`:

```python
import mcp, datos

def gastos_del_mes(args):
    mes = args.get("mes") or datos.mes_actual()
    return {"mes": mes, "total": datos.total(mes)}            # un resumen, no la base entera

def marcar_pagado(args):
    datos.marcar(args["nombre"]); return {"ok": True}

INSTRUCCIONES = "Prueba guarda tus gastos. Montos en pesos; negativo = gasto. Fechas AAAA-MM-DD."
HERRAMIENTAS = [
    mcp.herramienta("gastos_del_mes", "Total gastado en un mes. Úsala para «¿cómo voy este mes?».", gastos_del_mes,
                    {"mes": mcp.MES}),
    mcp.herramienta("marcar_pagado", "Marca un pago como hecho.", marcar_pagado,
                    {"nombre": {"type": "string", "maxLength": 100}}, ["nombre"], escribe=True),
]
```

| Función | Para qué |
|---|---|
| `mcp.herramienta(nombre, descripcion, funcion, propiedades={}, requeridos=(), *, titulo, escribe, borra)` | Una herramienta. `nombre`: minúsculas, números y `_`. `funcion(args)` recibe los argumentos **ya validados** y devuelve un dict (o una lista). |
| `mcp.FECHA`, `mcp.MES` | Esquemas listos para `AAAA-MM-DD` y `AAAA-MM`. |
| `mcp.ErrorHerramienta("…")` | Un error que la IA puede corregir (vuelve como `isError` con ese texto). Cualquier otro error vuelve solo con su tipo (`No se pudo (ValueError).`): su texto podría traer datos o detalles del código. |
| `mcp.actividad(n)` | Las últimas `n` llamadas `{fecha, herramienta, ok}` (lo muestra Ajustes). |
| `mcp.servir(herramientas, instrucciones=…)` | Arranca el servidor (lo llama `mcp_servidor.py`; úsalo tú solo si armas el tuyo). |

**Varias partes de la app, o una pieza, suman sus herramientas** con su propio módulo: `"mcp": {"modulos": ["mcp_herramientas",
"mcp_universos"]}`. Cada módulo vive en `bin/`, con su `HERRAMIENTAS` y su `INSTRUCCIONES`. Dos herramientas con el mismo nombre
detienen el servidor (mejor que una pise a otra en silencio). La forma de Alcancía (`{"nombre": (funcion, descripcion, esquema)}`)
también se entiende.

Lo que la pieza ya hace por ti: valida cada argumento contra su esquema (`type`, `enum`, `pattern`, `minimum`/`maximum`,
`maxLength`, `required`, `additionalProperties: false`), rechaza pedidos de más de 1 MB y respuestas de más de 512 KB («pide un
rango más corto»), corta a las 120 llamadas por minuto, manda a stderr lo que una herramienta imprima (nunca rompe el protocolo;
igual no imprimas datos: algunas IA guardan stderr en sus registros),
suma a las instrucciones que los datos son datos y nunca instrucciones, y anota cada llamada en `mcp-actividad.jsonl` (solo la
herramienta, la hora y si funcionó: **nunca los argumentos**).

**Buenas herramientas:** pocas y claras, con la descripción diciendo cuándo usarlas; un límite por defecto y un máximo; sin rutas,
ids internos ni claves; los montos y fechas con su unidad en `INSTRUCCIONES`. Lo que lee la IA viaja a su proveedor.

## 2. La sección «Conectar a tu IA» (Ajustes)

```js
// index.html: <script src="mcp.js"></script> después de i18n.js y componentes.js
const mcpUI = PiezaMCP.crear({ i18n, host, pintar: render, app: "Prueba", aviso: (t, o) => ui.aviso(t, o),
                               ejemplo: "¿Cuánto gasté en comida este mes?" });
window.Prueba = { ...window.Prueba, mcpListo: mcpUI.recibir };   // responde mcpEstado y mcpConectar
// al abrir Ajustes:
mcpUI.pedirEstado();
// donde va la sección:
html += mcpUI.html();
// en el manejador de clics (y de «change», para el interruptor de escribir):
if (mcpUI.manejarClic(ev)) return;
```

Muestra cada IA instalada con **Conectar** / **Quitar**, qué puede leer y qué puede cambiar, el interruptor «Permitir que mi IA
cambie cosas» (solo si la app tiene herramientas con `escribe=True`; guarda `mcp_escribir` con `config`), lo último que consultó y
la frase de privacidad. Si usas «Permitir…», la app tiene que aceptar `mcp_escribir` en su config (la pieza lo suma; con
`--sin-config=mcp_escribir` no).

**Al arrancar la app,** pide `mcpReparar` una vez (sin respuesta): si la persona movió o actualizó la app, las IA conectadas pasan a
la ruta nueva. En Swift, `host.enviar("mcpReparar", {})` desde la interfaz o `Procesador.correrJSON("mcp_conectar.py", ["reparar"])`.

**En la vista previa** (sin host), simula `mcpEstado` con `{ok: true, clientes: [{id: "claude_desktop", nombre: "Claude (app de
escritorio)", instalado: true, conectado: false}], herramientas: [...], actividad: [], escribir: false}`.

## 3. Conectarlo a mano (para quien prefiere la terminal)

La ruta es la de `bin/mcp_servidor.py` dentro de la app (`<ID>_PYTHON` es el Python que trae la app; si no, `python3`):

```bash
claude mcp add --scope user <id> -- python3 /ruta/a/bin/mcp_servidor.py      # Claude Code
codex mcp add <id> -- python3 /ruta/a/bin/mcp_servidor.py                     # ChatGPT (escritorio) y Codex
gemini mcp add -s user <id> python3 /ruta/a/bin/mcp_servidor.py               # Gemini CLI
```

Claude (app de escritorio), en `claude_desktop_config.json` (Mac: `~/Library/Application Support/Claude/`):

```json
{"mcpServers": {"<id>": {"command": "python3", "args": ["/ruta/a/bin/mcp_servidor.py"]}}}
```

Para probar sin ninguna IA: `npx @modelcontextprotocol/inspector python3 bin/mcp_servidor.py`, o a mano:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}}' \
              '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 bin/mcp_servidor.py
```

## Cómo se conecta, sin romper nada

`mcp_conectar.py` usa el comando de cada IA cuando lo tiene (`claude`, `codex`, `gemini mcp add`). Si no (Claude de escritorio,
Antigravity), edita su archivo: lo lee entero, cambia **solo** la entrada `<id>`, guarda una copia la primera vez
(`<archivo>.antes-de-<id>`) y escribe de forma atómica (si es un enlace, el archivo real). Un archivo con errores o con otra forma no
se toca: se le dice a la persona que lo conecte a mano. Quitar nunca crea un archivo que no existía.

## Seguridad

- Sin puertos ni red: solo la IA que la persona configuró puede abrirlo, y corre con sus permisos.
- Los argumentos se validan antes de llegar a la herramienta; las herramientas que escriben no existen para la IA hasta que la
  persona las permite (ni en la lista ni al llamarlas).
- Lo que devuelve una herramienta puede traer texto de terceros (la descripción de un movimiento, una nota): las instrucciones del
  servidor le dicen a la IA que son datos, nunca instrucciones. Igual, no devuelvas lo que no hace falta.
- Un nombre de módulo de `app.json` → `mcp.modulos` tiene que ser un archivo de `bin/` (nunca un módulo del sistema), y nunca
  `mcp`, `mcp_servidor` ni `mcp_conectar`.

## Pasar una app que ya tiene su MCP (Alcancía)

1. `pieza.py agregar mcp <app>`: si ya tiene `bin/mcp_servidor.py` y `bin/mcp_conectar.py`, no los pisa y avisa.
2. Mueve sus herramientas a `bin/mcp_herramientas.py`: el dict `HERRAMIENTAS = {"nombre": (funcion, descripcion, esquema)}` sirve
   tal cual, e `INSTRUCCIONES` también.
3. `pieza.py actualizar <app> mcp --forzar` y borra su `mcpConectar` de `app.json` → `acciones` (ahora lo declara la pieza; mismo
   nombre, mismos valores y misma respuesta `mcpListo`).
4. En la interfaz, cambia `data-mcp`/`data-mcp-quitar` por `mcpUI.manejarClic` y su sección por `mcpUI.html()` (o deja la suya:
   la respuesta trae además `herramientas`, `actividad` y `escribir`).
5. El error «No encontré … en este computador» llega como plantilla `{ia}` + `valores`: muéstralo con `Tp(r.error, r.valores)`.

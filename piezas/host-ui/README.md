# Pieza «host-ui» — el puente de la interfaz

La interfaz de toda app de la familia habla igual con lo que la contiene: `host.enviar(accion, datos)` hacia la app y
`window.<App>.<funcion>(json)` de vuelta. Un archivo (`ui/host.js`), sin dependencias, compatible con una CSP `script-src 'self'`.

| Dónde corre | Cómo llega el mensaje | `host.plataforma` |
|---|---|---|
| Mac (WKWebView) | `webkit.messageHandlers.<nombre>.postMessage({accion, datos})` | `window.<NOMBRE>_HOST` = `"mac"` |
| Windows / Linux (Electron) | `window.<nombre>Escritorio.enviar({accion, datos})` (lo expone el preload) | `"windows"` / `"linux"` |
| Celular (Capacitor) | `window.<nombre>Movil.enviar({accion, datos})` | `"movil"` |
| Navegador (vista previa, pruebas, demo de la página) | `simular` | `"web"` |

```html
<script src="host.js"></script>   <!-- antes de app.js: queda window.PiezaHost -->
```
```js
const host = PiezaHost.crearHost({
  nombre: "ana", global: "Ana",
  simular: {                                   // o una función (accion, datos, ctx) si ya tienes tu switch
    ...PiezaHost.simulacionesComunes(),        // probarIA, buscarActualizacion, actualizar, abrirEnlace (solo https), copiar
    listo: (d, c) => c.responder("estado", DEMO),
    guardar: (d, c) => c.luego(60, () => c.responder("guardado", { ok: true })),
  },
});
host.responder({                               // lo que llama la app: queda en window.Ana
  estado(e) { … },
  iaProbada(r) { ui.iaProbada(r); },
});
host.enviar("probarIA", { ia: "claude" });
if (host.esWeb) …                              // también esEscritorio, esMovil; <html data-host="…"> queda puesto
```

| API | |
|---|---|
| `crearHost({nombre, global, simular, ventana?, plano?, canales?})` | `nombre`: id en minúsculas (el de `app.json`); `global`: el objeto de respuestas. Un nombre que no calza lanza un error. |
| `enviar(accion, datos)` | `accion` validada (`^[A-Za-z][A-Za-z0-9]*$`); `datos` siempre un objeto (otra cosa viaja como `{}`). En la vista previa los datos van como copia JSON: la simulación nunca comparte objetos con la interfaz, igual que en la app. Una acción sin simular no hace nada. |
| `responder({funcion})` | Suma funciones a `window.<Global>` sin reemplazar el objeto (nunca `__proto__` ni `constructor`). También acepta objetos (`_pruebas`, lo que leen las pruebas de la app); otra cosa se avisa en la consola. Si la app hace `window.<Global> = {…}` después de `crearHost`, se avisa y lo nuevo se **suma** al mismo objeto (la app nativa y las piezas tienen sus respuestas ahí). |
| `atender(funcion, async (datos) => respuesta)` | Lo que la app le pide a la página y espera (`host.pedir` en «host-tauri»): lo que devuelve vuelve por `respuestaPagina {id, respuesta}` (o `null` si falla). |
| `llamar(funcion, json)` | Lo que hace la app: llama `window.<Global>.<funcion>` con una copia JSON. La simulación lo recibe como `ctx.responder`. |
| `luego(ms, f)`, `cancelarPendientes()` | Esperas de la simulación (y cortarlas en las pruebas). |
| `simulacionesComunes({espera?})` | Las respuestas de vista previa que toda app repetía. |

## El contrato que comparten todas las apps

- **Mensaje:** `{accion, datos}`. Los hosts nativos leen `datos`, nunca campos sueltos al lado de `accion`.
- **Probar la IA:** `probarIA {ia}` → `iaProbada {ia, ok, codigo?, plantilla?, valores?, ayuda?, texto?}` (la salida de
  `ia.py probar` de la pieza `ia`). Antes Graba, Corta, Repasa, Alcancía y Minuta usaban `{id}`: ya no.
- **Lo que viene del puente se valida**: la app nativa solo atiende el marco principal con su origen (ver `docs/enchufe.md`); la
  interfaz escapa todo lo que pinta (pieza `i18n`).

## Pasar una app a esta pieza

En todas: `pieza.py agregar host-ui <app>`, `<script src="host.js">` en `ui/index.html` antes de `app.js`, borrar el objeto
`host` y la constante `HOST` de `ui/app.js`, y en su lugar `const host = PiezaHost.crearHost({...})` y `const HOST = host.plataforma`.
`window.<App> = {…}` pasa a `host.responder({…})`. La función `simular(accion, d)` de cada app sigue sirviendo tal cual (modo
función); dentro, `A.x(…)` puede seguir siendo `window.<App>.x(…)` o pasar a `c.responder("x", …)` (copia JSON, como la app).

| App | Además (lo que no es mecánico) |
|---|---|
| Esquema | Nada más: ya manda `probarIA {ia}`. |
| Graba | `probarIA`: la interfaz manda `{ia}` (`ui/app.js`, `d.probar`) y lee `r.ia` en `iaProbada`; en `simular` igual. **Nativo:** `Ventana.swift` (`case "probarIA"`, `d["ia"]`) y `escritorio/src/main.js` (`probarIA(d)`, `d.ia`) responden `{ia, ok, texto}`. |
| Corta | Igual que Graba (`Ventana.swift` y la interfaz). |
| Repasa | Igual que Graba en `Ventana.swift`, **y** `movil/host/host.js` (`probarIA(d)`: `d.ia`, responde `{ia, …}`; la IA del teléfono sigue llamándose `"telefono"`). |
| Alcancía | Igual que Graba en `Ventana.swift`; en `movil/host/host.js` `probarIA` sigue en `SOLO_MAC`. |
| Minuta | Su mensaje es plano (`{accion, ...datos}`) y su preload se llama `minutaHost`: mientras `VisorWeb.swift`, `BarraMenu.swift` y `escritorio/src/main.js` no cambien, `crearHost({nombre: "minuta", global: "Minuta", plano: true, canales: {escritorio: "minutaHost"}})`. Quita la rama de Tauri (ya no se usa). No tiene `simular`: hoy pregunta `E.plataforma === "web"` en cada lugar; al pasar, junta esas ramas en `simular`. Luego cambia los hosts a `{accion, datos}` y quita `plano`. `probarIA` igual que Graba. |

## Si venías de 0.1.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `responder` acepta objetos | Puedes pasar `host.responder({ _pruebas: {…} })` en vez de asignarlo aparte. Lo que no es función ni objeto se avisa. |
| Reasignar `window.<App>` avisa y suma | Si tu app hacía `window.<App> = {…}` después de `crearHost`, ya no pierde las respuestas de las piezas, pero cámbialo por `host.responder({…})` para no ver el aviso. `window.<App>.x = …` sigue igual. |

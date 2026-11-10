# Pieza «trabajos» — lo largo, en segundo plano y sin perder nada

```python
import ia, trabajos
t = trabajos.Trabajo.nuevo("resumir", carpeta, ["leer", "escribir"], {"archivos": lista})
t.latir()                                         # latido cada 5 s mientras corre
for ruta in lista:
    if t.detenido():
        return t.terminar("detenido")
    t.poner_item(ruta, titulo=ruta, estado="escribiendo")
    texto, e = ia.preguntar_vivo(pedido, al_evento=lambda x: t.leyo(x["ruta"]) if x["t"] == "lee" else t.busco(x["patron"]),
                                 detener=t.detenido)
    t.poner_item(ruta, estado="fallo" if e else "listo", **({"error": e} if e else {}))
t.terminar("listo")
```
- Estado en `<carpeta de datos>/trabajos/<id>.json` (0600, escrito de una vez en cada cambio; hasta 40, los que esperan no se
  borran). `vista()` es lo que ve la interfaz. Estados: `corriendo` → `listo` | `con-fallas` | `detenido` | `error` |
  `esperando`; sin latido por 45 s, `interrumpido` (`estado_real`).
- Eventos JSONL en `<ID>_PROGRESO` (`emitir`): `{t: "estado", trabajo}`, `{t: "lee", id, ruta, n}`, `{t: "busca", id, patron}`.
- `detener(id)` (también `trabajos.py detener <entrada {id}>`), `t.esperar(preguntas)` + `t.seguir()`, `limpiar_preguntas`,
  `limpiar_respuestas`, `del_proyecto(proyecto, tipo)`, `esperando(proyecto)`. Un error de la IA (`{codigo, plantilla,
  valores}`) queda como frase en `error` y entero en `error_ia` para traducir.
- **Los lectores del host**, con tope por línea (1 MB) y por vuelta (4 MB):
  - Swift (`PiezaTrabajos`): `let l = LectorProgreso(prefijo: "ana") { eventos in … }`, `env["ANA_PROGRESO"] = l.url.path`,
    `l.empezar()` al lanzar y `l.terminar()` al terminar.
  - Electron: `const l = require("./progreso").lectorProgreso(aviso, { prefijo: "ana" })`, `env.ANA_PROGRESO = l.ruta`, `l.terminar()`.
- `ver` y `detener` no saben de proyectos: si la app tiene varios, revisa `t.x["proyecto"]` antes (como Esquema).

## Pasar una app a esta pieza
**Esquema**: `pieza.py actualizar esquema trabajos --forzar` deja `bin/trabajos.py` igual salvo `comun.` → `nucleo.` y el error
de la IA sin `ia_vivo` (mismo resultado). `documentar.detener` puede usar `trabajos.detener` después de su revisión de proyecto.
`LectorProgreso` sale de `Servicios.swift` (target `PiezaTrabajos` en `Package.swift`, `import PiezaTrabajos`, el `init` pide
`prefijo:`) y `lectorProgreso` de `escritorio/src/servicios.js` (`require("./progreso")`, segundo argumento `{prefijo: "esquema"}`).
**Las demás** (Corta y Graba con `estado.json` por carpeta, Minuta con `procesar.log`): sus procesos largos no tienen latido ni
«Detener»; pasarlos a trabajos es una mejora por app, no mecánica.

## Con el host genérico (0.2.0)
Una acción declarada con `"limite": "trabajo"` (o `{"segun": "orden", "valores": {"documentar": "trabajo"}, "otro": 120}`) no
tiene tope de tiempo en `host-mac`/`host-escritorio` 0.2: el host pone `<ID>_LATIDO` y el hilo de `t.latir()` lo toca cada 5 s
(`trabajos.latir_host()`). Si deja de latir por 45 s (120 s el primero), el host lo corta. Algo largo que no es un `Trabajo`:
`trabajos.mantener_vivo()` al empezar. Sin host que lo pida, nada cambia.

## Al cerrar la app (0.2.1)
Al salir, el host manda SIGTERM a lo que siga corriendo. Con `mantener_vivo()` el script sale con `SystemExit` (código 143): corren
sus `finally` y sus `with`, así borra sus temporales (un `.wav` a medias, una carpeta de trabajo). Si la app ya puso su propio
manejador de SIGTERM, gana el suyo; `mantener_vivo(limpiar_al_cortar=False)` no toca la señal. `trabajos.cortar_con_systemexit()`
hace solo eso, para un script que no late.

## Si venías de la 0.2.0
Nada que cambiar. **Corta** puede borrar la línea `signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))` que sigue a
`trabajos.mantener_vivo()` en `bin/render.py` y `bin/importar.py` (y el `import signal` si ya no se usa): ahora lo hace la pieza.

## Si venías de la 0.1.0 o 0.1.1
Nada que cambiar: 0.2.0 solo suma el latido para el host, y desde 0.1.1 `terminar` con un error de la IA raro (valores que no son texto) ya no se cae.

## En Rust (0.3.0)
Con host-tauri, también en `escritorio/src/pieza/trabajos.rs`, con el mismo formato en disco que `trabajos.py`:

```rust
let ts = trabajos::Trabajos::nuevos(&carpeta_datos, Arc::new(move |e| avisar_interfaz(e)));
let t = ts.crear("resumir", &carpeta, &["leer", "escribir"], json!({}))?;
t.latir();
// … t.etapa("escribir"); t.leyo(ruta); t.poner_item(ruta, campos, None); con `detener: &|| t.detenido()` en la IA
t.terminar("listo", None);
```

# Pieza «red» — HTTPS desde los scripts, sin sorpresas

```python
import red
r = red.Red(["api.ejemplo.com"], "Banco Ejemplo", maximo=5 * 1024 * 1024, tiempo=60)
try:
    datos = r.get("https://api.ejemplo.com/v1/movimientos", cabeceras={"Authorization": "Bearer " + llave})
    bytes_ = r.post(url, formulario={"a": "b"}, crudo=True)
except red.ErrorRed as e:
    responder(salida, e.como_dict())   # {ok: false, codigo, plantilla, valores, error}
```

- Solo `https://` a los dominios de la lista (exactos), puerto 443, sin `usuario:clave@`. Lo demás ni sale (`no_permitida`).
- **Nunca sigue redirecciones** (`redireccion`): se llevarían la llave a otro dominio.
- Tope de tamaño (cortado al leer, sin confiar en `Content-Length`: `grande`) y de tiempo del pedido entero (`demora`).
- Códigos: `no_permitida`, `redireccion`, `llave` (401/403), `esperar` (429), `error` (`{estado}`), `sin_conexion`, `demora`,
  `grande`, `no_entendi`. La frase nunca trae la credencial; `e.cuerpo` (hasta 2000 caracteres) es solo para registros.
- **Subidas grandes** (`r.subir(url, archivo, parte=8 MB, avance=fn, cabeceras=…)`): un PUT por parte con
  `Content-Range: bytes a-b/total`; mientras falta, el servicio responde 308 (sin `Location`) con `Range: bytes=0-n` y se sigue
  desde ahí; al final, su JSON. `desde=` para retomar. `pedir(…, datos=bytes, tipo=…)` manda un cuerpo tal cual.
- User-Agent: «<Nombre> (<repo>)» de `app.json` (`"repo": "dueño/repo"`; si no tiene esa forma, solo el nombre), siempre en
  ASCII.
- Pruebas: `<ID>_RED_PRUEBA=http://127.0.0.1:<puerto>` manda todo a un servidor falso (`/<dominio>/<ruta>`), solo fuera de la
  app (si el host puso `<ID>_RECURSOS`, se ignora).

## Si venías de la 0.1
Nada obligatorio: el User-Agent ya no rompe el pedido con un nombre fuera de latin-1. Graba (YouTube) puede usar `subir` cuando
pase a la pieza `youtube`.

## Pasar una app a esta pieza
**Alcancía** (la única que la usa hoy, en `bin/conectores/` y `sincronizar.py`): `pieza.py actualizar alcancia red --forzar`.
`ErrorRed(mensaje, estado, cuerpo)` pasa a `ErrorRed(codigo, valores, estado, cuerpo)`: donde se mostraba `str(e)` sigue
igual (misma frase en español); para traducir, mandar `e.como_dict()` y en la interfaz `Tp(r.plantilla, r.valores)`. La variable
de pruebas sigue siendo `ALCANCIA_RED_PRUEBA` (sale de `app.json`). Nuevo: tope de 10 MB por defecto (`maximo=` si un conector
baja más) y de 60 s del pedido entero. El User-Agent pasa a «<Nombre> (<repo de app.json>)»: poner `"repo"` en `app.json`.

## En Rust (0.3.0)
Con host-tauri, también en `escritorio/src/pieza/red.rs`. Mismas reglas que `red.py`:

```rust
let r = red::Red::nueva(&["api.ejemplo.com"], "Banco Ejemplo", &red::agente("Alcancía", Some("alcancia-app/alcancia")))?;
let saldo = r.get("https://api.ejemplo.com/v1/saldo", &[("Authorization", &format!("Bearer {llave}"))])?;  // Err(ErrorRed)
```

`ErrorRed::json()` da `{ok: false, codigo, plantilla, valores, error}`. `subir(...)` sube por partes y retoma desde el 308.

# Pieza «nucleo» — lo que todo script necesita

Lee `app.json` de la raíz de la app (lo busca hacia arriba desde el script; `<ID>_RECURSOS` solo si su prefijo es el id de ese
`app.json`) y entrega todo lo que cambia por app sin que el código diga el nombre de ninguna.

> **Empaqueta `app.json` junto a `bin/`.** En la app instalada, `nucleo` lo busca al lado de los scripts: inclúyelo en el `.app`
> (`empaquetar.sh`) y en Electron (`extraResources`). Sin él, ningún script arranca.

```python
import nucleo
nucleo.app()                       # {"nombre", "id", "datos", "config"}
nucleo.carpeta_datos()             # Application Support / %APPDATA% / ~/.config (o ~/<Nombre>/.<id> con "datos": "visible"), 0700
nucleo.config()                    # solo las claves y valores que declara app.json
nucleo.guardar_config({"tema": "oscuro"})       # nunca cambia una clave "interfaz": false (ver abajo)
nucleo.guardar_config({"carpeta": r}, desde_interfaz=False)  # solo el host, tras el selector del sistema
nucleo.escribir_json(ruta, valor)  # atómico, conserva permisos, sin temporales huérfanos (nuevo: 0600)
nucleo.escribir_atomico(ruta, texto, modo=nucleo.DOCUMENTO)  # un documento de la persona: 0644
nucleo.ruta_en(base, relativa)     # None si se sale de base
nucleo.script({"accion": fn}, __doc__)  # contrato: script.py <accion> [entrada.json] <salida.json>; errores como {"ok": false}
```

Variables que entiende: `<ID>_RECURSOS` (raíz de la app) y `<ID>_DATOS` (carpeta de datos), con `<ID>` = `id` en mayúsculas.

### Config en `app.json`

```json
"config": {"idioma_ui": ["es", "en"], "bienvenida": "bool", "carpeta": {"tipo": "texto", "interfaz": false}}
```

Una lista = valores posibles; `"bool"`, `"texto"` (hasta 2000 caracteres) o `"numero"` = tipo; `{"tipo": "texto", "max": 200000}`
para un texto más largo, `{"tipo": "texto", "patron": "auto|[a-z]{2,3}"}` para uno que tiene que calzar entero (un valor que va a otro programa); `guardar_config` conserva en el archivo las claves que no conoce. `{"tipo": …, "interfaz": false}` = una
clave que la interfaz no puede cambiar (la cambia el host después de algo que hizo la persona en el sistema, como elegir una carpeta).

### Datos a la vista (`"datos": "visible"`)

Con `"datos": "visible"` la carpeta es `~/<Nombre>/.<id>/` (como Graba: `~/Graba/.graba`), creada en 0700 (y `~/<Nombre>` también, si
la crea `nucleo`). En las pruebas, `<ID>_CARPETA` mueve `~/<Nombre>` entero (o `<ID>_DATOS` solo la interna) a una carpeta
temporal: nunca se tocan los datos reales. `"privado": true` en `app.json` deja todo archivo que escribe `nucleo` en 0600.

### `ruta_en(base, relativa)`

La ruta absoluta de `relativa` dentro de `base`, o `None` si se sale (`..`, absoluta, un enlace hacia afuera). Desde 0.7.1 también
`None` si `base` está vacía, es relativa o no es una carpeta que existe: el `""` que manda el inyector `carpetaActual` sin carpeta
nunca vuelve a ser la carpeta de trabajo del script.

### Si venías de la 0.7.0

Nada que cambiar. Esquema: `bin/carpeta.py` puede dejar de revisar `_sin_carpeta` antes de `ruta_en` (ya da `None`); si lo dejas, no
estorba. Si llamabas a `ruta_en` con una carpeta que todavía no existe, créala antes.

### Una carpeta propia (`"datos": {"carpeta": "~/minuta"}`)

Para una app cuyos datos ya viven en una carpeta suya (en Minuta, `~/minuta` es a la vez el checkout y los datos): `nucleo` la usa
tal cual, sin crearla ni cambiarle permisos, y solo si está dentro de `~`. `<ID>_DATOS` sigue mandando en las pruebas.

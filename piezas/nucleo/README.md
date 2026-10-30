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

Una lista = valores posibles; `"bool"`, `"texto"` (hasta 2000 caracteres) o `"numero"` = tipo; `{"tipo": …, "interfaz": false}` = una
clave que la interfaz no puede cambiar (la cambia el host después de algo que hizo la persona en el sistema, como elegir una carpeta).

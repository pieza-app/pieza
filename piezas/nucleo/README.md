# Pieza «nucleo» — lo que todo script necesita

Lee `app.json` de la raíz de la app (la ubica con `<ID>_RECURSOS` o buscando hacia arriba) y entrega todo lo que cambia por app
sin que el código diga el nombre de ninguna.

```python
import nucleo
nucleo.app()                       # {"nombre", "id", "datos", "config"}
nucleo.carpeta_datos()             # Application Support / %APPDATA% / ~/.config (o ~/<Nombre>/.<id> con "datos": "visible"), 0700
nucleo.config()                    # solo las claves y valores que declara app.json
nucleo.guardar_config({"tema": "oscuro"})
nucleo.escribir_json(ruta, valor)  # atómico, conserva permisos, sin temporales huérfanos
nucleo.ruta_en(base, relativa)     # None si se sale de base
nucleo.script({"accion": fn}, __doc__)  # contrato: script.py <accion> [entrada.json] <salida.json>; errores como {"ok": false}
```

Variables que entiende: `<ID>_RECURSOS` (raíz de la app) y `<ID>_DATOS` (carpeta de datos), con `<ID>` = `id` en mayúsculas.

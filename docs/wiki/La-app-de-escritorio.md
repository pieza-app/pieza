# La app de escritorio

Toda app de Pieza tiene cuatro capas:

```
ui/          la interfaz web (la misma en todos los sistemas)
host         la app nativa: host-tauri en Mac, Windows y Linux
bin/         scripts de Python (solo biblioteca estándar)
datos        en el computador de la persona
```

## `host-tauri`

- Es **un solo host** para Mac, Windows y Linux, en Rust con Tauri.
- Usa el navegador que ya trae el sistema. Por eso la app es liviana.
- El puente solo atiende a la ventana propia, con su página en `ui/`.
- Corre los scripts de `bin/` con límite de tiempo.
- Guarda los secretos en el llavero del sistema.

## Las acciones

Una acción la atiende uno de tres lados, en este orden:

1. **Registrada** en `escritorio/src/main.rs`: lo nativo propio de la app.
2. **Del host**: `listo`, `config`, `abrirEnlace` y las actualizaciones.
3. **Declarada** en `app.json` → `acciones`: solo corre un script. No necesita código nativo.

## Probar

- `cd escritorio && cargo test`.
- `bash escritorio/pruebas/arranque.sh` (en Linux la abre con Xvfb).
- `bash pruebas/correr.sh` corre todo.

## Lo que solo existe en Apple

Capturar la pantalla o el audio del sistema, el dictado o separar quién habla no se reescribe en Rust. Queda como un
**ayudante** chico en Swift, que la app corre como un script. Graba y Minuta lo necesitan: por eso son las últimas en pasar a
`host-tauri`.

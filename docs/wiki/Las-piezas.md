# Las piezas

Una pieza es una carpeta en `piezas/<id>/` con su `pieza.json`, su código, su ícono y un README corto.
La lista completa, con versiones, está en el [catálogo](https://github.com/pieza-app/pieza/blob/main/docs/catalogo.md).

## Agregar una pieza a una app

1. `python3 herramientas/pieza.py agregar <pieza> <carpeta-de-la-app>`.
2. La pieza se copia dentro de la app. Desde ahí es de la app: la puedes cambiar.
3. `piezas.json` recuerda la versión y la huella de cada archivo.

## Copiar y adueñarse

- `pieza.py estado <app>` dice qué tiene la app, qué hay nuevo y qué cambió.
- `pieza.py actualizar <app>` trae lo nuevo **sin pisar** lo que la app cambió.
- `pieza.py diferencias <app> <pieza>` muestra lo que la app mejoró, para devolverlo a Pieza.

## Algunas piezas

| Pieza | Para qué |
|---|---|
| `host-tauri` | La app nativa de Mac, Windows y Linux (Rust + Tauri) |
| `ia` | La IA de la persona (Claude, Codex o Gemini) |
| `i18n`, `bienvenida` | Idiomas y el primer uso (el idioma primero) |
| `tema`, `componentes` | Colores claro y oscuro, botones, diálogos y avisos |
| `actualizaciones`, `empaquetado` | Versiones seguras (SHA-256) y las descargas de cada sistema |
| `catalogo` | Contenido de la comunidad, validado y con huella |
| `github` | El repo listo para la comunidad: workflows, Dependabot y esta wiki |

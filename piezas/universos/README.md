# Pieza «universos» — colores y textos por temas

Un **universo** cambia dos cosas de la app:

1. Los colores: un tema de la pieza «tema» (`claro`, `oscuro` o `vidrio`, con colores propios si quiere).
2. Los textos y las listas que la app deja cambiar (un saludo, los elogios, los rangos…).

Un universo es **solo datos**. Nunca trae HTML, CSS ni código.

## Lo que trae

| Archivo | Va a | Qué es |
|---|---|---|
| `ui/universos.js` | `ui/universos.js` | `PiezaUniversos.crear({tema})`: `usar`, `dejar`, `texto`, `lista`, `actual` |
| `python/universo_formato.py` | `bin/universo_formato.py` | `validar(universo)` (también es el validador del catálogo) |
| `ui/universos/*.json` | `ui/universos/` | Tres de base: Espacio (vidrio), Bosque (claro) y Neón (oscuro) |

## Cómo se usa

1. Carga `universos.js` después de `tema.js`.
2. Crea la instancia con el tema: `const u = PiezaUniversos.crear({ tema });`.
3. Al elegir uno: `u.usar(universo)`. Registra su tema y lo aplica. Devuelve `null` si no sirve.
4. En la interfaz: `u.texto("saludo", "Hola")` y `u.lista("elogios", ["¡Bien!"])`. Lo que el universo no trae usa el texto de la app.
5. Escapa lo que muestras, como todo lo que viene de afuera.
6. Guarda el id elegido en una clave propia de la app (por ejemplo `config.universo`).

## El formato

```json
{"id": "espacio", "categoria": "espacio", "nombre": "Espacio", "emoji": "🚀", "idioma": "es",
 "descripcion": "…", "autor": "…", "categorias": ["Espacio"],
 "tema": {"base": "vidrio", "colores": {"acento": "#ffb020"}},
 "textos": {"saludo": "Bienvenida a bordo"}, "listas": {"elogios": ["Despegue perfecto."]}}
```

- `tema.colores`: solo los tokens de «tema», en `#rrggbb`.
- `textos`: hasta 60, de hasta 200 caracteres, sin `<`.
- `listas`: hasta 12, cada una de 1 a 30 textos de hasta 120 caracteres, sin `<`.
- La app decide qué claves usa. Las demás se ignoran.

## Universos de la comunidad

Usa la pieza «catalogo» con un tipo `universos`:

```json
"catalogo": {"repo": "ana-app/ana-catalogo", "tipos": {"universos": {"validador": "universo_formato", "singular": "universo", "incluidos": "ui/universos"}}}
```

- Los de base van dentro de la app (`ui/universos/`), así también los ve la vista previa.
- En el repo del catálogo, cada universo va en `universos/<categoria>/<id>.json`.
- `catalogo.py generar universos . index.json --validador=universo_formato.py` arma el índice.
- Una persona revisa cada universo antes de juntarlo: sin personajes, logos ni marcas de otros.

# Pieza «bienvenida» — el primer uso, con el idioma primero

El paso 0 es siempre el idioma: título fijo «Elige tu idioma · Choose your language», cada idioma escrito en su propio idioma
(`data-sin-traducir`, `lang`), el del sistema marcado «Sugerido» y con el foco, teclas 1/2 y flechas. Hasta elegir no se pinta
nada más y los avisos esperan. Después, los pasos que suma la app o cada pieza, y «Todo listo». Requiere `i18n`.

```html
<link rel="stylesheet" href="bienvenida.css">
<script src="i18n.js"></script><script src="bienvenida.js"></script>
```
```js
const bv = PiezaBienvenida.crear({
  i18n,
  guardarIdioma: (c) => host.enviar("config", { idioma_ui: c }),   // el mismo camino que Ajustes
  terminar: () => host.enviar("config", { bienvenida: true }),
  pintar, mostrarAviso: toast,
});
bv.sumarPaso({ id: "hola", titulo: "Hola, esto es Ana", cuerpo: () => "<p>…</p>", orden: 10 });
bv.sumarPaso({ id: "ia", titulo: "Tu IA", cuerpo: filasIA, puede: () => !!E.config.ia, orden: 20 });
bv.abrir({ config: E.config, forzar: new URLSearchParams(location.search).has("bienvenida") });

function pintar() {
  if (bv.soloIdioma) { raiz.innerHTML = bv.html(); bv.enfocar(); return; }   // nada más detrás
  raiz.innerHTML = app() + (bv.activa ? `<div class="capa"><div class="dialogo" role="dialog" aria-modal="true" aria-labelledby="t-bv">${bv.html()}</div></div>` : "");
  i18n.traducirDOM(raiz);
}
document.addEventListener("click", (ev) => { if (bv.manejarClic(ev)) return; /* … */ });
document.addEventListener("keydown", (ev) => { if (bv.manejarTecla(ev)) return; /* … */ });
function toast(t) { if (bv.retener(t)) return; /* … */ }
```

| API | |
|---|---|
| `crear({i18n, guardarIdioma, cargarIdioma?, terminar?, pintar?, mostrarAviso?, idiomas?, sistema?, listo?, documento?})` | `idiomas`: `[{codigo, nombre, sugerido}]` (hasta 9); `listo: false` quita el último paso o `{titulo, cuerpo}` lo cambia. |
| `sumarPaso({id, titulo, cuerpo(), puede?(), orden?})` | `titulo` es una frase en español (va por `T`); `cuerpo` lo arma quien suma el paso (con `esc()`) y la app lo traduce. |
| `abrir({config, forzar})` | `bienvenida: true` → no se abre; sin `idioma_ui` → paso 0; con idioma → desde el paso 1. |
| `html()`, `soloIdioma`, `activa`, `paso`, `pasos` | |
| `elegirIdioma(c)`, `ir(n)`, `terminar()`, `retener(...aviso)` | |
| `manejarClic(ev)`, `manejarTecla(ev)`, `enfocar()` | Devuelven `true` si era de la bienvenida. |

La app nativa tampoco muestra ni pide nada (permisos, actualizaciones) antes de que se guarde `idioma_ui`.

## Colores y pasos obligatorios (0.2.0)

- Los colores son variables propias de la pieza: define en el CSS de tu app `--bv-acento`, `--bv-linea`, `--bv-panel` y
  `--bv-texto-suave` (por ejemplo `--bv-texto-suave: var(--texto-suave)`). Sin definirlas se usan unos neutros.
- `sumarPaso({…, saltable: false})` quita «Lo hago después» en un paso que la app necesita sí o sí (por defecto, se puede saltar).
- Los atributos son `data-bv-idioma`, `.opciones-idioma` y `.opcion-idioma`. Si tu app o sus pruebas usaban otros (`data-idioma`,
  `.idiomas`), cámbialos al adoptar la pieza.

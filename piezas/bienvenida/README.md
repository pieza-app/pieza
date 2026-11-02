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
  // Con la pieza «componentes»: la caja accesible (foco, Tab, sin Esc). Cada paso trae data-pz-clave: el foco va a su título.
  raiz.innerHTML = app() + (bv.activa ? ui.envolver(bv.html(), { id: "t-bv", sinEsc: true }) : "") + ui.capas();
  i18n.traducirDOM(raiz);
  ui.despuesDePintar();
}
document.addEventListener("click", (ev) => { if (bv.manejarClic(ev)) return; /* … */ });
document.addEventListener("keydown", (ev) => { if (bv.manejarTecla(ev)) return; /* … */ });
function toast(t) { if (bv.retener(t)) return; /* … */ }
```

| API | |
|---|---|
| `crear({i18n, guardarIdioma, cargarIdioma?, terminar?(como, paso), pintar?, mostrarAviso?, idiomas?, sistema?, listo?, documento?, ajustes?, logo?})` | `idiomas`: `[{codigo, nombre, sugerido, detalle?}]` (hasta 9; `detalle` va debajo del nombre, en ese idioma); `listo: false` quita el último paso o `{titulo, cuerpo}` lo cambia. `ajustes: {es: "Para adultos", en: "For grown-ups"}`: dónde se cambia lo elegido (en la nota del idioma y en «Todo listo»; `false`: sin nota). `logo`: HTML de la app arriba del paso del idioma. `terminar` recibe `"fin"` o `"despues"` y el id del paso. |
| `sumarPaso({id, titulo, cuerpo(), puede?(), orden?, saltable?, despues?, fin?})` | `titulo` es una frase en español (va por `T`); `cuerpo` lo arma quien suma el paso (con `esc()`) y la app lo traduce. En el último paso (con `listo: false`): `saltable: true` o `despues: "texto"` muestra «Lo hago después»; `fin: {texto, principal: false, accion}` cambia el botón que termina (la acción corre después de terminar). |
| `abrir({config, forzar})` | `bienvenida: true` → no se abre; sin `idioma_ui` → paso 0; con idioma → desde el paso 1. |
| `html()`, `soloIdioma`, `activa`, `paso`, `pasos` | |
| `elegirIdioma(c)`, `ir(n)`, `terminar()`, `retener(...aviso)` | |
| `manejarClic(ev)`, `manejarTecla(ev)`, `enfocar()` | Devuelven `true` si era de la bienvenida. |

La app nativa tampoco muestra ni pide nada (permisos, actualizaciones) antes de que se guarde `idioma_ui`.

## Colores y pasos obligatorios (0.2.0)

- Los colores son variables propias de la pieza: define en el CSS de tu app `--bv-acento`, `--bv-linea`, `--bv-panel` y
  `--bv-texto-suave` (por ejemplo `--bv-texto-suave: var(--texto-suave)`). Sin definirlas se usan unos neutros. Con la pieza
  `tema` ya quedan conectadas a sus tokens: no hay que definirlas.
- `sumarPaso({…, saltable: false})` quita «Lo hago después» en un paso que la app necesita sí o sí (por defecto, se puede saltar).
- Los atributos son `data-bv-idioma`, `.opciones-idioma` y `.opcion-idioma`. Si tu app o sus pruebas usaban otros (`data-idioma`,
  `.idiomas`), cámbialos al adoptar la pieza.

## Botones (0.3.0)

Los botones de los pasos usan las clases de la pieza `componentes`: `.pz-pie`, `.pz-boton`, `.pz-principal` y `.pz-izq` («Atrás»).
Con `componentes` se ven como el resto de la app; sin ella, `bienvenida.css` los dibuja con `:where()` (especificidad 0) y los
colores `--bv-*` (más `--bv-sobre-acento`, el texto del botón principal). Cada paso lleva `data-pz-clave="bv-<id>"`.

## El sugerido y otros textos (0.4.0)

- El idioma sugerido lleva `data-autofoco`: con `componentes`, `ui.despuesDePintar()` lo enfoca solo (no hace falta `bv.enfocar()`).
- `ajustes` va por `T(ajustes.es)` en «Todo listo»: tradúcelo en tu `en.json`. Las frases nuevas («…en {donde}.», «Ya puedes
  empezar.») las suma `pieza.py actualizar`.

## Si venías de 0.3.0

Nada que cambiar. Lo que cada app puede usar o borrar:

| App | Qué |
|---|---|
| Corta | Vuelve el detalle bajo cada idioma: `idiomas: [{…, detalle: "Continuar en español"}, {…, detalle: "Continue in English"}]`; ya no hace falta reemplazar `class="opcion-idioma sugerido"` por `data-autofoco` en el HTML (la pieza lo pone). El logo puede ir con `logo` en vez de afuera de `bv.html()`. |
| Repasa (cuando la adopte) | `ajustes: {es: "Para adultos", en: "For grown-ups"}` y el paso de la IA con `saltable: true` («Lo hago después» y «Empezar»). Faltan solo sus cambios de atributos en `app.js` y las pruebas. |
| Alcancía (cuando la adopte) | El último paso con su acción: `sumarPaso({id: "cartola", …, fin: {texto: "Empezar sin cartola", principal: false}})` (el botón principal sigue en el cuerpo) y, en el celular, `despues: "Lo hago después"`; `logo: LOGO`. |
| Graba | `logo` para su tarjeta del idioma. |

Lo que sigue pendiente (en `docs/catalogo.md`): abrir mientras falte algo aunque la bienvenida ya se hizo (Graba), pasos con
sub-pantallas y estado propio, y el primer uso decidido por la app (Minuta).

## Si venías de 0.2.0

| Qué cambió | Qué hacer en la app |
|---|---|
| `.pie-dialogo`, `.boton`, `.principal`, `.izq` → `.pz-pie`, `.pz-boton`, `.pz-principal`, `.pz-izq` | Borra de tu `app.css` lo que dibujaba `.pieza-bv .boton`/`.pie-dialogo`/`.izq` (Esquema lo copiaba de `componentes`). En tus pruebas: `.pieza-bv .boton.principal` → `.pieza-bv .pz-boton.pz-principal`. |
| La caja la pone `ui.envolver` | Si armabas `<div class="capa"><div class="dialogo" role="dialog" …>` alrededor de `bv.html()`, cámbialo por `ui.envolver(bv.html(), {id: "t-bv", sinEsc: true})`. |
